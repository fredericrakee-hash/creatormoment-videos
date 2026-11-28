import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import bpy, bmesh, math, json, sys, os, random
from mathutils import Vector, Euler
from bpy_extras.object_utils import world_to_camera_view

FPS = 30
RES = (1080, 1920)
OUT = os.environ.get("OUT", QDIR)
SHOT = os.environ.get("SHOT", "A")
SHOTS = {"A": (0.0, 7.8), "B": (7.8, 16.0), "C": (16.0, 24.3), "D": (24.3, 30.6)}
SPEED = 0.12                     # m/s (the real rover is even slower)
X0 = -2.0
R = 0.25                         # wheel radius (wheels are ~50 cm tall)
WX = (1.05, 0.0, -1.0)           # wheel x offsets (front, middle, rear)
WY = 1.25                        # half track width
PERIOD = 2*math.pi*R

def ease(x):
    x = max(0.0, min(1.0, x)); return x*x*(3-2*x)
def lerp(a, b, k): return a + (b-a)*k
def rx(t): return X0 + SPEED*t

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; coll = sc.collection
rnd = random.Random(34)

def principled(name, color, rough=0.5, metal=0.0, emit=None, estr=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = estr
    return m
def dusty(name, c1, c2, scale=3.0, rough=0.6, metal=0.0, bump=0.15):
    """metal/paint with patchy red dust"""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = 8
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    rp = nt.nodes.new("ShaderNodeValToRGB"); rp.color_ramp.elements[0].color = (*c1, 1); rp.color_ramp.elements[1].color = (*c2, 1)
    rp.color_ramp.elements[0].position = 0.35; rp.color_ramp.elements[1].position = 0.75
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
def cyl(name, r, depth, loc, mat, rot=(0, 0, 0), parent=None, verts=32, r2=None, smooth=True):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=depth, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name; o.data.materials.append(mat)
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    if parent: o.parent = parent
    return o
def rod(name, p, q, r, mat, parent=None):
    p, q = Vector(p), Vector(q); d = q-p
    o = cyl(name, r, d.length, (p+q)/2, mat, parent=parent, verts=12)
    o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = d.to_track_quat('Z', 'Y')
    return o

# ------------------------------------------------------------------ terrain
def hgt(x, y):
    far = min(1.0, (abs(y) - 3.0)/12.0) if abs(y) > 3.0 else 0.0
    h = 0.02*math.sin(x*0.9 + y*0.4) + 0.015*math.sin(x*2.3 - y*1.7)
    h += far*(0.5*math.sin(x*0.08 + 0.5) + 0.35*math.sin(y*0.11 + x*0.05) + 0.2*math.sin(x*0.31 + y*0.2))
    return h
M_SOIL = bpy.data.materials.new("soil"); M_SOIL.use_nodes = True; nt = M_SOIL.node_tree
b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.95
tc = nt.nodes.new("ShaderNodeTexCoord")
n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 0.35; n1.inputs["Detail"].default_value = 8
nt.links.new(tc.outputs["Object"], n1.inputs["Vector"])
rp = nt.nodes.new("ShaderNodeValToRGB")
rp.color_ramp.elements[0].color = (0.30, 0.13, 0.06, 1); rp.color_ramp.elements[1].color = (0.52, 0.27, 0.14, 1)
rp.color_ramp.elements[0].position = 0.3; rp.color_ramp.elements[1].position = 0.75
nt.links.new(n1.outputs["Fac"], rp.inputs[0])
n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 60; n2.inputs["Detail"].default_value = 4
nt.links.new(tc.outputs["Object"], n2.inputs["Vector"])
vo = nt.nodes.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 140
nt.links.new(tc.outputs["Object"], vo.inputs["Vector"])
# track mask + track height map (object coords of the untransformed ground == world coords)
sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep.inputs[0])
def M(op, a=None, b_=None, v1=None, v2=None):
    n = nt.nodes.new("ShaderNodeMath"); n.operation = op
    if a is not None: nt.links.new(a, n.inputs[0])
    elif v1 is not None: n.inputs[0].default_value = v1
    if b_ is not None: nt.links.new(b_, n.inputs[1])
    elif v2 is not None: n.inputs[1].default_value = v2
    return n
