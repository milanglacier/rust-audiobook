---
title: 第六章 错误处理：没有异常的世界
---

# 第六章 错误处理：没有异常的世界

你写了一个程序，打开一个文件，读取里面的内容。文件不存在。在 Python 里，程序会抛出一个异常；在 Java 里，你得写 try-catch。但在 Rust 里，根本没有异常这个东西。打开文件的函数会返回一个 Result，里面要么是文件内容，要么是一个错误。你必须亲手决定怎么处理这个错误，编译器不会让你假装什么都没发生。

这一章讲三件事：第一，Rust 把错误分成两类，panic 和 Result，分别对应不可恢复和可恢复的错误。第二，Result 怎么用，从最原始的 match 到最简洁的问号运算符。第三，怎么设计自己的错误类型，让错误信息既清晰又方便调用者处理。

## 两种错误：panic 和 Result

我们先区分两个概念。Rust 里的错误分两类：不可恢复的，和可恢复的。

不可恢复的错误用 panic 表示。当程序遇到了一个绝对不应该发生的情况，比如数组越界，程序会立刻停下来，打印一条错误信息，然后退出。你可以手动调用 panic 宏来触发这种行为。

```rust
fn main() {
    panic!("something went terribly wrong");
}
```

panic 的意思是：这个错误说明程序本身有 bug，继续运行下去没有意义。

可恢复的错误用 Result 表示。文件不存在、网络超时、用户输入了非法字符——这些都是正常运行中可能遇到的情况。程序应该有能力处理这些错误，而不是直接崩溃。

Result 是一个 enum，只有两个变体：Ok 包着成功的值，Err 包着错误的值。上一章我们已经见过 enum 了，Result 没有任何魔法，就是一个普通的 enum。

```rust
enum Result<T, E> {
    Ok(T),
    Err(E),
}
```

所以记住：panic 是给 bug 用的，Result 是给正常错误用的。如果你不确定该用哪个，问自己一个问题：调用者有没有可能合理地处理这个错误？如果有，用 Result。

## 用 match 处理 Result

最直接的方式是用 match。打开一个文件会返回 Result，成功时是一个 File，失败时是一个 io Error。我们用 match 把两种情况分开处理。

```rust
use std::fs::File;

fn main() {
    let file = File::open("hello.txt");
    match file {
        Ok(f) => println!("file opened: {:?}", f),
        Err(e) => println!("failed to open: {e}"),
    }
}
```

这段代码很清晰，但也很啰嗦。如果你有三个可能出错的操作连在一起，每个都用 match，代码就会变成一层套一层的缩进地狱。Rust 提供了几个快捷方式来解决这个问题。

## unwrap 和 expect：快速但危险

第一个快捷方式是 unwrap。调用 unwrap 的意思是：如果 Result 是 Ok，把里面的值取出来；如果是 Err，直接 panic。

```rust
let file = File::open("hello.txt").unwrap();
```

这行代码很短，但很危险。文件不存在的时候，程序会直接崩溃。unwrap 适合两种场景：第一，你写的是原型代码，还不想处理错误。第二，你比编译器更清楚这个操作不会失败，比如你刚刚手动检查过文件存在。

expect 和 unwrap 几乎一样，区别是你可以指定 panic 时的错误信息。在正式代码里，如果你确实需要在错误时 panic，用 expect 比 unwrap 好，因为错误信息能帮你定位问题。

```rust
let file = File::open("config.toml")
    .expect("config.toml should exist in the project root");
```

但是，大多数时候你不想 panic，你想把错误传给调用者，让调用者决定怎么处理。这就是问号运算符登场的时候了。

## 问号运算符：优雅地传播错误

问号运算符是 Rust 错误处理的核心工具。在一个返回 Result 的表达式后面加一个问号，意思是：如果结果是 Ok，把值取出来继续往下走；如果结果是 Err，立刻从当前函数返回这个 Err。

我们来看一个具体的例子。这个函数读取一个文件的内容，返回一个 Result，成功时是 String，失败时是 io Error。

```rust
use std::fs;
use std::io;

fn read_file(path: &str) -> Result<String, io::Error> {
    let content = fs::read_to_string(path)?;
    Ok(content)
}
```

注意 {{`read_to_string`||read to string}} 后面那个问号。如果读取成功，content 就是文件内容的 String。如果读取失败，函数会立刻返回那个 Err，调用者会收到错误信息。

问号运算符的本质就是一个 match 的语法糖。刚才那一行，展开来写是这样的：

```rust
let content = match fs::read_to_string(path) {
    Ok(s) => s,
    Err(e) => return Err(e),
};
```

