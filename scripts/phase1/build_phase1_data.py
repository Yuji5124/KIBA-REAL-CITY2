from __future__ import annotations
import argparse,json,math,struct,zlib
from pathlib import Path
import xml.etree.ElementTree as ET

OE,ON=-2302.317826321731,-36106.717222697174
A,F=6378137.0,1/298.257222101
E2=F*(2-F); EP=E2/(1-E2); K=.9999; P0=math.radians(36); L0=math.radians(139+50/60)
def proj(lat,lon):
 p,l=math.radians(lat),math.radians(lon); n=A/math.sqrt(1-E2*math.sin(p)**2); t=math.tan(p)**2;c=EP*math.cos(p)**2;u=(l-L0)*math.cos(p);e4=E2**2;e6=e4*E2
 def m(x):return A*((1-E2/4-3*e4/64-5*e6/256)*x-(3*E2/8+3*e4/32+45*e6/1024)*math.sin(2*x)+(15*e4/256+45*e6/1024)*math.sin(4*x)-35*e6/3072*math.sin(6*x))
 return K*n*(u+(1-t+c)*u**3/6+(5-18*t+t*t+72*c-58*EP)*u**5/120)-OE,K*(m(p)-m(P0)+n*math.tan(p)*(u*u/2+(5-t+9*c+4*c*c)*u**4/24+(61-58*t+t*t+600*c-330*EP)*u**6/720))-ON
def unproj(x,y):
 lat=35.67455+y/111000;lon=139.8079+x/(111000*math.cos(math.radians(lat)))
 for _ in range(4):
  px,py=proj(lat,lon);d=1e-5;ax,ay=proj(lat+d,lon);bx,by=proj(lat,lon+d);j11=(ax-px)/d;j21=(ay-py)/d;j12=(bx-px)/d;j22=(by-py)/d;det=j11*j22-j12*j21;dx=x-px;dy=y-py
  lat+=(dx*j22-dy*j12)/det;lon+=(dy*j11-dx*j21)/det
 return lat,lon
