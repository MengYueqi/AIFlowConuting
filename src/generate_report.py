"""Generate markdown report from already annotated transactions via LLM."""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
from pathlib import Path
from typing import Tuple

from analyze.report_generator import TransactionReportGenerator, format_report_source


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_transactions_path(config_path: Path, config: dict) -> Path:
    output_cfg = config.get("output", {})
    metadata = config.get("metadata", {})
    if "transactions" not in output_cfg:
        raise ValueError("output.transactions must be configured")
    template = str(output_cfg["transactions"])
    try:
        relative_path = template.format(
            report_time=metadata.get("report_time", ""),
            tag=metadata.get("tag", ""),
        )
    except KeyError as exc:  # pragma: no cover - template misuse
        raise ValueError(f"Unknown placeholder in output template: {exc.args[0]}") from exc
    base_path = config_path.parent
    return (base_path / relative_path).resolve()


def read_model_config(config: dict) -> Tuple[str, str]:
    model_cfg = config.get("model", {})
    if not isinstance(model_cfg, dict):
        raise ValueError("model section in config must be a mapping")
    model_name = str(model_cfg.get("name", "qwen-32b")).strip()
    executable = str(model_cfg.get("executable", "ollama")).strip()
    if not model_name or not executable:
        raise ValueError("model.name and model.executable must be configured")
    return model_name, executable


def load_prompt_template(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding="utf-8")


def build_prompt(template: str, report_time: str, data_block: str) -> str:
    filled = template.replace("YYYY-MM", report_time or "YYYY-MM")
    placeholder = "{在此粘贴你的“总览 / 分类 / Top10 / 可选明细”原文}"
    return filled.replace(placeholder, data_block)


def call_ollama(prompt: str, model_name: str, executable: str) -> str:
    try:
        proc = subprocess.run(
            [executable, "run", model_name],
            input=prompt.encode("utf-8"),
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", "ignore")
        raise RuntimeError(f"Ollama invocation failed: {stderr}") from exc
    return proc.stdout.decode("utf-8", "ignore").strip()


def write_report(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate markdown report from annotated transactions via LLM",
    )
    parser.add_argument("--config", default="config.json", help="Path to config JSON")
    parser.add_argument(
        "--output",
        help="Optional path to override report output (default: report_time月报.md next to CSV)",
    )
    parser.add_argument(
        "--prompt",
        default="report/prompt.txt",
        help="Path to the LLM prompt template (default: report/prompt.txt)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logging.info("Starting report generation")

    config_path = Path(args.config)
    config = load_config(config_path)

    logging.info("Resolving transactions CSV path")
    csv_path = resolve_transactions_path(config_path, config)
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Annotated transactions not found: {csv_path}. Run process_and_annotate.py first."
        )

    logging.info("Parsing annotated transactions from %s", csv_path)
    generator = TransactionReportGenerator(csv_path)
    report_data = generator.generate()
    data_block = format_report_source(report_data)

    report_time = report_data.report_time or config.get("metadata", {}).get("report_time", "report")
    prompt_template_path = Path(args.prompt)
    logging.info("Loading prompt template from %s", prompt_template_path)
    prompt_template = load_prompt_template(prompt_template_path)
    prompt = build_prompt(prompt_template, report_time, data_block)

    model_name, executable = read_model_config(config)
    logging.info("Invoking Ollama model %s via %s", model_name, executable)
    print(prompt)
    markdown = call_ollama(prompt, model_name, executable)

    default_report = csv_path.parent / f"{report_time}月报.md"
    report_path = Path(args.output) if args.output else default_report

    logging.info("Writing report to %s", report_path)
    write_report(report_path, markdown)
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
