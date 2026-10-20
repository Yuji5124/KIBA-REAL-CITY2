from __future__ import annotations
import argparse, importlib.util, json, math, statistics
from collections import Counter, defaultdict
from pathlib import Path

def load_builder(p):
 s=importlib.util.spec_from_file_location('phase1_builder',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
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
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-root',default=r'C:\Users\hp\Desktop\KIBA-REAL-CITY');ap.add_argument('--output-root',default=str(project_root()));a=ap.parse_args();root=Path(a.source_root);out=Path(a.output_root);scene=json.loads((root/'data/processed/phase2a/phase2a_scene.json').read_text(encoding='utf-8'));rep=json.loads((root/'data/processed/phase2a/phase2a_report.json').read_text(encoding='utf-8'));builder=load_builder(root/'scripts/phase1/build_phase1_data.py');t=scene['terrain'];nx,nz=t['width'],t['height'];verts=t['vertices'];src=t['heightSource'];bounds=scene['bounds'];rings=[[[p[0],-p[2]] for p in r] for r in scene['parkBoundary']];facekeys={tuple(sorted(t['faces'][i:i+3])) for i in range(0,len(t['faces']),3)}
 def cell(x,z):
  u=(x-bounds[0])/(bounds[2]-bounds[0])*(nx-1);v=(z-bounds[1])/(bounds[3]-bounds[1])*(nz-1);ix=max(0,min(nx-2,math.floor(u)));iz=max(0,min(nz-2,math.floor(v)));fu=max(0,min(1,u-ix));fv=max(0,min(1,v-iz));q=iz*nx+ix;ids=(q,q+nx,q+1) if fu+fv<=1 else (q+1,q+nx,q+nx+1);return ids
 counts=Counter();samples=defaultdict(list);fallback_total=0
 for road in scene['roads']:
  for si,s in enumerate(road['stations']):
   probes=((s[0],s[1],s[2],'left'),(s[3],s[4],s[5],'right'),((s[0]+s[3])/2,(s[1]+s[4])/2,(s[2]+s[5])/2,'center'))
   for x,y,z,side in probes:
    ids=cell(x,z);inpark=any(inside(x,-z,r) for r in rings);hasface=tuple(sorted(ids)) in facekeys;hasvalid=all(src[j] in ('measured','interpolated') for j in ids)
    if not inpark:reason='outside_park_boundary'
    elif not hasvalid:reason='inside_park_triangle_touches_outside_or_unresolved_grid_vertex'
    elif not hasface:reason='inside_park_no_rendered_triangle_but_grid_heights_exist'
    else:reason='terrain_triangle_available'
    counts[reason]+=1
    if not hasvalid:
     fallback_total+=1;lat,lon=builder.unproj(x,-z);samples[reason].append({'wayId':road['id'],'run':road['run'],'station':si,'side':side,'xy':[round(x,3),round(z,3)],'latlon':[round(lat,8),round(lon,8)],'roadElevation':y,'gridVertexIds':list(ids),'gridVertexSources':[src[j] for j in ids]})
 # Find largest neighboring station delta and compare it to raw DEM at 1 m sampling.
 transitions=[]
 for road in scene['roads']:
  ss=road['stations']
  for i,(p,q) in enumerate(zip(ss,ss[1:])):
   ax=(p[0]+p[3])/2;az=(p[2]+p[5])/2;ah=(p[1]+p[4])/2;bx=(q[0]+q[3])/2;bz=(q[2]+q[5])/2;bh=(q[1]+q[4])/2;dist=math.hypot(bx-ax,bz-az);dy=bh-ah
   transitions.append({'wayId':road['id'],'run':road['run'],'segment':i,'highway':road['highway'],'group':road['group'],'start':[ax,az,ah],'end':[bx,bz,bh],'distanceMetres':dist,'deltaHeightMetres':dy,'absoluteDeltaMetres':abs(dy),'grade':abs(dy)/max(dist,.001)})
 transitions.sort(key=lambda q:q['grade'],reverse=True)
 # DEM PNGs are decoded once and indexed by XYZ tile address. A 3x3 median reduces single-pixel noise.
 tiles={}
 for folder in (root/'data/raw/gsi/dem1a_png',root/'data/raw/gsi/dem5a_png'):
  for f in folder.rglob('*.png'):
   tiles[(int(f.parent.parent.name),int(f.parent.name),int(f.stem))]=builder.rgbpng(f)[2]
 def rawdem(x,z):
  lat,lon=builder.unproj(x,-z)
  for level in (17,15):
   n=1<<level;xx=(lon+180)/360*n;yy=(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n;tx=int(xx);ty=int(yy);img=tiles.get((level,tx,ty))
   if img is None:continue
   px=min(255,int((xx-tx)*256));py=min(255,int((yy-ty)*256));vals=[]
   for y0 in range(max(0,py-1),min(256,py+2)):
    for x0 in range(max(0,px-1),min(256,px+2)):
     j=x0*3;v=img[y0][j]*65536+img[y0][j+1]*256+img[y0][j+2]
     if v not in (0xffffff,0x800000):vals.append((v-0x1000000 if v>=0x800000 else v)/100)
   if vals:return {'level':level,'median3x3':statistics.median(vals),'min3x3':min(vals),'max3x3':max(vals),'validPixels3x3':len(vals),'latlon':[lat,lon]}
  return None
 for tr in transitions[:20]:
  tr['rawDEMStart']=rawdem(*tr['start'][:2]);tr['rawDEMEnd']=rawdem(*tr['end'][:2])
  if tr['rawDEMStart'] and tr['rawDEMEnd']:
   tr['rawDEMMedianDeltaMetres']=round(tr['rawDEMEnd']['median3x3']-tr['rawDEMStart']['median3x3'],3);tr['DEMComparedDeltaDifferenceMetres']=round(tr['deltaHeightMetres']-tr['rawDEMMedianDeltaMetres'],3)
  else:tr['rawDEMMedianDeltaMetres']=None;tr['DEMComparedDeltaDifferenceMetres']=None
 for reason,v in samples.items():
  v.sort(key=lambda p:(p['wayId'],p['run'],p['station'],p['side']))
  for p in v:p['rawDEM']=rawdem(*p['xy'])
 result={'sourcePhase2aReport':rep,'roadSurfaceProbeClassification':dict(counts),'reconstructedNearestVertexFallbackProbes':fallback_total,'previousReportFallbackCount':rep['terrainFallbackSamplesForRoadEdges'],'classificationMatchesPreviousFallbackCount':fallback_total==rep['terrainFallbackSamplesForRoadEdges'],'sampleCoordinatesByCause':dict(samples),'largestRoadGradeTransitions':transitions[:20],'analysisNotes':['For each exported ribbon station, both edges and the reconstructed centerline were tested against Phase 2A grid source labels.','Raw DEM comparison uses a 3x3 valid-pixel median, preferring zoom 17 then zoom 15.','The 1 m DEM remains source data; this report does not edit it.']}
 dest=out/'reports/phase2b';dest.mkdir(parents=True,exist_ok=True);(dest/'road_terrain_diagnostics.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8');print(json.dumps({'classification':dict(counts),'reconstructed':fallback_total,'previous':rep['terrainFallbackSamplesForRoadEdges'],'topGrade':transitions[:5]},indent=2,ensure_ascii=False))
if __name__=='__main__':main()