def rgbpng(path):
 b=path.read_bytes();pos=8;parts=[];w=h=typ=depth=None
 while pos<len(b):
  ln=struct.unpack('>I',b[pos:pos+4])[0];tag=b[pos+4:pos+8];d=b[pos+8:pos+8+ln];pos+=ln+12
  if tag==b'IHDR':w,h,depth,typ,*_=struct.unpack('>IIBBBBB',d)
  if tag==b'IDAT':parts.append(d)
 if depth!=8 or typ!=2:raise ValueError('DEM PNG must be RGB8')
 raw=zlib.decompress(b''.join(parts));rows=[];prev=bytearray(w*3);k=0
 for _ in range(h):
  f=raw[k];k+=1;r=bytearray(raw[k:k+w*3]);k+=w*3
  for i in range(len(r)):
   l=r[i-3] if i>=3 else 0;u=prev[i];ul=prev[i-3] if i>=3 else 0
   if f==1:r[i]=(r[i]+l)&255
   elif f==2:r[i]=(r[i]+u)&255
   elif f==3:r[i]=(r[i]+(l+u)//2)&255
   elif f==4:
    q=l+u-ul;pa,pb,pc=abs(q-l),abs(q-u),abs(q-ul);r[i]=(r[i]+(l if pa<=pb and pa<=pc else u if pb<=pc else ul))&255
   elif f!=0:raise ValueError('PNG filter')
  rows.append(r);prev=r
 return w,h,rows
def inside(x,y,r):
 c=False;j=len(r)-1
 for i,(xx,yy) in enumerate(r):
  xj,yj=r[j]
  if (yy>y)!=(yj>y) and x<(xj-xx)*(y-yy)/(yj-yy+1e-30)+xx:c=not c
  j=i
 return c
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-root',default=r'C:\Users\hp\Desktop\KIBA-REAL-CITY');ap.add_argument('--output-root',default=str(Path(__file__).resolve().parents[2]));a=ap.parse_args();root=Path(a.source_root);osm=root/'data/raw/osm';files=list((osm/'layers').rglob('*.osm'))
 nodes={};ways={};rels={};dups=0;conf=[]
 for f in files:
  for e in ET.parse(f).getroot():
   if e.tag not in ('node','way','relation'):continue
   d={'id':e.get('id'),'v':int(e.get('version',0)),'tags':{x.get('k'):x.get('v') for x in e.findall('tag')}}
   if e.tag=='node':d.update(lat=float(e.get('lat')),lon=float(e.get('lon')));tab=nodes
   elif e.tag=='way':d['refs']=[x.get('ref') for x in e.findall('nd')];tab=ways
   else:d['members']=[(x.get('type'),x.get('ref'),x.get('role')) for x in e.findall('member')];tab=rels
   old=tab.get(d['id']);
   if old:
    dups+=1
    if old['tags']!=d['tags']:conf.append(e.tag+'/'+d['id'])
    if d['v']>=old['v']:tab[d['id']]=d
   else:tab[d['id']]=d
 errors=[f'way/{i}->node/{n}' for i,w in ways.items() for n in w['refs'] if n not in nodes]
 errors.extend(f'relation/{i}->{t}/{ref}' for i,r in rels.items() for t,ref,role in r.get('members',[]) if ref not in {'node':nodes,'way':ways,'relation':rels}.get(t,{}))
 b=ET.parse(osm/'kiba_park_relation_14273608.osm').getroot()
 for e in b.findall('node'):nodes.setdefault(e.get('id'),{'lat':float(e.get('lat')),'lon':float(e.get('lon')),'tags':{}})
 for e in b.findall('way'):ways.setdefault(e.get('id'),{'refs':[n.get('ref') for n in e.findall('nd')],'tags':{}})
 rel=next((x for x in b.findall('relation') if x.get('id')=='14273608'),None); rings=[]
 for m in rel.findall('member'):
  w=ways.get(m.get('ref'))
  if m.get('type')=='way' and m.get('role')=='outer' and w:
   r=[proj(nodes[n]['lat'],nodes[n]['lon']) for n in w['refs'] if n in nodes]
   if len(r)>2:rings.append(r)
 if not rings:raise RuntimeError('park outer boundary missing')
 # OSM multipolygon boundary may be split across several member ways; join by shared endpoint IDs.
 refs=[ways[m.get('ref')]['refs'][:] for m in rel.findall('member') if m.get('type')=='way' and m.get('role')=='outer' and m.get('ref') in ways]
 joined=[]
 while refs:
  chain=refs.pop(0)
  changed=True
  while changed and chain[0]!=chain[-1]:
   changed=False
   for i,seg in enumerate(refs):
    if chain[-1]==seg[0]:chain.extend(seg[1:])
    elif chain[-1]==seg[-1]:chain.extend(reversed(seg[:-1]))
    elif chain[0]==seg[-1]:chain[:0]=seg[:-1]
    elif chain[0]==seg[0]:chain[:0]=list(reversed(seg[1:]))
    else:continue
    refs.pop(i);changed=True;break
  if len(chain)>3 and chain[0]==chain[-1]:joined.append([proj(nodes[n]['lat'],nodes[n]['lon']) for n in chain if n in nodes])
 if joined:rings=joined
 ring=max(rings,key=len);X=[p[0] for r in rings for p in r];Z=[-p[1] for r in rings for p in r];box=[min(X),min(Z),max(X),max(Z)]
 dem=[];dempaths=list((root/'data/raw/gsi/dem1a_png').rglob('*.png'))+list((root/'data/raw/gsi/dem5a_png').rglob('*.png'))
 for p in dempaths:
  try:dem.append((p,*rgbpng(p)))
  except Exception:pass
 tilestats=[]
 for p,w,h,rows in dem:
  z=int(p.parent.parent.name);tx=int(p.parent.name);ty=int(p.stem);vv=[]
  for row in rows:
   for q in range(0,len(row),3):
    code=row[q]*65536+row[q+1]*256+row[q+2]
    if code not in (0xffffff,0x800000):
     if code>=0x800000:code-=0x1000000
     elevval=code/100
     if elevval>-1000:vv.append(elevval)
  n=1<<z;west=tx/n*360-180;east=(tx+1)/n*360-180
  lat=lambda yy:math.degrees(math.atan(math.sinh(math.pi*(1-2*yy/n))))
  tilestats.append({'file':str(p.relative_to(root)),'zoom':z,'validPixels':len(vv),'elevationRange':[round(min(vv),2),round(max(vv),2)] if vv else None,'coverageLonLat':[round(west,7),round(lat(ty+1),7),round(east,7),round(lat(ty),7)]})
 def elev(lat,lon):
  for level in (17,15):
   scale=1<<level;xx=(lon+180)/360*scale;yy=(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*scale;tx=int(xx);ty=int(yy);px=min(255,int((xx-tx)*256));py=min(255,int((yy-ty)*256))
   for p,w,h,rows in dem:
    if f'dem{1 if level==17 else 5}a_png' in str(p) and p.stem==str(ty) and p.parent.name==str(tx):
     q=px*3;v=rows[py][q]*65536+rows[py][q+1]*256+rows[py][q+2]
     if v==0xffffff or v==0x800000:continue
     if v>=0x800000:v-=0x1000000
     return v/100 if v/100>-1000 else None
  return None
 step=8;nx=math.ceil((box[2]-box[0])/step)+1;nz=math.ceil((box[3]-box[1])/step)+1;verts=[];ok=[];mask=[];heights=[];miss=[]
 for iz in range(nz):
  z=box[1]+(box[3]-box[1])*iz/(nz-1)
  for ix in range(nx):
   x=box[0]+(box[2]-box[0])*ix/(nx-1);north=-z;lat,lon=unproj(x,north);h=elev(lat,lon)
   inpark=any(inside(x,north,r) for r in rings);mask.append(inpark)
   if not inpark:h=None
   if h is not None:heights.append(h)
   verts.append([round(x,3),round(h or 0,2),round(z,3)]);ok.append(h is not None)
 faces=[]
 for iz in range(nz-1):
  for ix in range(nx-1):
   q=iz*nx+ix;r=(q,q+1,q+nx,q+nx+1)
   if ok[r[0]] and ok[r[1]] and ok[r[2]]:faces.extend([r[0],r[2],r[1]])
   if ok[r[1]] and ok[r[2]] and ok[r[3]]:faces.extend([r[1],r[2],r[3]])
   mx=(box[0]+(box[2]-box[0])*(ix+.5)/(nx-1));my=-(box[1]+(box[3]-box[1])*(iz+.5)/(nz-1))
   if not all(ok[i] for i in r) and any(inside(mx,my,poly) for poly in rings):miss.append([ix,iz])
 feats={k:[] for k in ['paths','buildings','water','vegetation','facilities']}
 for wid,w in ways.items():
  pts=[]
  for n in w.get('refs',[]):
   if n in nodes:
    x,y=proj(nodes[n]['lat'],nodes[n]['lon'])
    if any(inside(x,y,r) for r in rings):pts.append([round(x,3),0,round(-y,3)])
  if len(pts)<2:continue
  t=w.get('tags',{});obj={'id':wid,'points':pts,'tags':t}
  if 'highway' in t:feats['paths'].append(obj)
  if 'building' in t:feats['buildings'].append(obj)
  if 'water' in t or t.get('natural')=='water' or 'waterway' in t:feats['water'].append(obj)
  if t.get('natural') in ('wood','scrub','grassland','tree_row') or t.get('landuse') in ('grass','forest','meadow','recreation_ground'):feats['vegetation'].append(obj)
  if any(k in t for k in ('amenity','leisure','tourism','barrier','man_made')):feats['facilities'].append(obj)
 for nid,n in nodes.items():
  t=n.get('tags',{});x,y=proj(n['lat'],n['lon'])
  if any(inside(x,y,r) for r in rings):
   if t.get('natural')=='tree':feats['vegetation'].append({'id':nid,'point':[x,0,-y],'tags':t})
   if any(k in t for k in ('amenity','leisure','tourism','man_made')):feats['facilities'].append({'id':nid,'point':[x,0,-y],'tags':t})
 report={'osmFiles':len(files),'uniqueNodes':len(nodes),'uniqueWays':len(ways),'uniqueRelations':len(rels),'duplicateIdsRemoved':dups,'tagConflicts':conf[:40],'brokenReferenceCount':len(errors),'brokenReferences':errors[:40],'demTilesFound':len(dempaths),'demTilesDecoded':len(dem),'demTileResolutionCounts':{'1a':sum('dem1a_png' in str(p) for p,_,_,_ in dem),'5a':sum('dem5a_png' in str(p) for p,_,_,_ in dem)},'demTileCoverage':tilestats,'validTerrainVertices':sum(ok),'parkValidVertices':sum(ok),'parkMissingVertices':sum(1 for i in range(len(ok)) if mask[i] and not ok[i]),'outsideParkGridVertices':sum(1 for v in mask if not v),'missingTerrainCells':len(miss),'featureCounts':{k:len(v) for k,v in feats.items()},'coordinateOriginResidualMetres':[round(proj(35.67455,139.8079)[0],6),round(proj(35.67455,139.8079)[1],6)],'fountainsValidEmpty':(osm/'layers/water/fountains.osm').stat().st_size<500}
 scene={'crs':'EPSG:6677','coordinateConvention':'Three.js: x=east, y=T.P. metres, z=-north; local origin from KPR','origin':[OE,ON],'bounds':box,'parkBoundary':[[[round(x,3),0,round(-y,3)] for x,y in poly] for poly in rings],'terrain':{'width':nx,'height':nz,'vertices':verts,'faces':faces,'missingCells':miss,'stepMetres':step,'elevationRange':[min(heights),max(heights)] if heights else None},'features':feats,'validation':report}
 dest=Path(a.output_root)/'data/processed/phase1_threejs';dest.mkdir(parents=True,exist_ok=True);(dest/'phase1_scene.json').write_text(json.dumps(scene,separators=(',',':')),encoding='utf-8');(dest/'validation_report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8');print(json.dumps(report,indent=2,ensure_ascii=False))
if __name__=='__main__':main()
