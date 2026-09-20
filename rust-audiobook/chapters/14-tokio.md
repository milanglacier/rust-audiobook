---
title: 第十四章 Tokio：异步编程实战
---

# 第十四章 Tokio：异步编程实战

上一章我们学了 async 和 await 的原理：Future 是惰性的，.await 驱动它，执行器负责调度。但原理本身不能帮你写出一个真正的异步程序。你需要一个运行时来管理任务调度、提供异步 IO、处理定时器和信号。tokio 就是这个运行时。

Rust 的异步生态绝大多数建立在 tokio 之上。axum、reqwest、tonic、sqlx——这些你在实际项目中会用到的 crate，底层都依赖 tokio。这一章讲四件事：怎么启动 tokio 运行时，怎么用 spawn 创建异步任务，怎么用 select 同时等待多个事件，以及异步编程中常见的陷阱。

## 启动 tokio

tokio 的启动方式有两种。最常见的是用 tokio 的 main 属性宏。

```rust
#[tokio::main]
async fn main() {
    println!("hello from tokio!");
}
```

这个属性宏做的事情等价于：创建一个多线程运行时，然后用 block_on 驱动你的 async main。展开之后是这样的。

```rust
fn main() {
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(async {
        println!("hello from tokio!");
    });
}
```

多线程运行时默认使用和 CPU 核心数一样多的工作线程，每个线程有自己的任务队列，空闲时会从别的线程偷任务来执行。这就是工作窃取调度，英文叫 work-stealing。

如果你只需要一个单线程运行时——比如在写一个简单的脚本——可以用 current_thread flavor。

```rust
#[tokio::main(flavor = "current_thread")]
async fn main() {
    // 只在一个线程上运行
}
```

单线程运行时所有任务都在一个线程上轮流执行，适合不需要利用多核的场景。

在项目的 Cargo.toml 里，tokio 的依赖通常这样写。

```toml
[dependencies]
tokio = { version = "1", features = ["full"] }
```

full feature 包含了 tokio 所有的功能模块。在生产项目中，你可以只启用需要的 feature 来减少编译时间，比如只用 rt 加 macros 加 net。

所以记住：tokio main 宏是启动异步程序的标准方式。多线程运行时用工作窃取调度，适合服务器。单线程运行时适合脚本和简单场景。

## spawn：创建异步任务

在同步代码里，我们用 {{`thread::spawn`||thread spawn}} 创建线程。在异步代码里，对应的操作是 {{`tokio::spawn`||tokio spawn}}。

```rust
#[tokio::main]
async fn main() {
    let handle = tokio::spawn(async {
        "hello from task"
    });

    let result = handle.await.unwrap();
    println!("{result}");
}
```

tokio::spawn 接受一个 Future，把它放进运行时的任务队列。运行时会在合适的时候 poll 它。spawn 返回一个 JoinHandle，对它 .await 可以拿到任务的返回值。

和 thread::spawn 的一个重要区别：tokio::spawn 创建的任务非常轻量。一个线程通常占用几兆字节的栈空间，但一个 tokio 任务只需要几百字节。创建一万个线程可能会耗尽内存，但创建一万个 tokio 任务毫无压力。

我们来看一个更实际的例子：并发地从多个 URL 抓取数据。

```rust
#[tokio::main]
async fn main() {
    let urls = vec![
        "https://example.com/1",
        "https://example.com/2",
        "https://example.com/3",
    ];

    let mut handles = vec![];

    for url in urls {
        let handle = tokio::spawn(async move {
            let resp = reqwest::get(url).await.unwrap();
            resp.text().await.unwrap()
        });
        handles.push(handle);
    }

    for handle in handles {
        let body = handle.await.unwrap();
        println!("收到 {} 字节", body.len());
    }
}
```

每个 URL 的请求是一个独立的任务，它们并发执行。注意 async move：和线程一样，spawn 的 Future 必须拥有它使用的数据的所有权。

