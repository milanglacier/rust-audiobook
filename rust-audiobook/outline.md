# 听懂 Rust：从零开始的所有权之旅

## 听众与目标

- 听众背景：有至少一门编程语言经验（Python、JavaScript、Java 等均可），对系统编程和内存管理没有深入了解，想系统地学习 Rust。
- 听完后应该能够：
  - 理解 Rust 的所有权模型为什么存在，以及它如何保证内存安全
  - 读懂中等复杂度的 Rust 代码，知道编译器为什么接受或拒绝一段代码
  - 使用 struct、enum、trait、泛型来建模问题
  - 使用 Result 和 Option 做错误处理
  - 理解 Rust 的并发模型为什么被称为"无畏并发"
  - 知道如何用 Cargo 管理项目，找到和使用 crate
- 语言：中文（技术术语保留英文，见术语表）
- 深度（见 writing-guide.md §1 的四级）：第 3 级——机制层。讲清楚每个概念为什么存在、编译器的检查逻辑、常见的报错信息意味着什么。会展示关键代码片段，但不会逐行念代码。不涉及编译器内部实现或 MIR/LLVM 层面的细节。
- 总长度：15 章，每章 10–15 分钟，总计约 2.5–3.5 小时
- 材料来源：无特定材料，基于 Rust 官方文档、The Rust Programming Language (The Book)、Rust by Example 等公开资源的理解

## 术语表

| 概念 | 全书统一说法 | 首次出现时补充 |
| ---- | ------------ | -------------- |
| ownership | 所有权 | 英文叫 ownership |
| borrow / borrowing | 借用 | 英文叫 borrow |
| borrow checker | borrow checker | 中文可说"借用检查器" |
| move | move | 中文可说"移动" |
| clone | clone | — |
| Copy trait | Copy | 注意和 clone 的区别 |
| reference | 引用 | 英文叫 reference |
| mutable reference | 可变引用 | &mut T |
| immutable reference | 不可变引用 / 共享引用 | &T |
| lifetime | 生命周期 | 英文叫 lifetime |
| lifetime elision | 生命周期省略 | lifetime elision |
| scope | 作用域 | 英文叫 scope |
| stack / heap | 栈 / 堆 | stack / heap |
| struct | struct | 中文可说"结构体" |
| enum | enum | 中文可说"枚举" |
| pattern matching | 模式匹配 | pattern matching |
| trait | trait | — |
| generic | 泛型 | 英文叫 generic |
| trait bound | trait bound | 中文可说"trait 约束" |
| impl Trait | impl Trait | — |
| closure | closure | 中文可说"闭包" |
| iterator | 迭代器 | 英文叫 iterator |
| Result | Result | — |
| Option | Option | — |
| unwrap | unwrap | — |
| panic | panic | 中文可说"恐慌" |
| ? operator | 问号运算符 | — |
| thread | 线程 | 英文叫 thread |
| channel | channel | 中文可说"通道" |
| Mutex | Mutex | 中文可说"互斥锁" |
| Send / Sync | Send / Sync | 两个 marker trait |
| smart pointer | 智能指针 | smart pointer |
| Box | Box | 堆上分配 |
| Rc | Rc | reference counting |
| Arc | Arc | atomic reference counting |
| RefCell | RefCell | 运行时借用检查 |
| interior mutability | 内部可变性 | interior mutability |
| Cargo | Cargo | Rust 的包管理器和构建工具 |
| crate | crate | Rust 的编译单元和包 |
| macro | 宏 | macro |
| RAII | R A I I | Resource Acquisition Is Initialization |
| zero-cost abstraction | 零成本抽象 | zero-cost abstraction |
| type inference | 类型推断 | type inference |
| destructuring | 解构 | destructuring |
| async | async | — |
| await | await | — |
| Future | Future | — |
| poll | poll | — |
| Pin | Pin | 防止值在内存中移动 |
| executor / runtime | 执行器 / 运行时 | executor / runtime |
| tokio | tokio | 最流行的异步运行时 |
| spawn (async) | tokio::spawn | — |
| select | select | — |
| work-stealing | 工作窃取 | work-stealing |
| backpressure | 背压 | backpressure |

## 章节

### 01 为什么是 Rust