ay = M('ABSOLUTE', sep.outputs[1])
vv = M('DIVIDE', M('ADD', M('SUBTRACT', ay.outputs[0], v2=WY).outputs[0], v2=0.2).outputs[0], v2=0.4)     # 0..1 across the track
uu = M('DIVIDE', sep.outputs[0], v2=PERIOD)
inside = M('MULTIPLY', M('GREATER_THAN', vv.outputs[0], v2=0.0).outputs[0], M('LESS_THAN', vv.outputs[0], v2=1.0).outputs[0])
REVEAL = M('LESS_THAN', sep.outputs[0], v2=-100.0); REVEAL.name = "reveal"      # x < front wheel contact
mask = M('MULTIPLY', inside.outputs[0], REVEAL.outputs[0])
cmb = nt.nodes.new("ShaderNodeCombineXYZ"); nt.links.new(uu.outputs[0], cmb.inputs[0]); nt.links.new(vv.outputs[0], cmb.inputs[1])
img = nt.nodes.new("ShaderNodeTexImage"); img.image = bpy.data.images.load(f"{QDIR}/track.png"); img.image.colorspace_settings.name = 'Non-Color'
img.extension = 'REPEAT'; img.interpolation = 'Cubic'
nt.links.new(cmb.outputs[0], img.inputs[0])
# berm: slightly raised soil next to the track edges
edge = M('MULTIPLY', M('MULTIPLY', M('GREATER_THAN', vv.outputs[0], v2=-0.25).outputs[0], M('LESS_THAN', vv.outputs[0], v2=1.25).outputs[0]).outputs[0],
         M('SUBTRACT', v1=1.0, b_=inside.outputs[0]).outputs[0])
berm = M('MULTIPLY', M('MULTIPLY', edge.outputs[0], REVEAL.outputs[0]).outputs[0], v2=0.6)
trk = M('MULTIPLY', M('SUBTRACT', img.outputs[0], v2=0.75).outputs[0], mask.outputs[0])      # track is pressed in
hsum = M('ADD', M('ADD', trk.outputs[0], berm.outputs[0]).outputs[0], M('MULTIPLY', n2.outputs["Fac"], v2=0.25).outputs[0])
hsum2 = M('ADD', hsum.outputs[0], M('MULTIPLY', vo.outputs["Distance"], v2=0.12).outputs[0])
bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.8; bp.inputs["Distance"].default_value = 0.02
nt.links.new(hsum2.outputs[0], bp.inputs["Height"]); nt.links.new(bp.outputs[0], b.inputs["Normal"])
# compacted track a little darker/browner
mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = 'RGBA'
nt.links.new(M('MULTIPLY', mask.outputs[0], v2=0.35).outputs[0], mx.inputs["Factor"])
nt.links.new(rp.outputs[0], mx.inputs[6]); mx.inputs[7].default_value = (0.20, 0.09, 0.045, 1)
hi = M('MULTIPLY', M('GREATER_THAN', img.outputs[0], v2=0.82).outputs[0], mask.outputs[0])
mx2 = nt.nodes.new("ShaderNodeMix"); mx2.data_type = 'RGBA'
nt.links.new(M('MULTIPLY', hi.outputs[0], v2=0.45).outputs[0], mx2.inputs["Factor"])
nt.links.new(mx.outputs[2], mx2.inputs[6]); mx2.inputs[7].default_value = (0.62, 0.36, 0.20, 1)
nt.links.new(mx2.outputs[2], b.inputs["Base Color"])

XA, XB, YA, YB = -70, 50, -60, 60
bm = bmesh.new(); grid = []
NX, NY = 240, 160
def ycoord(j):
    u = j/NY*2 - 1; return 60*u*abs(u)**0.6 if abs(u) > 0 else 0.0
for i in range(NX+1):
    x = XA + (XB-XA)*i/NX; row = []
    for j in range(NY+1):
        y = ycoord(j); row.append(bm.verts.new((x, y, hgt(x, y))))
    grid.append(row)
