import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import bpy, bmesh, math, json, sys, os, random
from mathutils import Vector, Euler
from bpy_extras.object_utils import world_to_camera_view

FPS = 30
RES = (1080, 1920)
OUT = os.environ.get("OUT", QDIR)
SHOT = os.environ.get("SHOT", "A")
SHOTS = {"A": (0.0, 9.0), "B": (9.0, 29.6)}
R = 150.0                  # curve radius (m), curve turns left (centre at +y)
C = Vector((0, R, 0))
G2 = 0.7175                # half gauge
RC = G2 + 0.036            # rail-head centre offset
RT = 0.172                 # rail top height
R0 = 0.46                  # wheel rolling radius
TP = 0.1                   # tread taper (exaggerated a little so it reads on screen)
DMAX = 0.045               # lateral shift of the wheelset in the curve
VB = 2.5                   # m/s, close-up speed
VA = 22.0                  # m/s, wide shot speed

def ease(x):
    x = max(0.0, min(1.0, x)); return x*x*(3-2*x)
def lerp(a, b, k): return a + (b-a)*k
def arcpt(phi, o=0.0, z=0.0):
    return Vector((C.x + (R+o)*math.sin(phi), C.y - (R+o)*math.cos(phi), z))

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; coll = sc.collection
rnd = random.Random(5)

def principled(name, color, rough=0.5, metal=0.0, coat=0.0, emit=None, estr=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal; b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = estr
    return m
def noisy(name, c1, c2, scale=2.0, rough=0.8, metal=0.0, bump=0.3):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = 10; nz.inputs["Roughness"].default_value = 0.65
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    rp = nt.nodes.new("ShaderNodeValToRGB"); rp.color_ramp.elements[0].color = (*c1, 1); rp.color_ramp.elements[1].color = (*c2, 1)
    rp.color_ramp.elements[0].position = 0.3; rp.color_ramp.elements[1].position = 0.7
    nt.links.new(nz.outputs["Fac"], rp.inputs[0]); nt.links.new(rp.outputs[0], b.inputs["Base Color"])
    if bump:
        bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump
        nt.links.new(nz.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs[0], b.inputs["Normal"])
    return m
def obj_from_bm(name, bm, mat=None, smooth=False, parent=None):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); coll.objects.link(o)
    if mat: o.data.materials.append(mat)
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    if parent: o.parent = parent
    return o