- 一句话：从一个 C 语言的 use-after-free bug 出发，讲清楚 Rust 到底在解决什么问题，以及它用什么代价换来了安全。
- 听众带走的 2–4 件事：
  1. 内存安全问题（悬垂指针、双重释放、数据竞争）在 C/C++ 中有多普遍，后果有多严重
  2. 垃圾回收和手动管理各自的代价
  3. Rust 的第三条路：编译期检查所有权，零运行时开销
  4. Rust 的设计哲学——如果编译通过，这类 bug 就不存在
- 会出现的公式 / 代码 / 引文：
  - C 语言的 use-after-free 示例（展示，不念）
  - Rust 等价代码被编译器拒绝（展示，不念）
- 与前后章的衔接：这是全书的起点；下一章正式进入所有权的规则

### 02 所有权：每个值只有一个主人

- 一句话：Rust 最核心的规则——每个值有且只有一个 owner，owner 离开作用域时值被释放——以及这个规则带来的 move 语义。
- 听众带走的 2–4 件事：
  1. 所有权的三条规则
  2. 值在赋值和函数传参时会 move，原来的变量失效
  3. 栈上的简单类型实现了 Copy，赋值是复制而不是 move
  4. clone 是显式的深拷贝，move 是零成本的所有权转移
- 会出现的公式 / 代码 / 引文：
  - String 的 move 示例：`let s2 = s1;` 之后 `s1` 失效
  - 函数传参导致 move 的示例
  - Copy 类型（i32）和非 Copy 类型（String）的对比
  - 内存布局示意（栈指针 + 堆数据）用语言描述
- 与前后章的衔接：上一章讲了为什么需要规则；这一章给出了规则本身；下一章讲如何在不转移所有权的情况下"借"一个值来用

### 03 借用：不转移所有权的访问

- 一句话：借用让你在不 move 的情况下读取或修改一个值，但 borrow checker 会强制执行"同一时刻要么一个可变引用，要么任意个不可变引用"的规则。
- 听众带走的 2–4 件事：
  1. 不可变引用 &T：可以有多个，只能读
  2. 可变引用 &mut T：同一时刻只能有一个，可以读写
  3. 为什么不能同时存在可变和不可变引用——数据竞争的编译期防护
  4. 引用必须在 owner 还活着的时候使用——悬垂引用是编译错误
- 会出现的公式 / 代码 / 引文：
  - 不可变借用的基本示例
  - 可变借用的基本示例
  - 同时存在 &T 和 &mut T 时的编译错误
  - 悬垂引用的编译错误
- 与前后章的衔接：上一章讲了 move；这一章讲了借用；下一章讲编译器如何用生命周期来追踪引用的有效范围

### 04 生命周期：编译器的记忆

- 一句话：生命周期是编译器追踪"这个引用还有效吗"的机制，大多数时候编译器自己能推断，你只需在它推断不了时标注。
- 听众带走的 2–4 件事：
  1. 生命周期是什么：引用有效的那段作用域
  2. 生命周期省略规则：为什么大多数函数不需要手写 'a
  3. 什么时候必须标注：返回引用的函数、结构体持有引用
  4. 'static 的含义：活到程序结束的引用
- 会出现的公式 / 代码 / 引文：
  - `fn longest<'a>(x: &'a str, y: &'a str) -> &'a str` 的解读
  - 省略规则的三条法则
  - struct 持有引用时的生命周期标注
  - 常见的生命周期相关编译错误信息
- 与前后章的衔接：所有权三部曲到此结束；下一章转向 Rust 的数据建模能力

### 05 Struct 与 Enum：用类型说话

- 一句话：Rust 的 struct 和 enum 比大多数语言的对应物更强大——enum 可以携带数据，配合模式匹配让你把逻辑分支交给编译器检查。
- 听众带走的 2–4 件事：
  1. struct 的三种形式：命名字段、元组、单元
  2. enum 可以让每个变体携带不同类型的数据
  3. match 是穷尽的——漏掉一个分支编译器就报错
  4. Option 和 Result 就是普通的 enum，没有魔法
- 会出现的公式 / 代码 / 引文：
  - 定义一个带方法的 struct
  - enum 携带数据的示例（消息类型）
  - match 表达式和穷尽检查
  - Option 的定义：`enum Option<T> { Some(T), None }`
  - if let 的简洁写法
- 与前后章的衔接：上一章结束了所有权部分；这一章建立了数据建模的基础；下一章讲如何用 Result 和 Option 做错误处理

