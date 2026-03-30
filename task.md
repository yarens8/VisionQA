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
- [ ] Mobil ekran uyumu

### 4.4 Veri Seti Dogrulama Modulu
- [ ] Yanlis etiket tespiti
- [ ] Eksik etiket kontrolu
- [ ] Tutarsiz sinif analizi
- [ ] Veri butunlugu raporu

### 4.5 Guvenlik Denetim Modulu
- [ ] Hassas veri ifsasi kontrolu
- [ ] Maskelenmemis alan tespiti
- [ ] Hata mesaji guvenlik analizi
- [ ] Acik konfigurasyon bilgisi taramasi

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
- [ ] Sayfa yuklenme suresi
- [ ] API yanit suresi
- [ ] Mobil acilis suresi
- [ ] Veritabani sorgu sureleri

### 4.8 API Test Modulu
- [x] Endpoint cagri altyapisi
- [x] Response dogrulama temeli
- [ ] Hata senaryosu jenerasyonu
- [ ] Sozlesme (schema) uyum denetimi olgunlastirma

### 4.9 Mobil Test Modulu
- [x] Temel mobil executor
- [ ] Gesture test kapsami genisletme
- [ ] Ekran boyutu uyum matrisi
- [ ] Ag kosulu simulasyonu

### 4.10 Veritabani Kalite Modulu
- [x] Temel DB executor
- [x] Sorgu calistirma/sema dogrulama temeli
- [ ] Veri iliski ve tutarlilik analizleri
- [ ] Yavas sorgu raporlama olgunlastirma

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

- Mevcut adim: `4.3 screenshot tabanli UI/UX v1 ayaga kaldirildi`
- Tamamlananlar:
  - screenshot yukleme ve analiz endpoint'i
  - layout alignment finding v1
  - dikey spacing finding v1
  - ayni satirdaki boyut tutarliligi finding v1
  - annotated goruntu ve secili crop preview akisi
  - frontend sayfasi uzerinden standart skor + finding listesi gosterimi
- Siradaki is:
  - URL tabanli analiz akisi
  - mobil ekran varyantlari ve responsive parity
  - design system / spec karsilastirma derinlestirme
