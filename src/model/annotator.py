"""Tools for classifying individual transactions via Ollama + Qwen-32B."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from data_management.transactions import TransactionRecord

CATEGORY_LABELS: Dict[int, str] = {
    0: "收入",
    1: "餐饮",
    2: "交通",
    3: "居住",
    4: "购物",
    5: "娱乐",
    6: "其他",
}

PROMPT_TEMPLATE = """你是一个财经助手，需要根据一条交易记录判断它属于以下分类中的哪一类，只能选择一个：
0. 收入
1. 餐饮：吃饭、外卖、咖啡、零食
2. 交通：打车、地铁、公交、油费
3. 居住：房租、水电燃气、物业
4. 购物：衣服、日用品、电子产品
5. 娱乐：电影、游戏、旅游、会员
6. 其他：无法归类的支出或其他类型

category_name 字段必须严格等于以下标签之一：收入、餐饮、交通、居住、购物、娱乐、其他。
请只返回 JSON 字符串，格式如下：{{"category_id":<数字>,"category_name":"<分类名称>","reason":"<简短原因>"}}。
交易信息：
- 交易时间：{transaction_time}
- 交易对方：{counterparty}
- 交易类型：{transaction_type}
- 描述：{description}
- 金额：{amount}
"""


@dataclass
class AnnotationResult:
    """Structured result returned by the annotator."""

    category_id: int
    category_name: str
    reason: str
    raw_response: str


class OllamaAnnotationError(RuntimeError):
    """Raised when the Ollama call fails or returns malformed data."""


class TransactionCategoryAnnotator:
    """Helper that calls Ollama Qwen-32B to label a single transaction."""

    def __init__(
        self,
        model: str = "qwen-32b",
        executable: str = "ollama",
        env: Optional[Mapping[str, str]] = None,
    ) -> None:
        self._model = model
        self._exec = executable
        self._env = dict(env) if env else None

    def annotate(self, record: "TransactionRecord | Mapping[str, Any]") -> AnnotationResult:
        payload = self._to_payload(record)
        prompt = PROMPT_TEMPLATE.format(**payload)
        response_text = self._run_ollama(prompt)
        parsed = self._parse_response(response_text)
        return AnnotationResult(
            category_id=parsed["category_id"],
            category_name=parsed["category_name"],
            reason=parsed.get("reason", ""),
            raw_response=response_text,
        )

    def _to_payload(self, record: "TransactionRecord | Mapping[str, Any]") -> Dict[str, str]:
        if hasattr(record, "transaction_time"):
            payload = {
                "transaction_time": getattr(record, "transaction_time", ""),
                "counterparty": getattr(record, "counterparty", ""),
                "transaction_type": getattr(record, "transaction_type", ""),
                "description": getattr(record, "description", ""),
                "amount": getattr(record, "amount", ""),
            }
        else:
            mapping = dict(record)
            payload = {
                "transaction_time": str(mapping.get("transaction_time", "")),
                "counterparty": str(mapping.get("counterparty", "")),
                "transaction_type": str(mapping.get("transaction_type", "")),
                "description": str(mapping.get("description", "")),
                "amount": str(mapping.get("amount", "")),
            }
        return payload

    def _run_ollama(self, prompt: str) -> str:
        try:
            proc = subprocess.run(
                [self._exec, "run", self._model],
                input=prompt.encode("utf-8"),
                capture_output=True,
                check=True,
                env=self._env,
            )
        except subprocess.CalledProcessError as exc:  # pragma: no cover - runtime safety
            raise OllamaAnnotationError(exc.stderr.decode("utf-8", "ignore")) from exc
        return proc.stdout.decode("utf-8", "ignore").strip()

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        json_str = self._extract_json(response_text)
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise OllamaAnnotationError(
                f"Failed to parse Ollama response as JSON: {response_text}"
            ) from exc

        category_id = data.get("category_id")
        if category_id not in CATEGORY_LABELS:
            raise OllamaAnnotationError(f"Invalid category_id: {category_id}")
        data["category_name"] = CATEGORY_LABELS[category_id]
        return data

    @staticmethod
    def _extract_json(raw_text: str) -> str:
        match = re.search(r"\{.*\}", raw_text, flags=re.DOTALL)
        if not match:
            raise OllamaAnnotationError(f"No JSON object found in response: {raw_text}")
        return match.group(0)


def demo_annotation() -> None:
    """Minimal CLI helper for manual testing."""
    from data_management.transactions import TransactionRecord

    sample = TransactionRecord(
        transaction_time="2025-04-27 10:42:19",
        counterparty="星巴克",
        transaction_type="支出",
        description="星巴克咖啡",
        amount="37.00",
        source="alipay",
        report_time="2025-04",
        tag="",
    )
    annotator = TransactionCategoryAnnotator()
    result = annotator.annotate(sample)
    print(result)


__all__ = [
    "AnnotationResult",
    "TransactionCategoryAnnotator",
    "OllamaAnnotationError",
    "demo_annotation",
]
