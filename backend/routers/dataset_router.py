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

    # İstatistikleri LLM için metin olarak hazırla
    stats_text = f"Total Records: {total}\n"
    stats_text += "Class Distribution:\n"
    for cd in class_distribution:
        stats_text += f" - {cd.label}: {cd.count} (Ratio: {cd.ratio})\n"
    stats_text += "Split Distribution:\n"
    for sh in split_health:
        stats_text += f" - {sh.split}: {sh.count} (Ratio: {sh.ratio})\n"
        
    # Örnek kayıtları hazırla (çok uzun olmaması için max 10 kayıt)
    import json
    sample_records_list = []
    for r in records[:10]:
        sample_records_list.append({
            "id": r.id,
            "label": r.label,
            "text": r.text,
            "split": r.split,
            "width": r.width,
            "height": r.height,
            "annotations": [
                {"label": ann.label, "bbox": ann.bbox} for ann in r.annotations
            ]
        })
    sample_records_text = json.dumps(sample_records_list, indent=2)

    # LLM ile analiz et (Gerçek AI benchmark için deterministic yerine LLM kullanıyoruz)
    import asyncio
    from core.models.llm_client import LLMClient
    
    llm = LLMClient()
    # FastAPI thread-pool'unda çalıştığı için event loop oluşturup çalıştırabiliriz
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    if loop.is_running():
        # Eger zaten bir loop calisiyorsa (uvicorn vb.), thread pool executor icinde asyncio calistirmaliyiz
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, llm.evaluate_dataset_quality(stats_text, sample_records_text))
            ai_result = future.result()
    else:
        ai_result = loop.run_until_complete(llm.evaluate_dataset_quality(stats_text, sample_records_text))

    findings_data = ai_result.get("findings", [])
    score_data = ai_result.get("score_breakdown", {})
    
    findings: List[DatasetFinding] = []
    for index, f in enumerate(findings_data, start=1):
        findings.append(DatasetFinding(
            id=index,
            title=f.get("title", "AI Bulcusu"),
            severity=f.get("severity", "medium"),
            category=f.get("category", "unknown"),
            description=f.get("description", ""),
            evidence=f.get("evidence", ""),
            recommendation=f.get("recommendation", "")
        ))

    completeness = score_data.get("completeness", 80)
    balance = score_data.get("balance", 80)
    consistency = score_data.get("consistency", 80)
    validity = score_data.get("validity", 80)
    annotation_health = score_data.get("annotation_health", 80)
    overall_score = round((completeness + balance + consistency + validity + annotation_health) / 5)

    training_risks = []
    if findings:
        training_risks.append(DatasetTrainingRisk(
            severity="medium",
            summary=ai_result.get("training_risk_summary", "Model eğitimi için bazı riskler bulundu."),
            impacted_areas=["model performance", "validation stability"]
        ))

    return DatasetAnalysisResponse(
        dataset_name=request.dataset_name,
        total_records=total,
        overall_score=overall_score,
        quality_grade=_grade(overall_score),
        overview=f"LLM Analizi {len(findings)} kalite sorunu tespit etti.",
        ai_interpretation="Bu analiz Groq/LLM motoru tarafindan istatistikler ve sample'lar incelenerek tamamen otonom uretilmistir.",
        training_risk_summary=ai_result.get("training_risk_summary", ""),
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
        coverage_gaps=[],
        duplicate_signals=[],
        suspicious_label_signals=[],
        synthetic_data_suggestions=[],
        collection_targets=[],
        model_impact_summary=ai_result.get("model_impact_summary", ""),
        training_risks=training_risks,
    )
