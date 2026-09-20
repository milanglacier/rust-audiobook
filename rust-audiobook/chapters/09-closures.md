---
title: 第九章 Closure：捕获环境的函数
---

# 第九章 Closure：捕获环境的函数

上一章我们写迭代器链的时候，传给 map 和 filter 的那些小函数，写法有点特别：两条竖线夹着参数，后面跟着表达式，不需要名字，也不需要写 fn。这种东西叫 closure，中文可以叫闭包。closure 和普通函数最大的区别是什么？它能抓住周围环境里的变量。而在 Rust 里，这个"抓"的方式和所有权系统紧密绑定——是借用还是 move，编译器都要管。

这一章讲四件事：closure 的基本语法，三种捕获方式，三种 closure trait 分别对应什么行为，以及 move closure 在线程中的必要性。

## closure 的语法

我们先从最简单的例子开始。假设你有一个数字列表，想找出所有大于某个阈值的数。如果用普通函数，你没法在函数里直接引用阈值这个局部变量。但用 closure 可以。

定义一个变量 threshold 等于 5，然后写一个 closure，接收一个引用参数 x，返回 x 是否大于 threshold。注意，threshold 不是 closure 的参数，它是从周围环境里捕获的。

```rust
fn main() {
    let threshold = 5;
    let above = |x: &i32| *x > threshold;
    let numbers = vec![1, 3, 5, 7, 9];
    let result: Vec<_> = numbers.iter().filter(|x| above(x)).collect();
    println!("{:?}", result);
}
```

closure 的语法是两条竖线之间写参数，竖线后面写表达式或者代码块。如果 closure 的逻辑只有一行，可以省略大括号和 return。

和普通函数相比，closure 有两个便利。第一，参数类型大多数时候可以省略，编译器能从上下文推断。第二，返回类型也可以省略。所以一个很短的 closure 可以写成这样简洁的形式。

```rust
let add_one = |x| x + 1;
```

不过有一点要注意：一旦编译器在第一次使用时推断了 closure 的参数类型，后面就不能再用不同的类型调用它。closure 不是泛型函数，它的类型在第一次调用时就固定了。

所以记住：closure 就是能捕获环境变量的匿名函数，语法简洁，类型由编译器推断。

## 三种捕获方式

closure 怎么捕获环境变量？Rust 有三种方式，编译器会自动选择最轻量的那种。

第一种是不可变借用。如果 closure 里只是读取一个变量，编译器就用不可变引用来捕获它。这是最常见的情况，就像刚才 threshold 那个例子。closure 借了 threshold 来看看，不改它，不拿走它。

```rust
fn main() {
    let name = String::from("Rust");
    let greet = || println!("Hello, {name}!");
    greet();
    println!("{name}"); // name 依然有效
}
```

greet 这个 closure 只是读取了 name，所以用不可变借用捕获。调用 greet 之后，name 还是可以正常使用的。

第二种是可变借用。如果 closure 需要修改一个变量，编译器就用可变引用来捕获它。这意味着在 closure 存在期间，这个变量不能被别的代码使用。

```rust
fn main() {
    let mut count = 0;
    let mut increment = || {
        count += 1;
        println!("count: {count}");
    };
    increment();
    increment();
    // 这里 closure 不再被使用，count 的可变借用释放了
    println!("final: {count}");
}
```

注意两件事。第一，increment 这个变量本身必须声明为 mut，因为每次调用 closure 都会改变它捕获的状态。第二，在 closure 还活着的时候，你不能在 closure 之外访问 count，因为可变借用是独占的。

第三种是 move，也就是获取所有权。如果 closure 需要拿走一个变量的所有权，编译器就直接把变量 move 进 closure。这通常发生在 closure 的生命周期比它捕获的变量更长的时候。

你也可以用 move 关键字强制 closure 获取所有权，即使它只是读取变量。我们在 closure 前面加上 move。

```rust
fn main() {
    let name = String::from("Rust");
    let greet = move || println!("Hello, {name}!");
    greet();
    // println!("{name}"); // 编译错误：name 已经被 move 了
}
```

加了 move 之后，name 的所有权转移到了 closure 里。closure 外面的 name 就失效了。

所以记住：编译器会自动选择最轻量的捕获方式。只读就不可变借用，需要改就可变借用，需要拿走就 move。你也可以用 move 关键字强制获取所有权。

## 三种 closure trait

三种捕获方式对应三种 trait：Fn、FnMut 和 FnOnce。理解这三个 trait 是理解 Rust closure 系统的关键。

FnOnce 是最宽泛的。所有 closure 都实现了 FnOnce。FnOnce 的意思是：这个 closure 至少能被调用一次。为什么叫 Once？因为如果 closure 获取了某个变量的所有权并且在调用时消耗了它，那第二次调用就没有值可用了。

