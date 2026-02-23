# VisionQA: Yapay Zekâ Destekli Entegre Yazılım Kalite ve Test Framework’ü

## Özet

Günümüz yazılım sistemleri yalnızca fonksiyonel doğruluğun sağlanmasını değil; güvenlik, erişilebilirlik, performans, kullanıcı deneyimi ve veri kalitesi gibi çok boyutlu kalite gereksinimlerinin de karşılanmasını zorunlu kılmaktadır. Geleneksel yazılım test araçları çoğunlukla belirli bir kalite boyutuna odaklanmakta ve kod ya da DOM tabanlı çalıştıkları için arayüz değişikliklerine karşı kırılganlık göstermektedir. Bu durum, test bakım maliyetlerini artırmakta ve kritik senaryoların gözden kaçmasına neden olmaktadır.

Bu çalışmada geliştirilen VisionQA, Vision-Language Models (VLM) ve Large Language Models (LLM) teknolojilerini entegre ederek yazılım kalite süreçlerini görsel algı temelli ve otonom bir yaklaşımla ele alan modüler bir test framework’üdür. Sistem; fonksiyonel test, UI/UX doğrulama, veri seti doğrulama, hata analizi, güvenlik denetimi, erişilebilirlik testi ve performans ölçümü olmak üzere yedi ana modülden oluşmaktadır.

VisionQA’nın temel yeniliği, test sürecini yalnızca kod ve DOM seviyesinde değil, doğrudan kullanıcıya görünen arayüzün görsel bağlamı üzerinden değerlendirmesidir. Bu sayede testler UI değişikliklerine karşı daha dayanıklı hale gelmekte ve insan benzeri değerlendirme yeteneği kazanılmaktadır.

**Anahtar Kelimeler:** Yazılım Test Otomasyonu, Vision-Language Models, Otonom Test Ajanı, Görsel Test, Yapay Zekâ Destekli Kalite Güvencesi, Test Framework.

---

## 1. Giriş

### 1.1 Problem Tanımı

Modern yazılım sistemleri çok katmanlı ve karmaşık yapılara sahiptir. Yazılım ürünlerinin yalnızca doğru çalışması yeterli değildir; aynı zamanda:
- Güvenli olması
- Tüm kullanıcı grupları için erişilebilir olması
- Performans gereksinimlerini karşılaması
- Tasarım ile tutarlı olması
- Yapay zekâ bileşenlerinde veri kalitesinin sağlanması

gerekmektedir. Mevcut test yaklaşımlarında bu kalite boyutları farklı araçlar ve ayrı süreçlerle ele alınmaktadır. Bu parçalı yapı, test sürecinin karmaşıklaşmasına ve yüksek bakım maliyetlerine yol açmaktadır. Ayrıca Selenium, Cypress ve benzeri araçlar DOM yapısına bağımlı çalıştığından, arayüzde yapılan küçük değişiklikler dahi testlerin bozulmasına neden olabilmektedir.

### 1.2 Çalışmanın Amacı

Bu çalışmanın amacı:
- Yazılım kalite süreçlerini tek bir entegre sistem altında toplamak
- Görsel algı temelli test yaklaşımı geliştirmek
- Otonom test üretimi sağlamak
- Yapay zekâ veri seti doğrulamasını otomatikleştirmek
- Test bakım maliyetlerini azaltmak

ve bu hedefleri gerçekleştiren modüler bir test framework’ü tasarlamak ve geliştirmektir.

---

## 2. Literatür İncelemesi

### 2.1 Geleneksel Test Araçları

- **Selenium WebDriver:** Web tabanlı uygulamalar için yaygın olarak kullanılan açık kaynak test aracıdır. DOM bağımlıdır ve manuel senaryo yazımı gerektirir.
- **Appium:** Mobil uygulamalar için geliştirilmiştir. Kurulum maliyeti yüksektir ve test senaryoları kod tabanlıdır.
- **Cypress:** Modern web uygulamalarında hızlı test imkânı sunar ancak kapsamı web ile sınırlıdır.
- **Applitools:** Görsel test yapabilmektedir ancak maliyetlidir ve tam otonom senaryo üretimi sunmaz.

### 2.2 Literatürdeki Eksiklikler

Literatür incelemesi sonucunda aşağıdaki boşluklar tespit edilmiştir:
- VLM tabanlı görsel test yaklaşımı sınırlıdır.
- UI katmanında güvenlik analizi yapan sistem yoktur.
- Yapay zekâ veri seti doğrulamasını otomatik yapan entegre platform bulunmamaktadır.
- Çoklu kalite boyutlarını birleştiren bütüncül sistem eksiktir.

VisionQA bu boşlukları doldurmayı hedeflemektedir.

---

## 3. Sistem Mimarisi

### 3.1 Genel Mimari Yaklaşım

VisionQA modüler ve katmanlı bir mimariye sahiptir:

1.  **Core Engine:** Test orkestrasyonunu yönetir. Modüller arası koordinasyonu sağlar.
2.  **Executor Katmanı:** Farklı platformlar için soyutlanmış yürütme katmanı:
    - Web Executor (Playwright tabanlı)
    - Mobile Executor (Appium)
    - Desktop Executor
    - API Executor
    - Database Executor
