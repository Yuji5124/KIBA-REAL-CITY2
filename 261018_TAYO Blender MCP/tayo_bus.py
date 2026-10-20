"""青いバス（タヨ風）を生成するスクリプト。tayo_refs の参考画像をもとに寸法・色を決めている。
Blender MCP の execute_blender_code（または Blender のテキストエディタ）で実行する。
現在のシーンのオブジェクトは全て削除され、Tayo_bus.blend として保存される。

操作方法: オブジェクト "Tayo_Root" のカスタムプロパティ
  smile      : 0→1 で笑顔（黒目が◠になり、口が大きく開き、眉が上がる）
  blink      : 0→1 でまばたき
  steer      : 前輪のハンドル角
  wheel_spin : タイヤの追加回転
  Tayo_Root を Y 方向へ動かすとタイヤが自動で転がる（前方は -Y）
  Tayo_Body を回転/移動すると車体だけが揺れる（サスペンション表現）
"""
import bpy, bmesh, math, os
from mathutils import Matrix, Vector

OUT_DIR = r"C:\Users\hp\Desktop\Blender MCP"
FRONT, REAR = -2.1, 2.1          # 車体の前後端（前方は -Y）
K = 0.1                          # フロント面の丸み（左右端ほど後退）
WHEEL_R = 0.46
EYE_Z = 1.03


def fy(x):
    """フロント面の y 座標"""
    return FRONT + K * x * x


# ---------- シーン初期化（アドオンを止めないよう factory reset はしない） ----------
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.curves, bpy.data.lights,
             bpy.data.cameras, bpy.data.actions, bpy.data.collections):
    for d in list(coll):
        if d.users == 0 or coll is bpy.data.collections:
            coll.remove(d)
scene = bpy.context.scene
col = bpy.data.collections.new("Tayo")
scene.collection.children.link(col)


def link(obj):
    col.objects.link(obj)
    return obj


# ---------- コントロール ----------
root = link(bpy.data.objects.new("Tayo_Root", None))
root.empty_display_type = "ARROWS"
root.empty_display_size = 1.5
for key, val, lo, hi, sub in [("smile", 0.0, 0.0, 1.0, "FACTOR"),
                              ("blink", 0.0, 0.0, 1.0, "FACTOR"),
                              ("steer", 0.0, -0.6, 0.6, "ANGLE"),
                              ("wheel_spin", 0.0, -100.0, 100.0, "ANGLE")]:
    root[key] = val
    root.id_properties_ui(key).update(min=lo, max=hi, soft_min=lo, soft_max=hi, subtype=sub)
BODY = link(bpy.data.objects.new("Tayo_Body", None))
BODY.empty_display_type = "CUBE"
BODY.empty_display_size = 0.2
BODY.parent = root
_D = object()  # 親の既定値 = BODY


# ---------- マテリアル ----------
def mat(name, color, rough=0.4, metal=0.0, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    if emit:
        p.inputs["Emission Color"].default_value = (*color, 1)
        p.inputs["Emission Strength"].default_value = emit
    return m


def grille_mat():
    m = bpy.data.materials.new("Grille")
    m.use_nodes = True
    nt = m.node_tree
    p = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    p.inputs["Metallic"].default_value = 0.8
    p.inputs["Roughness"].default_value = 0.3
    tc = nt.nodes.new("ShaderNodeTexCoord")
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.bands_direction = "Z"
    wave.inputs["Scale"].default_value = 7.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].color = (0.02, 0.025, 0.035, 1)
    ramp.color_ramp.elements[1].position = 0.78
    ramp.color_ramp.elements[1].color = (0.8, 0.82, 0.86, 1)
    nt.links.new(tc.outputs["Object"], wave.inputs["Vector"])
    nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], p.inputs["Base Color"])
    return m


