from typing import Any, Dict, List


def classify_failed_step(step: Dict[str, Any], run_target: str = "", case_title: str = "") -> Dict[str, Any]:
    action = str(step.get("action") or "").lower()
    target = str(step.get("target") or step.get("selector_used") or "").strip()
    reason = str(step.get("reason") or step.get("error") or "").strip()
    combined = f"{action} {target} {reason}".lower()

    category = "real_bug_possible"
    title = "Test failure needs review"
    severity = "medium"
    probable_cause = "The run failed, but the failure pattern is not specific enough for automatic classification."
    recommendation = "Review the failed step, screenshot evidence, and the generated protocol before changing product code."

    if "target page, context or browser has been closed" in combined or "browser has been closed" in combined:
        category = "browser_context_closed"
        title = "Browser context closed during execution"
        severity = "high"
        probable_cause = "The browser or page context closed before the step could interact with the target."
        recommendation = "Check navigation flow, page redirects, popups, and whether the previous step caused the page to close or reload."
    elif "timeout" in combined or "timed out" in combined:
        category = "timing_issue"
        title = "Element did not become ready in time"
        severity = "medium"
        probable_cause = "The page may still be loading, rendering dynamically, or waiting behind an overlay when the step runs."
        recommendation = "Add a more specific wait condition, verify the page load state, or make the selector wait for the exact visible element."
    elif (
        "locator" in combined
        or "selector" in combined
        or "strict mode violation" in combined
        or "not found" in combined
        or (action in {"click", "type", "verify"} and target.startswith(("#", ".", "[", "button", "input", "a:")))
    ):
        category = "selector_issue"
        title = "Selector could not find the expected element"
        severity = "high"
        probable_cause = "The generated selector does not match the current DOM, or the expected element is absent on this URL."
        recommendation = f"Check target `{target or run_target}`. Regenerate the case from the current URL inventory or replace it with a stable id, data-test, role, text, or DOM-derived selector."
    elif action == "verify":
        category = "assertion_mismatch"
        title = "Expected page state was not observed"
        severity = "medium"
        probable_cause = "The page loaded, but the expected text, element, or state was not visible."
        recommendation = "Confirm whether the expected state belongs to this URL. If it does, add a precise wait or update the verification target."
    elif action in {"type", "click"} and not target:
        category = "test_case_generation_issue"
        title = "Generated step has no usable target"
        severity = "high"
        probable_cause = "The test protocol generated an interaction step without a reliable target selector."
        recommendation = "Regenerate protocols after visual analysis or keep this case as review-only until a DOM target is detected."

    return {
        "title": title,
        "category": category,
        "severity": severity,
        "affected_case": case_title,
        "run_target": run_target,
        "failed_step_order": step.get("order"),
        "failed_action": action or "step",
        "target": target or run_target,
        "selector_used": step.get("selector_used", ""),
        "probable_cause": probable_cause,
        "recommendation": recommendation,
        "evidence": {
            "reason": reason or "No failure reason was captured.",
            "duration_ms": step.get("duration_ms", 0),
            "screenshot": step.get("screenshot", ""),
            "screenshot_error": step.get("screenshot_error", ""),
            "attempts": step.get("attempts", []),
        },
    }


def build_bug_analysis(
    execution_report: Dict[str, Any],
    run_target: str = "",
    case_title: str = "",
) -> List[Dict[str, Any]]:
    return [
        classify_failed_step(step, run_target=run_target, case_title=case_title)
        for step in execution_report.get("steps", [])
        if step.get("status") == "failed"
    ]
