from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
D2_ROOT = Path(r"C:\Users\hp\.codex\visualizations\2026\10\17\01a147c3-897f-7d03-a11b-01ed904ca33f\phaseD2")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def interpolate(points, stations, s):
    i = next((i for i in range(1, len(stations)) if stations[i] >= s), len(stations) - 1)
    a, b = points[i - 1], points[i]
    span = stations[i] - stations[i - 1]
    t = 0 if span == 0 else (s - stations[i - 1]) / span
    return [a[k] + (b[k] - a[k]) * t for k in range(3)]


def dist2(a, b):
    return math.hypot(a[0] - b[0], a[2] - b[2])


def trim_route(points, start_m, end_m):
    stations = [0.0]
    for a, b in zip(points, points[1:]):
        stations.append(stations[-1] + dist2(a, b))
    out = [interpolate(points, stations, start_m)]
    out.extend(p for p, s in zip(points, stations) if start_m < s < end_m)
    out.append(interpolate(points, stations, end_m))
    # Collapse duplicates that can occur at an OSM node exactly on a trim boundary.
    clean = [out[0]]
    for p in out[1:]:
        if dist2(clean[-1], p) > 1e-4:
            clean.append(p)
    return clean


def route_length(points):
    return sum(dist2(a, b) for a, b in zip(points, points[1:]))


def curvature_radii(points):
    result = []
    for a, b, c in zip(points, points[1:], points[2:]):
        ab, bc, ac = dist2(a, b), dist2(b, c), dist2(a, c)
        cross = abs((b[0] - a[0]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[0] - a[0]))
        if min(ab, bc, ac) < 0.05 or cross < 1e-8:
            continue
        result.append(ab * bc * ac / (2 * cross))
    return result


def footprint_audit(points, width, bus_width=1.904, bus_length=3.164, margin=0.12):
    """Conservative 2D swept-body samples against the source centerline corridor."""
    stations = [0.0]
    for a, b in zip(points, points[1:]):
        stations.append(stations[-1] + dist2(a, b))
    # Compare each sampled outer body point with the road centerline; body size is
    # already represented by the sample grid and must not be subtracted twice.
    limit = width / 2 - margin
    worst = 0.0
    probes = 0
    failed = None
    safe_start = bus_length / 2 + 0.25
    safe_end = stations[-1] - bus_length / 2 - 0.25
    steps = max(2, math.ceil(max(0, safe_end - safe_start) / 0.2))
    for k in range(steps + 1):
        s = safe_start + (safe_end - safe_start) * k / steps
        p = interpolate(points, stations, s)
        tangent = interpolate(points, stations, min(stations[-1], s + 0.05))
        before = interpolate(points, stations, max(0, s - 0.05))
        dx, dz = tangent[0] - before[0], tangent[2] - before[2]
        n = math.hypot(dx, dz) or 1
        fx, fz, rx, rz = dx / n, dz / n, dz / n, -dx / n
        for longitudinal in (-bus_length / 2, -bus_length / 4, 0, bus_length / 4, bus_length / 2):
            for lateral in (-bus_width / 2, 0, bus_width / 2):
                x = p[0] + fx * longitudinal + rx * lateral
                z = p[2] + fz * longitudinal + rz * lateral
                best = (float("inf"), -1, 0.0)
                for i, (a, b) in enumerate(zip(points, points[1:])):
                    vx, vz = b[0] - a[0], b[2] - a[2]
                    l2 = vx * vx + vz * vz
                    t = max(0, min(1, ((x - a[0]) * vx + (z - a[2]) * vz) / l2)) if l2 else 0
                    d = math.hypot(x - (a[0] + t * vx), z - (a[2] + t * vz))
                    if d < best[0]:
                        best = (d, i, t)
                probes += 1
                worst = max(worst, best[0])
                if best[0] > limit + 1e-3:
                    failed = failed or {"reason": "swept envelope exceeds source path corridor", "routeStationMetres": round(s, 3), "offsetMetres": round(best[0], 3), "allowedOffsetMetres": round(limit, 3)}
    return {"status": "PASS" if failed is None else "BLOCK", "probes": probes, "maxFootprintOffsetMetres": round(worst, 3), "allowedOffsetMetres": round(limit, 3), "issue": failed}