M = {
    "blue": mat("Tayo_Blue", (0.085, 0.50, 0.90), 0.3),
    "blue_dark": mat("Tayo_Blue_Dark", (0.03, 0.22, 0.6), 0.4),
    "glass": mat("Glass", (0.024, 0.05, 0.11), 0.12),
    "pillar": mat("Glass_Divider", (0.05, 0.09, 0.18), 0.3),
    "bumper": mat("Bumper", (0.035, 0.038, 0.045), 0.5),
    "black": mat("Black", (0.01, 0.01, 0.012), 0.3),
    "brow": mat("Brow", (0.03, 0.035, 0.045), 0.4),
    "tire": mat("Tire", (0.02, 0.02, 0.022), 0.8),
    "chrome": mat("Chrome", (0.8, 0.82, 0.85), 0.18, 1.0),
    "white": mat("White", (0.95, 0.95, 0.95), 0.25),
    "sign": mat("Sign_White", (0.9, 0.93, 0.95), 0.4, 0, 0.5),
    "signblue": mat("Sign_Blue", (0.25, 0.8, 1.0), 0.3, 0, 0.6),
    "amber": mat("Amber", (1.0, 0.45, 0.02), 0.3, 0, 0.6),
    "red": mat("Red", (0.8, 0.02, 0.02), 0.3, 0, 0.6),
    "lamp": mat("Lamp_White", (0.95, 0.95, 0.9), 0.2, 0, 0.8),
    "navy": mat("Navy", (0.01, 0.025, 0.09), 0.4),
    "plate": mat("Plate_Blue", (0.04, 0.28, 0.8), 0.4),
    "asphalt": mat("Asphalt", (0.09, 0.09, 0.1), 0.9),
    "grass": mat("Ground", (0.3, 0.42, 0.25), 0.9),
    "line": mat("Road_Line", (0.9, 0.9, 0.85), 0.6),
    "grille": grille_mat(),
}


# ---------- ジオメトリ用ヘルパー ----------
def mesh_obj(name, bm, material=None, parent=_D, loc=(0, 0, 0)):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = link(bpy.data.objects.new(name, me))
    for mm in (material if isinstance(material, list) else [material] if material else []):
        me.materials.append(mm)
    obj.location = loc
    obj.parent = BODY if parent is _D else parent
    return obj


def smooth(obj, angle=40):
    obj.data.shade_smooth()
    obj.data.set_sharp_from_angle(angle=math.radians(angle))


def apply_mods(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    old = obj.data
    obj.modifiers.clear()
    obj.data = me
    bpy.data.meshes.remove(old)


def bend(obj, falloff=None):
    """フロント面の丸みに合わせて頂点を後退させる（親が原点・無回転の前提）"""
    ox, oy = obj.location.x, obj.location.y
    for v in obj.data.vertices:
        x = v.co.x + ox
        w = 1.0
        if falloff is not None:
            w = max(0.0, min(1.0, (falloff - (v.co.y + oy)) / (falloff - FRONT)))
        v.co.y += K * x * x * w


def box(name, center, size, material, bevel=0.0, parent=_D, segs=3, nx=0, rot=None, curved=False):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Diagonal((*size, 1)))
    if nx:
        edges = [e for e in bm.edges if abs(e.verts[0].co.x - e.verts[1].co.x) > 1e-6]
        bmesh.ops.subdivide_edges(bm, edges=edges, cuts=nx, use_grid_fill=True)
    obj = mesh_obj(name, bm, material, parent, center)
    if rot:
        obj.rotation_euler = [math.radians(a) for a in rot]
    if curved:
        bend(obj)
    if bevel:
        b = obj.modifiers.new("Bevel", "BEVEL")
        b.width = bevel
        b.segments = segs
        b.limit_method = "ANGLE"
        smooth(obj)
    return obj


def front_box(name, cx, cz, w, h, depth, proud, material, bevel=0.0):
    """フロント面に貼り付く板。proud = 車体前面からの出っ張り"""
    return box(name, (cx, FRONT - proud + depth / 2, cz), (w, depth, h), material,
               bevel, nx=max(2, int(w * 10)), curved=True)


def cyl(name, center, r, depth, material, axis="Y", parent=_D, segs=32, rot_z=0.0):
    rot = {"X": Matrix.Rotation(math.pi / 2, 4, "Y"),
           "Y": Matrix.Rotation(math.pi / 2, 4, "X"),
           "Z": Matrix.Identity(4)}[axis]
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                          radius1=r, radius2=r, depth=depth, matrix=rot)
    obj = mesh_obj(name, bm, material, parent, center)
    obj.rotation_euler.z = rot_z
    smooth(obj, 50)
    return obj