for i in range(NX):
    for j in range(NY):
        bm.faces.new([grid[i][j], grid[i+1][j], grid[i+1][j+1], grid[i][j+1]])
ground = obj_from_bm("ground", bm, M_SOIL, smooth=True)
# distant mesas / crater rim
M_FAR = dusty("far", (0.36, 0.19, 0.10), (0.55, 0.33, 0.20), 0.02, 0.95, 0, 0.3)
for k in range(9):
    a = rnd.uniform(-0.9, 2.6); dist = rnd.uniform(700, 1500)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1, location=(math.cos(a)*dist, math.sin(a)*dist, -30))
    hl = bpy.context.object; hl.scale = (rnd.uniform(250, 500), rnd.uniform(250, 500), rnd.uniform(60, 160)); hl.data.materials.append(M_FAR)
bpy.ops.mesh.primitive_plane_add(size=20000, location=(0, 0, -1.0)); bpy.context.object.data.materials.append(M_SOIL)
# rocks
M_ROCK = dusty("rock", (0.13, 0.07, 0.045), (0.36, 0.20, 0.11), 2.5, 0.85, 0, 0.5)
for k in range(260):
    x = rnd.uniform(-60, 40); y = rnd.uniform(-45, 45)
    if abs(y) < 2.3 or (abs(y) < 4 and -8 < x < 6): continue
    s = rnd.uniform(0.04, 0.35)*(1.0 + (abs(y) > 10)*1.5)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=(x, y, hgt(x, y) + s*0.2))
    o = bpy.context.object; o.name = f"rock{k}"; o.scale = (s*rnd.uniform(0.8, 1.6), s*rnd.uniform(0.8, 1.4), s*rnd.uniform(0.4, 0.8))
    o.rotation_euler = (rnd.uniform(0, 3), rnd.uniform(0, 3), rnd.uniform(0, 3)); o.data.materials.append(M_ROCK)
    dm = o.modifiers.new("d", 'DISPLACE'); tx = bpy.data.textures.new(f"rt{k}", 'CLOUDS'); tx.noise_scale = 0.6; dm.texture = tx; dm.strength = 0.35

# ------------------------------------------------------------------ rover
M_WHITE = dusty("deck", (0.62, 0.58, 0.52), (0.55, 0.38, 0.26), 4.0, 0.5, 0.1, 0.05)
M_METAL = dusty("metal", (0.55, 0.55, 0.56), (0.45, 0.33, 0.24), 6.0, 0.35, 0.85, 0.05)
M_DARK = principled("dark", (0.09, 0.09, 0.095), 0.5, 0.5)
M_GOLD = principled("gold", (0.85, 0.55, 0.20), 0.3, 1.0)
M_ALU = dusty("alu", (0.62, 0.62, 0.64), (0.50, 0.33, 0.22), 9.0, 0.5, 0.75, 0.1)
M_GLASS = principled("lens", (0.01, 0.01, 0.015), 0.05, 0.0)
M_HOLE = principled("hole", (0.01, 0.006, 0.004), 0.9)

rover = bpy.data.objects.new("rover", None); coll.objects.link(rover)
body = bpy.data.objects.new("body", None); coll.objects.link(body); body.parent = rover; body.location = (0, 0, 0.95)
box("chassis", (2.1, 1.65, 0.45), (0, 0, 0.05), M_WHITE, body)
box("deck", (2.2, 1.75, 0.04), (0, 0, 0.29), M_METAL, body)
box("deckbox1", (0.5, 0.5, 0.25), (0.45, 0.45, 0.43), M_WHITE, body)
box("deckbox2", (0.45, 0.35, 0.18), (-0.2, -0.5, 0.4), M_GOLD, body)
cyl("hga", 0.3, 0.05, (-0.3, 0.45, 0.5), M_METAL, rot=(0.5, 0.0, 0.0), parent=body)
cyl("hgastand", 0.04, 0.2, (-0.3, 0.45, 0.38), M_METAL, parent=body, verts=12)
cyl("uhf", 0.06, 0.35, (-0.75, 0.1, 0.48), M_WHITE, parent=body, verts=16)
# RTG at the back with fins
rtg = cyl("rtg", 0.32, 0.75, (-1.35, 0, 0.25), M_DARK, rot=(0, math.radians(-60), 0), parent=body)
for k in range(8):
    a = 2*math.pi*k/8
    f = box(f"fin{k}", (0.7, 0.02, 0.2), (0, 0, 0), M_DARK, rtg)
    f.location = (0.0, math.cos(a)*0.4, math.sin(a)*0.4) ; f.scale = (0.02, 0.18, 0.7)
    f.rotation_euler = (a, 0, 0)
