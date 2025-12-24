"""Generate Markdown reports from annotated transaction CSV files."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Dict, List


@dataclass
class CategorySummary:
    category_name: str
    total_amount: Decimal
    count: int

    def add(self, amount: Decimal) -> None:
        self.total_amount += amount
        self.count += 1


@dataclass
class ReportData:
    report_time: str
    total_income: Decimal
    total_expense: Decimal
    income_count: int
    expense_count: int
    categories: List[CategorySummary]
    top_expenses: List[dict]


class TransactionReportGenerator:
    """Generate summary statistics from annotated transactions."""

    def __init__(self, csv_path: Path) -> None:
        self._csv_path = csv_path

    def generate(self) -> ReportData:
        records = self._parse_csv()
        return self._summarize(records)

    def _parse_csv(self) -> List[dict]:
        if not self._csv_path.exists():
            raise FileNotFoundError(f"Transactions file not found: {self._csv_path}")
        with self._csv_path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            return list(reader)

    def _summarize(self, rows: List[dict]) -> ReportData:
        total_income = Decimal("0")
        total_expense = Decimal("0")
        income_count = 0
        expense_count = 0
        report_time = ""
        summaries: Dict[str, CategorySummary] = {}
        expense_rows: List[dict] = []

        for row in rows:
            amount = Decimal(row.get("amount", "0") or "0")
            report_time = row.get("report_time", report_time)
            tag = (row.get("tag") or row.get("category_name") or "其他").strip() or "其他"
            transaction_type = (row.get("transaction_type") or "").strip()

            if transaction_type == "收入":
                total_income += amount
                income_count += 1
                continue
            if transaction_type != "支出":
                continue

            total_expense += amount
            expense_count += 1
            summary = summaries.setdefault(tag, CategorySummary(tag, Decimal("0"), 0))
            summary.add(amount)
            expense_rows.append(
                {
                    "transaction_time": row.get("transaction_time", ""),
                    "counterparty": row.get("counterparty", ""),
                    "description": row.get("description", ""),
                    "tag": tag,
                    "amount": amount,
                }
            )

        categories = sorted(
            summaries.values(),
            key=lambda s: s.total_amount,
            reverse=True,
        )
        expense_rows.sort(key=lambda r: r["amount"], reverse=True)
        top_expenses = expense_rows[:10]
        return ReportData(
            report_time=report_time,
            total_income=total_income,
            total_expense=total_expense,
            income_count=income_count,
            expense_count=expense_count,
            categories=categories,
            top_expenses=top_expenses,
        )


def render_markdown(report: ReportData) -> str:
    lines = [
        f"# {report.report_time}月报",
        "",
        f"## 总览",
        f"- 收入：¥{report.total_income:.2f}（{report.income_count} 笔）",
        f"- 支出：¥{report.total_expense:.2f}（{report.expense_count} 笔）",
        "",
        "## 支出分类",
        "",
        "| 分类 | 金额 | 笔数 |",
        "| --- | ---: | ---: |",
    ]
    if not report.categories:
        lines.append("| 暂无支出记录 | - | - |")
    else:
        for summary in report.categories:
            lines.append(
                f"| {summary.category_name} | ¥{summary.total_amount:.2f} | {summary.count} |"
            )
    lines.extend(
        [
            "",
            "## 金额最高的 10 笔支出",
        ]
    )
    if not report.top_expenses:
        lines.append("暂无支出记录")
    else:
        lines.append("| 时间 | 对方 | 描述 | 分类 | 金额 |")
        lines.append("| --- | --- | --- | --- | ---: |")
        for row in report.top_expenses:
            lines.append(
                f"| {row['transaction_time']} | {row['counterparty']} | {row['description']} | {row['tag']} | ¥{row['amount']:.2f} |"
            )
    return "\n".join(lines) + "\n"


__all__ = ["TransactionReportGenerator", "render_markdown"]
