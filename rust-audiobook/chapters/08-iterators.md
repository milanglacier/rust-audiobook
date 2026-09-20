---
title: 第八章 迭代器与集合：数据的流水线
---

# 第八章 迭代器与集合：数据的流水线

假设你有一个文本文件，里面是一串数字，每行一个。你想读进来，过滤掉负数，把剩下的每个数乘以二，然后收集到一个 Vec 里。在很多语言里，你会写一个 for 循环，声明一个空列表，逐个判断，逐个追加。在 Rust 里，你可以用一条迭代器链把这件事写成一行。而且编译器会把这条链优化到和手写循环一样快——这就是零成本抽象。

这一章讲四件事：Iterator trait 的核心是什么，惰性求值意味着什么，常用的迭代器适配器有哪些，以及 Vec 和 HashMap 这两个最重要的集合怎么和所有权互动。

## Iterator trait：只需要一个 next

上一章我们讲了 trait。迭代器就是一个 trait，定义在标准库里，叫 Iterator。这个 trait 只要求你实现一个方法：next。

next 的签名很简单：每调用一次，返回一个 Option。如果还有元素，返回 Some 加上这个元素；如果没有了，返回 None。就这么一个方法，撑起了 Rust 整个迭代器生态。

```rust
trait Iterator {
    type Item;
    fn next(&mut self) -> Option<Self::Item>;
}
```

这里出现了一个新语法：type Item，叫做关联类型。你可以把它理解为迭代器产出的元素的类型。一个迭代器遍历 i32，它的 Item 就是 i32；遍历 String，Item 就是 String。

我们来动手实现一个最简单的迭代器：一个从某个数开始倒数到零的计数器。

```rust
struct Countdown {
    value: u32,
}

impl Iterator for Countdown {
    type Item = u32;

    fn next(&mut self) -> Option<u32> {
        if self.value > 0 {
            self.value -= 1;
            Some(self.value + 1)
        }  else {
            None
        }
    }
}
```

有了这个实现，你就可以用 for 循环来遍历它，也可以调用 map、filter 这些方法。因为这些方法都是 Iterator trait 提供的默认实现，你只要实现了 next，几十个方法就免费获得了。

```rust
let countdown = Countdown { value: 5 };
for n in countdown {
    println!("{n}");
}
```

所以记住：Iterator trait 的核心就是 next 方法。实现了 next，你就拥有了整个迭代器工具箱。

## 惰性求值：不到终点不干活

迭代器有一个非常重要的特性：惰性求值。当你调用 map 或者 filter 的时候，它们不会立即执行。它们只是记录下"你想做什么"，然后返回一个新的迭代器。真正的计算要等到你调用 collect、for 循环、或者其他消费方法的时候才会发生。

来看一个例子。这两行代码创建了一个迭代器链，但什么都没有发生。

```rust
let v = vec![1, 2, 3, 4, 5];
let iter = v.iter().map(|x| x * 2).filter(|x| *x > 4);
```

这里的 map 和 filter 各自返回一个新的迭代器，包裹着前一个迭代器。但没有任何元素被计算过。只有当你调用 collect 的时候，整条链才开始从头到尾运转。

```rust
let result: Vec<i32> = v.iter().map(|x| x * 2).filter(|x| *x > 4).collect();
```

惰性求值的好处是：如果你只需要前三个满足条件的元素，你可以在链的最后加上 take，迭代器会在拿到三个元素后立刻停下来，不会遍历整个集合。这在处理大数据或者无限序列的时候非常有价值。

## 常用的迭代器适配器

Rust 标准库提供了几十个迭代器方法。我们来看最常用的几个。

map 对每个元素做一次变换。你传入一个 closure，它接收一个元素，返回一个新元素。

```rust
let names = vec!["alice", "bob", "charlie"];
let upper: Vec<String> = names.iter().map(|s| s.to_uppercase()).collect();
```

filter 保留满足条件的元素，丢弃不满足的。注意 filter 的 closure 接收的是引用的引用，因为 filter 不想拿走元素的所有权。

```rust
let numbers = vec![1, 2, 3, 4, 5, 6];
let evens: Vec<&i32> = numbers.iter().filter(|n| *n % 2 == 0).collect();
```

enumerate 给每个元素加上一个从零开始的索引。返回的是一个元组，第一个是索引，第二个是元素。在你需要同时知道"第几个"和"是什么"的时候非常好用。

```rust
let fruits = vec!["apple", "banana", "cherry"];
for (i, fruit) in fruits.iter().enumerate() {
    println!("{i}: {fruit}");
}
```

zip 把两个迭代器配对。它把两个迭代器的元素一一对应地组合成元组，长度以较短的那个为准。

```rust
let names = vec!["alice", "bob"];
let scores = vec![95, 87];
let pairs: Vec<_> = names.iter().zip(scores.iter()).collect();
```

{{`flat_map`||flat map}} 是 map 和 flatten 的结合。当你的变换函数返回一个迭代器的时候，flat map 会把所有返回的迭代器展平成一个。

