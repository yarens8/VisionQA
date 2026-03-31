from collections import Counter, defaultdict
from typing import Any, Dict, List

from fastapi import APIRouter

from schemas import (
    DatasetAnalysisResponse,
    DatasetAnalyzeRequest,
    DatasetClassDistributionItem,
    DatasetCollectionTarget,
    DatasetCoverageGap,
    DatasetDuplicateSignal,
    DatasetFinding,
    DatasetScoreBreakdown,
    DatasetSplitHealthItem,
    DatasetSuspiciousLabelSignal,
    DatasetTrainingRisk,
)

router = APIRouter(prefix="/dataset", tags=["dataset"])


def _add_finding(
    findings: List[DatasetFinding],
    severity: str,
    category: str,
    title: str,
    description: str,
    evidence: str,
    recommendation: str,
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


@router.post("/analyze", response_model=DatasetAnalysisResponse)
def analyze_dataset(request: DatasetAnalyzeRequest):
    records = request.records
    findings: List[DatasetFinding] = []
    duplicate_signals: List[DatasetDuplicateSignal] = []
    suspicious_signals: List[DatasetSuspiciousLabelSignal] = []
    training_risks: List[DatasetTrainingRisk] = []
    coverage_gaps: List[DatasetCoverageGap] = []
    collection_targets: List[DatasetCollectionTarget] = []

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

    missing_label_records = [record.id or f"row-{index+1}" for index, record in enumerate(records) if not (record.label or "").strip()]
    if missing_label_records:
        _add_finding(
            findings,
            "high",
            "missing-label",
            "Etiketi eksik kayitlar var",
            "Etiketsiz kayitlar model egitiminde belirsiz hedefler yaratir.",
            ", ".join(missing_label_records[:6]),
            "Eksik label alanlarini doldur veya bu kayitlari egitim disina al.",
        )

    broken_records = []
    annotation_issues = 0
    text_grouped: Dict[str, set[str]] = defaultdict(set)
    fingerprint_map: Dict[str, List[str]] = defaultdict(list)
    for index, record in enumerate(records):
        record_id = record.id or f"row-{index+1}"
        if record.text:
            text_grouped[record.text.strip().lower()].add((record.label or "").strip().lower())
        fingerprint = "|".join(
            [
                (record.image_name or "").strip().lower(),
                (record.text or "").strip().lower(),
                (record.label or "").strip().lower(),
            ]
        )
        if fingerprint.strip("|"):
            fingerprint_map[fingerprint].append(record_id)

        if (record.width is not None and record.width <= 0) or (record.height is not None and record.height <= 0):
            broken_records.append(record_id)
        for ann in record.annotations:
            bbox = ann.bbox or []
            if bbox and len(bbox) != 4:
                annotation_issues += 1
            elif bbox and any(value < 0 for value in bbox):
                annotation_issues += 1
            elif bbox and record.width and record.height:
                x, y, w, h = bbox
                if x + w > record.width or y + h > record.height or w <= 0 or h <= 0:
                    annotation_issues += 1

    if broken_records:
        _add_finding(
            findings,
            "high",
            "broken-record",
            "Format veya boyut problemi olan kayitlar var",
            "Bazi kayitlar negatif/bozuk boyut gibi validation hatalari tasiyor.",
            ", ".join(broken_records[:6]),
            "Parse pipeline'ini ve image metadata alanlarini dogrula.",
        )

    if annotation_issues:
        _add_finding(
            findings,
            "medium",
            "annotation-health",
            "Bounding box/annotation sorunlari tespit edildi",
            "Annotation alanlarinda format veya koordinat sagligi bozuk olan kayitlar var.",
            f"Problemli annotation sayisi: {annotation_issues}",
            "BBox formatini standardize et ve image size sinirlarini validate et.",
        )

    if class_distribution:
        max_count = class_distribution[0].count
        min_count = class_distribution[-1].count
        if len(class_distribution) > 1 and max_count >= max(2, min_count * 4):
            _add_finding(
                findings,
                "high",
                "class-imbalance",
                "Sinif dagilimi dengesiz",
                "Baskin sinif ile en kucuk sinif arasinda belirgin oransal fark var.",
                f"Max {class_distribution[0].label}:{max_count}, Min {class_distribution[-1].label}:{min_count}",
                "Az temsil edilen siniflar icin veri toplama, augmentation veya weighted sampling dusun.",
            )
        tiny_classes = [item.label for item in class_distribution if item.ratio <= 0.08]
        if tiny_classes:
            _add_finding(
                findings,
                "medium",
                "rare-class",
                "Kirilgan az ornekli siniflar var",
                "Bazi siniflar egitimde kararsiz performans uretecek kadar az ornekle temsil ediliyor.",
                ", ".join(tiny_classes[:6]),
                "Bu siniflar icin veri artirma veya hedefli toplama plani cikar.",
            )
            coverage_gaps.append(
                DatasetCoverageGap(
                    id=len(coverage_gaps) + 1,
                    title="Rare class coverage zayif",
                    summary="Az temsil edilen siniflar modelin karar sinirinda kirilganlik yaratabilir.",
                    impacted_labels=tiny_classes[:6],
                )
            )

    if split_health and split_health[0].ratio >= 0.85:
        dominant_split = split_health[0]
        _add_finding(
            findings,
            "medium",
            "split-balance",
            "Split dagilimi dengesiz gorunuyor",
            "Train/val/test dagilimi asiri tek tarafa yigiliyor; bu validation guvenilirligini azaltabilir.",
            f"Dominant split: {dominant_split.split} ({dominant_split.count})",
            "Validation ve test splitlerini daha temsil edici sekilde ayir.",
        )
        coverage_gaps.append(
            DatasetCoverageGap(
                id=len(coverage_gaps) + 1,
                title="Validation coverage sinirli olabilir",
                summary="Split dagilimi asiri train agirlikli ise model genelleme kalitesini okumak zorlasir.",
                impacted_labels=[dominant_split.split],
            )
        )

    inconsistent_texts = []
    for text_value, grouped_labels in text_grouped.items():
        normalized_labels = {label for label in grouped_labels if label}
        if len(normalized_labels) > 1:
            inconsistent_texts.append((text_value[:40], sorted(normalized_labels)))
    if inconsistent_texts:
        preview = "; ".join(f"{text} -> {','.join(labels)}" for text, labels in inconsistent_texts[:4])
        _add_finding(
            findings,
            "medium",
            "label-consistency",
            "Ayni icerik farkli etiketlerle isaretlenmis",
            "Benzer text/content fingerprintleri birden fazla label ile gorunuyor.",
            preview,
            "Label taxonomy'sini temizle ve annotation guideline'ini netlestir.",
        )
        for index, (text_value, grouped_labels) in enumerate(inconsistent_texts[:6], start=1):
            suspicious_signals.append(
                DatasetSuspiciousLabelSignal(
                    id=index,
                    record_id=text_value,
                    current_label=", ".join(grouped_labels),
                    reason="Ayni text veya icerik farkli siniflarla eslenmis.",
                    suggested_review="Bu kayit grubunu manuel annotation review listesine ekle.",
                )
            )

    duplicate_candidates = [ids for ids in fingerprint_map.values() if len(ids) > 1]
    for index, ids in enumerate(duplicate_candidates[:8], start=1):
        duplicate_signals.append(
            DatasetDuplicateSignal(
                id=index,
                reason="Ayni image/text/label fingerprint birden fazla kez gorundu.",
                record_ids=ids[:6],
            )
        )
    if duplicate_signals:
        _add_finding(
            findings,
            "medium",
            "duplicate-signal",
            "Muhtemel tekrar eden kayitlar var",
            "Tekrarlayan ornekler modelin belirli kaliplari gereksiz agirlikla ogrenmesine yol acabilir.",
            f"Duplicate groups: {len(duplicate_signals)}",
            "Exact veya near-duplicate temizligi icin deduplication adimi ekle.",
        )
        coverage_gaps.append(
            DatasetCoverageGap(
                id=len(coverage_gaps) + 1,
                title="Cesitlilik kaybi riski",
                summary="Tekrarlayan ornekler dataset cesitliligini dusurup modeli dar kaliplara sabitleyebilir.",
                impacted_labels=[signal.record_ids[0] for signal in duplicate_signals[:3]],
            )
        )

    completeness = max(0, 100 - int((len(missing_label_records) / max(1, total)) * 100) - min(20, len(broken_records) * 5))
    balance = 100
    if len(class_distribution) > 1:
        balance = max(0, 100 - int((class_distribution[0].ratio - class_distribution[-1].ratio) * 100))
    consistency = max(0, 100 - len(inconsistent_texts) * 12 - len(duplicate_signals) * 6)
    validity = max(0, 100 - len(broken_records) * 12 - annotation_issues * 4)
    annotation_health = max(0, 100 - annotation_issues * 6)
    overall_score = round((completeness + balance + consistency + validity + annotation_health) / 5)

    if any(f.category == "class-imbalance" for f in findings):
        training_risks.append(
            DatasetTrainingRisk(
                severity="high",
                summary="Sinif dengesizligi modelin baskin sinifa kaymasina neden olabilir.",
                impacted_areas=["precision/recall dengesizligi", "rare class performansi", "bias riski"],
            )
        )
    if missing_label_records or broken_records:
        training_risks.append(
            DatasetTrainingRisk(
                severity="medium",
                summary="Eksik veya bozuk kayitlar egitim sinyalini kirli hale getirir.",
                impacted_areas=["label noise", "unstable convergence", "validation drift"],
            )
        )
    if suspicious_signals:
        training_risks.append(
            DatasetTrainingRisk(
                severity="medium",
                summary="Supheli veya tutarsiz etiketler modelin karar sinirini bulandurabilir.",
                impacted_areas=["class confusion", "false positive artisi"],
            )
        )
    if not training_risks:
        training_risks.append(
            DatasetTrainingRisk(
                severity="low",
                summary="Dataset temel validation seviyesinde saglikli gorunuyor.",
                impacted_areas=["low immediate training risk"],
            )
        )

    weakest_classes = [item.label for item in class_distribution if item.ratio <= 0.1][:4]
    synthetic_suggestions = []
    for index, label in enumerate(weakest_classes, start=1):
        collection_targets.append(
            DatasetCollectionTarget(
                label=label,
                priority=index,
                reason="Bu sinif veri dagiliminda zayif temsil ediliyor ve augmentation/distribution guclendirmesi gerektiriyor.",
            )
        )
    if weakest_classes:
        synthetic_suggestions.append(f"Az temsil edilen siniflar icin hedefli augmentation veya synthetic generation dusun: {', '.join(weakest_classes)}.")
    if duplicate_signals:
        synthetic_suggestions.append("Tekrarlayan ornekleri azaltip yerlerine cesitli yeni ornekler eklemek daha saglikli dagilim verir.")
    if not synthetic_suggestions:
        synthetic_suggestions.append("Mevcut dagilim kabul edilebilir; bir sonraki adim hard-case ornekleri toplayarak veri cesitliligini arttirmak olabilir.")

    ai_interpretation = (
        "Dataset sadece satir sagligi degil, egitim riski acisindan da analiz edildi. "
        "En kritik sorunlar genelde eksik etiket, sinif dengesizligi ve tutarsiz annotation kaliplari etrafinda toplaniyor."
        if findings
        else "Dataset temel kalite sinyallerinde temiz gorunuyor; bu haliyle baseline egitim icin uygun bir baslangic olabilir."
    )
    training_risk_summary = " ".join(risk.summary for risk in training_risks[:3])
    model_impact_summary = (
        "Bu dataset yapisi modelde en cok rare-class kacirma, class confusion ve validation yanilsamasi riski uretebilir."
        if findings
        else "Dataset mevcut haliyle temel model egitimi icin dengeli bir baslangic sinyali veriyor."
    )

    return DatasetAnalysisResponse(
        dataset_name=request.dataset_name,
        total_records=total,
        overall_score=overall_score,
        quality_grade=_grade(overall_score),
        overview=f"Dataset analizi {len(findings)} bulgu, {len(duplicate_signals)} duplicate sinyali ve {len(suspicious_signals)} supheli etiket sinyali uretti.",
        ai_interpretation=ai_interpretation,
        training_risk_summary=training_risk_summary,
        score_breakdown=DatasetScoreBreakdown(
            completeness=completeness,
            balance=balance,
            consistency=consistency,
            validity=validity,
            annotation_health=annotation_health,
        ),
        findings=findings,
        class_distribution=class_distribution,
        split_health=split_health,
        coverage_gaps=coverage_gaps,
        duplicate_signals=duplicate_signals,
        suspicious_label_signals=suspicious_signals,
        synthetic_data_suggestions=synthetic_suggestions,
        collection_targets=collection_targets,
        model_impact_summary=model_impact_summary,
        training_risks=training_risks,
    )
