import json
import csv
import hashlib
import os
import zipfile
import asyncio
from collections import Counter, defaultdict
from datetime import datetime
from io import BytesIO
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List
import xml.etree.ElementTree as ET

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from pydantic import ValidationError
from sqlalchemy.orm import Session

import schemas
from core.job_payload import to_json_payload
from core.security.job_runner import update_job_status
from core.tasks import run_dataset_analysis_task
from database import SessionLocal, get_db
from database.models import AnalysisJob, DatasetAnalysisRecord
from schemas import (
    DatasetAnalysisResponse,
    DatasetAnalyzeRequest,
    DatasetClassDistributionItem,
    DatasetCollectionTarget,
    DatasetCoverageGap,
    DatasetDuplicateSignal,
    DatasetFinding,
    DatasetDetailError,
    DatasetScoreBreakdown,
    DatasetSplitHealthItem,
    DatasetSuspiciousLabelSignal,
    DatasetTrainingRisk,
)

router = APIRouter(prefix="/dataset", tags=["dataset"])

MAX_ZIP_BYTES = 1000 * 1024 * 1024
MAX_ZIP_MEMBERS = 5000
MAX_HASH_IMAGE_COUNT = 200
MAX_HASH_TOTAL_BYTES = 50 * 1024 * 1024
DATASET_STORAGE_DIR = Path(__file__).resolve().parents[1] / "storage" / "datasets"
ANNOTATION_FILE_HINTS = ("dataset.json", "annotations.json", "annotation.json", "_annotations.coco.json")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
CSV_EXTENSIONS = {".csv"}
XML_EXTENSIONS = {".xml"}
YOLO_EXTENSIONS = {".txt"}


def _safe_artifact_label(label: str | None, fallback: str) -> str:
    raw = label or fallback
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in raw)
    return safe[:120] or fallback


def _write_dataset_artifact(source_type: str, source_label: str | None, content: bytes) -> Dict[str, Any]:
    DATASET_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(content).hexdigest()
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    extension = ".zip" if source_type == "zip" else ".json"
    filename = f"{timestamp}_{digest[:12]}_{_safe_artifact_label(source_label, 'dataset')}{extension}"
    path = DATASET_STORAGE_DIR / filename
    path.write_bytes(content)
    return {
        "type": source_type,
        "label": source_label,
        "path": os.path.relpath(path, Path(__file__).resolve().parents[1]),
        "sha256": digest,
        "size_bytes": len(content),
        "saved_at": datetime.utcnow(),
    }


def _add_finding(
    findings: List[DatasetFinding],
    severity: str,
    category: str,
    title: str,
    description: str,
    evidence: str,
    recommendation: str,
    *,
    error_type: str | None = None,
    image_id: str | None = None,
    annotation_id: str | None = None,
    file_name: str | None = None,
    field: str | None = None,
) -> None:
    findings.append(
        DatasetFinding(
            id=len(findings) + 1,
            title=title,
            severity=severity,
            category=category,
            description=description,
            evidence=evidence,
            recommendation=recommendation,
            error_type=error_type,
            image_id=image_id,
            annotation_id=annotation_id,
            file_name=file_name,
            field=field,
        )
    )


def _add_detail_error(
    detail_errors: List[DatasetDetailError],
    error_type: str,
    severity: str,
    message: str,
    field: str,
    *,
    image_id: Any = None,
    annotation_id: Any = None,
    file_name: Any = None,
    metadata: Dict[str, Any] | None = None,
) -> None:
    detail_errors.append(
        DatasetDetailError(
            error_id=f"PRED_{len(detail_errors) + 1:04d}",
            error_type=error_type,
            image_id=str(image_id) if image_id is not None else None,
            annotation_id=str(annotation_id) if annotation_id is not None else None,
            file_name=str(file_name) if file_name is not None else None,
            field=field,
            severity=severity,
            message=message,
            metadata=metadata or {},
        )
    )


def _grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 55:
        return "D"
    return "E"


def _record_id(record: Any, index: int) -> str:
    return str(record.id or f"record-{index + 1}")


def _clean_label(record: Any) -> str:
    return str(record.label or "").strip()


def _record_signature(record: Any) -> str:
    label = _clean_label(record).lower()
    image_name = str(record.image_name or "").strip().lower()
    text = " ".join(str(record.text or "").strip().lower().split())
    annotation_sig = []
    for annotation in record.annotations or []:
        annotation_sig.append(
            (
                str(annotation.label or "").strip().lower(),
                tuple(annotation.bbox or []),
            )
        )
    return repr((label, image_name, text, tuple(annotation_sig)))


def _bbox_problem(record: Any, bbox: Any) -> str | None:
    if not isinstance(bbox, list) or len(bbox) != 4:
        return "invalid_bbox"
    try:
        x, y, width, height = [float(value) for value in bbox]
    except (TypeError, ValueError):
        return "invalid_bbox"
    if x < 0 or y < 0 or width <= 0 or height <= 0:
        return "invalid_bbox"

    image_width = record.width
    image_height = record.height
    if image_width and image_height:
        # Normalized YOLO boxes are allowed when every coordinate is in [0, 1].
        normalized = all(0 <= value <= 1 for value in (x, y, width, height))
        if not normalized:
            if x + width > float(image_width) or y + height > float(image_height):
                return "out_of_bound_bbox"
    return None


def _bbox_is_invalid(record: Any, bbox: Any) -> bool:
    return _bbox_problem(record, bbox) is not None


