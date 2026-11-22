# 自我改进记忆配对实验报告

Self Improvement Memory Paired Experiment Report

本地 Qwen 编程实验与论文对照  |  Local Qwen coding experiments and comparison with the paper

### 主要发现  Main finding

在 10 道留出题的 Qwen3.8:27B 实验中，修正评分后，有笔记组通过 267/500 次（53.4%），无笔记组通过 271/500 次（54.2%）。平均配对差为 −0.8 个百分点，95% 置信区间为 −2.85 至 +1.25 个百分点。这套本地设置未观察到论文报告的稳定收益。

The corrected scores on ten held-out tasks were 267/500 (53.4%) with notes and 271/500 (54.2%) without notes. The mean paired difference was −0.8 percentage points (95% CI −2.85 to +1.25). The local setup did not show the consistent gain reported in the paper.

### 研究问题  Research questions

1. 两组从同一份解题指南出发时，继承并继续记录自我改进记忆（SIM），能提高新题的通过率吗？

1. Starting from the same solving guide, does inheriting and updating Self-Improvement Memory (SIM) improve accuracy on new tasks?

2. 总差距由哪些题推动？允许使用 Python 占位变量 _ 后，结论是否变化？

2. Which tasks drive the overall difference, and does allowing Python's underscore placeholder change the conclusion?

3. 本地的题集、优化预算和可修改范围，与论文有何差异？记录支持哪些解释？

3. How do the tasks, optimization budget and editable workflow differ from the paper, and which explanations are supported by the records?

### 笔记如何影响答题  How notes affect solving

SIM 记录问题根因、采纳的改法、修改理由、预计与实际效果。提案者和选择者阅读笔记，决定如何修改流程。解题模型只接收题目和当前指南，模型权重固定。

SIM records recurring problems, accepted edits, their rationale, and predicted and observed results. The proposer and selector consult it when editing the workflow. The solver receives the task and current guide. Model weights stay fixed.

## 实验设计与执行过程

Design and execution

### 每一对如何运行  How each pair was run

① 用两道源题改进初始指南，保存最终指南和源笔记。② 从同一份指南分出两组，用两道不同的目标题继续优化。有笔记组继承并更新 SIM，两组均保留目标阶段的常规修改历史。③ 固定两份最终指南后，各自在相同的留出题上作答。评分程序要求全部测试用例通过。

① Optimize the initial guide on two source tasks and save the retained guide and source notes. ② Fork from that guide into two branches and optimize on two target tasks. The SIM branch inherits and updates notes. Both branches keep their ordinary target-stage edit history. ③ Evaluate the two retained guides on identical held-out tasks. An answer passes only when it passes all verifier cases.

本地使用 10 个独立源起点。源与目标各优化 2 轮，每轮 2 个候选，每个候选在每道优化题上试 1 次。解题指南是简短的自然语言提示，答案是单条 Python 表达式。每个分支每道留出题作答 5 次，对应作答使用配对种子。留出结果仅用于计分。

The local study used ten independent source runs. Each stage had two rounds, two candidates per round, and one attempt per candidate per optimization task. The editable guide was a short prompt and the answer was one Python expression. Each branch sampled five answers per held-out task with matched seeds. Held-out results were used for evaluation.

### 从试验到完整评测  From pilot runs to full evaluation

先用 Qwen3.5:4B 测两道留出题，再以相同的小规模设计运行 Qwen3.8:27B。随后保留这两道题，加入八道新题，用 27B 完整重跑十对。扩展版共保存 1,500 次留出作答，其中 500 次是共同起点基线，两个最终分支各 500 次。

Two held-out tasks were used first with Qwen3.5:4B and then with Qwen3.8:27B. The expanded 27B run retained those tasks and added eight new ones. The ten pairs produced 1,500 stored held-out answers, including 500 for the shared starting guides and 500 for each final branch.

扩展版逐次保存作答和评分。运行中断后从已保存的位置继续。完成后核对了十对最终记录、共同起点以及留出题与优化过程的隔离。

The expanded run saved each answer and grade and resumed from checkpoints after interruptions. The final audit checked all ten pairs, their shared starts, and separation of held-out tasks from optimization.

### 后验评分修正  Post hoc scoring correction

原评分规则拒绝所有以下划线开头的变量名，误伤了常见占位变量 _。修正仅放行单个 _。用原隔离环境重评已有的 1,000 份最终答案，保留原始成绩和原先选定的指南。

The original verifier rejected underscore-prefixed names, including the conventional placeholder _. The revision exempted that single name. The 1,000 saved final answers were rescored in the original isolated environment, with the original results and selected guides retained.

## 实验结果

Results