# mast + head
cyl("mast", 0.06, 1.2, (0.75, -0.5, 0.88), M_WHITE, parent=body, verts=16)
head = box("head", (0.28, 0.55, 0.22), (0.8, -0.5, 1.55), M_WHITE, body)
for s in (-1, 1):
    cyl(f"eye{s}", 0.045, 0.06, (0.95, -0.5 + s*0.13, 1.55), M_GLASS, rot=(0, math.pi/2, 0), parent=body, verts=16)
    cyl(f"eyer{s}", 0.055, 0.03, (0.94, -0.5 + s*0.13, 1.55), M_METAL, rot=(0, math.pi/2, 0), parent=body, verts=16)
box("chemcam", (0.22, 0.2, 0.2), (0.75, -0.5, 1.78), M_WHITE, body)
cyl("chemlens", 0.06, 0.04, (0.87, -0.5, 1.78), M_GLASS, rot=(0, math.pi/2, 0), parent=body, verts=16)
# stowed arm with turret
rod("arm1", (1.05, 0.55, -0.05), (1.25, 0.1, 0.0), 0.045, M_WHITE, body)
rod("arm2", (1.25, 0.1, 0.0), (1.2, -0.45, 0.05), 0.04, M_WHITE, body)
box("turret", (0.28, 0.3, 0.3), (1.22, -0.55, 0.0), M_METAL, body)
cyl("drill", 0.03, 0.25, (1.22, -0.55, -0.25), M_METAL, parent=body, verts=12)
# hazcams
for s in (-1, 1):
    box(f"haz{s}", (0.05, 0.1, 0.06), (1.07, s*0.3, -0.2), M_DARK, body)

def wheel(name, loc):
    hub = bpy.data.objects.new(name, None); coll.objects.link(hub); hub.parent = rover; hub.location = loc
    spin = bpy.data.objects.new(name+"s", None); coll.objects.link(spin); spin.parent = hub
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=R - 0.008, depth=0.40, end_fill_type='NOTHING', rotation=(math.pi/2, 0, 0))
    rim = bpy.context.object; rim.name = name+"rim"; rim.data.materials.append(M_ALU); rim.parent = spin
    for p in rim.data.polygons: p.use_smooth = True
    rim.modifiers.new("sol", 'SOLIDIFY').thickness = 0.006
    side = 1 if loc[1] > 0 else -1
    cyl(name+"cap", 0.08, 0.06, (0, side*0.2, 0), M_METAL, rot=(math.pi/2, 0, 0), parent=spin, verts=24)
    for k in range(6):                     # curved titanium spokes (flexures)
        a = 2*math.pi*k/6
        b_ = box(name+f"sp{k}", (0.025, 0.012, R - 0.06), (0, side*0.19, 0), M_METAL, spin)
        b_.rotation_euler = (0, a, 0); b_.location = (math.sin(a)*(R - 0.03)/2, side*0.19, math.cos(a)*(R - 0.03)/2)
    # 24 chevron grousers
    for k in range(24):
        a = 2*math.pi*k/24
        for s in (-1, 1):
            g = box(name+f"g{k}{s}", (0.012, 0.205, 0.012), (0, 0, 0), M_ALU, spin)
            g.rotation_mode = 'XYZ'
            aa = a + s*0.04
            g.location = (math.sin(aa)*R, s*0.1, math.cos(aa)*R); g.rotation_euler = (0, aa, s*0.0)
    # J-P-L hole pattern around the circumference (dot / dash), on the centre band
    u = 0.30
    for ch in ".--- .--. .-..":
        if ch == " ": u += 0.05; continue
        ln = 0.022 if ch == "." else 0.066
        a = (u + ln/2)/R
        h = box(name+f"h{u:.3f}", (ln, 0.05, 0.004), (math.sin(a)*(R-0.006), 0, math.cos(a)*(R-0.006)), M_HOLE, spin)
        h.rotation_euler = (0, a, 0)
        u += ln + 0.022
    return hub, spin
