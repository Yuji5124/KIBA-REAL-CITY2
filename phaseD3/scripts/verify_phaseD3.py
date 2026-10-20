from __future__ import annotations
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build-phaseD3"
REPORTS = ROOT / "reports/phaseD3"


def check(name, ok, detail):
    print(f"{'PASS' if ok else 'FAIL'} | {name} | {detail}")
    return bool(ok)


def main():
    app = BUILD / "web/phaseD3/app.js"
    html = BUILD / "web/phaseD3/index.html"
    data = BUILD / "data/processed/phaseD2/drive_courses.json"
    audit = REPORTS / "b_course_segments.json"
    d2 = json.loads(data.read_text(encoding="utf-8"))
    report = json.loads(audit.read_text(encoding="utf-8"))
    b = d2["courses"]["B"]
    q = report["openedBInterval"]
    checks = []
    checks.append(check("D3 files", app.is_file() and html.is_file() and data.is_file(), "separate built web app and course data"))
    checks.append(check("70% vehicle preserved", d2["vehicleScale"] == 0.7 and b["busDimensionsMetres"]["length"] == 3.164 and b["busDimensionsMetres"]["widthIncludingMirrors"] == 1.904, "length 3.164m, width 1.904m"))
    checks.append(check("B route provenance", b["wayId"] == "742189607" and q["stationStartMetres"] == 40 and q["stationEndMetres"] == 60, "20m OSM interval only"))
    checks.append(check("B geometry static gate", q["status"] == "PASS" and q["sweptEnvelope"]["status"] == "PASS" and q["minPolylineRadiusMetres"] >= q["vehicleMinTurnRadiusMetres"] and q["maxGradeFraction"] <= 0.12, f"sweep={q['sweptEnvelope']['status']}; radius {q['minPolylineRadiusMetres']}m; grade {q['maxGradeFraction']:.2%}"))
    checks.append(check("B manual browser release gate", b["status"] == "playable_verified_manual_browser", f"course data status={b['status']}"))
    checks.append(check("B one-way GOAL behavior", b.get("oneWayGoal") is True and b.get("goalStationMetres", b["lengthMetres"]) < b["lengthMetres"], "forward-only completion preserves a full-body endpoint margin"))
    checks.append(check("749128168 remains blocked", report["candidateWays"]["749128168"]["playable"] is False, "review sections and 17.05% grade"))
    checks.append(check("Phase 2C bridges remain blocked", d2.get("bridgeRunsPlayable") in (None, False), "no bridge navigation added"))
    browser_file = REPORTS / "browser_test.json"
    if browser_file.exists():
        browser = json.loads(browser_file.read_text(encoding="utf-8"))
        manual = browser.get("manualBrowser", {})
        checks.append(check("Browser A/B drive", manual.get("aCourse") == "PASS" and manual.get("bCourse") == "PASS", f"A={manual.get('aCourse')}; B={manual.get('bCourse')}"))
        build_audit = json.loads((REPORTS / "build_audit.json").read_text(encoding="utf-8"))
        checks.append(check("Browser report matches app build", browser.get("phaseD3AppSha256") == build_audit.get("phaseD3AppSha256"), build_audit.get("phaseD3AppSha256", "missing app hash")))
    else:
        checks.append(check("Browser A/B drive", False, "pending live browser test"))
    result = {"phase": "KIBA PARK DRIVE Phase D3", "result": "PASS" if all(checks) else "INCOMPLETE", "checks": [bool(c) for c in checks], "browserReportPresent": browser_file.exists()}
    (REPORTS / "phaseD3_validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    raise SystemExit(0 if all(checks) else 1)


if __name__ == "__main__":
    main()
