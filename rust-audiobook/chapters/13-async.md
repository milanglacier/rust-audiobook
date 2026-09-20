---
title: 第十三章 异步：用协程驾驭并发 IO
---

# 第十三章 异步：用协程驾驭并发 IO

想象你在写一个聊天服务器。每来一个用户连接，你就创建一个线程来处理它。十个用户没问题，一百个也还行。但如果有一万个用户同时在线呢？一万个线程，每个线程占几兆字节的栈空间，光内存就要几十个 G。更糟糕的是，大部分时间这些线程什么都没干——它们在等网络数据到来。用线程来等 IO，就像雇一万个快递员，每人只负责等一个包裹，包裹没到就站在那里发呆。

Rust 的 async 和 await 提供了另一种方式：用协程代替线程。一个线程可以交替执行成千上万个协程，每个协程在等 IO 的时候主动让出控制权，让别的协程先跑。这一章讲四件事：为什么需要 async，Future 是什么，async 和 await 的语法怎么用，以及执行器在其中扮演什么角色。

## 线程的极限

第十章我们学了用 {{`std::thread::spawn`||std thread spawn}} 创建线程。线程是操作系统提供的并发原语，每个线程有自己的栈空间、自己的调度上下文。创建和切换线程是有代价的：每个线程的栈通常占几兆字节，线程之间的上下文切换需要操作系统介入。

对于 CPU 密集型的任务——比如并行计算、图像处理——线程是很好的选择。你有几个 CPU 核心，就开几个线程，每个线程都在满负荷计算。

但 IO 密集型的任务完全不一样。一个 Web 服务器大部分时间在做什么？等。等客户端发请求，等数据库返回结果，等文件读完。一个线程在等 IO 的时候，它占着几兆字节的栈空间，占着操作系统的一个线程名额，但 CPU 其实是空闲的。

当并发连接数从几十增长到几万，线程模型就撑不住了。这就是 async 要解决的问题：用极少的线程处理大量的并发 IO。

所以记住：线程适合 CPU 密集型并发，async 适合 IO 密集型并发。线程在等 IO 时什么都不干但仍占用资源，async 在等 IO 时让出资源给别的任务。

## Future：异步计算的抽象

Rust 的异步模型建立在一个核心 trait 上：Future。一个 Future 代表一个"还没完成的计算"。它的定义很简单：只有一个 poll 方法。

```rust
trait Future {
    type Output;
    fn poll(self: Pin<&mut Self>, cx: &mut Context) -> Poll<Self::Output>;
}
```

poll 做的事情是：尝试推进这个计算。如果计算完成了，返回 {{`Poll::Ready`||Poll Ready}} 加上结果值。如果还没完成——比如在等网络数据——返回 {{`Poll::Pending`||Poll Pending}}，意思是"我还没好，晚点再来问我"。

这和线程模型有本质区别。线程在等 IO 的时候会阻塞，操作系统把它挂起，整个线程干不了别的事。Future 在等 IO 的时候返回 Pending，调用者可以去驱动别的 Future。这就是协作式并发：每个任务在无法继续的时候主动让出控制权。

你可能注意到 poll 的第一个参数类型是 {{`Pin<&mut Self>`||Pin &mut Self}}，而不是普通的 &mut self。Pin 的作用是防止 Future 在内存中被移动。原因是：一个 async 函数在 await 点暂停时，它的局部变量要保存在 Future 内部。如果某个局部变量引用了 Future 自身的另一个字段，移动 Future 就会产生悬垂引用。Pin 告诉编译器：这个值的内存地址不会变。

不过你几乎不需要直接写 poll 方法。Pin 的细节在大多数情况下也不需要操心。Rust 提供了 async 和 await 两个关键字，让你像写同步代码一样写异步代码，编译器会帮你把它们转换成 Future 和 poll。

所以记住：Future 是 Rust 异步的核心抽象。它是惰性的——创建一个 Future 不会执行任何代码，只有被 poll 的时候才会推进。这和 JavaScript 的 Promise 不一样，Promise 创建即执行，Future 创建不执行。

## async fn 和 .await

在实际代码里，你不需要手动实现 Future。async 关键字帮你做这件事。一个 async fn 看起来几乎和普通函数一样。

```rust
async fn fetch_data(url: &str) -> String {
    let response = reqwest::get(url).await.unwrap();
    response.text().await.unwrap()
}
```

这个函数声明为 async，意味着它返回的不是 String，而是一个实现了 {{`Future<Output = String>`||Future，输出类型是 String}} 的类型。调用 fetch_data 不会执行函数体，只是创建一个 Future。只有对这个 Future 进行 .await，它才真正开始执行。

.await 做的事情是：如果 Future 已经完成，取出结果继续往下走。如果还没完成，暂停当前的 async 函数，把控制权交回给调用者。等底层的 IO 完成后，执行器会重新 poll 这个 Future，从暂停的地方继续。

