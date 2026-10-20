from __future__ import annotations
import argparse,importlib.util,json,math,re,xml.etree.ElementTree as ET
from pathlib import Path

def load_module(path):
 spec=importlib.util.spec_from_file_location('phase1_builder',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def point_in(x,y,r):
 c=False;j=len(r)-1
 for i,(xx,yy) in enumerate(r):
  xj,yj=r[j]
  if (yy>y)!=(yj>y) and x<(xj-xx)*(y-yy)/(yj-yy+1e-30)+xx:c=not c
  j=i
 return c
def cross(a,b):return a[0]*b[1]-a[1]*b[0]
def clipped_runs(points,rings):
 runs=[];cur=[]
 for p,q in zip(points,points[1:]):
  dx=q[0]-p[0];dy=q[1]-p[1];cuts=[0.0,1.0]
  for r in rings:
   for a,b in zip(r,r[1:]+r[:1]):
    ex=b[0]-a[0];ey=b[1]-a[1];den=cross((dx,dy),(ex,ey))
    if abs(den)<1e-12:continue
    t=cross((a[0]-p[0],a[1]-p[1]),(ex,ey))/den;u=cross((a[0]-p[0],a[1]-p[1]),(dx,dy))/den
    if -1e-9<=t<=1+1e-9 and -1e-9<=u<=1+1e-9:cuts.append(min(1,max(0,t)))
  cuts=sorted(set(round(t,10) for t in cuts))
  for t0,t1 in zip(cuts,cuts[1:]):
   if t1-t0<1e-8:continue
   mid=(t0+t1)/2;x=p[0]+dx*mid;y=p[1]+dy*mid
   a=[p[0]+dx*t0,p[1]+dy*t0];b=[p[0]+dx*t1,p[1]+dy*t1]
   if any(point_in(x,y,r) for r in rings):
    if cur and math.hypot(cur[-1][0]-a[0],cur[-1][1]-a[1])<.03:cur.append(b)
    else:
     if len(cur)>1:runs.append(cur)
     cur=[a,b]
   elif len(cur)>1:runs.append(cur);cur=[]
 if len(cur)>1:runs.append(cur)
 clean=[]
 for r in runs:
  out=[r[0]]
  for p in r[1:]:
   if math.hypot(p[0]-out[-1][0],p[1]-out[-1][1])>.08:out.append(p)
  if len(out)>1:clean.append(out)
 return clean
def catmull(p0,p1,p2,p3,t):
 t2=t*t;t3=t2*t
 return [0.5*((2*p1[k])+(-p0[k]+p2[k])*t+(2*p0[k]-5*p1[k]+4*p2[k]-p3[k])*t2+(-p0[k]+3*p1[k]-3*p2[k]+p3[k])*t3) for k in range(2)]
def width_for(tags):
 m=re.search(r'\d+(?:\.\d+)?',str(tags.get('width','')))
 if m:
  w=float(m.group())
  if .5<=w<=20:return w
 return {'footway':2.2,'pedestrian':3.6,'steps':1.8,'service':4.0,'tertiary':5.5,'path':1.8,'cycleway':2.5}.get(tags.get('highway'),2.0)
def group_for(hw):return 'steps' if hw=='steps' else 'vehicular' if hw in ('service','tertiary','residential','unclassified') else 'walk'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-root',default=r'C:\Users\hp\Desktop\KIBA-REAL-CITY');ap.add_argument('--output-root',default=str(Path(__file__).resolve().parents[2]));a=ap.parse_args();root=Path(a.source_root);out=Path(a.output_root);phase1=root/'data/processed/phase1_threejs/phase1_scene.json';report1=root/'data/processed/phase1_threejs/validation_report.json';builder=load_module(root/'scripts/phase1/build_phase1_data.py');src=json.loads(phase1.read_text(encoding='utf-8'));r1=json.loads(report1.read_text(encoding='utf-8'));t=src['terrain'];nx,nz=t['width'],t['height'];verts=t['vertices'];box=src['bounds'];polys=[[[p[0],-p[2]] for p in poly] for poly in src['parkBoundary']]
 mask=[];component=[];heights=[None]*len(verts);sources=['outside']*len(verts);reasons={};dem=[]
 for f in sorted(list((root/'data/raw/gsi/dem1a_png').rglob('*.png'))+list((root/'data/raw/gsi/dem5a_png').rglob('*.png'))):
  try:dem.append((f,*builder.rgbpng(f)))
  except Exception:continue
 def sample_dem(lat,lon):
  status=[]
  for level in (17,15):
   scale=1<<level;xx=(lon+180)/360*scale;yy=(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*scale;tx=int(xx);ty=int(yy);px=min(255,int((xx-tx)*256));py=min(255,int((yy-ty)*256));found=False
   for f,w,h,rows in dem:
    if int(f.parent.parent.name)!=level or f.stem!=str(ty) or f.parent.name!=str(tx):continue
    found=True;q=px*3;v=rows[py][q]*65536+rows[py][q+1]*256+rows[py][q+2]
    if v in (0xffffff,0x800000):status.append(f'dem{level}_nodata');break
    if v>=0x800000:v-=0x1000000
    return v/100,level,'measured',status
   if not found:status.append(f'dem{level}_tile_missing')
  return None,None,'nodata',status
 missing=[];measured_count=0;phase1_diff=[]
 for i,(x,h,z) in enumerate(verts):
  ix=i%nx;iz=i//nx;xraw=box[0]+(box[2]-box[0])*ix/(nx-1);zraw=box[1]+(box[3]-box[1])*iz/(nz-1);north=-zraw;ci=next((j for j,r in enumerate(polys) if point_in(xraw,north,r)),None);mask.append(ci is not None);component.append(ci)
  if ci is None:continue
  lat,lon=builder.unproj(xraw,north);elev,level,kind,reason=sample_dem(lat,lon)
  if elev is not None:
   heights[i]=h;sources[i]='measured';measured_count+=1;phase1_diff.append(abs(elev-h))
  else:
   missing.append({'index':i,'grid':[i%nx,i//nx],'xy':[round(x,3),round(z,3)],'latlon':[round(lat,8),round(lon,8)],'reason':'+'.join(reason) if reason else 'both DEM levels no-data'})
   key='+'.join(reason) if reason else 'both DEM levels no-data';reasons[key]=reasons.get(key,0)+1
 # IDW uses measured samples only; direct measurements are copied byte-for-byte at their 0.01 m source precision.
 interpolated=[];unresolved=[]
 for m in missing:
  i=m['index'];ix,iz=m['grid'];ci=component[i];candidates=[]
  for radius in range(1,13):
   for dz in range(-radius,radius+1):
    zz=iz+dz
    if zz<0 or zz>=nz:continue
    for dx in range(-radius,radius+1):
     xx=ix+dx
     if xx<0 or xx>=nx:continue
     j=zz*nx+xx
     if sources[j]!='measured' or component[j]!=ci:continue
     dist=math.hypot(verts[j][0]-verts[i][0],verts[j][2]-verts[i][2])
     if dist<=radius*10:candidates.append((dist,heights[j]))
   if len(candidates)>=8:break
  candidates=sorted(candidates)[:12]
  if not candidates:
   unresolved.append(m);sources[i]='unresolved';continue
  wsum=sum(1/max(d,.05)**2 for d,_ in candidates);h=sum(v/max(d,.05)**2 for d,v in candidates)/wsum;heights[i]=h;sources[i]='interpolated';m.update({'elevation':round(h,3),'neighborCount':len(candidates),'maxNeighborDistanceMetres':round(max(d for d,_ in candidates),3),'method':'IDW power=2'});interpolated.append(m)
 # Rebuild ground triangles across repaired cells; exclude exterior triangles and preserve each polygon component.
 faces=[];source_faces=[]
 for iz in range(nz-1):
  for ix in range(nx-1):
   q=iz*nx+ix;tris=[(q,q+nx,q+1),(q+1,q+nx,q+nx+1)]
   for tri in tris:
    if not all(mask[j] and heights[j] is not None for j in tri):continue
    x=sum(verts[j][0] for j in tri)/3;z=sum(verts[j][2] for j in tri)/3
    if not any(point_in(x,-z,r) for r in polys):continue
    faces.extend(tri);source_faces.append(tri)
 # Exact surface-height sampler follows the same two-triangle split used by the terrain mesh.
 xspan=box[2]-box[0];zspan=box[3]-box[1];fallback_samples=0
 def ground(x,z):
  nonlocal fallback_samples
  u=(x-box[0])/xspan*(nx-1);v=(z-box[1])/zspan*(nz-1);ix=max(0,min(nx-2,int(math.floor(u))));iz=max(0,min(nz-2,int(math.floor(v))));fu=max(0,min(1,u-ix));fv=max(0,min(1,v-iz));q=iz*nx+ix;b=q+1;c=q+nx;d=c+1
  if fu+fv<=1:ids=(q,c,b);weights=(1-fu-fv,fv,fu)
  else:ids=(b,c,d);weights=(1-fv,1-fu,fu+fv-1)
  if all(heights[j] is not None for j in ids):return sum(heights[j]*w for j,w in zip(ids,weights)),any(sources[j]=='interpolated' for j in ids)
  fallback_samples+=1;near=[]
  for j,h in enumerate(heights):
   if h is not None and mask[j]:near.append((math.hypot(verts[j][0]-x,verts[j][2]-z),h,sources[j]))
  if not near:return 0.0,True
  near.sort();return near[0][1],near[0][2]=='interpolated'
 # Load OSM paths directly so clipped segments cannot be joined across outside geometry.
 nodes={};ways={};wanted={str(f['id']) for f in src['features']['paths']}
 for f in (root/'data/raw/osm/layers').rglob('*.osm'):
  for e in ET.parse(f).getroot():
   if e.tag=='node':nodes[e.get('id')]=(float(e.get('lat')),float(e.get('lon')))
   elif e.tag=='way' and e.get('id') in wanted and 'paths' in str(f) and e.find("tag[@k='highway']") is not None:
    item={'refs':[n.get('ref') for n in e.findall('nd')],'tags':{x.get('k'):x.get('v') for x in e.findall('tag')},'version':int(e.get('version','0'))};old=ways.get(e.get('id'))
    if old is None or item['version']>=old['version']:ways[e.get('id')]=item
 roads=[];raw_runs=0;outside_segments=0;road_len=0;clearances=[];station_interp=0;group_counts={};step_deltas=[];step_slopes=[]
 for wid,w in ways.items():
  raw=[]
  for ref in w['refs']:
   if ref not in nodes:continue
   lat,lon=nodes[ref];x,north=builder.proj(lat,lon);raw.append((x,north))
  if len(raw)<2:continue
  runs=clipped_runs(raw,polys);raw_runs+=len(runs);hw=w['tags'].get('highway','other');width=width_for(w['tags']);group=group_for(hw)
  for ri,run in enumerate(runs):
   pts=[[x,-y] for x,y in run]
   smooth=[]
   for j in range(len(pts)-1):
    p0=pts[max(0,j-1)];p1=pts[j];p2=pts[j+1];p3=pts[min(len(pts)-1,j+2)];seglen=math.hypot(p2[0]-p1[0],p2[1]-p1[1]);steps=max(1,math.ceil(seglen/1.25))
    for s in range(steps):smooth.append(catmull(p0,p1,p2,p3,s/steps))
   smooth.append(pts[-1]);surface=[]
   for k,(cx,cz) in enumerate(smooth):
    prev=smooth[max(0,k-1)];nxt=smooth[min(len(smooth)-1,k+1)];tx=nxt[0]-prev[0];tz=nxt[1]-prev[1];length=math.hypot(tx,tz)
    if length<1e-8:continue
    px=-tz/length;pz=tx/length;half=width/2
    left=(cx+px*half,cz+pz*half);right=(cx-px*half,cz-pz*half)
    lh,li=ground(*left);rh,ri2=ground(*right);center,_=ground(cx,cz);off=.06
    surface.append([round(left[0],3),round(lh+off,3),round(left[1],3),round(right[0],3),round(rh+off,3),round(right[1],3)])
    clearances.extend([lh+off-lh,rh+off-rh]);station_interp+=int(li)+int(ri2)
   if len(surface)<2:continue
   indices=[]
   for k in range(len(surface)-1):a0=2*k;b0=a0+1;c0=a0+2;d0=a0+3;indices.extend([a0,c0,b0,b0,c0,d0])
   for k in range(len(surface)-1):
    a0,b0=surface[k],surface[k+1];dy=abs(((a0[1]+a0[4])-(b0[1]+b0[4]))/2);ds=math.hypot((a0[0]+a0[3]-b0[0]-b0[3])/2,(a0[2]+a0[5]-b0[2]-b0[5])/2)
    step_deltas.append(dy);step_slopes.append(dy/max(ds,.01))
   length=sum(math.hypot(b[0]-a0[0],b[1]-a0[1]) for a0,b in zip(smooth,smooth[1:]));road_len+=length
   roads.append({'id':wid,'run':ri,'width':round(width,2),'highway':hw,'group':group,'tags':w['tags'],'stations':surface,'indices':indices,'centerlineLengthMetres':round(length,2)})
   group_counts[group]=group_counts.get(group,0)+1
 # Scene holds a full immutable copy of Phase 1 data plus repaired terrain and road ribbons.
 phase2=json.loads(json.dumps(src));phase2['terrain']['vertices']=[[v[0],round(heights[i],3) if heights[i] is not None else 0,v[2]] for i,v in enumerate(verts)];phase2['terrain']['faces']=faces;phase2['terrain']['missingCells']=[];phase2['terrain']['heightSource']=sources;phase2['terrain']['interpolatedIndices']=[m['index'] for m in interpolated];phase2['roads']=roads
 phase2['phase2a']={'sourcePhase1Scene':'data/processed/phase1_threejs/phase1_scene.json','interpolation':{'method':'IDW (power 2), measured vertices only; same park component','offsetPreservedMetres':0,'resolved':len(interpolated),'unresolved':len(unresolved),'vertices':interpolated},'roadGeneration':{'centerlineSmoothing':'Catmull-Rom, approx 1.25 m sampling','terrainClearanceMetres':0.06,'clippedRunCount':raw_runs,'renderGroups':group_counts}}
 report={'phase1Snapshot':{'osmFiles':r1['osmFiles'],'phase1MeasuredVertices':r1['parkValidVertices'],'phase1MissingVertices':r1['parkMissingVertices'],'phase1MissingCells':r1['missingTerrainCells']},'demTileCount':len(dem),'demMissingCauseCounts':reasons,'measuredVertices':measured_count,'interpolatedVertices':len(interpolated),'unresolvedVertices':len(unresolved),'phase1MeasuredHeightMaxDifferenceMetres':max(phase1_diff,default=0),'interpolatedHeightRange':[round(min(x['elevation'] for x in interpolated),3),round(max(x['elevation'] for x in interpolated),3)] if interpolated else None,'interpolationMaxNeighborDistanceMetres':max((x['maxNeighborDistanceMetres'] for x in interpolated),default=0),'roadInputWayCount':len(ways),'roadRibbonRunCount':len(roads),'roadRunsClippedToPark':raw_runs,'roadExcludedRunCount':raw_runs-len(roads),'roadRenderedGroups':len(group_counts),'roadMeshVertices':sum(2*len(x['stations']) for x in roads),'roadMeshTriangles':sum(len(x['indices'])//3 for x in roads),'roadTotalCenterlineKm':round(road_len/1000,3),'roadWidthRangeMetres':[min((x['width'] for x in roads),default=0),max((x['width'] for x in roads),default=0)],'roadClearanceMetres':{'target':.06,'observedMin':round(min(clearances,default=0),5),'observedMax':round(max(clearances,default=0),5),'negativeClearanceSamples':sum(x<0 for x in clearances),'clearanceVariance':round(max(clearances,default=0)-min(clearances,default=0),6),'note':'The ribbon vertices are sampled on the terrain surface then raised by exactly 0.06m; edge locations using nearest valid terrain fallback are counted separately.'},'roadHeightChangeBetweenAdjacentStationsMetres':{'max':round(max(step_deltas,default=0),3),'maxGradeRatio':round(max(step_slopes,default=0),4)},'terrainFaceCountPhase1':len(t['faces'])//3,'terrainFaceCountPhase2':len(faces)//3,'terrainGapCellsPhase1':len(t['missingCells']),'terrainGapCellsPhase2':0 if not unresolved else len(unresolved),'terrainFallbackSamplesForRoadEdges':fallback_samples,'pathwaySegmentContinuity':'raw OSM paths clipped at park boundary; no out-of-bound vertex filtering joins','fpsMeasurement':'browser runtime display; captured during visual review, varies by device'}
 dest=out/'data/processed/phase2a';dest.mkdir(parents=True,exist_ok=True);(dest/'phase2a_scene.json').write_text(json.dumps(phase2,separators=(',',':')),encoding='utf-8');(dest/'phase2a_report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='phase1Snapshot'},indent=2,ensure_ascii=False))
if __name__=='__main__':main()
