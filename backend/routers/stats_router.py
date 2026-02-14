from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Dict, Any, List

from database import get_db
from database.models import Project, TestCase, TestRun

router = APIRouter(prefix="/stats", tags=["statistics"])

@router.get("/dashboard")
def get_dashboard_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Dashboard için özet istatistikler döner:
    - Toplam proje sayısı
    - Toplam test case sayısı
    - Son 7 gündeki test run sayısı
    - Başarı oranı
    - Son test run'lar
    - Haftalık trend
    """
    
    # 1. Toplam Proje Sayısı
    total_projects = db.query(func.count(Project.id)).scalar() or 0
    
    # 2. Toplam Test Case Sayısı
    total_cases = db.query(func.count(TestCase.id)).scalar() or 0
    
    # 3. Son 7 Gündeki Test Run Sayısı
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_runs_count = db.query(func.count(TestRun.id)).filter(
        TestRun.created_at >= seven_days_ago
    ).scalar() or 0
    
    # 4. Başarı Oranı (Completed olanların yüzdesi)
    total_runs = db.query(func.count(TestRun.id)).scalar() or 0
    if total_runs > 0:
        completed_runs = db.query(func.count(TestRun.id)).filter(
            TestRun.status == "completed"
        ).scalar() or 0
        success_rate = round((completed_runs / total_runs) * 100, 1)
    else:
        success_rate = 0.0
    
    # 5. Son Test Run'lar (Son 10 tanesi)
    recent_test_runs = db.query(TestRun).order_by(TestRun.created_at.desc()).limit(10).all()
    recent_runs_data = []
    for run in recent_test_runs:
        # Test Case bilgisini al
        test_case = db.query(TestCase).filter(TestCase.id == run.test_case_id).first()
        case_title = test_case.title if test_case else "Unknown Test"
        
        # Süre hesapla (eğer varsa)
        duration = "N/A"
        if run.started_at and run.completed_at:
            delta = run.completed_at - run.started_at
            duration = f"{delta.total_seconds():.1f}s"
        
        recent_runs_data.append({
            "id": run.id,
            "case_title": case_title,
            "status": run.status,
            "duration": duration,
            "created_at": run.created_at.isoformat() if run.created_at else None
        })
    
    # 6. Haftalık Trend (Son 7 gün, her gün kaç test koşuldu)
    weekly_trend = []
    for i in range(6, -1, -1):  # 6 gün önce -> bugün
        day = datetime.utcnow() - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        count = db.query(func.count(TestRun.id)).filter(
            TestRun.created_at >= day_start,
            TestRun.created_at < day_end
        ).scalar() or 0
        
        weekly_trend.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "count": count
        })
    
    return {
        "total_projects": total_projects,
        "total_cases": total_cases,
        "recent_runs": recent_runs_count,
        "success_rate": success_rate,
        "recent_test_runs": recent_runs_data,
        "weekly_trend": weekly_trend
    }


@router.get("/alerts")
def get_alerts(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Akıllı alarm sistemi - Kritik durumları tespit eder:
    - Başarı oranı düşük (<70%)
    - Son 3 günde test sayısı azaldı
    - Yavaş testler var (>10s)
    - Sürekli fail olan testler
    """
    alerts = []
    
    # 1. Başarı Oranı Kontrolü
    total_runs = db.query(func.count(TestRun.id)).scalar() or 0
    if total_runs > 0:
        completed_runs = db.query(func.count(TestRun.id)).filter(
            TestRun.status == "completed"
        ).scalar() or 0
        success_rate = round((completed_runs / total_runs) * 100, 1)
        
        if success_rate < 70:
            alerts.append({
                "type": "critical",
                "title": "Low Success Rate",
                "message": f"Success rate is {success_rate}% (below 70% threshold)",
                "action": "Review recent failed tests and fix critical issues",
                "severity": "high"
            })
        elif success_rate < 85:
            alerts.append({
                "type": "warning",
                "title": "Success Rate Declining",
                "message": f"Success rate is {success_rate}% (below optimal 85%)",
                "action": "Monitor test failures and investigate patterns",
                "severity": "medium"
            })
    
    # 2. Test Aktivitesi Kontrolü (Son 3 gün vs önceki 3 gün)
    three_days_ago = datetime.utcnow() - timedelta(days=3)
    six_days_ago = datetime.utcnow() - timedelta(days=6)
    
    recent_count = db.query(func.count(TestRun.id)).filter(
        TestRun.created_at >= three_days_ago
    ).scalar() or 0
    
    previous_count = db.query(func.count(TestRun.id)).filter(
        TestRun.created_at >= six_days_ago,
        TestRun.created_at < three_days_ago
    ).scalar() or 0
    
    if previous_count > 0 and recent_count < previous_count * 0.5:
        alerts.append({
            "type": "warning",
            "title": "Test Activity Decreased",
            "message": f"Test runs dropped by {int((1 - recent_count/previous_count) * 100)}% in last 3 days",
            "action": "Check if CI/CD pipeline is running properly",
            "severity": "medium"
        })
    
    # 3. Yavaş Testler (>10 saniye sürenler)
    slow_runs = db.query(TestRun).filter(
        TestRun.started_at.isnot(None),
        TestRun.completed_at.isnot(None)
    ).all()
    
    slow_count = 0
    for run in slow_runs:
        if run.started_at and run.completed_at:
            duration = (run.completed_at - run.started_at).total_seconds()
            if duration > 10:
                slow_count += 1
    
    if slow_count > 0:
        alerts.append({
            "type": "info",
            "title": "Slow Tests Detected",
            "message": f"{slow_count} tests took longer than 10 seconds",
            "action": "Optimize slow test cases or increase timeout limits",
            "severity": "low"
        })
    
    # 4. Sürekli Fail Olan Testler (Son 5 koşumda 3+ fail)
    # Basit yaklaşım: Son 10 run'a bak, aynı test_case_id'den 3+ failed varsa alarm
    recent_runs = db.query(TestRun).order_by(TestRun.created_at.desc()).limit(20).all()
    fail_counts = {}
    for run in recent_runs:
        if run.status == "failed":
            fail_counts[run.test_case_id] = fail_counts.get(run.test_case_id, 0) + 1
    
    flaky_tests = [case_id for case_id, count in fail_counts.items() if count >= 3]
    if flaky_tests:
        test_case = db.query(TestCase).filter(TestCase.id == flaky_tests[0]).first()
        case_name = test_case.title if test_case else "Unknown"
        alerts.append({
            "type": "critical",
            "title": "Flaky Test Detected",
            "message": f"Test '{case_name}' failed {fail_counts[flaky_tests[0]]} times recently",
            "action": "Review test logic or fix underlying bug",
            "severity": "high"
        })
    
    return {
        "alerts": alerts,
        "total_alerts": len(alerts),
        "critical_count": len([a for a in alerts if a["severity"] == "high"]),
        "warning_count": len([a for a in alerts if a["severity"] == "medium"])
    }
