---
id: src-agent
title: Agent 什么时候才有优势
tags: Agent, 学习路径
---

Agent 要解决的是：下一步做什么，要看上一步的结果才能决定。

一条最简单的 Agent 路径是：模型观察当前结果，决定调用哪一个工具，再把工具结果交回模型。

开始做 Agent 之前，最好已经有一个可以跑通的应用，这样才能判断哪一步真的需要分支。

任务步骤事先能写死时，用一条固定流程就够了。任务会分支、并且要调用工具时，Agent 才比固定流程有明显优势。

多 Agent 是把一次判断拆给多个角色。第一条链路还没跑通时，多 Agent 不会让判断变得更可靠。

已经做过可以演示的检索应用、并且准备接到真实业务里时，下一步更值得学的是工具调用和状态，而不是继续横向收集框架。

已经能做出检索演示之后，继续只补充框架名单，并不能覆盖业务链路里的分支。

这时可以只改一个点：在结果会分支的那一步，由模型决定调用哪个工具。

```evidence
id: agent-problem
option: Agent
dimension: 解决的问题
stance: info
quote: 下一步做什么，要看上一步的结果才能决定。
```

```evidence
id: agent-path
option: Agent
dimension: 主路径
stance: info
quote: 一条最简单的 Agent 路径是：模型观察当前结果，决定调用哪一个工具，再把工具结果交回模型。
```

```evidence
id: agent-base
option: Agent
dimension: 前置基础
stance: info
quote: 开始做 Agent 之前，最好已经有一个可以跑通的应用，这样才能判断哪一步真的需要分支。
```

```evidence
id: agent-fit
option: Agent
dimension: 何时更合适
stance: info
quote: 任务会分支、并且要调用工具时，Agent 才比固定流程有明显优势。
```

```evidence
id: agent-later-flow
option: Agent
dimension: 暂时不做
stance: later
quote: 任务步骤事先能写死时，用一条固定流程就够了。
when.prior_ai_project: false
```

```evidence
id: agent-later-multi
option: Agent
dimension: 暂时不做
stance: later
quote: 第一条链路还没跑通时，多 Agent 不会让判断变得更可靠。
when.prior_ai_project: false
```

```evidence
id: agent-start
option: Agent
dimension: 建议
stance: start
quote: 已经做过可以演示的检索应用、并且准备接到真实业务里时，下一步更值得学的是工具调用和状态，而不是继续横向收集框架。
when.prior_ai_project: true
when.goal: production
```

```evidence
id: agent-later-frameworks
option: Agent
dimension: 暂时不做
stance: later
quote: 已经能做出检索演示之后，继续只补充框架名单，并不能覆盖业务链路里的分支。
when.prior_ai_project: true
when.goal: production
```

```evidence
id: agent-next
option: Agent
dimension: 下一步
stance: next
quote: 在结果会分支的那一步，由模型决定调用哪个工具。
when.prior_ai_project: true
when.goal: production
```
