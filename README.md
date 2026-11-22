# SIM 编程配对复现

Self-Improvement Memory in paired local coding experiments

[中英双语实验报告 / Bilingual experiment report](REPORT.md)

最终重评结果为有笔记 **53.4%**、无笔记 **54.2%**，平均配对差 **−0.8 个百分点**。重评使用已保存的答案。

The final rescore was **53.4%** with SIM and **54.2%** without SIM, with a mean paired difference of **−0.8 percentage points**. It used the saved answers.

| 实验 / Experiment | 记录 / Records |
| --- | --- |
| Qwen3.5 4B · 2 道留出题 / held-out tasks | [实验目录 / Directory](experiments/qwen35-4b-2-heldout/) |
| Qwen3.8 27B · 2 道留出题 / held-out tasks | [实验目录 / Directory](experiments/qwen38-27b-2-heldout/) |
| Qwen3.8 27B · 10 道留出题 / held-out tasks | [实验目录 / Directory](experiments/qwen38-27b-10-heldout/) |
| 允许单个下划线后的重评 / Rescore allowing the underscore placeholder | [汇总 / Summary](experiments/qwen38-27b-10-heldout/results/regrade-allow-underscore/summary.json) · [逐次结果 / Trial scores](experiments/qwen38-27b-10-heldout/results/regrade-allow-underscore/final_trials.csv) |

每个实验目录含题目与评分规则、配对流程、实验参数和已有核验结果。各目录的 results/observations.sqlite 是完整事件库，含优化过程、生成的答案和评分。扩展实验另附去除本机路径后的日志、暂停记录和重评脚本。逐次通过情况见各目录的 results/final_trials.csv。

Each directory includes the tasks, verifier, paired runner, protocol, and existing audit. Its results/observations.sqlite contains the full event history, including optimization, generated answers, and grades. The expanded run also includes logs with local paths removed, pause records, and the rescoring script. Trial-level outcomes are in results/final_trials.csv.

[论文 / Paper](https://arxiv.org/abs/2611.18856)
