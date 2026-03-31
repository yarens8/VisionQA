# VisionQA Ultimate Platform - Task List

Bu gorev listesi referans dokuman ile hizalidir:
- Mimari: Core Engine + Executor + Modul
- Kapsam: 10 kalite modulu

---

## A. Mimari Omurga

### A1) Core Engine
- [ ] Test yasam dongusu orkestrasyonu tek servis altinda toparlanacak
- [ ] Modul yukleme mekanizmasi soyut arayuzler uzerinden standartlanacak
- [ ] Executor secim kurallari merkezi hale getirilecek
- [ ] Rapor toplama/standart cikti katmani birlestirilecek

### A2) Executor Katmani
- [x] Web executor temel calisma
- [x] API executor temel calisma
- [x] Database executor temel calisma
- [x] Mobile executor temel calisma
- [ ] Executor arayuzu tum platformlarda tek tip contract ile sertlestirilecek
- [ ] Ortak retry/timeout/policy yapisi tum executorlara uygulanacak

### A3) Modul Katmani
- [ ] Her modul icin ortak giris/cikis semasi tanimlanacak
- [ ] Moduller bagimsiz etkinlestirilebilir/devre disi birakilabilir hale getirilecek
- [ ] Modul sonuc normalizasyonu tamamlanacak

---

## B. 10 Modul Yol Haritasi

### 4.1 Otonom Test Modulu
- [x] Sayfa analizi (gorsel + LLM baglam)
- [x] Otomatik test case uretimi
- [x] Pozitif/negatif senaryo olusturma
- [x] Step bazli execution
- [ ] Cok platformlu (web disi) production seviye parity

### 4.2 Hata Analiz ve Raporlama Modulu
- [x] Step bazli hata/sonuc toplama
- [x] Reason/error alanlari
- [ ] Standart rapor semasi (ozet + yeniden uretim + kanit)
- [ ] Export formatlari (JSON/HTML/PDF)
- [ ] Kanit paketleme (screenshot/log/artifact)

### 4.3 UI/UX Denetim Modulu
- [x] Layout tutarlilik kontrolu
- [x] Bilesen tutarliligi
- [x] Tasarim uyum analizi
- [x] Screenshot tabanli bulgu ve preview akisi v1+
- [x] History kaydi / favori / yeniden adlandirma / silme
- [x] Yorumlayici UX finding katmani (hiyerarsi / whitespace / okuma akisi / attention v1)
- [ ] Mobil ekran uyumu

### 4.4 Veri Seti Dogrulama Modulu
- [x] Yanlis etiket sinyali v1
- [x] Eksik etiket kontrolu v1
- [x] Tutarsiz sinif analizi v1
- [x] Veri butunlugu raporu v1

### 4.5 Guvenlik Denetim Modulu
- [x] Hassas veri ifsasi kontrolu
- [x] Maskelenmemis alan tespiti
- [x] Hata mesaji guvenlik analizi
- [x] Acik konfigurasyon bilgisi taramasi
- [x] Screenshot/OCR tabanli security exposure audit v1
- [x] URL + response/header tabanli security hardening audit v2
- [x] AI saldiri hipotezi uretimi v3
- [x] Cross-platform attack correlation ve root-cause katmani v4

### 4.6 Erisilebilirlik Modulu
- [x] Visual-first screenshot tabanli temel analiz altyapisi
- [x] Tam sayfa kontrast / heatmap v1
- [x] Bulgu kutusu + kart eslesmesi
- [x] Secili bulgu crop preview akisi
- [x] Temel aday bilesen tespiti ve onceliklendirme v1
- [x] Bilesen tespit kalitesini artirma
- [x] Focus visibility sinyalleri
- [x] Alt-text kontrolu (metadata destekli v1)
- [x] Klavye navigasyonu (metadata destekli v1)
- [x] Dokunma alani boyutlari
- [x] Daha akilli bilesen siniflandirma (DINO destekli v1)
- [x] 4.6.1 OCR-hazir text-region cikarimi ve text-hint relabeling v1
- [x] 4.6.1 text-region adaylarindan buton / input / metin rolu cikarimi v2
- [x] 4.6.1 DINO kutularindan semantik aday uretimi ve text-fragment bastirma v3
- [x] 4.6.2 Gercek OCR kurulumu (Tesseract + pytesseract) ve Windows yol cozumleme
- [x] 4.6.2 OCR kelime satiri birlestirme v1
- [x] 4.6.3 Baslik / yardimci metin / giris alani rol ayrimi v1
- [x] 4.6.4 DINO + OCR hibrit siniflandirma v1
- [x] 4.6.5 Web metadata ile button / input / link kesinlestirme v1
- [x] 4.6.5 Mobile metadata adapter v1
- [x] 4.6.5 Desktop metadata adapter v1

