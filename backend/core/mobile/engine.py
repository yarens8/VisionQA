from __future__ import annotations

import base64
import io
from typing import Any, Dict, List, Optional

from PIL import Image


class MobileAnalysisEngine:
    def analyze(
        self,
        *,
        platform: str,
        screen_name: Optional[str],
        image_base64: Optional[str],
        element_metadata: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        image_meta = self._image_meta(image_base64)
        width = image_meta.get("width", 0)
        height = image_meta.get("height", 0)
        if not width or not height:
            inferred = self._infer_canvas_from_metadata(element_metadata)
            width = width or inferred["width"]
            height = height or inferred["height"]
        findings: List[Dict[str, Any]] = []

        screen_type = self._infer_screen_type(screen_name, element_metadata)
        detected_patterns = self._detected_patterns(element_metadata)
        self._touch_target_findings(findings, element_metadata)
        self._readability_findings(findings, element_metadata, width)
        self._layout_findings(findings, element_metadata, width, height)
        self._context_findings(findings, screen_type, element_metadata)
        self._thumb_zone_findings(findings, screen_type, element_metadata, width, height)
        self._safe_area_findings(findings, element_metadata, width, height)
        self._keyboard_overlap_findings(findings, screen_type, element_metadata, height)
        self._gesture_friction_findings(findings, screen_type, element_metadata, height)

        touch_score = self._score_touch(element_metadata, findings)
        readability_score = self._score_readability(element_metadata, findings)
        layout_score = self._score_layout(element_metadata, findings)
        interaction_score = self._score_interaction(screen_type, findings)
        mobile_ux = round((touch_score + readability_score + layout_score + interaction_score) / 4)
        overall = mobile_ux

        recommendations = self._recommendations(findings, screen_type)
        return {
            "platform": platform,
            "overall_score": overall,
            "overview": f"Mobil analiz {len(findings)} bulgu uretti. Screen type '{screen_type}' olarak yorumlandi ve mobile UX odakli sinyaller cikarildi.",
            "ai_interpretation": self._ai_interpretation(findings, screen_type),
            "ai_mobile_critic": self._ai_mobile_critic(findings, screen_type),
            "root_cause_summary": self._root_cause(findings, screen_type),
            "task_completion_friction": self._task_completion_friction(findings, screen_type),
            "thumb_zone_summary": self._thumb_zone_summary(findings, screen_type),
            "keyboard_overlap_signal": self._keyboard_overlap_signal(findings, screen_type),
            "safe_area_signal": self._safe_area_signal(findings),
            "gesture_friction_summary": self._gesture_friction_summary(findings, screen_type),
            "context_playbook": self._context_playbook(screen_type),
            "cross_platform_parity_summary": self._cross_platform_parity_summary(screen_type, findings),
            "score_breakdown": {
                "mobile_ux": mobile_ux,
                "touch_target": touch_score,
                "readability": readability_score,
                "layout": layout_score,
                "interaction_readiness": interaction_score,
            },
            "context_profile": {
                "screen_type": screen_type,
                "detected_patterns": detected_patterns,
                "cross_platform_consistency_signal": self._cross_platform_signal(screen_type, findings),
            },
            "findings": findings,
            "supported_now": [
                {"title": "Screenshot analysis", "status": "active", "description": "Mobil ekran goruntusu uzerinden UI/UX ve readability sinyalleri yorumlanir."},
                {"title": "Metadata-aware analysis", "status": "active", "description": "Appium veya benzeri executor'lardan gelen element metadata'si ile touch target ve context tespiti yapilir."},
                {"title": "Action readiness", "status": "active", "description": "Tap/swipe gibi mevcut mobile executor aksiyonlari capability katmaninda konumlandirilir."},
                {"title": "Context-aware mobile UX", "status": "active", "description": "Login, form, feed veya detail benzeri ekran tiplerine gore yorum uretilir."},
                {"title": "Thumb-zone and keyboard heuristics", "status": "active", "description": "Tek elle erisim, klavye cakismasi ve alt bolge CTA riski icin mobil-ozel sinyaller uretilir."},
                {"title": "Cross-platform parity hints", "status": "active", "description": "Web ve mobil hiyerarsi/yerlesim farklari icin ilk parity yorumlari sunulur."},
            ],
            "next_phase": [
                {"title": "Live emulator/device farm", "status": "next", "description": "Gercek emulator ve cihaz matrisi ile canli kosum, replay ve oturum yonetimi."},
                {"title": "Battery/FPS telemetry", "status": "next", "description": "Gercek kaynak tuketimi, frame drop ve startup telemetry katmani."},
                {"title": "Network shaping", "status": "next", "description": "3G/4G/zayif baglanti ve offline senaryolarinin aktif simulasyonu."},
                {"title": "Gesture replay intelligence", "status": "next", "description": "Gercek swipe/scroll/tap akisini kaydedip friction ve replay tabanli analiz katmani."},
            ],
            "recommendations": recommendations,
        }

    def _image_meta(self, image_base64: Optional[str]) -> Dict[str, int]:
        if not image_base64:
            return {"width": 0, "height": 0}
        try:
            data = base64.b64decode(image_base64)
            image = Image.open(io.BytesIO(data))
            return {"width": int(image.width), "height": int(image.height)}
        except Exception:
            return {"width": 0, "height": 0}

    def _infer_canvas_from_metadata(self, metadata: List[Dict[str, Any]]) -> Dict[str, int]:
        if not metadata:
            return {"width": 0, "height": 0}
        max_x = 0
        max_y = 0
        for item in metadata:
            max_x = max(max_x, int(item.get("x") or 0) + int(item.get("width") or 0))
            max_y = max(max_y, int(item.get("y") or 0) + int(item.get("height") or 0))
        return {
            "width": max(320, max_x + 24),
            "height": max(640, max_y + 160),
        }

    def _infer_screen_type(self, screen_name: Optional[str], metadata: List[Dict[str, Any]]) -> str:
        hints = " ".join(
            [
                (screen_name or "").lower(),
                " ".join(str(item.get("text_content") or "").lower() for item in metadata),
                " ".join(str(item.get("aria_label") or "").lower() for item in metadata),
            ]
        )
        if any(token in hints for token in ("login", "giris", "signin", "password", "otp")):
            return "auth"
        if any(token in hints for token in ("search", "ara", "filter")):
            return "search"
        if any(token in hints for token in ("checkout", "payment", "odeme", "cart")):
            return "checkout"
        if sum(1 for item in metadata if item.get("element_type") == "input") >= 3:
            return "form"
        if sum(1 for item in metadata if item.get("element_type") in {"image", "button"}) >= 6:
            return "feed"
        return "detail"

    def _detected_patterns(self, metadata: List[Dict[str, Any]]) -> List[str]:
        patterns: List[str] = []
        input_count = sum(1 for item in metadata if item.get("element_type") == "input")
        button_count = sum(1 for item in metadata if item.get("element_type") == "button")
        if input_count >= 3:
            patterns.append("form-heavy")
        if button_count >= 4:
            patterns.append("action-dense")
        if sum(1 for item in metadata if item.get("focus_visible")) >= 1:
            patterns.append("focus-aware")
        if not patterns:
            patterns.append("visual-only")
        return patterns

    def _add_finding(self, findings: List[Dict[str, Any]], severity: str, category: str, title: str, description: str, evidence: str, recommendation: str) -> None:
        findings.append(
            {
                "id": len(findings) + 1,
                "title": title,
                "severity": severity,
                "category": category,
                "description": description,
                "evidence": evidence,
                "recommendation": recommendation,
            }
        )

    def _touch_target_findings(self, findings: List[Dict[str, Any]], metadata: List[Dict[str, Any]]) -> None:
        for item in metadata:
            if item.get("element_type") not in {"button", "link", "checkbox", "radio"}:
                continue
            width = int(item.get("width") or 0)
            height = int(item.get("height") or 0)
            if 0 < width < 44 or 0 < height < 44:
                self._add_finding(
                    findings,
                    "high",
                    "touch-target",
                    "Dokunma alani kucuk",
                    "Mobil ekranda bu interaktif alan parmak hedefi icin yetersiz olabilir.",
                    f"{item.get('element_type')} size={width}x{height}",
                    "Tap hedeflerini en az 44x44 px civarina yaklastir ve bosluklarini ac.",
                )

    def _readability_findings(self, findings: List[Dict[str, Any]], metadata: List[Dict[str, Any]], image_width: int) -> None:
        long_text_blocks = 0
        for item in metadata:
            text = str(item.get("text_content") or "").strip()
            width = int(item.get("width") or 0)
            if len(text) >= 28 and width and image_width and width < image_width * 0.35:
                long_text_blocks += 1
        if long_text_blocks >= 2:
            self._add_finding(
                findings,
                "medium",
                "readability",
                "Mobil okumada sikisma riski var",
                "Dar alana uzun metinler yerlestirilmis; bu durum mobil taramada okunabilirligi dusurebilir.",
                f"Long narrow text blocks: {long_text_blocks}",
                "Metin satir genisligini rahatlat, yardimci metinleri parcala veya tipografiyi sadeleştir.",
            )

    def _layout_findings(self, findings: List[Dict[str, Any]], metadata: List[Dict[str, Any]], image_width: int, image_height: int) -> None:
        if not metadata or not image_width or not image_height:
            return
        overflow_like = 0
        upper_fold = 0
        for item in metadata:
            x = int(item.get("x") or 0)
            y = int(item.get("y") or 0)
            width = int(item.get("width") or 0)
            height = int(item.get("height") or 0)
            if x + width > image_width or y + height > image_height:
                overflow_like += 1
            if y < image_height * 0.45:
                upper_fold += 1
        if overflow_like:
            self._add_finding(
                findings,
                "high",
                "overflow",
                "Mobil yerlesimde tasma riski var",
                "Bazi elementler ekran sinirlarini asiyor veya asmaya cok yakin gorunuyor.",
                f"Overflow-like elements: {overflow_like}",
                "Constraint ve responsive breakpoint ayarlarini mobil oncelikli sekilde duzenle.",
            )
        if upper_fold >= max(6, len(metadata) * 0.7):
            self._add_finding(
                findings,
                "medium",
                "density",
                "Ust bolge mobil icin fazla yogun",
                "Ekranin ust kismina cok fazla icerik yigiliyor; bu durum ilk taramayi zorlastirabilir.",
                f"Upper fold element count: {upper_fold}",
                "Icerigi katmanlara ayir, kritik aksiyonu koru ve ikinci seviye bloklari asagi tasimayi dusun.",
            )

    def _context_findings(self, findings: List[Dict[str, Any]], screen_type: str, metadata: List[Dict[str, Any]]) -> None:
        if screen_type == "auth":
            input_count = sum(1 for item in metadata if item.get("element_type") == "input")
            button_count = sum(1 for item in metadata if item.get("element_type") == "button")
            if input_count >= 3 and button_count >= 3:
                self._add_finding(
                    findings,
                    "medium",
                    "auth-friction",
                    "Auth ekrani mobilde fazla yogun hissedilebilir",
                    "Login/onboarding akisinda fazla sayida alan ve aksiyon kullanicinin tamamlanma hizini dusurebilir.",
                    f"inputs={input_count}, buttons={button_count}",
                    "Primary aksiyonu one cikar, ikincil yardimlari ikinci seviyeye indir.",
                )
        if screen_type == "feed":
            self._add_finding(
                findings,
                "low",
                "feed-rhythm",
                "Feed ritmi mobilde izlenmeli",
                "Feed benzeri ekranlarda kart yogunlugu ve scroll ritmi kullanici algisini hizli etkiler.",
                "Feed-like pattern detected",
                "Kart araliklari, gorsel tekrar oranı ve ilk viewport yogunlugunu mobil odakta incele.",
            )

    def _thumb_zone_findings(
        self,
        findings: List[Dict[str, Any]],
        screen_type: str,
        metadata: List[Dict[str, Any]],
        image_width: int,
        image_height: int,
    ) -> None:
        if not image_height:
            return
        buttons = [item for item in metadata if item.get("element_type") == "button"]
        if not buttons:
            return
        primary = max(
            buttons,
            key=lambda item: (int(item.get("width") or 0) * int(item.get("height") or 0), len(str(item.get("text_content") or ""))),
        )
        center_y = int(primary.get("y") or 0) + int(primary.get("height") or 0) / 2
        if center_y < image_height * 0.55:
            self._add_finding(
                findings,
                "medium",
                "thumb-zone",
                "Birincil aksiyon tek elle erisim bolgesinden uzakta",
                "Ana CTA ust bolgede kaldigi icin tek elle kullanimda erisim ve tamamlama hizi zayiflayabilir.",
                f"Primary CTA center_y={round(center_y)} / height={image_height}",
                "Ana aksiyonu alt erisim bolgesine biraz daha yakinlastir veya destekleyici ikinci CTA'lari yukari tasima.",
            )

    def _safe_area_findings(
        self,
        findings: List[Dict[str, Any]],
        metadata: List[Dict[str, Any]],
        image_width: int,
        image_height: int,
    ) -> None:
        if not image_height:
            return
        risky = 0
        for item in metadata:
            if item.get("element_type") not in {"button", "input", "link"}:
                continue
            y = int(item.get("y") or 0)
            height = int(item.get("height") or 0)
            if y < image_height * 0.06 or (y + height) > image_height * 0.94:
                risky += 1
        if risky:
            self._add_finding(
                findings,
                "low",
                "safe-area",
                "Safe-area sinirlarina yakin interaktif alanlar var",
                "Notch, status bar veya alt sistem alanlarina yakin yerlesen bilesenler cihazlar arasi kirilganlik yaratabilir.",
                f"Safe-area riskli element sayisi: {risky}",
                "Ust ve alt kritik alanlarda sabit margin/padding kullan ve sistem inset'lerini hesaba kat.",
            )

    def _keyboard_overlap_findings(
        self,
        findings: List[Dict[str, Any]],
        screen_type: str,
        metadata: List[Dict[str, Any]],
        image_height: int,
    ) -> None:
        if screen_type not in {"auth", "form"} or not image_height:
            return
        inputs = [item for item in metadata if item.get("element_type") == "input"]
        buttons = [item for item in metadata if item.get("element_type") == "button"]
        if len(inputs) >= 2 and buttons:
            lower_buttons = [
                item for item in buttons
                if (int(item.get("y") or 0) + int(item.get("height") or 0) / 2) > image_height * 0.64
            ]
            if lower_buttons:
                self._add_finding(
                    findings,
                    "medium",
                    "keyboard-overlap",
                    "Klavye acildiginda ana aksiyon kapanabilir",
                    "Form ekraninda alt bolgeye yakin CTA'lar yazilim klavyesi acildiginda gorunurlugunu kaybedebilir.",
                    f"Keyboard-risk CTA count: {len(lower_buttons)}",
                    "Input odagi sirasinda sticky CTA, scroll-into-view veya alt bosluk stratejisi uygula.",
                )

    def _gesture_friction_findings(
        self,
        findings: List[Dict[str, Any]],
        screen_type: str,
        metadata: List[Dict[str, Any]],
        image_height: int,
    ) -> None:
        if not image_height:
            return
        buttons = [item for item in metadata if item.get("element_type") in {"button", "link"}]
        upper_actions = sum(1 for item in buttons if int(item.get("y") or 0) < image_height * 0.45)
        if screen_type in {"feed", "detail", "search"} and upper_actions >= 5:
            self._add_finding(
                findings,
                "medium",
                "gesture-friction",
                "Scroll ve swipe akisi aksiyon yogunlugu ile kiriliyor",
                "Ilk viewportta fazla aksiyon birikmesi dogal scroll ritmini ve gesture odakliligini bozabilir.",
                f"Upper interactive count: {upper_actions}",
                "Ilk viewportta aksiyon yogunlugunu sadeleştir ve ikincil kontrolleri overflow/menu altina tasimayi dusun.",
            )

    def _score_touch(self, metadata: List[Dict[str, Any]], findings: List[Dict[str, Any]]) -> int:
        score = 100
        score -= 18 * sum(1 for f in findings if f["category"] == "touch-target")
        return max(0, score)

    def _score_readability(self, metadata: List[Dict[str, Any]], findings: List[Dict[str, Any]]) -> int:
        score = 100
        score -= 14 * sum(1 for f in findings if f["category"] == "readability")
        return max(0, score)

    def _score_layout(self, metadata: List[Dict[str, Any]], findings: List[Dict[str, Any]]) -> int:
        score = 100
        score -= 18 * sum(1 for f in findings if f["category"] in {"overflow", "density", "safe-area"})
        return max(0, score)

    def _score_interaction(self, screen_type: str, findings: List[Dict[str, Any]]) -> int:
        score = 100
        if screen_type == "auth":
            score -= 10
        score -= 12 * sum(1 for f in findings if f["category"] in {"auth-friction", "thumb-zone", "keyboard-overlap", "gesture-friction"})
        return max(0, score)

    def _ai_interpretation(self, findings: List[Dict[str, Any]], screen_type: str) -> str:
        if not findings:
            return "Mobil ekran bu kosumda temel UX sinyallerinde saglikli gorunuyor; sonraki adim canli jest ve cihaz matrisi olabilir."
        if any(f["category"] == "touch-target" for f in findings):
            return "En guclu mobil risk dokunma alanlarinda. Kucuk hedefler ozellikle tek elle kullanimda gorev tamamlama hizini dusurur."
        if any(f["category"] == "overflow" for f in findings):
            return "Layout mobil constraint'lere tam oturmuyor gibi gorunuyor; bu durum cihazlar arasi responsive parity riskini arttirir."
        return f"{screen_type} tipindeki bu ekran mobilde okunabilirlik ve akis acisindan optimize edilmeye aday gorunuyor."

    def _ai_mobile_critic(self, findings: List[Dict[str, Any]], screen_type: str) -> str:
        categories = {finding["category"] for finding in findings}
        if not categories:
            return "Bu mobil ekran ilk bakista sakin ve gorev odakli gorunuyor; daha derin farki canli gesture ve cihaz matrisi gosterecektir."
        if "thumb-zone" in categories or "touch-target" in categories:
            return "Arayuzun ana problemi parmak erisimi ve tap ergonomisi. Kullanici dogru aksiyonu gorup yine de rahat secemeyebilir."
        if "keyboard-overlap" in categories:
            return "Form akisinda gorsel duzen fena degil ama yazilim klavyesi devreye girdiginde tamamlanma hizi dusme riski tasiyor."
        if "gesture-friction" in categories:
            return "Mobil ritim swipe/scroll akisi yerine aksiyon kalabaligina kayiyor; bu da ekranin akiciligini zedeliyor."
        return f"{screen_type} ekraninda temel islev var ama mobil ergonomi hala biraz desktop mirasi tasiyor."

    def _root_cause(self, findings: List[Dict[str, Any]], screen_type: str) -> str:
        categories = {finding["category"] for finding in findings}
        if "overflow" in categories:
            return "En baskin kok neden responsive constraint ve viewport-oncelikli yerlesim kararlarinin zayif olmasi."
        if "touch-target" in categories:
            return "En baskin kok neden desktop veya genel tasarim tokenlerinin mobile tap hedeflerine uygun olmamasi."
        if "keyboard-overlap" in categories:
            return "En baskin kok neden mobil form akisi tasarlanirken yazilim klavyesi ve viewport daralmasinin yeterince hesaba katilmamasi."
        if "auth-friction" in categories:
            return "En baskin kok neden mobil auth akisinda birincil/ikincil aksiyon ayriminin zayif kurulmasi."
        return "Belirgin tekil bir kok neden yerine mobil density, touch ve readability katmanlari birlikte gozden gecirilmeli."

    def _cross_platform_signal(self, screen_type: str, findings: List[Dict[str, Any]]) -> str:
        if any(f["category"] == "overflow" for f in findings):
            return "Web ile mobil arasinda responsive parity sapmasi olabilir."
        if screen_type == "auth":
            return "Auth ekrani web-mobil aksiyon hiyerarsisi acisindan karsilastirilmali."
        return "Temel mobil-web tutarlilik sinyali kabul edilebilir; detayli parity sonraki fazda derinlestirilebilir."

    def _task_completion_friction(self, findings: List[Dict[str, Any]], screen_type: str) -> int:
        friction = 20 if screen_type == "auth" else 12
        friction += 18 * sum(1 for finding in findings if finding["category"] in {"touch-target", "thumb-zone", "keyboard-overlap"})
        friction += 10 * sum(1 for finding in findings if finding["category"] in {"density", "gesture-friction", "auth-friction"})
        return min(100, friction)

    def _thumb_zone_summary(self, findings: List[Dict[str, Any]], screen_type: str) -> str:
        if any(finding["category"] == "thumb-zone" for finding in findings):
            return "Birincil aksiyon tek elle kullanimin rahat alt erisim bandindan uzak gorunuyor."
        return "Thumb-zone tarafinda belirgin bir CTA erisim riski cikmadi."

    def _keyboard_overlap_signal(self, findings: List[Dict[str, Any]], screen_type: str) -> str:
        if any(finding["category"] == "keyboard-overlap" for finding in findings):
            return "Form odaginda yazilim klavyesi CTA veya yardimci aksiyonlari perdeleyebilir."
        if screen_type in {"auth", "form"}:
            return "Bu kosumda klavye cakismasi icin belirgin bir sinyal yok; yine de canli cihazda dogrulama faydali olur."
        return "Bu ekran form merkezli olmadigi icin klavye cakismasi ana risk olarak gorunmuyor."

    def _safe_area_signal(self, findings: List[Dict[str, Any]]) -> str:
        if any(finding["category"] == "safe-area" for finding in findings):
            return "Kritik bilesenlerden bazilari cihazin ust/alt sistem alanlarina fazla yakin."
        return "Safe-area tarafinda belirgin bir cihaz kenari riski okunmadi."

    def _gesture_friction_summary(self, findings: List[Dict[str, Any]], screen_type: str) -> str:
        if any(finding["category"] == "gesture-friction" for finding in findings):
            return "Gesture ritmi aksiyon yogunlugu yuzunden zayifliyor; kaydirma akisinda dikkat bolunmesi olabilir."
        if screen_type == "feed":
            return "Feed benzeri bu ekranda gesture ritmi kabul edilebilir gorunuyor; canli replay sonraki fazda daha net karar verir."
        return "Bu ekranda gesture friction sinyali sinirli; esas risk dokunma ve yerlesim ergonomisinde toplaniyor."

    def _context_playbook(self, screen_type: str) -> List[str]:
        if screen_type == "auth":
            return [
                "Primary CTA'nin klavye acildiginda hala gorunur ve erisilebilir kaldigini kontrol et.",
                "Yardimci aksiyonlarin login gorevini golgelemediginden emin ol.",
                "OTP / sifre / e-posta alanlarinin tek elle duzgun tamamlandigini test et.",
            ]
        if screen_type == "checkout":
            return [
                "Odeme CTA'sinin thumb zone icinde kaldigini kontrol et.",
                "Toplam, teslimat ve odeme bilgilerinin alt bolgede karmasiklasmadigini incele.",
                "Klavye odagi ile form/odeme aksiyonunun cakismadigini dogrula.",
            ]
        if screen_type == "feed":
            return [
                "Ilk viewportta kart yogunlugu ve aksiyon tekrar oranini sade tut.",
                "Scroll ritmini bozan gereksiz buton veya sabit overlay var mi kontrol et.",
                "Kartlar arasi spacing ve thumb-reach dengesini karsilastir.",
            ]
        return [
            "Kritik aksiyonlarin alt erisim bolgesinde kalip kalmadigini kontrol et.",
            "Responsive spacing ve safe-area marjinlerini cihazlar arasi karsilastir.",
            "Mobilde okunabilirlik ile aksiyon yogunlugunun dengeli oldugunu dogrula.",
        ]

    def _cross_platform_parity_summary(self, screen_type: str, findings: List[Dict[str, Any]]) -> str:
        categories = {finding["category"] for finding in findings}
        if "overflow" in categories or "safe-area" in categories:
            return "Mobil yerlesim web varyantina gore daha kirilgan gorunuyor; parity sorunu buyuk ihtimalle breakpoint ve spacing tokenlerinde."
        if "thumb-zone" in categories:
            return "Web'de mantikli olan CTA konumu mobilde erisim acisindan geriye dusuyor; parity ergonomik olarak bozuluyor."
        if screen_type == "auth":
            return "Web ve mobil auth akisi benzer olabilir ama mobil tarafta birincil aksiyonun baskinligi ve klavye davranisi ayrica test edilmeli."
        return "Temel parity sinyali olumlu; derin farklar canli cihaz ve responsive matrix ile daha net acilir."

    def _recommendations(self, findings: List[Dict[str, Any]], screen_type: str) -> List[str]:
        recommendations: List[str] = []
        if any(f["category"] == "touch-target" for f in findings):
            recommendations.append("Button ve link hedeflerini mobil tap standardina gore buyut.")
        if any(f["category"] == "overflow" for f in findings):
            recommendations.append("Responsive layout constraint'lerini ve breakpoint mantigini mobilde yeniden kalibre et.")
        if any(f["category"] == "readability" for f in findings):
            recommendations.append("Dar kolonda uzun metinleri kisalt, parcala veya tipografiyi sadeleştir.")
        if any(f["category"] == "thumb-zone" for f in findings):
            recommendations.append("Ana CTA'yi thumb-friendly alt erisim bandina yaklastir ve tek elle ulasilabilir tut.")
        if any(f["category"] == "keyboard-overlap" for f in findings):
            recommendations.append("Yazilim klavyesi acildiginda CTA'nin gorunurlugunu koruyacak sticky veya scroll stratejisi ekle.")
        if any(f["category"] == "safe-area" for f in findings):
            recommendations.append("Ust/alt sistem alanlarina yakin interaktif bilesenler icin guvenli inset bosluklari tanimla.")
        if any(f["category"] == "gesture-friction" for f in findings):
            recommendations.append("Ilk viewportta swipe/scroll ritmini bozan aksiyon kalabaligini sadeleştir.")
        if screen_type == "auth":
            recommendations.append("Mobil auth ekraninda primary aksiyonu erken ve baskin konumda tut.")
        if not recommendations:
            recommendations.append("Canli device, gesture ve network kosullarini sonraki fazda ekleyerek coverage'i genislet.")
        return recommendations
