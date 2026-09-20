---
title: 第十章 并发：编译器守护的安全感
---

# 第十章 并发：编译器守护的安全感

你写了一个多线程程序。两个线程同时修改同一个变量，没有加锁。在 C 里，这个程序可能今天跑一百次都没事，明天突然在生产环境崩溃。这就是数据竞争——最难复现、最难调试的 bug 之一。在 Java 或 Python 里，运行时会抛异常或者给你一个莫名其妙的结果。但在 Rust 里，这段代码根本编译不过。编译器在你写完代码的那一刻就告诉你：这样做不安全。

Rust 把这种能力叫做"无畏并发"。这一章讲四件事：怎么用 spawn 和 move closure 创建线程，Send 和 Sync 这两个 trait 意味着什么，怎么用 Arc 加 Mutex 共享可变状态，以及怎么用 channel 做消息传递。

## 创建线程：spawn 和 move closure

在 Rust 里创建线程很简单。调用 {{`std::thread::spawn`||std thread spawn}}，传一个 closure 进去，就得到一个新线程。spawn 返回一个 JoinHandle，你可以用 join 方法等待线程结束。

```rust
use std::thread;
use std::time::Duration;

fn main() {
    let handle = thread::spawn(|| {
        for i in 1..5 {
            println!("子线程: {i}");
            thread::sleep(Duration::from_millis(1));
        }
    });

    for i in 1..3 {
        println!("主线程: {i}");
        thread::sleep(Duration::from_millis(1));
    }

    handle.join().unwrap();
}
```

这段代码创建了一个子线程，主线程和子线程会交替打印。join 确保主线程在子线程结束前不会退出。

但如果你想把主线程里的数据传给子线程，事情就变得有趣了。上一章我们讲过，spawn 的 closure 必须用 move。原因是：新线程可能活得比创建它的函数更久，closure 不能借用一个可能先消失的变量。

```rust
fn main() {
    let message = String::from("hello");
    let handle = thread::spawn(move || {
        println!("{message}");
    });
    // println!("{message}"); // 编译错误：message 已经 move 了
    handle.join().unwrap();
}
```

move 把 message 的所有权转移给了新线程的 closure。主线程不能再用 message。这听起来像是限制，但正是这条规则保证了数据安全：同一份数据不会同时被两个线程持有。

但问题来了：如果多个线程确实需要访问同一份数据怎么办？这就需要共享所有权，我们一会儿讲。先来看看 Rust 用什么机制在编译期保证线程安全。

## Send 和 Sync：编译期的线程安全

Rust 的线程安全建立在两个 marker trait 上：Send 和 Sync。它们不定义任何方法，只是一个标记，告诉编译器一个类型可以在线程之间怎么使用。

Send 的意思是：这个类型的值可以安全地从一个线程发送到另一个线程。换句话说，所有权可以跨线程转移。Rust 里几乎所有类型都是 Send 的。一个典型的例外是 Rc：Rc 用非原子操作来维护引用计数，如果两个线程同时修改计数器，就会出错。所以 Rc 不是 Send 的，你没法把 Rc 发送到另一个线程。

Sync 的意思是：这个类型的引用可以安全地在多个线程之间共享。也就是说，如果 T 是 Sync 的，那么 &T 就是 Send 的。这意味着多个线程可以同时持有对 T 的不可变引用。大多数基础类型都是 Sync 的。RefCell 不是 Sync 的，因为它的运行时借用检查不是线程安全的。

这两个 trait 的关键在于：你不需要手动实现它们。编译器会自动根据类型的字段来判断。如果一个 struct 的所有字段都是 Send 的，那这个 struct 就自动是 Send 的。如果你尝试在线程之间发送一个不是 Send 的类型，编译器会直接报错。

```rust
use std::rc::Rc;
use std::thread;

fn main() {
    let data = Rc::new(42);
    // let handle = thread::spawn(move || {
    //     println!("{data}");
    // });
    // 编译错误：`Rc<i32>` cannot be sent between threads safely
}
```