def box(name, size, loc, mat, parent=None, rot=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object; o.name = name; o.scale = size; o.data.materials.append(mat)
    if rot: o.rotation_euler = rot
    if parent: o.parent = parent
    return o
def cyl(name, r, depth, loc, mat, rot=(0, 0, 0), parent=None, verts=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name; o.data.materials.append(mat)
    for p in o.data.polygons: p.use_smooth = True
    if parent: o.parent = parent
    return o

# ------------------------------------------------------------------ materials
M_RAIL = noisy("rail", (0.16, 0.07, 0.035), (0.30, 0.15, 0.07), 6, 0.75, 0.3, 0.2)
M_HEAD = principled("railhead", (0.62, 0.62, 0.63), 0.18, 1.0)
M_SLEEPER = noisy("sleeper", (0.36, 0.35, 0.33), (0.52, 0.50, 0.47), 5, 0.9, 0.0, 0.4)
M_BALLAST = bpy.data.materials.new("ballast"); M_BALLAST.use_nodes = True
nt = M_BALLAST.node_tree; b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.95
tc = nt.nodes.new("ShaderNodeTexCoord"); vo = nt.nodes.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 18
nt.links.new(tc.outputs["Object"], vo.inputs["Vector"])
rp = nt.nodes.new("ShaderNodeValToRGB"); rp.color_ramp.elements[0].color = (0.10, 0.09, 0.08, 1); rp.color_ramp.elements[1].color = (0.42, 0.39, 0.35, 1)
nt.links.new(vo.outputs["Color"], rp.inputs[0]); nt.links.new(rp.outputs[0], b.inputs["Base Color"])
bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.9; bp.inputs["Distance"].default_value = 0.05
nt.links.new(vo.outputs["Distance"], bp.inputs["Height"]); nt.links.new(bp.outputs[0], b.inputs["Normal"])
M_GRASS = noisy("grass", (0.07, 0.09, 0.02), (0.30, 0.25, 0.08), 0.05, 0.9, 0.0, 0.2)
M_TREE = noisy("tree", (0.03, 0.06, 0.015), (0.12, 0.14, 0.03), 0.6, 0.9, 0.0, 0.6)
M_TRUNK = principled("trunk", (0.08, 0.05, 0.03), 0.9)
M_STEEL = principled("steel", (0.55, 0.55, 0.56), 0.22, 1.0)
M_GRIME = noisy("grime", (0.035, 0.03, 0.028), (0.12, 0.09, 0.07), 8, 0.7, 0.5, 0.3)
M_FRAME = noisy("frame", (0.025, 0.025, 0.028), (0.07, 0.065, 0.06), 4, 0.6, 0.3, 0.2)
M_YEL = principled("mark", (0.85, 0.55, 0.05), 0.5)

trackRoot = bpy.data.objects.new("trackRoot", None); coll.objects.link(trackRoot); trackRoot.location = C
def sweep(name, prof, phis, mat, closed=True, parent=trackRoot):
    """prof: list of (o, z) radial offset/height; swept along the arc, local to C."""
    bm = bmesh.new(); rings = []
    for ph in phis:
        rings.append([bm.verts.new(arcpt(ph, o, z) - C) for (o, z) in prof])
    n = len(prof)
    for i in range(len(rings)-1):
        for j in range(n if closed else n-1):
            a, b_, c, d = rings[i][j], rings[i+1][j], rings[i+1][(j+1) % n], rings[i][(j+1) % n]
            bm.faces.new([a, b_, c, d])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj_from_bm(name, bm, mat, parent=parent)

if SHOT == "A":
    PH0, PH1, NSEG = -0.9, 1.3, 900
else:
    PH0, PH1, NSEG = -0.25, 0.45, 420
phis = [PH0 + (PH1-PH0)*k/NSEG for k in range(NSEG+1)]
RAILP = [(-0.075, 0), (-0.075, 0.012), (-0.009, 0.03), (-0.009, 0.135), (-0.036, 0.142), (-0.036, 0.168), (-0.03, 0.172),
         (0.03, 0.172), (0.036, 0.168), (0.036, 0.142), (0.009, 0.135), (0.009, 0.03), (0.075, 0.012), (0.075, 0)]
for s, oc in (("out", RC), ("in", -RC)):
    sweep(f"rail_{s}", [(oc+o, z) for (o, z) in RAILP], phis, M_RAIL)
    sweep(f"head_{s}", [(oc-0.031, RT+0.0008), (oc+0.031, RT+0.0008)], phis, M_HEAD, closed=False)
# ballast bed + shoulders
sweep("ballast", [(-3.6, -0.55), (-2.0, -0.04), (2.0, -0.04), (3.6, -0.55)], phis, M_BALLAST, closed=False)
# sleepers (one mesh)
bm = bmesh.new(); sp = 0.6/R
k = 0; ph = PH0
while ph < PH1:
    res = bmesh.ops.create_cube(bm, size=1.0)
    for v in res["verts"]:
        o = v.co.y*2.6; z = v.co.z*0.2 - 0.1; dx = v.co.x*0.26
        p = arcpt(ph + dx/R, o, z) - C
        v.co = p
    ph += sp; k += 1
obj_from_bm("sleepers", bm, M_SLEEPER, parent=trackRoot)
# ground, trees, hills
bpy.ops.mesh.primitive_plane_add(size=6000, location=(0, 0, -0.5)); g = bpy.context.object; g.data.materials.append(M_GRASS); g.parent = trackRoot
g.location = (0, -R, -0.5)
for k in range(260 if SHOT == "A" else 60):
    ph = rnd.uniform(PH0-0.3, PH1+0.3); o = rnd.choice([-1, 1])*rnd.uniform(14, 160)
    if SHOT == "B" and abs(o) < 25: continue
    p = arcpt(ph, o, -0.5)
    if SHOT == "A" and ((p - arcpt(0.62, 14, 0)).length < 70 or (abs(o) < 30 and ph > 0.1)): continue
    h = rnd.uniform(6, 15)
    cyl(f"trunk{k}", 0.25, h*0.5, (p.x, p.y, h*0.25-0.5), M_TRUNK, parent=None, verts=8)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1, location=(p.x, p.y, h*0.62-0.5))
    t_ = bpy.context.object; t_.name = f"tree{k}"; t_.scale = (h*0.3, h*0.3, h*0.42); t_.data.materials.append(M_TREE)
    d = t_.modifiers.new("d", 'DISPLACE'); tx = bpy.data.textures.new(f"tt{k}", 'CLOUDS'); tx.noise_scale = 0.5; d.texture = tx; d.strength = 0.8
for k in range(9):
    a = rnd.uniform(-0.6, 3.6); dist = rnd.uniform(1400, 2400)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1, location=(math.cos(a)*dist, math.sin(a)*dist + R, -60))
    hl = bpy.context.object; hl.scale = (rnd.uniform(500, 900), rnd.uniform(500, 900), rnd.uniform(130, 260)); hl.data.materials.append(M_TREE)
