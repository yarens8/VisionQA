# VisionQA Ultimate Platform

AI Destekli Cok Platformlu Yazilim Kalite ve Test Framework'u

## 1. Giris

VisionQA, yalnizca fonksiyonel dogrulamaya odaklanan klasik test araclarinin otesinde; guvenlik, performans, erisilebilirlik, UI/UX, API ve veritabani kalite kontrollerini tek bir framework altinda birlestirmeyi hedefler.

Bu proje bir son kullanici uygulamasi degil, gelistirici ve QA ekiplerinin kullanabilecegi yeniden kullanilabilir bir test altyapisidir.

## 2. Projenin Amaci

VisionQA'nin amaci kalite kontrol sureclerini tek bir cati altinda toplamak:

- Coklu platform test yurutme
- Moduler kalite kontrol
- Otonom test uretimi
- Guvenlik ve performans analizi
- Erisilebilirlik denetimi
- API dogrulama
- Veritabani kalite kontrolu
- AI veri seti dogrulama

## 3. Framework Mimarisi

VisionQA 3 ana katmandan olusur:

1. Core Engine
- Test yasam dongusunu orkestre eder
- Modulleri dinamik yukler
- Uygun executor secer
- Sonuclari toplar ve raporu baslatir

2. Executor Katmani
- Platforma baglanir ve adimlari yurutur
- Ortam bilgisini toplar
- Sonuclari Core Engine'e iletir
- Hedef platformlar: Web, Mobile, API, Database

3. Modul Katmani
- Her modul tek bir kalite alanina odaklanir
- Standart cikti uretir
- Bagimsiz gelistirilip devreye alinabilir

## 4. Framework Modulleri (10)

1. Otonom Test Modulu
2. Hata Analiz ve Raporlama Modulu
3. UI/UX Denetim Modulu
4. Veri Seti Dogrulama Modulu
5. Guvenlik Denetim Modulu
6. Erisilebilirlik Modulu
7. Performans Analiz Modulu
8. API Test Modulu
9. Mobil Test Modulu
10. Veritabani Kalite Modulu

## 5. Mevcut Durum (Kisa)

- 4.1 Otonom Test Modulu: Calisiyor (analiz, case uretimi, step-based execution)
- 4.2 Hata Analiz ve Raporlama: Kismi (step error/success ozetleri var, standart raporlama gelistiriliyor)
- Diger moduller: yol haritasinda

## 6. Gelistirme Prensipleri

- Platform bagimsizlik
- Moduler genisletilebilirlik
- Low coupling / high cohesion
- Merkezi orkestrasyon
- Uzun vadeli surdurulebilirlik

## 7. Hizli Baslangic

Gereksinimler:

- Python 3.10+
- Node.js 20+
- PostgreSQL (opsiyonel, SQLite fallback destekli)
- Playwright Chromium

Kurulum:

```bash
git clone <repo-url>
cd VisionQA
cp .env.example .env
```

Backend:

```bash
cd backend
python run_server.py
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## 8. Dokumanlar

- `PROJECT_PLAN.md` -> Proje plani
- `PROJECT_REPORT.md` -> Akademik/teknik rapor
- `task.md` -> Uygulama gorev plani