### 4.7 Performans Analiz Modulu
- [x] Sayfa yuklenme suresi v1
- [x] API yanit suresi v1
- [ ] Mobil acilis suresi
- [x] Veritabani sorgu sureleri v1

### 4.8 API Test Modulu
- [x] Endpoint cagri altyapisi
- [x] Response dogrulama temeli
- [x] Hata senaryosu jenerasyonu v1
- [x] Sozlesme (schema) uyum denetimi v1

### 4.9 Mobil Test Modulu
- [x] Temel mobil executor
- [x] Mobil capability tanimi ve desteklenen akislari urunlestirme v1
- [x] Screenshot + metadata tabanli AI Mobile UX Analyzer v1
- [x] Context-aware mobile screen yorumlari v1
- [x] Cross-platform consistency signal v1
- [ ] Gesture test kapsami genisletme
- [ ] Ekran boyutu uyum matrisi
- [ ] Ag kosulu simulasyonu

### 4.10 Veritabani Kalite Modulu
- [x] Temel DB executor
- [x] Sorgu calistirma/sema dogrulama temeli
- [x] Veri iliski ve tutarlilik analizleri v1
- [x] Yavas sorgu raporlama olgunlastirma v1

---

## C. Kisa Faz Plani

### Faz 1 - Temel (Tamamlandi/Kismi)
- [x] Proje iskeleti
- [x] Backend + Frontend calisir durum
- [x] Temel executorlar
- [x] Temel AI entegrasyonu

### Faz 2 - Cekirdek Moduller (Devam)
- [x] 4.1 ana akis
- [x] 4.2 kismi
- [x] 4.6 visual-first accessibility v1
- [ ] Raporlama standardizasyonu

### Faz 3 - Kalan Moduller
- [ ] 4.3 - 4.10 modullerinin production seviyesi tamamlanmasi

---

## D. Kabul Kriterleri

- [ ] Tek kaynakli pipeline: LLM -> Backend -> DB -> Test Library
- [ ] Modul bazli bagimsiz calisma
- [ ] Platformlar arasi ortak execution policy
- [ ] Standart rapor semasi ve kanit ciktisi

---

## E. Erisilebilirlik Checkpoint

- Mevcut adim: `4.6 v1 donduruldu ve kapanis seviyesine getirildi`
- Tamamlananlar:
  - screenshot yukleme ve analiz endpoint'i
  - tam sayfa heatmap / overlay v1
  - secili bulgu preview akisi
  - bulgu karti ile kutu eslesmesi
  - temel bilesen aday tespiti
  - gelistirilmis bilesen birlestirme ve onceliklendirme
  - kucuk dokunma/tiklama alanlari icin touch target bulgulari
  - odak gorunurlugu icin focus visibility bulgulari
  - metadata geldigi durumda alt-text bulgulari
  - metadata geldigi durumda keyboard navigation bulgulari
  - DINO mevcutsa daha akilli bilesen yeniden etiketleme
  - gercek OCR kurulumu (Tesseract + pytesseract) ve engine'e baglanmasi
  - OCR satir birlestirme v1
  - baslik / yardimci metin / giris alani rol ayrimi v1
  - DINO + OCR hibrit siniflandirma v1
  - metin tasiyan adaylar icin DINO ikon downgrade korumasi
  - ikon kirpintilarini metin/semantik kutular icinde daha agresif bastirma
  - web metadata ile button / input / link kesinlestirme v1
  - mobile executor icin metadata cikarma v1
  - desktop executor icin metadata cikarma v1
  - analiz edilen screenshot ve URL gecmisini otomatik kaydetme
  - kaydedilen accessibility analizlerini UI uzerinden listeleme ve tekrar acma
  - kayitli accessibility analizleri icin favori / yeniden adlandirma / silme / filtreleme
- Siradaki is:
  - 4.6.6 Gercek ekranlarla tuning ve yanlis siniflandirma temizligi
  - 4.6.7 Dokumantasyonun son hale getirilmesi

## F. UI/UX Checkpoint