for o in list(coll.objects):
    if o.name.startswith(("trunk", "tree")): o.parent = trackRoot; o.matrix_parent_inverse = trackRoot.matrix_world.inverted()

# ------------------------------------------------------------------ wheelset (local: axle along y, centre at origin)
def wheel_bm(bm, side):
    r = lambda a: R0 - (a-0.0735)*TP
    rf = r(0.032) + 0.03
    prof = [(0.0, 0.13), (0.0, rf-0.014), (0.006, rf-0.002), (0.016, rf), (0.026, rf-0.006), (0.031, r(0.032)+0.004),
            (0.036, r(0.036)), (0.135, r(0.135)), (0.14, r(0.135)-0.012), (0.14, R0-0.07), (0.11, R0-0.10),
            (0.07, 0.24), (0.11, 0.15), (0.12, 0.13)]
    N = 64; rings = []
    for u in range(N):
        ang = 2*math.pi*u/N
        rings.append([bm.verts.new((rr*math.cos(ang), side*(0.68+a), rr*math.sin(ang))) for (a, rr) in prof])
    n = len(prof)
    for u in range(N):
        for j in range(n):
            a_, b_, c_, d_ = rings[u][j], rings[(u+1) % N][j], rings[(u+1) % N][(j+1) % n], rings[u][(j+1) % n]
            bm.faces.new([a_, b_, c_, d_])
def make_wheelset(name, x, simple=False):
    root = bpy.data.objects.new(name, None); coll.objects.link(root); root.rotation_mode = 'YXZ'
    bm = bmesh.new(); wheel_bm(bm, 1); wheel_bm(bm, -1); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    w = obj_from_bm(name+"_wheels", bm, M_STEEL, smooth=True, parent=root)
    cyl(name+"_axle", 0.08, 2.1, (0, 0, 0), M_GRIME, rot=(math.pi/2, 0, 0), parent=root)
    if not simple:
        for s in (-1, 1):
            # bolt circle + paint mark so the rotation reads
            for kk in range(6):
                an = kk*math.pi/3
                cyl(name+f"_bolt{s}{kk}", 0.022, 0.05, (0.19*math.cos(an), s*0.82, 0.19*math.sin(an)), M_GRIME, rot=(math.pi/2, 0, 0), parent=root, verts=8)
            box(name+f"_mark{s}", (0.03, 0.01, 0.12), (0, s*0.825, 0.33), M_YEL, parent=root)
            cyl(name+f"_hub{s}", 0.13, 0.16, (0, s*0.86, 0), M_GRIME, rot=(math.pi/2, 0, 0), parent=root)
    root.location = (x, 0, RT+R0)
    return root

