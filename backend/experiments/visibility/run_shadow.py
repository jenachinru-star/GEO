"""运行隔离的 AI 可见度影子实验。

默认仅 dry-run。只有显式传入 --execute 才调用外部 API。
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.engines.geo_aeo_analyzer import GEOAEOAnalyzer  # noqa: E402
from app.models import DoctorProfile  # noqa: E402
from experiments.visibility.provider_runner import GLMShadowRunner  # noqa: E402
from experiments.visibility.review_sheet import export_review_sheet  # noqa: E402
from experiments.visibility.schemas import RenderedQuestion  # noqa: E402


FIXTURE_PATH = BACKEND_ROOT / "tests" / "fixtures" / "visibility_questions.json"
OUTPUT_ROOT = PROJECT_ROOT / "artifacts" / "shadow"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI 可见度影子实验（默认 dry-run）")
    parser.add_argument("--profile-id", type=int, help="只读加载 DoctorProfile ID")
    parser.add_argument("--mode", choices=("chat", "grounded_search"), default="chat")
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--max-questions", type=int)
    parser.add_argument("--question-id", action="append", dest="question_ids")
    parser.add_argument("--execute", action="store_true", help="显式允许真实 API 调用")
    parser.add_argument(
        "--allow-unverified-grounded",
        action="store_true",
        help="仅做能力探测；当前 GLM 代理未验证联网，不应用于正式样本",
    )
    parser.add_argument("--experiment-id")
    return parser.parse_args()


def load_profile(profile_id: int | None) -> dict[str, str]:
    if profile_id is None:
        return {
            "doctor_name": "{{doctor_name}}",
            "hospital": "{{hospital}}",
            "department": "{{department}}",
            "city": "{{city}}",
            "specialty_primary": "{{specialty_primary}}",
            "specialty_secondary": "{{specialty_secondary}}",
        }
    db = SessionLocal()
    try:
        profile = db.query(DoctorProfile).filter(DoctorProfile.id == profile_id).first()
        if not profile:
            raise SystemExit(f"DoctorProfile {profile_id} 不存在")
        specialties = [item.strip() for item in (profile.specialty or "").replace("，", ",").split(",") if item.strip()]
        return {
            "doctor_name": profile.real_name or "",
            "hospital": profile.hospital or "",
            "department": profile.department or "",
            "city": profile.city or profile.province or "",
            "specialty_primary": specialties[0] if specialties else profile.department or "",
            "specialty_secondary": specialties[1] if len(specialties) > 1 else (specialties[0] if specialties else profile.department or ""),
        }
    finally:
        db.close()


def render(text: str, variables: dict[str, str]) -> str:
    rendered = text
    for key, value in variables.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    return rendered


def load_questions(variables: dict[str, str], selected: list[str] | None, maximum: int | None) -> list[RenderedQuestion]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    rows = payload["questions"]
    if selected:
        wanted = set(selected)
        rows = [row for row in rows if row["id"] in wanted]
        missing = wanted - {row["id"] for row in rows}
        if missing:
            raise SystemExit(f"未知 question id: {sorted(missing)}")
    if maximum is not None:
        rows = rows[:maximum]
    return [
        RenderedQuestion(
            id=row["id"],
            intent_type=row["intent_type"],
            branded=bool(row["branded"]),
            text=render(row["text"], variables),
            purpose=row["purpose"],
        )
        for row in rows
    ]


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    if args.samples < 1 or args.samples > 5:
        raise SystemExit("--samples 必须为 1 到 5")
    if args.max_questions is not None and args.max_questions < 1:
        raise SystemExit("--max-questions 必须大于 0")
    if args.execute and args.profile_id is None:
        raise SystemExit("真实执行必须明确 --profile-id")
    if args.execute and args.mode == "grounded_search" and not args.allow_unverified_grounded:
        raise SystemExit(
            "当前 GLM 代理已实测无结构化搜索来源；如仅做能力探测，显式加入 "
            "--allow-unverified-grounded"
        )

    profile = load_profile(args.profile_id)
    questions = load_questions(profile, args.question_ids, args.max_questions)
    planned = len(questions) * args.samples
    experiment_id = args.experiment_id or f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"

    plan = {
        "experiment_id": experiment_id,
        "execute": args.execute,
        "provider": "glm",
        "configured_model": settings.GLM_MODEL,
        "base_host": urlparse(settings.GLM_BASE_URL).hostname,
        "mode": args.mode,
        "samples": args.samples,
        "question_count": len(questions),
        "planned_requests": planned,
        "profile_id": args.profile_id,
        "questions": [asdict(question) for question in questions],
        "cost_note": "代理端点计费尚未确认；执行前需人工确认预算。",
    }
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    if not args.execute:
        print("DRY_RUN_ONLY：未调用外部 API，加入 --execute 才会执行。")
        return 0

    output_dir = OUTPUT_ROOT / experiment_id
    output_dir.mkdir(parents=True, exist_ok=False)
    write_json(output_dir / "manifest.json", plan)
    runner = GLMShadowRunner()
    analyzer = GEOAEOAnalyzer(
        doctor_name=profile["doctor_name"],
        hospital=profile["hospital"],
        department=profile["department"],
    )
    observations = []
    for question in questions:
        for sample_index in range(1, args.samples + 1):
            result = runner.run(experiment_id, question, args.mode, sample_index)
            if result.status == "succeeded":
                current = analyzer.analyze(result.answer)
                result.current_analyzer = {
                    "geo_mentioned": current.geo_mentioned,
                    "geo_rank": current.geo_rank,
                    "aeo_cited": current.aeo_cited,
                    "aeo_confidence": current.aeo_confidence,
                }
            observations.append(result.to_dict())
            print(f"{question.id} sample={sample_index} status={result.status} sources={len(result.sources)}")

    with (output_dir / "observations.jsonl").open("w", encoding="utf-8") as stream:
        for observation in observations:
            stream.write(json.dumps(observation, ensure_ascii=False) + "\n")
    errors = [row for row in observations if row["status"] != "succeeded"]
    with (output_dir / "provider-errors.jsonl").open("w", encoding="utf-8") as stream:
        for error in errors:
            stream.write(json.dumps(error, ensure_ascii=False) + "\n")
    export_review_sheet(observations, output_dir / "review-sheet.csv")
    write_json(output_dir / "summary.json", {
        "experiment_id": experiment_id,
        "planned": planned,
        "succeeded": len(observations) - len(errors),
        "failed": len(errors),
        "with_structured_sources": sum(bool(row["sources"]) for row in observations),
        "output_dir": str(output_dir),
    })
    print(f"实验完成：{output_dir}")
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