def ellipsoid(name, center, scale, material, parent=_D, rot_z=0.0):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=1.0,
                              matrix=Matrix.Diagonal((*scale, 1)))
    obj = mesh_obj(name, bm, material, parent, center)
    obj.rotation_euler.z = rot_z
    obj.data.shade_smooth()
    return obj


def rod(name, p0, p1, r, material, parent=_D):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    rot = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=r, radius2=r,
                          depth=d.length, matrix=rot)
    obj = mesh_obj(name, bm, material, parent, (p0 + p1) / 2)
    smooth(obj, 60)
    return obj


def text(name, body, loc, rot, size, material, parent=_D):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.extrude = 0.004
    obj = link(bpy.data.objects.new(name, cu))
    obj.data.materials.append(material)
    obj.location = loc
    obj.rotation_euler = [math.radians(a) for a in rot]
    obj.parent = BODY if parent is _D else parent
    return obj


def add_driver(owner, path, expr, vars, index=-1):
    fc = owner.driver_add(path, index) if index >= 0 else owner.driver_add(path)
    drv = fc.driver
    drv.type = "SCRIPTED"
    for vname, kind, data in vars:
        v = drv.variables.new()
        v.name = vname
        if kind == "PROP":
            v.type = "SINGLE_PROP"
            v.targets[0].id_type = "OBJECT"
            v.targets[0].id = root
            v.targets[0].data_path = data
        else:
            v.type = "TRANSFORMS"
            v.targets[0].id = root
            v.targets[0].transform_type = data
            v.targets[0].transform_space = "WORLD_SPACE"
    drv.expression = expr


def shape_keys(obj, funcs):
    """funcs: {プロパティ名: f(index, Vector)->Vector}。root の同名プロパティで駆動"""
    if not obj.data.shape_keys:
        obj.shape_key_add(name="Basis")
    for name, f in funcs.items():
        sk = obj.shape_key_add(name=name.capitalize(), from_mix=False)
        for i, v in enumerate(sk.data):
            v.co = f(i, v.co.copy())
        add_driver(sk, "value", "v", [("v", "PROP", f'["{name}"]')])


class Geo:
    """複数パーツを1メッシュにまとめる（パーツごとの頂点範囲を記録）"""

    def __init__(self):
        self.v, self.f, self.m, self.groups = [], [], [], {}

    def add(self, name, verts, faces, mi):
        o = len(self.v)
        self.v += [Vector(v) for v in verts]
        self.f += [tuple(i + o for i in f) for f in faces]
        self.m += [mi] * len(faces)
        self.groups[name] = range(o, len(self.v))

    def sphere(self, name, scale, off, mi, nu=32, nv=16):
        verts, faces = [], []
        for j in range(nv + 1):
            th = math.pi * j / nv
            for i in range(nu):
                ph = 2 * math.pi * i / nu
                verts.append((off[0] + scale[0] * math.sin(th) * math.cos(ph),
                              off[1] + scale[1] * math.sin(th) * math.sin(ph),
                              off[2] + scale[2] * math.cos(th)))
        for j in range(nv):
            for i in range(nu):
                a, b = j * nu + i, j * nu + (i + 1) % nu
                faces.append((a, b, b + nu, a + nu))
        self.add(name, verts, faces, mi)

    def tube(self, name, pts, r, mi, m=8):
        verts, faces = [], []
        for k, p in enumerate(pts):
            t = (pts[min(k + 1, len(pts) - 1)] - pts[max(k - 1, 0)]).normalized()
            b = Vector((0, 1, 0))
            n = t.cross(b).normalized()
            for i in range(m):
                a = 2 * math.pi * i / m
                verts.append(p + r * (math.cos(a) * n + math.sin(a) * b))
        for k in range(len(pts) - 1):
            for i in range(m):
                a, c = k * m + i, k * m + (i + 1) % m
                faces.append((a, c, c + m, a + m))
        self.add(name, verts, faces, mi)

    def build(self, name, mats, loc, rot_z=0.0):
        me = bpy.data.meshes.new(name)
        me.from_pydata([v.to_tuple() for v in self.v], [], self.f)
        for p, mi in zip(me.polygons, self.m):
            p.material_index = mi
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        obj = link(bpy.data.objects.new(name, me))
        for mm in mats:
            me.materials.append(mm)
        me.shade_smooth()
        obj.location = loc
        obj.rotation_euler.z = rot_z
        obj.parent = BODY
        return obj


