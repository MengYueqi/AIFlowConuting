"""Utilities to normalize and persist transaction data from CSV exports."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from typing import List, Mapping, Optional, Sequence, Union


@dataclass
class TransactionRecord:
    """Standardized shape for a single transaction entry."""

    transaction_time: str
    counterparty: str
    transaction_type: str
    description: str
    amount: str
    source: str
    report_time: str
    tag: str


class TransactionDataProcessor:
    """Process Alipay and WeChat CSV exports into a single normalized file."""

    OUTPUT_FIELDS: Sequence[str] = (
        "transaction_time",
        "counterparty",
        "transaction_type",
        "description",
        "amount",
        "source",
        "report_time",
        "tag",
    )

    def __init__(
        self,
        config: Union[Mapping[str, object], str, Path],
        base_path: Optional[Path] = None,
    ) -> None:
        self._last_output_path: Optional[Path] = None
        if isinstance(config, (str, Path)):
            config_path = Path(config)
            self._config = self._load_config_file(config_path)
            self._base_path = config_path.parent
        else:
            self._config = dict(config)
            self._base_path = Path(base_path) if base_path else Path.cwd()

        metadata = self._config.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise ValueError("metadata must be a mapping in config")
        self._report_time = str(metadata.get("report_time", "")).strip()
        if not self._report_time:
            raise ValueError("metadata.report_time must be configured")
        self._tag = str(metadata.get("tag", "") or "").strip()

    @staticmethod
    def _load_config_file(path: Path) -> Mapping[str, object]:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def process(self) -> List[TransactionRecord]:
        records: List[TransactionRecord] = []
        data_sources = self._config.get("data_sources", {})
        if not isinstance(data_sources, Mapping):
            raise ValueError("data_sources must be a mapping in config")

        for source_name, raw_paths in data_sources.items():
            if not isinstance(raw_paths, Sequence):
                raise ValueError("data source paths must be provided as a list or tuple")
            for raw_path in raw_paths:
                file_path = self._resolve_path(str(raw_path))
                records.extend(self._parse_file(file_path, str(source_name)))

        output_cfg = self._config.get("output")
        if not isinstance(output_cfg, Mapping) or "transactions" not in output_cfg:
            raise ValueError("output.transactions must be configured")
        output_template = str(output_cfg["transactions"])
        output_path = self._resolve_path(
            self._render_output_template(output_template)
        )
        self._last_output_path = output_path
        self._write_output(records, output_path)
        return records

    @property
    def last_output_path(self) -> Optional[Path]:
        """Return the last output path used, if any."""
        return self._last_output_path

    def _resolve_path(self, raw_path: str) -> Path:
        path = Path(raw_path)
        if not path.is_absolute():
            path = self._base_path / path
        return path

    def _render_output_template(self, template: str) -> str:
        """Render output template using known metadata placeholders."""
        try:
            return template.format(report_time=self._report_time, tag=self._tag)
        except KeyError as exc:
            raise ValueError(
                f"Unknown placeholder '{exc.args[0]}' in output.transactions template"
            ) from exc

    def _parse_file(self, path: Path, source_name: str) -> List[TransactionRecord]:
        if not path.exists():
            raise FileNotFoundError(f"Missing data file: {path}")

        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = reader.fieldnames or []
            schema = self._detect_schema(fieldnames)
            parser = (
                self._parse_alipay_row if schema == "alipay" else self._parse_wechat_row
            )
            records: List[TransactionRecord] = []
            for row in reader:
                if not row:
                    continue
                record = parser(row, source_name)
                if record:
                    records.append(record)
            return records

    @staticmethod
    def _detect_schema(fieldnames: Sequence[str]) -> str:
        normalized = [name.strip() if isinstance(name, str) else "" for name in fieldnames]
        if "金额(元)" in normalized:
            return "wechat"
        if "金额" in normalized:
            return "alipay"
        raise ValueError("Unable to detect schema for csv file")

    def _parse_alipay_row(
        self, row: Mapping[str, str], source_name: str
    ) -> Optional[TransactionRecord]:
        transaction_time = row.get("交易时间", "").strip()
        if not transaction_time:
            return None
        description = row.get("商品说明", "").strip() or row.get("备注", "").strip()
        transaction_type = self._normalize_type(row.get("收/支", ""))
        if transaction_type not in {"收入", "支出"}:
            return None
        return TransactionRecord(
            transaction_time=transaction_time,
            counterparty=row.get("交易对方", "").strip(),
            transaction_type=transaction_type,
            description=description,
            amount=self._normalize_amount(row.get("金额", "0")),
            source=source_name,
            report_time=self._report_time,
            tag=self._tag,
        )

    def _parse_wechat_row(
        self, row: Mapping[str, str], source_name: str
    ) -> Optional[TransactionRecord]:
        transaction_time = row.get("交易时间", "").strip()
        if not transaction_time:
            return None
        description = row.get("商品", "").strip() or row.get("备注", "").strip()
        transaction_type = self._normalize_type(row.get("收/支", ""))
        if transaction_type not in {"收入", "支出"}:
            return None
        return TransactionRecord(
            transaction_time=transaction_time,
            counterparty=row.get("交易对方", "").strip(),
            transaction_type=transaction_type,
            description=description,
            amount=self._normalize_amount(row.get("金额(元)", "0")),
            source=source_name,
            report_time=self._report_time,
            tag=self._tag,
        )

    @staticmethod
    def _normalize_type(value: str) -> str:
        normalized = value.strip()
        if not normalized:
            return "未知"
        if "不计" in normalized:
            return "不计收支"
        if "支" in normalized:
            return "支出"
        if "收" in normalized or "入" in normalized:
            return "收入"
        return normalized

    @staticmethod
    def _normalize_amount(value: str) -> str:
        cleaned = value.replace("¥", "").replace(",", "").strip()
        if not cleaned:
            cleaned = "0"
        try:
            decimal_value = Decimal(cleaned)
        except InvalidOperation as exc:
            raise ValueError(f"Invalid amount value: {value}") from exc
        return f"{decimal_value.quantize(Decimal('0.01'))}"

    def _write_output(self, records: Sequence[TransactionRecord], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(self.OUTPUT_FIELDS))
            writer.writeheader()
            for record in records:
                writer.writerow(asdict(record))


def main() -> None:
    """Ad-hoc entrypoint to run the processor without a separate test harness."""
    parser = argparse.ArgumentParser(description="Normalize local Alipay/WeChat CSVs.")
    parser.add_argument(
        "-c",
        "--config",
        default="config.json",
        help="Path to the JSON configuration file (default: config.json)",
    )
    args = parser.parse_args()

    processor = TransactionDataProcessor(args.config)
    records = processor.process()
    output_msg = f" -> {processor.last_output_path}" if processor.last_output_path else ""
    print(f"Processed {len(records)} transactions{output_msg}")


if __name__ == "__main__":
    main()


__all__ = ["TransactionDataProcessor", "TransactionRecord", "main"]
