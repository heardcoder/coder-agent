---
id: web-loop-engineering
title: Loop Engineering（循环工程） | 菜鸟教程
tags: loop engineering
url: https://www.runoob.com/ai-agent/loop-engineering.html
---

Loop Engineering（循环工程） | 菜鸟教程 前 --> 菜鸟教程 -- 学的不仅是技术，更是梦想！ 首页 HTML JavaScript CSS Vue React Python3 Java C C++ C# AI Go SQL Linux VS Code Bootstrap Git 本地书签 首页 HTML CSS JS 本地书签 搜索 Vue3 教程 Vue2 教程 Bootstrap3 Bootstrap4 Bootstrap5 机器学习 PyTorch TensorFlow Sklearn NLP AI Agent Ollama Coding Plan AI Agent 教程 AI Agent(智能体) 教程 AI Agent 简介 AI Agent 核心组件 AI Agent 术语 AI Agent 工作原理 AI 底层架构 大语言模型基础 大模型多模态 提示词工程 Token (词元) 推理与规划 向量数据库 RAG 与知识检索 Agent 上下文工程 Agent 架构 智能体工具 第一个 AI Agent OpenClaw (Clawdbot) 教程 OpenClaw 快速上手 QoderWork 教程 QoderWake 教程 WorkBuddy 入门教程 AI 工作流 CrewAI 构建智能体 LangChain 制作智能体 LangGraph 入门教程 Deep Agents 入门教程 GraphRAG 入门教程 Harness Engineering Hermes Agent Loop Engineering Vibe Coding Dify 入门教程 n8n 入门教程 Pi Coding Agent AI 3D (Blender) Python 实现智能体 Python 实现 AI Agent 工具调用 记忆系统 Python 智能体环境配置 AI Agent 问答实例 推理与规划 RAG 与知识检索 多智能体系统 工具与外部集成 多模态 Agent 评估、安全与对齐 生产部署与工程化 垂直应用场景 Hugging Face Transformers GraphRAG 入门教程 AI Agent 术语 Loop Engineering（循环工程） Loop Engineering（循环工程）是 2026 年 6 月在 AI 编程社区迅速传播的一个新概念，由 Google 工程师 Addy Osmani 系统整理，Anthropic Claude Code 负责人 Boris Cherny 和开发者 Peter Steinberger 分别在公开场合提出了相同的观点。 本文将带你从零理解什么是 Loop Engineering、它与 Prompt Engineering 的本质区别、构成一个完整 Agent Loop 的六大要素，以及如何设计自己的第一个可运行的 Loop。 AI 工程的演进过程 过去两年，AI 开发的重点正在不断变化：从研究如何写好提示词（Prompt），逐步发展到组织上下文（Context）、编排工具与流程（Harness），再到构建能够自主运行、持续交付结果的循环系统（Loop）。 Prompt：怎么问 AI ↓ Context：给 AI 什么信息 ↓ Harness：如何组织 AI 的能力 ↓ Loop：如何让 AI 持续创造结果 工程阶段 核心思想 关注点 输入内容 AI 能力 人的角色 典型场景 Prompt Engineering（提示词工程） 通过设计提示词获得更好的输出 怎么问问题 Prompt / 指令 单轮生成 提问者 聊天、写作、代码生成 Context Engineering（上下文工程） 组织并提供完整背景信息 给 AI 什么信息 知识库、历史记录、约束条件、上下文 上下文理解 信息组织者 RAG、AI 搜索、代码助手 Harness Engineering（编排工程） 连接模型、工具、数据形成工作流 如何调用能力 上下文 + API + 工具链 执行任务 系统设计者 Agent、自动化流程、多工具协同 Loop Engineering（循环工程） 构建目标驱动的自主闭环系统 如何持续完成目标 目标、状态、记忆、验证机制 规划 → 执行 → 验证 → 修复 → 持续运行 规则制定者 Claude Code、AI 编程、自动运营、AI 员工 Loop Engineering 的起源 Loop Engineering 的出现有一个清晰的时间节点：2026 年 6 月。 引爆点：两句话，百万次转发 2026 年 6 月初，Anthropic Claude Code 负责人 Boris Cherny 在一次公开演讲中说道： "I don't prompt Claude anymore. I have loops running. They're the ones prompting Claude and figuring out what to do. My job is to write loops." （我不再直接提示 Claude 了。我有一套 Loop 在运行，它们负责提示 Claude 并决定下一步做什么。我的工作是编写 Loop。） 几天后，2026 年 6 月 7 日，开发者 Peter Steinberger ——开源 AI Agent 项目 OpenClaw（GitHub 历史上获星最快的新仓库）的创作者——发了一条十二个字的推文： "You shouldn't be prompting coding agents anymore. You should be designing loops that prompt your agents." （你不应该再手动提示 AI 编程助手了。你应该设计让 Agent 自己提示自己的 Loop。） Prompt Engineering 是「教 AI 怎么做」 Loop Engineering 是「设计一个系统，让 AI 自己持续做」 这两句话在 AI 开发者社区引发了巨大的讨论，因为它们精准地描述了一种很多人已经感受到但尚未命名的趋势： 提示词写得好不好，已经不是瓶颈了；瓶颈在于你为 Agent 设计的整套运行系统 。 随后，Addy Osmani 在 Substack 发表了长文，将这一实践正式命名并系统化为 Loop Engineering ，使其成为独立的工程学科。 背景：AI 编程工具的三代演进 Loop Engineering 并非凭空而来，它是 AI 编程工具能力演进的自然结果。 阶段 代表工具 工作方式 瓶颈 第一代：自动补全 GitHub Copilot 早期版本 补全当前行或函数，人类主导所有决策 只能辅助，不能自主 第二代：对话式 ChatGPT、Claude.ai 问一句，答一句，人类手动推进每一步 人类成为瓶颈，速度受限于打字速度 第三代：Agent 自主循环 Claude Code、OpenAI Codex Agent Agent 自主规划、执行、验证，循环迭代直到完成 如何设计让 Loop 可靠运行的系统 第三代工具的出现意味着，工程师的核心竞争力从会写提示词变成了会设计 Loop。 什么是 Loop Engineering Loop Engineering 是设计、运营和持续改进反馈循环的工程实践，这些循环使 AI 编程 Agent 能够自主完成规划、执行代码修改、观察结果并在多轮迭代中完成任务。 用一句话概括： Loop Engineering 是把你从"提示 Agent 的人"变成"设计提示 Agent 的系统"的工程师。 什么是 Loop（循环） 一个 Loop 是一个递归目标系统：你定义一个目的，Agent 不断迭代，直到工作真正完成。 每个 Agent 在执行任务时已经内置了一个"内循环"：感知（Perceive）→ 推理（Reason）→ 行动（Act）→ 观察（Observe），然后再次循环。 Loop Engineering 工作在这个内循环的 上一层 ： 层级 谁在驱动 做什么 内循环（Agent 内置） Agent 自身 读文件 → 修改代码 → 运行测试 → 读错误 → 再修改 外循环（你来设计） 你设计的系统 按计划发现任务 → 分派 Agent → 验证结果 → 记录状态 → 开启下一轮 你不再坐在 Agent 旁边，为每一步打下一条指令。你在设计一套外部系统，它替你驾驶内循环，而你去做更有判断价值的事。 Loop Engineering 与 Prompt Engineering 的区别 维度 Prompt Engineering Loop Engineering 优化对象 你手写的单条指令 自动决定"提示什么、什么时候提示、结果是否可接受"的整套系统 工作单位 一次你手动输入的对话轮次 跨越多轮次、自动运行的完整工作流 成功衡量 第一个回复的质量 最终输出的结果质量 失败模式 模型给出了一个差劲的回答 系统的 Loop 设计不良：循环太早停止、忽视错误信号、无法验证完成 对 Agent 的视角 你手持的工具 你调度的长期运行进程 Prompt Engineering 并没有消亡。一个 Loop 是由多个 Prompt 组成的，写得差的 Prompt 放进 Loop 里只会让糟糕的工作以更快的速度产出。Loop Engineering 是在 Prompt Engineering 之上的层次，而不是替代它。 三个层次的完整技术栈： 层次 优化的是什么 工作单位 Pr

