"""根据已标注 review-sheet.csv 计算当前分析器的基础二分类指标。"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


TRUE_VALUES = {"1", "true", "yes", "y", "是"}
FALSE_VALUES = {"0", "false", "no", "n", "否"}


def parse_bool(value: str) -> bool | None:
    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    return None


def binary_metrics(pairs: list[tuple[bool, bool]]) -> dict[str, float | int | None]:
    tp = sum(predicted and actual for predicted, actual in pairs)
    fp = sum(predicted and not actual for predicted, actual in pairs)
    fn = sum(not predicted and actual for predicted, actual in pairs)
    tn = sum(not predicted and not actual for predicted, actual in pairs)
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    accuracy = (tp + tn) / len(pairs) if pairs else None
    return {
        "labeled": len(pairs),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "accuracy": accuracy,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("review_sheet", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    with args.review_sheet.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))

    mentioned_pairs = []
    citation_pairs = []
    for row in rows:
        machine_mentioned = parse_bool(row.get("machine_mentioned", ""))
        human_mentioned = parse_bool(row.get("human_target_mentioned", ""))
        if machine_mentioned is not None and human_mentioned is not None:
            mentioned_pairs.append((machine_mentioned, human_mentioned))

        machine_cited = parse_bool(row.get("machine_aeo_cited", ""))
        human_cited = parse_bool(row.get("human_has_valid_citation", ""))
        if machine_cited is not None and human_cited is not None:
            citation_pairs.append((machine_cited, human_cited))

    result = {
        "rows": len(rows),
        "mention": binary_metrics(mentioned_pairs),
        "legacy_aeo_vs_valid_citation": binary_metrics(citation_pairs),
        "warning": "legacy AEO 仅用于暴露旧算法误差，不代表 V2 来源引用实现。",
    }
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    print(payload)
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