# ---------- ボディ ----------
body = box("Body", (0, 0, 1.375), (2.0, 4.2, 2.15), M["blue"], bevel=0.16, segs=6, nx=16)
apply_mods(body)
bend(body, falloff=FRONT + 0.9)
for wy in (-1.25, 1.15):
    cutter = cyl("cutter", (0, wy, WHEEL_R), 0.58, 3.0, None, axis="X", parent=None)
    bo = body.modifiers.new("Arch", "BOOLEAN")
    bo.object = cutter
    bo.solver = "EXACT"
    apply_mods(body)
    bpy.data.objects.remove(cutter)
smooth(body, 35)

# フロント：ガラス・行先表示
front_box("Windshield", 0, 1.765, 1.74, 0.91, 0.03, 0.015, M["glass"], 0.04)
front_box("SignBox", 0, 2.33, 1.74, 0.2, 0.25, 0.03, M["black"], 0.03)
text("Sign_120", "120", (-0.37, fy(-0.37) - 0.036, 2.33), (90, 0, 0), 0.17, M["sign"])
front_box("SignPanel", 0.27, 2.33, 0.72, 0.17, 0.01, 0.036, M["sign"], 0.015)
for i, cx in enumerate((0.03, 0.27, 0.51)):
    cyl(f"SignDot_{i}", (cx, fy(cx) - 0.04, 2.33), 0.068, 0.008, M["signblue"], "Y", rot_z=math.atan(2 * K * cx))
    if i != 1:
        cyl(f"SignDotIn_{i}", (cx, fy(cx) - 0.044, 2.33), 0.055, 0.006, M["sign"], "Y", rot_z=math.atan(2 * K * cx))

# 屋根のエアコン
box("RoofAC", (0, -1.05, 2.565), (0.98, 1.6, 0.26), M["blue"], 0.09)
for i in range(7):
    box(f"Vent_{i}", (-0.33 + i * 0.11, -1.851, 2.58), (0.035, 0.02, 0.15), M["navy"], 0.012)
for s in (-1, 1):
    for i in range(10):
        box(f"ACSideVent_{s:+d}_{i}", (s * 0.491, -1.15 + i * 0.07, 2.58), (0.02, 0.025, 0.11), M["blue_dark"], 0.008)

# バンパー（中央が下がった笑顔型、両端は回り込む）
bm = bmesh.new()
cols = []
N = 33
for i in range(N):
    x = -1.04 + 2.08 * i / (N - 1)
    zt = 0.48 + 0.17 * x * x
    back = 0.9 * max(0.0, abs(x) - 0.85) ** 1.5
    yf, yb = fy(x) - 0.09 + back, fy(x) + 0.32
    cols.append([bm.verts.new(p) for p in ((x, yf, 0.12), (x, yf, zt), (x, yb, zt), (x, yb, 0.12))])
for a, b in zip(cols, cols[1:]):
    for k in range(4):
        bm.faces.new((a[k], b[k], b[(k + 1) % 4], a[(k + 1) % 4]))
bm.faces.new(cols[0][::-1])
bm.faces.new(cols[-1])
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bumper = mesh_obj("Bumper", bm, M["bumper"])
bb = bumper.modifiers.new("Bevel", "BEVEL")
bb.width, bb.segments, bb.limit_method = 0.05, 3, "ANGLE"
smooth(bumper)
for s in (-1, 1):
    x = s * 0.72
    zt = 0.48 + 0.17 * x * x
    box(f"Indicator_{s:+d}", (x, fy(x) - 0.012, zt + 0.045), (0.42, 0.03, 0.065), M["amber"], 0.02,
        rot=(0, -s * math.degrees(math.atan(0.34 * 0.72)), math.degrees(math.atan(2 * K * x))))
    cyl(f"BumperLight_{s:+d}", (s * 0.69, fy(s * 0.69) - 0.1, 0.27), 0.03, 0.02, M["lamp"], "Y")

