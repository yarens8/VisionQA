from __future__ import annotations

import io
from dataclasses import dataclass
from statistics import median
from typing import Dict, List, Optional

from PIL import Image, ImageDraw

from core.accessibility.engine import (
    ComponentCandidate,
    _component_display_name,
    _crop_to_base64,
    _detect_component_candidates,
    _image_to_base64,
    _normalize_base64_image,
)


@dataclass
class UiuxIssue:
    title: str
    severity: str
    category: str
    description: str
    recommendation: str
    candidate: ComponentCandidate


SEVERITY_BORDER = {
    "high": (248, 113, 113, 235),
    "medium": (251, 191, 36, 235),
    "low": (96, 165, 250, 235),
    "pass": (52, 211, 153, 235),
}


def _component_box(candidate: ComponentCandidate) -> Dict[str, int]:
    return {
        "x": int(candidate.x),
        "y": int(candidate.y),
        "width": int(candidate.width),
        "height": int(candidate.height),
    }


def _zone_candidate(x: int, y: int, width: int, height: int, label: str = "content-block") -> ComponentCandidate:
    return ComponentCandidate(
        x=max(0, int(x)),
        y=max(0, int(y)),
        width=max(1, int(width)),
        height=max(1, int(height)),
        label=label,
        confidence=0.72,
        contrast_ratio=4.5,
        dominant_dark="#111827",
        dominant_light="#f8fafc",
        severity="medium",
        description="UI/UX bolgesi",
        pixel_density=0.0,
        cluster_size=1,
        text_hint="",
        text_region_count=0,
    )


def _role_name(candidate: ComponentCandidate, image_width: int, image_height: int) -> str:
    return _component_display_name(candidate, image_width, image_height).strip()


def _penalty(severity: str) -> int:
    if severity == "high":
        return 24
    if severity == "medium":
        return 14
    if severity == "low":
        return 8
    return 0


def _cluster_by_left_edge(candidates: List[ComponentCandidate], threshold: int) -> List[List[ComponentCandidate]]:
    groups: List[List[ComponentCandidate]] = []
    for candidate in sorted(candidates, key=lambda item: (item.x, item.y)):
        target_group: Optional[List[ComponentCandidate]] = None
        for group in groups:
            group_left = median([item.x for item in group])
            if abs(candidate.x - group_left) <= threshold:
                target_group = group
                break
        if target_group is None:
            groups.append([candidate])
        else:
            target_group.append(candidate)

    return [sorted(group, key=lambda item: item.y) for group in groups if len(group) >= 2]


def _cluster_by_row(candidates: List[ComponentCandidate], threshold: int) -> List[List[ComponentCandidate]]:
    groups: List[List[ComponentCandidate]] = []
    for candidate in sorted(candidates, key=lambda item: (item.y, item.x)):
        center_y = candidate.y + candidate.height / 2
        target_group: Optional[List[ComponentCandidate]] = None
        for group in groups:
            group_center = median([item.y + item.height / 2 for item in group])
            if abs(center_y - group_center) <= threshold:
                target_group = group
                break
        if target_group is None:
            groups.append([candidate])
        else:
            target_group.append(candidate)

    return [sorted(group, key=lambda item: item.x) for group in groups if len(group) >= 2]


def _meaningful_candidates(image: Image.Image) -> List[ComponentCandidate]:
    width, height = image.size
    candidates = _detect_component_candidates(image)
    filtered: List[ComponentCandidate] = []
    for candidate in candidates:
        if candidate.width < max(42, int(width * 0.1)):
            continue
        if candidate.height < max(18, int(height * 0.035)):
            continue
        area_ratio = (candidate.width * candidate.height) / max(width * height, 1)
        if area_ratio > 0.82:
            continue
        filtered.append(candidate)
    return filtered[:12]