def _score_from_findings(findings: List[DatasetFinding]) -> DatasetScoreBreakdown:
    scores = {
        "completeness": 100,
        "balance": 100,
        "consistency": 100,
        "validity": 100,
        "annotation_health": 100,
    }
    severity_penalty = {"high": 28, "medium": 14, "low": 6}
    category_to_score = {
        "missing-label": "completeness",
        "missing-image": "validity",
        "broken-record": "validity",
        "annotation-health": "annotation_health",
        "invalid-category-id": "annotation_health",
        "class-imbalance": "balance",
        "rare-class": "balance",
        "split-balance": "balance",
        "split-leakage": "consistency",
        "duplicate-signal": "consistency",
        "label-consistency": "consistency",
    }

    for finding in findings:
        target = category_to_score.get(finding.category)
        if not target:
            continue
        scores[target] = max(0, scores[target] - severity_penalty.get(finding.severity, 10))

    return DatasetScoreBreakdown(**scores)


def _safe_zip_names(archive: zipfile.ZipFile) -> List[str]:
    names = archive.namelist()
    if len(names) > MAX_ZIP_MEMBERS:
        raise HTTPException(status_code=400, detail="ZIP icinde cok fazla dosya var.")
    for name in names:
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts:
            raise HTTPException(status_code=400, detail="ZIP icinde guvensiz dosya yolu bulundu.")
    return names


def _find_annotation_member(names: List[str]) -> str:
    json_names = [name for name in names if name.lower().endswith(".json")]
    for hint in ANNOTATION_FILE_HINTS:
        for name in json_names:
            if PurePosixPath(name).name.lower() == hint:
                return name
    for name in json_names:
        lowered = PurePosixPath(name).name.lower()
        if "annotation" in lowered or "dataset" in lowered:
            return name
    if len(json_names) == 1:
        return json_names[0]
    raise HTTPException(
        status_code=400,
        detail="ZIP icinde desteklenen annotation bulunamadi. Desteklenenler: JSON/COCO, CSV, Pascal VOC XML veya YOLO label txt dosyalari.",
    )


def _find_structured_member(names: List[str]) -> str | None:
    json_names = [name for name in names if name.lower().endswith(".json")]
    for hint in ANNOTATION_FILE_HINTS:
        for name in json_names:
            if PurePosixPath(name).name.lower() == hint:
                return name
    for name in json_names:
        lowered = PurePosixPath(name).name.lower()
        if "annotation" in lowered or "dataset" in lowered:
            return name
    if len(json_names) == 1:
        return json_names[0]

    csv_names = [name for name in names if PurePosixPath(name).suffix.lower() in CSV_EXTENSIONS]
    for name in csv_names:
        lowered = PurePosixPath(name).name.lower()
        if "annotation" in lowered or "dataset" in lowered or "label" in lowered:
            return name
    if len(csv_names) == 1:
        return csv_names[0]
    return None


def _normalize_image_name(image_name: Any) -> str:
    return PurePosixPath(str(image_name or "").replace("\\", "/")).name.lower()


def _zip_image_lookup(names: List[str]) -> set[str]:
    return {
        _normalize_image_name(name)
        for name in names
        if PurePosixPath(name).suffix.lower() in IMAGE_EXTENSIONS
    }


def _zip_image_hash_lookup(archive: zipfile.ZipFile, names: List[str]) -> dict[str, str]:
    image_infos = [
        archive.getinfo(name)
        for name in names
        if PurePosixPath(name).suffix.lower() in IMAGE_EXTENSIONS
    ]
    if len(image_infos) > MAX_HASH_IMAGE_COUNT:
        return {}
    if sum(info.file_size for info in image_infos) > MAX_HASH_TOTAL_BYTES:
        return {}

    hashes: dict[str, str] = {}
    for info in image_infos:
        name = info.filename
        try:
            digest = hashlib.sha256(archive.read(name)).hexdigest()
        except Exception:
            continue
        hashes[_normalize_image_name(name)] = digest
    return hashes


def _parse_bbox(value: Any) -> list[float] | None:
    if value is None or value == "":
        return None
    if isinstance(value, list):
        try:
            return [float(item) for item in value]
        except (TypeError, ValueError):
            return None
    text = str(value).strip()
    if not text:
        return None
    try:
        loaded = json.loads(text)
        if isinstance(loaded, list):
            return [float(item) for item in loaded]
    except Exception:
        pass
    parts = [part.strip() for part in text.replace(";", ",").split(",") if part.strip()]
    try:
        return [float(part) for part in parts]
    except ValueError:
        return None


def _records_from_csv_payload(raw: str, dataset_name: str = "CSV ZIP Dataset") -> DatasetAnalyzeRequest:
    reader = csv.DictReader(raw.splitlines())
    records = []
    for index, row in enumerate(reader, start=1):
        image_id = row.get("image_id") or row.get("id") or row.get("record_id") or str(index)
        annotation_id = row.get("annotation_id") or row.get("ann_id")
        label = row.get("label") or row.get("class") or row.get("category") or row.get("category_id") or ""
        bbox = _parse_bbox(row.get("bbox"))
        if bbox is None and {"x", "y", "width", "height"}.issubset(row.keys()):
            bbox = _parse_bbox([row.get("x"), row.get("y"), row.get("width"), row.get("height")])
        records.append(
            {
                "id": str(image_id),
                "split": row.get("split") or row.get("subset"),
                "label": str(label),
                "text": row.get("text") or "",
                "image_name": row.get("image_name") or row.get("file_name") or row.get("filename") or "",
                "width": int(float(row["width"])) if row.get("width") else None,
                "height": int(float(row["height"])) if row.get("height") else None,
                "annotations": [{"id": annotation_id, "label": str(label), "bbox": bbox}] if label or bbox else [],
                "metadata": {"source_format": "csv", "image_id": str(image_id)},
            }
        )
    return DatasetAnalyzeRequest(dataset_name=dataset_name, records=records)


