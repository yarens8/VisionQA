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


def _find_hierarchy_issue(candidates: List[ComponentCandidate], image_width: int, image_height: int) -> Optional[UiuxIssue]:
    if len(candidates) < 2:
        return None

    sorted_candidates = sorted(candidates, key=lambda item: item.width * item.height, reverse=True)
    primary = sorted_candidates[0]
    secondary = sorted_candidates[1]
    primary_area = primary.width * primary.height
    secondary_area = max(1, secondary.width * secondary.height)
    dominance_ratio = primary_area / secondary_area

    top_band = image_height * 0.55
    primary_is_low = (primary.y + primary.height / 2) > top_band

    if dominance_ratio < 1.22 or primary_is_low:
        role_name = _role_name(primary, image_width, image_height)
        return UiuxIssue(
            title="Gorsel hiyerarsi yeterince net degil",
            severity="medium",
            category="hierarchy",
            description=(
                f"Ekrandaki ana odak bolgesi olarak algilanan {role_name} diger buyuk bloklardan yeterince ayrismiyor "
                "ve ilk bakista dikkat hiyerarsisi zayif kaliyor."
            ),
            recommendation="Baslik, ana form veya ana mesaj blogunu daha baskin hale getir; ikincil bloklarin gorsel agirligini azalt.",
            candidate=primary,
        )

    return None


def _find_cta_issue(candidates: List[ComponentCandidate], image_width: int, image_height: int) -> Optional[UiuxIssue]:
    action_like = [candidate for candidate in candidates if candidate.label in {"action-button", "input-row", "form-panel"}]
    if not action_like:
        return None

    best_candidate = max(action_like, key=lambda item: item.width * item.height)
    area_ratio = (best_candidate.width * best_candidate.height) / max(image_width * image_height, 1)
    too_low = (best_candidate.y + best_candidate.height / 2) > image_height * 0.72
    too_small = area_ratio < 0.018 and best_candidate.label == "action-button"

    if too_low or too_small:
        role_name = _role_name(best_candidate, image_width, image_height)
        severity = "medium" if too_low else "low"
        return UiuxIssue(
            title="Birincil aksiyon yeterince baskin degil",
            severity=severity,
            category="cta-dominance",
            description=(
                f"Birincil aksiyon olarak yorumlanan {role_name} kullanicinin ilk bakis akisi icinde geri planda kaliyor. "
                "Bu durum gorev tamamlama hizini ve netligini dusurebilir."
            ),
            recommendation="Primary CTA'yi daha erken gorunen bir banda tasi veya buton boyutu/kontrasti ile daha baskin hale getir.",
            candidate=best_candidate,
        )

    return None


def _find_intent_issue(candidates: List[ComponentCandidate], image_width: int, image_height: int) -> Optional[UiuxIssue]:
    form_like = [candidate for candidate in candidates if candidate.label in {"form-panel", "input-row", "action-button"}]
    if len(form_like) < 2:
        return None

    left_candidates = [candidate for candidate in form_like if (candidate.x + candidate.width / 2) < image_width * 0.42]
    right_candidates = [candidate for candidate in form_like if (candidate.x + candidate.width / 2) > image_width * 0.58]
    centered_candidates = [
        candidate for candidate in form_like
        if image_width * 0.42 <= (candidate.x + candidate.width / 2) <= image_width * 0.58
    ]

    intent = "auth-flow" if len(form_like) >= 3 else "task-flow"
    off_balance_candidate: Optional[ComponentCandidate] = None
    if intent == "auth-flow":
        if right_candidates and not centered_candidates:
            off_balance_candidate = max(right_candidates, key=lambda item: item.width * item.height)
        elif left_candidates and not centered_candidates:
            off_balance_candidate = max(left_candidates, key=lambda item: item.width * item.height)

    if off_balance_candidate is None:
        return None

    role_name = _role_name(off_balance_candidate, image_width, image_height)
    return UiuxIssue(
        title="Ekran niyeti ile yerlesim dili tam ortusmuyor",
        severity="low",
        category="intent-mismatch",
        description=(
            f"Ekran bir {intent} gibi gorunuyor; ancak ana {role_name} merkezi akisin disina kaymis. "
            "Bu, ozellikle login veya hizli is tamamlama ekranlarinda gereksiz biliissel yuk olusturabilir."
        ),
        recommendation="Form-merkezli ekranlarda ana aksiyonu ve giris alanlarini daha merkezi veya daha net tek kolon akisinda topla.",
        candidate=off_balance_candidate,
    )