def _foreground_ratio(image: Image.Image, region: tuple[int, int, int, int]) -> float:
    left, top, right, bottom = region
    crop = image.crop((max(0, left), max(0, top), max(left + 1, right), max(top + 1, bottom))).convert("RGB")
    pixels = crop.load()
    width, height = crop.size
    if width <= 0 or height <= 0:
        return 0.0

    background = crop.getpixel((0, 0))
    foreground = 0
    total = width * height
    for y in range(height):
        for x in range(width):
            rgb = pixels[x, y]
            if sum(abs(int(channel) - int(bg)) for channel, bg in zip(rgb, background)) > 54:
                foreground += 1
    return foreground / max(total, 1)


def _fallback_structure_issues(image: Image.Image, image_width: int, image_height: int) -> List[UiuxIssue]:
    issues: List[UiuxIssue] = []
    hero_height = max(1, int(image_height * 0.55))
    left_ratio = _foreground_ratio(image, (0, 0, image_width // 2, hero_height))
    right_ratio = _foreground_ratio(image, (image_width // 2, 0, image_width, hero_height))
    imbalance = abs(left_ratio - right_ratio)

    if imbalance >= 0.08:
        heavier_side = "sag" if right_ratio > left_ratio else "sol"
        issues.append(
            UiuxIssue(
                title="Hero alani tek tarafa yigiliyor",
                severity="medium" if imbalance < 0.15 else "high",
                category="alignment",
                description=(
                    f"Ust bolgedeki gorsel agirlik {heavier_side} tarafa belirgin sekilde kaymis. "
                    "Bu durum hero alaninda denge ve hizalama hissini zayiflatabilir."
                ),
                recommendation="Hero alanindaki ana mesaj, form ve gorsel bloklarin agirligini iki kolon arasinda daha dengeli dagit.",
                candidate=_zone_candidate(0, 0, image_width, hero_height, "hero-panel"),
            )
        )

    top_ratio = _foreground_ratio(image, (0, 0, image_width, hero_height))
    bottom_ratio = _foreground_ratio(image, (0, hero_height, image_width, image_height))
    density_jump = abs(top_ratio - bottom_ratio)
    if density_jump >= 0.07:
        issues.append(
            UiuxIssue(
                title="Bolumler arasi yogunluk ani degisiyor",
                severity="medium",
                category="spacing",
                description=(
                    "Ust hero bolgesi ile alt icerik alani arasinda gorsel yogunluk bir anda degisiyor. "
                    "Bu kirilim sayfa ritmini sertlestirip akis hissini zayiflatabilir."
                ),
                recommendation="Hero ile alt liste/grid bolgesi arasina daha net gecis boslugu veya ara katman ekleyerek ritmi yumusat.",
                candidate=_zone_candidate(0, max(0, hero_height - int(image_height * 0.12)), image_width, int(image_height * 0.22)),
            )
        )

    bottom_left_ratio = _foreground_ratio(image, (0, hero_height, image_width // 2, image_height))
    bottom_right_ratio = _foreground_ratio(image, (image_width // 2, hero_height, image_width, image_height))
    bottom_imbalance = abs(bottom_left_ratio - bottom_right_ratio)
    if bottom_imbalance >= 0.05:
        heavier_side = "sag" if bottom_right_ratio > bottom_left_ratio else "sol"
        issues.append(
            UiuxIssue(
                title="Alt icerik dengesi esit dagilmiyor",
                severity="low" if bottom_imbalance < 0.1 else "medium",
                category="consistency",
                description=(
                    f"Alt bolgedeki icerik yogunlugu {heavier_side} tarafta toplanmis gorunuyor. "
                    "Bu dagilim kart veya kategori bloklarinda tutarli bir denge hissi vermeyebilir."
                ),
                recommendation="Alt bolgedeki kart ve kategori bloklarini esit kolon mantigi ile gruplayip bosluklari daha dengeli dagit.",
                candidate=_zone_candidate(0, hero_height, image_width, image_height - hero_height),
            )
        )

    return issues


def _find_alignment_issue(candidates: List[ComponentCandidate], image_width: int, image_height: int) -> Optional[UiuxIssue]:
    cluster_threshold = max(20, int(image_width * 0.06))
    deviation_threshold = max(14, int(image_width * 0.035))
    best_issue: Optional[UiuxIssue] = None
    best_delta = 0.0

    for group in _cluster_by_left_edge(candidates, cluster_threshold):
        if len(group) < 3:
            continue

        baseline = float(median([item.x for item in group]))
        for candidate in group:
            delta = abs(candidate.x - baseline)
            if delta <= deviation_threshold:
                continue

            severity = "high" if delta >= deviation_threshold * 1.7 else "medium"
            role_name = _role_name(candidate, image_width, image_height)
            issue = UiuxIssue(
                title="Sol hizalama ritmi kiriliyor",
                severity=severity,
                category="alignment",
                description=(
                    f"Benzer dikey akistaki {role_name} beklenen sol baslangic kolonundan yaklasik "
                    f"{int(round(delta))} px sapmis gorunuyor. Bu sapma ekranda daginik bir ritim olusturur."
                ),
                recommendation="Ayni akistaki kart, form ve metin bloklarini ortak bir sol kenar veya grid kolonu uzerine sabitle.",
                candidate=candidate,
            )
            if delta > best_delta:
                best_delta = delta
                best_issue = issue

    return best_issue


def _find_spacing_issue(candidates: List[ComponentCandidate], image_width: int, image_height: int) -> Optional[UiuxIssue]:
    column_threshold = max(20, int(image_width * 0.06))
    best_issue: Optional[UiuxIssue] = None
    best_delta = 0.0

    for group in _cluster_by_left_edge(candidates, column_threshold):
        if len(group) < 3:
            continue

        gaps = []
        for current, next_candidate in zip(group, group[1:]):
            gap = next_candidate.y - (current.y + current.height)
            if gap >= 0:
                gaps.append((current, next_candidate, gap))

        if len(gaps) < 2:
            continue

        baseline_gap = float(median([gap for _, _, gap in gaps]))
        deviation_threshold = max(10, int(max(baseline_gap, 12) * 0.25))

        for _, candidate, gap in gaps:
            delta = abs(gap - baseline_gap)
            if delta <= deviation_threshold:
                continue

            severity = "medium" if gap > baseline_gap else "low"
            role_name = _role_name(candidate, image_width, image_height)
            issue = UiuxIssue(
                title="Dikey spacing tutarliligi bozuluyor",
                severity=severity,
                category="spacing",
                description=(
                    f"Ayni dikey akistaki bosluk ritmi kiriliyor. {role_name} oncesindeki aralik yaklasik "
                    f"{int(round(gap))} px; grubun geri kalaninda ise referans aralik {int(round(baseline_gap))} px civarinda."
                ),
                recommendation="Ayni icerik akisi icin tek bir spacing token belirle ve bloklar arasi bosluklari o ritimde tut.",
                candidate=candidate,
            )
            if delta > best_delta:
                best_delta = delta
                best_issue = issue

    return best_issue


def _find_consistency_issue(candidates: List[ComponentCandidate], image_width: int, image_height: int) -> Optional[UiuxIssue]:
    row_threshold = max(18, int(image_height * 0.04))
    best_issue: Optional[UiuxIssue] = None
    best_ratio = 0.0

    for group in _cluster_by_row(candidates, row_threshold):
        if len(group) < 3:
            continue

        baseline_width = float(median([item.width for item in group]))
        if baseline_width <= 0:
            continue

        for candidate in group:
            delta_ratio = abs(candidate.width - baseline_width) / baseline_width
            if delta_ratio <= 0.22:
                continue

            severity = "medium" if delta_ratio >= 0.38 else "low"
            role_name = _role_name(candidate, image_width, image_height)
            issue = UiuxIssue(
                title="Ayni satirdaki boyut dili ayrisiyor",
                severity=severity,
                category="consistency",
                description=(
                    f"Ayni satirdaki benzer ogeler arasinda genislik dili tutarli degil. {role_name} "
                    f"beklenen genislikten yaklasik %{int(round(delta_ratio * 100))} oraninda sapmis."
                ),
                recommendation="Ayni satirdaki kart, buton veya bilgi bloklari icin ortak genislik kurali kullan ve outlier ogeleri normalize et.",
                candidate=candidate,
            )
            if delta_ratio > best_ratio:
                best_ratio = delta_ratio
                best_issue = issue

    return best_issue


def _render_overlay(image: Image.Image, issues: List[UiuxIssue]) -> str:
    overlay = image.convert("RGBA")
    draw = ImageDraw.Draw(overlay, "RGBA")

    for index, issue in enumerate(issues, start=1):
        color = SEVERITY_BORDER.get(issue.severity, SEVERITY_BORDER["low"])
        candidate = issue.candidate
        region = (
            candidate.x,
            candidate.y,
            candidate.x + candidate.width,
            candidate.y + candidate.height,
        )
        draw.rectangle(region, outline=color, width=3)
        badge_region = (candidate.x, max(0, candidate.y - 22), candidate.x + 26, max(0, candidate.y) + 4)
        draw.rounded_rectangle(badge_region, radius=8, fill=color)
        draw.text((candidate.x + 8, max(0, candidate.y - 18)), str(index), fill=(15, 23, 42, 255))

    return _image_to_base64(overlay)


class UiuxEngine:
    def analyze_image(self, image_base64: str, platform: str = "web") -> Dict:
        image_bytes = _normalize_base64_image(image_base64)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image_width, image_height = image.size
        candidates = _meaningful_candidates(image)

        issues = []
        for resolver in (
            _find_alignment_issue,
            _find_spacing_issue,
            _find_consistency_issue,
        ):
            issue = resolver(candidates, image_width, image_height)
            if issue:
                issues.append(issue)

        if len(issues) < 2:
            existing_categories = {issue.category for issue in issues}
            for fallback_issue in _fallback_structure_issues(image, image_width, image_height):
                if fallback_issue.category in existing_categories:
                    continue
                issues.append(fallback_issue)
                existing_categories.add(fallback_issue.category)
                if len(issues) >= 3:
                    break

        findings = []
        for index, issue in enumerate(issues, start=1):
            box = _component_box(issue.candidate)
            findings.append(
                {
                    "id": index,
                    "title": issue.title,
                    "severity": issue.severity,
                    "category": issue.category,
                    "affected_role": _role_name(issue.candidate, image_width, image_height),
                    "description": issue.description,
                    "bounding_box": box,
                    "crop_image_base64": _crop_to_base64(
                        image,
                        box["x"],
                        box["y"],
                        box["width"],
                        box["height"],
                    ),
                    "recommendation": issue.recommendation,
                }
            )

        alignment_score = max(52, 100 - sum(_penalty(issue.severity) for issue in issues if issue.category == "alignment"))
        spacing_score = max(52, 100 - sum(_penalty(issue.severity) for issue in issues if issue.category == "spacing"))
        consistency_score = max(52, 100 - sum(_penalty(issue.severity) for issue in issues if issue.category == "consistency"))
        overall_score = round((alignment_score + spacing_score + consistency_score) / 3)

        if findings:
            overview = (
                f"UI/UX taramasi {len(findings)} duzen problemi yakaladi. "
                f"En belirgin sinyaller hizalama, spacing ve boyut tutarliligi tarafinda toplandi."
            )
        else:
            overview = "UI/UX taramasi belirgin bir hizalama veya spacing kirilmasi bulmadi. Yerlesim temel seviyede dengeli gorunuyor."

        recommendations = list(dict.fromkeys([finding["recommendation"] for finding in findings]))
        if not recommendations:
            recommendations = [
                "Yerlesim iyi gorunse de farkli ekran genisliklerinde spacing ve grid hizasini tekrar kontrol et.",
            ]

        return {
            "platform": platform,
            "image": {
                "width": image_width,
                "height": image_height,
            },
            "overall_score": int(overall_score),
            "overview": overview,
            "alignment_score": int(alignment_score),
            "spacing_consistency_score": int(spacing_score),
            "layout_balance_score": int(consistency_score),
            "findings": findings,
            "artifacts": {
                "annotated_image_base64": _render_overlay(image, issues),
                "source_image_base64": _image_to_base64(image),
            },
            "recommendations": recommendations,
        }
