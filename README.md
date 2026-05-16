# VisionQA Platform

AI-assisted software quality and testing framework

## Overview

VisionQA, test sureclerini sadece fonksiyonel kontrol ile sinirlamayan; guvenlik, performans, erisilebilirlik, UI/UX, API ve veritabani kalite boyutlarini tek bir framework altinda birlestiren bir platformdur.

VisionQA bir son kullanici SaaS urunu degil; gelistirici ve QA ekipleri tarafindan yeniden kullanilabilir bir test altyapisi olarak tasarlanmistir.

## Problem Statement

Modern kalite sureclerinde ekipler genellikle farkli araclara bolunur:

- Fonksiyonel test, guvenlik, performans ve erisilebilirlik ayri araclarla yurutulur.
- Bu parcali yapi test bakimini zorlastirir ve operasyonel maliyeti artirir.
- DOM/selector bagimli yaklasimlar UI degisimlerinde kolay kirilir.
- Hata kanitlari ve raporlar standart olmadigi icin triage sureleri uzar.

VisionQA bu problemi, moduler ama tek orkestrasyon altinda calisan bir framework modeliyle cozer.

## Why VisionQA

| Klasik Yaklasim | VisionQA Yaklasimi |
|---|---|
| Tek kalite boyutuna odakli araclar | Tek framework altinda coklu kalite boyutu |
| Yüksek selector/DOM kirilganligi | Gorsel + baglamsal analizle daha dayanikli akış |
| Ayrik raporlama formatlari | Standardize rapor ciktilari |
| Platform bazli daginik otomasyon | Web/Mobile/API/DB icin tek orkestrasyon modeli |

## Core Workflow

1. Analyze: Hedef sistem gorsel/teknik olarak analiz edilir.
2. Generate: LLM destekli senaryolar ve adimlar olusturulur.
3. Execute: Uygun executor ile adimlar kosulur.
4. Report: Sonuclar standart rapor ve kanit ciktilarina donusturulur.

## Supported Platforms

- 🌐 Web Applications (React, Angular, Vue, etc.)
- 📱 Mobile Apps (iOS, Android, React Native, Flutter)
- 🖥️ Desktop Applications (Windows, macOS, Linux, Electron)
- 🔌 API Services (REST, GraphQL, WebSocket, gRPC)
- 🗄️ Databases (PostgreSQL, MySQL, MongoDB, Redis)

## ✨ Key Features

### 10 Testing Modules

