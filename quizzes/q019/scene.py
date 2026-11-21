import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import bpy, bmesh, math, json, sys, os, random
from mathutils import Vector, Euler, Matrix, noise
from bpy_extras.object_utils import world_to_camera_view

FPS = 30
RES = (1080, 1920)
OUT = os.environ.get("OUT", QDIR)
SHOT = "A"
SHOTS = {"A": (0.0, 9.6), "B": (9.6, 15.4), "C": (15.4, 21.4), "D": (21.4, 28.6)}
if "frames" in sys.argv:
    _st = int(os.environ.get("STEP", "2")); _a = int(os.environ.get("IFROM", "0")); _b = int(os.environ.get("ITO", int(28.6*FPS)))
    if all(os.path.exists(f"{OUT}/frames/f{i:04d}.png") for i in range(_a, _b, _st)): sys.exit(0)

def ease(x):
    x = max(0.0, min(1.0, x)); return x*x*(3-2*x)
def lerp(a, b, k): return a + (b-a)*k
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; coll = sc.collection
rnd = random.Random(19)

HAZE = (1.0, 0.72, 0.50)
def add_haze(m, dist=1800.0, amt=0.85, col=HAZE, strength=0.5):
    nt = m.node_tree; out = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]
    src = out.inputs["Surface"].links[0].from_socket
    cd = nt.nodes.new("ShaderNodeCameraData")
    mth = nt.nodes.new("ShaderNodeMath"); mth.operation = 'DIVIDE'; mth.inputs[1].default_value = -dist
    nt.links.new(cd.outputs["View Distance"], mth.inputs[0])
    ex = nt.nodes.new("ShaderNodeMath"); ex.operation = 'EXPONENT'; nt.links.new(mth.outputs[0], ex.inputs[0])
    inv = nt.nodes.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0; nt.links.new(ex.outputs[0], inv.inputs[1])
    sc_ = nt.nodes.new("ShaderNodeMath"); sc_.operation = 'MULTIPLY'; sc_.inputs[1].default_value = amt; nt.links.new(inv.outputs[0], sc_.inputs[0])
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs[0].default_value = (*col, 1); em.inputs[1].default_value = strength
    mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(sc_.outputs[0], mx.inputs[0]); nt.links.new(src, mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    return m

def principled(name, color, rough=0.5, metal=0.0, coat=0.0, haze=True, emit=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal; b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = (*emit[0], 1); b.inputs["Emission Strength"].default_value = emit[1]
    return add_haze(m) if haze else m
def mesh_obj(name, bm, mat, smooth=True, parent=None):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); coll.objects.link(o); o.data.materials.append(mat)
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    if parent: o.parent = parent
    return o
def box(name, x0, x1, y0, y1, z0, z1, mat, parent=None, bev=0.04, seg=2):
    bm = bmesh.new(); g = bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(x1-x0, y1-y0, z1-z0), verts=bm.verts)
    bmesh.ops.translate(bm, vec=((x0+x1)/2, (y0+y1)/2, (z0+z1)/2), verts=bm.verts)
    if bev > 0:
        bmesh.ops.bevel(bm, geom=bm.edges[:]+bm.verts[:], offset=bev, segments=seg, affect='EDGES', profile=0.5)
    o = mesh_obj(name, bm, mat, smooth=bev > 0, parent=parent)
    return o
def cyl(name, loc, r, depth, axis, mat, parent=None, verts=24):
    rot = {"x": (0, math.pi/2, 0), "y": (math.pi/2, 0, 0), "z": (0, 0, 0)}[axis]
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name; o.data.materials.append(mat)
    for p in o.data.polygons: p.use_smooth = True
    if parent: o.parent = parent
    return o

# ------------------------------------------------------------------ path of the truck
# road runs down along +x at -6 %; the escape lane leaves to the right (-y) and runs straight into a gravel bed (x>0)
def road_yc(x): return 0.0 if x < 0 else 0.0035*x*x
def ramp_z(x): return -0.06*x if x < 0 else 0.02*x
def road_z(x): return -0.06*x
def path_y(x):                       # centre of the truck's path
    return lerp(-1.85, -10.0, ease((x + 110)/80))
def path_z(x): return ramp_z(x) if x > -110 else road_z(x)
GB0, GB1 = 0.0, 130.0                # gravel bed x range
YB0, YB1 = -15.0, -6.0
STEER, DRIVES = 4.6, (0.65, -0.65)
T_IN = 15.6; V_IN = 24.0; DEC = 5.0
def s_of(t):
    if t <= T_IN: return 20*t + (4/(2*T_IN))*t*t
    tau = min(t - T_IN, V_IN/DEC); return s_of(T_IN) + V_IN*tau - 0.5*DEC*tau*tau
X_OFF = s_of(T_IN) + STEER          # front axle reaches x=0 at T_IN
def xref(t): return s_of(t) - X_OFF
def sink(xw): return 0.0 if xw <= 0 else 0.40*clamp(xw/9.0)
def ppos(x): return Vector((x, path_y(x), path_z(x)))
def truck_state(t):
    x = xref(t)
    p = ppos(x); fwd = (ppos(x + 1) - ppos(x - 1))
    yaw = math.atan2(fwd.y, fwd.x)
    pitch = math.atan2(path_z(x + 3) - path_z(x - 3), 6.0)
    sk = 0.5*(sink(x + STEER) + sink(x))
    king = ppos(x + 0.3)
    pa = ppos(x + 0.3 - 12.95)
    pa.z -= sink(x + 0.3 - 12.95)
    ty = math.atan2(king.y - pa.y, king.x - pa.x)
    tpitch = math.atan2((king.z - sk) - pa.z, 12.95)
    return {"x": x, "pos": p - Vector((0, 0, sk)), "yaw": yaw, "pitch": pitch, "king": king - Vector((0, 0, sk)),
            "tyaw": ty, "tpitch": tpitch, "dist": s_of(t)}
