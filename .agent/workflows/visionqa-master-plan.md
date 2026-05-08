---
description: VisionQA Otonom Test Mimari Planı
---

# VisionQA Otonom Test Master Planı

Bu plan, VisionQA'yı sadece butonlara basan bir araçtan, siteyi anlayan ve kendi kendine strateji geliştiren bir "Dijital Test Mühendisi" haline getirmeyi hedefler.

## 1. KATMAN: Görsel Algı ve Semantik Etiketleme (Gözler: SAM3 + DINO-X)
*   **DINO-X (Semantik Tanımlayıcı):** Nesneleri "anlamlarına" göre etiketler (Örn: "Ödeme Butonu", "Tarih Seçici").
*   **İkon Okuma:** Metinsiz sembolleri (Büyüteç, Çöp Kutusu) evrensel dile çevirir.
*   **Hiyerarşi Kurma:** "Bu fiyat bilgisi, şu otel kartının içindedir" gibi nesneler arası sahiplik ilişkisi kurar.
*   **SAM3 (Hassas Kesim):** Nesnelerin pikseller üzerindeki tam sınırlarını belirleyerek %100 isabetli tıklama sağlar.

## 2. KATMAN: Sayfa Kimliği ve İş Mantığı Keşfi (Beyin: LLM Identity Phase)
*   **Page Archetyping:** Sayfanın tipini (Login, Checkout, Product Detail vb.) belirler.
*   **Business Rule Extraction:** Sayfadaki mantıksal kuralları kendi kendine keşfeder.
    *   *Örnek:* "Adres seçilmeden ödemeye geçilemez" (Dependency Detection).
*   **Element Relationship Mapping:** Elementler arası parent-child ilişkilerini kurar.
*   **Risk Area Detection:** Test edilmesi en kritik alanları belirler.

## 3. KATMAN: Dinamik ve Risk Odaklı Senaryo Üretimi (Planning)
*   **Sınırsız Kapsam (Logical Coverage):** Sabit sayı yerine sayfanın mantıksal derinliğine göre dinamik test sayısı.
*   **Her business rule için:** 1 pozitif test (kural izlendi → başarı) + 1 negatif test (kural kasten ihlal edildi → hata beklentisi)
*   **Negatif Test Felsefesi — "The Rule Breaker":** İş kurallarını bilerek ihlal eden senaryolar.
*   **Dirençli Seçiciler:** Kırılgan CSS selector'lar yerine semantik hedeflerin kullanımı (button:has-text, aria-label, placeholder).
*   **Risk Bazlı Önceliklendirme:** critical → high → medium → low sıralamasıyla.

## 4. KATMAN: Dayanıklı İcra ve Kendi Kendini Onarma (Muscle: Self-Healing Executor)
*   **Self-Healing:** Sayfada bir şeyin yeri veya kodu değişirse görsel hafızayla yolu bulma.
*   **Global Solvers:** 
    *   **Cookie Cleanup:** Çerez banner'larını otomatik temizleme.
    *   **Pop-up Dismissal:** Bülten, reklam pop-up'larını otomatik kapatma.
    *   **Smart Wait:** Animasyonlar ve AJAX yüklemeleri için akıllı bekleme politikası.

## 5. KATMAN: Analiz ve Görsel Hata Tespiti (The Auditor)
*   **V.A.D (Visual Anomaly Detection):** Görsel kusurların (üst üste binen yazılar, kırık resimler) tespiti.
*   **Kök Neden Analizi:** Hatanın GERÇEK nedenini bulma (yüzeysel hata ≠ kök neden).

---

## 🛠️ Uygulama Fazları ve İlerleme Durumu

### ✅ Faz 1: Beyni Güçlendir (Prompt Engineering) — TAMAMLANDI
1.  ✅ **Metod-bazlı System Prompt:** Her görev için uzmanlaşmış "kişilik" (IDENTITY_SYSTEM_PROMPT, TESTGEN_SYSTEM_PROMPT, ERROR_ANALYSIS_SYSTEM_PROMPT)
2.  ✅ **`identify_page_purpose()` yeniden yazıldı:** Chain-of-Thought + Few-Shot Examples + Structured Output
3.  ✅ **`generate_test_cases()` yeniden yazıldı:** Logical Coverage stratejisi, Identity Report enjeksiyonu, semantik seçiciler, sabit test sayısı KALDIRILDI
4.  ✅ **`analyze_error()` güçlendirildi:** Kök neden analizi, self-healing action önerileri
5.  ✅ **`_format_cases()` güncellendi:** LLM risk_level'dan dinamik priority, zengin meta veriler (covers_rule, violation_strategy)

### ✅ Faz 2: Gözleri Tak (DINO-X Cloud API Entegrasyonu) — TAMAMLANDI
1.  ✅ `dinox_client.py` oluşturuldu.
2.  ✅ SAM3 + DINO-X çıktıları → Unified World View altyapısı kuruldu.
3.  ✅ Semantik etiketler ve yüksek seviyeli sayfa analizi `AICaseGenerator`'a entegre edildi.

### ✅ Faz 3: Kasları Güçlendir (Self-Healing Executor) — TAMAMLANDI
1.  ✅ `self_healing_executor.py` oluşturuldu.
2.  ✅ Global Solvers (Cookie/Pop-up dismissal) eklendi.
3.  ✅ `new_selector` destekli akıllı onarım (Healing) entegre edildi.
4.  ✅ `execution_router.py` yeni sisteme geçirildi.

### ✅ Faz 4: Denetleyiciyi Ata (Visual Anomaly Detection & Auditor)
1.  ✅ V.A.D. (Visual Anomaly Detection) entegrasyonu — `core/vad/engine.py` + 5 dedektör
2.  ✅ Post-test görsel analiz — `VADEngine.analyze_after_test()` metodu
3.  ✅ Gelişmiş hata raporlama (Screenshot karşılaştırma & Diff) — `core/vad/image_diff.py`
4.  ✅ Kök neden analizi (LLM ile CSS/HTML analizi) — `LLMClient.analyze_visual_anomalies()` metodu