WHEELS = []
for s in (-1, 1):
    for wx in WX:
        WHEELS.append(wheel(f"w{wx}{s}", (wx, s*WY, R)))
    # rocker-bogie suspension
    rod(f"rock{s}", (1.05, s*WY, R + 0.02), (0.15, s*(WY-0.05), 0.75), 0.035, M_METAL, rover)
    rod(f"rockb{s}", (0.15, s*(WY-0.05), 0.75), (-0.45, s*(WY-0.05), 0.6), 0.035, M_METAL, rover)
    rod(f"bog1{s}", (-0.45, s*(WY-0.05), 0.6), (0.0, s*WY, R + 0.02), 0.03, M_METAL, rover)
    rod(f"bog2{s}", (-0.45, s*(WY-0.05), 0.6), (-1.0, s*WY, R + 0.02), 0.03, M_METAL, rover)
    rod(f"pivot{s}", (0.15, s*(WY-0.05), 0.75), (0.15, s*0.8, 0.85), 0.04, M_METAL, rover)
    for wx in WX:
        rod(f"fork{wx}{s}", (wx, s*(WY-0.22), R), (wx, s*(WY-0.22), R + 0.2), 0.03, M_METAL, rover)

def pose(t):
    x = rx(t)
    rover.location = (x, 0, 0.0)
    body.rotation_euler = (0.004*math.sin(t*0.9), 0.003*math.sin(t*0.7 + 1), 0)
    for hub, spin in WHEELS:
        spin.rotation_euler = (0, x/R, 0)
    M_SOIL.node_tree.nodes["reveal"].inputs[1].default_value = x + WX[0]

# ------------------------------------------------------------------ environment: dusty butterscotch Mars sky
wo = bpy.data.worlds.new("w"); sc.world = wo; wo.use_nodes = True; nt = wo.node_tree
bg = nt.nodes["Background"]
tcw = nt.nodes.new("ShaderNodeTexCoord"); sepw = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tcw.outputs["Generated"], sepw.inputs[0])
rw = nt.nodes.new("ShaderNodeValToRGB"); cr = rw.color_ramp
cr.elements[0].position = 0.0; cr.elements[0].color = (0.62, 0.42, 0.26, 1)
cr.elements[1].position = 0.45; cr.elements[1].color = (0.42, 0.30, 0.22, 1)
nt.links.new(sepw.outputs[2], rw.inputs[0]); nt.links.new(rw.outputs[0], bg.inputs[0])
bg.inputs[1].default_value = 1.3
SUN_AZ = math.radians(-60)
sun_d = bpy.data.lights.new("sun", 'SUN'); sun_d.energy = 3.2; sun_d.color = (1.0, 0.90, 0.80); sun_d.angle = math.radians(0.4)
sun = bpy.data.objects.new("sun", sun_d); coll.objects.link(sun)
sun.rotation_euler = Euler((math.radians(68), 0, math.radians(-60)))

cam_d = bpy.data.cameras.new("cam"); cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 36; cam_d.clip_end = 20000; cam_d.clip_start = 0.02
cam = bpy.data.objects.new("cam", cam_d); coll.objects.link(cam); sc.camera = cam
SH = [(rnd.uniform(-1, 1), rnd.uniform(-1, 1)) for _ in range(400)]
def shake(t, amp, rate=1.5):
    i = int(t*rate); f = t*rate - i; a, b_ = SH[i % 400], SH[(i+1) % 400]; f = f*f*(3-2*f)
    return (a[0]+(b_[0]-a[0])*f)*amp, (a[1]+(b_[1]-a[1])*f)*amp
