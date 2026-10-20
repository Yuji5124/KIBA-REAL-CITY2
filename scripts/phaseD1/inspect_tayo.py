"""Read-only inspection/export for Tayo_bus.blend. Never saves the source blend."""
import bpy, json, sys, hashlib, os
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
src, report_path, glb_path = argv
scene = bpy.context.scene
objects=[]
points=[]
mesh_objs=[]
depsgraph=bpy.context.evaluated_depsgraph_get()
for obj in scene.objects:
    if obj.type != 'MESH' or obj.hide_render or obj.name.startswith(('Ground','Road')):
        continue
    mesh_objs.append(obj)
    deps = obj.evaluated_get(depsgraph)
    mesh = deps.to_mesh()
    for v in mesh.vertices:
        points.append(deps.matrix_world @ v.co)
    deps.to_mesh_clear()
    objects.append({"name":obj.name,"vertices":len(obj.data.vertices),"location":list(obj.location),"rotationEulerRadians":list(obj.rotation_euler),"scale":list(obj.scale)})
if not points:
    raise RuntimeError("No visible mesh geometry found")
mins=[min(p[i] for p in points) for i in range(3)]
maxs=[max(p[i] for p in points) for i in range(3)]
dims=[maxs[i]-mins[i] for i in range(3)]
center=[(maxs[i]+mins[i])/2 for i in range(3)]
long_axis=max(range(3), key=lambda i:dims[i])
wheel_objs=[o for o in scene.objects if any(k in o.name.lower() for k in ('wheel','tire','tyre','tire','バ'))]
wheel_centers=[]
for o in wheel_objs:
    corners=[o.matrix_world @ Vector(c) for c in o.bound_box]
    c=[sum(v[i] for v in corners)/8 for i in range(3)]
    wheel_centers.append({"name":o.name,"centerWorld":c,"dimensionsWorld":[max(v[i] for v in corners)-min(v[i] for v in corners) for i in range(3)]})
front=max((o for o in mesh_objs if o.name=='Windshield'), key=lambda o:o.location.y, default=None)
wheel_by_name={w['name']:w for w in wheel_centers}
front_axles=[wheel_by_name[n]['centerWorld'] for n in ('Wheel_FL','Wheel_FR') if n in wheel_by_name]
rear_axles=[wheel_by_name[n]['centerWorld'] for n in ('Wheel_RL','Wheel_RR') if n in wheel_by_name]
axle_centers=[[sum(v[i] for v in axle)/len(axle) for i in range(3)] for axle in (front_axles,rear_axles) if axle]
wheelbase=(sum((axle_centers[0][i]-axle_centers[1][i])**2 for i in (0,1,2))**.5) if len(axle_centers)==2 else None
report={"source":os.path.abspath(src),"readOnly":True,"sourceSha256":hashlib.sha256(open(src,'rb').read()).hexdigest(),"blenderVersion":bpy.app.version_string,"sceneUnitSystem":scene.unit_settings.system,"scaleLength":scene.unit_settings.scale_length,"meshObjectCount":len(mesh_objs),"objectNames":[o['name'] for o in objects],"worldBoundsMin":mins,"worldBoundsMax":maxs,"worldDimensionsXYZ":dims,"worldCenter":center,"longestWorldAxisIndexXYZ":long_axis,"forwardAxis":"-Y (observed Windshield at negative Y; rear panel at positive Y)","wheelCandidates":wheel_centers,"frontAxleCenterWorld":axle_centers[0] if axle_centers else None,"rearAxleCenterWorld":axle_centers[1] if len(axle_centers)>1 else None,"wheelbaseMetres":wheelbase,"trackWidthBetweenWheelCentersMetres":abs(front_axles[0][0]-front_axles[1][0]) if len(front_axles)==2 else None,"warnings":["Dimensions exclude display road/ground meshes named Ground* or Road*.","Wheelbase measured from mesh bounding-box centers; steering angle/radius is not authored and must be conservatively tested.","Bounding box includes mirrors; separate body-only dimensions need a production clearance margin."]}
os.makedirs(os.path.dirname(report_path),exist_ok=True)
with open(report_path,'w',encoding='utf-8') as f: json.dump(report,f,ensure_ascii=False,indent=2)
bpy.ops.object.select_all(action='DESELECT')
for o in mesh_objs: o.select_set(True)
bpy.context.view_layer.objects.active=mesh_objs[0]
os.makedirs(os.path.dirname(glb_path),exist_ok=True)
bpy.ops.export_scene.gltf(filepath=glb_path,export_format='GLB',use_selection=True,export_apply=False)
print('KIBA_D1_REPORT='+report_path)
print('KIBA_D1_GLB='+glb_path)
