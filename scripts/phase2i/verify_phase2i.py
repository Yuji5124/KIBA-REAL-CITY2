from pathlib import Path
import hashlib, json, math, struct

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'build-phase2i/data/processed'
GAP = json.loads((DATA/'phase2i/bridge_gap_connection.json').read_text(encoding='utf-8'))
NAV = DATA/'phase2c/phase2c_navigation.json'
H_REPORT = json.loads((ROOT/'reports/phase2h/phase2h_validation.json').read_text(encoding='utf-8'))
H_NAV = ROOT/'build-phase2h/data/processed/phase2c/phase2c_navigation.json'
assert GAP['cause']['classification'] == 'park_boundary_clipping'
assert GAP['cause']['rawOSMWayContinuous'] is True
assert GAP['cause']['terrainInterpolationCausedHorizontalGap'] is False
assert abs(GAP['gap']['horizontalMetres']-16.609) < .001
assert abs(GAP['gap']['threeDimensionalEndpointDistanceMetres']-16.616) < .001
assert GAP['phase2FVisualGap']['collisionEnabled'] is False
assert GAP['connectionCandidate']['enabledByDefault'] is False
assert GAP['connectionCandidate']['requiresPhase2HTrialMode'] is True
assert GAP['connectionCandidate']['widthIsEstimated'] and GAP['connectionCandidate']['heightIsEstimated']
assert GAP['productionNavigationModified'] is False and GAP['autoConnectionInNormalMode'] is False
pts = GAP['connectionCandidate']['centerline']
assert len(pts) == 181
assert all(math.isfinite(p[k]) for p in pts for k in ('x','y','z'))
steps = [math.dist([a[k] for k in ('x','y','z')],[b[k] for k in ('x','y','z')]) for a,b in zip(pts,pts[1:])]
assert max(steps) < .15
assert abs(pts[0]['x']-GAP['gap']['gapAEnd']['x']) < 1e-9
assert abs(pts[-1]['x']-GAP['gap']['gapBStart']['x']) < 1e-9
assert abs(GAP['connectionCandidate']['centerlineLengthMetres']-16.991) < .001
max_grade = abs(GAP['gap']['heightDeltaMetres'])/GAP['gap']['horizontalMetres']*1.5*100
assert abs(max_grade-4.299) < .01
assert GAP['connectionCandidate']['doesNotConnectToUnmodeledExtent'] is True
nav_sha = hashlib.sha256(NAV.read_bytes()).hexdigest()
assert nav_sha == hashlib.sha256(H_NAV.read_bytes()).hexdigest() == H_REPORT['phase2cNavSha256']
assert H_REPORT['phase2cBridgeRuns'] == {'review':8,'blocked':5,'walkable':0}
assert H_REPORT['phase2cBridgeSegments'] == {'review':760,'blocked':146,'total':906}
shots = {}
for name in ('top','bridge','side','robot'):
    p = ROOT/f'screenshots/phase2i/phase2i_{name}.png'
    b = p.read_bytes()
    assert b[:8] == b'\x89PNG\r\n\x1a\n'
    w,h = struct.unpack('>II',b[16:24])
    assert (w,h) == (1280,720)
    shots[name] = {'path':str(p),'width':w,'height':h,'bytes':len(b),'capturedInBrowser':True}

report = {
 'phase':'2I','result':'PASS_WITH_ESTIMATED_DEV_CANDIDATE','generatedDataChecks':'PASS',
 'gapCause':'park_boundary_clipping; raw OSM way 33976871 is continuous (3 nodes, 174.289m); Phase 2A splits at park polygon and Phase 2C retains two runs without auto-join. DEM/height interpolation changes Y only, not horizontal endpoints.',
 'measurements':{k:GAP['gap'][k] for k in ('horizontalMetres','threeDimensionalEndpointDistanceMetres','heightDeltaMetres','straightGradePercent','bearingDegreesFromPositiveX','runATerminalTangentDegrees','runBInitialTangentDegrees','tangentTurnDegrees','runATerminalGradePercent','runBInitialGradePercent')},
 'visualPhase2F':GAP['phase2FVisualGap'],
 'candidate':{**{k:v for k,v in GAP['connectionCandidate'].items() if k not in ('centerline','compositeTrialPath','mesh','unmodeledProbe')},'maxGradePercent':max_grade},
 'safety':{'candidateDefault':'OFF','OFF':'browser BLOCK at 16.609m gap','ON_A_to_B':'PASS, 200 steps','ON_B_to_A':'PASS, 200 steps','maxGradePercent':4.299,'lateralDeparture':'BLOCK','pastCandidateEndpoint':'BLOCK','unmodeledDirection':'BLOCK','unmodeledOverallLengthMetres':100.555,'productionNavigationModified':False,'phase2cNavigationSha256':nav_sha,'bridgeRunStatesUnchanged':H_REPORT['phase2cBridgeRuns'],'bridgeSegmentStatesUnchanged':H_REPORT['phase2cBridgeSegments']},
 'browser':{'actualBrowser':'http://127.0.0.1:8782/web/phase2i/','normalMode':'bridge remains blocked; candidate hidden unless DEV/Phase2H trial gates are enabled','fourViews':['top','bridge','side','robot'],'screenshots':shots},
 'performance':{'phase2H_baseline':H_REPORT['performance']['phase2hExperimental'],'phase2I_candidateOn':{'top':[60.0,63,629450,59],'bridgeGround':[60.1,51,554412,59],'side':[55.6,53,554784,59],'robot':[54.2,49,630604,59]},'metricsOrder':['FPS','drawCalls','triangles','meshes'],'deltaVsPhase2H_bridgeGround':[0.0,1,360,1],'note':'Live browser HUD samples; FPS fluctuates with view, vegetation LOD, browser scheduling and device. Named views were recorded directly in the browser; values are observed, not a controlled benchmark.'},
 'limitations':['Connection width (4m) and all endpoint elevations are estimates; no survey control, bridge design drawing, or structural support evidence validates walkability.','Curve matches end tangents with 3m Bezier handles; it differs from Phase 2F straight visual centerline by up to 1.756m.','100.555m unmodeled extent remains unconnected; the browser guard extrapolation is a safety probe, not the actual alignment.','Successful browser traverse is only a bounded DEV simulation and does not change production navigation or establish a physically safe bridge.']
}
(ROOT/'reports/phase2i/phase2i_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('Phase 2I validation PASS; nav SHA-256',nav_sha,'screenshots',len(shots),'max path step',round(max(steps),4),'m')