def aim(loc, tgt, t, amp):
    cam.location = loc
    e = (Vector(tgt)-Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sx, sy = shake(t, amp); e.x += sx; e.z += sy; cam.rotation_euler = e

def cam_pose(t):
    x = rx(t)
    if SHOT == "A":
        k = ease(t/7.8)
        cam_d.lens = lerp(44, 52, k)
        loc = Vector((x + lerp(8.0, 6.8, k), lerp(-6.5, -5.6, k), 0.6))
        tgt = Vector((x - 0.1, 0.0, 1.0))
    elif SHOT == "B":
        k = ease((t-7.8)/8.2)
        cam_d.lens = 30
        loc = Vector((x + lerp(1.3, 0.3, k), -WY - lerp(1.55, 1.25, k), lerp(0.42, 0.36, k)))
        tgt = Vector((x + lerp(0.35, -0.5, k), -WY, 0.24))
    elif SHOT == "C":
        k = ease((t-16.0)/8.3)
        cam_d.lens = 32
        xc = x - 3.2 + lerp(-0.4, 0.5, k)
        loc = Vector((xc - 0.5, -WY - 0.75, 1.05))
        tgt = Vector((xc + 0.4, -WY, 0.0))
    else:
        k = ease((t-24.3)/6.3)
        cam_d.lens = lerp(30, 34, k)
        loc = Vector((x - lerp(9.0, 10.0, k), lerp(-3.2, -3.0, k), lerp(3.2, 3.8, k)))
        tgt = Vector((x + 0.5, 0.0, 0.5))
    aim(loc, tgt, t, math.radians(0.08))

# ------------------------------------------------------------------ render
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.cycles.samples = int(os.environ.get("SPP", "12")); sc.cycles.use_denoising = True; sc.cycles.use_adaptive_sampling = True
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.resolution_percentage = int(os.environ.get("PCT", "50"))
sc.render.use_persistent_data = True
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
sc.view_settings.exposure = float(os.environ.get("EXPO", "0.0"))

def screen(p):
    v = world_to_camera_view(sc, cam, Vector(p)); return (v.x*RES[0], (1-v.y)*RES[1], v.z)
def full(t):
    pose(t); bpy.context.view_layer.update(); cam_pose(t); bpy.context.view_layer.update()

t0, t1 = SHOTS[SHOT]
mode = sys.argv[sys.argv.index("--")+1] if "--" in sys.argv else "frames"
if mode == "test":
    for t in [float(x) for x in os.environ.get("TT", str((t0+t1)/2)).split(",")]:
        full(t)
        sc.render.filepath = f"{OUT}/test{SHOT}_{t}.png"; bpy.ops.render.render(write_still=True)
elif mode == "meta":
    meta = {}
    for i in range(int(round(t0*FPS)), int(round(t1*FPS))):
        t = i/FPS; full(t); x = rx(t)
        # a Morse group in the left track behind the rover: first mark of the next full group behind x-3
        xm = math.floor((x - 3.0)/PERIOD)*PERIOD + 0.30
        meta[i] = {"rover": screen((x, 0, 1.2)), "wheel": screen((x + WX[1], -WY - 0.2, R)), "wheelF": screen((x + WX[0], -WY - 0.2, R)),
                   "mast": screen((x + 0.8, -0.5, 2.5)), "track": screen((x - 2.0, -WY, 0.0)),
                   "morse0": screen((xm, -WY, 0.0)), "morse1": screen((xm + 0.89, -WY, 0.0)),
                   "trackfar": screen((x - 12.0, -WY, 0.0))}
    json.dump(meta, open(f"{OUT}/meta{SHOT}.json", "w"))
else:
    os.makedirs(f"{OUT}/frames", exist_ok=True)
    step = int(os.environ.get("STEP", "2"))
    for i in range(int(os.environ.get("IFROM", int(round(t0*FPS)))), int(os.environ.get("ITO", int(round(t1*FPS)))), step):
        out = f"{OUT}/frames/f{i:04d}.png"
        if os.path.exists(out): continue
        full(i/FPS)
        sc.render.filepath = out; bpy.ops.render.render(write_still=True)
