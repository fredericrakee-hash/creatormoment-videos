import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import bpy, bmesh, math, json, sys, os, random
from mathutils import Vector, Euler, Matrix
from bpy_extras.object_utils import world_to_camera_view

FPS = 30
RES = (1080, 1920)
OUT = os.environ.get("OUT", QDIR)
SHOT = os.environ.get("SHOT", "A")
SHOTS = {"A": (0.0, 7.6), "B": (7.6, 27.0)}
V = 9.0                                   # m/s (~32 km/h)
AIM = Vector((math.cos(math.radians(-9)), math.sin(math.radians(-9)), 0.01)).normalized()   # world direction to the target
X0 = -40.0

def ease(x):
    x = max(0.0, min(1.0, x)); return x*x*(3-2*x)
def lerp(a, b, k): return a + (b-a)*k

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; coll = sc.collection
rnd = random.Random(21)

def principled(name, color, rough=0.5, metal=0.0, coat=0.0, emit=None, estr=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal; b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = estr
    return m
def noisy(name, c1, c2, scale=2.0, rough=0.8, metal=0.0, bump=0.3, coord="Object"):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = 10; nz.inputs["Roughness"].default_value = 0.65
    nt.links.new(tc.outputs[coord], nz.inputs["Vector"])
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
def cyl(name, r, depth, loc, mat, rot=(0, 0, 0), parent=None, verts=32, r2=None):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=depth, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name; o.data.materials.append(mat)
    for p in o.data.polygons: p.use_smooth = True
    if parent: o.parent = parent
    return o
def prism(name, pts_xz, y0, y1, mat, parent=None, bevel=0.04):
    """extrude a closed x-z polygon along y"""
    bm = bmesh.new()
    a = [bm.verts.new((x, y0, z)) for (x, z) in pts_xz]; b_ = [bm.verts.new((x, y1, z)) for (x, z) in pts_xz]
    n = len(pts_xz)
    bm.faces.new(a); bm.faces.new(list(reversed(b_)))
    for i in range(n):
        bm.faces.new([a[i], a[(i+1) % n], b_[(i+1) % n], b_[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = obj_from_bm(name, bm, mat, parent=parent)
    if bevel:
        bv = o.modifiers.new("bv", 'BEVEL'); bv.width = bevel; bv.segments = 2; bv.limit_method = 'ANGLE'
    return o

# ------------------------------------------------------------------ terrain
def hgt(x, y):
    """rolling, bumpy dirt track (metres)"""
    h = 0.55*math.sin(x*0.42 + 0.3) + 0.35*math.sin(x*0.23 + 1.7) + 0.22*math.sin(x*0.91 + 0.8)
    h *= 0.15 + 0.85*math.exp(-(y/5.0)**2)
    return h + low(x, y) + 0.04*math.sin(y*1.3+x*0.7)
def low(x, y):
    return 1.6*math.sin(x*0.011 + 0.4)*math.cos(y*0.02)
M_DIRT = noisy("dirt", (0.13, 0.085, 0.05), (0.36, 0.27, 0.17), 0.6, 0.95, 0.0, 0.5)
# add grass patches over the dirt
nt = M_DIRT.node_tree; b = nt.nodes["Principled BSDF"]; old = b.inputs["Base Color"].links[0].from_socket
tc = nt.nodes.new("ShaderNodeTexCoord"); nz2 = nt.nodes.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = 0.06; nz2.inputs["Detail"].default_value = 6
nt.links.new(tc.outputs["Object"], nz2.inputs["Vector"])
rp2 = nt.nodes.new("ShaderNodeValToRGB"); rp2.color_ramp.elements[0].position = 0.5; rp2.color_ramp.elements[1].position = 0.62
mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = 'RGBA'
nt.links.new(nz2.outputs["Fac"], rp2.inputs[0]); nt.links.new(rp2.outputs[0], mx.inputs["Factor"])
nt.links.new(old, mx.inputs[6]); mx.inputs[7].default_value = (0.11, 0.11, 0.035, 1)
nt.links.new(mx.outputs[2], b.inputs["Base Color"])

XA, XB = (-140, 120) if SHOT == "A" else (-60, 330)
NX, NY = int((XB-XA)/0.6), 80
YA, YB = -70, 70
bm = bmesh.new(); grid = []
for i in range(NX+1):
    x = XA + (XB-XA)*i/NX; row = []
    for j in range(NY+1):
        u = j/NY; y = YA + (YB-YA)*(u**1.0)
        row.append(bm.verts.new((x, y, hgt(x, y))))
    grid.append(row)
for i in range(NX):
    for j in range(NY):
        bm.faces.new([grid[i][j], grid[i+1][j], grid[i+1][j+1], grid[i][j+1]])
ground = obj_from_bm("ground", bm, M_DIRT, smooth=True)
bpy.ops.mesh.primitive_plane_add(size=20000, location=(0, 0, -2.2)); bpy.context.object.data.materials.append(M_DIRT)
M_BUSH = noisy("bush", (0.05, 0.06, 0.02), (0.20, 0.17, 0.06), 1.5, 0.9, 0.0, 0.5)
for k in range(220):
    x = rnd.uniform(XA, XB); y = rnd.choice([-1, 1])*rnd.uniform(9, 70)
    if SHOT == "A" and -35 < y < -14: continue
    s = rnd.uniform(0.4, 1.4)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=(x, y, hgt(x, y) + s*0.2))
    o = bpy.context.object; o.name = f"bush{k}"; o.scale = (s*1.3, s*1.1, s*0.7); o.data.materials.append(M_BUSH)
for k in range(10):
    a = rnd.uniform(-1.2, 2.2); dist = rnd.uniform(1400, 2600)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1, location=(math.cos(a)*dist+200, math.sin(a)*dist, -60))
    hl = bpy.context.object; hl.scale = (rnd.uniform(500, 900), rnd.uniform(500, 900), rnd.uniform(110, 230)); hl.data.materials.append(M_BUSH)
# tread ruts / tracks of earlier vehicles (dark strips)

# ------------------------------------------------------------------ tank
M_CAMO = bpy.data.materials.new("camo"); M_CAMO.use_nodes = True; nt = M_CAMO.node_tree
b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.72
tc = nt.nodes.new("ShaderNodeTexCoord"); n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 0.35; n1.inputs["Detail"].default_value = 2
n1.inputs["Distortion"].default_value = 0.6
nt.links.new(tc.outputs["Object"], n1.inputs["Vector"])
rp = nt.nodes.new("ShaderNodeValToRGB"); cr = rp.color_ramp; cr.interpolation = 'CONSTANT'
cr.elements[0].position = 0.0; cr.elements[0].color = (0.035, 0.045, 0.03, 1)
cr.elements[1].position = 0.42; cr.elements[1].color = (0.075, 0.085, 0.045, 1)
e = cr.elements.new(0.58); e.color = (0.10, 0.068, 0.04, 1)
nt.links.new(n1.outputs["Fac"], rp.inputs[0])
nd = nt.nodes.new("ShaderNodeTexNoise"); nd.inputs["Scale"].default_value = 3.0; nd.inputs["Detail"].default_value = 12
nt.links.new(tc.outputs["Object"], nd.inputs["Vector"])
dust = nt.nodes.new("ShaderNodeMix"); dust.data_type = 'RGBA'; dust.inputs["Factor"].default_value = 0.0
mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[1].default_value = 0.45; mr.inputs[2].default_value = 0.75; mr.inputs[4].default_value = 0.55
nt.links.new(nd.outputs["Fac"], mr.inputs[0]); nt.links.new(mr.outputs[0], dust.inputs["Factor"])
nt.links.new(rp.outputs[0], dust.inputs[6]); dust.inputs[7].default_value = (0.30, 0.24, 0.16, 1)
nt.links.new(dust.outputs[2], b.inputs["Base Color"])
bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.12
nt.links.new(nd.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs[0], b.inputs["Normal"])
M_TRACK = noisy("track", (0.02, 0.02, 0.02), (0.10, 0.085, 0.07), 9, 0.65, 0.6, 0.6)
M_RUB = principled("rubber", (0.025, 0.025, 0.025), 0.8)
M_DARK = principled("darkmetal", (0.03, 0.03, 0.03), 0.4, 0.6)
M_GLASS = principled("glass", (0.01, 0.015, 0.02), 0.05, coat=1.0)

tank = bpy.data.objects.new("tank", None); coll.objects.link(tank); tank.rotation_mode = 'XYZ'
hullE = bpy.data.objects.new("hullE", None); coll.objects.link(hullE); hullE.parent = tank   # hull (suspension moves it)
# lower hull + upper hull with sloped glacis
prism("lowhull", [(-3.7, 0.45), (3.3, 0.45), (3.95, 1.05), (3.9, 1.3), (-3.75, 1.3)], -1.2, 1.2, M_CAMO, hullE)
prism("uphull", [(-3.85, 1.25), (3.95, 1.25), (4.0, 1.36), (1.6, 1.82), (-3.7, 1.82), (-3.9, 1.6)], -1.86, 1.86, M_CAMO, hullE)
for s in (-1, 1):
    box(f"skirt{s}", (7.3, 0.08, 0.62), (0.15, s*1.83, 1.0), M_CAMO, hullE)
    for k in range(5):
        box(f"skseam{s}{k}", (0.03, 0.09, 0.6), (-3.0 + k*1.5, s*1.835, 1.0), M_DARK, hullE)
    box(f"fender{s}", (0.9, 0.5, 0.05), (3.75, s*1.6, 1.33), M_CAMO, hullE, rot=(0, 0.25, 0))
    cyl(f"light{s}", 0.09, 0.08, (3.92, s*1.45, 1.42), principled("lamp", (1, 1, 1), 0.2, emit=(1, 0.85, 0.6), estr=6), rot=(0, math.pi/2, 0), parent=hullE)
box("driverhatch", (0.8, 0.7, 0.1), (2.6, -0.5, 1.84), M_CAMO, hullE)
for k in range(3):
    box(f"periscope{k}", (0.12, 0.18, 0.08), (3.0, -0.75 + k*0.25, 1.86), M_GLASS, hullE)
for s in (-1, 1):
    box(f"stow{s}", (1.4, 0.45, 0.4), (-3.1, s*1.35, 2.0), M_CAMO, hullE)
box("engdeck", (2.8, 3.1, 0.06), (-2.3, 0, 1.84), M_DARK, hullE)
# tracks + road wheels (attached to the tank root so the hull can bounce on its suspension)
TR = []
for s in (-1, 1):
    pts = []
    for k in range(24):
        a = math.pi/2 + math.pi*k/23
        pts.append((-3.55 + 0.42*math.cos(a), 0.47 + 0.42*math.sin(a)))
    for k in range(24):
        a = -math.pi/2 + math.pi*k/23
        pts.append((3.45 + 0.45*math.cos(a)*1.0, 0.62 + 0.45*math.sin(a)*1.05))
    trk = prism(f"track{s}", pts, s*1.18, s*1.84, M_TRACK, tank, bevel=0.03)
    TR.append(trk)
    for k in range(7):
        cyl(f"rw{s}{k}", 0.34, 0.5, (-2.85 + k*0.95, s*1.5, 0.4), M_RUB, rot=(math.pi/2, 0, 0), parent=tank)
# turret
turret = bpy.data.objects.new("turret", None); coll.objects.link(turret); turret.parent = hullE; turret.location = (-0.35, 0, 1.82)
bm = bmesh.new()
poly = [(2.0, -0.6), (1.75, -1.55), (-1.6, -1.65), (-2.3, -1.3), (-2.3, 1.3), (-1.6, 1.65), (1.75, 1.55), (2.0, 0.6)]
lo = [bm.verts.new((x, y, 0.0)) for (x, y) in poly]; hi = [bm.verts.new((x*0.96, y*0.93, 0.82)) for (x, y) in poly]
bm.faces.new(list(reversed(lo))); bm.faces.new(hi)
for i in range(len(poly)):
    bm.faces.new([lo[i], lo[(i+1) % len(poly)], hi[(i+1) % len(poly)], hi[i]])
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
tb = obj_from_bm("turretbody", bm, M_CAMO, parent=turret); bv = tb.modifiers.new("bv", 'BEVEL'); bv.width = 0.05; bv.segments = 2
box("bustle", (1.0, 2.6, 0.55), (-2.65, 0, 0.42), M_CAMO, turret)
box("cmdsight", (0.45, 0.45, 0.42), (0.2, 0.95, 1.0), M_CAMO, turret)
box("cmdsightwin", (0.05, 0.3, 0.2), (0.43, 0.95, 1.05), M_GLASS, turret)
box("gunsight", (0.55, 0.4, 0.3), (1.4, -1.0, 0.95), M_CAMO, turret)
box("gunsightwin", (0.05, 0.3, 0.18), (1.68, -1.0, 0.97), M_GLASS, turret)
cyl("hatch", 0.38, 0.08, (-0.6, 0.7, 0.86), M_CAMO, parent=turret)
cyl("mg", 0.03, 1.0, (-0.4, -0.7, 1.05), M_DARK, rot=(0, math.pi/2, 0), parent=turret, verts=12)
for s in (-1, 1):
    for k in range(4):
        cyl(f"smoke{s}{k}", 0.055, 0.25, (0.6 - k*0.17, s*1.62, 0.65), M_DARK, rot=(s*0.6, -0.4, 0), parent=turret, verts=12)
cyl("ant1", 0.008, 2.4, (-2.4, 1.1, 1.85), M_DARK, parent=turret, verts=6)
cyl("ant2", 0.008, 2.0, (-2.4, -1.1, 1.65), M_DARK, parent=turret, verts=6)
# barrel on its trunnion
gun = bpy.data.objects.new("barrelpivot", None); coll.objects.link(gun); gun.parent = turret; gun.location = (1.7, 0, 0.45)
box("mantlet", (0.55, 0.85, 0.6), (0.1, 0, 0), M_CAMO, gun)
cyl("barrel", 0.105, 3.0, (1.85, 0, 0), M_CAMO, rot=(0, math.pi/2, 0), parent=gun)
cyl("barrel2", 0.09, 2.6, (4.6, 0, 0), M_CAMO, rot=(0, math.pi/2, 0), parent=gun)
cyl("evac", 0.16, 0.6, (3.1, 0, 0), M_CAMO, rot=(0, math.pi/2, 0), parent=gun)
cyl("muzzleref", 0.1, 0.12, (5.95, 0, 0), M_DARK, rot=(0, math.pi/2, 0), parent=gun)
MUZZLE = Vector((5.95, 0, 0))

# dust puffs (volume) kicked up behind the tracks
M_DUST = bpy.data.materials.new("dust"); M_DUST.use_nodes = True; nt = M_DUST.node_tree
nt.nodes.remove(nt.nodes["Principled BSDF"])
vs = nt.nodes.new("ShaderNodeVolumePrincipled"); vs.inputs["Color"].default_value = (0.55, 0.42, 0.30, 1)
tcd = nt.nodes.new("ShaderNodeTexCoord"); nzd = nt.nodes.new("ShaderNodeTexNoise"); nzd.inputs["Scale"].default_value = 1.6; nzd.inputs["Detail"].default_value = 4
nt.links.new(tcd.outputs["Object"], nzd.inputs["Vector"])
gr = nt.nodes.new("ShaderNodeTexGradient"); gr.gradient_type = 'SPHERICAL'; nt.links.new(tcd.outputs["Object"], gr.inputs["Vector"])
mul = nt.nodes.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'; nt.links.new(nzd.outputs["Fac"], mul.inputs[0]); nt.links.new(gr.outputs["Fac"], mul.inputs[1])
den = nt.nodes.new("ShaderNodeMath"); den.operation = 'MULTIPLY'; den.name = "den"; den.inputs[1].default_value = 0.0
nt.links.new(mul.outputs[0], den.inputs[0]); nt.links.new(den.outputs[0], vs.inputs["Density"])
nt.links.new(vs.outputs[0], nt.nodes["Material Output"].inputs["Volume"])
PUFFS = []
for k in range(0):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=(0, 0, -50))
    p = bpy.context.object; p.name = f"puff{k}"; m = M_DUST.copy(); p.data.materials.append(m); PUFFS.append((p, m))

def tank_state(t):
    x = X0 + V*t
    zf = hgt(x+2.6, -1.5)*0.5 + hgt(x+2.6, 1.5)*0.5; zr = hgt(x-2.6, -1.5)*0.5 + hgt(x-2.6, 1.5)*0.5
    zl = hgt(x, 1.5); zr_ = hgt(x, -1.5)
    pitch = math.atan2(zf-zr, 5.2); roll = math.atan2(zl-zr_, 3.0)
    return Vector((x, 0, (zf+zr)/2)), pitch, roll

def pose(t):
    loc, pitch, roll = tank_state(t)
    # suspension lag: hull pitches a bit more and lags slightly
    _, p2, r2 = tank_state(t-0.12)
    tank.location = loc; tank.rotation_euler = (roll, -pitch, 0)
    hullE.rotation_euler = (0.4*(r2-roll), -0.5*(p2-pitch) - 0.012*math.sin(t*11), 0); hullE.location = (0, 0, 0.03*math.sin(t*9))
    bpy.context.view_layer.update()
    # perfect 2-axis stabilisation: keep the barrel pointing along AIM in world space
    Mh = turret.parent.matrix_world.to_3x3()
    d = Mh.inverted() @ AIM
    turret.rotation_euler = (0, 0, math.atan2(d.y, d.x))
    gun.rotation_euler = (0, -math.atan2(d.z, math.hypot(d.x, d.y)), 0)
    # dust
    for k, (p, m) in enumerate(PUFFS):
        age = (t - k*0.45) % (16*0.45)
        born = t - age
        bx = X0 + V*born - 3.6
        r = 0.8 + age*0.9
        p.location = (bx - age*0.6, (-1.5 if k % 2 else 1.5) + (k % 3 - 1)*0.4, hgt(bx, 0) + 0.3 + r*0.4)
        p.scale = (r*1.3, r, r*0.75)
        m.node_tree.nodes["den"].inputs[1].default_value = 0.9*math.exp(-age*0.55)*min(1, age*3)

# ------------------------------------------------------------------ environment
wo = bpy.data.worlds.new("w"); sc.world = wo; wo.use_nodes = True
bg = wo.node_tree.nodes["Background"]
sky = wo.node_tree.nodes.new("ShaderNodeTexSky"); sky.sky_type = 'MULTIPLE_SCATTERING'
wo.node_tree.links.new(sky.outputs[0], bg.inputs[0])
SUN_ROT = 20
sky.sun_elevation = math.radians(8); sky.sun_rotation = math.radians(SUN_ROT); sky.altitude = 0; sky.aerosol_density = 2.0; sky.sun_intensity = 0.5
bg.inputs[1].default_value = 0.2
sun_d = bpy.data.lights.new("sun", 'SUN'); sun_d.energy = 3.6; sun_d.color = (1.0, 0.68, 0.45); sun_d.angle = math.radians(0.6)
sun = bpy.data.objects.new("sun", sun_d); coll.objects.link(sun)
sun.rotation_euler = Euler((math.radians(82), 0, math.radians(SUN_ROT+90)))

cam_d = bpy.data.cameras.new("cam"); cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 36; cam_d.clip_end = 100000; cam_d.clip_start = 0.05
cam = bpy.data.objects.new("cam", cam_d); coll.objects.link(cam); sc.camera = cam
SH = [(rnd.uniform(-1, 1), rnd.uniform(-1, 1)) for _ in range(400)]
def shake(t, amp, rate=2.5):
    i = int(t*rate); f = t*rate - i; a, b_ = SH[i % 400], SH[(i+1) % 400]; f = f*f*(3-2*f)
    return (a[0]+(b_[0]-a[0])*f)*amp, (a[1]+(b_[1]-a[1])*f)*amp
def aim(loc, tgt, t, amp, rate=2.5):
    cam.location = loc
    e = (Vector(tgt)-Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sx, sy = shake(t, amp, rate); e.x += sx; e.z += sy; cam.rotation_euler = e

def cam_pose(t):
    x = X0 + V*t
    if SHOT == "A":
        k = ease(t/7.6)
        cam_d.lens = lerp(55, 48, k)
        loc = Vector((x + lerp(-4, 4, k), -30, low(x, -30) + 2.6))
        tgt = Vector((x + 1.0, 0, low(x, 0) + 1.9))
    else:
        k = ease((t-7.6)/5.0); k2 = ease((t-17.0)/10.0)
        cam_d.lens = lerp(30, 40, k2)
        loc = Vector((x + lerp(13.5, 11.0, k) - 4.0*k2, lerp(-9.5, -7.0, k) - 4*k2, 0))
        loc.z = low(loc.x, loc.y) + 1.3 + 0.9*k2
        tgt = Vector((x + 1.0 + 1.5*k2, lerp(-0.5, 0.0, k), low(x, 0) + 1.8))
    aim(loc, tgt, t, math.radians(0.12))

# ------------------------------------------------------------------ render
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.cycles.samples = int(os.environ.get("SPP", "14")); sc.cycles.use_denoising = True; sc.cycles.use_adaptive_sampling = True
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transparent_max_bounces = 6
sc.cycles.volume_bounces = 0; sc.cycles.volume_step_rate = 4.0; sc.cycles.volume_max_steps = 32
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.resolution_percentage = int(os.environ.get("PCT", "60"))
sc.render.use_persistent_data = True
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
sc.view_settings.exposure = float(os.environ.get("EXPO", "0.0"))

def screen(p):
    v = world_to_camera_view(sc, cam, Vector(p)); return (v.x*RES[0], (1-v.y)*RES[1], v.z)
def full(t):
    pose(t); cam_pose(t); bpy.context.view_layer.update()

t0, t1 = SHOTS[SHOT]
mode = sys.argv[sys.argv.index("--")+1] if "--" in sys.argv else "frames"
if mode == "test":
    for t in [float(x) for x in os.environ.get("TT", str((t0+t1)/2)).split(",")]:
        full(t)
        sc.render.filepath = f"{OUT}/test{SHOT}_{t}.png"; bpy.ops.render.render(write_still=True)
elif mode == "meta":
    meta = {}
    for i in range(int(round(t0*FPS)), int(round(t1*FPS))):
        t = i/FPS; full(t)
        hw = hullE.matrix_world; gw = gun.matrix_world
        _, pitch, _ = tank_state(t)
        hp = math.degrees(math.asin(max(-1, min(1, (hw.to_3x3() @ Vector((1, 0, 0))).z))))
        meta[i] = {"muz": screen(gw @ MUZZLE), "brl": screen(gw @ Vector((1.0, 0, 0))), "far": screen(gw @ Vector((14.0, 0, 0))),
                   "hf": screen(hw @ Vector((3.95, -1.86, 1.3))), "hr": screen(hw @ Vector((-3.85, -1.86, 1.3))),
                   "turret": screen(turret.matrix_world @ Vector((0, 0, 0.9))), "pitch": hp}
    json.dump(meta, open(f"{OUT}/meta{SHOT}.json", "w"))
else:
    os.makedirs(f"{OUT}/frames", exist_ok=True)
    step = int(os.environ.get("STEP", "2"))
    for i in range(int(os.environ.get("IFROM", int(round(t0*FPS)))), int(os.environ.get("ITO", int(round(t1*FPS)))), step):
        out = f"{OUT}/frames/f{i:04d}.png"
        if os.path.exists(out): continue
        full(i/FPS)
        sc.render.filepath = out; bpy.ops.render.render(write_still=True)