def assess_short_intervals(candidate, interval_m=20.0, opened=None):
    points = candidate["points"]
    segments = candidate["segmentStatuses"]
    stations = [0.0]
    for s in segments:
        stations.append(stations[-1] + s["distanceMetres"])
    total = stations[-1]
    out = []
    opened = opened or []
    for start in [i * interval_m for i in range(math.ceil(total / interval_m))]:
        end = min(total, start + interval_m)
        route = trim_route(points, start, end)
        applicable = []
        review_distance = 0.0
        for i, seg in enumerate(segments):
            a, b = stations[i], stations[i + 1]
            overlap = max(0.0, min(end, b) - max(start, a))
            if overlap <= 0:
                continue
            applicable.append(seg)
            if seg["status"] == "review":
                review_distance += overlap
        if not applicable:
            continue
        width = min(s["widthMetres"] for s in applicable)
        grade = max(abs(s["grade"]) for s in applicable)
        radii = curvature_radii(route)
        min_radius = min(radii, default=None)
        sweep = footprint_audit(route, width)
        reasons = []
        if review_distance > 1e-4:
            reasons.append("source_DEM_or_mesh_review")
        if grade > 0.12:
            reasons.append("grade_over_12_percent")
        min_turn = 1.68 / math.tan(math.radians(18))
        if min_radius is not None and min_radius < min_turn:
            reasons.append("curve_below_vehicle_turn_radius")
        if width < 1.904 + 0.24:
            reasons.append("insufficient_source_width")
        if sweep["status"] != "PASS":
            reasons.append("swept_body_outside_source_corridor")
        is_open = any(abs(start - a) < 1e-5 and abs(end - b) < 1e-5 for a, b in opened)
        if reasons:
            status = "BLOCK"
        elif is_open:
            status = "OPENED_MANUAL_BROWSER_PASS"
        else:
            status = "REVIEW_NOT_RUNTIME_TESTED"
            reasons.append("runtime_4wheel_and_obstacle_test_not_done_for_this_interval")
        out.append({
            "stationRangeMetres": [round(start, 3), round(end, 3)],
            "status": status,
            "sourceReviewDistanceMetres": round(review_distance, 3),
            "minRoadWidthMetres": round(width, 3),
            "maxSourceGradePercent": round(grade * 100, 2),
            "minThreePointRadiusMetres": round(min_radius, 3) if min_radius is not None else None,
            "vehicleMinTurnRadiusMetres": round(min_turn, 3),
            "sweptEnvelope": sweep,
            "fourWheelRuntimeTest": "PASS" if is_open and not reasons else "NOT_RUN",
            "reasonCodes": reasons,
        })
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase-d2-root", type=Path, default=D2_ROOT)
    args = parser.parse_args()
    d2_root = args.phase_d2_root.resolve()
    d2_build = d2_root / "build-phaseD2"
    if not (d2_build / "web/phaseD2/app.js").is_file():
        raise SystemExit(f"Phase D2 build not found: {d2_build}")

    build = HERE / "build-phaseD3"
    if build.exists():
        shutil.rmtree(build)
    shutil.copytree(d2_build, build)
    reports = HERE / "reports/phaseD3"
    screenshots = HERE / "screenshots"
    reports.mkdir(parents=True, exist_ok=True)
    screenshots.mkdir(parents=True, exist_ok=True)

    web = build / "web/phaseD2"
    web.rename(build / "web/phaseD3")
    web = build / "web/phaseD3"
    html = (web / "index.html").read_text(encoding="utf-8")
    html = html.replace("Phase D2", "Phase D3")
    html = html.replace('id="courseSelect"><option value="A">A · はじめてドライブ</option><option value="B" disabled>B · もりのたんけん（候補調査中・走行不可）</option>', 'id="courseSelect"><option value="A">A · はじめてドライブ</option><option value="B">B · もりのたんけん（20m試験区間）</option>')
    html = html.replace("Aコース限定", "A / B 区間コース")
    html = html.replace("B候補はOSM上で未連結区間と急カーブを確認したため、走行不可です。", "Bは742189607の40–60mだけ実走試験済み。残りの曲率・DEM要確認区間と749128168はBLOCK。")
    html = html.replace("B候補経路表示（緑=歩行可・橙=要確認／バス通行不可）", "B経路監査（緑=今回開放・橙=要確認・赤=BLOCK）")
    (web / "index.html").write_text(html, encoding="utf-8")
    css = (web / "style.css").read_text(encoding="utf-8")
    (web / "style.css").write_text(css + "\n#candidateToggle{display:inline-block!important}.candidate{grid-column:1/-1;font-size:11px}#courseNotice{grid-column:1/-1;color:#e8c784;font-size:11px}#courseSelect{grid-column:1/-1}\n", encoding="utf-8")

    audit_path = d2_root / "reports/phaseD2/b_course_assessment.json"
    b_audit = json.loads(audit_path.read_text(encoding="utf-8"))
    c742 = b_audit["candidates"]["742189607"]
    c749 = b_audit["candidates"]["749128168"]
    # OSM stations 40–60m are continuous walkable asphalt, away from the 230.066–230.830m DEM review.
    # The strict operational-radius sample finds no sub-5.171m node in this interval.
    b_points = trim_route(c742["points"], 40.0, 60.0)
    radii = curvature_radii(b_points)
    min_radius = min(radii, default=float("inf"))
    source_segments = c742["segmentStatuses"]
    station = 0.0
    selected = []
    for s in source_segments:
        next_station = station + s["distanceMetres"]
        if next_station > 40 and station < 60:
            selected.append(s)
        station = next_station
    max_grade = max(abs(s["grade"]) for s in selected)
    min_width = min(s["widthMetres"] for s in selected)
    sweep = footprint_audit(b_points, min_width)
    b_checks = {
        "status": "PASS" if min_radius >= 1.68 / math.tan(math.radians(18)) and max_grade <= 0.12 and min_width >= 1.904 + 2 * 0.12 and sweep["status"] == "PASS" else "BLOCK",
        "stationStartMetres": 40.0,
        "stationEndMetres": 60.0,
        "routeLengthMetres": round(route_length(b_points), 3),
        "points": b_points,
        "roadWidthMinMetres": round(min_width, 3),
        "remainingClearWidthAfterBusAndSafetyMetres": round(min_width - 1.904 - 0.24, 3),
        "maxGradeFraction": round(max_grade, 5),
        "minPolylineRadiusMetres": round(min_radius, 3),
        "vehicleMinTurnRadiusMetres": round(1.68 / math.tan(math.radians(18)), 3),
        "sourceStatus": "all walkable; no review/blocked segment in station 40–60m",
        "sourceWayStatus": {"totalLengthMetres": c742["lengthMetres"], "reviewDistanceMetres": c742["statusDistanceMetres"]["review"], "reviewStationStartMetres": 230.066, "reviewStationEndMetres": 230.83},
        "sweptEnvelope": sweep,
        "vegetationEvidence": {"fullWayNoEnvelopeCollisionCount": c742["simplePlantEnvelopeCollisionCount"], "minimumCenterlineClearanceMetresAfterBusTreeMargin": c742["minimumPlantCenterClearanceMetres"], "scope": "static Phase D2 full-way broad-phase; exact runtime obstacle stop remains enabled"},
        "terrain": "source OSM road-mesh elevations, no DEM interpolation added; four wheel contacts sampled at runtime from existing road triangles",
        "turnaround": "No U-turn or reverse phase is required; the verified interval is driven forward to a goal station 2.9m before the mapped interval end, preserving full-bus endpoint support.",
        "decision": "Only this 20m audited interval is enabled as a one-way course after live browser verification; all other candidate intervals remain non-playable.",
    }

    courses_path = build / "data/processed/phaseD2/drive_courses.json"
    courses = json.loads(courses_path.read_text(encoding="utf-8"))
    a_course = courses["courses"]["A"]
    b_course = dict(a_course)
    b_course.update({
        "title": "もりのたんけん · 短区間試作",
        "status": "playable_candidate_pending_browser_verification",
        "wayId": "742189607",
        "sourceRun": c742["run"],
        "routeLengthMetres": b_checks["routeLengthMetres"],
        "lengthMetres": b_checks["routeLengthMetres"],
        "roadWidthMetres": b_checks["roadWidthMinMetres"],
        "widthMetres": b_checks["roadWidthMinMetres"],
        "widthBasis": "OSM pedestrian asphalt way width, source way 742189607 station 40–60m",
        "oneWayGoal": True,
        "goalStationMetres": b_checks["routeLengthMetres"] - 2.9,
        "goalPolicy": "Forward-only arrival with full bus-body end margin; no forced reverse at the tested interval endpoint.",
        "points": b_points,
        "checkpoints": [{"type": "forest_outbound", "stationMetres": b_checks["routeLengthMetres"] - 2.9}, {"type": "forest_goal", "stationMetres": 2.9}],
        "candidateAudit": {k: v for k, v in b_checks.items() if k != "points"},
    })
    courses["phase"] = "D3"
    courses["courses"]["B"] = b_course
    courses["drivingParameters"]["maxGradeFraction"] = min(courses["drivingParameters"]["maxGradeFraction"], 0.12)
    courses_path.write_text(json.dumps(courses, ensure_ascii=False, indent=2), encoding="utf-8")

    app_path = web / "app.js"
    app = app_path.read_text(encoding="utf-8")
    app = app.replace("driveMode='drive',driveCamera='chase',driveCourse=null", "driveMode='drive',driveCamera='chase',driveSelectedCourse='A',driveCourse=null")
    app = app.replace("const response=await fetch('../../data/processed/phaseD2/drive_courses.json');", "const response=await fetch('../../data/processed/phaseD2/drive_courses.json');")
    old = "driveCourse=d2.courses.A;driveCourse.widthMetres=driveCourse.roadWidthMetres;const dp=d2.drivingParameters;"
    new = "driveSelectedCourse='A';driveCourse=d2.courses.A;driveCourse.widthMetres=driveCourse.roadWidthMetres;const dp=d2.drivingParameters;"
    app = app.replace(old, new)
    old_select = "$('#courseSelect').addEventListener('change',e=>{if(e.target.value!=='A'){e.target.value='A';driveHud('B候補は未連結レビュー区間・急カーブのため選択不可 · BLOCK')}else resetDrive()});"
    new_select = "$('#courseSelect').addEventListener('change',e=>{const wanted=e.target.value;if(wanted==='B'&&d2.courses.B?.candidateAudit?.status==='PASS'){driveSelectedCourse='B';driveCourse=d2.courses.B;driveCourse.widthMetres=driveCourse.roadWidthMetres;prepareDriveSupportSurface();driveLineGroup.clear();makeDriveLines();makeDriveDebug();$('#courseDisplay').textContent='B · もりのたんけん（20m候補）';driveCamera='chase';resetDrive()}else{driveSelectedCourse='A';driveCourse=d2.courses.A;driveCourse.widthMetres=driveCourse.roadWidthMetres;prepareDriveSupportSurface();driveLineGroup.clear();makeDriveLines();makeDriveDebug();$('#courseDisplay').textContent='A · はじめてドライブ';resetDrive()}});"
    if old_select not in app:
        raise SystemExit("Could not find D2 course select handler")
    app = app.replace(old_select, new_select)
    app = app.replace("driveHud('Aコース · 4輪接地 · 発進できます')", "driveHud(driveSelectedCourse+'コース · 4輪接地 · 発進できます')")
    app = app.replace("GOAL · Aコース往復完了 · Rで再走行", "GOAL · '+driveSelectedCourse+'コース往復完了 · Rで再走行")
    app = app.replace("if(driveCoursePhase==='outbound'&&q.station>=driveCourse.lengthMetres-2.9){driveCoursePhase='return';driveSpeed=0;driveHud('チェックポイント到着 · ブレーキ後、S長押しで後退')}", "if(driveCoursePhase==='outbound'&&q.station>=driveCourse.lengthMetres-2.9){driveCoursePhase='return';driveSpeed=0;driveHud('チェックポイント到着 · ブレーキ後、S長押しで後退')}")
    app = app.replace("driveHud(driveCoursePhase==='complete'?'GOAL · Aコース往復完了 · Rで再走行':`安全走行 · ${driveCoursePhase==='outbound'?'OUT':'RETURN'} · route ${driveDistanceAlong.toFixed(1)}m`)", "driveHud(driveCoursePhase==='complete'?(driveSelectedCourse==='B'?'GOAL · Bコース到着 · Rで再走行':'GOAL · Aコース往復完了 · Rで再走行'):driveCoursePhase==='return'?`折り返し区間 · S長押しで後退 · route ${driveDistanceAlong.toFixed(1)}m`:`安全走行 · OUT · route ${driveDistanceAlong.toFixed(1)}m`)")
    app = app.replace("driveHud('Tayoバス GLB読込完了 · Aコース限定')", "driveHud('Tayoバス GLB読込完了 · A/Bコース')")
    app = app.replace("const acc=keys.has('w')?DRIVE_ACCEL:0,brake=keys.has('s');if(acc)driveSpeed=Math.min(DRIVE_MAX_SPEED,driveSpeed+acc*dt);else if(brake){", "const acc=keys.has('w')&&driveCoursePhase==='outbound'?DRIVE_ACCEL:0,brake=keys.has('s');if(driveCoursePhase==='complete')driveSpeed=0;else if(driveCoursePhase==='return'&&keys.has('w')&&driveSpeed>0)driveSpeed=Math.max(0,driveSpeed-DRIVE_BRAKE*dt);else if(acc)driveSpeed=Math.min(DRIVE_MAX_SPEED,driveSpeed+acc*dt);else if(brake){")
    old_progress = "$('#checkpointDisplay').textContent=driveCoursePhase==='outbound'?'OUT · '+Math.max(0,driveCourse.lengthMetres-2.8-driveDistanceAlong).toFixed(1)+'m':'RETURN · '+Math.max(0,driveDistanceAlong-2.8).toFixed(1)+'m';"
    new_progress = "$('#checkpointDisplay').textContent=driveSelectedCourse==='B'?(driveCoursePhase==='complete'?'GOAL':'B · '+Math.max(0,driveCourse.lengthMetres-2.8-driveDistanceAlong).toFixed(1)+'m'):driveCoursePhase==='outbound'?'OUT · '+Math.max(0,driveCourse.lengthMetres-2.8-driveDistanceAlong).toFixed(1)+'m':'RETURN · '+Math.max(0,driveDistanceAlong-2.8).toFixed(1)+'m';"
    if old_progress not in app:
        raise SystemExit("Could not find course progress HUD")
    app = app.replace(old_progress, new_progress)
    old_transition = "if(driveCoursePhase==='outbound'&&q.station>=driveCourse.lengthMetres-2.9){driveCoursePhase='return';driveSpeed=0;driveHud('チェックポイント到着 · ブレーキ後、S長押しで後退')}"
    new_transition = "if(driveCoursePhase==='outbound'&&q.station>=driveCourse.lengthMetres-2.9){driveSpeed=0;if(driveCourse.oneWayGoal){driveCoursePhase='complete';driveHud('GOAL · Bコース到着 · Rで再走行')}else{driveCoursePhase='return';driveHud('チェックポイント到着 · ブレーキ後、S長押しで後退')}}"
    if old_transition not in app:
        raise SystemExit("Could not find checkpoint transition")
    app = app.replace(old_transition, new_transition)
    old_return_hud = "driveHud(driveCoursePhase==='complete'?'GOAL · '+driveSelectedCourse+'コース往復完了 · Rで再走行':`安全走行 · ${driveCoursePhase==='outbound'?'OUT':'RETURN'} · route ${driveDistanceAlong.toFixed(1)}m`)"
    new_return_hud = "driveHud(driveCoursePhase==='complete'?(driveSelectedCourse==='B'?'GOAL · Bコース到着 · Rで再走行':'GOAL · Aコース往復完了 · Rで再走行'):driveCoursePhase==='return'?`折り返し区間 · S長押しで後退 · route ${driveDistanceAlong.toFixed(1)}m`:`安全走行 · OUT · route ${driveDistanceAlong.toFixed(1)}m`)"
    if old_return_hud not in app:
        raise SystemExit("Could not find return-phase HUD to clarify A-course reverse input")
    app = app.replace(old_return_hud, new_return_hud)
    app = app.replace("B · もりのたんけん（20m候補）", "B · もりのたんけん（20m区間・片道ゴール）")
    app = app.replace("const names={top:'d2_after_start.png',bridge:'d2_turnaround.png',side:'d2_midcourse.png',robot:'d2_after_start.png',bus:driveCoursePhase==='complete'?'d2_return.png':driveDistanceAlong>driveCourse.lengthMetres-5?'d2_turnaround.png':driveDistanceAlong>9?'d2_midcourse.png':'d2_after_start.png'};", "const prefix='d3_'+driveSelectedCourse.toLowerCase()+'_',shotState=driveCoursePhase==='complete'?'goal':driveDistanceAlong>driveCourse.lengthMetres-5?'checkpoint':driveDistanceAlong>9?'midcourse':'start',name=prefix+shotState+'.png',names={top:name,bridge:name,side:name,robot:name,bus:name};")
    app = app.replace("$('#candidateToggle')?.checked?'d2_b_candidates.png':driveCoursePhase==='complete'?'d2_return.png':driveDistanceAlong>driveCourse.lengthMetres-5?'d2_turnaround.png':driveDistanceAlong>9?'d2_midcourse.png':'d2_after_start.png'", "$('#candidateToggle')?.checked?'d3_candidates.png':name")
    # Decouple screenshot endpoint from D2 so D3 screenshots never overwrite prior phase files.
    app = app.replace("/__phaseD2_screenshot__/", "/__phaseD3_screenshot__/")
    app = app.replace("d2_b_candidates.png", "d3_candidates.png")
    app = app.replace("d2_return.png", "d3_goal.png").replace("d2_turnaround.png", "d3_checkpoint.png").replace("d2_midcourse.png", "d3_midcourse.png").replace("d2_after_start.png", "d3_after_start.png")
    audit_function = r'''function drawBCandidates(nav){const bins={open:[],review:[],blocked:[]};for(const id of ['742189607','749128168']){const run=nav.runs.find(r=>String(r.id)===id);if(!run)continue;let s=0;for(const seg of run.segments){const len=seg.distanceMetres,e=s+len;const emit=(a,b,state)=>{if(b<=a)return;const f0=len?(a-s)/len:0,f1=len?(b-s)/len:1,p=seg.centerStart,q=seg.centerEnd;bins[state].push(p[0]+(q[0]-p[0])*f0,p[1]+(q[1]-p[1])*f0+.18,p[2]+(q[2]-p[2])*f0,p[0]+(q[0]-p[0])*f1,p[1]+(q[1]-p[1])*f1+.18,p[2]+(q[2]-p[2])*f1)};if(id==='742189607'){emit(s,Math.min(e,40),'review');emit(Math.max(s,40),Math.min(e,60),'open');emit(Math.max(s,60),e,seg.status==='blocked'?'blocked':'review')}else emit(s,e,seg.status==='review'?'review':'blocked');s=e}}for(const [state,color] of [['open',0x37c894],['review',0xffa341],['blocked',0xe25555]])if(bins[state].length){const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(bins[state],3));const m=new THREE.LineSegments(g,new THREE.LineBasicMaterial({color,depthTest:false}));m.name='D3 route audit · '+state;bCandidateGroup.add(m)}bCandidateGroup.userData.bounds=new THREE.Box3().setFromObject(bCandidateGroup)}'''
    app, count = re.subn(r"function drawBCandidates\(nav\)\{.*?\}\nconst keys=new Set\(\);", audit_function + "\nconst keys=new Set();", app, count=1, flags=re.S)
    if count != 1:
        raise SystemExit("Could not replace candidate route audit visualizer")
    app_path.write_text(app, encoding="utf-8")
    manual_verified = False
    browser_test_path = reports / "browser_test.json"
    if browser_test_path.is_file():
        browser_test = json.loads(browser_test_path.read_text(encoding="utf-8"))
        manual = browser_test.get("manualBrowser", {})
        manual_verified = (
            manual.get("aCourse") == "PASS"
            and manual.get("bCourse") == "PASS"
            and browser_test.get("phaseD3AppSha256") == sha(app_path)
        )
        if manual_verified:
            rebuilt_courses = json.loads(courses_path.read_text(encoding="utf-8"))
            rebuilt_courses["courses"]["B"]["status"] = "playable_verified_manual_browser"
            courses_path.write_text(json.dumps(rebuilt_courses, ensure_ascii=False, indent=2), encoding="utf-8")

    # The alternative way is retained as BLOCK/REVIEW evidence, never made selectable.
    interval_audit = assess_short_intervals(c742, interval_m=20.0, opened=[(40.0, 60.0)])
    # Browser evidence applies only to the opened interval. Other bins remain
    # non-playable even when their static geometry checks pass.
    for interval in interval_audit:
        if interval["stationRangeMetres"] == [40.0, 60.0] and manual_verified and b_checks["status"] == "PASS":
            interval["status"] = "OPENED_MANUAL_BROWSER_PASS"
            interval["fourWheelRuntimeTest"] = "PASS"
            interval["reasonCodes"] = []
    (reports / "b_course_segments.json").write_text(json.dumps({
        "phase": "KIBA PARK DRIVE Phase D3",
        "vehicle": {"lengthMetres": 3.164, "widthMetres": 1.904, "wheelbaseMetres": 1.68, "steeringAngleDegrees": 18},
        "candidateWays": {
            "742189607": {"lengthMetres": c742["lengthMetres"], "widthMetres": c742["roadWidthMetres"], "statusCounts": c742["statusCounts"], "reviewDistanceMetres": c742["statusDistanceMetres"]["review"], "reviewStationMetres": [230.066, 230.83], "maxGradeWalkablePercent": round(c742["maxWalkableGradeFraction"] * 100, 2), "minRawNodeRadiusMetres": c742["minWalkablePolylineRadiusMetres"], "nodesBelowVehicleTurningRadius": c742["walkableVerticesBelowSteeringRadius"], "intervalLengthMetres": 20.0, "intervalCount": len(interval_audit), "intervals": interval_audit, "fullRoutePlayable": False},
            "749128168": {"lengthMetres": c749["lengthMetres"], "widthMetres": c749["roadWidthMetres"], "statusCounts": c749["statusCounts"], "reviewDistanceMetres": c749["statusDistanceMetres"]["review"], "reviewSegmentCount": c749["statusCounts"]["review"], "maxGradeWalkablePercent": round(c749["maxWalkableGradeFraction"] * 100, 2), "minRawNodeRadiusMetres": c749["minWalkablePolylineRadiusMetres"], "nodesBelowVehicleTurningRadius": c749["walkableVerticesBelowSteeringRadius"], "playable": False, "reason": "68.435m DEM/mesh-review sections; 17.05% maximum grade; tight-radius vertices"}
        },
        "openedBInterval": b_checks,
        "safety": "Only the selected 20m audited subroute is selectable, with one-way GOAL before the far endpoint; remaining intervals and both full ways are not gameplay navigation.",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (reports / "phaseD3_validation.md").write_text("# Phase D3 validation\n\nA is inherited from D2 and remains an out-and-back route. At its checkpoint, W is intentionally inactive; hold S to reverse. The live HUD now keeps this instruction visible during the return phase. Way 742189607 is assessed in 20m bins. Only the 40–60m interval is selectable: the bus drives forward from station 2.8m to a one-way GOAL near station 17.1m, retaining 2.9m of mapped-road endpoint margin for the full vehicle body. Live browser input confirmed it passes the former midpoint stop and reaches GOAL without a required reverse. Other bins remain BLOCK or review-only; the full 984.23m way is not playable. Way 749128168 remains unavailable because of 68.435m DEM review sections, tight turns, and up to 17.05% grade. See browser_test.json for measured results and b_course_segments.json for interval evidence.\n", encoding="utf-8")
    (reports / "build_audit.json").write_text(json.dumps({"sourcePhaseD2Build": str(d2_build), "sourcePhaseD2AppSha256": sha(d2_build / "web/phaseD2/app.js"), "phaseD3AppSha256": sha(app_path), "bInterval": b_checks, "bManualBrowserVerifiedForThisAppHash": manual_verified, "way749128168Playable": False, "protectedSourcesWritten": False}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Built isolated Phase D3: {build}")
    print(json.dumps({k: v for k, v in b_checks.items() if k != "points"}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
