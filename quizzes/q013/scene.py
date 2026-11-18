import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import bpy, bmesh, math, json, sys, os, random
from mathutils import Vector, Euler
from bpy_extras.object_utils import world_to_camera_view

FPS = 30
RES = (1080, 1920)
OUT = os.environ.get("OUT", QDIR)
SHOT = os.environ.get("SHOT", "A")
SHOTS = {"A": (0.0, 6.8), "B": (6.8, 16.3), "C": (16.3, 32.3)}
YC = -2.25            # centre of our track
SPAN = 60.0           # mast spacing
STG = 0.30            # stagger (m) either side
ZC = 5.318            # contact wire centre height
YM1 = YC - 3.35       # mast line of track 1
PANT = -14.3          # pantograph head position in train coords

def ease(x):
    x = max(0.0, min(1.0, x)); return x*x*(3-2*x)
def lerp(a, b, k): return a + (b-a)*k

def wire_off(x, sign=1):
    """lateral offset of the contact wire at x (zigzag between masts)"""
    k = math.floor(x/SPAN); u = x/SPAN - k
    a = STG*(1 if k % 2 == 0 else -1)*sign
    return a + (-a - a)*u

def train_x(t):
    if t < 6.8:  return 150 + 68*t          # head-on approach, ~245 km/h
    if t < 16.3: return -5000                # not in shot B
    return -32 + 8.0*(t - 16.3)             # slow motion ride (shot C)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; coll = sc.collection
rnd = random.Random(13)

def principled(name, color, rough=0.5, metal=0.0, coat=0.0, emit=None, estr=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal; b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = estr
    return m
def noisy(name, col, rough, scale=0.3, amt=0.35, metal=0.0, rough_var=0.0, bump=0.15, bscale=40):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = 12
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs["Factor"].default_value = amt
    mix.inputs[6].default_value = (*col, 1); nt.links.new(nz.outputs["Fac"], mix.inputs[7])
    nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    if rough > 0.8 and metal == 0: b.inputs["Specular IOR Level"].default_value = 0.2
    if rough_var:
        mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[3].default_value = rough - rough_var; mr.inputs[4].default_value = rough + rough_var
        nt.links.new(nz.outputs["Fac"], mr.inputs[0]); nt.links.new(mr.outputs[0], b.inputs["Roughness"])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump
    n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = scale*bscale; n2.inputs["Detail"].default_value = 6
    nt.links.new(tc.outputs["Object"], n2.inputs["Vector"]); nt.links.new(n2.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs[0], b.inputs["Normal"])
    return m
def box(name, size, loc, mat, parent=None, rot=None, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object; o.name = name; o.scale = size; o.data.materials.append(mat)
    if rot: o.rotation_euler = rot
    if parent: o.parent = parent
    if bevel:
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        md = o.modifiers.new("bv", 'BEVEL'); md.width = bevel; md.segments = 2
    return o
def bm_cyl(bm, p0, p1, r, n=8):
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0; L = d.length
    if L < 1e-6: return
    q = d.to_track_quat('Z', 'Y')
    ring0, ring1 = [], []
    for i in range(n):
        a = 2*math.pi*i/n; v = q @ Vector((r*math.cos(a), r*math.sin(a), 0))
        ring0.append(bm.verts.new(p0 + v)); ring1.append(bm.verts.new(p1 + v))
    for i in range(n):
        j = (i+1) % n; f = bm.faces.new([ring0[i], ring0[j], ring1[j], ring1[i]]); f.smooth = True
    bm.faces.new(list(reversed(ring0))); bm.faces.new(ring1)
def bm_box(bm, c, s):
    res = bmesh.ops.create_cube(bm, size=1.0)
    for v in res["verts"]:
        v.co = Vector((c[0] + v.co.x*s[0], c[1] + v.co.y*s[1], c[2] + v.co.z*s[2]))
def finish(bm, name, mat, parent=None, smooth=False):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); coll.objects.link(o); o.data.materials.append(mat)
    if parent: o.parent = parent
    return o

M_BALL = noisy("ballast", (0.30, 0.28, 0.26), 0.95, scale=6.0, amt=0.75, bump=0.6, bscale=8)
M_SLP = noisy("sleeper", (0.42, 0.40, 0.37), 0.9, scale=3.0, amt=0.4)
M_RAIL = noisy("rail", (0.22, 0.13, 0.08), 0.6, scale=2.0, amt=0.5, metal=0.6, rough_var=0.2)
M_RTOP = principled("railtop", (0.75, 0.74, 0.72), 0.22, 1.0)
M_GALV = noisy("galv", (0.42, 0.43, 0.44), 0.45, scale=1.5, amt=0.35, metal=0.8, rough_var=0.1)
M_COPPER = principled("copper", (0.28, 0.17, 0.10), 0.35, 0.9)
M_INS = principled("insul", (0.25, 0.10, 0.05), 0.25, 0.0, coat=0.6)
M_GRASS = noisy("grass", (0.13, 0.15, 0.045), 0.95, scale=0.02, amt=0.6, bump=0.3, bscale=400)
M_TREE = noisy("tree", (0.035, 0.055, 0.02), 0.9, scale=0.4, amt=0.6, bump=0.5, bscale=10)
M_HILL = noisy("hill", (0.07, 0.08, 0.04), 0.9, scale=0.004, amt=0.5)

# ------------------------------------------------------------------ ground, ballast, track
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -0.9)); g = bpy.context.object; g.scale = (12000, 12000, 1); g.data.materials.append(M_GRASS)
bm = bmesh.new()
X0, X1 = -1600, 1600
pts = [(-8.5, -0.9), (-5.2, -0.13), (5.2, -0.13), (8.5, -0.9)]
vs = [[bm.verts.new((x, y, z)) for (y, z) in pts] for x in (X0, X1)]
for i in range(3): bm.faces.new([vs[0][i], vs[0][i+1], vs[1][i+1], vs[1][i]])
finish(bm, "ballast", M_BALL)
for yc in (YC, -YC):
    o = box(f"slp{yc}", (0.24, 2.6, 0.18), (X0, yc, -0.1), M_SLP)
    md = o.modifiers.new("arr", 'ARRAY'); md.count = 5300; md.relative_offset_displace = (0.6/0.24, 0, 0)
    for s in (1, -1):
        y = yc + s*0.7175
        box(f"rail{yc}{s}", (X1 - X0, 0.07, 0.15), ((X0+X1)/2, y, -0.075), M_RAIL)
        box(f"rtop{yc}{s}", (X1 - X0, 0.072, 0.02), ((X0+X1)/2, y, -0.008), M_RTOP)

