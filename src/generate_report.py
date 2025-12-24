"""Generate markdown report from already annotated transactions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from analyze.report_generator import TransactionReportGenerator, render_markdown


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


def write_report(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate markdown report from annotated transactions",
    )
    parser.add_argument("--config", default="config.json", help="Path to config JSON")
    parser.add_argument(
        "--output",
        help="Optional path to override report output (default: report_time月报.md next to CSV)",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    config = load_config(config_path)

    csv_path = resolve_transactions_path(config_path, config)
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Annotated transactions not found: {csv_path}. Run process_and_annotate.py first."
        )

    generator = TransactionReportGenerator(csv_path)
    report_data = generator.generate()
    markdown = render_markdown(report_data)

    report_time = report_data.report_time or config.get("metadata", {}).get("report_time", "report")
    default_report = csv_path.parent / f"{report_time}月报.md"
    report_path = Path(args.output) if args.output else default_report

    write_report(report_path, markdown)
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