def make_bogie(name, xc, simple=False):
    root = bpy.data.objects.new(name, None); coll.objects.link(root)
    ws = [make_wheelset(name+"w0", 1.25, simple), make_wheelset(name+"w1", -1.25, simple)]
    for w_ in ws: w_.parent = root
    for s in (-1, 1):
        box(name+f"side{s}", (3.6, 0.2, 0.32), (0, s*1.02, RT+R0+0.12), M_FRAME, parent=root)
        for xx in (1.25, -1.25):
            box(name+f"abox{s}{xx}", (0.42, 0.26, 0.3), (xx, s*1.0, RT+R0), M_FRAME, parent=root)
            if not simple:
                for dy in (-0.07, 0.07):
                    cyl(name+f"spr{s}{xx}{dy}", 0.075, 0.24, (xx+dy*2.2, s*1.02, RT+R0+0.4), M_YEL if False else M_GRIME, parent=root, verts=16)
    box(name+"cross", (0.5, 2.0, 0.34), (0, 0, RT+R0+0.1), M_FRAME, parent=root)
    if not simple:
        for s in (-1, 1):
            cyl(name+f"damp{s}", 0.05, 0.6, (0.5, s*0.75, RT+R0+0.3), M_STEEL, rot=(0, 0.9, 0), parent=root, verts=12)
            box(name+f"brake{s}", (0.5, 0.12, 0.18), (0.2, s*0.3, RT+R0+0.38), M_FRAME, parent=root)
    root.location = (xc, 0, 0)
    return root, ws

# ------------------------------------------------------------------ train body
M_BODY = bpy.data.materials.new("body"); M_BODY.use_nodes = True; nt = M_BODY.node_tree
b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.28; b.inputs["Coat Weight"].default_value = 0.6; b.inputs["Metallic"].default_value = 0.3
tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep.inputs[0])
mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[1].default_value = -1.8; mr.inputs[2].default_value = 1.8
nt.links.new(sep.outputs["Z"], mr.inputs[0])
ramp = nt.nodes.new("ShaderNodeValToRGB"); cr = ramp.color_ramp; cr.interpolation = 'CONSTANT'
cr.elements[0].position = 0.0; cr.elements[0].color = (0.05, 0.05, 0.055, 1)
cr.elements[1].position = 0.12; cr.elements[1].color = (0.62, 0.035, 0.03, 1)
for pos, col in ((0.24, (0.72, 0.72, 0.70)), (0.50, (0.012, 0.015, 0.02)), (0.74, (0.72, 0.72, 0.70))):
    e = cr.elements.new(pos); e.color = (*col, 1)
nt.links.new(mr.outputs[0], ramp.inputs[0]); nt.links.new(ramp.outputs[0], b.inputs["Base Color"])
BODY_Z = RT + 1.2 + 1.8

def make_car(name, lead=False, simple=True):
    root = bpy.data.objects.new(name, None); coll.objects.link(root)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, BODY_Z)); bd = bpy.context.object; bd.name = name+"_body"
    bd.scale = (25.0 if not lead else 22.0, 2.9, 3.6); bd.data.materials.append(M_BODY); bd.parent = root
    bv = bd.modifiers.new("bv", 'BEVEL'); bv.width = 0.35; bv.segments = 5
    if lead:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1, location=(11.0, 0, BODY_Z))
        n = bpy.context.object; n.name = name+"_nose"; n.scale = (5.0, 1.45, 1.8); n.data.materials.append(M_BODY); n.parent = root
        for p in n.data.polygons: p.use_smooth = True
        cyl(name+"_lamp", 0.12, 0.05, (15.6, 0.7, BODY_Z-0.6), principled("lamp", (1, 1, 1), 0.2, emit=(1, 0.9, 0.7), estr=40), rot=(0, math.pi/2, 0), parent=root)
        cyl(name+"_lamp2", 0.12, 0.05, (15.6, -0.7, BODY_Z-0.6), bpy.data.materials["lamp"], rot=(0, math.pi/2, 0), parent=root)
    box(name+"_skirt", (24.0 if not lead else 21.0, 2.6, 0.5), (0, 0, RT+1.15), M_FRAME, parent=root)
    bogies = []
    for xb in ((-9.0, 9.0) if not lead else (-7.5, 8.0)):
        bg_, ws = make_bogie(name+f"_bg{xb}", xb, simple); bg_.parent = root; bogies.append((bg_, ws, xb))
    return root, bogies

