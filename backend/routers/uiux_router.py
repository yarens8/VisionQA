import base64
import io

from fastapi import APIRouter, Depends, HTTPException
from PIL import Image
from sqlalchemy.orm import Session

import schemas
from database import get_db
from database.models import UiuxAnalysisRecord
from core.uiux.engine import UiuxEngine


router = APIRouter(prefix="/uiux", tags=["uiux"])
engine = UiuxEngine()


def _record_meta(record: UiuxAnalysisRecord) -> dict:
    payload = dict(record.analysis_payload or {})
    meta = dict(payload.get("_history_meta") or {})
    payload["_history_meta"] = meta
    return payload


def _build_thumbnail_base64(source_image_base64: str, max_size: tuple[int, int] = (240, 160)) -> str | None:
    if not source_image_base64:
        return None
    try:
        image_bytes = base64.b64decode(source_image_base64)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image.thumbnail(max_size)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception:
        return None


def _save_uiux_record(db: Session, result: dict, *, source_label: str | None = None) -> None:
    try:
        record = UiuxAnalysisRecord(
            platform=result.get("platform", "web"),
            source_type="upload",
            source_label=source_label,
            overall_score=int(result.get("overall_score") or 0),
            findings_count=len(result.get("findings") or []),
            overview=result.get("overview") or "",
            analysis_payload=result,
        )
        db.add(record)
        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"UI/UX history save failed: {exc}")


def _normalize_uiux_payload(payload: dict) -> dict:
    normalized = dict(payload or {})
    overall_score = int(normalized.get("overall_score") or 100)
    normalized.setdefault("ux_score", overall_score)
    normalized.setdefault("visual_hierarchy_score", overall_score)
    normalized.setdefault("readability_score", overall_score)
    normalized.setdefault("consistency_score", int(normalized.get("layout_balance_score") or overall_score))
    normalized.setdefault("friction_score", overall_score)
    normalized.setdefault("focus_score", overall_score)
    normalized.setdefault("ai_critic_summary", "Kayit eski bir UI/UX analizinden geldigi icin AI critic ozeti varsayilan olarak dolduruldu.")
    normalized.setdefault(
        "score_summary",
        {
            "ux_score": normalized["ux_score"],
            "visual_hierarchy_score": normalized["visual_hierarchy_score"],
            "spacing_score": int(normalized.get("spacing_consistency_score") or overall_score),
            "consistency_score": normalized["consistency_score"],
            "readability_score": normalized["readability_score"],
            "friction_score": normalized["friction_score"],
            "focus_score": normalized["focus_score"],
        },
    )
    normalized.setdefault(
        "attention_prediction",
        {
            "focus_score": normalized["focus_score"],
            "primary_focus_label": "content-block",
            "attention_path": [],
            "summary": "Kayit eski bir analiz oldugu icin attention prediction varsayilan olarak gosteriliyor.",
        },
    )
    fixed_findings = []
    for finding in normalized.get("findings") or []:
        item = dict(finding)
        item.setdefault("ai_critic", item.get("description") or "")
        item.setdefault("why_this_matters", item.get("recommendation") or "")
        fixed_findings.append(item)
    normalized["findings"] = fixed_findings
    return normalized


def _history_item_schema(record: UiuxAnalysisRecord) -> schemas.UiuxHistoryItem:
    payload = record.analysis_payload or {}
    meta = (payload.get("_history_meta") or {})
    source_image_base64 = ((payload.get("artifacts") or {}).get("source_image_base64")) or None
    return schemas.UiuxHistoryItem(
        id=record.id,
        platform=record.platform,
        source_type=record.source_type,
        source_label=record.source_label,
        is_favorite=bool(meta.get("is_favorite", False)),
        overall_score=record.overall_score,
        findings_count=record.findings_count,
        overview=record.overview or "",
        thumbnail_base64=_build_thumbnail_base64(source_image_base64),
        created_at=record.created_at,
    )


@router.post("/analyze-image", response_model=schemas.UiuxAnalysisResponse)
async def analyze_uiux_image(
    request: schemas.UiuxAnalysisRequest,
    db: Session = Depends(get_db),
):
    try:
        result = engine.analyze_image(
            image_base64=request.image_base64,
            platform=request.platform,
        )
        _save_uiux_record(db, result, source_label="Manuel screenshot analizi")
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"UI/UX analysis failed: {exc}") from exc


@router.get("/history", response_model=list[schemas.UiuxHistoryItem])
def get_uiux_history(
    limit: int = 10,
    db: Session = Depends(get_db),
):
    safe_limit = max(1, min(limit, 30))
    records = (
        db.query(UiuxAnalysisRecord)
        .order_by(UiuxAnalysisRecord.created_at.desc(), UiuxAnalysisRecord.id.desc())
        .limit(safe_limit)
        .all()
    )
    return [_history_item_schema(record) for record in records]


@router.get("/history/{record_id}", response_model=schemas.UiuxHistoryDetail)
def get_uiux_history_detail(
    record_id: int,
    db: Session = Depends(get_db),
):
    record = db.query(UiuxAnalysisRecord).filter(UiuxAnalysisRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="UI/UX history record not found.")

    return schemas.UiuxHistoryDetail(
        id=record.id,
        platform=record.platform,
        source_type=record.source_type,
        source_label=record.source_label,
        is_favorite=bool(((record.analysis_payload or {}).get("_history_meta") or {}).get("is_favorite", False)),
        created_at=record.created_at,
        analysis=schemas.UiuxAnalysisResponse.model_validate(_normalize_uiux_payload(record.analysis_payload)),
    )


@router.patch("/history/{record_id}", response_model=schemas.UiuxHistoryItem)
def update_uiux_history_record(
    record_id: int,
    request: schemas.UiuxHistoryUpdateRequest,
    db: Session = Depends(get_db),
):
    record = db.query(UiuxAnalysisRecord).filter(UiuxAnalysisRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="UI/UX history record not found.")

    if request.source_label is not None:
        cleaned = request.source_label.strip()
        record.source_label = cleaned or None

    if request.is_favorite is not None:
        payload = _record_meta(record)
        payload["_history_meta"]["is_favorite"] = bool(request.is_favorite)
        record.analysis_payload = payload

    db.commit()
    db.refresh(record)
    return _history_item_schema(record)


@router.delete("/history/{record_id}", response_model=schemas.UiuxHistoryDeleteResponse)
def delete_uiux_history_record(
    record_id: int,
    db: Session = Depends(get_db),
):
    record = db.query(UiuxAnalysisRecord).filter(UiuxAnalysisRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="UI/UX history record not found.")

    db.delete(record)
    db.commit()
    return schemas.UiuxHistoryDeleteResponse(success=True)