- Mevcut adim: `4.3 screenshot tabanli UI/UX v1+ vitrin seviyesine getirildi`
- Tamamlananlar:
  - screenshot yukleme ve analiz endpoint'i
  - layout alignment finding v1
  - dikey spacing finding v1
  - ayni satirdaki boyut tutarliligi finding v1
  - annotated goruntu ve secili crop preview akisi
  - frontend sayfasi uzerinden standart skor + finding listesi gosterimi
  - gorsel hiyerarsi / CTA baskinligi / intent mismatch finding'leri
  - whitespace balance / section separation / readability flow finding'leri
  - attention flow / conversion friction / trust signal / persona risk v1 finding'leri
  - attention overlay gorunumu
  - analiz gecmisi kaydetme, tekrar acma, favori / yeniden adlandirma / silme
- Siradaki is:
  - URL tabanli analiz akisi
  - mobil ekran varyantlari ve responsive parity
  - design system / spec karsilastirma derinlestirme

## G. Security Checkpoint

- Mevcut adim: `4.5 katmanli Security Intelligence Framework v1-v4 ilk calisan surume getirildi`
- Tamamlananlar:
  - screenshot yukleme ile security analizi
  - OCR tabanli gorunur metin taramasi
  - e-posta / telefon / token / kart benzeri veri ifsasi finding'leri
  - stack trace / exception / debug-page sinyali finding'leri
  - overlay goruntu ve secili bulgu crop preview akisi
  - URL tabanli analiz ile screenshot alma
  - response text toplama ve security sinyaline baglama
  - response header uzerinden temel hardening kontrolleri
  - CSP / X-Frame-Options / X-Content-Type-Options / Referrer-Policy eksigi finding'leri
  - HTTP kullanimina karsi transport-security finding'i
  - session cookie Secure / HttpOnly / SameSite ve genis CORS sinyalleri
  - auth / search / upload / admin / API baglamina gore saldiri hipotezi uretimi
  - brute force / enumeration / SQLi / XSS / upload abuse / authz bypass / IDOR-mass assignment hipotezleri
  - attack playbook adimlari, confidence ve priority ile zenginlestirilmis hipotezler
  - attack chain sinyalleri, linked evidence ve root cause taxonomy yorumlari
  - SecurityPage uzerinde Visual / Surface / Hypotheses / Correlation katmanlari ile framework gorunumu
  - primary context ve attack readiness ozetleri
  - URL tabanli kontrollu active simulation starter
  - method discovery / reflection / SQL-like davranis / temel IDOR probe sinyalleri
  - payload family library ve role-based scenario onerileri
  - security history kaydi, tekrar acma, favori / yeniden adlandirma / silme
  - API / DB / scenario modullerine yonlendiren cross-module security hints
- Security Intelligence Framework hedef katmanlari:
  - Layer 1 `Visual Exposure`: screenshot + OCR + metadata ile PII, token, debug, maskelenmemis alan, config/info exposure
  - Layer 2 `Surface Security Audit`: URL + response + headers + body ile transport, header hardening, auth/cookie ve yuzey riskleri
  - Layer 3 `AI Attack Hypotheses`: sayfa/endpoint baglamina gore brute force, SQLi, XSS, IDOR, upload abuse, enumeration gibi test hipotezleri
  - Layer 4 `Attack Correlation & Root Cause`: web + API + DB sinyallerini baglayip attack chain, muhtemel kok neden ve remediation path cikarimi
- Siradaki is:
  - executor tabanli aktif negatif security probing
  - auth / cookie / header derinlestirme ve kanit toplama
  - security history kaydi ve tekrar acma akisi
  - web + API + DB arasinda daha kuvvetli attack chain korelasyonu

## H. API Checkpoint

- Mevcut adim: `4.8 AI yorumlu API analiz modulu guclu v1`
- Tamamlananlar:
  - manuel request kosumu uzerinden standart analiz endpoint'i
  - status mismatch / slow response / server error / error leakage finding'leri
  - API endpoint icin beklenmeyen HTML content-type sinyali
  - auth headersiz mutating request basarisi icin risk sinyali
  - OPTIONS ve reflection tabanli basit negatif kontrol akisi
  - beklenen field ve response-type ile basit contract/schema uyum denetimi
  - endpoint context siniflandirmasi (auth / upload / search / admin / mutation / generic)
  - AI failure explanation ve root cause summary
  - context-aware test generation
  - endpoint risk score ve health/validation/security/performance/contract score breakdown
  - cross-module correlation (performance / security / DB / UIUX)
  - frontend uzerinde overall score + risk score + AI aciklama + generated tests + correlation + raw response gorunumu