1. 🤖 **Autonomous Tester** - Test modulu SAM3 veya Grounding DINO tabanli opsiyonel sayfa analizi ile LLM destekli page identity, business rule discovery ve test case generation akisini birlestirir; risk dengeli pozitif/negatif scenario taslaklari uretir. Step bazli execution, run progress, execution summary ve protocol loglari sayesinde hangi adimin neden koptugu okunabilir hale gelir; self-healing executor katmani overlay temizleme, selector iyilestirme ve retry denemeleriyle kosuyu daha dayanikli hale getirmeyi hedefler. Web akisi aktif v1 seviyesindedir; diger platformlarda parity gelistirme alanidir.
2. 🎨 **Cross-Platform UI/UX Auditor** - Web, mobil ve masaustu uygulamalarda tasarim ile gercek arayuzun uyumunu analiz eder. Layout hatalari, hizalama problemleri ve gorsel tutarsizliklari tespit eder.
3. 🧾 **AI Dataset Validator** - Dataset modulu yalnizca eksik veri veya class imbalance bulmakla kalmaz; annotation health, label consistency, suspicious label sinyali, duplicate/near-duplicate benzeri tekrarlar, split health ve coverage gaps katmanlarini birlikte yorumlar. Dataset Quality Score ile completeness, balance, consistency, validity ve annotation health eksenlerinde puanlama yapar; Training Risk Analyzer ve Dataset -> Model Impact ozetleri ile bu veri setinin egitim tarafinda ne tur riskler uretebilecegini aciklar. Synthetic data suggestion, collection target onerileri ve bulgu bazli AI interpretation sayesinde sadece sorun degil, sonraki veri toplama ve iyilestirme yonu de tarif edilir.
4. 🎥 **Universal Bug Analyzer** - Bug analyzer katmani step bazli hata/sonuc toplama, reason/error sinyalleri, execution summary ve run loglari ile kosu sonrasini okunur hale getirir. JSON export akisi ve Jira/Slack entegrasyon starter'lari mevcut; boylece bulunan problem sadece tespit edilmez, paylasilabilir bir rapor akisina da baglanir. Buna karsin kanit paketleme, tam standardize bug schema ve zengin export formatlari halen genisletilmesi gereken alanlardir.
5. 🔒 **Multi-Platform Security Auditor** - Guvenlik modulu tek bir scanner degil, katmanli bir `Security Intelligence Framework` olarak tasarlanir. Visual Exposure katmani screenshot/OCR/metadata ile hassas veri ifsasini, token veya debug sizintilarini bulur. Surface Security Audit katmani URL, response body ve header uzerinden temel sertlestirme ve dis yuzey risklerini denetler. Sonraki katmanlarda AI Attack Hypotheses ile baglama gore hangi saldiri siniflarinin denenmesi gerektigi uretilir; Attack Correlation & Root Cause ile web, API ve veritabani sinyalleri baglanarak attack chain ve muhtemel kok neden aciklanir.
6. ♿ **Accessibility Analyzer** - Screenshot veya URL girdileri uzerinden visual-first erisilebilirlik sinyalleri uretir. Sayisal goruntu isleme kullanarak kontrast, okunabilirlik, renk ayrismasi ve gorunur erisilebilirlik risklerini tespit eder; OCR, opsiyonel vision provider ve metadata destekli bilesen anlama ile buton, giris alani, yardimci metin ve benzeri UI parcalarini yorumlayip iyilestirme onerileri uretir.
7. 🚀 **Cross-Platform Performance Analyzer** - Performans modulu web, API ve DB sinyallerini ayni analiz altinda toplar. Web tarafinda page load ve temel browser metric'leri; API tarafinda avg/p50/p95/p99, timeout ve error-rate; DB tarafinda query duration ve query-level latency korelasyonu uretir. Technical Score ile User Perceived Performance Score ayridir; AI Performance Root Cause Analyzer, bottleneck confidence, timeline summary ve module-specific optimization suggestions ile performans sayilari yorumlanan bir rapora donusur. Boylece metrikler sadece olculmez, muhtemel darbogaz kaynagi da UI/API/DB baglaminda aciklanir.
8. 📱 **Mobile-Specific Test Suite** - Mobil modulu mevcut capability'yi durustce urunlestirir ve screenshot + metadata tabanli `AI Mobile UX Analyzer` cikarir. Touch target, readability, overflow, density, auth friction, thumb-zone analysis, keyboard overlap, safe-area risk ve gesture friction sinyalleri uretilir. Screen type baglamina gore context-aware mobile yorum, task completion friction, context playbook ve cross-platform parity summary sunulur; `supported now` ve `next phase` ayrimi ile canli emulator/device farm, battery/FPS telemetry ve network shaping gibi daha ileri katmanlar net sekilde konumlandirilir.
9. 🔌 **API Test Suite** - API modulu klasik request calistiricidan daha genis bir analiz katmani sunar. Endpoint health check, response/status validation, basit contract kontrolu ve negatif senaryo sinyallerini tek cikti altinda toplar. AI Failure Explanation katmani bir 5xx veya validation sapmasinin muhtemel nedenini yorumlar; Context-Aware Test Generation endpoint baglamina gore login, search, upload veya admin akislarina uygun test onerileri cikarir. Endpoint Risk Score ve cross-module correlation sayesinde API bulgulari performans, security ve DB modulleriyle bir arada okunabilir.
10. 🗄️ **Database Quality Checker** - Veritabani modulu sadece query calistirmaz; schema quality, constraint, veri tutarliligi, null yogunlugu, risky query ve security-storage sinyallerini birlikte yorumlar. Table Quality Score ile integrity, completeness, consistency, performance ve security eksenlerinde puanlama yapar. Business Rule Violation Detector ve Schema Smell Detection sayesinde sadece teknik hata degil, zamanla bozulmus tablo tasarimi veya is kurali sapmalari da gorunur hale gelir; AI interpretation katmani bulgularin olasi etkisini ve duzeltme yonunu aciklar.

## 🏗️ Architecture

VisionQA katmanli bir framework mimarisi kullanir:

```text
┌──────────────────────────────────────────────────────────────┐
│                    VisionQA Interface Layer                  │
│                Web Dashboard / CLI / SDK Entry              │
└───────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────┐
│                         Core Engine                          │
│  - Test orchestration                                        │
│  - Module loading                                            │
│  - Executor selection                                        │
│  - Result aggregation                                        │
└───────────────┬───────────────────────────┬──────────────────┘
                │                           │
                ▼                           ▼
┌──────────────────────────────┐   ┌───────────────────────────┐
│        Executor Layer        │   │        Module Layer       │
│  Web / Mobile / API / DB     │   │  10 Quality Modules       │
│  Action execution + telemetry │   │  Domain analysis + report │
└───────────────┬──────────────┘   └──────────────┬────────────┘
                │                                 │
                └──────────────┬──────────────────┘
                               ▼
                 ┌──────────────────────────────┐
                 │   Standard Report Output      │
                 │ JSON / UI Report / Evidence   │
                 └──────────────────────────────┘
```

