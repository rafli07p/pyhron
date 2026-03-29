#!/usr/bin/env python3
"""
Pyhron Demo Test Runner — Feature Evaluation Report

Runs the full demo test suite against the FastAPI application and generates
an HTML report summarising pass/fail status for every feature area.

Usage:
    # Against in-process TestClient (no running server needed):
    python scripts/run_demo_tests.py

    # Against a live server:
    DEMO_BASE_URL=http://localhost:8000 python scripts/run_demo_tests.py

    # Open the report after running:
    open demo_test_report.html       # macOS
    xdg-open demo_test_report.html   # Linux
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPORT_PATH = Path("demo_test_report.html")
TESTS_PATH = "tests/e2e/test_demo_web_features.py"


def run_tests() -> dict:
    """Execute pytest and capture JSON results."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            TESTS_PATH,
            "-v",
            "--tb=short",
            "--no-header",
            "-p",
            "no:cacheprovider",
            # Override addopts to skip coverage for demo run
            "-o",
            "addopts=",
            "--json-report",
            "--json-report-file=-",
        ],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parent.parent),
    )

    # Try to parse JSON report from stdout
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        pass

    # Fallback: parse verbose pytest output
    return _parse_verbose_output(result.stdout, result.stderr, result.returncode)


def _parse_verbose_output(stdout: str, stderr: str, returncode: int) -> dict:
    """Parse verbose pytest output into a structured report."""
    tests = []
    for line in (stdout + stderr).splitlines():
        line = line.strip()
        if "PASSED" in line or "FAILED" in line or "ERROR" in line or "SKIPPED" in line:
            if "::" in line:
                parts = line.split("::")
                nodeid = "::".join(p.strip() for p in parts if p.strip())
                if "PASSED" in line:
                    outcome = "passed"
                elif "FAILED" in line:
                    outcome = "failed"
                elif "SKIPPED" in line:
                    outcome = "skipped"
                else:
                    outcome = "error"
                # Clean up nodeid
                for tag in (" PASSED", " FAILED", " ERROR", " SKIPPED"):
                    nodeid = nodeid.replace(tag, "")
                tests.append({"nodeid": nodeid.strip(), "outcome": outcome})

    summary = {
        "passed": sum(1 for t in tests if t["outcome"] == "passed"),
        "failed": sum(1 for t in tests if t["outcome"] == "failed"),
        "error": sum(1 for t in tests if t["outcome"] == "error"),
        "skipped": sum(1 for t in tests if t["outcome"] == "skipped"),
        "total": len(tests),
    }
    return {
        "created": datetime.now(tz=UTC).isoformat(),
        "exitcode": returncode,
        "summary": summary,
        "tests": tests,
    }


# Feature area mapping: test class prefix → human-readable label
FEATURE_AREAS = {
    "TestHealthInfrastructure": "Health & Infrastructure",
    "TestAuthentication": "Authentication & Authorization",
    "TestCSRFProtection": "CSRF Protection",
    "TestSecurityHeaders": "Security Headers",
    "TestMarketOverview": "IDX Market Overview",
    "TestEquityScreener": "Equity Screener",
    "TestStockDetail": "Stock Detail",
    "TestMacroDashboard": "Macro Dashboard",
    "TestCommodityPrices": "Commodity Prices",
    "TestCommodityStockImpact": "Commodity-Stock Impact",
    "TestFixedIncome": "Fixed Income",
    "TestNewsSentiment": "News Sentiment",
    "TestGovernanceIntelligence": "Governance Intelligence",
    "TestStrategyManagement": "Strategy Management",
    "TestBacktestExecution": "Backtest Execution",
    "TestLiveTrading": "Live Trading",
    "TestLiveTradingRisk": "Live Trading Risk",
    "TestPaperTrading": "Paper Trading",
    "TestGatewayMarketData": "Gateway: Market Data",
    "TestGatewayOrders": "Gateway: Orders",
    "TestGatewayPortfolio": "Gateway: Portfolio",
    "TestGatewayRisk": "Gateway: Risk Check",
    "TestGatewayBacktest": "Gateway: Backtest",
    "TestGatewayAdmin": "Gateway: Admin",
    "TestCrossCuttingConcerns": "Cross-Cutting Concerns",
}