def mat_of(pos, yaw, pitch):
    return Matrix.Translation(pos) @ Matrix.Rotation(yaw, 4, 'Z') @ Matrix.Rotation(-pitch, 4, 'Y')
def wheels_world(t):
    st = truck_state(t)
    Mt = mat_of(st["pos"], st["yaw"], st["pitch"]); Mr = mat_of(st["king"], st["tyaw"], st["tpitch"])
    out = []
    for ax in (STEER,) + DRIVES:
        for s in (-1, 1): out.append(Mt @ Vector((ax, s*0.95, 0.0)))
    for ax in (-12.3, -13.6):
        for s in (-1, 1): out.append(Mr @ Vector((ax, s*0.95, 0.0)))
    return out

# ------------------------------------------------------------------ terrain
def terrain(x, y):
    zr = road_z(max(-1500.0, min(x, 600.0))); dy = y - road_yc(min(x, 600.0))
    n1 = noise.fractal(Vector((x/90, y/90, 0.3)), 0.6, 2.0, 5)
    if dy > 0:
        k = max(0.0, dy - 6.5)
        h = zr - 0.1 + 0.85*k*(1 - 0.35*clamp(k/220)) + 9*n1*clamp(k/15)
        h += 6*max(0.0, noise.noise(Vector((x/30, y/30, 2.0))))*clamp(k/8)
    else:
        k = max(0.0, -dy - 6.5)
        h = zr - 0.1 - 0.42*k*(1 - 0.5*clamp(k/120)) + 6*n1*clamp(k/25)
        h = max(h, zr - 45 + 10*n1)
    # big distant mountains
    far = clamp((abs(dy) - 220)/450)*clamp((x + 2800)/300)
    h += far*(260*max(0.0, noise.fractal(Vector((x/700, y/700, 1.1)), 0.55, 2.0, 5) + 0.25))
    # escape lane platform + embankment
    if x > -125:
        cy = path_y(min(x, 0.0)) if x < 0 else -10.0
        half = 3.0 if x < -40 else (6.0 if x > 0 else 4.0)
        d = abs(y - cy) - half
        zp = ramp_z(x) - 0.06
        if x > GB1 + 6: zp = ramp_z(GB1) - 0.06 + 0.25*(x - GB1 - 6)
        if d < 0: h = zp
        else: h = max(h, zp - 0.55*d) if (y < cy or x > 0) else h
    if abs(dy) < 6.2: h = min(h, zr - 0.05) if dy < 0 else zr - 0.05
    return h
def axis(a, b, da, ia, ib, db):
    out = []; v = a
    while v < b:
        out.append(v); v += da if (v < ia or v > ib) else db
    return out
XS = axis(-900, 600, 8.0, -330, 190, 1.5) + axis(600, 3200, 30.0, 0, 0, 30.0)
XS = axis(-3000, -900, 30.0, 0, 0, 30) + XS
YS = axis(-700, 800, 8.0, -45, 130, 1.25)
YS = axis(-2600, -700, 30.0, 0, 0, 30) + YS + axis(800, 2800, 30.0, 0, 0, 30)
bm = bmesh.new(); vs = []
for y in YS:
    vs.append([bm.verts.new((x, y, terrain(x, y))) for x in XS])
for j in range(len(YS) - 1):
    for i in range(len(XS) - 1):
        bm.faces.new([vs[j][i], vs[j][i+1], vs[j+1][i+1], vs[j+1][i]])