def _records_from_pascal_xml_payload(xml_payloads: list[tuple[str, str]]) -> DatasetAnalyzeRequest:
    records = []
    for index, (name, raw) in enumerate(xml_payloads, start=1):
        root = ET.fromstring(raw)
        image_id = root.findtext("id") or root.findtext("filename") or PurePosixPath(name).stem
        width = int(float(root.findtext("./size/width", "0") or 0)) or None
        height = int(float(root.findtext("./size/height", "0") or 0)) or None
        filename = root.findtext("filename") or f"{PurePosixPath(name).stem}.jpg"
        annotations = []
        for obj_index, obj in enumerate(root.findall("object"), start=1):
            label = (obj.findtext("name") or "").strip()
            box = obj.find("bndbox")
            bbox = None
            if box is not None:
                xmin = float(box.findtext("xmin", "0") or 0)
                ymin = float(box.findtext("ymin", "0") or 0)
                xmax = float(box.findtext("xmax", "0") or 0)
                ymax = float(box.findtext("ymax", "0") or 0)
                bbox = [xmin, ymin, xmax - xmin, ymax - ymin]
            annotations.append({"id": f"{PurePosixPath(name).stem}-{obj_index}", "label": label, "bbox": bbox})
        records.append(
            {
                "id": str(image_id or index),
                "split": PurePosixPath(name).parts[0].lower() if PurePosixPath(name).parts else None,
                "label": annotations[0]["label"] if annotations else "",
                "image_name": filename,
                "width": width,
                "height": height,
                "annotations": annotations,
                "metadata": {"source_format": "pascal_voc", "xml_file": name, "image_id": str(image_id or index)},
            }
        )
    return DatasetAnalyzeRequest(dataset_name="Pascal VOC ZIP Dataset", records=records)


def _records_from_yolo_zip(archive: zipfile.ZipFile, names: List[str]) -> DatasetAnalyzeRequest:
    label_names = [
        name for name in names
        if PurePosixPath(name).suffix.lower() in YOLO_EXTENSIONS
        and "label" in str(PurePosixPath(name).parent).lower()
    ]
    records = []
    for index, label_name in enumerate(sorted(label_names), start=1):
        split = "unspecified"
        parts = [part.lower() for part in PurePosixPath(label_name).parts]
        for candidate in ("train", "valid", "val", "test"):
            if candidate in parts:
                split = "val" if candidate == "valid" else candidate
                break
        stem = PurePosixPath(label_name).stem
        image_name = ""
        for ext in IMAGE_EXTENSIONS:
            candidates = [name for name in names if PurePosixPath(name).stem == stem and PurePosixPath(name).suffix.lower() == ext]
            if candidates:
                image_name = candidates[0]
                break
        annotations = []
        for line_index, line in enumerate(archive.read(label_name).decode("utf-8", errors="ignore").splitlines(), start=1):
            parts = line.strip().split()
            if len(parts) < 5:
                continue
            class_id = parts[0]
            bbox = [float(value) for value in parts[1:5]]
            annotations.append({"id": f"{stem}-{line_index}", "label": class_id, "category_id": class_id, "bbox": bbox})
        records.append(
            {
                "id": stem or str(index),
                "split": split,
                "label": annotations[0]["label"] if annotations else "",
                "image_name": image_name or f"{stem}.jpg",
                "annotations": annotations,
                "metadata": {"source_format": "yolo", "label_file": label_name, "image_id": stem or str(index)},
            }
        )
    if not records:
        raise HTTPException(status_code=400, detail="ZIP icinde YOLO labels klasoru bulunamadi.")
    return DatasetAnalyzeRequest(dataset_name="YOLO ZIP Dataset", records=records)


def _records_from_dataset_payload(payload: Any) -> DatasetAnalyzeRequest:
    if isinstance(payload, list):
        return DatasetAnalyzeRequest(dataset_name="Uploaded ZIP Dataset", records=payload)
    if isinstance(payload, dict) and "records" in payload:
        return DatasetAnalyzeRequest(
            dataset_name=payload.get("dataset_name") or payload.get("name") or "Uploaded ZIP Dataset",
            records=payload.get("records") or [],
        )
    raise HTTPException(status_code=400, detail="Dataset JSON formati records listesi icermiyor.")


def _records_from_coco_payload(payload: Dict[str, Any]) -> DatasetAnalyzeRequest:
    images = {image.get("id"): image for image in payload.get("images", []) if isinstance(image, dict)}
    categories = {
        category.get("id"): str(category.get("name") or category.get("label") or category.get("id"))
        for category in payload.get("categories", [])
        if isinstance(category, dict)
    }
    grouped_annotations: Dict[Any, List[Dict[str, Any]]] = defaultdict(list)
    for annotation in payload.get("annotations", []):
        if isinstance(annotation, dict):
            grouped_annotations[annotation.get("image_id")].append(annotation)

    records = []
    for image_id, image in images.items():
        annotations = []
        labels = []
        for annotation in grouped_annotations.get(image_id, []):
            category_id = annotation.get("category_id")
            label = categories.get(category_id, str(category_id or ""))
            labels.append(label)
            annotations.append(
                {
                    "id": str(annotation.get("id")) if annotation.get("id") is not None else None,
                    "label": label,
                    "bbox": annotation.get("bbox"),
                    "category_id": category_id,
                }
            )

        records.append(
            {
                "id": str(image_id),
                "split": image.get("split") or image.get("subset"),
                "label": labels[0] if labels else "",
                "text": image.get("caption") or image.get("text"),
                "image_name": image.get("file_name") or image.get("name"),
                "width": image.get("width"),
                "height": image.get("height"),
                "annotations": annotations,
                "metadata": {
                    "source_format": "coco",
                    "image_id": str(image_id),
                    "invalid_category_ids": [
                        annotation.get("id")
                        for annotation in grouped_annotations.get(image_id, [])
                        if annotation.get("category_id") not in categories
                    ],
                },
            }
        )

    return DatasetAnalyzeRequest(
        dataset_name=str(payload.get("dataset_name") or payload.get("info", {}).get("description") or "COCO ZIP Dataset"),
        records=records,
    )