def _classify_test(nodeid: str) -> str:
    """Map a test node ID to its feature area."""
    for class_name, label in FEATURE_AREAS.items():
        if class_name in nodeid:
            return label
    return "Other"


def _status_icon(outcome: str) -> str:
    if outcome == "passed":
        return '<span style="color:#22c55e;font-weight:bold">PASS</span>'
    if outcome == "failed":
        return '<span style="color:#ef4444;font-weight:bold">FAIL</span>'
    if outcome == "skipped":
        return '<span style="color:#eab308;font-weight:bold">SKIP</span>'
    return '<span style="color:#f97316;font-weight:bold">ERROR</span>'


def _area_badge(passed: int, total: int) -> str:
    if passed == total:
        return '<span style="background:#22c55e;color:#fff;padding:2px 8px;border-radius:4px;font-size:0.85em">ALL PASS</span>'
    if passed == 0:
        return '<span style="background:#ef4444;color:#fff;padding:2px 8px;border-radius:4px;font-size:0.85em">ALL FAIL</span>'
    return f'<span style="background:#eab308;color:#fff;padding:2px 8px;border-radius:4px;font-size:0.85em">{passed}/{total}</span>'


def generate_html(report: dict) -> str:
    """Build an HTML report from pytest results."""
    tests = report.get("tests", [])
    summary = report.get("summary", {})
    created = report.get("created", datetime.now(tz=UTC).isoformat())

    total = summary.get("total", len(tests))
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    skipped = summary.get("skipped", 0)
    errors = summary.get("error", 0)
    pass_rate = f"{(passed / total * 100):.1f}" if total else "0.0"

    # Group tests by feature area
    areas: dict[str, list[dict]] = {}
    for t in tests:
        area = _classify_test(t["nodeid"])
        areas.setdefault(area, []).append(t)

    # Build area summary rows
    area_rows = ""
    for area_name in FEATURE_AREAS.values():
        area_tests = areas.get(area_name, [])
        if not area_tests:
            continue
        a_passed = sum(1 for t in area_tests if t["outcome"] == "passed")
        a_total = len(area_tests)
        area_rows += f"""
        <tr>
            <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb">{area_name}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;text-align:center">{a_total}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;text-align:center">{a_passed}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;text-align:center">{a_total - a_passed}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;text-align:center">{_area_badge(a_passed, a_total)}</td>
        </tr>"""

    # Build individual test rows
    test_rows = ""
    for t in tests:
        name = t["nodeid"].split("::")[-1] if "::" in t["nodeid"] else t["nodeid"]
        area = _classify_test(t["nodeid"])
        test_rows += f"""
        <tr>
            <td style="padding:6px 12px;border-bottom:1px solid #f3f4f6;font-size:0.9em">{area}</td>
            <td style="padding:6px 12px;border-bottom:1px solid #f3f4f6;font-family:monospace;font-size:0.85em">{name}</td>
            <td style="padding:6px 12px;border-bottom:1px solid #f3f4f6;text-align:center">{_status_icon(t['outcome'])}</td>
        </tr>"""

    # Handle "Other" area
    for area_name, area_tests in areas.items():
        if area_name not in FEATURE_AREAS.values() and area_tests:
            a_passed = sum(1 for t in area_tests if t["outcome"] == "passed")
            a_total = len(area_tests)
            area_rows += f"""
            <tr>
                <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb">{area_name}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;text-align:center">{a_total}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;text-align:center">{a_passed}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;text-align:center">{a_total - a_passed}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;text-align:center">{_area_badge(a_passed, a_total)}</td>
            </tr>"""

    overall_color = "#22c55e" if failed == 0 and errors == 0 else "#ef4444"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pyhron Demo Test Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f9fafb; color: #1f2937; padding: 24px; }}
        .container {{ max-width: 1100px; margin: 0 auto; }}
        h1 {{ font-size: 1.8em; margin-bottom: 4px; }}
        .subtitle {{ color: #6b7280; margin-bottom: 24px; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px; margin-bottom: 32px; }}
        .card {{ background: #fff; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center; }}
        .card .number {{ font-size: 2em; font-weight: 700; }}
        .card .label {{ color: #6b7280; font-size: 0.9em; margin-top: 4px; }}
        table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 32px; }}
        th {{ background: #f3f4f6; padding: 10px 12px; text-align: left; font-weight: 600; font-size: 0.9em; border-bottom: 2px solid #e5e7eb; }}
        .section-title {{ font-size: 1.3em; font-weight: 600; margin: 32px 0 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Pyhron Trading Platform — Demo Test Report</h1>
        <p class="subtitle">Generated: {created} | Evaluating all features and functional areas</p>

        <div class="summary-grid">
            <div class="card">
                <div class="number" style="color:{overall_color}">{total}</div>
                <div class="label">Total Tests</div>
            </div>
            <div class="card">
                <div class="number" style="color:#22c55e">{passed}</div>
                <div class="label">Passed</div>
            </div>
            <div class="card">
                <div class="number" style="color:#ef4444">{failed}</div>
                <div class="label">Failed</div>
            </div>
            <div class="card">
                <div class="number" style="color:#eab308">{skipped}</div>
                <div class="label">Skipped</div>
            </div>
            <div class="card">
                <div class="number" style="color:{overall_color}">{pass_rate}%</div>
                <div class="label">Pass Rate</div>
            </div>
        </div>

        <h2 class="section-title">Feature Area Summary</h2>
        <table>
            <thead>
                <tr>
                    <th>Feature Area</th>
                    <th style="text-align:center">Tests</th>
                    <th style="text-align:center">Passed</th>
                    <th style="text-align:center">Failed</th>
                    <th style="text-align:center">Status</th>
                </tr>
            </thead>
            <tbody>{area_rows}</tbody>
        </table>

        <h2 class="section-title">Individual Test Results</h2>
        <table>
            <thead>
                <tr>
                    <th>Feature Area</th>
                    <th>Test Name</th>
                    <th style="text-align:center">Result</th>
                </tr>
            </thead>
            <tbody>{test_rows}</tbody>
        </table>

        <p style="color:#9ca3af;font-size:0.85em;margin-top:16px;text-align:center">
            Pyhron Quantitative Trading Platform &mdash; Feature Evaluation Suite
        </p>
    </div>
</body>
</html>"""


def main() -> None:
    print("=" * 60)
    print("  Pyhron Demo Test Runner — Feature Evaluation")
    print("=" * 60)
    print()

    print("Running demo test suite ...")
    report = run_tests()

    summary = report.get("summary", {})
    total = summary.get("total", 0)
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)

    print(f"\nResults: {passed}/{total} passed, {failed} failed")
    print()

    html = generate_html(report)
    REPORT_PATH.write_text(html, encoding="utf-8")
    print(f"HTML report written to: {REPORT_PATH.resolve()}")

    # Print console summary
    tests = report.get("tests", [])
    areas: dict[str, list[dict]] = {}
    for t in tests:
        area = _classify_test(t["nodeid"])
        areas.setdefault(area, []).append(t)

    print()
    print(f"{'Feature Area':<35} {'Pass':>5} {'Total':>6}  Status")
    print("-" * 60)
    for area_name in FEATURE_AREAS.values():
        area_tests = areas.get(area_name, [])
        if not area_tests:
            continue
        a_passed = sum(1 for t in area_tests if t["outcome"] == "passed")
        a_total = len(area_tests)
        status = "OK" if a_passed == a_total else "ISSUES"
        print(f"{area_name:<35} {a_passed:>5} {a_total:>6}  {status}")

    print()
    if failed == 0:
        print("All feature areas evaluated successfully!")
    else:
        print(f"{failed} test(s) need attention. See HTML report for details.")

    sys.exit(report.get("exitcode", 1 if failed else 0))


if __name__ == "__main__":
    main()
