---
id: src-rag
title: RAG 解决什么问题
tags: RAG, 学习路径
---

RAG 要解决的是：回答必须依赖一组你提供的资料，而不是只靠模型自己的记忆。

一条 RAG 链路通常是：把文档切分，检索相关片段，把片段交给模型，再生成答案。

做过后端开发的人，已经熟悉请求、数据和返回。还没做过检索或 Agent 时，这条链路的输入输出仍然比较固定，更容易在几周内做成一个可以演示的程序。

输入输出比较固定、又想先看到一个完整程序时，RAG 比 Agent 更合适。

资料如果是自己的技术笔记，第一步适合做成带引用的问答，并且每个回答都要回到笔记里的原句。

```evidence
id: rag-problem
option: RAG
dimension: 解决的问题
stance: info
quote: 回答必须依赖一组你提供的资料，而不是只靠模型自己的记忆。
```

```evidence
id: rag-path
option: RAG
dimension: 主路径
stance: info
quote: 一条 RAG 链路通常是：把文档切分，检索相关片段，把片段交给模型，再生成答案。
```

```evidence
id: rag-base
option: RAG
dimension: 前置基础
stance: info
quote: 做过后端开发的人，已经熟悉请求、数据和返回。
```

```evidence
id: rag-fit
option: RAG
dimension: 何时更合适
stance: info
quote: 输入输出比较固定、又想先看到一个完整程序时，RAG 比 Agent 更合适。
```

```evidence
id: rag-start
option: RAG
dimension: 建议
stance: start
quote: 还没做过检索或 Agent 时，这条链路的输入输出仍然比较固定，更容易在几周内做成一个可以演示的程序。
when.prior_ai_project: false
when.goal: demo
```

```evidence
id: rag-next
option: RAG
dimension: 下一步
stance: next
quote: 第一步适合做成带引用的问答，并且每个回答都要回到笔记里的原句。
when.prior_ai_project: false
when.goal: demo
```