3.  **AI Katmanı:**
    - VLM (görsel algılama)
    - LLM (akıl yürütme ve raporlama)
    - OCR (metin tespiti)
4.  **Raporlama ve Analiz Katmanı:** Test sonuçlarını anlamlı çıktılara dönüştürür.

### 3.2 Framework Yaklaşımı

VisionQA bir SaaS uygulaması olarak değil, tekrar kullanılabilir bir test framework’ü olarak tasarlanmıştır.

Kullanım senaryoları:
- CLI üzerinden (`visionqa run`)
- Python kütüphanesi olarak import edilerek
- Web arayüzü üzerinden görsel kullanım

Bu yapı sayesinde sistem hem geliştirici hem de son kullanıcı için uygun hale getirilmiştir.

---

## 4. Modüller

### 4.1 Otonom Test Ajanı (Platform-Specific)
- VLM ile UI elementlerini algılar
- LLM ile test senaryoları üretir
- Edge-case ve negatif testleri otomatik oluşturur
- Playwright ile execution gerçekleştirir

### 4.2 UI/UX Denetçisi
- Tasarım ile canlı uygulama karşılaştırması
- Görsel regresyon analizi
- Platformlar arası tutarlılık kontrolü

### 4.3 Veri Seti Doğrulayıcı (AI-Specific)
- Görselleri VLM ile yeniden etiketler
- Mevcut etiketlerle karşılaştırır
- Hatalı veri oranını raporlar
- Confidence score üretir
*Bu modül AI projeleri için özgün bir katkı sunmaktadır.*

### 4.4 Hata Analizcisi
- Video ve screenshot analizi
- Otomatik bug raporu üretimi
- Olası kök neden analizi

### 4.5 Görsel Güvenlik Denetçisi
- UI üzerinde hassas veri sızıntısı tespiti
- Maskelenmemiş şifre alanları kontrolü
- Debug mesaj analizi

### 4.6 Erişilebilirlik Uzmanı
- WCAG uyumluluk kontrolü
- Renk kontrast analizi
- Alt-text eksiklik tespiti

### 4.7 Performans Ölçer
- Sayfa yüklenme analizi
- Render gecikmesi ölçümü
- Kullanıcı algısına dayalı performans değerlendirmesi

---

## 5. Performans ve Benchmark Sonuçları (Planlanan)

VisionQA'nın başarısı, endüstri standardı araçlarla (Selenium, Appium, Manual QA) karşılaştırmalı olarak üç temel metrik üzerinden değerlendirilecektir.

### 5.1 Robustness (Dayanıklılık) Benchmark'ı
Bu test, sistemin **Self-Healing** yeteneğini ölçer.
*   **Senaryo:** E-ticaret sitesinde "Sepete Ekle" butonunun `id` ve `class` nitelikleri kasıtlı olarak değiştirilir (Örn: `#add-to-cart` -> `#btn-primary-99`).
*   **Hedef:**
    *   **Selenium/Appium:** Test başarısız olur (%0 Başarı).
    *   **VisionQA:** Görsel algı (VLM) ile butonu tanır ve testi tamamlar (%90+ Başarı).
*   **Metrik:** `Fragility Score` (Kırılganlık Skoru)

### 5.2 Productivity (Verimlilik) Benchmark'ı
Bu test, test otomasyonu oluşturma süresini (Time-to-Value) ölçer.
*   **Senaryo:** "Login ol, ürün ara, detay sayfasına git, sepete ekle" (End-to-End Flow).
*   **Karşılaştırma:**
    *   **Manuel Otomasyon (Selenium/Code):** Ortalama 45-60 dakika (Kodlama + Debug).
    *   **VisionQA (Autonomous Agent):** Ortalama 2-3 dakika (Prompt -> Generation -> Execution).
*   **Metrik:** `Acceleration Rate` (Hızlanma Oranı - Hedef: 15x)

### 5.3 Accuracy (Görsel Doğruluk) Benchmark'ı
Bu test, AI modellerinin görsel hataları ve elementleri ne kadar doğru tespit ettiğini ölçer.
*   **Dataset:** 500 adet e-ticaret ekran görüntüsü (Butonlar, Formlar, Hata Mesajları).
*   **Hedef:**
    *   **Element Tespiti (Object Detection):** %95+ (SAM3/DINO-X ile)
    *   **Hata Sınıflandırma (Bug Classification):** %85+ (LLM Analizi ile)
*   **Metrik:** `F1 Score` ve `mAP` (mean Average Precision)

---

## 6. Katkılar

- Görsel algı temelli DOM-bağımsız test yaklaşımı
- UI bazlı güvenlik analizi
- VLM tabanlı veri seti doğrulama
- Çok modüllü entegre kalite framework’ü
- Otonom edge-case üretimi

---

## 7. Sonuç

VisionQA, yazılım kalite testini yalnızca bir otomasyon problemi olarak değil; görsel algı ve yapay zekâ destekli bütüncül bir kalite değerlendirme süreci olarak ele almaktadır. Sistem, geleneksel test araçlarının sınırlamalarını aşarak daha dayanıklı, kapsamlı ve kullanıcı deneyimi odaklı testler sunmaktadır.

Bu çalışma, yazılım kalite mühendisliğinde yapay zekâ entegrasyonunun potansiyelini göstermekte ve gelecekteki araştırmalar için güçlü bir temel oluşturmaktadır.