# ------------------------------------------------------------------ environment
wo = bpy.data.worlds.new("w"); sc.world = wo; wo.use_nodes = True
bg = wo.node_tree.nodes["Background"]
sky = wo.node_tree.nodes.new("ShaderNodeTexSky"); sky.sky_type = 'MULTIPLE_SCATTERING'
wo.node_tree.links.new(sky.outputs[0], bg.inputs[0])
SUN_ROT = 300 if SHOT == "A" else 15
sky.sun_elevation = math.radians(7); sky.sun_rotation = math.radians(SUN_ROT); sky.altitude = 0; sky.aerosol_density = 1.6; sky.sun_intensity = 0.5
bg.inputs[1].default_value = 0.18 if SHOT == "A" else 0.32
sun_d = bpy.data.lights.new("sun", 'SUN'); sun_d.energy = 3.4; sun_d.color = (1.0, 0.70, 0.48); sun_d.angle = math.radians(0.6)
sun = bpy.data.objects.new("sun", sun_d); coll.objects.link(sun)
sun.rotation_euler = Euler((math.radians(83), 0, math.radians(SUN_ROT+90)))

cam_d = bpy.data.cameras.new("cam"); cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 36; cam_d.clip_end = 100000; cam_d.clip_start = 0.02
cam = bpy.data.objects.new("cam", cam_d); coll.objects.link(cam); sc.camera = cam
SH = [(rnd.uniform(-1, 1), rnd.uniform(-1, 1)) for _ in range(400)]
def shake(t, amp, rate=2.5):
    i = int(t*rate); f = t*rate - i; a, b_ = SH[i % 400], SH[(i+1) % 400]; f = f*f*(3-2*f)
    return (a[0]+(b_[0]-a[0])*f)*amp, (a[1]+(b_[1]-a[1])*f)*amp