# ------------------------------------------------------------------ catenary (masts, cantilevers, wires)
def wire_y(x, yc, sign): return yc + wire_off(x, sign)
def msg_z(x):
    u = (x/SPAN) % 1.0
    return ZC + 0.3 + 1.0*(2*u - 1)**2
bm = bmesh.new(); bmi = bmesh.new(); bmc = bmesh.new()
for k in range(int(X0/SPAN), int(X1/SPAN) + 1):
    x = k*SPAN
    for yc, ym, sign in ((YC, YM1, 1), (-YC, -YM1, -1)):
        s = 1 if ym > yc else -1         # side of the mast relative to the track
        # H-beam mast
        bm_box(bm, (x, ym, 3.6), (0.26, 0.30, 8.6))
        bm_box(bm, (x, ym, -0.6), (0.9, 0.9, 0.6))
        wy = wire_y(x, yc, sign)
        # top tube (messenger support) and diagonal brace
        bm_cyl(bm, (x, ym - s*0.15, 6.75), (x, yc - s*0.9, 6.75), 0.035)
        bm_cyl(bm, (x, ym - s*0.15, 5.05), (x, yc - s*0.6, 6.72), 0.03)
        # registration arm holding the contact wire
        bm_cyl(bm, (x, ym - s*0.15, 5.45), (x + 0.0, wy - s*0.25, ZC + 0.12), 0.022)
        bm_cyl(bm, (x, wy - s*0.25, ZC + 0.12), (x + 0.9, wy, ZC + 0.02), 0.012)
        # insulators near the mast
        for z in (6.75, 5.05):
            bm_cyl(bmi, (x, ym - s*0.18, z), (x, ym - s*0.75, z), 0.06, 10)
        bm_cyl(bmi, (x, ym - s*0.18, 5.45), (x, ym - s*0.7, 5.42), 0.06, 10)
        # droppers
        for d in range(1, 10):
            xd = x + d*SPAN/10
            bm_cyl(bmc, (xd, wire_y(xd, yc, sign), ZC), (xd, wire_y(xd, yc, sign)*0.5 + yc*0.5, msg_z(xd)), 0.006, 4)
finish(bm, "masts", M_GALV); finish(bmi, "insulators", M_INS); finish(bmc, "droppers", M_COPPER)
def make_wire(name, pts, r, mat):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = 2
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts): sp.points[i].co = (*p, 1)
    o = bpy.data.objects.new(name, cu); coll.objects.link(o); o.data.materials.append(mat); return o