# ---------- 側面 ----------
for s in (-1, 1):
    xs = s * 1.0
    box(f"SideGlass_{s:+d}", (xs, 0.18, 1.86), (0.03, 3.4, 0.8), M["glass"], 0.03)
    box(f"SideGlassFront_{s:+d}", (xs, -1.71, 1.86), (0.03, 0.18, 0.8), M["glass"], 0.03)
    for i, y in enumerate((-0.85, -0.15, 0.55, 1.25)):
        box(f"SideDivider_{s:+d}_{i}", (s * 1.008, y, 1.86), (0.03, 0.025, 0.8), M["pillar"])
    box(f"SideDividerH_{s:+d}", (s * 1.008, 0.18, 2.02), (0.03, 3.4, 0.02), M["pillar"])
    text(f"Side_120_{s:+d}", "120", (s * 1.012, 0.45, 1.12), (90, 0, 90 * s), 0.42, M["navy"])
    for y in (-0.7, 1.55):
        ellipsoid(f"SideMarker_{s:+d}_{y}", (xs, y, 0.85), (0.02, 0.045, 0.045), M["amber"])
    for i in range(8):
        box(f"SideVent_{s:+d}_{i}", (s * 1.004, 1.72, 0.85 + i * 0.05), (0.02, 0.22, 0.022), M["blue_dark"])
    # ミラー（屋根の角から前方外側へ伸びて垂れ下がる）
    p0 = (s * 0.88, FRONT + 0.15, 2.3)
    p1 = (s * 1.27, FRONT - 0.18, 2.28)
    rod(f"MirrorArm_{s:+d}", p0, p1, 0.022, M["black"])
    rod(f"MirrorStem_{s:+d}", p1, (s * 1.29, FRONT - 0.2, 2.18), 0.02, M["black"])
    box(f"Mirror_{s:+d}", (s * 1.3, FRONT - 0.2, 2.02), (0.12, 0.08, 0.4), M["black"], 0.045)
# 右側（+X）のドア
box("Door", (1.0, -0.25, 1.44), (0.032, 0.6, 1.64), M["glass"], 0.03)
box("DoorDivider", (1.012, -0.25, 1.44), (0.03, 0.03, 1.64), M["pillar"])

# ---------- 後部 ----------
box("RearWindow", (0, REAR + 0.006, 1.82), (1.62, 0.03, 0.9), M["glass"], 0.06)
box("RearPlate", (-0.42, REAR + 0.024, 1.5), (0.5, 0.012, 0.2), M["plate"], 0.01)
text("Rear_120", "120", (-0.42, REAR + 0.032, 1.5), (90, 0, 180), 0.16, M["sign"])
box("RearChrome", (0, REAR + 0.01, 1.22), (1.0, 0.02, 0.05), M["chrome"], 0.01)
box("RearPanel", (0, REAR + 0.004, 0.8), (0.9, 0.012, 0.25), M["blue_dark"], 0.04)
for s in (-1, 1):
    for z, mm in ((1.02, "red"), (0.87, "amber"), (0.72, "lamp")):
        box(f"TailLight_{s:+d}_{mm}", (s * 0.78, REAR + 0.006, z), (0.2, 0.03, 0.14), M[mm], 0.015)
box("RearBumper", (0, REAR - 0.05, 0.31), (2.06, 0.26, 0.38), M["bumper"], 0.06)

# ---------- 顔 ----------
HIDE = 0.07  # 隠しパーツを白目の奥へ押し込む量


def make_eye(name, cx):
    s = 1 if cx > 0 else -1
    g = Geo()
    g.sphere("rim", (0.225, 0.04, 0.24), (0, 0.006, 0), 2)
    g.sphere("white", (0.2, 0.055, 0.215), (0, 0, 0), 0)
    px = -s * 0.06  # 黒目は少し内側（寄り目）
    g.sphere("pupil", (0.065, 0.022, 0.095), (px, -0.05, 0.01), 1, 20, 10)
    g.sphere("hi", (0.022, 0.008, 0.028), (px + 0.025, -0.071, 0.06), 0, 12, 6)
    arc = [Vector((px * 0.5 + 0.075 * math.cos(a), -0.062 + HIDE, -0.035 + 0.07 * math.sin(a)))
           for a in [math.pi * k / 14 for k in range(15)]]
    g.tube("arc", arc, 0.018, 1)  # 笑顔の「◠」目（通常時は奥に隠す）
    obj = g.build(name, [M["white"], M["black"], M["chrome"]], (cx, fy(cx), EYE_Z), math.atan(2 * K * cx))
    show_arc = set(g.groups["arc"])
    hide_pupil = set(g.groups["pupil"]) | set(g.groups["hi"])

    def smile(i, co):
        if i in show_arc:
            co.y -= HIDE
        elif i in hide_pupil:
            co.y += HIDE
        return co

    def blink(i, co):
        co.z = co.z * 0.07 - 0.06
        return co

    shape_keys(obj, {"smile": smile, "blink": blink})