tokio::spawn 要求 Future 满足两个条件：Send 加 'static。Send 是因为多线程运行时可能在任意线程上执行任务。'static 是因为 spawn 出去的任务可能活得比创建它的函数更久，不能持有短生命周期的引用。这和 thread::spawn 的要求完全一致。

所以记住：tokio::spawn 是异步世界的 thread::spawn。任务比线程轻量几个数量级，但同样要求 Send 加 'static。

## select!：等待多个事件

在实际的异步程序中，你经常需要同时等待多个事件：一条来自客户端的消息、一个超时信号、一个关闭通知。哪个先到就处理哪个。tokio 的 {{`select!`||select 宏}} 做的就是这件事。

```rust
use tokio::time::{sleep, Duration};

#[tokio::main]
async fn main() {
    let result = tokio::select! {
        val = fetch_data("https://example.com") => {
            format!("收到数据: {val}")
        }
        _ = sleep(Duration::from_secs(5)) => {
            "超时了".to_string()
        }
    };
    println!("{result}");
}
```

select 同时驱动两个 Future：一个网络请求和一个五秒的定时器。哪个先完成，就执行对应的分支，另一个被取消。这就是一个超时模式：请求在五秒内完成就拿到数据，超过五秒就返回超时。

被取消的 Future 会被 drop。它持有的资源会被释放，正在进行的 IO 操作会被中断。Rust 的取消就是 drop——不需要额外的取消 API，这是所有权系统的又一个好处。

select 还有一个常见用法：在循环里持续监听多个事件源。

```rust
use tokio::sync::mpsc;
use tokio::signal;

async fn run(mut rx: mpsc::Receiver<String>) {
    loop {
        tokio::select! {
            Some(msg) = rx.recv() => {
                println!("处理消息: {msg}");
            }
            _ = signal::ctrl_c() => {
                println!("收到关闭信号，退出");
                break;
            }
        }
    }
}
```

这个循环同时等待两件事：channel 里的新消息和 Ctrl-C 信号。收到消息就处理，收到 Ctrl-C 就退出。这种模式在服务端程序里非常常见。

所以记住：select 让你同时等待多个 Future，先完成的先处理，其余的被取消。超时、关闭信号、多路复用，都靠 select。

## 异步 channel 和同步原语

第十章我们学了标准库的 mpsc channel。tokio 提供了异步版本，发送和接收都可以在 .await 点暂停而不阻塞线程。

```rust
use tokio::sync::mpsc;

#[tokio::main]
async fn main() {
    let (tx, mut rx) = mpsc::channel(32);

    tokio::spawn(async move {
        for i in 0..5 {
            tx.send(format!("消息 {i}")).await.unwrap();
        }
    });

    while let Some(msg) = rx.recv().await {
        println!("收到: {msg}");
    }
}
```

注意一个关键区别：标准库的 {{`mpsc::channel`||m p s c channel}} 是无界的，发送者可以无限地往里塞消息。tokio 的 mpsc::channel 需要指定缓冲区大小，这里是 32。当缓冲区满了，send 会暂停等待，直到接收方取走一条消息。这是背压机制——发送方不能无限地生产，必须等接收方跟上节奏。

tokio 还提供了 oneshot channel：一个发送者发一条消息，一个接收者收一条消息。常用于异步函数之间传递一次性结果，比如一个任务算完了把结果发回给请求方。

tokio 也有异步的 Mutex。和标准库的 Mutex 不同，tokio 的 Mutex 在等待锁的时候不会阻塞线程，而是暂停当前任务，让运行时去执行别的任务。

```rust
use std::sync::Arc;
use tokio::sync::Mutex;

#[tokio::main]
async fn main() {
    let data = Arc::new(Mutex::new(vec![]));

    let mut handles = vec![];
    for i in 0..5 {
        let data = Arc::clone(&data);
        handles.push(tokio::spawn(async move {
            let mut lock = data.lock().await;
            lock.push(i);
        }));
    }

    for h in handles { h.await.unwrap(); }
    println!("{:?}", *data.lock().await);
}
```

