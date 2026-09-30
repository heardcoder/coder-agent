# CoderAgent：技术研究流程

用户的一段话先拆成问题、选项和背景。研究是一个 ReAct 循环：模型调用 `lookup` 查资料，程序先读本地笔记，没有再联网搜索，并把新页面写回 `corpus/`。建议由模型调用 `submit_advice` 提交，每条都要引用这次读到的原句；不合格会把原因送回下一轮。最多 6 轮。

默认模型是 `deepseek-flash`，也就是 DeepSeek-V4.1-Flash。密钥只在执行命令时通过 `--api-key` 传入，不写入文件，也不从环境变量读取。调用时会把请求参数和响应摘要打到标准错误，其中不含密钥。

## 运行

```bash
cd coderagent
python3 -m coderagent --api-key sk-你的密钥 \
  "我有 Python 和后端开发经验，每周大约 8 小时，还没做过 AI 项目，想先做个能演示的应用。应该先学习 RAG 还是 Agent？"
python3 -m unittest discover -s tests
```

不带参数、在终端里运行时，会提示你输入这段话。模型先把它拆成问题、选项和背景；没说清的字段会停下来，不会编一个默认值。

要看着步骤走，可以开本地页面。进度用 SSE 推送，做完一步显示一步：

```bash
python3 -m coderagent --web --api-key sk-你的密钥
```

浏览器打开 `http://127.0.0.1:8765`。密钥仍只在启动命令里传入。

已经拆好的 JSON 仍可以用 `--request` 直接跑，例如 `examples/rag_vs_agent.json`。研究和拆解都会请求模型，所以需要传入密钥。

## 输入

用户的一段话会被拆成：

- `question`：要回答的问题
- `options`：明确在比较的 2 到 3 个选项，也是检索标签
- `profile`：背景、是否做过 AI 项目、目标（`demo` 或 `production`）、每周小时数

## 语料

`corpus/` 是项目自己的学习笔记。每条证据的 `quote` 必须能在笔记正文里原样找到，对不上的证据在调用模型前就会被丢掉。