def make_brow(name, cx):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.022
    cu.bevel_resolution = 3
    cu.resolution_u = 12
    sp = cu.splines.new("BEZIER")
    angles = [165, 125, 90, 55, 15]
    sp.bezier_points.add(len(angles) - 1)
    for bp, a in zip(sp.bezier_points, angles):
        r = math.radians(a)
        bp.co = (0.23 * math.cos(r), 0, 0.24 * math.sin(r))
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    tmp = link(bpy.data.objects.new("tmp", cu))
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp)
    bpy.data.curves.remove(cu)
    obj = link(bpy.data.objects.new(name, me))
    me.materials.append(M["brow"])
    me.shade_smooth()
    obj.location = (cx, fy(cx) - 0.04, 1.27)
    obj.rotation_euler.z = math.atan(2 * K * cx)
    obj.parent = BODY

    def smile(i, co):
        t = min(abs(co.x) / 0.23, 1.0)
        co.z += 0.05 + 0.05 * (1 - t * t)
        return co

    def blink(i, co):
        co.z -= 0.03
        return co

    shape_keys(obj, {"smile": smile, "blink": blink})


def mouth_verts(W, curve, Hc, He, top, pad, N=41):
    """口の輪郭（上辺 N 点 + 下辺 N 点）。端は丸める"""
    tops, bots = [], []
    for i in range(N):
        u = i / (N - 1) * 2 - 1
        x = u * (W / 2 + pad)
        r = math.sqrt(max(0.0, 1 - u ** 8))
        zt = top + curve * u * u
        zb = zt - (He + (Hc - He) * (1 - u * u)) * r
        tops.append(Vector((x, K * x * x, zt + pad)))
        bots.append(Vector((x, K * x * x, zb - pad)))
    return tops + bots


def make_mouth(name, y, material, pad):
    N = 41
    neutral = mouth_verts(0.8, 0.05, 0.24, 0.12, 0.0, pad, N)
    laugh = mouth_verts(0.84, -0.04, 0.33, 0.22, 0.05, pad, N)
    me = bpy.data.meshes.new(name)
    me.from_pydata([v.to_tuple() for v in neutral], [], [(i, N + i, N + i + 1, i + 1) for i in range(N - 1)])
    obj = link(bpy.data.objects.new(name, me))
    me.materials.append(material)
    obj.location = (0, y, 0.78)
    obj.parent = BODY
    sol = obj.modifiers.new("Solidify", "SOLIDIFY")
    sol.thickness = 0.015
    shape_keys(obj, {"smile": lambda i, co: laugh[i].copy()})


for s in (-1, 1):
    make_eye(f"Eye_{s:+d}", s * 0.7)
    make_brow(f"Brow_{s:+d}", s * 0.68)
make_mouth("Mouth_Rim", FRONT - 0.012, M["chrome"], 0.03)
make_mouth("Mouth", FRONT - 0.022, M["grille"], 0.0)
ellipsoid("Nose", (0, FRONT - 0.005, 0.86), (0.085, 0.03, 0.035), M["chrome"])