### 06 错误处理：没有异常的世界

- 一句话：Rust 没有 try-catch，而是用 Result 和 Option 这两个 enum 把错误变成普通的返回值，用 ? 运算符让错误自动往上传播。
- 听众带走的 2–4 件事：
  1. panic 和 Result 的区别：不可恢复 vs 可恢复
  2. Result 的用法：match、unwrap、expect、? 运算符
  3. ? 运算符的本质：遇到 Err 就提前返回
  4. 如何设计自己的错误类型
- 会出现的公式 / 代码 / 引文：
  - 文件读取的 Result 处理链
  - ? 运算符的展开等价代码
  - 自定义错误类型和 From trait 的实现
  - unwrap 在什么场景下可以用
- 与前后章的衔接：上一章讲了 enum 和 Option；这一章深入了 Result；下一章讲 trait——错误处理里已经用到的 From 就是一个 trait

### 07 Trait：共享行为的契约

- 一句话：Trait 定义了一组行为的契约，是 Rust 实现多态的核心方式——类似接口但更灵活，因为你可以给别人的类型加 trait。
- 听众带走的 2–4 件事：
  1. 定义 trait 和为类型实现 trait
  2. trait bound：用 trait 约束泛型参数
  3. impl Trait 语法：参数位置和返回值位置的不同含义
  4. 常见的标准库 trait：Display、Debug、Clone、From、Iterator
- 会出现的公式 / 代码 / 引文：
  - 定义一个 Summary trait 并为两个 struct 实现
  - 泛型函数 + trait bound 的写法
  - `impl Trait` 在参数和返回值位置的示例
  - 孤儿规则的解释
- 与前后章的衔接：上一章用到了 From trait；这一章系统讲 trait；下一章的迭代器就是一个 trait

### 08 迭代器与集合：数据的流水线

- 一句话：Rust 的迭代器是零成本抽象的典型——你用 map、filter、collect 写出声明式的数据处理链，编译器帮你优化到和手写循环一样快。
- 听众带走的 2–4 件事：
  1. Iterator trait 只需要实现一个 next 方法
  2. 惰性求值：链式调用不会立即执行，直到遇到 collect 或 for
  3. 常用适配器：map、filter、enumerate、zip、take、flat_map
  4. Vec、HashMap 等集合类型的基本用法和所有权关系
- 会出现的公式 / 代码 / 引文：
  - 一个迭代器链的示例：读取文件 → 按行 → 过滤 → 收集
  - 自己实现一个简单的 Iterator
  - Vec 的所有权：into_iter vs iter vs iter_mut
  - HashMap 的基本操作
- 与前后章的衔接：上一章讲了 trait；这一章用了 Iterator trait；下一章讲 closure——迭代器链里传给 map 和 filter 的就是 closure

### 09 Closure：捕获环境的函数

- 一句话：Closure 是能捕获周围变量的匿名函数，Rust 的 closure 特别在于它的捕获方式和所有权系统紧密绑定——是借用还是 move，编译器都要管。
- 听众带走的 2–4 件事：
  1. closure 的语法和基本用法
  2. 三种捕获方式：不可变借用、可变借用、move
  3. 三种 closure trait：Fn、FnMut、FnOnce 分别对应什么
  4. move closure 在线程中的必要性
- 会出现的公式 / 代码 / 引文：
  - closure 语法和类型推断的示例
  - 三种捕获方式的对比示例
  - move 关键字在 closure 前的用法
  - 一个把 closure 作为参数的泛型函数
- 与前后章的衔接：上一章的迭代器用了 closure；这一章深入了 closure 本身；下一章讲并发——move closure 在线程间传递数据时不可或缺

### 10 并发：编译器守护的安全感

- 一句话：Rust 的"无畏并发"不是口号——Send 和 Sync 这两个 marker trait 让编译器在编译期阻止数据竞争，你不需要祈祷自己没忘加锁。
- 听众带走的 2–4 件事：
  1. std::thread::spawn 和 move closure 传递数据
  2. Send 和 Sync 的含义：什么类型可以跨线程发送、什么可以跨线程共享
  3. Mutex 和 Arc 配合使用共享可变状态
  4. channel 做消息传递：mpsc 模型