换句话说，.await 就是暂停点。每个 .await 都是一个"我可以在这里暂停，让别人先跑"的声明。

我们来看一个更直观的例子。假设你要同时发起两个网络请求。

```rust
async fn fetch_two(url1: &str, url2: &str) -> (String, String) {
    let future1 = fetch_data(url1);
    let future2 = fetch_data(url2);
    tokio::join!(future1, future2)
}
```

这里 fetch_data 被调用了两次，但只是创建了两个 Future，还没有执行。{{`tokio::join!`||tokio join 宏}} 同时驱动两个 Future，等它们都完成后返回两个结果的元组。和顺序执行相比，总耗时接近两个请求中更慢的那个，而不是两个的总和。

一个重要的规则：.await 只能在 async 函数或 async 块里使用。你不能在普通的同步函数里 .await 一个 Future。这是因为 .await 需要暂停当前函数的执行，而只有 async 函数才有暂停和恢复的能力。

所以记住：async fn 创建 Future，.await 驱动 Future。async 让你用同步的写法写异步代码，编译器负责把它变成状态机。

## 执行器：谁来驱动 Future

到这里你可能有一个疑问：如果 async fn 只是创建 Future，那谁来第一次 poll 它？谁在 IO 完成后唤醒它？

答案是执行器，英文叫 executor，也叫 runtime。Rust 的标准库定义了 Future trait，但故意不提供执行器。这是一个设计决策：不同的场景需要不同的执行器。一个 Web 服务器需要一个多线程的工作窃取调度器，一个嵌入式设备可能只需要一个单线程的事件循环。

一个执行器做两件事。第一，调度：决定什么时候 poll 哪个 Future。第二，IO 驱动：当 Future 返回 Pending 时，注册一个唤醒回调，等底层 IO 完成后通知调度器重新 poll 这个 Future。

最流行的执行器是 tokio。其他选择包括 async-std 和 smol。它们的核心思想都一样：管理一组 Future，在 IO 就绪时推进它们。

这意味着一个 async fn main 本身是不能直接运行的。你需要一个执行器来启动它。

```rust
fn main() {
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(async {
        println!("hello from async!");
    });
}
```

tokio 提供了一个方便的属性宏 {{`#[tokio::main]`||tokio main 属性宏}}，帮你自动创建运行时并把 async main 包装起来。下一章我们会详细讲 tokio。

所以记住：Rust 把 Future 的定义和 Future 的执行分开了。标准库定义接口，社区提供实现。这种分离让 async Rust 在从 Web 服务器到嵌入式设备的各种场景都能用。

## async 与所有权

async 函数和所有权系统的交互需要特别注意。一个 async 函数在 .await 点暂停时，它的整个状态——局部变量、暂停位置——都保存在 Future 里。这意味着 Future 持有这些变量的所有权。

一个常见的问题出在 Send 上。大多数异步执行器是多线程的，一个 Future 可能在一个线程上开始执行，在 .await 暂停后，被另一个线程唤醒继续执行。这意味着 Future 必须是 Send 的——它的所有状态都要能安全地跨线程传递。

如果你在 .await 之前持有一个不是 Send 的值，比如 Rc 或者标准库的 MutexGuard，并且这个值跨越了 .await 点，编译器会报错。

```rust
async fn bad_example() {
    let data = Rc::new(42);
    some_async_operation().await;  // data 跨越了这个 .await 点
    println!("{data}");  // Rc 不是 Send，编译器拒绝
}
```

解决方案通常是两种。第一，把非 Send 的值限制在 .await 之前用完，不要让它跨越暂停点。第二，换用 Send 的替代品——用 Arc 代替 Rc，用 tokio 的异步 Mutex 代替标准库的 Mutex。

这些规则和前面学的所有权、Send trait 是一脉相承的。第十章讲线程安全时我们说过，Rc 不是 Send 的。在异步代码里，这条规则同样生效，只是触发它的方式不同：不是 thread::spawn，而是 .await 暂停点。

所以记住：async 函数的 Future 持有所有跨越 .await 点的变量。多线程执行器要求 Future 是 Send 的。非 Send 的值不能跨越 .await 点。

## 回顾

我们来回顾这一章的要点。

第一，async 适合 IO 密集型并发。线程在等 IO 时空闲但占用资源，async 在等 IO 时让出资源给别的任务。

第二，Future 是异步的核心抽象。它是惰性的，创建不执行，只有被 poll 的时候才推进。poll 返回 Ready 表示完成，返回 Pending 表示还没好。

第三，async fn 创建 Future，.await 驱动 Future。.await 是暂停点，每个暂停点都是当前任务让出控制权的机会。

第四，执行器负责调度和驱动 Future。Rust 标准库不提供执行器，tokio 是最流行的选择。

下一章我们讲 tokio——Rust 异步生态的核心运行时。我们会用 tokio 写实际的异步程序，学习 spawn、select、异步 channel 这些工具。