# ---------- タイヤ ----------
for label, wy, front in [("FL", -1.25, True), ("FR", -1.25, True), ("RL", 1.15, False), ("RR", 1.15, False)]:
    s = -1 if label.endswith("L") else 1
    center = (s * 0.86, wy, WHEEL_R)
    if front:
        pivot = link(bpy.data.objects.new(f"Steer_{label}", None))
        pivot.empty_display_type = "SPHERE"
        pivot.empty_display_size = 0.15
        pivot.location = center
        pivot.parent = root
        add_driver(pivot, "rotation_euler", "v", [("v", "PROP", '["steer"]')], 2)
        tire = cyl(f"Wheel_{label}", (0, 0, 0), WHEEL_R, 0.38, M["tire"], "X", pivot, 48)
    else:
        tire = cyl(f"Wheel_{label}", center, WHEEL_R, 0.38, M["tire"], "X", root, 48)
    bv = tire.modifiers.new("Bevel", "BEVEL")
    bv.width, bv.segments = 0.08, 4
    out = s * 0.19
    cyl(f"Hub_{label}", (out, 0, 0), 0.28, 0.03, M["chrome"], "X", tire)
    cyl(f"HubCap_{label}", (out + s * 0.02, 0, 0), 0.1, 0.04, M["chrome"], "X", tire)
    for k in range(6):
        a = k * 2 * math.pi / 6
        cyl(f"Bolt_{label}_{k}", (out + s * 0.025, 0.17 * math.cos(a), 0.17 * math.sin(a)),
            0.025, 0.03, M["black"], "X", tire, 12)
    # Tayo_Root を前(-Y)へ動かすと前転する + wheel_spin
    add_driver(tire, "rotation_euler", f"-y/{WHEEL_R} + spin",
               [("y", "LOC", "LOC_Y"), ("spin", "PROP", '["wheel_spin"]')], 0)

# ---------- 環境 ----------
box("Ground", (0, 0, -0.01), (60, 60, 0.02), M["grass"], parent=None)
box("Road", (0, 0, 0.0), (8, 60, 0.01), M["asphalt"], parent=None)
for x in (-3.6, 3.6):
    box(f"RoadEdge_{x}", (x, 0, 0.007), (0.12, 60, 0.01), M["line"], parent=None)
for i in range(15):
    box(f"RoadDash_{i}", (-2.0, -28 + i * 4, 0.007), (0.12, 2.0, 0.01), M["line"], parent=None)

world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs["Color"].default_value = (0.5, 0.7, 1.0, 1)
bg.inputs["Strength"].default_value = 1.0

sun = link(bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN")))
sun.data.energy = 4.0
sun.data.angle = math.radians(8)
sun.rotation_euler = (math.radians(50), 0, math.radians(-35))

target = link(bpy.data.objects.new("CamTarget", None))
target.location = (0, 0, 1.3)
target.parent = root
cam = link(bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera")))
cam.data.lens = 38
cam.location = (-5.0, -8.2, 2.3)
tc = cam.constraints.new("TRACK_TO")
tc.target = target
tc.track_axis = "TRACK_NEGATIVE_Z"
tc.up_axis = "UP_Y"
scene.camera = cam

# ---------- アニメーション（10秒: 走ってきて止まり、にっこり笑う） ----------
scene.render.fps = 24
scene.frame_start, scene.frame_end = 1, 240


def keys(obj, path, fv, index=-1):
    for f, v in fv:
        if path.startswith("["):
            obj[path[2:-2]] = float(v)
            obj.keyframe_insert(path, frame=f)
        else:
            getattr(obj, path)[index] = v
            obj.keyframe_insert(path, index=index, frame=f)


keys(root, "location", [(1, 7.0), (20, 7.0), (140, 0.0)], 1)              # 前進して停止（タイヤは自動回転）
keys(BODY, "rotation_euler", [(1, 0), (20, 0), (32, -0.025), (55, 0),       # 発進で鼻上げ、停止で前のめり
                              (125, 0), (141, 0.04), (150, -0.015), (158, 0)], 0)
keys(BODY, "location", [(150, 0.0)] + [(152 + 6 * i, 0.06 if i % 2 == 0 else 0.0) for i in range(11)]
     + [(220, 0.0)], 2)                                                     # 笑いながらぴょこぴょこ
keys(root, '["smile"]', [(1, 0), (140, 0), (152, 1), (215, 1), (232, 0)])
keys(root, '["blink"]', [(1, 0), (70, 0), (73, 1), (76, 0), (190, 0), (193, 1), (196, 0)])
scene.frame_set(1)

# ---------- レンダー設定 ----------
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    scene.render.engine = "BLENDER_EEVEE"
scene.eevee.taa_render_samples = 32
scene.view_settings.view_transform = "Standard"
scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
scene.render.resolution_percentage = 100

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT_DIR, "Tayo_bus.blend"))
print("SAVED", len(col.objects), "objects")