不过 tokio 的文档有一个建议：如果锁的持有时间很短，而且不跨越 .await 点，标准库的 Mutex 通常更快。tokio 的 Mutex 的优势在于你可以在持有锁的时候 .await。标准库的 Mutex 在异步上下文中如果持有锁的同时 .await，可能会阻塞整个工作线程。

所以记住：tokio 提供了异步版本的 channel 和 Mutex。异步 mpsc 有缓冲区限制，提供背压。选择标准库还是 tokio 的同步原语，取决于你是否需要在持有锁的时候 .await。

## 常见陷阱

异步编程有几个新手容易踩的坑。这里讲最常见的三个。

第一个坑：在 async 代码里调用阻塞操作。如果你在一个 tokio 任务里调用了 {{`std::thread::sleep`||std thread sleep}} 或者同步的文件读取，这个操作会阻塞整个工作线程。tokio 的调度器在阻塞期间没法运行其他任务，这就违背了 async 的初衷。

解决方案是用 tokio 提供的异步替代品：用 {{`tokio::time::sleep`||tokio time sleep}} 代替 std::thread::sleep，用 {{`tokio::fs`||tokio f s}} 代替 std::fs。如果你必须调用一个阻塞的 API——比如一个只有同步接口的第三方库——用 {{`tokio::task::spawn_blocking`||tokio task spawn blocking}} 把它放到专门的阻塞线程池里。

```rust
let result = tokio::task::spawn_blocking(|| {
    std::fs::read_to_string("big_file.txt")
}).await.unwrap();
```

spawn_blocking 会在一个独立的线程池上运行阻塞操作，不会影响 tokio 的异步工作线程。

第二个坑：忘记 .await。调用一个 async 函数但不 .await 它，这个函数根本不会执行。编译器会给一个 warning 说 Future 没有被使用，但如果你忽略了这个 warning，bug 就很难找。

```rust
async fn save_to_db(data: &str) { /* ... */ }

async fn process() {
    save_to_db("important");  // 忘了 .await！这行什么都没做
    // 应该写 save_to_db("important").await;
}
```

这是 Future 惰性的直接后果。不 poll 就不执行，不 .await 就不 poll。

第三个坑：递归的 async 函数。async 函数的返回类型是编译器自动生成的 Future 类型。如果函数递归调用自己，这个 Future 类型在编译期的大小就变成无限的。编译器会拒绝。解决方案是用 {{`Box::pin`||Box pin}} 把递归调用包装起来，把 Future 放到堆上。

```rust
use std::pin::Pin;
use std::future::Future;

fn traverse(node: Node) -> Pin<Box<dyn Future<Output = ()> + Send>> {
    Box::pin(async move {
        process(&node).await;
        for child in node.children {
            traverse(child).await;
        }
    })
}
```

这种场景不常见，但遇到了要知道怎么解决。

所以记住：不要在 async 上下文中调用阻塞操作，用异步替代品或 spawn_blocking。不要忘记 .await，否则 Future 不会执行。递归 async 函数需要用 Box::pin 包装。

## 回顾

这一章我们用 tokio 实际写了异步代码。

第一，tokio main 宏是启动异步程序的入口。多线程运行时用工作窃取调度，适合高并发场景。单线程运行时适合简单脚本。

第二，tokio::spawn 创建轻量的异步任务。一万个任务的开销远小于一万个线程。和 thread::spawn 一样，要求 Send 加 'static。

第三，select 同时等待多个 Future，先完成的先处理，其余取消。超时、关闭信号、多路复用，都靠 select。

第四，tokio 提供了异步版本的 channel 和 Mutex。异步 mpsc 有背压机制。标准库和 tokio 的同步原语各有适用场景。

下一章是这本书的最后一章。我们会把目光从语言本身移开，看看 Rust 的工具链和生态——Cargo 怎么管理项目，社区有哪些值得了解的 crate，以及从这本书出发你应该往哪些方向继续深入。