for yc, sign in ((YC, 1), (-YC, -1)):
    xs = [X0 + i*SPAN for i in range(int((X1-X0)/SPAN) + 1)]
    make_wire(f"contact{yc}", [(x, wire_y(x, yc, sign), ZC) for x in xs], 0.022, M_COPPER)
    xs2 = [X0 + i*3.0 for i in range(int((X1-X0)/3.0) + 1)]
    make_wire(f"messenger{yc}", [(x, wire_y(x, yc, sign)*0.5 + yc*0.5, msg_z(x)) for x in xs2], 0.013, M_COPPER)

# ------------------------------------------------------------------ landscape
for k in range(260):
    side = rnd.choice((1, -1)); x = rnd.uniform(-1500, 1500); y = side*rnd.uniform(28, 260)
    if abs(x - 600) < 40 and side < 0 and abs(y) < 60: continue
    r = rnd.uniform(3, 7)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1, location=(x, y, -0.9 + r*0.8))
    o = bpy.context.object; o.scale = (r*rnd.uniform(0.8, 1.2), r*rnd.uniform(0.8, 1.2), r*rnd.uniform(0.9, 1.4)); o.data.materials.append(M_TREE)
    md = o.modifiers.new("d", 'DISPLACE'); tx = bpy.data.textures.new(f"t{k}", 'CLOUDS'); tx.noise_scale = 0.5; md.texture = tx; md.strength = 0.6
for k in range(16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1, location=(rnd.uniform(-4000, 4000), rnd.choice([1, -1])*rnd.uniform(1800, 3500), -40))
    h = bpy.context.object; h.scale = (rnd.uniform(500, 1100), rnd.uniform(300, 700), rnd.uniform(100, 260)); h.data.materials.append(M_HILL)
for s in (1, -1):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1, location=(s*9000, 0, -60))
    h = bpy.context.object; h.scale = (900, 2600, 150); h.data.materials.append(M_HILL)

# ------------------------------------------------------------------ high-speed train
M_WHITE = principled("white", (0.80, 0.80, 0.79), 0.25, 0.1, coat=0.8)
M_RED = principled("red", (0.45, 0.01, 0.015), 0.3, 0.1, coat=0.8)
M_GLASS = principled("glass", (0.01, 0.012, 0.016), 0.05, coat=1.0)
M_DARK = principled("dark", (0.025, 0.025, 0.028), 0.6)
M_GREY = principled("grey", (0.30, 0.31, 0.32), 0.45, 0.5)
M_CARB = principled("carbon", (0.05, 0.05, 0.05), 0.5)
M_HEAD = principled("headl", (0.9, 0.9, 0.85), 0.2, emit=(1, 0.93, 0.8), estr=25.0)
P = [(0, 0.5), (1.1, 0.5), (1.35, 0.62), (1.45, 0.9), (1.46, 1.15), (1.47, 1.4), (1.47, 1.85), (1.46, 2.55),
     (1.44, 3.0), (1.40, 3.3), (1.25, 3.58), (1.0, 3.75), (0.55, 3.84), (0, 3.86)]
RING = P + [(-y, z) for (y, z) in reversed(P[1:-1])]
SEG = list(range(len(P)-1)) + list(reversed(range(len(P)-1)))   # segment -> profile band index
def seg_mat(j, kind):
    if j == 4: return 1                     # red stripe
    if j == 6 and kind == "car": return 2   # window band
    if j <= 1: return 3                     # dark underbody
    return 0
train = bpy.data.objects.new("train", None); coll.objects.link(train)
def car_mesh(name, x_front, length, nose=0.0, tail_nose=False):
    bm = bmesh.new(); rings = []
    xs = []
    if nose:
        n = 16
        for i in range(n + 1):
            u = i/n; xs.append((x_front - nose*u, u))
    else:
        xs.append((x_front, 1.0))
    xs.append((x_front - nose - length, 1.0))
    for x, u in xs:
        fw = 0.06 + 0.94*(1 - (1 - u)**2)**0.5
        fh = 0.14 + 0.86*(1 - (1 - u)**2.2)**0.75
        rings.append([bm.verts.new((x if not nose else x, y*fw, 0.5 + (z - 0.5)*fh)) for (y, z) in RING])
    # nose rings go front->back in x: fix x for nose (front at x_front + 0)
    nr = len(RING)
    for ri in range(len(rings) - 1):
        a, b = rings[ri], rings[ri+1]; u = xs[ri][1]
        for j in range(nr):
            jj = (j+1) % nr
            f = bm.faces.new([a[j], a[jj], b[jj], b[j]]); f.smooth = True
            band = SEG[j] if j < len(SEG) else 0
            mi = seg_mat(band, "loco" if nose else "car")
            if nose and ri < len(rings) - 2 and 0.28 < u < 0.66 and 6 <= band <= 12: mi = 2
            f.material_index = mi
    bm.faces.new(list(reversed(rings[0]))).material_index = 0
    bm.faces.new(rings[-1]).material_index = 0
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); coll.objects.link(o)
    for m in (M_WHITE, M_RED, M_GLASS, M_DARK): o.data.materials.append(m)
    o.parent = train
    return o
