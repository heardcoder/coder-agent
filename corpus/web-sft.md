---
id: web-sft
title: 大模型后训练全解：SFT、RLHF/PPO、DPO 的原理、实践与选择_sft rlhf ppo dpo-CSDN博客
tags: SFT
url: https://blog.csdn.net/u012316485/article/details/160279691
---

大模型后训练全解：SFT、RLHF/PPO、DPO 的原理、实践与选择_sft rlhf ppo dpo-CSDN博客 大模型后训练全解：SFT、RLHF/PPO、DPO 的原理、实践与选择 原创 已于 2026-04-28 14:51:03 修改 · 5.6k 阅读 · 31 · 44 · 本内容遵循CC 4.0 BY-SA版权协议 版权声明：本文为博主原创文章，遵循 CC 4.0 BY-SA 版权协议，转载请附上原文出处链接和本声明。 GEO检测 · 收录于 当前文章被以下社区和专栏收录： 于 2026-04-20 19:58:27 首次发布 本文覆盖范围：SFT 监督微调、RLHF（PPO）强化学习对齐、DPO 直接偏好优化，以及它们的变体、工具链、实战代码和选择决策。结合 InstructGPT、LLaMA 2/3、Zephyr、DeepSeek-R1、Qwen3 等真实案例说明。 一、为什么需要后训练（Post-Training）？ 预训练（Pre-Training）让一个语言模型学会了"下一个 token 是什么"——它掌握了语言规律、广博的世界知识、甚至初步的推理能力。但预训练的优化目标是最大化训练语料的对数似然，这意味着模型学会的是"互联网平均水平的文字接龙"，而不是"对人类有帮助、无害、诚实的回答"。 给一个纯预训练模型发送"帮我写一封道歉信"，它可能会继续生成"帮我写一封道歉信的示例……"或者索性开始胡说八道——因为训练数据里这类格式的文本不少。它不理解"用户"和"助手"的角色关系，不知道什么是有用的回答，也不懂得拒绝有害请求。 后训练（Post-Training）正是解决这个问题的一套流程，其核心目标是： 行为对齐（Behavioral Alignment） ：让模型按照指令行事，而不只是续写文本 偏好对齐（Preference Alignment） ：让模型的输出符合人类的价值偏好（有用、无害、诚实） 能力激活（Capability Activation） ：激发模型在推理、代码、数学等特定领域的潜力 一个完整的后训练历史可以分为三个阶段：第一阶段，InstructGPT 提出了 SFT + RLHF 的标准流程，让模型能够遵循指令，代表模型是 GPT-3.5 和早期 ChatGPT；第二阶段，DPO 通过消除独立奖励模型降低了对齐的复杂度，让中小团队也能做对齐，代表模型是 Zephyr、Intel NeuralChat、早期 LLaMA 微调版本；第三阶段，DeepSeek-R1 证明了纯 RL 能产生突破性推理能力，GRPO 成为标准，代表模型是 DeepSeek-R1、QwQ、Kimi k1.5。 理解这三个阶段，就等于理解了整个后训练技术的演化逻辑。下面我们逐一深入。 二、SFT：监督微调，一切的起点 2.1 什么是 SFT？ SFT（Supervised Fine-Tuning，监督微调）是后训练的第一步，也是最直观的一步：给模型看大量高质量的（指令，回答）对，用标准的交叉熵损失训练模型去模仿这些示范回答。 从优化角度，SFT 的损失函数是： 其中 是指令（prompt）， 是期望的回答， 是模型。这与预训练的语言建模损失在形式上完全一样，差别只在于：SFT 的数据是精心设计的高质量（指令, 回答）对，而且 只在回答部分计算 loss ，不对指令部分计算 loss（让模型学会"如何回答"，而不是"如何提问"）。 这一点在代码上体现为：将指令部分的 token 的 label 设置为 -100（PyTorch 会忽略 label=-100 的位置），只让模型在回答 token 上反向传播。 2.2 SFT 数据的格式 现代大模型的 SFT 数据通常用 ChatML 格式组织多轮对话： <|im_start|>system 你是一个有帮助的助手。<|im_end|> <|im_start|>user 帮我解释一下什么是黑洞。<|im_end|> <|im_start|>assistant 黑洞是宇宙中一种极端的天体，其引力强到连光都无法逃脱……<|im_end|> 这种格式明确区分了系统提示、用户输入和模型回答，让模型学会角色扮演。 2.3 SFT 用在哪些模型中？ Stanford Alpaca（2023） ：最早的开源 SFT 实验之一。用 GPT-3.5 生成的 52K 条指令-回答对，对 LLaMA-7B 做 SFT，就能得到一个基本能对话的模型。成本极低但效果惊人，开启了"用 AI 生成 SFT 数据"的先河。 InstructGPT（OpenAI, 2022） ：SFT 是 RLHF 三阶段流程的第一步。先用人工标注的约 13000 条（prompt, 演示回答）对做 SFT，得到一个基础对话模型，再继续做 RLHF。 LLaMA 2-Chat（Meta, 2023） ：在经过 SFT 预热后，再做 RLHF（迭代式 PPO + 拒绝采样）。SFT 数据来自 Meta 内部的人工标注对话。 DeepSeek-R1-Distill 系列 ：通过对 LLaMA 3 和 Qwen2.5 基座模型，用 DeepSeek-R1 生成的 80 万条长链式推理（CoT）数据做 SFT，直接蒸馏出了具备推理能力的小模型——完全不用 RL。这说明 SFT 在数据质量足够高时，能够有效传递大模型的推理模式。 2.4 SFT 的局限性 SFT 的本质是 模仿学习（Imitation Learning） ，它有两个根本局限： 第一，覆盖范围限于训练数据 。模型只能学到训练数据中展示过的行为模式。对于训练数据没有涉及的新场景，SFT 模型的泛化能力有限。 第二，无法表达"哪个更好" 。SFT 给模型展示的是"正确"答案，但没有展示"哪种正确答案更好"。对于同一个问题，简洁清晰的回答和冗长啰嗦的回答，在 SFT 的 loss 里差别不大——只要都是"正确"的。 第二个局限正是 RLHF 和 DPO 要解决的问题。 2.5 用 TRL 的 SFTTrainer 做实战 HuggingFace TRL 库提供了 SFTTrainer ，封装了 SFT 的完整流程： from datasets import load_dataset from transformers import AutoModelForCausalLM, AutoTokenizer from trl import SFTConfig, SFTTrainer from peft import LoraConfig # 加载基础模型 model = AutoModelForCausalLM.from_pretrained( "Qwen/Qwen2.5-7B", torch_dtype="auto", device_map="auto" ) tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-7B") # LoRA 配置：只训练部分参数，节省显存 lora_config = LoraConfig( r=64, lora_alpha=128, target_modules=["q_proj", "v_proj", "k_proj", "o_proj", "gate_proj", "up_proj", "down_proj"], lora_dropout=0.05, bias="none", task_type="CAUSAL_LM" ) # 加载对话数据集（ChatML 格式） dataset = load_dataset("trl-lib/Capybara", split="train") # SFT 训练配置 sft_config = SFTConfig( output_dir="./sft_output", num_train_epochs=3, per_device_train_batch_size=2, gradient_accumulation_steps=8, learning_rate=2e-4, warmup_ratio=0.03, lr_scheduler_type="cosine", bf16=True, logging_steps=10, save_steps=500, max_length=2048, # 关键：只在 assistant 的回答部分计算 loss dataset_text_field="messages", ) trainer = SFTTrainer( model=model, args=sft_config, train_dataset=dataset, peft_config=lora_config, tokenizer=tokenizer, ) trainer.train() trainer.save_model("./sft_final") 对于自定义数据集，数据格式需要包含 messages 字段，每条样本是一个对话列表： # 自定义数据集格式 { "messages": [ {"role": "system", "content": "你是一个专业的法律顾问。"}, {"role": "user", "content": "合同违约怎么处理？"}, {"role": "assistant", "content": "合同违约的处理方式包括……"} ] } TRL 的 SFTTrainer 会自动检测对话格式，应用对应的 chat template，并将 assis