def aim(loc, tgt, t, amp, rate=2.5):
    cam.location = loc
    e = (Vector(tgt)-Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sx, sy = shake(t, amp, rate); e.x += sx; e.z += sy; cam.rotation_euler = e

META_PTS = {}
if SHOT == "A":
    cars = [make_car("car0", lead=True)] + [make_car(f"car{k}") for k in (1, 2, 3)]
    LENS = [22.0+5.5, 25.0+1.2, 25.0+1.2, 25.0+1.2]
    def place(t):
        s = -60 + VA*t
        for k, (root, bogies) in enumerate(cars):
            if k > 0: s -= (24.2 if k == 1 else 25.6)
            ph = s/R
            root.location = arcpt(ph); root.rotation_euler = (0, 0, ph)
            for (bg_, ws, xb) in bogies:
                # bogies follow the curve: small yaw relative to body
                bg_.rotation_euler = (0, 0, xb/R)
                bg_.location = (xb, (xb*xb)/(2*R), 0)
                for w_ in ws: w_.rotation_euler = (0, -VA*t/R0, 0)
        return s
    def pose(t):
        s = place(t)
        k = ease(t/9.0)
        lead = arcpt(s/R + 2/R, 0, 2.2)
        cam_d.lens = 38
        loc = arcpt(0.62, 14, 5.5)
        mid = arcpt(0.2, 0, 1.5)
        tgt = mid.lerp(lead, 0.35 + 0.5*k)
        aim(loc, tgt, t, math.radians(0.15))
else:
    bogie, WS = make_bogie("bogie", 0.0, simple=False)
    # car floor above + underfloor equipment
    box("floor", (30, 2.9, 0.25), (-11, 0, RT+1.25), M_FRAME)
    for k_ in range(6):
        box(f"uf{k_}", (rnd.uniform(1.2, 2.4), rnd.uniform(1.2, 2.0), rnd.uniform(0.4, 0.6)), (-4.5 - k_*3.3, rnd.uniform(-0.3, 0.3), RT+0.95), M_GRIME)
    def lat(t): return DMAX*ease((t-19.8)/2.0)
    def pose(t):
        s = VB*(t-9.0)
        trackRoot.rotation_euler = (0, 0, -s/R)
        d = lat(t)
        bogie.location = (0, -d, 0)
        for w_, xx in zip(WS, (1.25, -1.25)):
            yc = (xx*xx)/(2*R)
            w_.location = (xx, yc, RT+R0)
            w_.rotation_euler = (math.atan(2*d*TP/(2*RC)) * (1 if xx > 0 else 1), -s/R0, xx/R)
        # camera
        k1 = ease((t-13.6)/3.6); k2 = ease((t-18.0)/11.0)
        loc = Vector((lerp(5.0, 3.9, k1), lerp(-3.2, 0.0, k1), lerp(0.9, 0.36, k1)))
        loc.x -= 0.35*k2
        tgt = Vector((lerp(0.8, 1.25, k1), lerp(-0.4, -0.0, k1), lerp(0.45, 0.40, k1)))
        cam_d.lens = lerp(26, 30, k1)
        aim(loc, tgt, t, math.radians(0.12), 3.0)

# ------------------------------------------------------------------ render
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.cycles.samples = int(os.environ.get("SPP", "14")); sc.cycles.use_denoising = True; sc.cycles.use_adaptive_sampling = True
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transparent_max_bounces = 6
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.resolution_percentage = int(os.environ.get("PCT", "60"))
sc.render.use_persistent_data = True
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
sc.view_settings.exposure = float(os.environ.get("EXPO", "0.0"))

def screen(p):
    v = world_to_camera_view(sc, cam, Vector(p)); return (v.x*RES[0], (1-v.y)*RES[1], v.z)

t0, t1 = SHOTS[SHOT]
mode = sys.argv[sys.argv.index("--")+1] if "--" in sys.argv else "frames"
if mode == "test":
    for t in [float(x) for x in os.environ.get("TT", str((t0+t1)/2)).split(",")]:
        pose(t); bpy.context.view_layer.update()
        sc.render.filepath = f"{OUT}/test{SHOT}_{t}.png"; bpy.ops.render.render(write_still=True)
elif mode == "meta":
    meta = {}
    for i in range(int(round(t0*FPS)), int(round(t1*FPS))):
        t = i/FPS; pose(t); bpy.context.view_layer.update()
        if SHOT == "B":
            w0 = WS[0].matrix_world
            d = lat(t)
            m = {"wO": screen(w0 @ Vector((0, -(0.68+0.0735-d), -R0-0.0))),
                 "wI": screen(w0 @ Vector((0, (0.68+0.0735+d), -R0))),
                 "cO": screen(w0 @ Vector((0, -0.75, 0))), "cI": screen(w0 @ Vector((0, 0.75, 0))),
                 "topO": screen(w0 @ Vector((0, -0.75, R0))), "topI": screen(w0 @ Vector((0, 0.75, R0))),
                 "axle": screen(w0 @ Vector((0, 0, 0))),
                 "railO": [screen(arcpt(p, RC, RT)) for p in [k/R for k in range(0, 40, 2)]],
                 "railI": [screen(arcpt(p, -RC, RT)) for p in [k/R for k in range(0, 40, 2)]]}
        else:
            m = {}
        meta[i] = m
    json.dump(meta, open(f"{OUT}/meta{SHOT}.json", "w"))
else:
    os.makedirs(f"{OUT}/frames", exist_ok=True)
    step = int(os.environ.get("STEP", "2"))
    for i in range(int(os.environ.get("IFROM", int(round(t0*FPS)))), int(os.environ.get("ITO", int(round(t1*FPS)))), step):
        out = f"{OUT}/frames/f{i:04d}.png"
        if os.path.exists(out): continue
        pose(i/FPS); bpy.context.view_layer.update()
        sc.render.filepath = out; bpy.ops.render.render(write_still=True)