# power car: nose tip at x=+0, 7 m nose, 20.9 m total
pc = car_mesh("power", 0.0, 13.9, nose=7.0)
for o in train.children:
    pass
cars = [(-21.5, 25.0), (-47.1, 25.0), (-72.7, 25.0)]
for k, (xf, L) in enumerate(cars):
    car_mesh(f"car{k}", xf, L)
    box(f"gang{k}", (0.9, 2.5, 3.0), (xf + 0.3, 0, 2.1), M_DARK, train)
# headlights + bogies
for s in (1, -1):
    box(f"hl{s}", (0.12, 0.28, 0.1), (-1.2, s*0.85, 1.05), M_HEAD, train)
M_WHEEL = principled("wheel", (0.3, 0.29, 0.28), 0.35, 0.9)
for xb in (-3.5, -17.5, -24.0, -44.0, -49.6, -69.6, -75.2, -95.2):
    box(f"bog{xb}", (3.2, 2.3, 0.45), (xb, 0, 0.55), M_DARK, train)
    for dx in (-1.25, 1.25):
        for s in (1, -1):
            bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=0.46, depth=0.12, location=(xb + dx, s*0.72, 0.46), rotation=(math.radians(90), 0, 0))
            o = bpy.context.object; o.data.materials.append(M_WHEEL); o.parent = train
# pantograph (single arm) on the power car roof
pb = bmesh.new(); pcar = bmesh.new(); pins = bmesh.new()
bx = PANT
for dx in (-0.7, 0.7):
    for s in (1, -1):
        bm_cyl(pins, (bx + dx, s*0.45, 3.84), (bx + dx, s*0.45, 4.12), 0.07, 10)
for s in (1, -1):
    bm_cyl(pb, (bx - 0.8, s*0.45, 4.15), (bx + 0.8, s*0.45, 4.15), 0.03)
for dx in (-0.7, 0.7):
    bm_cyl(pb, (bx + dx, -0.45, 4.15), (bx + dx, 0.45, 4.15), 0.03)
knee = (bx + 1.25, 0, 4.78)
for s in (1, -1):
    bm_cyl(pb, (bx - 0.75, s*0.3, 4.22), knee, 0.035)
bm_cyl(pb, (bx - 0.6, 0, 4.25), (bx + 1.1, 0, 4.72), 0.02)
bm_cyl(pb, knee, (bx, 0, 5.21), 0.03)
bm_cyl(pb, (bx + 0.6, 0, 4.98), (bx, 0, 5.18), 0.012)
# head: cross tube, strip carriers, horns
bm_cyl(pb, (bx, -0.65, 5.2), (bx, 0.65, 5.2), 0.025)
for dx in (-0.16, 0.16):
    bm_box(pb, (bx + dx, 0, 5.24), (0.07, 1.25, 0.05))
    bm_box(pcar, (bx + dx, 0, 5.285), (0.055, 1.2, 0.03))
    for s in (1, -1):
        prev = (bx + dx, s*0.6, 5.26)
        for a in range(1, 7):
            ang = a/6*math.pi/2
            p = (bx + dx, s*(0.6 + 0.3*math.sin(ang)), 5.26 - 0.22*(1 - math.cos(ang)))
            bm_cyl(pb, prev, p, 0.016); prev = p
finish(pb, "pantframe", M_GREY, train); finish(pcar, "carbon", M_CARB, train); finish(pins, "pantins", M_INS, train)
# roof details (boxes/equipment)
box("roofbox", (3.0, 1.4, 0.10), (-8.5, 0, 3.86), M_GREY, train, bevel=0.04)

# ------------------------------------------------------------------ environment
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
SUNROT = float(os.environ.get("SUNROT", "300"))
set_sun(7, SUNROT, 3.6, (1.0, 0.64, 0.40), 0.16)

