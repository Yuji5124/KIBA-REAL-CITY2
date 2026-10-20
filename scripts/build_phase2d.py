from __future__ import annotations
import argparse, collections, hashlib, importlib.util, json, math, random, xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image

def load_helper(p):
    spec=importlib.util.spec_from_file_location('phase1_data',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def inside(x,z,ring):
    c=False;j=len(ring)-1
    for i,(xx,zz) in enumerate(ring):
        xj,zj=ring[j]
        if (zz>z)!=(zj>z) and x<(xj-xx)*(z-zz)/(zj-zz+1e-30)+xx:c=not c
        j=i
    return c
def inside_any(x,z,rings):return any(inside(x,z,r) for r in rings if len(r)>=3)
def dist_seg(px,pz,ax,az,bx,bz):
    dx,dz=bx-ax,bz-az;t=max(0,min(1,((px-ax)*dx+(pz-az)*dz)/(dx*dx+dz*dz+1e-12)));return math.hypot(px-ax-t*dx,pz-az-t*dz)
def area(r):return abs(sum(r[i][0]*r[(i+1)%len(r)][1]-r[(i+1)%len(r)][0]*r[i][1] for i in range(len(r)))/2) if len(r)>=3 else 0
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-root',default=r'C:\Users\hp\Desktop\KIBA-REAL-CITY');ap.add_argument('--output-root',default=str(Path(__file__).resolve().parent));ap.add_argument('--tree-spacing',type=float,default=6.2);a=ap.parse_args();src=Path(a.source_root);out=Path(a.output_root)
    helper=load_helper(src/'scripts/phase1/build_phase1_data.py');scene=json.loads((src/'data/processed/phase2b/phase2b_scene.json').read_text(encoding='utf-8'));nav=json.loads((src/'data/processed/phase2c/phase2c_navigation.json').read_text(encoding='utf-8'));bounds=scene['bounds'];t=scene['terrain'];nx,nz=t['width'],t['height'];dx,dz=t['gridSpacingMetres'];verts=t['vertices'];park_rings=[[(p[0],p[2]) for p in ring] for ring in scene['parkBoundary']]
    water=[[(p[0],p[2]) for p in f.get('points',[])] for f in scene['features'].get('water',[]) if len(f.get('points',[]))>=3];buildings=[[(p[0],p[2]) for p in f.get('points',[])] for f in scene['features'].get('buildings',[]) if len(f.get('points',[]))>=3]
    areas=[];point_features=[]
    for f in scene['features'].get('vegetation',[]):
        tags=f.get('tags',{});pts=f.get('points',[])
        if len(pts)>=3:
            ring=[(p[0],p[2]) for p in pts];kind='woodland' if tags.get('natural') in ('wood','scrub') or tags.get('landuse')=='forest' else 'lawn' if tags.get('landuse') in ('grass','meadow') else 'garden'
            areas.append({'osmId':str(f['id']),'tags':tags,'kind':kind,'areaSquareMetres':round(area(ring),1),'ringXZ':[[round(x,3),round(z,3)] for x,z in ring],'source':'osm_vegetation_area'})
        elif f.get('point'):
            point_features.append(f)
    # Road/nav collision clearance is spatially indexed in 8 m cells. The tested corridor covers the ribbon plus a 0.55 m vegetation setback.
    cell=8.0;road_bins=collections.defaultdict(list)
    for run in nav['runs']:
        for s in run['segments']:
            x0,z0=s['centerStart'][0],s['centerStart'][2];x1,z1=s['centerEnd'][0],s['centerEnd'][2];r=s['widthMetres']/2+.55
            item=(x0,z0,x1,z1,r,bool(run['bridge']))
            for ix in range(math.floor((min(x0,x1)-r)/cell),math.floor((max(x0,x1)+r)/cell)+1):
                for iz in range(math.floor((min(z0,z1)-r)/cell),math.floor((max(z0,z1)+r)/cell)+1):road_bins[(ix,iz)].append(item)
    def ground(x,z):
        ix=max(0,min(nx-1,round((x-bounds[0])/dx)));iz=max(0,min(nz-1,round((z-bounds[1])/dz)));return verts[iz*nx+ix][1]
    def excluded(x,z):
        if not inside_any(x,z,park_rings):return 'outside_park'
        if inside_any(x,z,water):return 'water'
        if inside_any(x,z,buildings):return 'building'
        for q in road_bins.get((math.floor(x/cell),math.floor(z/cell)),[]):
            if dist_seg(x,z,*q[:4])<q[4]:return 'path_bridge_or_navigation_clearance'
        return None
    # Record the exact tile geography and estimate usable photo overlap by sampling the mapped park at 3 m spacing.
    photo_root=src/'data/raw/gsi/seamlessphoto';photo_files=sorted(photo_root.rglob('*.jpg'));photo_cache={};photo_tiles=[];tile_stats={}
    for f in photo_files:
        zoom=int(f.parents[1].name);tx=int(f.parent.name);ty=int(f.stem);n=1<<zoom
        def lat(y):return math.degrees(math.atan(math.sinh(math.pi*(1-2*y/n))))
        corners=[helper.proj(lat(ty),tx/n*360-180),helper.proj(lat(ty),(tx+1)/n*360-180),helper.proj(lat(ty+1),(tx+1)/n*360-180),helper.proj(lat(ty+1),tx/n*360-180)]
        xs=[p[0] for p in corners];zs=[-p[1] for p in corners];tile_key=(zoom,tx,ty);tile_stats[tile_key]={'file':str(f.relative_to(src)).replace('\\','/'),'boundsLocalMetres':[round(min(xs),2),round(min(zs),2),round(max(xs),2),round(max(zs),2)],'widthPixels':Image.open(f).width,'heightPixels':Image.open(f).height,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
    for z in range(math.floor(bounds[1]),math.ceil(bounds[3]),3):
        for x in range(math.floor(bounds[0]),math.ceil(bounds[2]),3):
            if not inside_any(x,z,park_rings):continue
            lat,lon=helper.unproj(x,-z);n=1<<18;tx=int((lon+180)/360*n);ty=int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n)
            if (18,tx,ty) in tile_stats:tile_stats[(18,tx,ty)]['parkGridSamples']=tile_stats[(18,tx,ty)].get('parkGridSamples',0)+1
            tile_stats.setdefault('_counts',{'parkSamples':0,'coveredSamples':0});tile_stats['_counts']['parkSamples']+=1
            if (18,tx,ty) in tile_stats:tile_stats['_counts']['coveredSamples']+=1
    for k,v in list(tile_stats.items()):
        if k=='_counts':continue
        photo_tiles.append({'zoom':k[0],'x':k[1],'y':k[2],**v})
    def photo_green(x,z):
        lat,lon=helper.unproj(x,-z);zoom=18;n=1<<zoom;u=(lon+180)/360*n;v=(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n;tx,ty=int(u),int(v);f=photo_root/str(zoom)/str(tx)/f'{ty}.jpg'
        if not f.is_file():return None,None,None
        key=(tx,ty)
        if key not in photo_cache:photo_cache[key]=Image.open(f).convert('RGB').load()
        px=max(0,min(255,int((u-tx)*256)));py=max(0,min(255,int((v-ty)*256)));pix=photo_cache[key];green=0;total=0
        gs=[]
        for yy in range(max(0,py-5),min(256,py+6)):
            for xx in range(max(0,px-5),min(256,px+6)):
                r,g,b=pix[xx,yy];total+=1;green+=int(g>45 and g>r*1.08 and g>b*1.04 and g-r>9);gs.append(g)
        mean=sum(gs)/max(1,len(gs));stdev=math.sqrt(max(0,sum(q*q for q in gs)/max(1,len(gs))-mean*mean))
        return green/max(1,total),f'{zoom}/{tx}/{ty}',round(stdev,1)
    # OSM point trees keep their surveyed horizontal position; elevation is sampled from the existing Phase 2B render terrain.
    osm_path=src/'data/raw/osm/layers/vegetation/trees.osm';tree_root=ET.parse(osm_path).getroot();mapped=[];rejected=collections.Counter()
    for node in tree_root.findall('node'):
        tags={q.get('k'):q.get('v') for q in node.findall('tag')}
        if tags.get('natural')!='tree' or 'amenity' in tags:continue
        x,north=helper.proj(float(node.get('lat')),float(node.get('lon')));x,z=x,-north;why=excluded(x,z)
        if why:rejected[why]+=1;continue
        mapped.append({'id':node.get('id'),'source':'osm_mapped_tree','sourceAccuracy':'OSM point position; vertical placement uses Phase 2B terrain sample','x':round(x,3),'y':round(ground(x,z),3),'z':round(z,3),'variant':None,'scale':None,'color':None,'tags':tags})
    # Density is only inferred inside mapped wooded/garden polygons. The 14 photos verify canopy color only where their tile covers the polygon.
    estimated=[];accepted_bins=collections.defaultdict(list);photo_counts=collections.Counter();poly_stats=[];mapped_xy=[(q['x'],q['z']) for q in mapped]
    for area_rec in areas:
        ring=[tuple(p) for p in area_rec['ringXZ']];kind=area_rec['kind'];spacing=a.tree_spacing if kind=='woodland' else a.tree_spacing*1.55 if kind=='garden' else 0
        made=0
        if spacing:
            x0=min(p[0] for p in ring);x1=max(p[0] for p in ring);z0=min(p[1] for p in ring);z1=max(p[1] for p in ring);seed=int(hashlib.sha256(area_rec['osmId'].encode()).hexdigest()[:8],16);rng=random.Random(seed)
            iz=0;z=z0+spacing*.28
            while z<z1:
                ix=0;x=x0+spacing*.28
                while x<x1:
                    qx=x+(rng.random()-.5)*spacing*.72;qz=z+(rng.random()-.5)*spacing*.72
                    if inside(qx,qz,ring) and not excluded(qx,qz):
                        nearby=any(math.hypot(qx-ox,qz-oz)<3.2 for ox,oz in mapped_xy)
                        bx,bz=math.floor(qx/spacing),math.floor(qz/spacing)
                        for ax in range(bx-1,bx+2):
                            for az in range(bz-1,bz+2):
                                for ox,oz in accepted_bins[(ax,az)]:
                                    if math.hypot(qx-ox,qz-oz)<spacing*.72:nearby=True;break
                                if nearby:break
                            if nearby:break
                        if not nearby and rng.random()<.82:
                            pg,tile,_=photo_green(qx,qz)
                            if tile and (pg or 0)<.34:photo_counts['photo_non_green_rejected']+=1
                            else:
                                source='estimated_from_aerial_canopy' if tile else 'estimated_from_osm_vegetation_area'
                                kind2='garden' if kind=='garden' else 'woodland';rng2=random.Random(seed+ix*101+iz*701);variant=rng2.randrange(4);scale=round(rng2.uniform(.78,1.35) if kind2=='woodland' else rng2.uniform(.62,.95),3);color=['#477d4d','#538a50','#648f52','#397149'][rng2.randrange(4)]
                                rec={'id':f"est-{area_rec['osmId']}-{ix}-{iz}",'source':source,'sourceAccuracy':'estimated placement inside mapped vegetation area; aerial green test where available','polygonOsmId':area_rec['osmId'],'x':round(qx,3),'y':round(ground(qx,qz),3),'z':round(qz,3),'variant':variant,'scale':scale,'color':color,'aerialTile':tile,'aerialGreenFraction':round(pg,3) if pg is not None else None}
                                estimated.append(rec);accepted_bins[(math.floor(qx/spacing),math.floor(qz/spacing))].append((qx,qz));made+=1;photo_counts[source]+=1
                    ix+=1;x=x0+ix*spacing
                iz+=1;z=z0+iz*spacing
        poly_stats.append({'osmId':area_rec['osmId'],'kind':kind,'areaSquareMetres':area_rec['areaSquareMetres'],'estimatedTrees':made})
    # Photo-only estimates use green, textured canopy-like patches in the actual tile-covered park area.
    photo_step=3.8;photo_rng=random.Random(14273608);photo_xy=[(q['x'],q['z']) for q in mapped+estimated];aerial_added=0;z=bounds[1]+photo_step*.37;row=0
    while z<bounds[3]:
        x=bounds[0]+photo_step*.29;col=0
        while x<bounds[2]:
            qx=x+(photo_rng.random()-.5)*photo_step*.65;qz=z+(photo_rng.random()-.5)*photo_step*.65
            if inside_any(qx,qz,park_rings) and not excluded(qx,qz):
                pg,tile,texture=photo_green(qx,qz)
                if tile and pg>=.43 and texture>=11 and photo_rng.random()<.68 and all(math.hypot(qx-ox,qz-oz)>4.2 for ox,oz in photo_xy):
                    owner=next((ar['osmId'] for ar in areas if inside(qx,qz,[tuple(v) for v in ar['ringXZ']])),None)
                    scale=round(photo_rng.uniform(.68,1.2),3);variant=photo_rng.randrange(4);color=['#477d4d','#538a50','#648f52','#397149'][photo_rng.randrange(4)]
                    estimated.append({'id':f'aerial-{row}-{col}','source':'estimated_from_aerial_canopy','sourceAccuracy':'synthetic tree center inferred from green textured aerial-photo neighborhood; not a mapped tree','polygonOsmId':owner,'x':round(qx,3),'y':round(ground(qx,qz),3),'z':round(qz,3),'variant':variant,'scale':scale,'color':color,'aerialTile':tile,'aerialGreenFraction':round(pg,3),'aerialGreenTextureStdDev':texture})
                    photo_xy.append((qx,qz));aerial_added+=1;photo_counts['estimated_from_aerial_canopy']+=1
            col+=1;x=bounds[0]+col*photo_step
        row+=1;z=bounds[1]+row*photo_step
    # Keep mapped tree instances distinguishable, but make their visual variation deterministic and non-uniform.
    for rec in mapped:
        seed=int(rec['id'])%100000;rr=random.Random(seed);rec['variant']=rr.randrange(4);rec['scale']=round(rr.uniform(.82,1.22),3);rec['color']=['#2775a5','#3887af','#4e96b9','#316887'][rr.randrange(4)]
    shrubs=[];grass_tufts=[]
    for area_rec in areas:
        ring=[tuple(p) for p in area_rec['ringXZ']];kind=area_rec['kind'];spacing=2.8 if kind in ('woodland','garden') else 1.35 if kind=='lawn' else 0
        if not spacing:continue
        x0=min(p[0] for p in ring);x1=max(p[0] for p in ring);z0=min(p[1] for p in ring);z1=max(p[1] for p in ring);seed=int(hashlib.sha256(('detail'+area_rec['osmId']).encode()).hexdigest()[:8],16);rng=random.Random(seed);iz=0;z=z0
        while z<z1:
            ix=0;x=x0
            while x<x1:
                qx=x+(rng.random()-.5)*spacing*.8;qz=z+(rng.random()-.5)*spacing*.8
                if inside(qx,qz,ring) and not excluded(qx,qz):
                    if kind=='lawn' and rng.random()<.43:
                        rr=random.Random(seed+ix*19+iz*991);grass_tufts.append({'x':round(qx,3),'y':round(ground(qx,qz),3),'z':round(qz,3),'scale':round(rr.uniform(.65,1.35),2),'color':['#91ad60','#a3b76c','#789e56'][rr.randrange(3)]})
                    elif kind in ('woodland','garden') and rng.random()<.19 and all(math.hypot(qx-q['x'],qz-q['z'])>2.4 for q in mapped+estimated):
                        rr=random.Random(seed+ix*37+iz*1117);shrubs.append({'x':round(qx,3),'y':round(ground(qx,qz),3),'z':round(qz,3),'scale':round(rr.uniform(.55,1.05),2),'color':['#3d7449','#52834e','#688c51'][rr.randrange(3)],'source':'estimated_from_osm_vegetation_area'})
                ix+=1;x=x0+ix*spacing
            iz+=1;z=z0+iz*spacing
    imagery={'tileCount':len(photo_tiles),'zoom':18,'tileSizePixels':256,'tiles':photo_tiles,'parkCoverageGridStepMetres':3,'parkGridSamples':tile_stats.get('_counts',{}).get('parkSamples',0),'coveredParkGridSamples':tile_stats.get('_counts',{}).get('coveredSamples',0),'coveredParkPercent':round(100*tile_stats.get('_counts',{}).get('coveredSamples',0)/max(1,tile_stats.get('_counts',{}).get('parkSamples',0)),2),'treePointCoverageCount':sum(1 for q in mapped if q.get('aerialTile')),'photoOnlyTreeEstimates':aerial_added}
    tree_points=mapped+estimated;tree_bins=collections.defaultdict(list);spawn_cell=10.0
    for q in tree_points:tree_bins[(math.floor(q['x']/spawn_cell),math.floor(q['z']/spawn_cell))].append(q)
    scenic=None;scenic_score=1e9
    for run in nav['runs']:
        for s in run['segments']:
            if s['status']!='walkable':continue
            x=(s['centerStart'][0]+s['centerEnd'][0])/2;z=(s['centerStart'][2]+s['centerEnd'][2])/2;y=(s['centerStart'][1]+s['centerEnd'][1])/2
            bx,bz=math.floor(x/spawn_cell),math.floor(z/spawn_cell)
            nearby=[q for ix in range(bx-2,bx+3) for iz in range(bz-2,bz+3) for q in tree_bins[(ix,iz)]]
            if not nearby:continue
            nearest=min(nearby,key=lambda q:math.hypot(x-q['x'],z-q['z']));d=math.hypot(x-nearest['x'],z-nearest['z'])
            if 6<=d<=18 and abs(d-8)<scenic_score:scenic_score=abs(d-8);scenic={'position':[round(x,3),round(y,3),round(z,3)],'heading':round(math.atan2(-(nearest['x']-x),-(nearest['z']-z)),4),'wayId':run['id'],'run':run['run'],'nearestTreeId':nearest['id'],'nearestTreeSource':nearest['source'],'nearestTreeDistanceMetres':round(d,2),'status':'walkable'}
    tree_data={'coordinateSystem':'EPSG:6677 local metres, Three.js (x=easting,y=height,z=-northing)','heightBasis':'Phase 2B terrain sample','sourceCounts':{'phase2bVegetationFeatures':len(scene['features'].get('vegetation',[])),'rawOsmNaturalTreePoints':sum(1 for n in tree_root.findall('node') if any(q.get('k')=='natural' and q.get('v')=='tree' for q in n.findall('tag')) and not any(q.get('k')=='amenity' for q in n.findall('tag'))),'mappedTreesUsed':len(mapped),'osmVegetationAreasUsed':len(areas),'estimatedTrees':len(estimated),'estimatedShrubs':len(shrubs),'grassTufts':len(grass_tufts)},'mappedTrees':mapped,'estimatedTrees':estimated,'estimatedShrubs':shrubs,'grassTufts':grass_tufts,'vegetationAreas':areas,'photoCoverage':imagery,'photoCanopyCounts':dict(photo_counts),'excludedMappedTrees':dict(rejected),'polygonPlacementStats':poly_stats,'scenicSpawn':scenic,'placementExclusions':['Phase 2C navigation ribbon + 0.55 m clearance (includes paths and bridges)','water polygons','buildings','park boundary outside','existing mapped tree radius via local spacing'],'lod':{'nearMetres':180,'farMetres':520,'beyondMetres':'hidden','instanceVariants':4,'treeGeometry':'low-poly instanced tree variants; two LOD meshes per variant'},'attribution':{'osm':'© OpenStreetMap contributors, ODbL 1.0','imagery':'Geospatial imagery from GSI seamlessphoto tiles already present in raw data'}}
    report={'sourcePhase2b':'data/processed/phase2b/phase2b_scene.json','sourcePhase2c':'data/processed/phase2c/phase2c_navigation.json','rawInputsModified':False,'phase2cMovementLogicCopiedToSeparateViewer':True,'vegetation':tree_data['sourceCounts'],'treePointSources':{'measuredOSM':'mappedTrees list; horizontal position from OSM node, y sampled from existing DEM mesh','estimatedAerial':'estimatedTrees with source=estimated_from_aerial_canopy; placed only where an existing aerial tile covers the park and a green, textured pixel neighborhood passes the canopy-likelihood screen','estimatedArea':'estimatedTrees with source=estimated_from_osm_vegetation_area; placement is synthetic within mapped OSM woodland polygons, not a measured tree'},'photoCoverage':imagery,'placement':{'spacingTargetMetres':a.tree_spacing,'osmTreeRejections':dict(rejected),'photoCanopyCounts':dict(photo_counts),'polygons':poly_stats},'render':{'terrainChanged':False,'movementLayerChanged':False,'treeInstancesInstanced':True,'nearLodMetres':180,'farLodMetres':520,'drawCallsAddedExpected':12,'viewDistanceCulling':True},'limitations':['Aerial tiles cover only a sampled fraction of the park; OSM-area placements elsewhere are synthetic, not photo-observed.','OSM tree points provide horizontal positions; height/species/crown dimensions are approximations.','Canopy screening uses a green-pixel and local texture heuristic, not a trained tree detector.']}
    (out/'data/processed/phase2d').mkdir(parents=True,exist_ok=True);(out/'reports/phase2d').mkdir(parents=True,exist_ok=True)
    (out/'data/processed/phase2d/phase2d_vegetation.json').write_text(json.dumps(tree_data,separators=(',',':'),ensure_ascii=False),encoding='utf-8');(out/'reports/phase2d/phase2d_source_analysis.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8');print(json.dumps({'vegetation':tree_data['sourceCounts'],'photoCoverage':{k:v for k,v in imagery.items() if k!='tiles'},'placement':report['placement']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
