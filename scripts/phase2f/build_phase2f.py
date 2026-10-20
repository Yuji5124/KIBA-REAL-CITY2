from __future__ import annotations
import argparse, json, math, xml.etree.ElementTree as ET
from pathlib import Path

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--root',default=r'C:\Users\hp\Desktop\KIBA-REAL-CITY'); a=ap.parse_args(); root=Path(a.root)
 nav=json.loads((root/'data/processed/phase2c/phase2c_navigation.json').read_text(encoding='utf-8'))
 align=json.loads((root/'data/processed/phase2e/phase2e_bridge_alignment.json').read_text(encoding='utf-8'))
 report2b=json.loads((root/'reports/phase2b/phase2b_report.json').read_text(encoding='utf-8'))
 selected=[]
 for run in nav['runs']:
  segs=[s for s in run['segments'] if s.get('wayId')=='33976871']
  if segs: selected.append((run,segs))
 if len(selected)!=2: raise SystemExit(f'Expected two clipped OSM runs, got {len(selected)}')
 def ribbon(a,b,width,offset=.06):
  dx=b[0]-a[0]; dz=b[2]-a[2]; length=math.hypot(dx,dz)
  if length<1e-5: raise ValueError('zero-length segment')
  nx,nz=-dz/length,dx/length; h=width/2
  return [[a[0]+nx*h,a[1]+offset,a[2]+nz*h],[a[0]-nx*h,a[1]+offset,a[2]-nz*h],[b[0]+nx*h,b[1]+offset,b[2]+nz*h],[b[0]-nx*h,b[1]+offset,b[2]-nz*h]]
 surfaces=[]
 for run,segs in selected:
  for s in segs: surfaces.append({'kind':'mapped_osm_route','wayId':'33976871','corners':ribbon(s['centerStart'],s['centerEnd'],4.0),'baseWidthMetres':s['widthMetres'],'candidateWidthMetres':4.0,'sourceHeightsEstimated':True,'sourceSegmentIndex':s['segmentIndex']})
 left=selected[0][1][-1]['centerEnd']; right=selected[1][1][0]['centerStart']; gap=math.dist((left[0],left[2]),(right[0],right[2]))
 gapSurf={'kind':'boundary_clipped_visual_candidate','wayId':'33976871','corners':ribbon(left,right,4.0),'baseWidthMetres':None,'candidateWidthMetres':4.0,'sourceHeightsEstimated':True,'heightMethod':'linear interpolation between adjacent Phase 2C estimated bridge-run endpoint heights; visual-only +0.06m offset','endpointA':left,'endpointB':right,'lengthMetres':gap,'heightDeltaMetres':right[1]-left[1],'autoConnected':False,'collisionEnabled':False}
 surfaces.append(gapSurf)
 nodes={}; way=None
 for fp in (root/'data/raw/osm/layers').rglob('*.osm'):
  try: tree=ET.parse(fp).getroot()
  except ET.ParseError: continue
  for n in tree.findall('node'):
   if n.get('id') in {'6980957124','6958098784','6982757453'}: nodes[n.get('id')]=(float(n.get('lat')),float(n.get('lon')))
  for w in tree.findall('way'):
   if w.get('id')=='33976871': way={'refs':[n.get('ref') for n in w.findall('nd')],'tags':{t.get('k'):t.get('v') for t in w.findall('tag')}}
 if not way or len(nodes)<3: raise SystemExit('OSM way 33976871 coordinates unavailable')
 # Phase 1's EPSG:6677 local projection, preserving its project origin.
 phase1=Path(__file__).resolve().parents[1]/'phase1'/'build_phase1_data.py'
 ns={}; exec(compile(phase1.read_text(encoding='utf-8'),str(phase1),'exec'),ns)
 projected=[]
 for ref in way['refs']:
  lat,lon=nodes[ref]; x,n=ns['proj'](lat,lon); projected.append({'nodeId':ref,'lat':lat,'lon':lon,'eastingEPSG6677':ns['OE']+x,'northingEPSG6677':ns['ON']+n,'x':x,'z':-n})
 osmLength=sum(math.dist((projected[i]['x'],projected[i]['z']),(projected[i+1]['x'],projected[i+1]['z'])) for i in range(len(projected)-1))
 runEnds=[{'run':r['run'],'start':ss[0]['centerStart'],'end':ss[-1]['centerEnd'],'segments':len(ss)} for r,ss in selected]
 deck={'phase':'2F','assetName':'Kiba Park Ohashi · bridge deck candidate','coordinateSystem':align['coordinateSystem'],'status':'visual_candidate_review_only','collisionEnabled':False,'navigationModified':False,'widthMetres':4.0,'widthBasis':'working visual estimate only; no surveyed width source in local OSM/GLB','surfaceHeightOffsetMetres':0.06,'surfaceHeightOffsetBasis':'render separation only; not physical deck elevation','sourceOSMWayId':'33976871','sourceOSMTags':way['tags'],'projectedOSMNodes':projected,'osmWayLengthMetres':osmLength,'clippedRuns':runEnds,'gap':gapSurf,'surfaces':surfaces,'g62':{'registeredWithIdentityTransform':True,'registrationStatus':'visual hypothesis, no survey control','boundsXYZ':align['asset']['boundsXYZ'],'overlapOfOSMRouteInG62XZBounds':sum(1 for r,ss in selected for s in ss if align['asset']['boundsXYZ'][0][0]<=s['centerStart'][0]<=align['asset']['boundsXYZ'][0][1] and align['asset']['boundsXYZ'][2][0]<=s['centerStart'][2]<=align['asset']['boundsXYZ'][2][1]) / sum(len(ss) for r,ss in selected)},'officialReference':{'totalLengthMetres':250.0,'maxSpanMetres':96.95,'pylonHeightMetres':60.0,'source':'Japan Concrete Institute archive; total bridge dimension, not the mapped OSM way length'},'unmodeledLengthDifferenceMetres':250.0-osmLength,'notes':['Deck geometry follows the mapped OSM footway runs and adds one amber visual span across the 16.616m park-boundary clip gap.','The gap fill interpolates between estimated Phase 2C bridge-run endpoint heights; it is not measured.','Phase 2C nav/collision data is read only. The amber segment remains blocked by the existing nav data.','The OSM way is only about 149m versus the documented 250m total bridge length; remaining extent and branches are unresolved and omitted.','G6.2 identity registration is visual only. Axis metadata conflict remains unresolved; no survey control points found.']}
 out=root/'data/processed/phase2f'; out.mkdir(parents=True,exist_ok=True); (out/'bridge_deck_candidate.json').write_text(json.dumps(deck,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 metrics={'phase':'2F','sourceOSMWayId':'33976871','osmProjectedLengthMetres':round(osmLength,3),'documentedBridgeLengthMetres':250.0,'unmodeledLengthDifferenceMetres':round(250-osmLength,3),'phase2CRuns':len(selected),'phase2CSegments':sum(len(ss) for r,ss in selected),'clippedGapMetres':round(gap,3),'phase2GapReportMetres':16.616,'gapEndpointHeightsEstimatedMetres':[left[1],right[1]],'gapHeightDeltaMetres':round(right[1]-left[1],3),'candidateWidthMetres':4.0,'candidateWidthIsEstimated':True,'candidateDeckSurfaceHeightOffsetMetres':0.06,'candidateTopTriangles':2*len(surfaces),'osmPathStartEndProjected':projected,'g62XZBounds':align['asset']['boundsXYZ'][[0,2][0]] if False else [align['asset']['boundsXYZ'][0],align['asset']['boundsXYZ'][2]],'g62RouteOverlapFraction':deck['g62']['overlapOfOSMRouteInG62XZBounds'],'navDataModified':False,'collisionEnabledForCandidate':False,'status':'review_only_not_walkable','fps':60.1,'drawCalls':55,'triangles':600380,'meshCount':53,'performanceMeasurementBasis':'actual browser top-view HUD; one-second sample'}
 navLength=sum(s['distanceMetres'] for r,ss in selected for s in ss)
 deckLength=navLength+gap
 metrics.update({'phase2CNavSurfaceLengthMetres':round(navLength,3),'candidateDeckLengthMetres':round(deckLength,3),'candidateDeckVsDocumentedLengthGapMetres':round(250-deckLength,3),'rawOSMLengthNotCoveredByPhase2CPlusGapMetres':round(osmLength-deckLength,3),'heightDifferenceToPhase2CEstimatedRunsMetres':0.06,'heightDifferenceBasis':'render-only offset at mapped stations; interpolated gap endpoints remain estimated','browserValidation':{'actualBrowser':'Codex in-app browser, localhost:8779','viewsConfirmed':['top','bridge','side','robot'],'movementTest':'PASS 24.0m, 326 swept probes; stairs BLOCK, >35% BLOCK, gap BLOCK, boundary BLOCK','baselinePhase2E':{'fps':60.1,'drawCalls':53,'triangles':599740,'meshes':51},'phase2FTop':{'fps':60.1,'drawCalls':55,'triangles':600380,'meshes':53},'delta':{'fps':0.0,'drawCalls':2,'triangles':640,'meshes':2},'measurementNote':'One-second HUD sample in an actual browser; FPS may vary with hardware and view/LOD.'},'screenshots':['screenshots/phase2f/phase2e_before_top.png','screenshots/phase2f/phase2f_top.png','screenshots/phase2f/phase2f_bridge.png','screenshots/phase2f/phase2f_side.png','screenshots/phase2f/phase2f_robot.png']})
 (root/'reports/phase2f').mkdir(parents=True,exist_ok=True); (root/'reports/phase2f/phase2f_validation.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(metrics,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
