---
title: 第二章 所有权：每个值只有一个主人
---

# 第二章 所有权：每个值只有一个主人

上一章我们说，Rust 用所有权系统在编译期保证内存安全。听起来很厉害，但具体的规则是什么？我们从一个简单的场景开始。

你创建了一个 String，把它赋值给另一个变量。然后你想用原来的变量打印这个字符串。在 Python 或者 Java 里，这完全没有问题。但在 Rust 里，编译器拒绝了。这就是 move。

```rust
fn main() {
    let s1 = String::from("hello");
    let s2 = s1;
    println!("{s1}"); // 编译错误：value used after move
}
```

为什么会这样？因为 Rust 的每个值有且只有一个 owner。s1 把值交给了 s2，s1 就不再是 owner 了。这一章我们讲四件事：所有权的三条规则是什么，move 是怎么回事，Copy 类型和普通类型有什么区别，以及 clone 和 move 各自适合什么场景。

## 所有权的三条规则

Rust 的所有权系统建立在三条简单的规则上。这三条规则是整个语言的地基，后面几章讲的借用、生命周期，都是在这个地基上展开的。

第一条：Rust 中的每一个值都有一个变量，叫做这个值的 owner。

第二条：在任何时刻，一个值只能有一个 owner。

第三条：当 owner 离开作用域，英文叫 scope，值会被自动释放。

这三条规则合在一起，构成了 Rust 的内存管理方式。不需要手动 free，不需要垃圾回收器。值跟着 owner 走，owner 没了，值就没了。

来看一个最基本的例子。在一个大括号包围的作用域里创建一个 String，作用域结束时，String 自动被释放。

```rust
{
    let s = String::from("hello");
    // 可以使用 s
} // s 离开作用域，String 的内存被释放
```

这个自动释放的行为有一个正式的名字，叫做 RAII，全称 Resource Acquisition Is Initialization。C++ 也有 RAII，但 C++ 不会阻止你在释放之后继续使用指针。Rust 的所有权规则保证了：一旦 owner 消失，任何试图访问这个值的代码都会被编译器拦住。

## Move：所有权的转移

理解了三条规则之后，我们来看 move 是怎么发生的。

在开头的例子里，我们写了 let s2 等于 s1。在 Python 里，这意味着 s2 和 s1 都指向同一块数据，两个变量都能用。但在 Rust 里，这行代码的意思是：s1 的所有权被转移给了 s2，s1 从此失效。

为什么 Rust 要这样设计？我们需要理解 String 在内存里是怎么存储的。一个 String 实际上由两部分组成：一个在栈上的结构体，包含指向堆内存的指针、长度和容量；以及堆上的实际字符数据。

当你写 let s2 等于 s1 的时候，Rust 复制了栈上的那个结构体——指针、长度和容量。但堆上的数据没有被复制。现在 s1 和 s2 的指针指向同一块堆内存。

如果两个变量都有效，当它们各自离开作用域时，同一块堆内存就会被释放两次。这就是双重释放，我们上一章讲过的内存安全 bug。Rust 的解决方案是：把 s1 标记为无效。这样只有 s2 会在离开作用域时释放内存，不会有双重释放的问题。

这就是 move 的本质：栈上的数据被复制了，但所有权从旧变量转移到了新变量，旧变量失效。整个过程没有堆内存的复制，非常高效。

函数调用也会发生 move。当你把一个值传给函数，所有权就转移到了函数参数上。函数执行结束，参数离开作用域，值被释放。原来的变量在调用之后就不能用了。

```rust
fn takes_ownership(s: String) {
    println!("{s}");
} // s 离开作用域，String 被释放

fn main() {
    let s = String::from("hello");
    takes_ownership(s);
    // println!("{s}"); // 编译错误：value used after move
}
```

编译器会说：value used after move。s 的所有权已经交给了 takes_ownership 函数，main 里的 s 不再有效。

函数也可以通过返回值把所有权交还给调用者。如果你需要在函数调用之后继续使用这个值，可以让函数把它返回出来。

```rust
fn takes_and_gives_back(s: String) -> String {
    println!("{s}");
    s
}

fn main() {
    let s1 = String::from("hello");
    let s2 = takes_and_gives_back(s1);
    println!("{s2}");
}
```

但是你可以想象，如果每次调用函数都要靠返回值把所有权还回来，代码会变得非常啰嗦。这个问题的解决方案叫借用，我们下一章会讲。

## Copy 类型：不用 move 的简单值

你可能会问：如果所有的赋值都会导致 move，那写 let y 等于 x，其中 x 是一个整数，x 也会失效吗？

答案是不会。整数、浮点数、布尔值、字符这些简单类型在 Rust 里实现了一个叫 Copy 的 trait。Copy 类型的赋值是真正的复制，不是 move。

```rust
fn main() {
    let x = 5;
    let y = x;
    println!("x = {x}, y = {y}"); // 完全没有问题
}
```

x 和 y 都有效。这是因为整数 5 存储在栈上，复制它的成本非常低——就是复制几个字节。不存在堆内存，不存在双重释放的风险，所以 Rust 允许直接复制。