def _find_clutter_issue(candidates: List[ComponentCandidate], image_width: int, image_height: int) -> Optional[UiuxIssue]:
    if not candidates:
        return None

    top_half_count = sum(1 for candidate in candidates if (candidate.y + candidate.height / 2) < image_height * 0.58)
    unique_bands = {
        int(((candidate.y + candidate.height / 2) / max(image_height, 1)) * 6)
        for candidate in candidates
    }
    if top_half_count >= 6 or len(unique_bands) >= 5:
        candidate = max(candidates, key=lambda item: item.width * item.height)
        return UiuxIssue(
            title="Gorsel yogunluk fazla artiyor",
            severity="medium",
            category="visual-clutter",
            description=(
                "Ekranda ayni anda cok fazla ayri odak bolgesi olusuyor. Bu yogunluk kullanicinin nereye bakacagini "
                "hizlica belirlemesini zorlastirabilir."
            ),
            recommendation="Ikincil ogeleri sadeleştir, birincil akis disindaki bloklari birlestir veya daha alt oncelikli hale getir.",
            candidate=candidate,
        )
    return None


def _find_whitespace_issue(candidates: List[ComponentCandidate], image_width: int, image_height: int) -> Optional[UiuxIssue]:
    if len(candidates) < 2:
        return None

    total_area = sum(candidate.width * candidate.height for candidate in candidates)
    fill_ratio = total_area / max(image_width * image_height, 1)
    left_fill = sum(
        candidate.width * candidate.height
        for candidate in candidates
        if (candidate.x + candidate.width / 2) < image_width * 0.5
    )
    right_fill = max(1, total_area - left_fill)
    side_ratio = max(left_fill, right_fill) / max(1, min(left_fill or 1, right_fill))

    if fill_ratio > 0.34 or side_ratio > 1.9:
        candidate = max(candidates, key=lambda item: item.width * item.height)
        return UiuxIssue(
            title="Bosluk dagilimi dengeli degil",
            severity="medium" if fill_ratio > 0.34 else "low",
            category="whitespace-balance",
            description=(
                "Icerik bloklari ile negatif alan arasindaki denge saglikli dagilmiyor. "
                "Bazi bolgeler sikisik, bazi bolgeler ise gereksiz bos kaliyor."
            ),
            recommendation="Icerik yogunlugunu kolonlar arasinda dengele ve bloklarin etrafinda daha istikrarli nefes alanlari birak.",
            candidate=candidate,
        )
    return None


def _find_section_separation_issue(candidates: List[ComponentCandidate], image_width: int, image_height: int) -> Optional[UiuxIssue]:
    if len(candidates) < 3:
        return None

    ordered = sorted(candidates, key=lambda item: item.y)
    gaps = []
    for current, next_candidate in zip(ordered, ordered[1:]):
        gap = next_candidate.y - (current.y + current.height)
        if gap >= 0:
            gaps.append((current, next_candidate, gap))

    if not gaps:
        return None

    smallest_gap_pair = min(gaps, key=lambda item: item[2])
    largest_gap_pair = max(gaps, key=lambda item: item[2])
    min_gap = smallest_gap_pair[2]
    max_gap = largest_gap_pair[2]

    if min_gap < max(10, int(image_height * 0.018)) or max_gap > max(64, int(image_height * 0.2)):
        current, next_candidate, gap = smallest_gap_pair if min_gap < max(10, int(image_height * 0.018)) else largest_gap_pair
        severity = "medium" if gap < max(10, int(image_height * 0.018)) else "low"
        return UiuxIssue(
            title="Bolum gecisleri yeterince net degil",
            severity=severity,
            category="section-separation",
            description=(
                f"Ardisik iki ana bolum arasindaki gecis araligi yaklasik {int(round(gap))} px. "
                "Bu deger section ayrimini ya fazla zayif ya da fazla kopuk hissettirebilir."
            ),
            recommendation="Section'lar arasinda daha istikrarli ara bosluk kullan ve gerekirse ayirici bir katman veya baslik ritmi ekle.",
            candidate=next_candidate,
        )
    return None