编译器的错误信息很明确：Rc 不能安全地在线程之间发送。它还会告诉你：如果你需要跨线程共享数据，考虑使用 Arc。

所以记住：Send 和 Sync 不需要你写任何代码。编译器通过类型系统自动检查线程安全。在其他语言里，这些检查要么靠程序员自律，要么靠运行时检测。Rust 把它提前到了编译期。

## Arc 加 Mutex：共享可变状态

好，我们回到刚才的问题：多个线程需要访问同一份数据。如果只是读取，用 Arc 包一下就行了。Arc 是 Rc 的线程安全版本，它用原子操作来维护引用计数，所以是 Send 加 Sync 的。

```rust
use std::sync::Arc;
use std::thread;

fn main() {
    let data = Arc::new(String::from("hello"));
    let mut handles = vec![];

    for i in 0..3 {
        let data_clone = Arc::clone(&data);
        let handle = thread::spawn(move || {
            println!("线程 {i}: {data_clone}");
        });
        handles.push(handle);
    }

    for handle in handles {
        handle.join().unwrap();
    }
}
```

每个线程拿到 Arc 的一个 clone。注意，clone 一个 Arc 不会复制底层的 String，只是增加引用计数。所有线程共享同一份字符串数据。

但如果线程需要修改数据呢？Arc 只提供不可变访问。你需要内部可变性，这时候就要把 Mutex 装进 Arc。Mutex 是互斥锁，同一时刻只有一个线程能持有锁并修改里面的数据。

我们来写一个经典的例子：多个线程共同递增一个计数器。

```rust
use std::sync::{Arc, Mutex};
use std::thread;

fn main() {
    let counter = Arc::new(Mutex::new(0));
    let mut handles = vec![];

    for _ in 0..10 {
        let counter = Arc::clone(&counter);
        let handle = thread::spawn(move || {
            let mut num = counter.lock().unwrap();
            *num += 1;
        });
        handles.push(handle);
    }

    for handle in handles {
        handle.join().unwrap();
    }

    println!("最终计数: {}", *counter.lock().unwrap());
}
```

我们来拆解这段代码。counter 的类型是 {{`Arc<Mutex<i32>>`||Arc Mutex i32}}。外层的 Arc 让多个线程可以共享所有权。内层的 Mutex 保证同一时刻只有一个线程能修改里面的 i32。

每个线程先 clone 一份 Arc，然后 move 进 closure。在 closure 里，调用 lock 方法获取锁。lock 返回一个 MutexGuard，这是一个智能指针，可以通过它读写里面的值。当 MutexGuard 离开作用域，锁自动释放。这就是 R A I I 模式：获取资源的时候加锁，离开作用域的时候自动释放。不需要手动 unlock，也就不会忘记 unlock。

如果你漏掉 Arc，直接把 Mutex 传给线程会怎样？编译器会报错，因为 Mutex 被 move 进了第一个线程之后，第二个线程就没法用了。Arc 解决的正是这个问题：它让所有权被安全地共享。

如果你不用 Mutex，直接把 Arc 里的值改了会怎样？做不到。Arc 只提供不可变访问，你拿不到可变引用。Mutex 通过 lock 提供了内部可变性，而且是线程安全的内部可变性。

所以记住：Arc 加 Mutex 是 Rust 里共享可变状态的标准模式。Arc 提供跨线程的共享所有权，Mutex 提供线程安全的内部可变性，R A I I 保证锁一定会被释放。

## Channel：消息传递

共享状态不是线程通信的唯一方式。另一种经典方式是消息传递。Rust 标准库提供了 mpsc channel，mpsc 的意思是 multiple producer, single consumer，也就是多个发送者、一个接收者。

创建一个 channel 会得到两个端：一个发送端 tx，一个接收端 rx。发送端可以 clone 给多个线程，但接收端只能有一个。