def _request_from_annotation_payload(payload: Any) -> DatasetAnalyzeRequest:
    if isinstance(payload, dict) and {"images", "annotations"}.issubset(payload.keys()):
        return _records_from_coco_payload(payload)
    return _records_from_dataset_payload(payload)


def _request_from_zip_archive(archive: zipfile.ZipFile, names: List[str]) -> DatasetAnalyzeRequest:
    structured_member = _find_structured_member(names)
    if structured_member:
        suffix = PurePosixPath(structured_member).suffix.lower()
        raw_bytes = archive.read(structured_member)
        if suffix == ".json":
            try:
                annotation_payload = json.loads(raw_bytes.decode("utf-8"))
            except UnicodeDecodeError as exc:
                raise HTTPException(status_code=400, detail="Annotation JSON UTF-8 olarak okunamadi.") from exc
            except json.JSONDecodeError as exc:
                raise HTTPException(status_code=400, detail="Annotation JSON gecersiz formatta.") from exc
            return _request_from_annotation_payload(annotation_payload)
        if suffix == ".csv":
            return _records_from_csv_payload(raw_bytes.decode("utf-8-sig", errors="ignore"))

    xml_payloads = [
        (name, archive.read(name).decode("utf-8", errors="ignore"))
        for name in names
        if PurePosixPath(name).suffix.lower() in XML_EXTENSIONS
    ]
    if xml_payloads:
        return _records_from_pascal_xml_payload(xml_payloads)

    yolo_like = any(
        PurePosixPath(name).suffix.lower() in YOLO_EXTENSIONS and "label" in str(PurePosixPath(name).parent).lower()
        for name in names
    )
    if yolo_like:
        return _records_from_yolo_zip(archive, names)

    raise HTTPException(status_code=400, detail="ZIP icinde desteklenen annotation formati bulunamadi.")


def _attach_zip_image_evidence(request: DatasetAnalyzeRequest, image_names: set[str], image_hashes: dict[str, str] | None = None) -> None:
    for record in request.records:
        image_name = _normalize_image_name(record.image_name)
        if image_name:
            record.metadata = {
                **(record.metadata or {}),
                "image_found_in_zip": image_name in image_names,
                "image_hash": (image_hashes or {}).get(image_name),
            }


def _save_dataset_record(db: Session | None, result: DatasetAnalysisResponse, *, source_type: str, source_label: str | None = None) -> None:
    if db is None or not hasattr(db, "add"):
        return
    try:
        payload = to_json_payload(result)
        record = DatasetAnalysisRecord(
            dataset_name=result.dataset_name,
            source_type=source_type,
            source_label=source_label,
            overall_score=result.overall_score,
            quality_grade=result.quality_grade,
            findings_count=len(result.findings),
            detail_errors_count=len(result.detail_errors),
            total_records=result.total_records,
            analysis_payload=payload,
        )
        db.add(record)
        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"Dataset history save failed: {exc}")


def _history_item_schema(record: DatasetAnalysisRecord) -> schemas.DatasetHistoryItem:
    return schemas.DatasetHistoryItem(
        id=record.id,
        dataset_name=record.dataset_name,
        source_type=record.source_type,
        source_label=record.source_label,
        overall_score=record.overall_score,
        quality_grade=record.quality_grade,
        findings_count=record.findings_count,
        detail_errors_count=record.detail_errors_count,
        total_records=record.total_records,
        created_at=record.created_at,
    )


