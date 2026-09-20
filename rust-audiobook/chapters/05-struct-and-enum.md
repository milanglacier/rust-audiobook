---
title: 第五章 Struct 与 Enum：用类型说话
---

# 第五章 Struct 与 Enum：用类型说话

你在写一个程序，需要表示一个用户：有名字、有邮箱、有年龄。在 Python 里你可能用一个字典，在 Java 里你会写一个 class。在 Rust 里，你用 struct。但 Rust 的类型系统不止于此。当你需要表示"一个值可能是这种，也可能是那种"的时候，Rust 提供了 enum。enum 不只是一组标签，它的每个变体可以携带完全不同的数据。配合模式匹配，编译器会强制你处理每一种可能性。

这一章讲四件事：struct 怎么定义和使用，enum 怎么携带数据，match 为什么要求你穷尽所有分支，以及 Option 和 Result 为什么只是普通的 enum。

## Struct：把相关的数据绑在一起

struct 最常见的形式是命名字段 struct。你给每个字段一个名字和类型，然后用大括号创建实例。

我们来定义一个表示用户的 struct。它有四个字段：username 是 String 类型，email 也是 String，age 是 u32，active 是 bool。

```rust
struct User {
    username: String,
    email: String,
    age: u32,
    active: bool,
}

fn main() {
    let user = User {
        username: String::from("alice"),
        email: String::from("alice@example.com"),
        age: 30,
        active: true,
    };
    println!("{} is {} years old", user.username, user.age);
}
```

创建实例的时候，每个字段都要赋值，顺序无所谓，但不能漏掉任何一个。如果你想修改字段的值，整个变量必须声明为 mut。Rust 不允许单个字段可变而其他字段不可变。

除了命名字段 struct，Rust 还有两种不太常见的形式。第一种是元组 struct，字段没有名字，只有类型。适合用来给一个基本类型加上语义。

```rust
struct Meters(f64);
struct Seconds(f64);
```

这两个 struct 底层都是 f64，但类型不同。你不能把 Meters 传给一个期望 Seconds 的函数，编译器会拒绝。这就是用类型来防止犯错。

第二种是单元 struct，既没有字段也没有数据。它看起来没什么用，但在实现 trait 的时候会用到。我们后面会遇到。

```rust
struct AlwaysEqual;
```

## 给 struct 加方法

光有数据还不够，你还想给 struct 加上行为。在 Rust 里，方法写在 impl 块里面。

我们给刚才的 User 加一个方法，判断这个用户是不是活跃的。方法的第一个参数是 &self，表示对自身的不可变引用。

```rust
impl User {
    fn is_active(&self) -> bool {
        self.active
    }

    fn deactivate(&mut self) {
        self.active = false;
    }
}
```

注意 {{`deactivate`||deactivate}} 的参数是 &mut self，因为它需要修改 struct 的字段。这和上一章讲的借用规则完全一致：读取用 &self，修改用 &mut self。

你还可以在 impl 块里定义关联函数，也就是不以 self 作为参数的函数。最常见的关联函数就是 new，用来创建实例。调用关联函数用双冒号语法。

```rust
impl User {
    fn new(username: String, email: String, age: u32) -> User {
        User {
            username,
            email,
            age,
            active: true,
        }
    }
}

let user = User::new(
    String::from("alice"),
    String::from("alice@example.com"),
    30,
);
```

你在标准库里见过的 {{`String::from`||String from}} 就是一个关联函数。现在你知道它的来历了。

## Enum：一个值，多种可能

struct 让你把多个字段绑在一起。enum 解决的是另一个问题：一个值在不同时刻可能是完全不同的东西。

最简单的 enum 就是一组标签，和 C 或 Java 的 enum 类似。

```rust
enum Direction {
    Up,
    Down,
    Left,
    Right,
}
```

但 Rust 的 enum 远不止于此。每个变体可以携带不同类型的数据。这让 enum 变成了一个非常强大的建模工具。

假设你在写一个聊天程序，消息有好几种类型：纯文本消息有一段文字，退出消息什么都没有，移动消息带两个坐标，颜色变更消息带三个数字。你可以用一个 enum 把这些全部表达出来。

```rust
enum Message {
    Quit,
    Echo(String),
    Move { x: i32, y: i32 },
    ChangeColor(i32, i32, i32),
}
```

看看这四个变体：Quit 不携带数据，就像单元 struct。Echo 携带一个 String，像元组 struct。Move 携带命名字段，像普通 struct。ChangeColor 携带三个 i32。一个 enum 把四种完全不同的数据形状装在了一起。

你也可以给 enum 加方法，语法和 struct 一样。

```rust
impl Message {
    fn call(&self) {
        // 根据变体做不同的事
    }
}

let msg = Message::Echo(String::from("hello"));
msg.call();
```

所以记住：struct 是"这些字段全都有"，enum 是"这些可能性里选一个"。两者配合使用，你就能精确地描述程序中数据的形状。

