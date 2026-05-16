import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from routers.execution_router import _compile_step_dsl, _is_optional_banner_click


def test_cookie_banner_click_is_optional_and_fast():
    step = _compile_step_dsl({
        "order": 3,
        "action": "click",
        "target": "button:has-text('Accept Cookies')",
        "value": "",
    })

    assert _is_optional_banner_click(step["action"], step["target_hint"]) is True
    assert step["policy"]["required"] is False
    assert step["policy"]["retry"] == 0
    assert step["policy"]["timeout_ms"] <= 2500
    assert step["policy"]["fallback_allowed"] is False


def test_non_banner_click_stays_required():
    step = _compile_step_dsl({
        "order": 6,
        "action": "click",
        "target": "#login-button",
        "value": "",
    })

    assert _is_optional_banner_click(step["action"], step["target_hint"]) is False
    assert step["policy"]["required"] is True
