"""Model utilities for AIFlowConuting."""

from .annotator import (
    AnnotationResult,
    TransactionCategoryAnnotator,
    OllamaAnnotationError,
    demo_annotation,
)

__all__ = [
    "AnnotationResult",
    "TransactionCategoryAnnotator",
    "OllamaAnnotationError",
    "demo_annotation",
]
