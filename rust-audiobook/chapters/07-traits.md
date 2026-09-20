---
title: 第七章 Trait：共享行为的契约
---

# 第七章 Trait：共享行为的契约

假设你写了一个函数，需要把任意类型格式化成一段摘要文字。在 Python 里你可能随手写个 if-elif 判断类型，在 Java 里你会定义一个接口。Rust 的做法叫 trait。但 trait 比接口更灵活——你甚至可以给标准库的类型、给别人写的 struct 加上新的行为。这一章我们就来搞清楚 trait 是什么、怎么用、以及为什么 Rust 的整个生态都建立在 trait 之上。

这一章讲四件事：第一，怎么定义一个 trait，怎么给类型实现 trait。第二，怎么用 trait bound 约束泛型参数。第三，impl Trait 语法在参数和返回值位置分别意味着什么。第四，标准库里有哪些 trait 你会天天用到。

## 定义 trait 和实现 trait

我们从一个具体的例子开始。假设你有两种内容类型：新闻文章和推文。它们的字段完全不同，但你希望它们都能生成一段摘要。在 Rust 里，你用 trait 来表达这个共同的能力。

trait 的定义很简单：给出 trait 的名字，列出它要求的方法签名。我们定义一个叫 Summary 的 trait，里面有一个方法 summarize，接收对自身的不可变引用，返回一个 String。

```rust
trait Summary {
    fn summarize(&self) -> String;
}
```

定义好之后，我们分别为两个 struct 实现这个 trait。语法是 impl 加 trait 的名字，再加 for 加类型的名字。每个实现必须提供 trait 里声明的所有方法。

```rust
struct NewsArticle {
    title: String,
    author: String,
    content: String,
}

impl Summary for NewsArticle {
    fn summarize(&self) -> String {
        format!("{}, by {}", self.title, self.author)
    }
}

struct Tweet {
    username: String,
    content: String,
}

impl Summary for Tweet {
    fn summarize(&self) -> String {
        format!("@{}: {}", self.username, self.content)
    }
}
```

注意，NewsArticle 和 Tweet 是两个完全不同的 struct，但它们现在都有了 summarize 这个方法。这就是 trait 的核心作用：定义一组行为的契约，让不同的类型各自实现。

trait 还可以提供默认实现。如果你在 trait 定义里写了方法体，那么具体类型可以选择用默认版本，也可以覆盖掉。这比 Java 的接口默认方法更早出现，用法也更自然。

这里有一点很重要。在 Rust 里，你可以给任何类型实现 trait，包括你自己没定义的类型。比如你可以给 i32 实现 Summary。但有一个限制，叫做孤儿规则，英文叫 orphan rule：trait 和类型至少有一个必须是你自己的 crate 定义的。换句话说，你不能给别人的类型实现别人的 trait。这条规则防止了两个 crate 对同一个类型提供互相矛盾的实现。

## 泛型与 trait bound

光能实现 trait 还不够，真正的力量在于把 trait 用在泛型里。假设你想写一个函数，接收任何实现了 Summary 的类型，然后打印它的摘要。你不需要关心传进来的到底是 NewsArticle 还是 Tweet，只要求传进来的东西有 summarize 方法。

这就是 trait bound，中文可以叫 trait 约束。写法是在泛型参数后面加冒号，再写上 trait 的名字。

```rust
fn notify<T: Summary>(item: &T) {
    println!("Breaking: {}", item.summarize());
}
```

这个函数说的是：T 可以是任何类型，但必须实现了 Summary。如果你传一个没有实现 Summary 的类型进来，编译器会立刻报错，而且错误信息会明确告诉你缺少哪个 trait 的实现。

当 trait bound 变多的时候，函数签名会变长。Rust 提供了 where 子句来让签名更清晰。

```rust
fn complex_function<T, U>(t: &T, u: &U) -> String
where
    T: Summary + Clone,
    U: Summary + Debug,
{
    format!("{} and {:?}", t.summarize(), u)
}
```

这里的加号表示同时要求多个 trait。T 必须既实现了 Summary 又实现了 Clone。这种组合在实际代码里非常常见。