def _job_status_schema(job: AnalysisJob) -> schemas.AnalysisJobStatusResponse:
    return schemas.AnalysisJobStatusResponse(
        job_id=job.id,
        status=job.status,
        module_name=job.module_name,
        target=job.target,
        celery_task_id=job.celery_task_id,
        source_record_id=job.source_record_id,
        error_message=job.error_message,
        result=job.result_payload,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


async def _run_dataset_job_inline_if_still_queued(job_id: int, delay_seconds: float = 3.0) -> None:
    await asyncio.sleep(delay_seconds)
    db = SessionLocal()
    try:
        job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
        if not job or job.status != "queued":
            return
        update_job_status(db, job, "running")
        try:
            result = _analyze_dataset_impl(
                job.request_payload or {},
                db=db,
                source_type="json",
                source_label=(job.request_payload or {}).get("dataset_name") or "dataset.json",
            )
            update_job_status(db, job, "completed", result_payload=to_json_payload(result))
        except Exception as exc:
            update_job_status(db, job, "failed", error_message=str(exc))
    finally:
        db.close()


def _dataset_ticket_priority(analysis: DatasetAnalysisResponse) -> str:
    severities = [item.severity for item in analysis.findings] + [item.severity for item in analysis.detail_errors]
    if "high" in severities:
        return "high"
    if "medium" in severities:
        return "medium"
    return "low"


def _dataset_ticket_items(analysis: DatasetAnalysisResponse) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []

    for finding in analysis.findings:
        items.append({
            "source": "dataset_finding",
            "severity": finding.severity,
            "category": finding.category,
            "title": finding.title,
            "description": finding.description,
            "evidence": finding.evidence,
            "recommendation": finding.recommendation,
        })

    for error in analysis.detail_errors:
        items.append({
            "source": "validator_error",
            "severity": error.severity,
            "category": error.error_type,
            "title": error.error_type,
            "description": error.message,
            "evidence": (
                f"image_id={error.image_id or '-'}, annotation_id={error.annotation_id or '-'}, "
                f"field={error.field}, file={error.file_name or '-'}"
            ),
            "recommendation": "Annotation kaydını belirtilen alan ve dosya bağlamında düzelt.",
        })

    for gap in analysis.coverage_gaps:
        items.append({
            "source": "coverage_gap",
            "severity": "medium",
            "category": "coverage",
            "title": gap.title,
            "description": gap.summary,
            "evidence": f"Impacted labels: {', '.join(gap.impacted_labels)}",
            "recommendation": "Etkilenen sınıflar için ek veri toplama veya augmentation planı oluştur.",
        })

    for signal in analysis.duplicate_signals:
        items.append({
            "source": "duplicate_signal",
            "severity": "medium",
            "category": "duplicate",
            "title": "Duplicate dataset signal",
            "description": signal.reason,
            "evidence": f"Record IDs: {', '.join(signal.record_ids)}",
            "recommendation": "Tekrarlı kayıtları deduplicate et veya split leakage etkisini kontrol et.",
        })

    for signal in analysis.suspicious_label_signals:
        items.append({
            "source": "suspicious_label",
            "severity": "medium",
            "category": "label_consistency",
            "title": "Suspicious label signal",
            "description": signal.reason,
            "evidence": f"Record: {signal.record_id}; current_label={signal.current_label}",
            "recommendation": signal.suggested_review,
        })

    for target in analysis.collection_targets:
        items.append({
            "source": "collection_target",
            "severity": "low",
            "category": "data_collection",
            "title": f"Collect more data for {target.label}",
            "description": target.reason,
            "evidence": f"Priority: P{target.priority}",
            "recommendation": "Bu sınıf için hedefli veri toplama planı oluştur.",
        })

    return items


def _build_dataset_ticket_payload(analysis: DatasetAnalysisResponse, provider: str) -> Dict[str, Any]:
    items = _dataset_ticket_items(analysis)
    if not items:
        raise HTTPException(
            status_code=422,
            detail="Bu dataset analizinde ticket'a aktarılacak gerçek finding, validator error veya coverage sinyali bulunamadı.",
        )

    provider_prefix = "JIRA" if provider == "jira" else "SLACK"
    high_count = sum(1 for item in items if item["severity"] == "high")
    medium_count = sum(1 for item in items if item["severity"] == "medium")
    return {
        "provider": provider,
        "ticket_key": f"{provider_prefix}-DATASET-{hashlib.sha1((analysis.dataset_name + str(analysis.total_records) + str(len(items))).encode('utf-8')).hexdigest()[:8].upper()}",
        "title": f"Dataset Quality: {analysis.dataset_name} - {len(items)} gerçek kalite bulgusu",
        "description": analysis.overview,
        "priority": _dataset_ticket_priority(analysis),
        "status": "created",
        "module": "dataset",
        "dataset_name": analysis.dataset_name,
        "quality_grade": analysis.quality_grade,
        "overall_score": analysis.overall_score,
        "total_records": analysis.total_records,
        "summary": {
            "findings_count": len(analysis.findings),
            "detail_errors_count": len(analysis.detail_errors),
            "high_count": high_count,
            "medium_count": medium_count,
        },
        "work_items": items,
    }


@router.post("/tickets/jira")
def create_dataset_jira_ticket(analysis: DatasetAnalysisResponse):
    ticket = _build_dataset_ticket_payload(analysis, "jira")
    return {
        "success": True,
        "provider": "jira",
        "configured": False,
        "ticket": ticket,
        "message": f"{ticket['ticket_key']} dataset analiz çıktısından oluşturuldu.",
    }


@router.post("/upload-analyze", response_model=DatasetAnalysisResponse)
async def upload_and_analyze_dataset(file: UploadFile = File(...), db: Session = Depends(get_db)):
    filename = file.filename or "dataset.zip"
    if not filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Lutfen .zip uzantili bir dataset paketi yukleyin.")

    raw = await file.read()
    if len(raw) > MAX_ZIP_BYTES:
        raise HTTPException(status_code=400, detail="ZIP dosyasi 250 MB limitini asiyor.")
    source_artifact = _write_dataset_artifact("zip", filename, raw)

    try:
        with zipfile.ZipFile(BytesIO(raw)) as archive:
            names = _safe_zip_names(archive)
            image_names = _zip_image_lookup(names)
            image_hashes = _zip_image_hash_lookup(archive, names)

            request = _request_from_zip_archive(archive, names)
            _attach_zip_image_evidence(request, image_names, image_hashes)
            return _analyze_dataset_impl(request, db=db, source_type="zip", source_label=filename, source_artifact=source_artifact)
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=400, detail="Yuklenen dosya gecerli bir ZIP degil.") from exc


@router.post("/analyze", response_model=DatasetAnalysisResponse)
def analyze_dataset(
    request: Any = Body(...),
    db: Session = Depends(get_db),
):
    return _analyze_dataset_impl(request, db=db)


@router.post("/analyze-job", response_model=schemas.AnalysisJobStartResponse)
async def start_dataset_analysis_job(
    request: Any = Body(...),
    db: Session = Depends(get_db),
):
    dataset_name = "Dataset v1"
    if isinstance(request, dict):
        dataset_name = str(request.get("dataset_name") or request.get("name") or dataset_name)

    job = AnalysisJob(
        job_type="dataset_analysis",
        module_name="dataset",
        status="queued",
        target=dataset_name,
        request_payload=request,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    async_result = run_dataset_analysis_task.delay(job.id)
    job.celery_task_id = async_result.id
    db.commit()
    asyncio.create_task(_run_dataset_job_inline_if_still_queued(job.id))

    return schemas.AnalysisJobStartResponse(
        job_id=job.id,
        status=job.status,
        module_name=job.module_name,
        target=job.target,
    )


@router.get("/jobs/{job_id}", response_model=schemas.AnalysisJobStatusResponse)
def get_dataset_job_status(job_id: int, db: Session = Depends(get_db)):
    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id, AnalysisJob.module_name == "dataset").first()
    if not job:
        raise HTTPException(status_code=404, detail="Dataset analysis job not found.")
    return _job_status_schema(job)


