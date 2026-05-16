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


def test_case_generator_specializes_saucedemo_steps_by_case_intent():
    """Generated steps should differ by test case intent, not use one generic template."""
    from core.agents.case_generator import AICaseGenerator

    generator = AICaseGenerator.__new__(AICaseGenerator)
    raw_cases = {
        "happy_path": [
            {
                "title": "Successful login",
                "steps": [
                    {"action": "type", "target": "input[type='text']", "value": ""},
                    {"action": "click", "target": "button[type='submit']", "value": ""},
                    {"action": "verify", "target": "body", "value": ""},
                ],
            }
        ],
        "negative_path": [
            {
                "title": "Test invalid form submission",
                "steps": [
                    {"action": "click", "target": "button[type='submit']", "value": ""},
                    {"action": "verify", "target": ".error", "value": ""},
                ],
            }
        ],
        "security_checks": [
            {
                "title": "Basic XSS injection test",
                "steps": [
                    {"action": "type", "target": "input[type='text']", "value": "<script>alert('xss')</script>"},
                    {"action": "click", "target": "button[type='submit']", "value": ""},
                    {"action": "verify", "target": "body", "value": ""},
                ],
            }
        ],
    }

    cases = generator._format_cases(raw_cases, "https://www.saucedemo.com/")
    by_title = {case["title"]: case for case in cases}

    happy_steps = by_title["Successful login"]["steps"]
    invalid_steps = by_title["Test invalid form submission"]["steps"]
    xss_steps = by_title["Basic XSS injection test"]["steps"]

    assert [step["action"] for step in happy_steps[:2]] == ["navigate", "wait"]
    assert any(step["target"] == "#user-name" and step["value"] == "standard_user" for step in happy_steps)
    assert any(step["target"] == "#password" and step["value"] == "secret_sauce" for step in happy_steps)
    assert any(step["target"] == "#login-button" for step in happy_steps)
    assert any(".inventory_list" in step["target"] for step in happy_steps)

    assert any(step["target"] == "#login-button" for step in invalid_steps)
    assert any("[data-test='error']" in step["target"] for step in invalid_steps)
    assert not any(step["action"] == "type" for step in invalid_steps)

    assert any(step["target"] == "#user-name" and "<script>" in step["value"] for step in xss_steps)
    assert any(step["target"] == "#password" for step in xss_steps)
    assert xss_steps != invalid_steps


def test_saucedemo_fallback_returns_two_cases_per_category():
    """Fallback should stay small for token limits but balanced by category."""
    from core.models.llm_client import LLMClient

    client = LLMClient.__new__(LLMClient)
    raw_cases = client._get_fallback_cases("https://www.saucedemo.com/", "web")

    for category in ["happy_path", "negative_path", "edge_cases", "security_checks"]:
        assert len(raw_cases[category]) == 2

    assert raw_cases["total_rules_covered"] == 8


def test_generic_fallback_returns_two_cases_per_category():
    """The two-per-category fallback rule applies to every URL."""
    from core.models.llm_client import LLMClient

    client = LLMClient.__new__(LLMClient)
    raw_cases = client._get_fallback_cases("https://example.com/login", "web")

    for category in ["happy_path", "negative_path", "edge_cases", "security_checks"]:
        assert len(raw_cases[category]) == 2

    assert raw_cases["total_rules_covered"] == 8


def test_case_generator_caps_llm_output_to_two_cases_per_category():
    """If the LLM returns too many cases, persist at most two per category."""
    from core.agents.case_generator import AICaseGenerator

    generator = AICaseGenerator.__new__(AICaseGenerator)
    raw_cases = {
        "happy_path": [
            {"title": "Happy 1", "steps": [{"action": "verify", "target": "body"}]},
            {"title": "Happy 2", "steps": [{"action": "verify", "target": "body"}]},
            {"title": "Happy 3", "steps": [{"action": "verify", "target": "body"}]},
        ],
        "negative_path": [
            {"title": "Negative 1", "steps": [{"action": "verify", "target": "body"}]},
            {"title": "Negative 2", "steps": [{"action": "verify", "target": "body"}]},
            {"title": "Negative 3", "steps": [{"action": "verify", "target": "body"}]},
        ],
    }

    cases = generator._format_cases(raw_cases, "https://example.com/")
    categories = [case["category"] for case in cases]

    assert categories.count("happy_path") == 2
    assert categories.count("negative_path") == 2
    assert "Happy 3" not in {case["title"] for case in cases}
    assert "Negative 3" not in {case["title"] for case in cases}