```rust
use std::sync::mpsc;
use std::thread;

fn main() {
    let (tx, rx) = mpsc::channel();

    thread::spawn(move || {
        let message = String::from("hello");
        tx.send(message).unwrap();
        // println!("{message}"); // 编译错误：message 已经被 send 了
    });

    let received = rx.recv().unwrap();
    println!("收到: {received}");
}
```

注意一个关键细节：send 会 move 值的所有权。调用 send 之后，message 就属于 channel 了，发送线程不能再使用它。这是所有权系统在保护你：如果发送之后发送线程还能修改 message，接收线程拿到的数据就可能不一致。

recv 方法会阻塞当前线程，直到收到一条消息。如果你不想阻塞，可以用 try_recv，它会立即返回一个 Result。

我们来看一个更完整的例子：多个生产者往同一个 channel 里发消息。

```rust
use std::sync::mpsc;
use std::thread;

fn main() {
    let (tx, rx) = mpsc::channel();

    for i in 0..3 {
        let tx_clone = tx.clone();
        thread::spawn(move || {
            let message = format!("来自线程 {i}");
            tx_clone.send(message).unwrap();
        });
    }

    drop(tx); // 关键：必须 drop 原始的 tx

    for received in rx {
        println!("收到: {received}");
    }
}
```

这里有一个容易踩的坑：原始的 tx 必须被 drop 掉。因为接收端的 for 循环会一直等，直到所有发送端都关闭。如果你忘了 drop 原始的 tx，程序就会永远等下去。每个线程里的 tx_clone 在线程结束时会自动 drop，但原始的 tx 还在 main 里活着。

channel 和 Arc 加 Mutex 各有适用场景。channel 适合一个方向的数据流，比如任务队列、日志收集。Arc 加 Mutex 适合多个线程需要读写同一块数据的场景，比如共享缓存。在实际项目中，两种方式经常一起使用。

## 编译器的安全网

我们来把这一章和前面几章串起来。Rust 的并发安全不是靠一个单独的机制，而是靠所有权、借用、trait 这些你已经学过的概念协同工作。

所有权系统保证一个值只有一个 owner，所以把值 move 给另一个线程后，原来的线程就用不了了，不会出现两个线程同时修改同一个变量。

借用规则保证同一时刻要么一个可变引用，要么多个不可变引用，这在单线程里防止数据竞争，在多线程里同样有效。

Send 和 Sync 这两个 trait 让编译器在类型层面追踪什么东西可以跨线程。不是 Send 的类型根本传不进 spawn，不是 Sync 的类型根本拿不到跨线程的共享引用。

这些规则叠在一起，结果就是：如果你的代码编译通过，编译器已经帮你排除了数据竞争。你不需要在代码审查时盯着每一个锁看有没有忘记加，不需要用动态检测工具来碰运气，也不需要祈祷那个只在高并发下出现的 bug 不会在生产环境里被触发。编译器就是你的安全网。

## 回顾

我们来回顾这一章的要点。

第一，用 spawn 加 move closure 创建线程。move 把数据的所有权转移给新线程，保证线程不会持有悬垂引用。

第二，Send 和 Sync 是两个 marker trait，编译器自动根据类型的组成来判断。Send 表示值可以跨线程发送，Sync 表示引用可以跨线程共享。不满足的类型编译器直接拒绝。

第三，Arc 加 Mutex 是共享可变状态的标准模式。Arc 提供线程安全的引用计数共享所有权，Mutex 提供线程安全的内部可变性，R A I I 保证锁一定释放。

第四，channel 做消息传递。send 会 move 值的所有权，保证发送后发送方不能再修改。mpsc 支持多个发送者、一个接收者。

下一章我们讲智能指针。这一章里出现的 Arc 和 Mutex 就是智能指针。下一章我们系统讲清楚 Box、Rc、Arc、RefCell 各自解决什么问题，以及 Deref 和 Drop 这两个 trait 如何让智能指针像普通引用一样使用。