```rust
let sentences = vec!["hello world", "foo bar"];
let words: Vec<&str> = sentences.iter().flat_map(|s| s.split_whitespace()).collect();
```

最后是 fold，它把所有元素归约成一个值。你提供一个初始值和一个累加函数。求和、求积、拼接字符串，都可以用 fold。

```rust
let sum = vec![1, 2, 3, 4, 5].iter().fold(0, |acc, x| acc + x);
```

这些方法可以自由组合。一条迭代器链可以有 map、filter、take、collect 串在一起，读起来就像在描述"对数据做什么"，而不是"怎么一步一步做"。这就是声明式风格的魅力。

## Vec：最常用的集合

说完迭代器，我们来看集合。Vec，也就是动态数组，是 Rust 里最常用的集合类型。

创建一个 Vec 有两种常见方式：用 new 创建空的，或者用 vec 宏直接给出初始值。

```rust
let mut v1: Vec<i32> = Vec::new();
v1.push(1);
v1.push(2);

let v2 = vec![1, 2, 3];
```

Vec 拥有它里面所有元素的所有权。当 Vec 被释放的时候，里面的每个元素也会被释放。这和所有权规则完全一致。

这里有一个重要的话题：遍历 Vec 的时候，你选择哪种迭代器方式，决定了所有权的去向。Rust 提供了三种方法。

第一种是 iter，返回不可变引用。遍历之后 Vec 还在，你还能用它。

```rust
let v = vec![1, 2, 3];
for n in v.iter() {
    println!("{n}");
}
println!("v still exists: {:?}", v);
```

第二种是 {{`iter_mut`||iter mut}}，返回可变引用。你可以在遍历的同时修改每个元素，但 Vec 本身必须是 mut 的。

```rust
let mut v = vec![1, 2, 3];
for n in v.iter_mut() {
    *n *= 2;
}
```

第三种是 {{`into_iter`||into iter}}，消耗 Vec 本身，把每个元素的所有权交出来。遍历之后 Vec 就没了。当你在 for 循环里直接写 for n in v，Rust 调用的就是 into iter。

```rust
let v = vec![String::from("a"), String::from("b")];
for s in v {
    println!("{s}");
    // s 的所有权在这个循环体里
}
// v 已经不能用了
```

这三种方式的选择取决于你的需求：只需要读，用 iter；需要改，用 iter mut；需要拿走元素，用 into iter。

## HashMap：键值对的集合

另一个常用的集合是 HashMap。它存储键值对，通过键来快速查找值。HashMap 不在预导入模块里，需要手动引入。

```rust
use std::collections::HashMap;

let mut scores = HashMap::new();
scores.insert(String::from("alice"), 95);
scores.insert(String::from("bob"), 87);
```

查询的时候用 get 方法，它返回一个 Option。因为你查的键可能不存在，所以 Rust 用 Option 来表达这个可能性。

```rust
if let Some(score) = scores.get("alice") {
    println!("alice's score: {score}");
}
```

HashMap 的所有权规则和 Vec 一样直觉：对于实现了 Copy 的类型，比如 i32，值会被复制进去。对于拥有所有权的类型，比如 String，所有权会被 move 进 HashMap。

```rust
let key = String::from("charlie");
let value = 92;
scores.insert(key, value);
// key 已经被 move 进去了，不能再用
// value 是 i32，实现了 Copy，还能用
```

遍历 HashMap 用 for 循环，每次拿到一个键值对的引用。

```rust
for (name, score) in &scores {
    println!("{name}: {score}");
}
```

HashMap 还有一个很实用的方法叫 entry。它让你检查一个键是否存在，如果不存在就插入一个默认值。这在统计词频这类场景里特别好用。

```rust
let text = "hello world hello rust";
let mut word_count = HashMap::new();
for word in text.split_whitespace() {
    let count = word_count.entry(word).or_insert(0);
    *count += 1;
}
```

entry 返回一个 Entry enum，{{`or_insert`||or insert}} 在键不存在时插入默认值，然后返回值的可变引用。这样你就可以直接在原地修改。

## 回顾

我们来总结这一章的核心内容。

第一，Iterator trait 的核心是 next 方法。实现了 next，你就自动获得了 map、filter、collect 等几十个方法。

第二，迭代器是惰性的。链式调用不会立即执行，直到遇到 collect 或 for 循环这样的消费者才开始计算。这让迭代器既优雅又高效。

第三，遍历 Vec 有三种方式：iter 借用、iter mut 可变借用、into iter 消耗。选择哪种取决于你要不要保留 Vec，要不要修改元素。

第四，HashMap 存储键值对，查询返回 Option，entry 方法让"不存在就插入"变得简洁。集合类型的所有权规则和其他地方完全一致。

下一章我们讲 closure，也就是闭包。你在这一章已经用了很多 closure 了——传给 map 的那个竖线加表达式，传给 filter 的条件函数，都是 closure。下一章会讲清楚 closure 怎么捕获周围的变量，以及这件事和所有权之间的关系。