def _analyze_dataset_impl(
    request: Any,
    db: Session | None = None,
    source_type: str = "json",
    source_label: str | None = None,
    source_artifact: Dict[str, Any] | None = None,
):
    if source_artifact is None and source_type == "json":
        try:
            artifact_bytes = json.dumps(request, ensure_ascii=False, default=str).encode("utf-8")
            source_artifact = _write_dataset_artifact("json", source_label or "dataset.json", artifact_bytes)
        except Exception as exc:
            print(f"Dataset source artifact save failed: {exc}")

    if not isinstance(request, DatasetAnalyzeRequest):
        try:
            request = _request_from_annotation_payload(request)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc

    records = request.records
    total = len(records)
    
    labels = [record.label.strip() for record in records if record.label and record.label.strip()]
    label_counter = Counter(labels)
    class_distribution = [
        DatasetClassDistributionItem(label=label, count=count, ratio=round(count / max(1, total), 3))
        for label, count in label_counter.most_common()
    ]
    split_counter = Counter((record.split or "unspecified").strip().lower() or "unspecified" for record in records)
    split_health = [
        DatasetSplitHealthItem(split=split_name, count=count, ratio=round(count / max(1, total), 3))
        for split_name, count in split_counter.most_common()
    ]

    findings: List[DatasetFinding] = []
    detail_errors: List[DatasetDetailError] = []
    duplicate_signals: List[DatasetDuplicateSignal] = []
    suspicious_label_signals: List[DatasetSuspiciousLabelSignal] = []
    coverage_gaps: List[DatasetCoverageGap] = []
    collection_targets: List[DatasetCollectionTarget] = []

    missing_label_ids: List[str] = []
    missing_image_ids: List[str] = []
    broken_record_ids: List[str] = []
    invalid_annotation_ids: List[str] = []
    invalid_category_ids: List[str] = []
    split_leakage_ids: List[str] = []
    signatures: Dict[str, List[str]] = defaultdict(list)
    split_by_image_name: Dict[str, set[str]] = defaultdict(set)
    split_by_hash: Dict[str, set[str]] = defaultdict(set)
    text_to_labels: Dict[str, set[str]] = defaultdict(set)
    text_to_ids: Dict[str, List[str]] = defaultdict(list)

    for index, record in enumerate(records):
        rid = _record_id(record, index)
        image_id = (record.metadata or {}).get("image_id") or rid
        file_name = record.image_name
        label = _clean_label(record)
        if not label:
            missing_label_ids.append(rid)
            _add_detail_error(
                detail_errors,
                "missing_label",
                "high",
                "Image/record has no usable label or annotation target.",
                "annotations",
                image_id=image_id,
                file_name=file_name,
            )
        if record.metadata.get("image_found_in_zip") is False:
            missing_image_ids.append(rid)
            _add_detail_error(
                detail_errors,
                "corrupt_image_reference",
                "high",
                "Annotation references an image file that is not present in the ZIP package.",
                "file_name",
                image_id=image_id,
                file_name=file_name,
            )
        if (record.width is not None and record.width <= 0) or (record.height is not None and record.height <= 0):
            broken_record_ids.append(rid)
            _add_detail_error(
                detail_errors,
                "broken_record",
                "high",
                "Record has invalid image width or height.",
                "width_height",
                image_id=image_id,
                file_name=file_name,
                metadata={"width": record.width, "height": record.height},
            )

        for annotation in record.annotations or []:
            annotation_id = annotation.id
            if annotation.category_id is not None:
                invalid_ann_ids = set(record.metadata.get("invalid_category_ids") or [])
                if annotation_id in invalid_ann_ids or str(annotation_id) in {str(item) for item in invalid_ann_ids}:
                    invalid_category_ids.append(rid)
                    _add_detail_error(
                        detail_errors,
                        "invalid_category_id",
                        "high",
                        "Annotation uses a category_id that is not defined in the categories list.",
                        "category_id",
                        image_id=image_id,
                        annotation_id=annotation_id,
                        file_name=file_name,
                        metadata={"category_id": annotation.category_id},
                    )
            bbox_problem = _bbox_problem(record, annotation.bbox)
            if not str(annotation.label or "").strip():
                invalid_annotation_ids.append(rid)
                _add_detail_error(
                    detail_errors,
                    "missing_label",
                    "high",
                    "Annotation has no label.",
                    "label",
                    image_id=image_id,
                    annotation_id=annotation_id,
                    file_name=file_name,
                )
                break
            if bbox_problem:
                invalid_annotation_ids.append(rid)
                _add_detail_error(
                    detail_errors,
                    bbox_problem,
                    "high",
                    "Bounding box is invalid or exceeds image boundaries.",
                    "bbox",
                    image_id=image_id,
                    annotation_id=annotation_id,
                    file_name=file_name,
                    metadata={"bbox": annotation.bbox},
                )
                break

        signatures[_record_signature(record)].append(rid)
        image_key = _normalize_image_name(record.image_name)
        split_name = (record.split or "unspecified").strip().lower() or "unspecified"
        if image_key and split_name != "unspecified":
            split_by_image_name[image_key].add(split_name)
        image_hash = record.metadata.get("image_hash")
        if image_hash and split_name != "unspecified":
            split_by_hash[str(image_hash)].add(split_name)
        text_key = " ".join(str(record.text or "").strip().lower().split())
        if text_key and label:
            text_to_labels[text_key].add(label.lower())
            text_to_ids[text_key].append(rid)

    if missing_label_ids:
        _add_finding(
            findings,
            "high",
            "missing-label",
            "Eksik etiketli kayıtlar bulundu",
            "Bazı kayıtların label alanı boş. Bu durum eğitim sırasında sınıf hedefini belirsiz hale getirir.",
            f"Records: {', '.join(missing_label_ids[:8])}",
            "Etiketsiz kayıtları tamamla veya eğitim setinden ayırıp review kuyruğuna al.",
        )

    if missing_image_ids:
        _add_finding(
            findings,
            "high",
            "missing-image",
            "Annotation görsel dosyası zip içinde bulunamadı",
            "Bazı annotation kayıtları zip paketinde bulunmayan görselleri referans ediyor. Bu durum training loader aşamasında veri kaybına veya hataya yol açabilir.",
            f"Records: {', '.join(missing_image_ids[:8])}",
            "Annotation dosyasındaki image_name değerlerini dataset klasörüyle eşleştir veya eksik görselleri pakete ekle.",
        )

    if broken_record_ids:
        _add_finding(
            findings,
            "high",
            "broken-record",
            "Bozuk kayıt boyutu tespit edildi",
            "Bazı kayıtların genişlik/yükseklik bilgisi geçersiz. Bu durum image loader veya annotation projection hatasına yol açabilir.",
            f"Records: {', '.join(broken_record_ids[:8])}",
            "Kaynak görselleri ve metadata extraction adımını doğrula; width/height değerlerini yeniden üret.",
        )

    if invalid_annotation_ids:
        _add_finding(
            findings,
            "high",
            "annotation-health",
            "Annotation/bounding box sağlığı bozuk",
            "Bazı annotation kayıtlarında eksik label, hatalı bbox uzunluğu, negatif veya taşan boyut sinyali var.",
            f"Records: {', '.join(sorted(set(invalid_annotation_ids))[:8])}",
            "Annotation dosyalarını format validator ile yeniden geçir ve bbox değerlerini görüntü boyutlarıyla hizala.",
        )

    if invalid_category_ids:
        _add_finding(
            findings,
            "high",
            "invalid-category-id",
            "Tanımsız category_id kullanımı bulundu",
            "Bazı COCO annotation kayıtları categories listesinde bulunmayan category_id değerlerini kullanıyor.",
            f"Records: {', '.join(sorted(set(invalid_category_ids))[:8])}",
            "Annotation category_id değerlerini categories sözlüğüyle eşleştir ve hatalı ID'leri düzelt.",
        )

    for ids in signatures.values():
        if len(ids) > 1:
            duplicate_signals.append(
                DatasetDuplicateSignal(
                    id=len(duplicate_signals) + 1,
                    reason="Aynı label/image/text/annotation imzasına sahip kayıtlar bulundu.",
                    record_ids=ids[:6],
                )
            )
            for duplicate_id in ids[1:6]:
                duplicate_record = next((record for record in records if _record_id(record, records.index(record)) == duplicate_id), None)
                _add_detail_error(
                    detail_errors,
                    "duplicate_annotation",
                    "medium",
                    "Record has the same label/image/text/annotation signature as another record.",
                    "annotations",
                    image_id=duplicate_id,
                    file_name=getattr(duplicate_record, "image_name", None),
                    metadata={"duplicate_group": ids[:6]},
                )
    if duplicate_signals:
        _add_finding(
            findings,
            "medium",
            "duplicate-signal",
            "Duplicate veya near-duplicate kayıt sinyali var",
            "Aynı içerik imzasına sahip kayıtlar train/validation davranışını yapay olarak iyileştirebilir.",
            f"Duplicate groups: {len(duplicate_signals)}",
            "Tekrarlı örnekleri deduplicate et veya split'ler arası sızıntı oluşturmadığını doğrula.",
        )

    inconsistent_texts = [(text, labels, text_to_ids[text]) for text, labels in text_to_labels.items() if len(labels) > 1]
    if inconsistent_texts:
        for text, labels_for_text, ids in inconsistent_texts[:5]:
            suspicious_label_signals.append(
                DatasetSuspiciousLabelSignal(
                    id=len(suspicious_label_signals) + 1,
                    record_id=", ".join(ids[:4]),
                    current_label=", ".join(sorted(labels_for_text)),
                    reason=f"Aynı metin/semantik ipucu farklı etiketlerle görünüyor: '{text[:48]}'.",
                    suggested_review="Bu örnekleri manuel review ile doğrula; label mapping veya annotation yönergesi kaymış olabilir.",
                )
            )
        _add_finding(
            findings,
            "medium",
            "label-consistency",
            "Label consistency riski bulundu",
            "Aynı text ipucuna sahip kayıtlar farklı sınıflara atanmış. Bu durum modelin karar sınırını bulanıklaştırır.",
            f"Inconsistent text groups: {len(inconsistent_texts)}",
            "Benzer içeriklerin aynı etiket yönergesine göre işaretlendiğini doğrula.",
        )

    if label_counter:
        max_label, max_count = label_counter.most_common(1)[0]
        max_ratio = max_count / max(1, sum(label_counter.values()))
        if len(label_counter) >= 2 and max_ratio >= 0.72:
            _add_finding(
                findings,
                "high",
                "class-imbalance",
                "Sınıf dağılımı dengesiz",
                "Bir sınıf veri setinin büyük bölümünü kaplıyor. Bu durum modelin çoğunluk sınıfa kaymasına neden olabilir.",
                f"{max_label}: {round(max_ratio * 100, 1)}%",
                "Az temsil edilen sınıflar için veri artır veya sampling/class weight stratejisi uygula.",
            )

        rare_labels = [
            label
            for label, count in label_counter.items()
            if count <= max(1, round(sum(label_counter.values()) * 0.05)) and len(label_counter) >= 3
        ]
        if rare_labels:
            _add_finding(
                findings,
                "medium",
                "rare-class",
                "Nadir sınıf sinyali var",
                "Bazı sınıflar çok az örnekle temsil ediliyor. Bu sınıflarda recall ve genelleme riski oluşur.",
                f"Rare labels: {', '.join(rare_labels[:8])}",
                "Nadir sınıflar için hedefli veri toplama veya synthetic augmentation planı oluştur.",
            )
            coverage_gaps.append(
                DatasetCoverageGap(
                    id=len(coverage_gaps) + 1,
                    title="Nadir sınıf coverage gap",
                    summary="Az temsil edilen sınıflarda model etkisi yüksek olabilir.",
                    impacted_labels=rare_labels[:8],
                )
            )
            for priority, label in enumerate(rare_labels[:5], start=1):
                collection_targets.append(
                    DatasetCollectionTarget(
                        label=label,
                        priority=priority,
                        reason="Bu sınıf veri setinde düşük örnek sayısıyla temsil ediliyor.",
                    )
                )

    specified_splits = {name: count for name, count in split_counter.items() if name != "unspecified"}
    leaked_image_names = {name: splits for name, splits in split_by_image_name.items() if len(splits) > 1}
    leaked_hashes = {image_hash: splits for image_hash, splits in split_by_hash.items() if len(splits) > 1}
    if leaked_image_names or leaked_hashes:
        split_leakage_ids = sorted(set(leaked_image_names) | set(leaked_hashes))
        for leak_key, splits in list(leaked_image_names.items())[:8]:
            _add_detail_error(
                detail_errors,
                "split_leakage",
                "high",
                "Same image reference appears in more than one split.",
                "split",
                file_name=leak_key,
                metadata={"splits": sorted(splits)},
            )
        for leak_key, splits in list(leaked_hashes.items())[:8]:
            _add_detail_error(
                detail_errors,
                "split_leakage",
                "high",
                "Same image hash appears in more than one split.",
                "split",
                metadata={"image_hash": leak_key, "splits": sorted(splits)},
            )
        _add_finding(
            findings,
            "high",
            "split-leakage",
            "Split leakage sinyali bulundu",
            "Aynı görsel referansı veya görsel hash'i birden fazla split içinde görünüyor.",
            f"Leakage keys: {', '.join(split_leakage_ids[:8])}",
            "Train/validation/test split'lerini yeniden üret ve aynı görselin farklı split'lere sızmadığını doğrula.",
        )

    if len(specified_splits) >= 2:
        split_total = sum(specified_splits.values())
        low_splits = [name for name, count in specified_splits.items() if count / max(1, split_total) < 0.08]
        high_splits = [name for name, count in specified_splits.items() if count / max(1, split_total) > 0.86]
        if low_splits or high_splits:
            _add_finding(
                findings,
                "medium",
                "split-balance",
                "Train/validation/test split dengesi zayıf",
                "Split dağılımı sağlıklı değerlendirme için dengesiz görünüyor.",
                f"Low: {', '.join(low_splits) or 'none'}; High: {', '.join(high_splits) or 'none'}",
                "Train/validation/test oranlarını yeniden dengele ve duplicate örneklerin split'ler arasında sızmadığını kontrol et.",
            )

    score_breakdown = _score_from_findings(findings)
    completeness = score_breakdown.completeness
    balance = score_breakdown.balance
    consistency = score_breakdown.consistency
    validity = score_breakdown.validity
    annotation_health = score_breakdown.annotation_health
    overall_score = round((completeness + balance + consistency + validity + annotation_health) / 5)

    training_risks = []
    if findings:
        high_count = sum(1 for item in findings if item.severity == "high")
        training_risks.append(DatasetTrainingRisk(
            severity="high" if high_count else "medium",
            summary="Dataset kalite sinyalleri model doğruluğu, validation güvenilirliği ve sınıf bazlı recall üzerinde risk oluşturuyor.",
            impacted_areas=["model performance", "validation stability", "class-level recall"]
        ))

    synthetic_suggestions = [
        f"{target.label} sınıfı için kontrollü augmentation veya ek veri toplama planı oluştur."
        for target in collection_targets[:4]
    ]

    result = DatasetAnalysisResponse(
        dataset_name=request.dataset_name,
        total_records=total,
        overall_score=overall_score,
        quality_grade=_grade(overall_score),
        overview=f"Dataset analizi {len(findings)} kalite sorunu tespit etti.",
        ai_interpretation=(
            "Deterministik kalite kuralları; eksik etiket, annotation sağlığı, duplicate, "
            "label consistency, split dengesi ve sınıf dağılımı sinyallerini birlikte yorumladı."
        ),
        training_risk_summary=training_risks[0].summary if training_risks else "Belirgin eğitim riski sinyali görülmedi.",
        score_breakdown=DatasetScoreBreakdown(
            completeness=completeness,
            balance=balance,
            consistency=consistency,
            validity=validity,
            annotation_health=annotation_health,
        ),
        findings=findings,
        detail_errors=detail_errors,
        class_distribution=class_distribution,
        split_health=split_health,
        coverage_gaps=coverage_gaps,
        duplicate_signals=duplicate_signals,
        suspicious_label_signals=suspicious_label_signals,
        synthetic_data_suggestions=synthetic_suggestions,
        collection_targets=collection_targets,
        model_impact_summary=(
            "Kalite bulguları arttıkça modelin genelleme kabiliyeti, minority-class recall ve "
            "validation metriklerinin güvenilirliği düşebilir."
            if findings
            else "Bu örneklemde model eğitimini doğrudan zayıflatacak belirgin kalite sinyali görülmedi."
        ),
        training_risks=training_risks,
        source_artifact=source_artifact,
    )
    _save_dataset_record(db, result, source_type=source_type, source_label=source_label)
    return result


@router.get("/history", response_model=List[schemas.DatasetHistoryItem])
def get_dataset_history(limit: int = 20, db: Session = Depends(get_db)):
    records = (
        db.query(DatasetAnalysisRecord)
        .order_by(DatasetAnalysisRecord.created_at.desc())
        .limit(max(1, min(limit, 100)))
        .all()
    )
    return [_history_item_schema(record) for record in records]


@router.get("/history/{record_id}", response_model=schemas.DatasetHistoryDetail)
def get_dataset_history_detail(record_id: int, db: Session = Depends(get_db)):
    record = db.query(DatasetAnalysisRecord).filter(DatasetAnalysisRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Dataset analysis history record not found.")
    return schemas.DatasetHistoryDetail(
        id=record.id,
        dataset_name=record.dataset_name,
        source_type=record.source_type,
        source_label=record.source_label,
        created_at=record.created_at,
        analysis=record.analysis_payload,
    )
