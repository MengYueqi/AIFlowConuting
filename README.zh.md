# AIFlowConuting（中文）

[English](README.md)

AIFlowConuting 是一款个人账本助手，能够对支付宝/微信账单进行标准化处理，依靠本地大模型为每笔交易打上分类标签，并产出月度 Markdown 报告。该项目基于 Vibe Coding 打造，并感谢 Codex 在迭代过程中的支持。

## 功能特点
- **数据清洗**：`TransactionDataProcessor` 读取支付宝和微信的 CSV 导出，只保留明确的“收入/支出”记录。
- **大模型打标**：`process_and_annotate.py` 调用本地 Ollama 模型（默认 `qwen-32b`）对每条记录分类，并记录日志。
- **报告生成**：`generate_report.py` 将标注后的 CSV 汇总成 Markdown 报告，包含总览、分类表格以及支出 Top 10。
- **人工校准流程**：先生成并打标交易，允许人工校对后再生成报告。

## 快速开始
1. **安装依赖**
   - Python 3.8+
   - [Ollama](https://ollama.ai) 以及配置的模型（见 `config.json`，默认 `qwen-32b`）
   - 若后续引入第三方库，可通过 `pip install -r requirements.txt` 安装（目前仅用标准库）

2. **准备数据**
   - 将支付宝、微信账单 CSV 放入 `data/<month>/`。
   - 编辑 `config.json`，配置源文件路径、`report_time` 以及 Ollama 模型/执行路径。

3. **标准化并打标**
   ```bash
   PYTHONPATH=src python3 src/process_and_annotate.py --config config.json
   ```
   生成 `data/processed/transaction-{report_time}.csv`，可按需人工调整。

4. **生成报告**
   ```bash
   PYTHONPATH=src python3 src/generate_report.py --config config.json
   ```
   在 CSV 同目录下产出 `{report_time}月报.md`（可通过 `--output` 自定义路径）。

## 项目结构
- `src/data_management/` – CSV 标准化逻辑
- `src/model/` – Ollama 打标工具
- `src/process_and_annotate.py` – 标准化 + 打标 CLI
- `src/analyze/` 与 `src/generate_report.py` – Markdown 报告生成
- `data/` – 原始账单与处理结果

## 致谢
项目基于 Vibe Coding 工作流完成，特别感谢 Codex 在迭代和代码生成方面的持续帮助。