def test_case_generator_keeps_distinct_saucedemo_fallback_steps():
    """Two cases in the same category should not collapse into the same action list."""
    from core.agents.case_generator import AICaseGenerator
    from core.models.llm_client import LLMClient

    generator = AICaseGenerator.__new__(AICaseGenerator)
    client = LLMClient.__new__(LLMClient)
    raw_cases = client._get_fallback_cases("https://www.saucedemo.com/", "web")

    cases = generator._format_cases(raw_cases, "https://www.saucedemo.com/")
    by_title = {case["title"]: case for case in cases}

    valid_login = by_title["Login with valid standard user"]["steps"]
    visible_form = by_title["Login form is visible on page load"]["steps"]
    invalid_password = by_title["Reject invalid password"]["steps"]
    sql_test = by_title["Basic SQL injection string test"]["steps"]

    assert any(step["value"] == "standard_user" for step in valid_login)
    assert any(step["target"] == "#login-button" and step["action"] == "verify" for step in visible_form)
    assert any(step["value"] == "wrong_password" for step in invalid_password)
    assert any(step["value"] == "' OR 1=1 --" for step in sql_test)
    assert valid_login != visible_form


def test_case_generator_removes_type_steps_when_no_input_detected():
    """Generated protocols must not type into controls that were not visually detected."""
    from core.agents.case_generator import AICaseGenerator

    generator = AICaseGenerator.__new__(AICaseGenerator)
    generator.last_analysis_metadata = {
        "detected_elements": [
            {"label": "link", "score": 0.91, "box": [10, 10, 80, 30]},
            {"label": "text", "score": 0.88, "box": [10, 40, 250, 80]},
        ]
    }
    raw_cases = {
        "happy_path": [
            {
                "title": "Search visible content",
                "steps": [
                    {"action": "navigate", "target": "https://the-internet.herokuapp.com/"},
                    {"action": "type", "target": "input[placeholder='Search...']", "value": "login"},
                    {"action": "click", "target": "button[type='submit']"},
                ],
            }
        ]
    }

    cases = generator._format_cases(raw_cases, "https://the-internet.herokuapp.com/")
    steps = cases[0]["steps"]

    assert not any(step["action"] == "type" for step in steps)


def test_visual_fallback_uses_page_inventory_without_fake_login_or_inputs():
    """Inventory fallback should create balanced cases without inventing login fields."""
    from core.agents.case_generator import AICaseGenerator

    generator = AICaseGenerator.__new__(AICaseGenerator)
    generator.last_analysis_metadata = {
        "detected_elements": [
            {"label": "link", "score": 0.91, "box": [10, 10, 80, 30]},
            {"label": "button", "score": 0.88, "box": [10, 40, 140, 80]},
        ],
        "dom_interactive_elements": [
            {"kind": "link", "selector": "a:has-text(\"Elements\")", "text": "Elements"},
            {"kind": "button", "selector": "button:has-text(\"Start\")", "text": "Start"},
        ],
    }

    cases = generator._build_visual_fallback_cases("https://demoqa.com/")
    categories = [case["category"] for case in cases]
    all_steps = [step for case in cases for step in case["steps"]]
    all_text = " ".join(
        f"{case['title']} " + " ".join(str(step.get("target", "")) for step in case["steps"])
        for case in cases
    ).lower()

    assert len(cases) == 8
    assert categories.count("happy_path") == 2
    assert categories.count("negative_path") == 2
    assert categories.count("edge_case") == 2
    assert categories.count("security") == 2
    assert not any(step["action"] == "type" for step in all_steps)
    assert "login" not in all_text
    assert "password" not in all_text
    assert any(case["title"] == "Review visible error surface" for case in cases)
    assert any(case["title"] == "Review visible navigation surface" for case in cases)


