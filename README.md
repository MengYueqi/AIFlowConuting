# AIFlowConuting

English (default) | [中文](README.zh.md)

AIFlowConuting is a personal bookkeeping assistant that normalizes Alipay/WeChat statements, annotates each transaction via local LLMs, and produces month-end markdown reports. Built in a Vibe Coding environment and proudly refined with help from Codex.

## Features
- **Data normalization** – `TransactionDataProcessor` ingests heterogeneous CSV exports from Alipay and WeChat, keeping only clear income/expense records.
- **LLM-assisted tagging** – `process_and_annotate.py` calls a local Ollama model (default `qwen-32b`) to classify spending categories and logs every annotation.
- **Report generation** – `generate_report.py` summarizes the annotated CSV into a markdown report with overview stats, category tables, and the top 10 expenses.
- **Manual review flow** – normalization and annotation run first so you can manually correct the CSV before producing the final report.

## Getting Started
1. **Install dependencies**
   - Python 3.8+
   - [Ollama](https://ollama.ai) with the configured model (see `config.json`, default `qwen-32b`)
   - `pip install -r requirements.txt` if future dependencies are added (currently standard library only)

2. **Prepare data**
   - Place Alipay/WeChat CSV exports under `data/<month>/`.
   - Edit `config.json` to point to the source files, set `report_time`, and confirm the Ollama model/executable.

3. **Normalize & annotate**
   ```bash
   PYTHONPATH=src python3 src/process_and_annotate.py --config config.json
   ```
   This creates `data/processed/transaction-{report_time}.csv`. Review/edit the file as needed.

4. **Generate the report**
   ```bash
   PYTHONPATH=src python3 src/generate_report.py --config config.json
   ```
   Produces `{report_time}月报.md` next to the CSV (override path with `--output`).

## Project Structure
- `src/data_management/` – CSV normalization logic
- `src/model/` – Ollama annotation utilities
- `src/process_and_annotate.py` – CLI pipeline for normalization + annotation
- `src/analyze/` & `src/generate_report.py` – Markdown report generation
- `data/` – Raw statements and processed outputs

## Acknowledgements
Developed in a Vibe Coding workflow, with special thanks to Codex for iterative guidance and code generation support.