```rust
fn consume_closure<F: FnOnce() -> String>(f: F) {
    let result = f();
    println!("{result}");
}

fn main() {
    let name = String::from("Rust");
    let c = move || name; // move 进来，然后返回出去
    consume_closure(c);
    // consume_closure(c); // 编译错误：c 已经被消耗了
}
```

这个 closure 把 name move 进来，调用时又把 name 返回出去。name 的所有权转移出了 closure，所以 closure 只能被调用一次。

FnMut 比 FnOnce 多了一个保证：可以被调用多次。但它可能会修改捕获的变量。实现了 FnMut 的 closure 自动也实现了 FnOnce。

```rust
fn call_twice<F: FnMut()>(mut f: F) {
    f();
    f();
}

fn main() {
    let mut count = 0;
    let increment = || count += 1;
    call_twice(increment);
    println!("{count}");
}
```

注意 call_twice 的参数 f 需要声明为 mut，因为调用 FnMut 的 closure 会修改它的内部状态。

Fn 是最严格的。实现了 Fn 的 closure 可以被调用任意次，而且不会修改任何捕获的变量。它只是读取。实现了 Fn 的 closure 自动也实现了 FnMut 和 FnOnce。

三者的关系是：Fn 是 FnMut 的子集，FnMut 是 FnOnce 的子集。

当你写一个泛型函数接收 closure 作为参数时，该选哪个 trait？原则是：用最宽泛的那个就行。如果你只调用一次，用 FnOnce。如果你要调用多次，用 FnMut。如果你要调用多次而且需要在多线程间共享，用 Fn。选得越宽泛，调用者能传的 closure 种类就越多。

## 把 closure 作为参数和返回值

我们来看一个实际的例子：写一个函数，接收一个 closure 作为过滤条件，对一个列表做过滤。

```rust
fn filter_list<F>(list: &[i32], predicate: F) -> Vec<i32>
where
    F: Fn(&i32) -> bool,
{
    list.iter().filter(|x| predicate(x)).copied().collect()
}

fn main() {
    let numbers = vec![1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
    let evens = filter_list(&numbers, |x| x % 2 == 0);
    println!("{:?}", evens);
}
```

泛型参数 F 带了一个 trait bound：Fn 引用 i32 返回 bool。任何满足这个签名的 closure 或者普通函数都可以传进来。

返回 closure 的时候稍微不一样。因为 closure 的具体类型是编译器生成的匿名类型，你没法直接写出类型名字。这时候就要用 impl Trait 语法。

```rust
fn make_adder(x: i32) -> impl Fn(i32) -> i32 {
    move |y| x + y
}

fn main() {
    let add_five = make_adder(5);
    println!("{}", add_five(3));
}
```

注意这里必须用 move。因为 x 是 make_adder 的参数，函数返回后 x 就不存在了。如果 closure 只是借用 x，就会产生悬垂引用。move 让 closure 获取 x 的所有权，这样 closure 可以安全地活到函数返回之后。

这个例子也解释了为什么返回 closure 几乎总是需要 move。closure 要活得比创建它的函数更久，就必须拥有它捕获的一切。

## move closure 和线程

move closure 最重要的应用场景是多线程。当你用 spawn 创建一个新线程时，传给新线程的 closure 必须拥有它使用的所有数据。因为新线程可能活得比创建它的线程更久，借用在这里行不通。

```rust
use std::thread;

fn main() {
    let message = String::from("hello from thread");
    let handle = thread::spawn(move || {
        println!("{message}");
    });
    handle.join().unwrap();
}
```

如果你去掉 move，编译器会报错：closure may outlive the current function, but it borrows message, which is owned by the current function。编译器告诉你：这个 closure 可能比当前函数活得更久，但它借用了 message，而 message 属于当前函数。解决办法就是 move。

这就是所有权系统和 closure 的交汇点：编译器通过追踪 closure 的捕获方式，确保跨线程传递数据时不会出现悬垂引用或数据竞争。这个机制是下一章讲并发安全的基础。

## 回顾

我们来回顾这一章的要点。

第一，closure 是能捕获环境变量的匿名函数，语法简洁，参数和返回类型由编译器推断。

第二，closure 有三种捕获方式：不可变借用、可变借用、move。编译器自动选择最轻量的方式，你也可以用 move 关键字强制获取所有权。

第三，三种捕获方式对应三种 trait。Fn 只读，可以调用任意次。FnMut 可以修改捕获的变量，也可以调用多次。FnOnce 可能消耗捕获的变量，至少能调用一次。三者是包含关系：Fn 包含于 FnMut 包含于 FnOnce。

第四，当 closure 的生命周期比创建它的作用域更长时，必须用 move 获取所有权。这在返回 closure 和跨线程传递 closure 时尤其重要。

下一章我们讲并发。你会看到 move closure 如何和 Rust 的线程模型配合，让编译器在编译期就阻止数据竞争。
