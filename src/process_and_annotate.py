"""Pipeline script: normalize CSV exports then annotate each record via Ollama."""

from __future__ import annotations

import argparse
import csv
import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import List, Mapping, Tuple

from data_management.transactions import TransactionDataProcessor, TransactionRecord
from model.annotator import OllamaAnnotationError, TransactionCategoryAnnotator

ANNOTATION_FIELDS = ("category_id", "category_name", "category_reason")


def run_pipeline(config_path: Path) -> Path:
    """Run normalization + annotation, returning the path to the updated CSV."""
    config = _load_config(config_path)
    processor = TransactionDataProcessor(config, base_path=config_path.parent)
    records = processor.process()

    model_name, model_exec = _read_model_config(config)
    annotator = TransactionCategoryAnnotator(model=model_name, executable=model_exec)
    annotated_rows = _annotate_records(records, annotator)

    output_path = processor.last_output_path
    if not output_path:
        raise RuntimeError("Processor did not provide an output path")
    _write_annotated_csv(output_path, annotated_rows)
    return output_path


def _load_config(config_path: Path) -> Mapping[str, object]:
    with config_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _read_model_config(config: Mapping[str, object]) -> Tuple[str, str]:
    model_cfg = config.get("model", {})
    if not isinstance(model_cfg, Mapping):
        raise ValueError("model section in config must be a mapping")
    model_name = str(model_cfg.get("name", "qwen-32b")).strip()
    executable = str(model_cfg.get("executable", "ollama")).strip()
    if not model_name:
        raise ValueError("model.name must be configured")
    if not executable:
        raise ValueError("model.executable must be configured")
    return model_name, executable


def _annotate_records(
    records: List[TransactionRecord],
    annotator: TransactionCategoryAnnotator,
) -> List[dict]:
    annotated: List[dict] = []
    for record in records:
        try:
            annotation = annotator.annotate(record)
        except OllamaAnnotationError as exc:
            raise RuntimeError(f"Failed to annotate record {record}: {exc}") from exc
        row = asdict(record)
        row["category_id"] = annotation.category_id
        row["category_name"] = annotation.category_name
        row["category_reason"] = annotation.reason
        row["tag"] = annotation.category_name
        logging.info(
            "Annotated %s %s -> %s (%s)",
            record.transaction_time,
            record.description,
            annotation.category_name,
            annotation.reason,
        )
        annotated.append(row)
    return annotated


def _write_annotated_csv(path: Path, rows: List[dict]) -> None:
    fieldnames = list(TransactionDataProcessor.OUTPUT_FIELDS) + list(ANNOTATION_FIELDS)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(
        description="Normalize CSV data and annotate each row using Ollama."
    )
    parser.add_argument(
        "-c",
        "--config",
        default="config.json",
        help="Path to the JSON config file (default: config.json)",
    )
    args = parser.parse_args()

    output_path = run_pipeline(config_path=Path(args.config))
    print(f"Annotated transactions written to {output_path}")


if __name__ == "__main__":
    main()