问号运算符做的事情完全一样，只是用一个字符代替了四行代码。

这里的关键是：问号运算符只能在返回 Result 的函数里使用。因为它的 Err 分支是一个 return 语句，所以函数的返回类型必须是 Result。如果你在 main 函数里想用问号运算符，需要把 main 的返回类型改成 Result。

```rust
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let content = fs::read_to_string("hello.txt")?;
    println!("{content}");
    Ok(())
}
```

问号运算符真正强大的地方在于它可以链式使用。假设你需要先打开文件，再读取内容，再解析成数字，每一步都可能出错。没有问号运算符，你需要三层 match。有了问号运算符，代码是平铺直叙的。

```rust
fn read_number(path: &str) -> Result<i32, Box<dyn std::error::Error>> {
    let content = fs::read_to_string(path)?;
    let number = content.trim().parse::<i32>()?;
    Ok(number)
}
```

两个问号，两次可能的提前返回，但代码读起来就像没有错误处理一样干净。

## 自定义错误类型

刚才我们用了 {{`Box<dyn std::error::Error>`||Box dyn Error}} 作为错误类型。这个写法很方便，因为几乎所有的错误类型都实现了 Error trait，都能装进这个 Box 里。但在正式项目里，你通常想定义自己的错误类型，这样调用者可以用 match 区分不同的错误。

我们来看一个例子。假设你写了一个配置文件解析器，可能遇到两种错误：文件读不到，或者文件内容格式不对。你可以用一个 enum 来表示这两种情况。

```rust
use std::io;

enum ConfigError {
    IoError(io::Error),
    ParseError(String),
}
```

然后你要给这个 enum 实现 From trait。From trait 让一种类型可以自动转换成另一种类型。这里的关键是，问号运算符在返回 Err 的时候，会自动调用 From 来做类型转换。

```rust
impl From<io::Error> for ConfigError {
    fn from(e: io::Error) -> Self {
        ConfigError::IoError(e)
    }
}
```

有了这个 From 的实现，当你在一个返回 Result 加 ConfigError 的函数里，对一个返回 io Error 的操作使用问号运算符，Rust 会自动把 io Error 转换成 ConfigError。你不需要手动写转换代码。

```rust
fn load_config(path: &str) -> Result<Config, ConfigError> {
    let content = fs::read_to_string(path)?;  // io::Error → ConfigError
    let config = parse_config(&content)?;       // ParseError stays as-is
    Ok(config)
}
```

换句话说，问号运算符做了两件事：检查 Result 是不是 Err，如果是，用 From 把错误转换成函数返回类型要求的错误类型，然后提前返回。

在实际项目中，你可能不想手写每一个 From 的实现。社区里有一个非常流行的 crate 叫 thiserror，它用一个宏帮你自动生成 From 的实现和错误信息的格式化。但底层的原理就是我们刚才讲的：enum 加 From trait 加问号运算符。

## Option 和问号运算符

值得一提的是，问号运算符不只能用在 Result 上，也能用在 Option 上。如果一个表达式的类型是 Option，加上问号的意思是：如果是 Some，取出里面的值；如果是 None，立刻返回 None。

```rust
fn first_line(text: &str) -> Option<&str> {
    let line = text.lines().next()?;
    Some(line)
}
```

但注意，Result 的问号和 Option 的问号不能混用。一个返回 Result 的函数里不能对 Option 用问号，反过来也一样。如果你确实需要在 Result 的函数里处理 Option，可以用 ok_or 方法把 Option 转换成 Result。

```rust
fn first_number(text: &str) -> Result<i32, String> {
    let line = text.lines().next().ok_or("empty text")?;
    let n = line.parse::<i32>().map_err(|e| e.to_string())?;
    Ok(n)
}
```

## 回顾

我们来总结这一章的核心内容。

第一，Rust 没有异常，把错误分成两类。不可恢复的用 panic，说明程序有 bug。可恢复的用 Result，调用者可以选择怎么处理。

第二，处理 Result 有几种方式。match 最明确但最啰嗦。unwrap 和 expect 在 Err 时会 panic，适合原型代码或者你确定不会出错的场景。问号运算符是最常用的，它在 Err 时自动提前返回，让代码像没有错误处理一样干净。

第三，自定义错误类型用 enum 来定义，给 enum 实现 From trait，问号运算符就会自动做类型转换。这个模式是 Rust 错误处理的标准做法。

下一章我们讲 trait，也就是 Rust 的行为契约。这一章里已经出现了好几个 trait，比如 From 和 Error。下一章我们系统地讲清楚 trait 是什么、怎么定义、怎么使用。