# ------------------------------------------------------------------ camera
cam_d = bpy.data.cameras.new("cam"); cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 36; cam_d.clip_end = 100000; cam_d.clip_start = 0.05
cam = bpy.data.objects.new("cam", cam_d); coll.objects.link(cam); sc.camera = cam
SH = [(rnd.uniform(-1, 1), rnd.uniform(-1, 1)) for _ in range(400)]
def shake(t, amp, rate=2.5):
    i = int(t*rate); f = t*rate - i; a, b_ = SH[i % 400], SH[(i+1) % 400]; f = f*f*(3-2*f)
    return (a[0]+(b_[0]-a[0])*f)*amp, (a[1]+(b_[1]-a[1])*f)*amp
def aim(loc, tgt, t, amp):
    cam.location = loc
    e = (Vector(tgt)-Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sx, sy = shake(t, amp); e.x += sx; e.z += sy; cam.rotation_euler = e

def pose(t):
    tx = train_x(t)
    train.location = (tx, YC, 0)
    if SHOT == "A":
        k = ease(t/6.8)
        cam_d.lens = lerp(160, 140, k)
        loc = (720, 0.0, lerp(4.6, 4.3, k))
        tgt = (tx - 6, YC + 0.9, 2.6)
        aim(loc, tgt, t, math.radians(0.06))
    elif SHOT == "B":
        k = ease((t - 6.8)/9.5)
        cam_d.lens = lerp(40, 44, k)
        loc = (lerp(-34, -26, k), YC - 0.4, lerp(19, 18, k))
        tgt = (lerp(42, 48, k), YC + 0.0, 0.0)
        aim(loc, tgt, t, math.radians(0.05))
    else:
        u = t - 16.3
        r = ease((u - 11.4)/4.2)        # rise off the roof at the end
        cam_d.lens = lerp(62, 30, r)
        lx, ly, lz = lerp(PANT - 7.0, PANT - 30, r), lerp(1.5, 7.5, r), lerp(5.75, 13.5, r)
        gx, gy, gz = lerp(PANT + 0.2, PANT + 30, r), lerp(-0.1, -0.3, r), lerp(5.18, 4.0, r)
        aim((tx + lx, YC + ly, lz), (tx + gx, YC + gy, gz), t, math.radians(0.12))

# ------------------------------------------------------------------ render
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.cycles.samples = int(os.environ.get("SPP", "10")); sc.cycles.use_denoising = True; sc.cycles.use_adaptive_sampling = True
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transparent_max_bounces = 6
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.resolution_percentage = int(os.environ.get("PCT", "50"))
sc.render.use_persistent_data = True
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
sc.view_settings.exposure = float(os.environ.get("EXPO", "-0.3"))

def screen(p):
    v = world_to_camera_view(sc, cam, Vector(p)); return (v.x*RES[0], (1-v.y)*RES[1], v.z)
def shot_for(t):
    for k, (a, b) in SHOTS.items():
        if a <= t < b: return k
    return "C"
mode = sys.argv[sys.argv.index("--")+1] if "--" in sys.argv else "frames"
if mode == "test":
    for t in [float(x) for x in os.environ.get("TT", "3").split(",")]:
        SHOT = shot_for(t); pose(t); bpy.context.view_layer.update()
        sc.render.filepath = f"{OUT}/test_{t}.png"; bpy.ops.render.render(write_still=True)
elif mode == "meta":
    meta = {}
    for i in range(0, int(SHOTS["C"][1]*FPS)):
        t = i/FPS; SHOT = shot_for(t); pose(t); bpy.context.view_layer.update()
        tx = train_x(t); px = tx + PANT
        m = {"off": wire_off(px)}
        m["contact"] = screen((px, YC + wire_off(px), 5.30))
        m["strip"] = screen((px, YC, 5.30))
        for kk in range(-1, 3):
            x = kk*SPAN
            m[f"m{kk}"] = screen((x, YC + wire_off(x + 0.01), ZC))
            m[f"c{kk}"] = screen((x, YC, ZC))
        meta[i] = m
    json.dump(meta, open(f"{OUT}/meta.json", "w"))
else:
    os.makedirs(f"{OUT}/frames", exist_ok=True)
    step = int(os.environ.get("STEP", "2"))
    i0 = int(os.environ.get("IFROM", "0")); i1 = int(os.environ.get("ITO", int(SHOTS["C"][1]*FPS)))
    for i in range(i0, i1, step):
        out = f"{OUT}/frames/f{i:04d}.png"
        if os.path.exists(out): continue
        t = i/FPS; SHOT = shot_for(t); pose(t); bpy.context.view_layer.update()
        sc.render.filepath = out; bpy.ops.render.render(write_still=True)