def ground_mat():
    m = bpy.data.materials.new("ground"); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.92
    tc = nt.nodes.new("ShaderNodeTexCoord"); geo = nt.nodes.new("ShaderNodeNewGeometry")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.02; nz.inputs["Detail"].default_value = 10
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    cr = nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (0.018, 0.032, 0.010, 1); cr.color_ramp.elements[1].color = (0.075, 0.068, 0.035, 1)
    cr.color_ramp.elements[0].position = 0.35; cr.color_ramp.elements[1].position = 0.7
    nt.links.new(nz.outputs["Fac"], cr.inputs[0])
    # steep faces -> bare rock
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(geo.outputs["Normal"], sep.inputs[0])
    rk = nt.nodes.new("ShaderNodeMapRange"); rk.inputs[1].default_value = 0.62; rk.inputs[2].default_value = 0.45
    nt.links.new(sep.outputs[2], rk.inputs[0])
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.inputs[7].default_value = (0.06, 0.056, 0.05, 1)
    nt.links.new(rk.outputs[0], mx.inputs[0]); nt.links.new(cr.outputs[0], mx.inputs[6]); nt.links.new(mx.outputs[2], b.inputs["Base Color"])
    nz2 = nt.nodes.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = 0.6; nz2.inputs["Detail"].default_value = 8
    nt.links.new(tc.outputs["Object"], nz2.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.6
    nt.links.new(nz2.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs[0], b.inputs["Normal"])
    return add_haze(m)
mesh_obj("terrain", bm, ground_mat())

# ------------------------------------------------------------------ road + markings
def asphalt():
    m = bpy.data.materials.new("asphalt"); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.78
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.4; nz.inputs["Detail"].default_value = 6
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    cr = nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (0.035, 0.035, 0.037, 1); cr.color_ramp.elements[1].color = (0.075, 0.072, 0.07, 1)
    nt.links.new(nz.outputs["Fac"], cr.inputs[0]); nt.links.new(cr.outputs[0], b.inputs["Base Color"])
    nz2 = nt.nodes.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = 60; nt.links.new(tc.outputs["Object"], nz2.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.25
    nt.links.new(nz2.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs[0], b.inputs["Normal"])
    return add_haze(m)
M_ASPH = asphalt()
M_WLINE = principled("wline", (0.75, 0.75, 0.72), 0.6)
M_YLINE = principled("yline", (0.80, 0.55, 0.05), 0.6)
def strip(name, xa, xb, yfun, w0, w1, zfun, mat, step=1.0, dash=None):
    bm = bmesh.new(); prev = None; x = xa
    while x <= xb:
        yc = yfun(x); z = zfun(x)
        if dash and (x % dash[0]) > dash[1]:
            prev = None; x += step/4; continue
        ring = [bm.verts.new((x, yc + w0, z)), bm.verts.new((x, yc + w1, z))]
        if prev: bm.faces.new([prev[0], prev[1], ring[1], ring[0]])
        prev = ring; x += step
    return mesh_obj(name, bm, mat, smooth=False)
strip("road", -2900, 520, road_yc, -6.0, 6.0, lambda x: road_z(x) + 0.0, M_ASPH)
strip("edgeR", -900, 520, road_yc, -3.75, -3.6, lambda x: road_z(x) + 0.012, M_WLINE, 0.5)
strip("edgeL", -900, 520, road_yc, 3.6, 3.75, lambda x: road_z(x) + 0.012, M_WLINE, 0.5)
strip("cy1", -900, 520, road_yc, -0.18, -0.06, lambda x: road_z(x) + 0.012, M_YLINE, 0.5)
strip("cy2", -900, 520, road_yc, 0.06, 0.18, lambda x: road_z(x) + 0.012, M_YLINE, 0.5)
# exit lane (paved) from the road to the bed
strip("exitlane", -125, 0.5, lambda x: path_y(x), -2.6, 2.6, lambda x: path_z(x) + 0.006, M_ASPH, 0.5)
# strip("exitedge", -110, 0.5, lambda x: path_y(x), 2.45, 2.6, lambda x: path_z(x) + 0.016, M_WLINE, 0.5)

# guard rail along the outer (right) side of the road before the exit, and along the curve after it
M_RAIL = principled("rail", (0.55, 0.56, 0.57), 0.35, 0.9)
M_POST = principled("post", (0.25, 0.22, 0.2), 0.7, 0.3)
def guardrail(xa, xb, side):
    bm = bmesh.new(); x = xa; prev = None
    while x <= xb:
        yc = road_yc(x) + side*6.3; z = road_z(x)
        ring = [bm.verts.new((x, yc, z + 0.55)), bm.verts.new((x, yc, z + 0.85))]
        if prev: bm.faces.new([prev[0], prev[1], ring[1], ring[0]])
        prev = ring; x += 1.0
    o = mesh_obj(f"rail{xa}", bm, M_RAIL, smooth=False)
    x = xa
    while x <= xb:
        box(f"p{x}", x - 0.08, x + 0.08, road_yc(x) + side*6.3 - 0.08 - side*0.12, road_yc(x) + side*6.3 + 0.08 - side*0.12, road_z(x) - 0.5, road_z(x) + 0.8, M_POST, bev=0)
        x += 4.0
guardrail(-700, -150, -1)
guardrail(25, 300, -1)

# ------------------------------------------------------------------ gravel bed (dynamic ruts)
def gravel_mat():
    m = bpy.data.materials.new("gravel"); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.85
    tc = nt.nodes.new("ShaderNodeTexCoord")
    vo = nt.nodes.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 38.0; vo.feature = 'F1'
    nt.links.new(tc.outputs["Object"], vo.inputs["Vector"])
    vo2 = nt.nodes.new("ShaderNodeTexVoronoi"); vo2.inputs["Scale"].default_value = 38.0; vo2.feature = 'DISTANCE_TO_EDGE'
    nt.links.new(tc.outputs["Object"], vo2.inputs["Vector"])
    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (0.16, 0.13, 0.10, 1); cr.color_ramp.elements[1].color = (0.42, 0.36, 0.29, 1)
    nt.links.new(vo.outputs["Color"], cr.inputs[0])
    sh = nt.nodes.new("ShaderNodeMapRange"); sh.inputs[1].default_value = 0.0; sh.inputs[2].default_value = 0.12; sh.inputs[3].default_value = 0.35; sh.inputs[4].default_value = 1.0
    nt.links.new(vo2.outputs["Distance"], sh.inputs[0])
    mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs[0].default_value = 1.0
    nt.links.new(cr.outputs[0], mul.inputs[6]); nt.links.new(sh.outputs[0], mul.inputs[7])
    nt.links.new(mul.outputs[2], b.inputs["Base Color"])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.9; bp.inputs["Distance"].default_value = 0.02
    nt.links.new(sh.outputs[0], bp.inputs["Height"]); nt.links.new(bp.outputs[0], b.inputs["Normal"])
    return add_haze(m)
M_GRAVEL = gravel_mat()
TRACKS = (-10.95, -9.05)
def bed_h(x, y, xf):
    h = ramp_z(x) + 0.03*noise.noise(Vector((x*1.3, y*1.3, 0.5)))
    # shallow lip at the edges
    h -= 0.25*clamp((y - (YB1 - 0.8))/0.8) + 0.25*clamp(((YB0 + 0.8) - y)/0.8)
    if 0 < x < xf:
        dep = sink(x) + 0.06
        for ty in TRACKS:
            d = abs(y - ty)
            if d < 0.42: h -= dep*(0.5 + 0.5*math.cos(math.pi*d/0.42))
            elif d < 0.9: h += 0.10*clamp(x/6)*math.sin(math.pi*(d - 0.42)/0.48)
    # pushed-up pile in front of the wheels
    if xf > 0 and 0 < x - xf < 1.6:
        k = (x - xf)/1.6
        for ty in TRACKS:
            d = abs(y - ty)
            if d < 0.7: h += 0.22*clamp(xf/8)*math.sin(math.pi*k)*(1 - d/0.7)
    return h
BED = None
def build_bed(xf):
    global BED
    if BED is not None:
        me = BED.data; bpy.data.objects.remove(BED, do_unlink=True); bpy.data.meshes.remove(me)
    bm = bmesh.new(); vs = []
    xs = axis(GB0, GB1, 0.6, -1, 75, 0.14)
    ys = axis(YB0, YB1 + 0.01, 0.12, -100, 100, 0.12)
    for y in ys: vs.append([bm.verts.new((x, y, bed_h(x, y, xf))) for x in xs])
    for j in range(len(ys) - 1):
        for i in range(len(xs) - 1):
            bm.faces.new([vs[j][i], vs[j][i+1], vs[j+1][i+1], vs[j+1][i]])
    BED = mesh_obj("bed", bm, M_GRAVEL)

# loose pebbles near the C-camera (outside the wheel tracks)
M_PEB = [principled(f"peb{k}", c, 0.8) for k, c in enumerate(((0.36, 0.31, 0.25), (0.30, 0.26, 0.21), (0.42, 0.37, 0.30), (0.26, 0.23, 0.19)))]
peb_me = []
for k in range(5):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    for v in bm.verts:
        v.co *= 1 + 0.25*noise.noise(v.co*1.7 + Vector((k*3.1, 0, 0)))
    bmesh.ops.scale(bm, vec=(1.0, 0.85, 0.6), verts=bm.verts)
    me = bpy.data.meshes.new(f"peb{k}"); bm.to_mesh(me); bm.free(); me.materials.append(M_PEB[k % 4])
    for p in me.polygons: p.use_smooth = True
    peb_me.append(me)
NP = int(os.environ.get("NPEB", "7000"))
for k in range(NP):
    x = rnd.uniform(52, 66); y = rnd.uniform(YB0 + 0.6, -11.6) if rnd.random() < 0.7 else rnd.uniform(-8.4, YB1 - 0.6)
    o = bpy.data.objects.new(f"pb{k}", peb_me[k % 5]); coll.objects.link(o)
    s = rnd.uniform(0.008, 0.022)
    o.location = (x, y, bed_h(x, y, 0) + s*0.2); o.scale = (s, s, s); o.rotation_euler = (rnd.uniform(0, 6.3), rnd.uniform(0, 6.3), rnd.uniform(0, 6.3))

# ------------------------------------------------------------------ trees
M_CON = principled("conifer", (0.016, 0.03, 0.014), 0.9)
bm = bmesh.new()
for (r_, d_, z_) in ((2.6, 7, 4.5), (2.0, 6, 8.0), (1.2, 5, 11.5)):
    g_ = bmesh.ops.create_cone(bm, cap_ends=True, segments=9, radius1=r_, radius2=0.0, depth=d_)
    bmesh.ops.translate(bm, verts=g_["verts"], vec=(0, 0, z_))
con_me = bpy.data.meshes.new("con"); bm.to_mesh(con_me); bm.free(); con_me.materials.append(M_CON)
NT = int(os.environ.get("NTREES", "14000")); k = 0; tries = 0
while k < NT and tries < NT*8:
    tries += 1
    x = rnd.uniform(-800, 450); y = rnd.uniform(-450, 500)
    dy = y - road_yc(x)
    if abs(dy) < 9.5: continue
    if x > -130 and -22 < y < 0 and x < GB1 + 20: continue
    if -270 < x < -95 and -45 < y < -6: continue
    if x > -130 and y < 0 and x < GB1 + 12 and y > -30: continue
    dens = 0.6 + 0.6*noise.noise(Vector((x/120, y/120, 1.7)))
    if rnd.random() > dens: continue
    o = bpy.data.objects.new(f"t{k}", con_me); coll.objects.link(o)
    s = rnd.uniform(0.7, 1.4)
    o.location = (x, y, terrain(x, y) - 0.6); o.scale = (s, s, s*rnd.uniform(0.85, 1.25)); o.rotation_euler.z = rnd.uniform(0, 6.28)
    k += 1

# ------------------------------------------------------------------ truck
M_PAINT = principled("paint", (0.32, 0.018, 0.012), 0.28, 0.35, coat=1.0)
M_CHROME = principled("chrome", (0.85, 0.85, 0.86), 0.08, 1.0)
M_DARK = principled("dark", (0.025, 0.025, 0.027), 0.6, 0.2)
M_TIRE = principled("tire", (0.018, 0.018, 0.018), 0.85)
M_RIM = principled("rim", (0.7, 0.7, 0.72), 0.25, 1.0)
M_GLASS = principled("glass", (0.01, 0.012, 0.015), 0.04, 0.0, coat=1.0)
M_TRAIL = principled("trailer", (0.62, 0.62, 0.60), 0.45, 0.1)
M_HEAD = principled("headlamp", (1, 0.95, 0.85), 0.2, emit=((1.0, 0.92, 0.78), 25.0))
M_AMBER = principled("amber", (1, 0.5, 0.1), 0.3, emit=((1.0, 0.45, 0.08), 8.0))
M_RED = principled("redtape", (0.5, 0.02, 0.02), 0.4)
tractor = bpy.data.objects.new("tractor", None); coll.objects.link(tractor)
trailer = bpy.data.objects.new("trailer", None); coll.objects.link(trailer)
P = tractor
box("frame", -1.7, 5.6, -0.5, 0.5, 0.72, 1.05, M_DARK, P, 0.02)
box("bumper", 5.55, 5.85, -1.25, 1.25, 0.5, 0.95, M_CHROME, P, 0.06)
box("hood", 3.2, 5.6, -1.02, 1.02, 1.05, 2.15, M_PAINT, P, 0.18, 4)
box("grille", 5.5, 5.68, -0.55, 0.55, 1.0, 2.05, M_CHROME, P, 0.03)
for k in range(9):
    box(f"gs{k}", 5.66, 5.7, -0.5, 0.5, 1.08 + k*0.105, 1.12 + k*0.105, M_DARK, P, 0)
for s in (-1, 1):
    box(f"fender{s}", 3.55, 5.5, s*0.95 - 0.32, s*0.95 + 0.32, 0.95, 1.45, M_PAINT, P, 0.15, 3)
    box(f"head{s}", 5.5, 5.62, s*0.95 - 0.22, s*0.95 + 0.22, 1.25, 1.42, M_HEAD, P, 0.02)
    box(f"amb{s}", 5.45, 5.6, s*1.2 - 0.06, s*1.2 + 0.06, 1.5, 1.58, M_AMBER, P, 0.01)
    box(f"step{s}", 1.6, 3.1, s*1.2 - 0.1, s*1.2 + 0.1, 0.6, 0.72, M_CHROME, P, 0.02)
    cyl(f"tank{s}", (1.75, s*1.02, 0.95), 0.34, 1.7, "x", M_CHROME, P)
    cyl(f"stack{s}", (1.15, s*1.18, 2.55), 0.1, 3.0, "z", M_CHROME, P, 16)
    box(f"mirror{s}", 3.0, 3.12, s*1.55 - 0.1, s*1.55 + 0.1, 2.05, 2.65, M_DARK, P, 0.03)
    box(f"marm{s}", 3.0, 3.06, s*1.2, s*1.5, 2.3, 2.34, M_CHROME, P, 0)
    box(f"swin{s}", 2.0, 3.0, s*1.2 - 0.02, s*1.2 + 0.02, 2.15, 2.85, M_GLASS, P, 0)
box("cab", 1.3, 3.25, -1.2, 1.2, 1.0, 3.05, M_PAINT, P, 0.12, 3)
bm = bmesh.new()   # raked windshield
for v in ((3.27, -1.08, 2.15), (3.27, 1.08, 2.15), (3.0, 1.05, 2.95), (3.0, -1.05, 2.95)): bm.verts.new(v)
bm.faces.new(bm.verts[:]); mesh_obj("wshield", bm, M_GLASS, smooth=False, parent=P)
box("sleeper", -0.9, 1.35, -1.2, 1.2, 1.05, 3.45, M_PAINT, P, 0.15, 3)
box("visor", 3.15, 3.45, -1.15, 1.15, 2.98, 3.05, M_DARK, P, 0.02)
box("fifth", -1.6, 0.2, -0.9, 0.9, 1.05, 1.18, M_DARK, P, 0.02)
for k, x in enumerate((0.9, 1.2, 1.5, 1.8, 2.1)):
    box(f"cabl{k}", x, x + 0.1, -0.06, 0.06, 3.05, 3.1, M_AMBER, P, 0)
WHEELS = []
def wheel(name, x, y, r, w, parent):
    e = bpy.data.objects.new(name, None); coll.objects.link(e); e.parent = parent; e.location = (x, y, r)
    cyl(name + "t", (0, 0, 0), r, w, "y", M_TIRE, e, 32)
    cyl(name + "r", (0, (0.01 if y > 0 else -0.01), 0), r*0.58, w + 0.02, "y", M_RIM, e, 24)
    for k in range(6):
        a = k*math.pi/3
        cyl(name + f"n{k}", (r*0.3*math.cos(a), (w/2 + 0.02)*(1 if y > 0 else -1), r*0.3*math.sin(a)), 0.035, 0.04, "y", M_CHROME, e, 8)
    WHEELS.append((e, r))
R_W = 0.52
for s in (-1, 1):
    wheel(f"ws{s}", STEER, s*1.02, R_W, 0.32, P)
    for k, ax in enumerate(DRIVES): wheel(f"wd{k}{s}", ax, s*0.92, R_W, 0.6, P)
T = trailer
box("tbox", -15.2, 0.9, -1.3, 1.3, 1.3, 4.1, M_TRAIL, T, 0.05)
box("tbase", -15.2, 0.9, -1.27, 1.27, 1.12, 1.32, M_DARK, T, 0.02)
for k in range(32):
    x = -15.0 + k*0.5
    box(f"rib{k}", x, x + 0.05, -1.32, 1.32, 1.3, 4.1, M_TRAIL, T, 0)
for s in (-1, 1):
    box(f"tape{s}", -15.1, 0.8, s*1.31 - 0.01, s*1.31 + 0.01, 1.42, 1.5, M_RED, T, 0)
    box(f"skirt{s}", -10.8, -3.0, s*1.22 - 0.02, s*1.22 + 0.02, 0.55, 1.12, M_TRAIL, T, 0.01)
    box(f"leg{s}", -0.9, -0.75, s*0.9 - 0.06, s*0.9 + 0.06, 0.25, 1.12, M_DARK, T, 0.01)
    for k, ax in enumerate((-12.3, -13.6)): wheel(f"wt{k}{s}", ax, s*0.92, R_W, 0.6, T)
box("tframe", -14.5, 0.0, -0.5, 0.5, 0.85, 1.12, M_DARK, T, 0.01)
box("bumpbar", -15.0, -14.8, -1.15, 1.15, 0.5, 0.65, M_DARK, T, 0.01)
for s in (-1, 1):
    box(f"tl{s}", -15.25, -15.2, s*1.05 - 0.1, s*1.05 + 0.1, 1.45, 1.6, principled(f"tlm{s}", (0.6, 0.02, 0.02), 0.3, emit=((1, 0.05, 0.02), 6.0)), T, 0)

def place_truck(t):
    st = truck_state(t)
    tractor.matrix_world = mat_of(st["pos"], st["yaw"], st["pitch"])
    trailer.matrix_world = mat_of(st["king"], st["tyaw"], st["tpitch"])
    ang = st["dist"]/R_W
    for e, r in WHEELS: e.rotation_euler = (0, ang, 0)
    return st

# ------------------------------------------------------------------ smoke + dust + flying gravel
def smoke_mat(name, col, emitcol=None):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    for n_ in list(nt.nodes): nt.nodes.remove(n_)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    pb = nt.nodes.new("ShaderNodeBsdfPrincipled"); pb.inputs["Base Color"].default_value = (*col, 1); pb.inputs["Roughness"].default_value = 1.0
    al = nt.nodes.new("ShaderNodeAttribute"); al.attribute_name = "alpha"; al.attribute_type = 'GEOMETRY'
    lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.5
    inv = nt.nodes.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    nt.links.new(lw.outputs["Facing"], inv.inputs[1])
    pw = nt.nodes.new("ShaderNodeMath"); pw.operation = 'POWER'; pw.inputs[1].default_value = 1.6; nt.links.new(inv.outputs[0], pw.inputs[0])
    tc = nt.nodes.new("ShaderNodeTexCoord"); nzs = nt.nodes.new("ShaderNodeTexNoise"); nzs.inputs["Scale"].default_value = 0.9; nzs.inputs["Detail"].default_value = 6
    nt.links.new(tc.outputs["Object"], nzs.inputs["Vector"])
    nm = nt.nodes.new("ShaderNodeMapRange"); nm.inputs[1].default_value = 0.3; nm.inputs[2].default_value = 0.7; nm.inputs[3].default_value = 0.25; nm.inputs[4].default_value = 1.0
    nt.links.new(nzs.outputs["Fac"], nm.inputs[0])
    pw2 = nt.nodes.new("ShaderNodeMapRange"); pw2.inputs[3].default_value = 0.45; pw2.inputs[4].default_value = 1.0; nt.links.new(pw.outputs[0], pw2.inputs[0])
    m0 = nt.nodes.new("ShaderNodeMath"); m0.operation = 'MULTIPLY'; nt.links.new(pw2.outputs[0], m0.inputs[0]); nt.links.new(nm.outputs[0], m0.inputs[1])
    ml = nt.nodes.new("ShaderNodeMath"); ml.operation = 'MULTIPLY'; nt.links.new(al.outputs["Fac"], ml.inputs[0]); nt.links.new(m0.outputs[0], ml.inputs[1])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(ml.outputs[0], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(pb.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs[0])
    return m
M_SMOKE = smoke_mat("smoke", (0.62, 0.62, 0.62))
M_DUST = smoke_mat("dust", (0.66, 0.56, 0.44))
WIDX_SMOKE = [2, 3, 4, 5, 6, 7, 8, 9]          # drive + trailer wheels smoke (brakes)
DYN = []
def clear_dyn():
    global DYN
    for o in DYN:
        me = o.data; bpy.data.objects.remove(o, do_unlink=True); bpy.data.meshes.remove(me)
    DYN = []
WCACHE = {}
def wpos(t):
    k = round(t*60)
    if k not in WCACHE: WCACHE[k] = wheels_world(k/60)
    return WCACHE[k]
def trail(bm, la, t, wi, age_max, rfun, afun, rise, drift, seed, mint=0.0):
    pts = []
    n = int(age_max*15)
    for j in range(n + 1):
        ta = t - j/15
        if ta < mint: break
        pa = t - ta
        p = wpos(ta)[wi].copy()
        p += Vector((drift[0]*pa, drift[1]*pa, rise*pa + 0.25))
        pts.append((p, pa, ta))
    if len(pts) < 2: return
    NS = 9; prev = None
    for j, (p, pa, ta) in enumerate(pts):
        r = rfun(pa, ta)
        if r <= 0: prev = None; continue
        tt = (pts[min(j+1, len(pts)-1)][0] - pts[max(j-1, 0)][0])
        if tt.length < 1e-5: tt = Vector((1, 0, 0))
        tt.normalize()
        a_ = tt.cross(Vector((0, 0, 1)))
        a_ = a_.normalized() if a_.length > 1e-4 else Vector((0, 1, 0))
        b_ = tt.cross(a_)
        off = 0.3*r*Vector((noise.noise(Vector((ta*3, seed, 0))), noise.noise(Vector((ta*3, seed, 5))), 0.5*noise.noise(Vector((ta*3, seed, 9)))))
        ring = []
        for i in range(NS):
            aa = 2*math.pi*i/NS
            rr = r*(1 + 0.2*noise.noise(Vector((ta*5, i*0.9, seed))))
            v = bm.verts.new(p + off + rr*(math.cos(aa)*a_ + math.sin(aa)*b_)); v[la] = afun(pa, ta); ring.append(v)
        if prev:
            for i in range(NS): bm.faces.new([prev[i], prev[(i+1) % NS], ring[(i+1) % NS], ring[i]])
        prev = ring
# flying gravel: precomputed ballistic stones
STONES = []
srnd = random.Random(5)
tt_ = T_IN
while tt_ < T_IN + V_IN/DEC:
    ws = wheels_world(tt_)
    st = truck_state(tt_)
    v = max(0.0, V_IN - DEC*(tt_ - T_IN))
    for wi, p in enumerate(ws):
        if p.x <= 0.3: continue
        for _ in range(int(3*clamp(v/12) + 1)):
            side = 1 if (wi % 2 == 1) else -1
            vel = Vector((v*srnd.uniform(0.15, 0.55), side*srnd.uniform(0.5, 3.2), srnd.uniform(1.5, 4.5)*clamp(v/10 + 0.2)))
            STONES.append((tt_, Vector((p.x + 0.5, p.y + side*0.25, p.z + 0.1)), vel, srnd.uniform(0.02, 0.05)))
    tt_ += 1/30
def build_dyn(t):
    clear_dyn()
    # brake smoke (before the gravel)
    if t < 21.5:
        bm = bmesh.new(); la = bm.verts.layers.float.new("alpha")
        for wi in WIDX_SMOKE:
            trail(bm, la, t, wi, 3.0,
                  lambda pa, ta: (0.22 + 0.7*math.sqrt(pa) + 0.3*pa) if ta < T_IN + 0.5 else 0.0,
                  lambda pa, ta: clamp(0.6*math.exp(-pa/1.8)*clamp(pa/0.12 + 0.3)), 1.3, (0.0, 1.4 if wi % 2 else -0.6), wi*7.3)
        if len(bm.verts):
            o = mesh_obj("smk", bm, M_SMOKE); DYN.append(o)
        else: bm.free()
    # dust from the gravel bed
    if t > T_IN:
        bm = bmesh.new(); la = bm.verts.layers.float.new("alpha")
        for wi in (0, 1, 4, 5, 8, 9):
            trail(bm, la, t, wi, 12.0,
                  lambda pa, ta: (0.35 + 0.9*math.sqrt(pa) + 0.12*pa) if (wpos(ta)[0].x > 0.0 and ta < T_IN + V_IN/DEC) else 0.0,
                  lambda pa, ta: clamp(0.50*math.exp(-pa/3.5)*clamp(pa/0.15 + 0.3)*clamp(max(0.0, V_IN - DEC*(ta - T_IN))/8 + 0.15)),
                  0.22, (0.35, 0.45), wi*3.1, mint=T_IN)
        if len(bm.verts):
            o = mesh_obj("dust", bm, M_DUST); DYN.append(o)
        else: bm.free()
    # flying stones
    bm = bmesh.new(); n = 0
    for (t0, p0, v0, r) in STONES:
        a = t - t0
        if a < 0 or a > 1.6: continue
        p = p0 + v0*a + Vector((0, 0, -4.9*a*a))
        if p.z < ramp_z(p.x) - 0.05: continue
        g = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=r)
        bmesh.ops.translate(bm, verts=g["verts"], vec=p); n += 1
    if n:
        o = mesh_obj("stones", bm, M_PEB[0], smooth=False); DYN.append(o)
    else: bm.free()

# ------------------------------------------------------------------ sky + sun
wo = bpy.data.worlds.new("w"); sc.world = wo; wo.use_nodes = True
bg = wo.node_tree.nodes["Background"]
sky = wo.node_tree.nodes.new("ShaderNodeTexSky"); sky.sky_type = 'MULTIPLE_SCATTERING'
wo.node_tree.links.new(sky.outputs[0], bg.inputs[0])
sky.altitude = 0; sky.aerosol_density = 1.6; sky.sun_intensity = 0.5
sun_d = bpy.data.lights.new("sun", 'SUN'); sun_d.angle = math.radians(0.6)
sun = bpy.data.objects.new("sun", sun_d); coll.objects.link(sun)
def set_sun(el, rot, energy, color, bgs):
    sky.sun_elevation = math.radians(el); sky.sun_rotation = math.radians(rot)
    sun.rotation_euler = Euler((math.radians(90 - el), 0, math.radians(rot + 90)))
    sun_d.energy = energy; sun_d.color = color; bg.inputs[1].default_value = bgs
SUNROT = float(os.environ.get("SUNROT", "255"))
SUNEL = float(os.environ.get("SUNEL", "10"))
set_sun(SUNEL, SUNROT, 3.8, (1.0, 0.62, 0.36), 0.17)

# ------------------------------------------------------------------ camera
cam_d = bpy.data.cameras.new("cam"); cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 36; cam_d.clip_end = 20000; cam_d.clip_start = 0.05
cam = bpy.data.objects.new("cam", cam_d); coll.objects.link(cam); sc.camera = cam
SH = [(rnd.uniform(-1, 1), rnd.uniform(-1, 1)) for _ in range(400)]
def shake(t, amp, rate=1.6):
    i = int(t*rate); f = t*rate - i; a, b_ = SH[i % 400], SH[(i+1) % 400]; f = f*f*(3-2*f)
    return (a[0]+(b_[0]-a[0])*f)*amp, (a[1]+(b_[1]-a[1])*f)*amp
def aim(loc, tgt, t, amp, fstop=None, fdist=None):
    cam.location = loc
    e = (Vector(tgt)-Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sx, sy = shake(t, amp); e.x += sx; e.z += sy; cam.rotation_euler = e
    if fstop:
        cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = fstop
        cam_d.dof.focus_distance = fdist or (Vector(tgt) - Vector(loc)).length
    else:
        cam_d.dof.use_dof = False

def pose(t):
    st = place_truck(t)
    mid = st["pos"] + Vector((0, 0, 2.0))
    if SHOT == "A":
        k = ease(t/9.6)
        cam_d.lens = lerp(105, 80, k)
        loc = Vector((-118, -8.6, road_z(-118) + 1.3))
        tgt = st["pos"] + Vector((-3, 0.8, 2.2))
        aim(loc, tgt, t, math.radians(0.04), fstop=11, fdist=(tgt - loc).length)
    elif SHOT == "B":
        u = (t - 9.6)/5.8; k = ease(u)
        cam_d.lens = 30
        p = st["pos"]
        loc = p + Vector((-30 + 4*k, lerp(5, 1, k), 15 - 2*k))
        tgt = p + Vector((14, lerp(-2, -4, k), -1.0))
        aim(loc, tgt, t, math.radians(0.12), fstop=None)
    elif SHOT == "C":
        u = (t - 15.4)/6.0; k = ease(u)
        cam_d.lens = lerp(34, 38, k)
        loc = Vector((66.5, -13.4, ramp_z(66.5) + 0.62))
        tf = st["pos"] + Vector((3.5, 0, 1.0))
        tgt = Vector((lerp(tf.x, 48, clamp((t - 18.5)/2.5)), -10.5, 1.3 + ramp_z(tf.x)))
        aim(loc, tgt, t, math.radians(0.18 + 0.25*clamp(1 - (t - 16)/4)), fstop=5.6, fdist=(tf - loc).length)
    else:
        u = (t - 21.4)/7.2; k = ease(u)
        cam_d.lens = lerp(42, 48, k)
        loc = Vector((lerp(88, 84, k), lerp(-24, -22, k), ramp_z(80) + lerp(7.5, 6.5, k)))
        tgt = Vector((50, -10.5, ramp_z(50) + 1.4))
        aim(loc, tgt, t, math.radians(0.05), fstop=8.0)

# ------------------------------------------------------------------ render
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.cycles.samples = int(os.environ.get("SPP", "10")); sc.cycles.use_denoising = True; sc.cycles.use_adaptive_sampling = True
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transparent_max_bounces = 32
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.resolution_percentage = int(os.environ.get("PCT", "50"))
sc.render.use_persistent_data = os.environ.get("PERSIST","1") == "1"
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
sc.view_settings.exposure = float(os.environ.get("EXPO", "-0.35"))

def screen(p):
    v = world_to_camera_view(sc, cam, Vector(p)); return (v.x*RES[0], (1-v.y)*RES[1], v.z)
def shot_for(t):
    for k, (a, b) in SHOTS.items():
        if a <= t < b: return k
    return "D"
END = SHOTS["D"][1]
_bed_xf = [None]
def setup(t):
    global SHOT
    SHOT = shot_for(t); pose(t)
    xf = max(0.0, wheels_world(t)[0].x + 0.6) if t > T_IN - 0.5 else 0.0
    if _bed_xf[0] is None or abs(xf - _bed_xf[0]) > 0.01:
        build_bed(xf); _bed_xf[0] = xf
    build_dyn(t)
    bpy.context.view_layer.update()
mode = sys.argv[sys.argv.index("--")+1] if "--" in sys.argv else "frames"
if mode == "test":
    for t in [float(x) for x in os.environ.get("TT", "3").split(",")]:
        setup(t)
        sc.render.filepath = f"{OUT}/test_{t}.png"; bpy.ops.render.render(write_still=True)
elif mode == "meta":
    meta = {}
    for i in range(0, int(END*FPS)):
        t = i/FPS; SHOT = shot_for(t); pose(t); st = truck_state(t); bpy.context.view_layer.update()
        p = st["pos"]
        meta[i] = {"truck": screen(p + Vector((2.0, 0, 3.6))), "front": screen(tractor.matrix_world @ Vector((5.6, -1.0, 1.0))),
                   "wheel": screen(wheels_world(t)[2]), "bed": screen((30, -10, ramp_z(30) + 0.1)),
                   "bed2": screen((55, -12.5, ramp_z(55))), "bedfar": screen((70, -10, ramp_z(70)))}
    json.dump(meta, open(f"{OUT}/meta.json", "w"))
else:
    os.makedirs(f"{OUT}/frames", exist_ok=True)
    step = int(os.environ.get("STEP", "2"))
    i0 = int(os.environ.get("IFROM", "0")); i1 = int(os.environ.get("ITO", int(END*FPS)))
    for i in range(i0, i1, step):
        out = f"{OUT}/frames/f{i:04d}.png"
        if os.path.exists(out): continue
        import time as _tm; _t0 = _tm.time()
        setup(i/FPS); _t1 = _tm.time()
        sc.render.filepath = out; bpy.ops.render.render(write_still=True)
        print(f"TIMING f{i} setup {_t1-_t0:.1f}s render {_tm.time()-_t1:.1f}s", flush=True)
