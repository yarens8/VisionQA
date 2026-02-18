from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import datetime, timedelta
from typing import Dict, Any

from database import get_db
from database.models import Project, TestCase, TestRun, TestStatus

router = APIRouter(prefix="/stats", tags=["statistics"])


@router.get("/dashboard")
def get_dashboard_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Dashboard için özet istatistikler döner:
    - Toplam proje sayısı
    - Toplam test case sayısı
    - Son 7 gündeki test run sayısı
    - Başarı oranı
    - Platform bazlı dağılım (Ultimate Platform için)
    - Son test run'lar (platform bilgisiyle)
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

    # 4. Başarı Oranı - Tek sorguda hem toplam hem completed sayısını al
    run_stats = db.query(
        func.count(TestRun.id).label("total"),
        func.sum(
            case((TestRun.status == TestStatus.COMPLETED, 1), else_=0)
        ).label("completed")
    ).one()

    total_runs = run_stats.total or 0
    completed_runs = run_stats.completed or 0
    success_rate = round((completed_runs / total_runs) * 100, 1) if total_runs > 0 else 0.0

    # 5. Platform Bazlı Dağılım (Ultimate Platform için kritik)
    platform_stats_raw = db.query(
        TestRun.platform,
        func.count(TestRun.id).label("total"),
        func.sum(
            case((TestRun.status == TestStatus.COMPLETED, 1), else_=0)
        ).label("completed")
    ).group_by(TestRun.platform).all()

    platform_breakdown = []
    for row in platform_stats_raw:
        p_total = row.total or 0
        p_completed = row.completed or 0
        p_success = round((p_completed / p_total) * 100, 1) if p_total > 0 else 0.0
        platform_breakdown.append({
            "platform": row.platform.value if row.platform else "unknown",
            "total_runs": p_total,
            "success_rate": p_success
        })

    # 6. Son Test Run'lar (Son 10 tanesi) - JOIN ile tek sorguda
    recent_test_runs = (
        db.query(TestRun, TestCase.title.label("case_title"))
        .outerjoin(TestCase, TestRun.test_case_id == TestCase.id)
        .order_by(TestRun.created_at.desc())
        .limit(10)
        .all()
    )

    recent_runs_data = []
    for run, case_title in recent_test_runs:
        duration = "N/A"
        if run.started_at and run.completed_at:
            delta = run.completed_at - run.started_at
            duration = f"{delta.total_seconds():.1f}s"

        recent_runs_data.append({
            "id": run.id,
            "case_title": case_title or "Exploratory Test",
            "platform": run.platform.value if run.platform else "unknown",
            "module": run.module_name,
            "status": run.status.value if run.status else "unknown",
            "duration": duration,
            "created_at": run.created_at.isoformat() if run.created_at else None
        })

    # 7. Haftalık Trend (Son 7 gün, her gün kaç test koşuldu)
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
        "platform_breakdown": platform_breakdown,   # YENİ: Platform bazlı dağılım
        "recent_test_runs": recent_runs_data,
        "weekly_trend": weekly_trend
    }


@router.get("/alerts")
def get_alerts(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Akıllı alarm sistemi - Kritik durumları tespit eder:
    - Başarı oranı düşük (<70%)
    - Son 3 günde test sayısı azaldı
    - Yavaş testler var (>10s) - verimli sorgu ile
    - Sürekli fail olan testler (Flaky Test)
    """
    alerts = []

    # 1. Başarı Oranı Kontrolü - Tek sorguda
    run_stats = db.query(
        func.count(TestRun.id).label("total"),
        func.sum(
            case((TestRun.status == TestStatus.COMPLETED, 1), else_=0)
        ).label("completed")
    ).one()

    total_runs = run_stats.total or 0
    if total_runs > 0:
        completed_runs = run_stats.completed or 0
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

    # 3. Yavaş Testler (>10 saniye) - Verimli: Sadece tamamlanmış olanları say
    slow_count = db.query(func.count(TestRun.id)).filter(
        TestRun.started_at.isnot(None),
        TestRun.completed_at.isnot(None),
        (TestRun.completed_at - TestRun.started_at) > timedelta(seconds=10)
    ).scalar() or 0

    if slow_count > 0:
        alerts.append({
            "type": "info",
            "title": "Slow Tests Detected",
            "message": f"{slow_count} tests took longer than 10 seconds",
            "action": "Optimize slow test cases or increase timeout limits",
            "severity": "low"
        })

    # 4. Flaky Test Tespiti - Son 20 run'da aynı case 3+ kez fail olduysa
    recent_runs = db.query(TestRun).filter(
        TestRun.status == TestStatus.FAILED
    ).order_by(TestRun.created_at.desc()).limit(20).all()

    fail_counts: Dict[int, int] = {}
    for run in recent_runs:
        if run.test_case_id:
            fail_counts[run.test_case_id] = fail_counts.get(run.test_case_id, 0) + 1

    flaky_case_ids = [case_id for case_id, count in fail_counts.items() if count >= 3]
    if flaky_case_ids:
        test_case = db.query(TestCase).filter(TestCase.id == flaky_case_ids[0]).first()
        case_name = test_case.title if test_case else "Unknown"
        alerts.append({
            "type": "critical",
            "title": "Flaky Test Detected",
            "message": f"Test '{case_name}' failed {fail_counts[flaky_case_ids[0]]} times recently",
            "action": "Review test logic or fix underlying bug",
            "severity": "high"
        })

    return {
        "alerts": alerts,
        "total_alerts": len(alerts),
        "critical_count": len([a for a in alerts if a["severity"] == "high"]),
        "warning_count": len([a for a in alerts if a["severity"] == "medium"])
    }


@router.get("/platforms")
def get_platform_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Platform bazlı detaylı istatistikler döner.
    Ultimate Platform vizyonu için: Web, Android, Windows, API, DB
    """
    platform_data = db.query(
        TestRun.platform,
        func.count(TestRun.id).label("total"),
        func.sum(
            case((TestRun.status == TestStatus.COMPLETED, 1), else_=0)
        ).label("completed"),
        func.sum(
            case((TestRun.status == TestStatus.FAILED, 1), else_=0)
        ).label("failed")
    ).group_by(TestRun.platform).all()

    platforms = []
    for row in platform_data:
        p_total = row.total or 0
        p_completed = row.completed or 0
        p_failed = row.failed or 0
        p_success = round((p_completed / p_total) * 100, 1) if p_total > 0 else 0.0

        platforms.append({
            "platform": row.platform.value if row.platform else "unknown",
            "total_runs": p_total,
            "completed": p_completed,
            "failed": p_failed,
            "success_rate": p_success
        })

    return {
        "platforms": platforms,
        "total_platforms_active": len(platforms)
    }
