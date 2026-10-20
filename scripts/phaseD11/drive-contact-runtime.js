let driveSupportTriangles=[],driveLastFit=null;
const DRIVE_CONTACT_LIFT=.012;
function prepareDriveSupportSurface(){
 const road=(phaseData?.roads||[]).find(r=>String(r.id)===String(driveCourse.wayId));
 if(!road)throw new Error('A course OSM surface missing');
 const vertices=[];for(const s of road.stations)vertices.push(s.slice(0,3),s.slice(3,6));
 driveSupportTriangles=[];for(let i=0;i<road.indices.length;i+=3){const a=vertices[road.indices[i]],b=vertices[road.indices[i+1]],c=vertices[road.indices[i+2]];driveSupportTriangles.push({a,b,c,minX:Math.min(a[0],b[0],c[0]),maxX:Math.max(a[0],b[0],c[0]),minZ:Math.min(a[2],b[2],c[2]),maxZ:Math.max(a[2],b[2],c[2])})}
 if(!driveSupportTriangles.length)throw new Error('A course support surface has no triangles');
}
function triangleHeight(tri,x,z){
 const [x1,y1,z1]=tri.a,[x2,y2,z2]=tri.b,[x3,y3,z3]=tri.c;const d=(z2-z3)*(x1-x3)+(x3-x2)*(z1-z3);if(Math.abs(d)<1e-10)return null;
 const a=((z2-z3)*(x-x3)+(x3-x2)*(z-z3))/d,b=((z3-z1)*(x-x3)+(x1-x3)*(z-z3))/d,c=1-a-b;return Math.min(a,b,c)>=-1e-6?a*y1+b*y2+c*y3:null;
}
function driveSurfaceHeight(x,z){
 for(const t of driveSupportTriangles){if(x<t.minX-1e-5||x>t.maxX+1e-5||z<t.minZ-1e-5||z>t.maxZ+1e-5)continue;const y=triangleHeight(t,x,z);if(y!==null)return{y,source:'Aコース路面メッシュ'}}
 const y=groundY(x,z);return Number.isFinite(y)?{y,source:'DEM地形メッシュ'}:null;
}
function fitBusToWheelSurfaces(x,z,heading){
 if(!bus?.userData?.wheelContacts)return{ok:false,reason:'GLB車輪接地点データなし'};
 const src=bus.userData.wheelContacts,names=['FL','FR','RL','RR'],fx=Math.sin(heading),fz=Math.cos(heading),rx=Math.cos(heading),rz=-Math.sin(heading),contacts=[];
 for(const name of names){const p=src[name];if(!p)return{ok:false,reason:'GLB '+name+'接地点なし'};if(![p.x,p.y,p.z].every(Number.isFinite))return{ok:false,reason:'GLB '+name+'接地点が非数値: '+JSON.stringify(p)};const wx=x+rx*p.x+fx*p.z,wz=z+rz*p.x+fz*p.z,s=driveSurfaceHeight(wx,wz),dem=groundY(wx,wz);if(!s||!Number.isFinite(s.y)||!Number.isFinite(dem))return{ok:false,reason:name+'路面標高なし'};contacts.push({name,local:p,worldX:wx,worldZ:wz,surfaceY:s.y,terrainY:dem,source:s.source})}
 const left=contacts.filter(c=>c.name.endsWith('L')),right=contacts.filter(c=>c.name.endsWith('R')),front=contacts.filter(c=>c.name.startsWith('F')),rear=contacts.filter(c=>c.name.startsWith('R'));
 const mean=a=>a.reduce((s,v)=>s+v,0)/a.length,avg=(arr,key)=>mean(arr.map(c=>key.includes('.')?key.split('.').reduce((o,k)=>o?.[k],c):c[key])),dx=avg(right,'local.x')-avg(left,'local.x'),dz=avg(front,'local.z')-avg(rear,'local.z');if(!Number.isFinite(dx)||!Number.isFinite(dz)||Math.abs(dx)<.1||Math.abs(dz)<.1)return{ok:false,reason:'GLB車軸配置不整合'};
 const slopeRight=(avg(right,'surfaceY')-avg(left,'surfaceY'))/dx,slopeForward=(avg(front,'surfaceY')-avg(rear,'surfaceY'))/dz;
 const forward=new THREE.Vector3(fx,slopeForward,fz).normalize();let rightVec=new THREE.Vector3(rx,slopeRight,rz);rightVec.addScaledVector(forward,-rightVec.dot(forward)).normalize();const up=new THREE.Vector3().crossVectors(forward,rightVec).normalize();
 const basis=new THREE.Matrix4().makeBasis(rightVec,up,forward),quat=new THREE.Quaternion().setFromRotationMatrix(basis),baseYs=contacts.map(c=>c.surfaceY-(rightVec.y*c.local.x+up.y*c.local.y+forward.y*c.local.z)),baseY=mean(baseYs)+DRIVE_CONTACT_LIFT;bus.position.set(x,baseY,z);bus.quaternion.copy(quat);
 for(const c of contacts){const lp=new THREE.Vector3(c.local.x,c.local.y,c.local.z).applyQuaternion(quat);c.bodyContactY=baseY+lp.y;c.gapMetres=c.bodyContactY-c.surfaceY;c.demDeltaMetres=c.bodyContactY-c.terrainY}
 const gaps=contacts.map(c=>c.gapMetres);driveLastFit={contacts,slopeRight,slopeForward,baseY,minGap:Math.min(...gaps),maxGap:Math.max(...gaps),maxAbsGap:Math.max(...gaps.map(Math.abs))};updateDriveContactHud();return{ok:true,fit:driveLastFit};
}
function updateDriveContactHud(){const el=$('#contactDebug');if(!el)return;if(!driveLastFit||!Number.isFinite(driveLastFit.maxAbsGap)){el.textContent='GLB '+JSON.stringify(bus?.userData?.wheelContacts||null)+' | Fit '+JSON.stringify({slopeRight:driveLastFit?.slopeRight,slopeForward:driveLastFit?.slopeForward,baseY:driveLastFit?.baseY,contacts:driveLastFit?.contacts?.map(c=>({name:c.name,local:c.local,surfaceY:c.surfaceY,terrainY:c.terrainY,gap:c.gapMetres}))});return}const c=driveLastFit.contacts;el.textContent=c.map(p=>`${p.name} ${p.gapMetres>=0?'+':''}${(p.gapMetres*100).toFixed(1)}cm (DEM ${(p.demDeltaMetres*100).toFixed(1)}cm)`).join(' · ')+' | pitch '+(Math.atan(driveLastFit.slopeForward)*180/Math.PI).toFixed(1)+'° roll '+(Math.atan(driveLastFit.slopeRight)*180/Math.PI).toFixed(1)+'°';}
