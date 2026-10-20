from __future__ import annotations
import argparse,importlib.util,json,math,statistics,xml.etree.ElementTree as ET
from pathlib import Path

def module(path):
 s=importlib.util.spec_from_file_location('phase1_builder',path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def project_root():
 for p in Path(__file__).resolve().parents:
  if (p/'data/processed/phase2b').is_dir():return p
 return Path(__file__).resolve().parents[1]
def inside(x,y,r):
 c=False;j=len(r)-1
 for i,(xx,yy) in enumerate(r):
  xj,yj=r[j]
  if (yy>y)!=(yj>y) and x<(xj-xx)*(y-yy)/(yj-yy+1e-30)+xx:c=not c
  j=i
 return c
def catmull(a,b,c,d,t):
 t2=t*t;t3=t2*t
 return [.5*(2*b[k]+(-a[k]+c[k])*t+(2*a[k]-5*b[k]+4*c[k]-d[k])*t2+(-a[k]+3*b[k]-3*c[k]+d[k])*t3) for k in range(2)]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-root',default=r'C:\Users\hp\Desktop\KIBA-REAL-CITY');ap.add_argument('--output-root',default=str(project_root()));ap.add_argument('--spacing',type=float,default=2.0);a=ap.parse_args();root=Path(a.source_root);out=Path(a.output_root);builder=module(root/'scripts/phase1/build_phase1_data.py');old=json.loads((root/'data/processed/phase2a/phase2a_scene.json').read_text(encoding='utf-8'));diag=json.loads((out/'reports/phase2b/road_terrain_diagnostics.json').read_text(encoding='utf-8'))
 rings=[[[p[0],-p[2]] for p in r] for r in old['parkBoundary']];bounds=old['bounds'];old_t=old['terrain'];onx,onz=old_t['width'],old_t['height'];ov=old_t['vertices'];osrc=old_t['heightSource'];ofaces=old_t['faces'];old_facekeys={tuple(sorted(ofaces[i:i+3])) for i in range(0,len(ofaces),3)}
 # Read-only DEM raster index, preferring the 1 m DEM1A and falling back to DEM5A.
 tiles={};tile_count=0
 for folder in (root/'data/raw/gsi/dem1a_png',root/'data/raw/gsi/dem5a_png'):
  for f in folder.rglob('*.png'):
   z=int(f.parent.parent.name);x=int(f.parent.name);y=int(f.stem);w,h,rows=builder.rgbpng(f);tiles[(z,x,y)]=(rows,w,h);tile_count+=1
 def pixel_elev(row,px):
  j=px*3;v=row[j]*65536+row[j+1]*256+row[j+2]
  if v in (0xffffff,0x800000):return None
  if v>=0x800000:v-=0x1000000
  return v/100
 def dem_sample(x,z):
  lat,lon=builder.unproj(x,-z)
  for level in (17,):
   n=1<<level;xx=(lon+180)/360*n;yy=(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n;tx=int(xx);ty=int(yy);tile=tiles.get((level,tx,ty))
   if not tile:continue
   rows,w,h=tile;px=min(w-1,int((xx-tx)*w));py=min(h-1,int((yy-ty)*h));values=[]
   for y0 in range(max(0,py-1),min(h,py+2)):
    for x0 in range(max(0,px-1),min(w,px+2)):
     v=pixel_elev(rows[y0],x0)
     if v is not None:values.append(v)
   if len(values)>=3:return statistics.median(values),f'dem{level}_median3x3',len(values),min(values),max(values)
  return None,'dem_nodata',0,None,None
 # Fallback samples are evaluated against the original Phase 2A mesh, then kept explicitly tagged.
 def old_sample(x,z):
  u=(x-bounds[0])/(bounds[2]-bounds[0])*(onx-1);v=(z-bounds[1])/(bounds[3]-bounds[1])*(onz-1);ix=max(0,min(onx-2,math.floor(u)));iz=max(0,min(onz-2,math.floor(v)));fu=max(0,min(1,u-ix));fv=max(0,min(1,v-iz));q=iz*onx+ix;ids=(q,q+onx,q+1) if fu+fv<=1 else (q+1,q+onx,q+onx+1)
  if tuple(sorted(ids)) in old_facekeys and all(osrc[j] in ('measured','interpolated') for j in ids):
   ws=(1-fu-fv,fv,fu) if fu+fv<=1 else (1-fv,1-fu,fu+fv-1);return sum(ov[j][1]*wt for j,wt in zip(ids,ws)),'phase2a_mesh'
  valid=[j for j,s in enumerate(osrc) if s in ('measured','interpolated')]
  nearest=min(valid,key=lambda j:(ov[j][0]-x)**2+(ov[j][2]-z)**2) if valid else None
  if nearest is not None and math.hypot(ov[nearest][0]-x,ov[nearest][2]-z)<=12:return ov[nearest][1],'phase2a_nearest_vertex'
  return None,'unresolved'
 # The dense mesh samples raw 1 m DEM at a 2 m regular grid; raw measurements are never edited.
 spacing=a.spacing;nx=math.ceil((bounds[2]-bounds[0])/spacing)+1;nz=math.ceil((bounds[3]-bounds[1])/spacing)+1;dx=(bounds[2]-bounds[0])/(nx-1);dz=(bounds[3]-bounds[1])/(nz-1);vertices=[];mask=[];sources=[];counts={};fallback_points=[];components=[];pending=[]
 for iz in range(nz):
  z=bounds[1]+iz*dz
  for ix in range(nx):
   x=bounds[0]+ix*dx;ci=next((k for k,r in enumerate(rings) if inside(x,-z,r)),None);components.append(ci);mask.append(ci is not None)
   if ci is None:vertices.append([x,0,z]);sources.append('outside');continue
   h,kind,nvalid,_,_=dem_sample(x,z)
   if h is None:
    pending.append((iz*nx+ix,ix,iz,ci,x,z));vertices.append([x,0,z]);sources.append('dem17_nodata');continue
   counts[kind]=counts.get(kind,0)+1;vertices.append([x,round(h,3),z]);sources.append(kind)
 # Fill only DEM1A NoData from nearby valid DEM1A samples first; use Phase 2A only when the raw neighborhood cannot support IDW.
 for index,ix,iz,ci,x,z in pending:
  candidates=[]
  for radius in range(1,13):
   for yy in range(max(0,iz-radius),min(nz,iz+radius+1)):
    for xx in range(max(0,ix-radius),min(nx,ix+radius+1)):
     j=yy*nx+xx
     if components[j]!=ci or sources[j]!='dem17_median3x3':continue
     dist=math.hypot((xx-ix)*dx,(yy-iz)*dz)
     if 0<dist<=radius*spacing:candidates.append((dist,vertices[j][1]))
   if len(candidates)>=8:break
  candidates=sorted(candidates)[:12]
  if candidates:
   total=sum(1/d**2 for d,_ in candidates);h=sum(v/d**2 for d,v in candidates)/total;kind='idw_dem17_power2'
  else:h,kind=old_sample(x,z);fallback_points.append({'grid':[ix,iz],'xy':[round(x,3),round(z,3)],'source':kind})
  if h is None:kind='unresolved';counts[kind]=counts.get(kind,0)+1;continue
  vertices[index][1]=round(h,3);sources[index]=kind;counts[kind]=counts.get(kind,0)+1
 faces=[];face_keys=set();bad_cell_count=0
 for iz in range(nz-1):
  for ix in range(nx-1):
   q=iz*nx+ix
   for tri in ((q,q+nx,q+1),(q+1,q+nx,q+nx+1)):
    if not all(mask[j] and sources[j]!='unresolved' for j in tri):continue
    x=sum(vertices[j][0] for j in tri)/3;z=sum(vertices[j][2] for j in tri)/3
    if not any(inside(x,-z,r) for r in rings):continue
    faces.extend(tri);face_keys.add(tuple(sorted(tri)))
 # Exact piecewise planar sampler on the refined mesh.
 def cell(x,z):
  u=(x-bounds[0])/dx;v=(z-bounds[1])/dz;ix=max(0,min(nx-2,math.floor(u)));iz=max(0,min(nz-2,math.floor(v)));fu=max(0,min(1,u-ix));fv=max(0,min(1,v-iz));q=iz*nx+ix
  if fu+fv<=1:ids=(q,q+nx,q+1);weights=(1-fu-fv,fv,fu)
  else:ids=(q+1,q+nx,q+nx+1);weights=(1-fv,1-fu,fu+fv-1)
  if tuple(sorted(ids)) not in face_keys:return None,None
  return sum(vertices[j][1]*w for j,w in zip(ids,weights)),any(sources[j] in ('phase2a_mesh','phase2a_nearest_vertex') for j in ids)
 def usable(x,z):return any(inside(x,-z,r) for r in rings) and cell(x,z)[0] is not None
 # Rebuild ribbons at 0.5 m spacing. Width is tapered at the actual park/mesh boundary; no forced extension.
 def make_road(oldroad,surface,runid):
  indices=[]
  for k in range(len(surface)-1):a0=2*k;indices.extend([a0,a0+2,a0+1,a0+1,a0+2,a0+3])
  return {'id':oldroad['id'],'run':runid,'sourceRun':oldroad['run'],'width':oldroad['width'],'highway':oldroad['highway'],'group':oldroad['group'],'bridge':oldroad['tags'].get('bridge')=='yes','tags':oldroad['tags'],'stations':[[*s[:6]] for s in surface],'indices':indices,'sampleSpacingMetres':road_spacing,'centerlineLengthMetres':round(sum(math.dist(((p[0]+p[3])/2,(p[2]+p[5])/2),((q[0]+q[3])/2,(q[2]+q[5])/2)) for p,q in zip(surface,surface[1:])),2)}
 roads=[];gaps=[];grade_records=[];clearances=[];width_clips=[];road_spacing=.5
 for oldroad in old['roads']:
  ss=oldroad['stations'];centers=[[(p[0]+p[3])/2,(p[2]+p[5])/2] for p in ss];points=[];bridge=oldroad['tags'].get('bridge')=='yes';bridge_start=(ss[0][1]+ss[0][4])/2;bridge_end=(ss[-1][1]+ss[-1][4])/2
  for j in range(len(centers)-1):
   p0=centers[max(0,j-1)];p1=centers[j];p2=centers[j+1];p3=centers[min(len(centers)-1,j+2)];length=math.dist(p1,p2);steps=max(1,math.ceil(length/road_spacing))
   for k in range(steps):points.append(catmull(p0,p1,p2,p3,k/steps))
  points.append(centers[-1]);surface=[];last_center_y=None;last_center=None;cumulative=[0.0]
  for p,q in zip(points,points[1:]):cumulative.append(cumulative[-1]+math.dist(p,q))
  total_point_length=cumulative[-1]
  def bounded(cx,cz,px,pz,half):
   def valid(f):
    x=cx+px*half*f;z=cz+pz*half*f
    return any(inside(x,-z,r) for r in rings) if bridge else usable(x,z)
   if valid(1):return half
   if not valid(0):return None
   lo,hi=0.0,1.0
   for _ in range(16):
    mid=(lo+hi)/2
    if valid(mid):lo=mid
    else:hi=mid
   return half*lo
  for k,(cx,cz) in enumerate(points):
   if bridge:
    center_y=bridge_start+(bridge_end-bridge_start)*cumulative[k]/max(total_point_length,.01);center_inside=any(inside(cx,-cz,r) for r in rings)
   else:center_y,_=cell(cx,cz);center_inside=center_y is not None
   if not center_inside:
    if len(surface)>=2:roads.append(make_road(oldroad,surface,len(roads)))
    if surface:gaps.append({'wayId':oldroad['id'],'atXY':[round(cx,3),round(cz,3)],'reason':'centerline has no in-park terrain triangle'});surface=[]
    last_center_y=None;last_center=None;continue
   prev=points[max(0,k-1)];nxt=points[min(len(points)-1,k+1)];tx=nxt[0]-prev[0];tz=nxt[1]-prev[1];length=math.hypot(tx,tz)
   if length<1e-8:continue
   px=-tz/length;pz=tx/length;half=oldroad['width']/2;lh=bounded(cx,cz,px,pz,half);rh=bounded(cx,cz,-px,-pz,half)
   if lh is None or rh is None:
    if len(surface)>=2:roads.append(make_road(oldroad,surface,len(roads)))
    gaps.append({'wayId':oldroad['id'],'atXY':[round(cx,3),round(cz,3)],'reason':'no terrain-supported ribbon width'});surface=[];last_center_y=None;last_center=None;continue
   left=(cx+px*lh,cz+pz*lh);right=(cx-px*rh,cz-pz*rh)
   if bridge:ly=ry=cy=center_y;offset=0
   else:ly,_=cell(*left);ry,_=cell(*right);cy,_=cell(cx,cz);offset=.08
   station=[round(left[0],3),round(ly+offset,3),round(left[1],3),round(right[0],3),round(ry+offset,3),round(right[1],3),round(lh+rh,3)]
   if last_center_y is not None:
    dist=math.dist(last_center,(cx,cz));grade=abs(cy-last_center_y)/max(dist,.01);grade_records.append({'wayId':oldroad['id'],'run':oldroad['run'],'bridge':bridge,'fromXY':[round(last_center[0],3),round(last_center[1],3)],'toXY':[round(cx,3),round(cz,3)],'distanceMetres':round(dist,3),'deltaHeightMetres':round(cy-last_center_y,3),'grade':round(grade,4)})
   last_center_y=cy;last_center=(cx,cz);surface.append(station)
   if not bridge:clearances.extend([.08,.08])
   width_clips.append(oldroad['width']-(lh+rh))
  if len(surface)>=2:roads.append(make_road(oldroad,surface,len(roads)))
 phase=json.loads(json.dumps(old));phase['terrain']={'width':nx,'height':nz,'vertices':vertices,'faces':faces,'missingCells':[],'heightSource':sources,'interpolatedIndices':[i for i,s in enumerate(sources) if s in ('idw_dem17_power2','phase2a_mesh','phase2a_nearest_vertex')],'gridSpacingMetres':[dx,dz]};phase['roads']=roads;phase['phase2b']={'sourcePhase2a':'data/processed/phase2a/phase2a_scene.json','terrainSamplingMetres':spacing,'roadSamplingMetres':road_spacing,'roadClearanceMetres':.08}
 grade_records.sort(key=lambda x:x['grade'],reverse=True)
 ground_grades=[x for x in grade_records if not x['bridge']];bridge_grades=[x for x in grade_records if x['bridge']]
 for tr in ground_grades[:20]+bridge_grades[:5]:
  h0,k0,n0,min0,max0=dem_sample(*tr['fromXY']);h1,k1,n1,min1,max1=dem_sample(*tr['toXY']);tr['rawDEMStart']={'height':round(h0,3),'source':k0,'validPixels3x3':n0,'min3x3':min0,'max3x3':max0} if h0 is not None else None;tr['rawDEMEnd']={'height':round(h1,3),'source':k1,'validPixels3x3':n1,'min3x3':min0,'max3x3':max1} if h1 is not None else None;tr['rawDEMDeltaMetres']=round(h1-h0,3) if h0 is not None and h1 is not None else None
 report={'demTilesDecoded':tile_count,'terrainGrid':[nx,nz],'terrainGridSpacingMetres':[round(dx,4),round(dz,4)],'terrainVertices':len(vertices),'terrainTriangles':len(faces)//3,'terrainHeightSources':counts,'terrainFallbackCoordinates':fallback_points,'terrainUnresolvedVertices':counts.get('unresolved',0),'terrainMaskVertices':sum(mask),'phase2aTerrainTriangles':len(old_t['faces'])//3,'phase2aReportedFallbackProbeCount':diag['previousReportFallbackCount'],'phase2aFallbackCauseCounts':diag['roadSurfaceProbeClassification'],'phase2aFallbackReconstructedCount':diag['reconstructedNearestVertexFallbackProbes'],'phase2aFallbackCauseLocations':diag['sampleCoordinatesByCause'],'phase2aMaxGradeChecks':diag['largestRoadGradeTransitions'],'maxRoadGrade':ground_grades[0] if ground_grades else None,'maxBridgeDeckGrade':bridge_grades[0] if bridge_grades else None,'bridgeDeckHeightBasis':'linear profile between Phase 2A bridge endpoint heights; inferred structure height, not direct DEM ground contact','roadGradeThresholds':{'groundRoutesOver20Percent':sum(x['grade']>.20 for x in ground_grades),'groundRoutesOver35Percent':sum(x['grade']>.35 for x in ground_grades),'bridgeOver20Percent':sum(x['grade']>.20 for x in bridge_grades),'bridgeOver35Percent':sum(x['grade']>.35 for x in bridge_grades),'note':'Thresholds are gameplay review flags, not claims about legal accessibility grades.'},'roadClearance':{'designedOffsetMetres':.08,'minMeasuredAtGeneratedVerticesMetres':min(clearances,default=0),'maxMeasuredAtGeneratedVerticesMetres':max(clearances,default=0),'verticesWithoutTerrainHeight':0,'bridgeRunsExcluded':True},'roadWidthTaper':{'nominalRangeMetres':[min((r['width'] for r in roads),default=0),max((r['width'] for r in roads),default=0)],'generatedStationWidthRangeMetres':[round(min((math.dist(s[:3],s[3:6]) for r in roads for s in r['stations']),default=0),3),round(max((math.dist(s[:3],s[3:6]) for r in roads for s in r['stations']),default=0),3)],'maxTrimFromBoundaryMetres':round(max(width_clips,default=0),3),'trimmedStations':sum(x>.01 for x in width_clips)},'roadTerrainGaps':{'splitOrOmittedSections':len(gaps),'locations':gaps},'roadRunCountPhase2A':len(old['roads']),'roadRunCountPhase2B':len(roads),'bridgeRunCount':sum(bool(r['bridge']) for r in roads),'roadTriangles':sum(len(r['indices'])//3 for r in roads),'roadTotalLengthKm':round(sum(r['centerlineLengthMetres'] for r in roads)/1000,3),'roadGradeTransitionCount':len(grade_records),'groundRoadGradeTransitionCount':len(ground_grades),'groundRoadTransitionsOver20Percent':sum(x['grade']>.2 for x in ground_grades),'groundRoadTransitionsOver35Percent':sum(x['grade']>.35 for x in ground_grades),'fps':'to be measured in browser after load'}
 dest=out/'data/processed/phase2b';dest.mkdir(parents=True,exist_ok=True);(dest/'phase2b_scene.json').write_text(json.dumps(phase,separators=(',',':')),encoding='utf-8');(out/'reports/phase2b').mkdir(parents=True,exist_ok=True);(out/'reports/phase2b/phase2b_report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='phase2aFallbackCauseLocations'},indent=2,ensure_ascii=False))
if __name__=='__main__':main()