1. **Core Engine**
- Test yasam dongusunu orkestre eder.
- Modulleri dinamik yukler.
- Uygun executor secimini yapar.
- Sonuclari toplayip raporlama akisina aktarir.

2. **Executor Layer**
- Hedef platform ile baglanti kurar.
- Test adimlarini yurutur.
- Ortam ve calisma bilgilerini toplar.
- Sonuclari Core Engine'e iletir.

3. **Module Layer**
- Her modul tek bir kalite alanina odaklanir.
- Test ciktilarini alan bazli analiz eder.
- Standart bir cikti formatina donusturur.
- Gerektiginde visual-first ve sayisal goruntu isleme tabanli analiz yaklasimlari kullanir.

High-level flow:

`Input (Web/Mobile/API/DB) -> Core Engine -> Executor -> Module Analysis -> Standard Report`

## Development Principles

- Platform independence
- Modular extensibility
- Low coupling / high cohesion
- Central orchestration
- Long-term sustainability

## Design Principles

- Single source of truth: Test uretimi ve kayit akisinda tek kaynakli pipeline.
- Deterministic orchestration: Kosu politikasi, retry/timeout ve sira yonetimi merkezi.
- Module isolation: Her kalite modulunun bagimsiz gelistirilebilir yapisi.
- Executor abstraction: Platform farklarini soyutlayan ortak calistirma modeli.

## Current Module Snapshot

Su an platform icinde moduller ayni olgunluk seviyesinde degildir; bazilari aktif v1, bazilari erken/orta v1 seviyesindedir.

- `4.1 Autonomous Tester`: aktif v1. SAM3 primary ve Grounding DINO fallback destekli opsiyonel sayfa analizi, LLM destekli identity/business-rule/case generation, pozitif/negatif scenario uretimi, self-healing destekli step bazli execution ve run log/summary akisi mevcut; web akisi ana odaktir, multi-platform parity sonraki gelistirme alanidir.
- `4.2 Bug Analyzer`: erken/orta v1. Step log, execution summary, JSON export ve Jira/Slack starter akislari var; ancak standardize reproduction schema, artifact packaging ve zengin export formatlari henuz tamamlanmadi.
- `4.6 Accessibility`: aktif v1. OCR + opsiyonel vision provider + metadata destekli visual-first accessibility analiz akisi, history ve URL/screenshot akisi mevcut.
- `4.3 UI/UX`: aktif v1. Screenshot tabanli finding, UX critic ozeti, score sistemi, attention/focus yorumlari ve history akisi mevcut.
- `4.5 Security`: aktif v1. Visual exposure, surface audit, attack hypotheses, correlation/root cause ve active simulation starter akislari mevcut.
- `4.7 Performance`: aktif v1. Web/API/DB metrikleri, technical vs perceived score, root cause, timeline summary ve optimization katmanlari mevcut.
- `4.8 API`: aktif v1. Endpoint health, validation, context-aware test generation, risk scoring ve failure explanation mevcut.
- `4.10 Database`: aktif v1. Schema/constraint/consistency/performance/security yorumu, table quality score ve interpretation akisi mevcut.
- `4.4 Dataset`: aktif v1. Validation, class balance, annotation health, duplicate/suspicious label sinyali, split health, training risk, synthetic suggestion, collection target ve model impact akislari mevcut.
- `4.9 Mobile`: aktif v1. Capability positioning, mobile UX analyzer, thumb-zone/keyboard/safe-area/gesture friction katmanlari ve parity yorumlari mevcut.

Sonraki fazlarda moduller history/trend, deeper telemetry, live execution parity ve cross-module chain analiziyle daha da derinlestirilecektir.

## Vision Providers

SAM3 ve Grounding DINO opsiyonel runtime provider olarak kullanilir. Varsayilan akista `VISION_MODEL_PROVIDER=sam3`, `VISION_MODEL_FALLBACK=dinox` seklindedir; SAM3 yuklenemezse veya sonuc uretmezse Grounding DINO denenir. CI yalnizca import ve fallback davranisini test eder, gercek model indirme/inference calistirmaz.

Yerel Docker smoke testi:

```bash
docker compose run --rm sam3-cache
```

Bu komut `facebook/sam3` modelini `huggingface_cache` volume'una indirir. Volume silinmedigi surece sonraki calistirmalarda model yeniden indirilmez; sadece cache'ten yuklenir.