## Match：穷尽的模式匹配

有了 enum 之后，你需要一种方式来处理每种变体。Rust 的 match 表达式就是为此而生的。

match 的规则很简单：你给出每个变体对应的代码，编译器保证你没有漏掉任何一个。

```rust
fn process(msg: Message) {
    match msg {
        Message::Quit => println!("quit"),
        Message::Echo(text) => println!("echo: {text}"),
        Message::Move { x, y } => println!("move to ({x}, {y})"),
        Message::ChangeColor(r, g, b) => println!("color: {r},{g},{b}"),
    }
}
```

注意每个分支是怎么把变体里的数据"解开"的。Echo 分支把里面的 String 绑定到变量 text，Move 分支把 x 和 y 分别绑定。这叫做解构，英文叫 destructuring。模式匹配不只是检查"是哪个变体"，还同时把数据取出来。

这里最重要的特性是穷尽检查。如果你漏掉了一个变体，比如忘了处理 ChangeColor，编译器会直接报错：non-exhaustive patterns。这意味着你不可能悄悄忘记处理某种情况。编译器在编译期就帮你查漏补缺了。

如果你确实有一些变体不需要特殊处理，可以用下划线作为兜底分支。

```rust
match msg {
    Message::Quit => println!("quit"),
    _ => println!("other message"),
}
```

下划线匹配所有剩余的情况。这样既满足了穷尽检查的要求，又不需要给每个变体写代码。

match 还可以用在不是 enum 的值上。数字、字符串、元组都可以 match。但 enum 加 match 是最经典的组合，你在 Rust 代码里会到处看到。

## Option：没有 null 的世界

现在我们来看 Rust 里最重要的 enum 之一：Option。

很多语言有 null 这个概念。一个变量可能有值，也可能是 null。问题是，null 总是悄悄出现。你以为一个变量有值，直接拿来用，结果运行时才发现它是 null，程序就崩了。这就是著名的 null pointer exception。

Rust 的解决方案很简单：完全没有 null。如果一个值可能不存在，你必须用 Option 来表达。Option 就是一个普通的 enum，定义在标准库里。

```rust
enum Option<T> {
    Some(T),
    None,
}
```

这里的 T 是一个泛型参数，英文叫 generic，意思是 Some 里面可以装任何类型的值。Option 加 i32 表示"可能有一个 i32，也可能没有"。Option 加 String 表示"可能有一个 String，也可能没有"。

使用 Option 的时候，你必须显式地处理 None 的情况。编译器不会让你直接把 Option 当成里面的值来用。

```rust
let x: Option<i32> = Some(5);
let y: Option<i32> = None;

match x {
    Some(n) => println!("got {n}"),
    None => println!("nothing"),
}
```

你不能直接写 x + 1，因为 x 不是 i32，它是 Option 加 i32。你必须先用 match 或者其他方法把 i32 取出来。这就是 Rust 的设计哲学：把"这个值可能不存在"这件事编码到类型系统里，让编译器强制你处理。

Option 因为太常用了，Rust 允许你直接写 Some 和 None，不需要写 Option 加双冒号加 Some。这是一个特殊待遇，其他 enum 的变体还是需要加前缀的。

## if let：只关心一种情况

有时候你只关心 Option 是 Some 的情况，不关心 None。用 match 就显得啰嗦了，因为你还得写一个下划线分支什么都不做。Rust 提供了 if let 语法来简化这种场景。

```rust
let value: Option<i32> = Some(42);

if let Some(n) = value {
    println!("got {n}");
}
```

if let 做的事情和 match 完全一样，只是省掉了你不关心的分支。你也可以加一个 else 来处理其他情况。

```rust
if let Some(n) = value {
    println!("got {n}");
} else {
    println!("nothing");
}
```

这在处理 Option 和 Result 的时候特别好用。你会在 Rust 代码里频繁看到 if let。

## 回顾

我们来回顾这一章的要点。

第一，struct 把相关的数据绑在一起。有三种形式：命名字段、元组、单元。方法写在 impl 块里，用 &self 读取，用 &mut self 修改。

第二，enum 表示"多种可能性里选一个"，每个变体可以携带不同类型的数据。这让 enum 远比其他语言的枚举强大。

第三，match 是处理 enum 的核心工具，编译器要求你穷尽所有分支，漏一个都不行。这叫穷尽检查，它在编译期就帮你消除遗漏。

第四，Option 和 Result 就是普通的 enum，没有任何编译器魔法。Option 用 Some 和 None 取代了 null，让"值可能不存在"这件事变成了类型系统的一部分。

下一章我们讲错误处理。你已经见过 Result 的定义了——它和 Option 一样是一个 enum，只是用来表达"操作可能成功也可能失败"。下一章会告诉你怎么用 Result 优雅地处理错误，以及问号运算符如何让错误处理代码变得干净利落。