- 会出现的公式 / 代码 / 引文：
  - spawn + move closure 的基本示例
  - 不加 Arc 时的编译错误
  - Arc + Mutex 共享计数器的示例
  - mpsc::channel 的生产者-消费者示例
- 与前后章的衔接：上一章讲了 move closure；这一章讲了并发中的所有权和借用；下一章讲智能指针——Arc 就是一种智能指针

### 11 智能指针：超越引用

- 一句话：当普通引用不够用时——需要堆分配、需要多个 owner、需要运行时借用检查——Rust 提供了 Box、Rc、Arc、RefCell 这些智能指针，每个解决一个具体问题。
- 听众带走的 2–4 件事：
  1. Box：把值放到堆上，最简单的智能指针，用于递归类型和 trait object
  2. Rc 和 Arc：引用计数实现多所有者，Arc 是线程安全版
  3. RefCell 和内部可变性：把借用检查推迟到运行时
  4. Deref 和 Drop trait：智能指针背后的机制
- 会出现的公式 / 代码 / 引文：
  - 用 Box 定义链表节点
  - Rc 共享数据的示例
  - RefCell 突破不可变限制的示例
  - Rc + RefCell 组合的典型用法
- 与前后章的衔接：上一章用了 Arc；这一章系统讲了所有智能指针；下一章是全书收尾，讲生态和实践

### 13 异步：用协程驾驭并发 IO

- 一句话：当并发连接数从几十增长到几万，线程模型就撑不住了——async 用协程代替线程，让一个线程交替执行成千上万个任务。
- 听众带走的 2–4 件事：
  1. 线程适合 CPU 密集型，async 适合 IO 密集型
  2. Future trait 是异步的核心抽象，惰性的——创建不执行，poll 才推进
  3. async fn 创建 Future，.await 驱动 Future，编译器把它变成状态机
  4. Rust 标准库不提供执行器，tokio 是最流行的选择
- 会出现的公式 / 代码 / 引文：
  - Future trait 的定义：poll、Pin、Poll::Ready 和 Poll::Pending
  - async fn 和 .await 的基本用法
  - tokio::join! 并发驱动多个 Future
  - Rc 跨越 .await 点导致非 Send 的编译错误
- 与前后章的衔接：上一章讲了智能指针，Pin 和 Arc 都在 async 中再次出现；下一章讲 tokio 实战

### 14 Tokio：异步编程实战

- 一句话：tokio 是 Rust 异步生态的核心运行时——它提供任务调度、异步 IO、定时器、channel，几乎所有异步 crate 都建立在它之上。
- 听众带走的 2–4 件事：
  1. #[tokio::main] 启动运行时，多线程用工作窃取调度
  2. tokio::spawn 创建轻量异步任务，比线程轻几个数量级
  3. select! 同时等待多个 Future，先完成的先处理，其余取消
  4. tokio 提供异步 channel（有背压）和异步 Mutex
- 会出现的公式 / 代码 / 引文：
  - tokio::main 宏和手动创建 Runtime 的等价写法
  - tokio::spawn 并发抓取多个 URL 的示例
  - select! 实现超时和优雅关闭的模式
  - tokio::sync::mpsc 和标准库 mpsc 的区别
  - spawn_blocking 处理阻塞操作
  - 常见陷阱：阻塞 async 上下文、忘记 .await、递归 async 函数
- 与前后章的衔接：上一章讲了 async 原理；这一章用 tokio 实战；下一章是全书收尾，讲生态和实践

### 15 生态与实践：从学到用

- 一句话：Rust 的工具链和生态是它吸引人的另一半——Cargo、crate 生态、测试、文档、以及从这本书出发你应该往哪里走。
- 听众带走的 2–4 件事：
  1. Cargo 的核心功能：new、build、run、test、doc、publish
  2. 依赖管理和 crates.io 生态
  3. Rust 的测试框架：单元测试、集成测试、文档测试
  4. 接下来的学习路线：Web 开发、unsafe、宏、嵌入式等方向
- 会出现的公式 / 代码 / 引文：
  - Cargo.toml 的结构
  - `#[test]` 和 `#[cfg(test)]` 的写法
  - 文档注释和 `cargo doc` 的效果
  - 推荐的 crate 和学习资源（展示为延伸阅读）
- 与前后章的衔接：这是全书最后一章；回顾全书脉络，指向未来的学习方向
