from __future__ import annotations
import argparse, importlib.util, json, math, statistics
from collections import Counter
from pathlib import Path

def load_module(path):
 spec=importlib.util.spec_from_file_location('phase1_builder',path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
def project_root():
 for p in Path(__file__).resolve().parents:
  if (p/'data/processed/phase2c').is_dir():return p
 return Path(__file__).resolve().parents[1]
def inside(x,y,ring):
 c=False;j=len(ring)-1
 for i,(xx,yy) in enumerate(ring):
  xj,yj=ring[j]
  if (yy>y)!=(yj>y) and x<(xj-xx)*(y-yy)/(yj-yy+1e-30)+xx:c=not c
  j=i
 return c
def inside_any(x,y,rings):return any(inside(x,y,r) for r in rings)
def clamp(v,lo,hi):return max(lo,min(hi,v))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-root',default=r'C:\Users\hp\Desktop\KIBA-REAL-CITY');ap.add_argument('--output-root',default=str(project_root()));ap.add_argument('--max-adjustment',type=float,default=.12);a=ap.parse_args();src=Path(a.source_root);out=Path(a.output_root)
 scene=json.loads((src/'data/processed/phase2b/phase2b_scene.json').read_text(encoding='utf-8'));oldreport=json.loads((src/'reports/phase2b/phase2b_report.json').read_text(encoding='utf-8'));bld=load_module(src/'scripts/phase1/build_phase1_data.py');t=scene['terrain'];bounds=scene['bounds'];nx,nz=t['width'],t['height'];dx,dz=t['gridSpacingMetres'];verts=t['vertices'];sources=t['heightSource'];rings=[[[p[0],-p[2]] for p in r] for r in scene['parkBoundary']];water_rings=[[[p[0],-p[2]] for p in f['points']] for f in scene['features'].get('water',[]) if len(f.get('points',[]))>=3]
 # Load DEM1A PNGs read-only and sample the same 3x3 median used by Phase 2B.
 tiles={};dem_tiles=0
 for f in (src/'data/raw/gsi/dem1a_png').rglob('*.png'):
  z=int(f.parent.parent.name);x=int(f.parent.name);y=int(f.stem);w,h,rows=bld.rgbpng(f);tiles[(z,x,y)]=(w,h,rows);dem_tiles+=1
 def pxheight(row,x):
  j=x*3;v=row[j]*65536+row[j+1]*256+row[j+2]
  if v in (0xffffff,0x800000):return None
  if v>=0x800000:v-=0x1000000
  return v/100
 dem_cache={}
 def dem(x,z):
  key=(round(x,2),round(z,2))
  if key in dem_cache:return dem_cache[key]
  lat,lon=bld.unproj(x,-z);n=1<<17;u=(lon+180)/360*n;v=(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n;tx,ty=int(u),int(v);tile=tiles.get((17,tx,ty))
  if not tile:dem_cache[key]=(None,'dem17_tile_missing',0);return dem_cache[key]
  w,h,rows=tile;ix=min(w-1,int((u-tx)*w));iy=min(h-1,int((v-ty)*h));vals=[]
  for y0 in range(max(0,iy-1),min(h,iy+2)):
   for x0 in range(max(0,ix-1),min(w,ix+2)):
    q=pxheight(rows[y0],x0)
    if q is not None:vals.append(q)
  result=(statistics.median(vals),'dem17_median3x3',len(vals)) if len(vals)>=3 else (None,'dem17_nodata',len(vals));dem_cache[key]=result;return result
 def mesh_height(x,z):
  u=(x-bounds[0])/dx;v=(z-bounds[1])/dz;ix=max(0,min(nx-2,math.floor(u)));iz=max(0,min(nz-2,math.floor(v)));fu=clamp(u-ix,0,1);fv=clamp(v-iz,0,1);q=iz*nx+ix
  if fu+fv<=1:ids=(q,q+nx,q+1);weights=(1-fu-fv,fv,fu)
  else:ids=(q+1,q+nx,q+nx+1);weights=(1-fv,1-fu,fu+fv-1)
  if any(sources[i] in ('outside','unresolved') for i in ids):return None
  return sum(verts[i][1]*w for i,w in zip(ids,weights))
 def water_at(x,z):return inside_any(x,-z,water_rings)
 # Re-measure every Phase 2B centerline transition against both the rendered mesh and point-sampled raw DEM.
 grade_checks=[]
 for r in scene['roads']:
  ss=r['stations'];centers=[((s[0]+s[3])/2,(s[2]+s[5])/2) for s in ss];mesh=[((s[1]+s[4])/2 if r['bridge'] else mesh_height(x,z)) for s,(x,z) in zip(ss,centers)];raw=[None if r['bridge'] else dem(x,z)[0] for x,z in centers]
  for i in range(1,len(ss)):
   dist=math.dist(centers[i-1],centers[i]);dy=(mesh[i]-mesh[i-1]) if mesh[i] is not None and mesh[i-1] is not None else ((ss[i][1]+ss[i][4]-ss[i-1][1]-ss[i-1][4])/2);grade=abs(dy)/max(dist,.01)
   if grade<.2:continue
   rdy=raw[i]-raw[i-1] if raw[i] is not None and raw[i-1] is not None else None
   if r['group']=='steps' or r['highway']=='steps':cause='mapped_stairway'
   elif r['bridge']:cause='bridge_deck_inferred'
   elif rdy is not None and abs(rdy)<=.08 and abs(dy)>=.12:cause='likely_raster_or_mesh_sampling_artifact'
   elif rdy is not None and abs(rdy)>=.15 and rdy*dy>0 and abs(rdy)>=abs(dy)*.65:cause='supported_by_local_dem_change'
   else:cause='ambiguous_dem_vs_mesh'
   grade_checks.append({'wayId':r['id'],'run':r['run'],'group':r['group'],'highway':r['highway'],'bridge':r['bridge'],'fromXY':[round(centers[i-1][0],3),round(centers[i-1][1],3)],'toXY':[round(centers[i][0],3),round(centers[i][1],3)],'distanceMetres':round(dist,3),'meshDeltaMetres':round(dy,3),'meshGrade':round(grade,4),'rawDEMDeltaMetres':round(rdy,3) if rdy is not None else None,'cause':cause})
 # Create a separate nav/collision ribbon. Small raster sampling corrections are clamped per station and never touch the source render mesh.
 max_adjust=a.max_adjustment;nav_runs=[];grade_counts=Counter();run_counts=Counter();samples_adjusted=[];source_fallbacks=Counter();smooth_grade_stats=[];walk_segments=[];review_segments=[];blocked_segments=[];grid_spacing=5.0
 for rid,r in enumerate(scene['roads']):
  ss=r['stations'];n=len(ss);centers=[((s[0]+s[3])/2,(s[2]+s[5])/2) for s in ss];is_bridge=bool(r['bridge']);is_steps=(r['group']=='steps' or r['highway']=='steps');base=[];rawh=[];rawsrc=[];crossed=[]
  for i,(x,z) in enumerate(centers):
   h=mesh_height(x,z)
   if h is None:h=(ss[i][1]+ss[i][4])/2-.08
   base.append(h);q,source,_=dem(x,z);rawh.append(q);rawsrc.append(source)
   crossed.append(water_at(x,z))
  if is_bridge:
   profile=[(s[1]+s[4])/2 for s in ss];correction=[0.0]*n
  elif is_steps:
   profile=base[:];correction=[0.0]*n
  else:
   profile=[]
   for h,q in zip(base,rawh):
    if q is None:target=h;source_fallbacks['phase2b_mesh_fallback']+=1
    else:target=h+clamp(q-h,-max_adjust,max_adjust);samples_adjusted.append(abs(target-h))
    profile.append(target)
   unsmoothed=profile[:]
   if n>=3:
    profile=[profile[0]]+[clamp(.25*unsmoothed[i-1]+.5*unsmoothed[i]+.25*unsmoothed[i+1],base[i]-max_adjust,base[i]+max_adjust) for i in range(1,n-1)]+[profile[-1]]
   correction=[profile[i]-base[i] for i in range(n)]
  surface=[]
  for i,s in enumerate(ss):
   left=(s[0],s[2]);right=(s[3],s[5]);offset=(profile[i]-base[i]) if not is_bridge else profile[i]-(s[1]+s[4])/2
   ly=mesh_height(*left);ry=mesh_height(*right)
   if ly is None:ly=s[1]-.08
   if ry is None:ry=s[4]-.08
   # Bridge y already represents an estimated deck; other collision surfaces sit 8 cm above terrain to avoid Z-fighting.
   if is_bridge:ly=ry=profile[i]
   else:ly=ly+.08+offset;ry=ry+.08+offset
   surface.append([round(left[0],3),round(ly,3),round(left[1],3),round(right[0],3),round(ry,3),round(right[1],3)])
  statuses=[];seg_records=[]
  for i in range(n-1):
   s0,s1=surface[i],surface[i+1];c0,c1=centers[i],centers[i+1];dist=math.dist(c0,c1);dy=(profile[i+1]-profile[i]);grade=abs(dy)/max(dist,.01);width=(math.dist(s0[:3],s0[3:6])+math.dist(s1[:3],s1[3:6]))/2;reasons=[]
   points=((s0[0],s0[2]),(s0[3],s0[5]),(s1[0],s1[2]),(s1[3],s1[5]))
   if is_steps:status='blocked';reasons.append('stairs_are_not_auto-climbable_for_wheeled_proxy')
   elif is_bridge:status='review';reasons.append('estimated_bridge_deck_height')
   elif any(water_at(x,z) for x,z in points):status='blocked';reasons.append('water_intersection')
   elif any(not inside_any(x,-z,rings) for x,z in points):status='blocked';reasons.append('park_boundary_or_missing_triangle')
   elif width<.9:status='blocked';reasons.append('corridor_narrower_than_proxy_clearance')
   elif grade>.35:status='blocked';reasons.append('grade_over_35_percent')
   elif grade>.20:status='review';reasons.append('grade_over_20_percent')
   elif rawh[i] is None or rawh[i+1] is None:status='review';reasons.append('DEM_NoData_using_Phase2B_mesh')
   elif abs(correction[i])>.06 or abs(correction[i+1])>.06:status='review';reasons.append('bounded_DEM_mesh_reconciliation')
   else:status='walkable';reasons.append('within_proxy_grade_and_width_limits')
   grade_counts[status]+=1;run_counts[status]+=int(status!='walkable');smooth_grade_stats.append(grade);statuses.append(status)
   seg={'runIndex':rid,'wayId':r['id'],'sourceRun':r['run'],'segmentIndex':i,'status':status,'reason':reasons[0],'grade':round(grade,4),'distanceMetres':round(dist,3),'estimatedHeight':is_bridge,'corners':[s0[:3],s0[3:6],s1[:3],s1[3:6]],'centerStart':[round(c0[0],3),round(profile[i]+(.08 if not is_bridge else 0),3),round(c0[1],3)],'centerEnd':[round(c1[0],3),round(profile[i+1]+(.08 if not is_bridge else 0),3),round(c1[1],3)],'widthMetres':round(width,3)}
   seg_records.append(seg)
   (walk_segments if status=='walkable' else review_segments if status=='review' else blocked_segments).append(seg)
  nav_runs.append({'id':r['id'],'run':r['run'],'group':r['group'],'highway':r['highway'],'bridge':is_bridge,'stairs':is_steps,'heightBasis':'phase2b_endpoint_linear_inference' if is_bridge else 'phase2b_terrain_plus_bounded_dem1a_reconciliation','maxCorrectionMetres':round(max((abs(x) for x in correction),default=0),3),'stations':surface,'centerHeightsMetres':[round(y+(.08 if not is_bridge else 0),3) for y in profile],'statuses':statuses,'segments':seg_records})
 # Areas omitted by Phase 2B remain explicit blocked markers; they do not produce connecting polygons.
 gap_source=oldreport['roadTerrainGaps']['locations'];gap_areas=[]
 for g in gap_source:
  gx,gz=g['atXY'];gh=mesh_height(gx,gz)
  gap_areas.append({'wayId':g['wayId'],'centerXY':[gx,gz],'centerY':round((gh if gh is not None else .05)+.16,3),'radiusMetres':1.25,'status':'blocked','reason':g['reason'],'autoConnected':False})
 # Prepare a deterministic longest continuous walkable segment run for an in-browser collision test.
 test_route=None
 for run in nav_runs:
  best_start=best_end=cur_start=0;best_length=0.0;cur_length=0.0
  for i,status in enumerate(run['statuses']):
   seg=run['segments'][i]
   if status=='walkable':
    if cur_length==0:cur_start=i
    cur_length+=seg['distanceMetres']
    if cur_length>best_length:best_length=cur_length;best_start=cur_start;best_end=i+1
   else:cur_length=0
  if best_length>0 and (test_route is None or best_length>test_route['lengthMetres']):
   stations=run['stations'];ys=run['centerHeightsMetres'];points=[];test_length=min(best_length,24.0);acc=0.0
   s=stations[best_start];points.append([round((s[0]+s[3])/2,3),ys[best_start],round((s[2]+s[5])/2,3)])
   for k in range(best_start,best_end):
    seglen=run['segments'][k]['distanceMetres'];s=stations[k+1];point=[round((s[0]+s[3])/2,3),ys[k+1],round((s[2]+s[5])/2,3)]
    if acc+seglen<=test_length:points.append(point);acc+=seglen
    else:
     f=(test_length-acc)/max(seglen,.001);p=points[-1];points.append([round(p[0]+(point[0]-p[0])*f,3),round(p[1]+(point[1]-p[1])*f,3),round(p[2]+(point[2]-p[2])*f,3)]);acc=test_length;break
   test_route={'runIndex':nav_runs.index(run),'wayId':run['id'],'sourceRun':run['run'],'lengthMetres':round(acc,2),'points':points,'status':'walkable'}
 report={'sourcePhase2b':'data/processed/phase2b/phase2b_scene.json','sourceDEM':'data/raw/gsi/dem1a_png (read-only)','demTilesDecoded':dem_tiles,'renderTerrainModified':False,'rawDEMModified':False,'navigationLayer':'data/processed/phase2c/phase2c_navigation.json','sampleSpacingMetres':.5,'maximumVerticalCorrectionMetres':max_adjust,'maximumObservedCorrectionMetres':round(max(samples_adjusted,default=0),3),'terrainGradeAudit':{'phase2bReportedGroundTransitionsOver20Percent':oldreport['groundRoadTransitionsOver20Percent'],'phase2bReportedGroundTransitionsOver35Percent':oldreport['groundRoadTransitionsOver35Percent'],'reconstructedTransitionsOver20Percent':sum(x['meshGrade']>.20 and not x['bridge'] for x in grade_checks),'reconstructedTransitionsOver35Percent':sum(x['meshGrade']>.35 and not x['bridge'] for x in grade_checks),'reviewedTransitions':len(grade_checks),'causeCounts':dict(Counter(x['cause'] for x in grade_checks)),'worstTransitions':sorted(grade_checks,key=lambda x:x['meshGrade'],reverse=True)[:40]},'navigation':{'segmentCounts':dict(grade_counts),'walkableSegments':len(walk_segments),'reviewSegments':len(review_segments),'blockedSegments':len(blocked_segments),'bridgeRuns':sum(r['bridge'] for r in nav_runs),'bridgeMaximumGrade':round(max((x['grade'] for r in nav_runs if r['bridge'] for x in r['segments']),default=0),4),'stairRunsBlocked':sum(r['stairs'] for r in nav_runs),'gapBlockers':len(gap_areas),'testRouteMetres':test_route['lengthMetres'] if test_route else 0,'routeGapsAutoConnected':False,'minWidthMetres':round(min((x['widthMetres'] for x in walk_segments+review_segments+blocked_segments),default=0),3),'maxWalkableGrade':round(max((x['grade'] for x in walk_segments),default=0),4),'maxRequiredCorrectionsMetres':round(max((r['maxCorrectionMetres'] for r in nav_runs if not r['bridge'] and not r['stairs']),default=0),3),'phase2bMeshFallbackStations':source_fallbacks['phase2b_mesh_fallback']},'robotProxy':{'radiusMetres':.28,'heightMetres':.65,'speedMetresPerSecond':2.0,'stepLimitMetres':.16,'collidesOn':'blocked, outside ribbon, water, omitted gap, step over limit','reviewAreasTraversableInPrototype':True,'stairsTraversable':False},'limitations':['Bridge surface height is inferred from Phase 2B bridge endpoints and remains review-only.','Steps are blocked for the wheeled proxy; no climb ability is simulated.','DEM reconciliation is capped at 0.12 m per station and creates a separate collision/render layer.','A 2D station/ribbon collision proxy is used; rigid-body swept-volume physics is not included.']}
 nav={'coordinateSystem':'EPSG:6677 local metres; +Y up','source':'Phase 2B scene and raw DEM1A, read-only','heightCorrectionsAreSeparate':True,'maxPerStationCorrectionMetres':max_adjust,'statusLegend':{'walkable':'#35c978','review':'#f1ad3d','blocked':'#e85258'},'robotProxy':report['robotProxy'],'runs':nav_runs,'blockedAreas':gap_areas,'testRoute':test_route,'gradeAuditTransitions':grade_checks}
 (out/'data/processed/phase2c').mkdir(parents=True,exist_ok=True);(out/'reports/phase2c').mkdir(parents=True,exist_ok=True);(out/'data/processed/phase2c/phase2c_navigation.json').write_text(json.dumps(nav,separators=(',',':')),encoding='utf-8');(out/'reports/phase2c/phase2c_report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='terrainGradeAudit'},indent=2,ensure_ascii=False))
if __name__=='__main__':main()