```evidence
id: web-loop-engineering-1
option: loop engineering
dimension: 资料原句
stance: info
quote: Loop Engineering（循环工程） | 菜鸟教程 前 --> 菜鸟教程 -- 学的不仅是技术，更是梦想！
```

```evidence
id: web-loop-engineering-2
option: loop engineering
dimension: 资料原句
stance: info
quote: 本文将带你从零理解什么是 Loop Engineering、它与 Prompt Engineering 的本质区别、构成一个完整 Agent Loop 的六大要素，以及如何设计自己的第一个可运行的 Loop。
```

```evidence
id: web-loop-engineering-3
option: loop engineering
dimension: 资料原句
stance: info
quote: ） Prompt Engineering 是「教 AI 怎么做」 Loop Engineering 是「设计一个系统，让 AI 自己持续做」 这两句话在 AI 开发者社区引发了巨大的讨论，因为它们精准地描述了一种很多人已经感受到但尚未命名的趋势： 提示词写得好不好，已经不是瓶颈了；瓶颈在于你为 Agent 设计的整套运行系统 。
```

```evidence
id: web-loop-engineering-4
option: loop engineering
dimension: 资料原句
stance: info
quote: 随后，Addy Osmani 在 Substack 发表了长文，将这一实践正式命名并系统化为 Loop Engineering ，使其成为独立的工程学科。
```

```evidence
id: web-loop-engineering-5
option: loop engineering
dimension: 资料原句
stance: info
quote: 背景：AI 编程工具的三代演进 Loop Engineering 并非凭空而来，它是 AI 编程工具能力演进的自然结果。
```

```evidence
id: web-loop-engineering-6
option: loop engineering
dimension: 资料原句
stance: info
quote: 什么是 Loop Engineering Loop Engineering 是设计、运营和持续改进反馈循环的工程实践，这些循环使 AI 编程 Agent 能够自主完成规划、执行代码修改、观察结果并在多轮迭代中完成任务。
```

```evidence
id: web-loop-engineering-7
option: loop engineering
dimension: 资料原句
stance: info
quote: 用一句话概括： Loop Engineering 是把你从"提示 Agent 的人"变成"设计提示 Agent 的系统"的工程师。
```

```evidence
id: web-loop-engineering-8
option: loop engineering
dimension: 资料原句
stance: info
quote: Loop Engineering 是在 Prompt Engineering 之上的层次，而不是替代它。
```
