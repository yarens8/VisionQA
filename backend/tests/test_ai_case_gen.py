"""
VisionQA Backend - Temel API Testleri
CI/CD ortamında veritabanı gerektirmeden çalışır.
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


def test_app_imports():
    """main.py ve temel modüller import edilebiliyor mu?"""
    import main
    assert main.app is not None, "FastAPI app oluşturulamadı"
    print("✅ main.py import OK")


def test_models_import():
    """Veritabanı modelleri import edilebiliyor mu?"""
    from database.models import Project, TestCase, TestRun, Finding, TestStep
    assert Project is not None
    assert TestCase is not None
    assert TestRun is not None
    print("✅ Tüm modeller import OK")


def test_stats_router_import():
    """stats_router doğru import ediliyor mu?"""
    from routers.stats_router import router
    assert router is not None
    print("✅ stats_router import OK")


def test_platform_enum():
    """Platform enum değerleri doğru mu?"""
    from database.models import PlatformType
    assert PlatformType.WEB == "web"
    assert PlatformType.MOBILE_ANDROID == "mobile_android"
    assert PlatformType.DESKTOP_WINDOWS == "desktop_windows"
    assert PlatformType.API == "api"
    print("✅ PlatformType enum değerleri doğru")


def test_test_status_enum():
    """TestStatus enum değerleri doğru mu?"""
    from database.models import TestStatus
    assert TestStatus.PENDING == "pending"
    assert TestStatus.RUNNING == "running"
    assert TestStatus.COMPLETED == "completed"
    assert TestStatus.FAILED == "failed"
    print("✅ TestStatus enum değerleri doğru")


def test_health_endpoint():
    """Health endpoint çalışıyor mu? (DB mock ile)"""
    with patch('database.get_db') as mock_db:
        mock_session = MagicMock()
        mock_db.return_value = iter([mock_session])

        import main
        client = TestClient(main.app)
        response = client.get("/health")
        # 200 veya 503 olabilir (DB bağlantısı yok ama endpoint var)
        assert response.status_code in [200, 503], f"Beklenmeyen status: {response.status_code}"
        print(f"✅ /health endpoint yanıt verdi: {response.status_code}")


if __name__ == '__main__':
    test_app_imports()
    test_models_import()
    test_stats_router_import()
    test_platform_enum()
    test_test_status_enum()
    print("\n🎉 Tüm testler başarılı!")
