---
title: 第十一章 智能指针：超越引用
---

# 第十一章 智能指针：超越引用

到目前为止，我们一直在用两种方式持有数据：要么直接拥有一个值，要么通过引用借来看看。大多数时候这就够了。但有些时候你会遇到普通引用解决不了的问题。比如你想在堆上分配一个值，或者你希望一份数据同时有两个 owner，又或者你想在只有不可变引用的情况下修改数据。这些场景，就是智能指针存在的理由。

这一章讲四件事：第一，Box 怎么把值放到堆上。第二，Rc 和 Arc 怎么让一个值有多个 owner。第三，RefCell 怎么把借用检查推迟到运行时。第四，智能指针背后的两个 trait，Deref 和 Drop。

## Box：最简单的智能指针

我们从最简单的开始。Box 做的事情很纯粹：在堆上分配一块内存，把值放进去，然后给你一个指向堆上数据的指针。Box 本身在栈上，它拥有堆上那个值的所有权。当 Box 离开作用域时，堆上的值也跟着被释放。

什么时候需要 Box？最常见的场景是递归类型。假设你要定义一个链表。链表的每个节点包含一个值和指向下一个节点的指针。你很自然地写出这样的 enum。

```rust
// 编译不过
enum List {
    Cons(i32, List),
    Nil,
}
```

编译器会拒绝，说 recursive type has infinite size。原因是编译器需要在编译期知道每个类型占多少字节。List 里面包含 List，List 里面又包含 List，无穷无尽，编译器算不出大小。

解决方法是用 Box 加一层间接。Box 本身的大小是固定的，就是一个指针的大小。编译器不需要知道堆上的数据有多大，只需要知道指针有多大。

```rust
enum List {
    Cons(i32, Box<List>),
    Nil,
}

let list = List::Cons(1,
    Box::new(List::Cons(2,
        Box::new(List::Cons(3,
            Box::new(List::Nil))))));
```

Box 还有一个常见的用途：创建 trait object。当你想让一个集合里存放不同类型的值，只要求它们都实现了某个 trait，就可以用 {{`Box<dyn Trait>`||Box dyn Trait}}。这一点我们在 trait 那一章提到过，这里不展开了。

所以记住：Box 是最简单的智能指针，它的唯一作用就是在堆上分配内存。当你需要固定大小的间接访问时，用 Box。

## Rc：单线程的多所有者

所有权的规则是每个值只有一个 owner。但有时候，一个值确实需要被多个部分共享。比如一个图数据结构里，多个边可能指向同一个节点。你不想为每条边复制一份节点数据，也不想用引用来搞一堆生命周期标注。

Rc 就是为这种场景设计的。Rc 是 reference counting 的缩写，意思是引用计数。每次你 clone 一个 Rc，引用计数加一。每次一个 Rc 离开作用域，引用计数减一。当计数变成零的时候，值被释放。

```rust
use std::rc::Rc;

let a = Rc::new(String::from("hello"));
let b = Rc::clone(&a);
let c = Rc::clone(&a);
println!("count: {}", Rc::strong_count(&a)); // 3
```

注意这里我们用的是 {{`Rc::clone`||Rc clone}} 而不是普通的 clone。虽然写法上你也可以用 a.clone()，但社区习惯用 Rc clone 来强调这里只是增加引用计数，不是深拷贝。Rc clone 的开销非常小，就是给计数器加一。

Rc 有一个重要的限制：它只能用于单线程。如果你试图把 Rc 发送到另一个线程，编译器会拒绝。原因是 Rc 的引用计数不是原子操作，在多线程环境下会出现数据竞争。

如果需要跨线程共享数据，用 Arc。Arc 是 atomic reference counting 的缩写，它的引用计数用原子操作来更新，所以是线程安全的。我们在并发那一章已经见过 Arc 和 Mutex 配合使用的例子。

```rust
use std::sync::Arc;
use std::thread;

let data = Arc::new(vec![1, 2, 3]);
let data_clone = Arc::clone(&data);

thread::spawn(move || {
    println!("{:?}", data_clone);
});
```

还有一点：Rc 和 Arc 只提供不可变访问。你不能通过 Rc 修改里面的值。如果你需要多个 owner 同时还能修改数据，就需要下一节讲的 RefCell。

所以记住：Rc 让单线程里的多个部分共享同一个值，Arc 是它的线程安全版本。两者都通过引用计数来管理所有权，都只提供不可变访问。

## RefCell 和内部可变性

正常情况下，Rust 的借用规则在编译期执行。你要么有多个不可变引用，要么有一个可变引用。但有时候你确实需要在只有不可变引用的情况下修改数据。RefCell 就是做这件事的。

RefCell 把借用检查从编译期推迟到运行时。你可以在 RefCell 上调用 borrow 拿到一个不可变引用，或者调用 borrow_mut 拿到一个可变引用。借用规则还是那些规则——同一时刻不能同时有可变和不可变引用——但违反规则的后果从编译错误变成了运行时 panic。

```rust
use std::cell::RefCell;

let data = RefCell::new(5);

{
    let mut v = data.borrow_mut();
    *v += 1;
}

println!("{}", data.borrow()); // 6
```