def test_format_cases_fills_missing_categories_from_inventory_fallback():
    """If LLM only returns compatible happy cases, missing categories are inventory-filled."""
    from core.agents.case_generator import AICaseGenerator

    generator = AICaseGenerator.__new__(AICaseGenerator)
    generator.last_analysis_metadata = {
        "detected_elements": [{"label": "link", "score": 0.91, "box": [10, 10, 80, 30]}],
        "dom_interactive_elements": [{"kind": "link", "selector": "a:has-text(\"Elements\")", "text": "Elements"}],
    }
    raw_cases = {
        "happy_path": [
            {"title": "Home page loads", "steps": [{"action": "verify", "target": "body"}]},
        ],
        "negative_path": [
            {
                "title": "Successful Login with Valid Credentials",
                "steps": [
                    {"action": "type", "target": "#user-name", "value": "standard_user"},
                    {"action": "type", "target": "#password", "value": "secret_sauce"},
                    {"action": "click", "target": "#login-button"},
                ],
            }
        ],
        "security_checks": [
            {
                "title": "Security test: Cross-site scripting (XSS) attack",
                "steps": [
                    {"action": "type", "target": "input[type='text']", "value": "<script>alert(1)</script>"},
                    {"action": "verify", "target": "body"},
                ],
            },
            {
                "title": "Security test: SQL injection attack",
                "steps": [
                    {"action": "type", "target": "input[type='text']", "value": "' OR 1=1 --"},
                    {"action": "verify", "target": "body"},
                ],
            },
        ],
    }

    cases = generator._format_cases(raw_cases, "https://demoqa.com/")
    categories = [case["category"] for case in cases]
    all_steps = [step for case in cases for step in case["steps"]]
    all_titles = " ".join(case["title"].lower() for case in cases)

    assert categories.count("happy_path") == 2
    assert categories.count("negative_path") == 2
    assert categories.count("edge_case") == 2
    assert categories.count("security") == 2
    assert "successful login" not in all_titles
    assert "xss" not in all_titles
    assert "sql injection" not in all_titles
    assert "review visible error surface" in all_titles
    assert not any(step["action"] == "type" for step in all_steps)
    assert not any("submit" in step["target"].lower() for step in all_steps if step["action"] == "click")
    assert any(step["action"] == "verify" and "body" in step["target"] for step in all_steps)


def test_case_generator_rejects_login_cases_for_non_login_page_without_inputs():
    """A homepage with no login controls must not keep generated login protocols."""
    from core.agents.case_generator import AICaseGenerator

    generator = AICaseGenerator.__new__(AICaseGenerator)
    generator.last_analysis_metadata = {
        "detected_elements": [
            {"label": "link", "score": 0.91, "box": [10, 10, 80, 30]},
            {"label": "text", "score": 0.88, "box": [10, 40, 250, 80]},
        ]
    }
    raw_cases = {
        "happy_path": [
            {
                "title": "Successful Login with Valid Credentials",
                "description": "User is redirected to the dashboard",
                "steps": [
                    {"action": "navigate", "target": "https://demoqa.com/"},
                    {"action": "type", "target": "#user-name", "value": "standard_user"},
                    {"action": "type", "target": "#password", "value": "secret_sauce"},
                    {"action": "click", "target": "#login-button"},
                ],
            }
        ]
    }

    cases = generator._format_cases(raw_cases, "https://demoqa.com/")

    assert cases
    assert not any("login" in case["title"].lower() for case in cases)
    assert not any("#user-name" in step["target"] for case in cases for step in case["steps"])
    assert not any("#login-button" in step["target"] for case in cases for step in case["steps"])


def test_generic_login_rewrite_does_not_use_saucedemo_selectors():
    """Only SauceDemo should use SauceDemo-specific selectors."""
    from core.agents.case_generator import AICaseGenerator

    generator = AICaseGenerator.__new__(AICaseGenerator)
    generator.last_analysis_metadata = {
        "detected_elements": [
            {"label": "input field", "score": 0.91, "box": [10, 10, 180, 40]},
            {"label": "button", "score": 0.88, "box": [10, 50, 120, 85]},
        ]
    }
    raw_cases = {
        "happy_path": [
            {
                "title": "Successful login",
                "steps": [
                    {"action": "type", "target": "#user-name", "value": ""},
                    {"action": "type", "target": "#password", "value": ""},
                    {"action": "click", "target": "#login-button"},
                ],
            }
        ]
    }

    cases = generator._format_cases(raw_cases, "https://example.com/login")
    targets = [step["target"] for step in cases[0]["steps"]]

    assert "#user-name" not in targets
    assert "#password" not in targets
    assert "#login-button" not in targets
    assert any("input[type='password']" in target for target in targets)


def test_world_view_includes_real_dom_interactive_elements():
    """Prompt context should expose real selectors from the exact URL."""
    from core.agents.case_generator import AICaseGenerator

    generator = AICaseGenerator.__new__(AICaseGenerator)
    generator.last_analysis_metadata = {
        "dom_interactive_elements": [
            {
                "kind": "link",
                "selector": "a:has-text(\"Elements\")",
                "text": "Elements",
                "href": "/elements",
            },
            {
                "kind": "button",
                "selector": "button:has-text(\"Start\")",
                "text": "Start",
            },
        ]
    }

    context = generator._build_world_view(
        "https://demoqa.com/",
        [{"label": "link", "score": 0.91, "box": [1, 2, 3, 4]}],
        vision_provider="SAM3",
    )

    assert "REAL DOM INTERACTIVE ELEMENTS" in context
    assert 'selector="a:has-text("Elements")"' in context
    assert "href='/elements'" in context


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