- Siradaki is:
  - OpenAPI schema kontrati ile derin response validation
  - header/cookie/auth expectation profilleri
  - cok adimli API senaryolari ve history akisi
  - aktif role-based negative execution genisletme

## I. Veritabani Checkpoint

- Mevcut adim: `4.10 AI yorumlu veritabani kalite modulu guclu v1`
- Tamamlananlar:
  - query metninden SELECT star / limitsiz select / mutation / DDL risk sinyali
  - query latency uzerinden slow query finding'leri
  - tablo sema audit'i ve eksik kolon bulgulari
  - bos tablo, yuksek null density ve duplicate identifier sinyalleri
  - format consistency ve security-storage sinyalleri
  - business rule violation detector v1
  - constraint summary (primary key / foreign key / unique / nullable)
  - schema smell detection v1
  - table quality score ve integrity/completeness/consistency/performance/security breakdown
  - AI interpretation ve root cause summary
  - API-DB consistency check v1
  - frontend uzerinde overall score + table quality + AI yorum + schema snapshot + smells + sample rows gorunumu
- Siradaki is:
  - tablo iliski analizi ve foreign key tutarliligi
  - explain plan / index coverage yorumlari
  - kalite audit history ve tekrar acma akisi

## J. Performans Checkpoint

- Mevcut adim: `4.7 AI yorumlu performans modulu guclu v1`
- Tamamlananlar:
  - web page load / FCP / LCP / TTI / CLS benzeri temel browser metrikleri v1
  - API average / p50 / p95 / p99 / timeout ve error-rate sinyalleri
  - DB query duration korelasyonu
  - teknik skor ve user perceived performance score ayrimi
  - AI root cause analyzer ve optimization suggestions
  - performans bulgulari icin web / api / db bazli finding uretimi
  - performans ile API / DB / UIUX arasinda cross-module correlation yorumlari
  - frontend uzerinde score, metrics, finding, AI summary ve correlation gorunumu
- Siradaki is:
  - daha derin browser perf observer ve resource telemetry
  - concurrency/load profilini genisletme
  - mobil startup/FPS telemetry
  - trend/history akisi

## K. Dataset Checkpoint

- Mevcut adim: `4.4 AI yorumlu dataset kalite modulu guclu v1`
- Tamamlananlar:
  - JSON tabanli dataset validation akisi
  - eksik label, bozuk kayit ve annotation health finding'leri
  - class distribution ve imbalance sinyalleri
  - label consistency ve suspicious label signal v1
  - duplicate signal / tekrar eden fingerprint tespiti v1
  - completeness / balance / consistency / validity / annotation health score breakdown
  - overall dataset quality score ve grade
  - training risk summary ve impacted areas
  - synthetic data suggestion katmani
  - frontend uzerinde dataset input, score, findings, duplicate/suspicious signal ve AI interpretation gorunumu
- Siradaki is:
  - goruntu/etiket uyumu ile mislabeled detection derinlestirme
  - near-duplicate clustering
  - model ciktilari ile dataset korelasyonu
  - dataset history ve tekrar acma akisi

## L. Mobil Checkpoint

- Mevcut adim: `4.9 mobil capability + AI Mobile UX Analyzer guclu v1`
- Tamamlananlar:
  - mobil executor kapasitesinin urun icinde net konumlandirilmasi
  - screenshot + metadata tabanli mobil analiz endpoint'i
  - touch target, readability, overflow, density ve auth friction finding'leri
  - login / search / checkout / form / feed / detail baglamina gore context-aware yorum
  - mobile UX / touch / readability / layout / interaction readiness score breakdown
  - supported now ve next phase capability kartlari
  - cross-platform consistency signal ve root cause summary
  - frontend uzerinde mobil screenshot + metadata input ve AI yorum gorunumu
  - thumb-zone, keyboard overlap, safe-area ve gesture friction sinyalleri
  - AI Mobile UX Critic ve context playbook katmani
  - cross-platform parity summary ve task completion friction skoru
- Siradaki is:
  - canli emulator/device farm akisi
  - gesture replay ve mobile action telemetry
  - FPS / battery / memory / network shaping katmanlari