注意 borrow_mut 拿到的是一个特殊的智能指针类型，叫 RefMut。当 RefMut 离开作用域时，借用自动释放。这就是为什么我们用了一个大括号把可变借用包起来——确保可变引用在不可变引用 borrow 之前被释放。

如果你违反了规则，比如同时持有两个可变引用，程序不会编译失败，而是在运行时 panic。这比编译期检查更危险，所以 RefCell 应该谨慎使用。

RefCell 最常见的用法是和 Rc 配合。Rc 给你多个 owner，但只有不可变访问。RefCell 给你内部可变性。两者结合，{{`Rc<RefCell<T>>`||Rc RefCell T}} 就让多个 owner 都能修改同一个值。

```rust
use std::cell::RefCell;
use std::rc::Rc;

let shared = Rc::new(RefCell::new(vec![1, 2, 3]));

let a = Rc::clone(&shared);
let b = Rc::clone(&shared);

a.borrow_mut().push(4);
b.borrow_mut().push(5);

println!("{:?}", shared.borrow()); // [1, 2, 3, 4, 5]
```

a 和 b 都是 shared 的 clone，它们共享同一份 Vec。通过 borrow_mut，它们都能修改这个 Vec。这在编译期的所有权系统里是不可能的，但 RefCell 让它在运行时成为可能，代价是你要自己保证不会同时持有两个可变引用。

所以记住：RefCell 把借用检查推迟到运行时。它通常和 Rc 配合使用，提供"多 owner 加可变访问"的能力。但运行时 panic 的风险意味着你应该只在真正需要的时候用它。

## Deref 和 Drop：智能指针的幕后机制

到这里你可能会问：Box、Rc、RefCell 为什么叫"智能"指针？它们和普通引用有什么本质区别？答案在两个 trait 里：Deref 和 Drop。

Deref trait 让一个类型表现得像引用一样。当你在 Box 上调用方法时，Rust 会自动"解引用"到里面的值。这就是为什么 Box 用起来几乎和直接持有值一模一样。

```rust
let boxed = Box::new(String::from("hello"));
println!("{}", boxed.len()); // 直接调用 String 的方法
```

你没有写 {{`(*boxed).len()`||解引用 boxed 点 len}}，Rust 自动帮你做了。这个自动行为叫做 deref coercion。编译器看到你在 Box String 上调用 len，就自动把 Box 解引用成 String，再把 String 解引用成 str，找到 len 方法。这个链条可以走很多层，全部在编译期完成，零运行时开销。

Drop trait 让你自定义值被释放时的行为。当一个值离开作用域时，Rust 自动调用它的 drop 方法。对于 Box，drop 释放堆上的内存。对于 Rc，drop 把引用计数减一，如果减到零就释放。对于 Mutex 的锁，drop 自动解锁。

```rust
struct CustomPointer {
    data: String,
}

impl Drop for CustomPointer {
    fn drop(&mut self) {
        println!("dropping: {}", self.data);
    }
}

fn main() {
    let a = CustomPointer { data: String::from("first") };
    let b = CustomPointer { data: String::from("second") };
    println!("created");
    // 离开作用域时，b 先被 drop，然后 a
}
```

这就是 Rust 的 RAII 模式，英文全称是 Resource Acquisition Is Initialization。资源在创建时获取，在离开作用域时自动释放。文件句柄关闭、网络连接断开、内存释放——全部通过 Drop trait 自动完成，你不需要手动写清理代码。

所以记住：Deref 让智能指针用起来像普通引用，Drop 让资源在离开作用域时自动释放。这两个 trait 是所有智能指针的基础，也是 Rust 零成本抽象的典型代表。

## 选择哪种指针

最后我们来做一个简单的总结，帮你在实际编码中做选择。

如果你只需要把值放到堆上，或者需要一个固定大小的间接层，用 Box。大多数情况下 Box 就够了。

如果你需要在单线程里让多个部分共享同一个值，用 Rc。如果是多线程，用 Arc。

如果你需要在不可变的上下文里修改数据，用 RefCell。通常和 Rc 配合使用。

如果你不确定该用哪个，先试试最简单的方案——直接持有值，用 clone 复制。clone 的开销在大多数场景下远小于你花在思考指针选择上的时间。只有当 clone 的开销真的成为瓶颈，或者 clone 在语义上不正确的时候，才考虑智能指针。

## 回顾

我们来总结这一章。

第一，Box 把值放到堆上，大小固定，是最简单的智能指针。递归类型和 trait object 是它最常见的用途。

第二，Rc 和 Arc 通过引用计数实现多所有者。Rc 用于单线程，Arc 用于多线程。两者都只提供不可变访问。

第三，RefCell 把借用检查推迟到运行时，提供内部可变性。Rc 加 RefCell 的组合让多个 owner 都能修改数据，但违反规则会在运行时 panic。

第四，Deref 和 Drop 是智能指针背后的机制。Deref 让智能指针像引用一样使用，Drop 让资源自动释放。

下一章是这本书的最后一章。我们会把目光从语言本身移开，看看 Rust 的工具链和生态——Cargo 怎么管理项目，社区有哪些值得了解的 crate，以及从这本书出发你应该往哪里走。