```evidence
id: web-sft-1
option: SFT
dimension: 资料原句
stance: info
quote: 大模型后训练全解：SFT、RLHF/PPO、DPO 的原理、实践与选择_sft rlhf ppo dpo-CSDN博客 大模型后训练全解：SFT、RLHF/PPO、DPO 的原理、实践与选择 原创 已于 2026-04-28 14:51:03 修改 · 5.
```

```evidence
id: web-sft-2
option: SFT
dimension: 资料原句
stance: info
quote: GEO检测 · 收录于 当前文章被以下社区和专栏收录： 于 2026-04-20 19:58:27 首次发布 本文覆盖范围：SFT 监督微调、RLHF（PPO）强化学习对齐、DPO 直接偏好优化，以及它们的变体、工具链、实战代码和选择决策。
```

```evidence
id: web-sft-3
option: SFT
dimension: 资料原句
stance: info
quote: 二、SFT：监督微调，一切的起点 2.
```

```evidence
id: web-sft-4
option: SFT
dimension: 资料原句
stance: info
quote: SFT（Supervised Fine-Tuning，监督微调）是后训练的第一步，也是最直观的一步：给模型看大量高质量的（指令，回答）对，用标准的交叉熵损失训练模型去模仿这些示范回答。
```

```evidence
id: web-sft-5
option: SFT
dimension: 资料原句
stance: info
quote: 从优化角度，SFT 的损失函数是： 其中 是指令（prompt）， 是期望的回答， 是模型。
```

```evidence
id: web-sft-6
option: SFT
dimension: 资料原句
stance: info
quote: 这与预训练的语言建模损失在形式上完全一样，差别只在于：SFT 的数据是精心设计的高质量（指令, 回答）对，而且 只在回答部分计算 loss ，不对指令部分计算 loss（让模型学会"如何回答"，而不是"如何提问"）。
```

```evidence
id: web-sft-7
option: SFT
dimension: 资料原句
stance: info
quote: 2 SFT 数据的格式 现代大模型的 SFT 数据通常用 ChatML 格式组织多轮对话： <|im_start|>system 你是一个有帮助的助手。
```

```evidence
id: web-sft-8
option: SFT
dimension: 资料原句
stance: info
quote: Stanford Alpaca（2023） ：最早的开源 SFT 实验之一。
```