所以记住：泛型让你写出通用的代码，trait bound 让编译器保证这些通用代码只会在满足条件的类型上运行。这就是 Rust 实现多态的方式——不是运行时去查方法表，而是编译期就确定了调用哪个实现。

## impl Trait 语法

刚才的 trait bound 写法虽然精确，但有时候显得啰嗦。Rust 提供了一个更简洁的写法：impl Trait。

在参数位置，impl Trait 等价于一个匿名的 trait bound。

```rust
fn notify(item: &impl Summary) {
    println!("Breaking: {}", item.summarize());
}
```

这个函数和刚才的泛型版本功能完全一样。编译器看到 impl Summary，就知道参数的类型必须实现了 Summary。对于简单的情况，这种写法更好读。

但在返回值位置，impl Trait 的含义不太一样。返回 impl Trait 意味着：这个函数返回某个实现了这个 trait 的类型，但调用者不知道具体是哪个类型。

```rust
fn make_summary() -> impl Summary {
    Tweet {
        username: String::from("rustlang"),
        content: String::from("Rust 2024 is here!"),
    }
}
```

这里的关键是，函数内部确定了返回的是 Tweet，但外部只知道返回的东西有 summarize 方法。这在返回 closure 或者迭代器的时候特别有用，因为这些类型的名字要么写不出来，要么写出来会非常长。

注意一个限制：返回 impl Trait 的函数不能在不同分支返回不同的具体类型。你不能在 if 里返回 Tweet，else 里返回 NewsArticle，即使它们都实现了 Summary。这是因为编译器需要在编译期确定返回值的大小。如果你确实需要返回不同的类型，后面讲智能指针的时候会介绍 trait object 的方式。

## 标准库里的常用 trait

Rust 标准库定义了大量 trait，其中有几个你几乎每天都会用到。我们来快速过一遍最重要的几个。

首先是 Display 和 Debug。Display 决定了一个类型怎么被格式化给用户看，就是你在 println 里用大括号的时候调用的那个 trait。Debug 则是给程序员看的调试输出，用大括号加冒号加问号来调用。大多数时候，Debug 可以用 derive 自动生成，而 Display 需要手写。

```rust
use std::fmt;

#[derive(Debug)]
struct Point {
    x: f64,
    y: f64,
}

impl fmt::Display for Point {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "({}, {})", self.x, self.y)
    }
}
```

说到 derive，这是 Rust 里一个非常方便的机制。你在 struct 或者 enum 上面加一个 derive 属性，编译器就自动帮你实现指定的 trait。常用的可以 derive 的 trait 有 Debug、Clone、Copy、PartialEq、Hash 等等。

然后是 Clone 和 Copy。我们在所有权那一章讲过，Clone 提供显式的深拷贝，Copy 让赋值变成隐式的按位复制。Copy 是 Clone 的子 trait，也就是说实现 Copy 的类型必须先实现 Clone。

接下来是 From 和 Into。上一章我们在错误处理里已经见过 From：它定义了类型之间的转换。当你为类型 A 实现了从类型 B 的 From，你就自动获得了 B 到 A 的 Into。问号运算符能自动转换错误类型，靠的就是 From。

最后是 Iterator。这个 trait 只要求你实现一个 next 方法，返回 Option。下一章我们会专门来讲迭代器，但现在你需要知道的是：Iterator 是一个 trait，所有迭代器的方法——map、filter、collect——都是这个 trait 提供的默认方法。这就是 trait 的威力：定义一个核心方法，免费获得几十个衍生方法。

## 回顾

我们来回顾这一章的要点。trait 是 Rust 定义共享行为的方式，你写出方法签名，让不同的类型各自提供实现。trait bound 让泛型代码在编译期就确保类型满足要求。impl Trait 语法让参数和返回值的写法更简洁。标准库的 Display、Debug、Clone、From、Iterator 这些 trait 构成了 Rust 生态的基石。

下一章我们讲迭代器。你会看到 Iterator 这个 trait 如何撑起 Rust 里最优雅的数据处理模式——零成本的链式调用。