def _find_readability_flow_issue(candidates: List[ComponentCandidate], image_width: int, image_height: int) -> Optional[UiuxIssue]:
    if len(candidates) < 3:
        return None

    ordered = sorted(candidates, key=lambda item: item.y + item.height / 2)
    jumps = []
    previous_center = None
    for candidate in ordered:
        center = candidate.y + candidate.height / 2
        if previous_center is not None:
            jumps.append(center - previous_center)
        previous_center = center

    if not jumps:
        return None

    inconsistent_jump = max(jumps) / max(1.0, min(jumps))
    if inconsistent_jump >= 2.8:
        candidate = ordered[min(len(ordered) - 1, 1)]
        return UiuxIssue(
            title="Okuma akisi rahat ilerlemiyor",
            severity="low",
            category="readability-flow",
            description=(
                "Baslik, aciklama, form ve aksiyon bloklari arasindaki dikey ilerleme ritmi tutarli degil. "
                "Bu durum kullanicinin ekrani tarama hizini yavaslatabilir."
            ),
            recommendation="Ana okuma akisindaki bloklari daha lineer bir yukaridan asagi siraya ve daha tutarli araliklara oturt.",
            candidate=candidate,
        )
    return None


def _classify_screen_intent(candidates: List[ComponentCandidate], image_width: int, image_height: int) -> str:
    form_like = sum(1 for candidate in candidates if candidate.label in {"form-panel", "input-row", "action-button"})
    top_heavy = sum(1 for candidate in candidates if (candidate.y + candidate.height / 2) < image_height * 0.45)
    small_actions = sum(1 for candidate in candidates if candidate.label in {"action-button", "small-text"})

    if form_like >= 3:
        return "auth-flow"
    if top_heavy >= max(2, len(candidates) // 2) and small_actions >= 2:
        return "landing"
    if len(candidates) >= 6:
        return "dashboard"
    return "generic"


def _find_attention_flow_issue(candidates: List[ComponentCandidate], image_width: int, image_height: int) -> Optional[UiuxIssue]:
    if len(candidates) < 3:
        return None

    ranked = sorted(candidates, key=lambda item: item.width * item.height, reverse=True)[:3]
    centers = [(candidate.x + candidate.width / 2, candidate.y + candidate.height / 2) for candidate in ranked]
    horizontal_span = max(point[0] for point in centers) - min(point[0] for point in centers)
    vertical_span = max(point[1] for point in centers) - min(point[1] for point in centers)

    if horizontal_span > image_width * 0.42 and vertical_span > image_height * 0.24:
        candidate = ranked[0]
        return UiuxIssue(
            title="Dikkat akisi birden fazla yone dagiliyor",
            severity="medium",
            category="attention-flow",
            description=(
                "Ilk bakista one cikan ana bloklar tek bir akista ilerlemiyor. Goz, soldan saga ve yukaridan asagi "
                "tek rota yerine birden fazla odak arasinda ziplayabilir."
            ),
            recommendation="Ana mesaji, formu ve birincil aksiyonu daha tek eksenli bir odak akisi uzerinde grupla.",
            candidate=candidate,
        )

    return None


def _find_conversion_friction_issue(candidates: List[ComponentCandidate], image_width: int, image_height: int) -> Optional[UiuxIssue]:
    action_buttons = [candidate for candidate in candidates if candidate.label == "action-button"]
    form_candidates = [candidate for candidate in candidates if candidate.label in {"form-panel", "input-row"}]
    if not action_buttons or not form_candidates:
        return None

    primary_cta = max(action_buttons, key=lambda item: item.width * item.height)
    closest_form = min(
        form_candidates,
        key=lambda item: abs((item.y + item.height / 2) - (primary_cta.y + primary_cta.height / 2)),
    )
    vertical_gap = abs(primary_cta.y - (closest_form.y + closest_form.height))
    cta_below_fold = (primary_cta.y + primary_cta.height / 2) > image_height * 0.68

    if vertical_gap > image_height * 0.12 or cta_below_fold:
        severity = "medium" if cta_below_fold else "low"
        return UiuxIssue(
            title="Birincil aksiyona giden yol surtunmeli",
            severity=severity,
            category="conversion-friction",
            description=(
                "Form ile birincil aksiyon arasindaki gecis cok acik degil. Kullanici, gorevi tamamlamak icin "
                "sonraki adimi ekstra tarama ile bulmak zorunda kalabilir."
            ),
            recommendation="Primary CTA'yi ilgili form veya ana mesaj bloguna daha yakin konumlandir ve sonraki adimi daha netlestir.",
            candidate=primary_cta,
        )

    return None


def _find_trust_signal_issue(candidates: List[ComponentCandidate], image_width: int, image_height: int) -> Optional[UiuxIssue]:
    intent = _classify_screen_intent(candidates, image_width, image_height)
    if intent not in {"auth-flow", "landing"}:
        return None

    form_like = [candidate for candidate in candidates if candidate.label in {"form-panel", "input-row"}]
    support_like = [candidate for candidate in candidates if candidate.label in {"small-text", "text-line", "action-button"}]
    if not form_like:
        return None

    main_form = max(form_like, key=lambda item: item.width * item.height)
    nearby_support = 0
    for candidate in support_like:
        if candidate is main_form:
            continue
        vertical_distance = abs((candidate.y + candidate.height / 2) - (main_form.y + main_form.height / 2))
        if vertical_distance <= image_height * 0.18:
            nearby_support += 1

    if nearby_support <= 1:
        return UiuxIssue(
            title="Guven sinyalleri zayif kaliyor",
            severity="low",
            category="trust-signal",
            description=(
                "Ozellikle form-merkezli bu ekranda guven veren yardimci sinyaller sinirli gorunuyor. "
                "Kullanici gizlilik, destek veya dogrulama hissini yeterince alamayabilir."
            ),
            recommendation="Form cevresine yardimci aciklama, guven verici mikro metin veya destekleyici durum bilgileri ekle.",
            candidate=main_form,
        )

    return None


def _find_persona_issue(candidates: List[ComponentCandidate], image_width: int, image_height: int) -> Optional[UiuxIssue]:
    if len(candidates) < 3:
        return None

    intent = _classify_screen_intent(candidates, image_width, image_height)
    top_density = sum(
        candidate.width * candidate.height
        for candidate in candidates
        if (candidate.y + candidate.height / 2) < image_height * 0.45
    ) / max(image_width * image_height, 1)

    if top_density > 0.18:
        candidate = max(candidates, key=lambda item: item.width * item.height)
        persona = "yeni kullanici" if intent in {"landing", "auth-flow"} else "hizli gorev kullanicisi"
        return UiuxIssue(
            title="Bazi kullanici profilleri icin ilk tarama zorlasiyor",
            severity="low",
            category="persona-risk",
            description=(
                f"Bu yerlesim, ozellikle {persona} icin ilk bakista fazla biliissel yuk olusturabilir. "
                "Ana gorev ile ikincil secenekler yeterince hizli ayrisamayabilir."
            ),
            recommendation="Birincil gorevi daha erken ayristir ve ikincil secenekleri ilk tarama aninda daha geri planda tut.",
            candidate=candidate,
        )

    return None


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


def _render_attention_overlay(image: Image.Image, candidates: List[ComponentCandidate]) -> str:
    overlay = image.convert("RGBA")
    draw = ImageDraw.Draw(overlay, "RGBA")

    ranked = sorted(candidates, key=lambda item: item.width * item.height, reverse=True)[:4]
    centers = []
    for index, candidate in enumerate(ranked, start=1):
        center_x = int(candidate.x + candidate.width / 2)
        center_y = int(candidate.y + candidate.height / 2)
        centers.append((center_x, center_y))

        glow_radius = max(26, min(84, int(max(candidate.width, candidate.height) * 0.38)))
        draw.ellipse(
            (
                center_x - glow_radius,
                center_y - glow_radius,
                center_x + glow_radius,
                center_y + glow_radius,
            ),
            fill=(34, 211, 238, 88 if index == 1 else 56),
            outline=(34, 211, 238, 240),
            width=4,
        )
        draw.ellipse(
            (
                center_x - 13,
                center_y - 13,
                center_x + 13,
                center_y + 13,
            ),
            fill=(251, 191, 36, 255 if index == 1 else 230),
            outline=(15, 23, 42, 255),
            width=3,
        )
        label_left = center_x + 18
        label_top = center_y - 20
        draw.rounded_rectangle(
            (label_left, label_top, label_left + 26, label_top + 24),
            radius=8,
            fill=(15, 23, 42, 230),
            outline=(255, 255, 255, 170),
            width=1,
        )
        draw.text((label_left + 9, label_top + 4), str(index), fill=(255, 255, 255, 255))

    for current, next_point in zip(centers, centers[1:]):
        draw.line((current[0], current[1], next_point[0], next_point[1]), fill=(248, 113, 113, 235), width=7)
        arrow_size = 12
        draw.ellipse(
            (
                next_point[0] - arrow_size,
                next_point[1] - arrow_size,
                next_point[0] + arrow_size,
                next_point[1] + arrow_size,
            ),
            fill=(248, 113, 113, 235),
            outline=(255, 255, 255, 180),
            width=2,
        )

    return _image_to_base64(overlay)


def _ai_critic_for(issue: UiuxIssue) -> str:
    mapping = {
        "hierarchy": "Ana mesaj ile ikincil bloklar arasinda yeterli baskinlik farki yok; ekran ilk bakista neyin oncelikli oldugunu guclu sekilde anlatamiyor.",
        "cta-dominance": "CTA butonu veya birincil aksiyon, cevresindeki bloklardan yeterince ayrismadigi icin kullanici sonraki adimi gec algilayabilir.",
        "alignment": "Grid ve kolon ritmindeki sapma arayuzu daha az kontrollu hissettirir; bu da kalite algisini ve tarama hizini olumsuz etkiler.",
        "spacing": "Bosluk token'lari kararsiz davraniyor; ekran parcalar arasindaki ritim bozuldugunda kullanici akis yerine daginik parcaciklar gorur.",
        "consistency": "Benzer gorunmesi gereken ogeler farkli boyut veya agirlikta calisiyor; bu da tasarim dilinin tek bir sistem gibi hissettirmesini zorlastiriyor.",
        "whitespace-balance": "Negatif alan dagilimi dengeli olmadiginda ekran bir yerde sikisik, baska yerde gereksiz bos hissedilir; bu da profesyonellik algisini dusurebilir.",
        "section-separation": "Bolumler arasi gecis ritmi zayif oldugunda kullanici ekrani bir hikaye gibi degil, kopuk parcalar gibi okumaya baslar.",
        "readability-flow": "Basliktan aksiyona giden dikey akis yeterince akici degil; goz dogal okuma rotasinda takilabilir.",
        "visual-clutter": "Ayni anda fazla odak noktasi olusuyor; kullanici ekrandaki asıl gorevi secmek icin gereksiz enerji harcar.",
        "conversion-friction": "Ana goreve gitmek icin fazladan tarama gerekiyor; bu da tamamlama hizini ve donusum potansiyelini zayiflatabilir.",
        "trust-signal": "Ozellikle form odakli ekranlarda yardimci guven sinyalleri zayif oldugunda kullanici karar vermekte daha isteksiz olabilir.",
        "attention-flow": "Odak noktasi tek bir rota olusturmuyor; goz birden fazla yone sicrayarak ekranin mesajini gec kavrayabilir.",
        "persona-risk": "Bu yerlesim deneyimli kullanicilar icin yonlendirilebilir olsa da yeni kullanicilar icin ilk taramada daha fazla bilissel yuk olusturabilir.",
        "intent-mismatch": "Ekranin amaci ile yerlesim dili tam ortusmuyor; kullanici burada hangi gorevin hizla tamamlanmasi gerektigini gec anlayabilir.",
    }
    return mapping.get(issue.category, issue.description)


def _why_this_matters_for(issue: UiuxIssue) -> str:
    mapping = {
        "hierarchy": "Kullanici ana aksiyonu veya ana mesaji gec fark edebilir; bu da etkileşim ve donusum oranini dusurebilir.",
        "cta-dominance": "Birincil aksiyon gec fark edilirse gorev tamamlama suresi uzar ve terk etme ihtimali artar.",
        "alignment": "Hizalama bozuldugunda urun daha az guvenilir ve daha az rafine gorunebilir.",
        "spacing": "Tutarsiz spacing, okunabilirligi ve akisi dusurerek kullanicinin ekrani taramasini zorlastirir.",
        "consistency": "Tutarsiz bilesen dili kullanicinin hangi ogelerin benzer davrandigini anlamasini zorlastirir.",
        "whitespace-balance": "Nefes alamayan veya asiri bos ekranlar karar verme rahatligini azaltir.",
        "section-separation": "Bolumler net ayrismazsa kullanici ekrani yanlis yorumlayabilir veya sonraki adimi gec anlayabilir.",
        "readability-flow": "Okuma akisi yavasladiginda bilgi alma ve aksiyona gecis sureci de yavaslar.",
        "visual-clutter": "Yuksek gorsel yuk, ozellikle yeni kullanicilar icin yorucu bir ilk izlenim yaratir.",
        "conversion-friction": "Surtunme arttikca form tamamlama ve CTA tiklama olasiligi azalabilir.",
        "trust-signal": "Guven hissi dusuk ekranlar giris, odeme veya kayit gibi kritik anlarda terk edilme riski tasir.",
        "attention-flow": "Odak dağılırsa kullanici ana hikayeyi veya ana aksiyonu kacirabilir.",
        "persona-risk": "Farkli kullanici profilleri ayni ekranda ayni rahatlikta ilerleyemez; bu da genel UX kalitesini asagi ceker.",
        "intent-mismatch": "Niyet ve yerlesim uyusmazsa ekranin amaci belirsizlesir ve kullanici emin olmadan ilerler.",
    }
    return mapping.get(issue.category, "Bu bulgu, ekranin anlasilirligini ve gorev tamamlama rahatligini olumsuz etkileyebilir.")


def _focus_score(candidates: List[ComponentCandidate], image_width: int, image_height: int) -> int:
    if not candidates:
        return 92
    ranked = sorted(candidates, key=lambda item: item.width * item.height, reverse=True)[:3]
    primary = ranked[0]
    secondary_area = ranked[1].width * ranked[1].height if len(ranked) > 1 else 1
    dominance_ratio = (primary.width * primary.height) / max(1, secondary_area)
    center_x = primary.x + primary.width / 2
    center_y = primary.y + primary.height / 2
    center_distance = abs(center_x - image_width / 2) / max(image_width / 2, 1) + abs(center_y - image_height * 0.38) / max(image_height, 1)
    score = 72 + min(18, int(dominance_ratio * 8)) - min(18, int(center_distance * 28))
    return max(38, min(96, score))


def _primary_focus_label(candidates: List[ComponentCandidate], image_width: int, image_height: int) -> str:
    if not candidates:
        return "net odak yok"
    candidate = max(candidates, key=lambda item: item.width * item.height)
    return _role_name(candidate, image_width, image_height)


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
            _find_hierarchy_issue,
            _find_cta_issue,
            _find_intent_issue,
            _find_clutter_issue,
            _find_whitespace_issue,
            _find_section_separation_issue,
            _find_readability_flow_issue,
            _find_attention_flow_issue,
            _find_conversion_friction_issue,
            _find_trust_signal_issue,
            _find_persona_issue,
        ):
            issue = resolver(candidates, image_width, image_height)
            if issue:
                issues.append(issue)

        if len(issues) < 3:
            existing_categories = {issue.category for issue in issues}
            for fallback_issue in _fallback_structure_issues(image, image_width, image_height):
                if fallback_issue.category in existing_categories:
                    continue
                issues.append(fallback_issue)
                existing_categories.add(fallback_issue.category)
                if len(issues) >= 4:
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
                    "ai_critic": _ai_critic_for(issue),
                    "why_this_matters": _why_this_matters_for(issue),
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
        consistency_score = max(52, 100 - sum(_penalty(issue.severity) for issue in issues if issue.category in {"consistency", "section-separation"}))
        hierarchy_score = max(48, 100 - sum(_penalty(issue.severity) for issue in issues if issue.category in {"hierarchy", "cta-dominance", "intent-mismatch", "attention-flow"}))
        readability_score = max(50, 100 - sum(_penalty(issue.severity) for issue in issues if issue.category in {"readability-flow", "section-separation", "whitespace-balance"}))
        friction_score = max(46, 100 - sum(_penalty(issue.severity) for issue in issues if issue.category in {"conversion-friction", "visual-clutter", "persona-risk", "trust-signal"}))
        focus_score = _focus_score(candidates, image_width, image_height)
        overall_score = round((alignment_score + spacing_score + consistency_score + hierarchy_score + readability_score + friction_score + focus_score) / 7)

        if findings:
            overview = (
                f"AI UX Critic bu ekranda {len(findings)} anlamli sinyal buldu. "
                f"En belirgin riskler gorsel hiyerarsi, okuma akisi ve kullaniciyi yoran surtunme noktalarinda toplandi."
            )
        else:
            overview = "AI UX Critic belirgin bir UX kirilmasi bulmadi. Ekran temel hiyerarsi, spacing ve odak dagilimi acisindan dengeli gorunuyor."

        ai_critic_summary = (
            "Ekran; odak netligi, bosluk ritmi, gorsel hiyerarsi ve kullanici surtunmesi acisindan birlikte okunarak yorumlandi. "
            "Bulgu metinleri yalnizca neyin bozuk oldugunu degil, bunun kullanici davranisina nasil yansiyabilecegini de aciklar."
        )

        recommendations = list(dict.fromkeys([finding["recommendation"] for finding in findings]))
        if not recommendations:
            recommendations = [
                "Yerlesim iyi gorunse de farkli ekran genisliklerinde spacing ve grid hizasini tekrar kontrol et.",
            ]

        ranked_candidates = sorted(candidates, key=lambda item: item.width * item.height, reverse=True)[:4]
        attention_path = [_role_name(candidate, image_width, image_height) for candidate in ranked_candidates]

        return {
            "platform": platform,
            "image": {
                "width": image_width,
                "height": image_height,
            },
            "overall_score": int(overall_score),
            "ux_score": int(overall_score),
            "overview": overview,
            "alignment_score": int(alignment_score),
            "spacing_consistency_score": int(spacing_score),
            "layout_balance_score": int(consistency_score),
            "visual_hierarchy_score": int(hierarchy_score),
            "readability_score": int(readability_score),
            "consistency_score": int(consistency_score),
            "friction_score": int(friction_score),
            "focus_score": int(focus_score),
            "ai_critic_summary": ai_critic_summary,
            "score_summary": {
                "ux_score": int(overall_score),
                "visual_hierarchy_score": int(hierarchy_score),
                "spacing_score": int(spacing_score),
                "consistency_score": int(consistency_score),
                "readability_score": int(readability_score),
                "friction_score": int(friction_score),
                "focus_score": int(focus_score),
            },
            "attention_prediction": {
                "focus_score": int(focus_score),
                "primary_focus_label": _primary_focus_label(candidates, image_width, image_height),
                "attention_path": attention_path,
                "summary": "Odak akisi en buyuk gorsel bloklarin muhtemel ilk bakis sirasi uzerinden tahmin edildi.",
            },
            "findings": findings,
            "artifacts": {
                "annotated_image_base64": _render_overlay(image, issues),
                "attention_overlay_image_base64": _render_attention_overlay(image, candidates),
                "source_image_base64": _image_to_base64(image),
            },
            "recommendations": recommendations,
        }
