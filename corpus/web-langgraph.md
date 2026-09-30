---
id: web-langgraph
title: LangGraph - LangChain 框架
tags: LangGraph
---

LangGraph - LangChain 框架 跳到内容 我们正在为 LangChain、LangGraph 和 LangSmith 招聘多个职位，团队正在壮大。 加入我们！ LangGraph LangGraph 正在初始化搜索 GitHub 指南 参考 示例 资源 LangGraph GitHub 指南 指南 入门 入门 快速入门 LangGraph 基础 部署 预构建智能体 预构建智能体 概述 运行智能体 流式传输 模型 工具 MCP 集成 上下文 记忆 人机协作 多智能体 评估 部署 用户界面 LangGraph 框架 LangGraph 框架 智能体架构 图 流式传输 持久化 记忆 人机协作 断点 时间回溯 工具 子图 多智能体 函数式 API LangGraph 平台 LangGraph 平台 概述 入门 组件 数据管理 身份验证与访问控制 助手 线程 运行 流式传输 人机协作 断点 时间回溯 MCP 重复发送 Webhook Cron 作业 服务器定制 部署 参考 示例 资源 目录 入门 核心优势 LangGraph 的生态系统 更多资源 致谢 LangGraph LangGraph 是一个低级别的编排框架，用于构建、管理和部署长时间运行、有状态的智能体，受到 Klarna、Replit、Elastic 等塑造智能体未来的公司的信任。 入门 ¶ 安装 LangGraph pip install -U langgraph 然后， 使用预构建组件 创建智能体 # pip install -qU "langchain[anthropic]" to call the model from langgraph.prebuilt import create_react_agent def get_weather ( city : str ) -> str : """Get weather for a given city.""" return f "It's always sunny in { city } !" agent = create_react_agent ( model = "anthropic:claude-3-7-sonnet-latest" , tools = [ get_weather ], prompt = "You are a helpful assistant" ) # Run the agent agent . invoke ( { "messages" : [{ "role" : "user" , "content" : "what is the weather in sf" }]} ) 更多信息请参见 快速入门 。或者，要了解如何构建具有可定制架构、长期记忆和其他复杂任务处理能力的 智能体工作流 ，请参见 LangGraph 基础教程 。 核心优势 ¶ LangGraph 为*任何*长时间运行、有状态的工作流或智能体提供底层支持基础设施。LangGraph 不抽象提示或架构，并提供以下核心优势： 持久执行 ：构建能够抵御故障并长时间运行的智能体，可从上次中断的地方自动恢复。 人机协作 ：在执行的任何时间点检查和修改智能体状态，无缝地融入人工监督。 全面记忆 ：创建真正有状态的智能体，既具备用于持续推理的短期工作记忆，也具备跨会话的长期持久记忆。 使用 LangSmith 进行调试 ：利用可视化工具深入了解复杂的智能体行为，这些工具可以追踪执行路径、捕获状态转换并提供详细的运行时指标。 生产就绪部署 ：利用可扩展的基础设施，自信地部署复杂的智能体系统，该基础设施旨在处理有状态、长时间运行工作流的独特挑战。 LangGraph 的生态系统 ¶ 虽然 LangGraph 可以独立使用，但它也能与任何 LangChain 产品无缝集成，为开发人员提供构建智能体所需的全套工具。为了改进您的 LLM 应用程序开发，请将 LangGraph 与以下产品搭配使用： LangSmith — 有助于智能体评估和可观察性。调试性能不佳的 LLM 应用程序运行、评估智能体轨迹、在生产环境中获得可见性，并随着时间的推移提高性能。 LangGraph 平台 — 使用专为长时间运行、有状态工作流设计的部署平台，轻松部署和扩展智能体。在团队之间发现、重用、配置和共享智能体 — 并在 LangGraph Studio 中通过可视化原型快速迭代。 LangChain – 提供集成和可组合组件，以简化 LLM 应用程序开发。 注意 正在寻找 LangGraph 的 JS 版本？请参阅 JS 仓库 和 JS 文档 。 更多资源 ¶ 指南 ：关于流式传输、添加记忆与持久化以及设计模式（例如分支、子图等）的快速、可操作的代码片段。 参考 ：关于核心类、方法、如何使用图和检查点 API 以及更高级的预构建组件的详细参考。 示例 ：LangGraph 入门的引导式示例。 LangChain 学院 ：通过我们免费的结构化课程学习 LangGraph 的基础知识。 模板 ：用于常见智能体工作流（例如 ReAct 智能体、记忆、检索等）的预构建参考应用程序，可以克隆和适配。 案例研究 ：了解行业领导者如何使用 LangGraph 大规模交付 AI 应用程序。 致谢 ¶ LangGraph 的灵感来源于 Pregel 和 Apache Beam 。其公共接口借鉴了 NetworkX 。LangGraph 由 LangChain 的创建者 LangChain Inc. 构建，但可以独立于 LangChain 使用。 返回顶部 下一步 快速入门 版权所有 © 2025 LangChain, Inc | 同意偏好 使用 Material for MkDocs 构建 Cookie 同意 我们使用 Cookie 来识别您的重复访问和偏好，并衡量我们文档的有效性以及用户是否找到了他们正在搜索的内容。 点击“接受”将使我们的文档变得更好。谢谢！ ❤️ GitHub 接受 拒绝

```evidence
id: web-langgraph-1
option: LangGraph
dimension: 资料原句
stance: info
quote: LangGraph - LangChain 框架 跳到内容 我们正在为 LangChain、LangGraph 和 LangSmith 招聘多个职位，团队正在壮大。
```

```evidence
id: web-langgraph-2
option: LangGraph
dimension: 资料原句
stance: info
quote: 入门 ¶ 安装 LangGraph pip install -U langgraph 然后， 使用预构建组件 创建智能体 # pip install -qU "langchain[anthropic]" to call the model from langgraph.
```

```evidence
id: web-langgraph-3
option: LangGraph
dimension: 资料原句
stance: info
quote: 或者，要了解如何构建具有可定制架构、长期记忆和其他复杂任务处理能力的 智能体工作流 ，请参见 LangGraph 基础教程 。
```

```evidence
id: web-langgraph-4
option: LangGraph
dimension: 资料原句
stance: info
quote: 核心优势 ¶ LangGraph 为*任何*长时间运行、有状态的工作流或智能体提供底层支持基础设施。
```

```evidence
id: web-langgraph-5
option: LangGraph
dimension: 资料原句
stance: info
quote: LangGraph 不抽象提示或架构，并提供以下核心优势： 持久执行 ：构建能够抵御故障并长时间运行的智能体，可从上次中断的地方自动恢复。
```

```evidence
id: web-langgraph-6
option: LangGraph
dimension: 资料原句
stance: info
quote: LangGraph 的生态系统 ¶ 虽然 LangGraph 可以独立使用，但它也能与任何 LangChain 产品无缝集成，为开发人员提供构建智能体所需的全套工具。
```

```evidence
id: web-langgraph-7
option: LangGraph
dimension: 资料原句
stance: info
quote: 为了改进您的 LLM 应用程序开发，请将 LangGraph 与以下产品搭配使用： LangSmith — 有助于智能体评估和可观察性。
```

```evidence
id: web-langgraph-8
option: LangGraph
dimension: 资料原句
stance: info
quote: LangGraph 平台 — 使用专为长时间运行、有状态工作流设计的部署平台，轻松部署和扩展智能体。
```