这就是 Copy 类型和非 Copy 类型的根本区别。Copy 类型的值完全在栈上，复制它没有任何额外的成本。非 Copy 类型，比如 String，涉及堆上的数据，直接复制意味着复制整个堆内存，成本可能很高。所以 Rust 对非 Copy 类型默认使用 move，强制你显式决定是否要做一次昂贵的复制。

哪些类型是 Copy 的？有一个简单的判断标准：如果一个类型以及它的所有部分都不需要在离开作用域时做特殊的清理工作，它就可以是 Copy 的。具体来说：所有整数类型、浮点数类型、布尔类型、字符类型，以及只包含 Copy 类型的元组。

```rust
let a: i32 = 42;      // Copy
let b: f64 = 3.14;    // Copy
let c: bool = true;    // Copy
let d: char = 'R';    // Copy
let e: (i32, bool) = (1, true); // Copy，因为 i32 和 bool 都是 Copy

let s: String = String::from("hello"); // 不是 Copy
let v: Vec<i32> = vec![1, 2, 3];      // 不是 Copy
```

String 不是 Copy，Vec 不是 Copy，任何涉及堆分配的类型都不是 Copy。对这些类型，赋值就是 move。

## Clone：我就是想要一份副本

有时候你确实需要复制一个非 Copy 类型的值。比如你有一个 String，你想把它传给一个函数，但之后还想继续使用它。除了等下一章讲的借用之外，还有一个直接的办法：调用 clone。

```rust
fn main() {
    let s1 = String::from("hello");
    let s2 = s1.clone();
    println!("s1 = {s1}, s2 = {s2}");
}
```

这段代码编译通过。clone 做了一次完整的深拷贝：不仅复制了栈上的结构体，还复制了堆上的字符数据。s1 和 s2 各自拥有独立的堆内存，各自是各自那份数据的 owner。

clone 和 move 的区别很重要。move 是零成本的——只复制栈上的几个字节，然后让旧变量失效。clone 是有成本的——它需要分配新的堆内存，复制所有数据。如果你的 String 有一百万个字符，clone 就要复制一百万个字符。

这就是为什么 Rust 不默认 clone。在其他语言里，比如 Python，赋值通常只是复制引用，两个变量指向同一块数据。在 Java 里也类似。这看起来很方便，但代价是你永远不知道有多少个变量指向同一块数据，垃圾回收器需要在运行时追踪所有这些引用。

Rust 的做法是：move 是默认行为，零成本，安全。需要复制的时候，你写一个 clone，清清楚楚地告诉读代码的人和编译器：这里发生了一次可能很昂贵的深拷贝。

一个实用的建议：不要害怕使用 clone。初学 Rust 的时候，如果编译器报错说 value used after move，先试试加一个 clone 让代码跑起来。等你对所有权和借用更熟悉之后，再回来考虑哪些 clone 可以用借用替代。过早优化不如先把代码写对。

## 所有权和函数参数的完整图景

让我们把 move、Copy 和函数调用放在一起看一个完整的例子。

```rust
fn makes_copy(x: i32) {
    println!("{x}");
}

fn takes_ownership(s: String) {
    println!("{s}");
}

fn main() {
    let n = 42;
    makes_copy(n);
    println!("{n}"); // OK：i32 是 Copy 的，n 仍然有效

    let s = String::from("hello");
    takes_ownership(s);
    // println!("{s}"); // 编译错误：String 不是 Copy，s 已经被 move
}
```

调用 makes_copy 的时候，n 的值被复制了一份传给函数。n 还是有效的，因为 i32 是 Copy 的。调用 takes_ownership 的时候，s 的所有权被转移给了函数参数。s 在 main 里就不能用了，因为 String 不是 Copy 的。

这就是 Rust 的规则：传参和赋值的行为取决于类型是不是 Copy。Copy 类型复制，非 Copy 类型 move。没有隐式的深拷贝，没有意外。编译器保证你不会在 move 之后使用一个已经失效的变量。

## 回顾

我们来回顾这一章的核心内容。

第一，所有权有三条规则：每个值有一个 owner，同一时刻只能有一个 owner，owner 离开作用域时值被释放。这三条规则是 Rust 内存管理的全部基础。

第二，赋值和函数传参对非 Copy 类型会发生 move——所有权从旧变量转移到新变量，旧变量失效。move 只复制栈上的数据，是零成本的。

第三，整数、浮点数、布尔值等简单类型实现了 Copy trait，赋值时会自动复制，不会 move。判断标准是：值完全在栈上，不需要堆上的清理工作。

第四，如果你需要对非 Copy 类型做一次真正的深拷贝，使用 clone。clone 是显式的，有成本的，但有时候就是你需要的。

这套规则很安全，但也有一个明显的不便：你想让一个函数读一下某个值，就得把所有权交出去，要么靠返回值拿回来，要么 clone 一份。这太啰嗦了。下一章我们讲 Rust 对这个问题的解决方案——借用，让你在不转移所有权的情况下，安全地访问一个值。
