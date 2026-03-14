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
- [ ] Layout tutarlilik kontrolu
- [ ] Bilesen tutarliligi
- [ ] Tasarim uyum analizi
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
- [ ] Kontrast oran kontrolu
- [ ] Alt-text kontrolu
- [ ] Klavye navigasyonu
- [ ] Dokunma alani boyutlari

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
- [ ] Raporlama standardizasyonu

### Faz 3 - Kalan Moduller
- [ ] 4.3 - 4.10 modullerinin production seviyesi tamamlanmasi

---

## D. Kabul Kriterleri

- [ ] Tek kaynakli pipeline: LLM -> Backend -> DB -> Test Library
- [ ] Modul bazli bagimsiz calisma
- [ ] Platformlar arasi ortak execution policy
- [ ] Standart rapor semasi ve kanit ciktisi

