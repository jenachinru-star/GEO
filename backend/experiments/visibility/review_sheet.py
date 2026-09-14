"""把影子 Observation 转为可人工标注的安全 CSV。"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


REVIEW_FIELDS = (
    "experiment_id",
    "question_id",
    "intent_type",
    "branded",
    "provider",
    "configured_model",
    "response_model",
    "mode",
    "sample_index",
    "status",
    "question_text",
    "answer",
    "sources_json",
    "machine_mentioned",
    "machine_rank",
    "machine_aeo_cited",
    "human_request_valid",
    "human_refusal",
    "human_target_mentioned",
    "human_recommendation",
    "human_rank",
    "human_sole_recommendation",
    "human_has_valid_citation",
    "human_sentiment",
    "human_competitors_json",
    "human_citations_json",
    "privacy_flag",
    "reviewer",
    "review_note",
    "adjudication_note",
)


def spreadsheet_safe(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    if text.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + text
    return text


def export_review_sheet(observations: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=REVIEW_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for observation in observations:
            current = observation.get("current_analyzer") or {}
            row = dict(observation)
            row.update({
                "sources_json": json.dumps(observation.get("sources") or [], ensure_ascii=False),
                "machine_mentioned": current.get("geo_mentioned", ""),
                "machine_rank": current.get("geo_rank", ""),
                "machine_aeo_cited": current.get("aeo_cited", ""),
            })
            writer.writerow({field: spreadsheet_safe(row.get(field, "")) for field in REVIEW_FIELDS})