| 条件 / Setting | 有笔记 / SIM | 无笔记 / No SIM | 平均差 / Δ pp |
| --- | --- | --- | --- |
| 4B · 2 题 / tasks | 0/100 · 0.0% | 0/100 · 0.0% | +0.0 |
| 27B · 2 题 / tasks | 4/100 · 4.0% | 5/100 · 5.0% | -1.0 |
| 27B · 10 题 / tasks | 260/500 · 52.0% | 263/500 · 52.6% | -0.6 |
| 27B · 10 题重评 / rescored | 267/500 · 53.4% | 271/500 · 54.2% | -0.8 |

差值为每对的有笔记通过率减无笔记通过率，再在 10 对上取平均。pp 表示百分点。

Δ is the mean of ten within-pair differences in pass rate. pp denotes percentage points.

### 逐题结果  Results by held out task

| 题目 / Task | 有笔记 / SIM | 无笔记 / No SIM | 重评差 / Δ pp |
| --- | --- | --- | --- |
| 众数与平局 / Mode and ties | 3 | 4 | -2 |
| 连续递减段 / Decreasing runs | 0 | 1 → 2 | -4 |
| 前缀和 / Prefix sums | 34 | 34 | +0 |
| 相邻变化下标 / Change indices | 47 | 43 | +8 |
| 最近相同元素 / Nearest match | 5 | 8 | -6 |
| 滑动窗口最大值 / Window max | 31 | 34 | -6 |
| 连续偶数段 / Even runs | 0 → 3 | 1 → 2 | +2 |
| 左右平衡下标 / Balance index | 42 → 45 | 39 → 45 | +0 |
| 仅出现一次 / Unique elements | 50 | 50 | +0 |
| 相同数对计数 / Equal pairs | 48 → 49 | 49 | +0 |

每题每组条件各 50 次作答。箭头表示通过次数由原评分到重评的变化。重评后仍为 2 胜、4 平、4 负。

Each condition had 50 answers per task. Arrows show changes in pass counts after rescoring. SIM still won two pairs, tied four, and lost four.

## 差异来源与结论

Where the difference came from

### 逐题差值  Task level differences

重评后，最近相同元素与滑动窗口最大值各少通过 3 次，合计拉低总通过率 1.2 个百分点。相邻变化下标多通过 4 次，抵消 0.8 个百分点。左右平衡下标原有 3 次优势，放行 _ 后两组均为 45/50。

After rescoring, nearest match and window max each accounted for three fewer passes with SIM, together reducing the overall rate by 1.2 points. Change indices contributed four extra passes, offsetting 0.8 points. Balance index originally favored SIM by three passes and became a 45/50 tie after allowing _.

### 为什么没有复现提升  Why the paper’s gain did not recur

第 1、2、10 组没有可继承的源笔记。有笔记分支有六组沿用源指南，第 3、4、8 组的最终指南在两个分支逐字相同。部分组别重叠。扩大留出题改善了覆盖面，用于形成笔记的优化题仍然很少。

Pairs 1, 2 and 10 had no source notes to inherit. Six SIM branches retained the source guide, and pairs 3, 4 and 8 ended with identical guides across branches. These groups overlap. Adding held-out tasks broadened evaluation, while the optimization set that generated the notes remained small.

论文用 Gemini 3.8 Flash，把 Terminus-2 从 Terminal-Bench 2.1 迁移到 Terminal-Bench 4。每阶段 10 轮，每轮 5 个提案，目标优化和留出各 33 道题。论文可修改实际执行的工作流程，例如增补验收检查。其十对结果为 9 胜 1 负，平均优势为 2.36 个百分点。

The paper used Gemini 3.8 Flash to transfer Terminus-2 from Terminal-Bench 2.1 to Terminal-Bench 4. Each stage used ten rounds and five proposals per round. The target had 33 optimization and 33 held-out tasks. The paper could edit executable workflow behavior, such as completion checks. SIM won nine of ten pairs, with a mean gain of 2.36 points.

本地结果适用于这一模型、这批普通编程题和这套短指南预算。模型、题集和优化范围同时变化，现有记录无法估计各因素的独立影响。已选定的指南是在原评分规则下产生的，重评只修正最终答案的计分。

The local estimate applies to this model, these programming tasks, and this short-guide budget. The model, task set and optimization scope changed together, so their separate effects cannot be estimated here. Guides were selected under the original verifier. Rescoring updates the grades of final answers.

### 来源  Sources

[1] Self-Improvement Memory Enables Continual Recursive Self-Improvement, §§3, 4.4 and Table 3. https://arxiv.org/html/2611.18856v1

[2] 实验依据包括已保存的实验方案、逐次作答、原始成绩、重评成绩与完整性核对记录。

The experiment records include the protocol, individual answers, original and revised scores, and audit results.
