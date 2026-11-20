import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import bpy, bmesh, math, json, sys, os, random
from mathutils import Vector, Euler, noise
from bpy_extras.object_utils import world_to_camera_view

FPS = 30
RES = (1080, 1920)
OUT = os.environ.get("OUT", QDIR)
SHOT = "A"
SHOTS = {"A": (0.0, 8.4), "B": (8.4, 16.0), "C": (16.0, 23.4), "D": (23.4, 27.6)}

def ease(x):
    x = max(0.0, min(1.0, x)); return x*x*(3-2*x)
def lerp(a, b, k): return a + (b-a)*k
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; coll = sc.collection
rnd = random.Random(17)

HAZE = (1.0, 0.70, 0.48)
def add_haze(m, dist=1400.0, amt=0.85, col=HAZE, strength=0.55):
    """aerial perspective: blend towards a warm haze colour with camera distance"""
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

def principled(name, color, rough=0.5, metal=0.0, coat=0.0, haze=True):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal; b.inputs["Coat Weight"].default_value = coat
    return add_haze(m) if haze else m
def mesh_obj(name, bm, mat, smooth=True):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); coll.objects.link(o); o.data.materials.append(mat)
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    return o
def tube(name, pts, r, mat, n=8):
    bm = bmesh.new(); prev = None
    for k, p in enumerate(pts):
        t_ = (pts[min(k+1, len(pts)-1)] - pts[max(k-1, 0)]).normalized()
        a_ = t_.cross(Vector((0, 0, 1))); a_ = a_.normalized() if a_.length > 1e-4 else Vector((1, 0, 0))
        b_ = t_.cross(a_)
        ring = [bm.verts.new(p + r*(math.cos(2*math.pi*i/n)*a_ + math.sin(2*math.pi*i/n)*b_)) for i in range(n)]
        if prev:
            for i in range(n):
                bm.faces.new([prev[i], prev[(i+1) % n], ring[(i+1) % n], ring[i]])
        prev = ring
    return mesh_obj(name, bm, mat)
def strut(bm, p, q, r):
    """square-section steel angle between p and q, added to bm"""
    d = (q - p); L = d.length; t_ = d/L
    a_ = t_.cross(Vector((0, 0, 1))); a_ = a_.normalized() if a_.length > 1e-4 else Vector((1, 0, 0))
    b_ = t_.cross(a_)
    vs = []
    for e in (p, q):
        vs.append([bm.verts.new(e + r*(sx*a_ + sy*b_)) for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1))])
    for i in range(4):
        bm.faces.new([vs[0][i], vs[0][(i+1) % 4], vs[1][(i+1) % 4], vs[1][i]])

# ------------------------------------------------------------------ terrain (river valley along y, line spans along x)
def river_x(y): return 22*math.sin(y/170.0) + 10*math.sin(y/61.0)
def terrain(x, y):
    d = abs(x - river_x(y))
    if d < 34: return -1.5
    k = clamp((d - 34)/320)
    h = 78*(k*k*(3-2*k)) + max(0.0, d - 354)*0.10
    h += 10*noise.fractal(Vector((x/260, y/260, 0.3)), 0.6, 2.0, 4)*clamp((d - 40)/90)
    h += max(0.0, abs(y) - 700)*0.06       # hills closing the valley far away
    return h - 1.5*clamp(1 - (d - 34)/12)
NX, NY = 220, 260
X0, X1, Y0, Y1 = -1300, 1300, -1700, 1700
bm = bmesh.new(); vs = []
for j in range(NY + 1):
    y = lerp(Y0, Y1, j/NY); row = []
    for i in range(NX + 1):
        x = lerp(X0, X1, i/NX)
        # denser sampling near the valley floor
        row.append(bm.verts.new((x, y, terrain(x, y))))
    vs.append(row)
for j in range(NY):
    for i in range(NX):
        bm.faces.new([vs[j][i], vs[j][i+1], vs[j+1][i+1], vs[j+1][i]])
def ground_mat():
    m = bpy.data.materials.new("ground"); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.92
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.012; nz.inputs["Detail"].default_value = 10
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    cr = nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (0.025, 0.04, 0.015, 1); cr.color_ramp.elements[1].color = (0.10, 0.09, 0.04, 1)
    cr.color_ramp.elements[0].position = 0.35; cr.color_ramp.elements[1].position = 0.7
    nt.links.new(nz.outputs["Fac"], cr.inputs[0]); nt.links.new(cr.outputs[0], b.inputs["Base Color"])
    nz2 = nt.nodes.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = 0.5; nz2.inputs["Detail"].default_value = 6
    nt.links.new(tc.outputs["Object"], nz2.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.5
    nt.links.new(nz2.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs[0], b.inputs["Normal"])
    return add_haze(m)
ground = mesh_obj("terrain", bm, ground_mat())

def water_mat():
    m = bpy.data.materials.new("water"); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (0.02, 0.035, 0.035, 1)
    b.inputs["Roughness"].default_value = 0.04; b.inputs["Specular IOR Level"].default_value = 0.6
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.35; nz.inputs["Detail"].default_value = 6
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1, 4, 1)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); nt.links.new(mp.outputs[0], nz.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.15
    nt.links.new(nz.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs[0], b.inputs["Normal"])
    return add_haze(m, amt=0.6)
bm = bmesh.new(); prev = None
for j in range(161):
    y = lerp(-1700, 1700, j/160); cx = river_x(y)
    ring = [bm.verts.new((cx - 36, y, -0.3)), bm.verts.new((cx + 36, y, -0.3))]
    if prev: bm.faces.new([prev[0], prev[1], ring[1], ring[0]])
    prev = ring
mesh_obj("river", bm, water_mat(), smooth=False)

# trees: instanced conifers + broadleaf blobs on the slopes
M_CON = principled("conifer", (0.018, 0.035, 0.016), 0.9)
M_LEAF = principled("leaf", (0.06, 0.07, 0.02), 0.85)
bm = bmesh.new()
for (r_, d_, z_) in ((3.4, 9, 5.5), (2.6, 8, 10.0), (1.6, 6, 14.0)):
    g_ = bmesh.ops.create_cone(bm, cap_ends=True, segments=9, radius1=r_, radius2=0.0, depth=d_)
    bmesh.ops.translate(bm, verts=g_["verts"], vec=(0, 0, z_))
con_me = bpy.data.meshes.new("con"); bm.to_mesh(con_me); bm.free(); con_me.materials.append(M_CON)
bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=4.5)
bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, 6))
leaf_me = bpy.data.meshes.new("leaf"); bm.to_mesh(leaf_me); bm.free(); leaf_me.materials.append(M_LEAF)
NT = int(os.environ.get("NTREES", "14000"))
k = 0; tries = 0
while k < NT and tries < NT*6:
    tries += 1
    x = rnd.uniform(-750, 750); y = rnd.uniform(-1100, 1100)
    d = abs(x - river_x(y))
    if d < 44: continue
    if abs(x) < 26 and abs(y) < 900 and False: continue
    dens = 0.5 + 0.5*noise.noise(Vector((x/150, y/150, 1.7)))
    if rnd.random() > dens: continue
    con = rnd.random() < 0.8
    o = bpy.data.objects.new(f"t{k}", con_me if con else leaf_me); coll.objects.link(o)
    s = rnd.uniform(0.7, 1.35)
    o.location = (x, y, terrain(x, y) - 1.0); o.scale = (s, s, s*rnd.uniform(0.85, 1.2)); o.rotation_euler.z = rnd.uniform(0, 6.28)
    k += 1

# ------------------------------------------------------------------ pylons + catenary wires
M_STEEL = principled("steel", (0.36, 0.37, 0.38), 0.55, 0.6)
PY = [(-330.0, 0.0), (330.0, 0.0), (-990.0, 0.0), (990.0, 0.0)]
HT = 46.0
def pylon(px, py):
    zb = min(terrain(px + dx, py + dy) for dx in (-5, 5) for dy in (-5, 5)) - 0.5
    bm = bmesh.new()
    def leg(sx, sy, z):
        w = lerp(5.0, 1.2, clamp((z - zb)/(HT - 6)))
        return Vector((px + sx*w, py + sy*w, z))
    lv = [zb + HT*k/9 for k in range(10)]
    cs = ((1, 1), (-1, 1), (-1, -1), (1, -1))
    for c in cs:
        for a, b_ in zip(lv[:-1], lv[1:]): strut(bm, leg(*c, a), leg(*c, b_), 0.16)
    for a, b_ in zip(lv[:-1], lv[1:]):
        for c0, c1 in zip(cs, cs[1:] + cs[:1]):
            strut(bm, leg(*c0, a), leg(*c1, b_), 0.07); strut(bm, leg(*c1, a), leg(*c0, b_), 0.07)
            strut(bm, leg(*c0, b_), leg(*c1, b_), 0.08)
    # cross arm (conductors) at 0.72 HT, earth-wire peak at top
    za = zb + HT*0.72
    for sy in (-1, 1):
        strut(bm, Vector((px - 1.0, py, za)), Vector((px - 1.0, py + sy*11, za)), 0.22)
        strut(bm, Vector((px + 1.0, py, za)), Vector((px + 1.0, py + sy*11, za)), 0.22)
        strut(bm, Vector((px, py + sy*2.0, za + 4.5)), Vector((px, py + sy*11, za)), 0.12)
    strut(bm, Vector((px, py, zb + HT - 0.5)), Vector((px, py, zb + HT + 4)), 0.2)
    mesh_obj(f"pylon{px}", bm, M_STEEL, smooth=False)
    return zb
ZB = {p: pylon(*p) for p in PY}
TOPZ = ZB[PY[0]] + HT + 4.0
TOPZ2 = ZB[PY[1]] + HT + 4.0
ARMZ = (ZB[PY[0]] + HT*0.72, ZB[PY[1]] + HT*0.72)
CAT = 1500.0
def cat(x, x0, x1, z0, z1, a=CAT):
    """catenary through (x0,z0),(x1,z1) with parameter a (approx: shift by linear tilt)"""
    xm = (x0 + x1)/2
    base = a*(math.cosh((x - xm)/a) - 1) - a*(math.cosh((x0 - xm)/a) - 1)
    return lerp(z0, z1, (x - x0)/(x1 - x0)) + base
def shield_z(x): return cat(x, -330, 330, TOPZ, TOPZ2)
M_WIRE = principled("wire", (0.42, 0.42, 0.40), 0.35, 1.0)
WR = float(os.environ.get("WR", "0.045"))
def wire(name, y, z0, z1, x0=-330, x1=330, r=WR):
    pts = [Vector((x, y, cat(x, x0, x1, z0, z1))) for x in [lerp(x0, x1, k/240) for k in range(241)]]
    tube(name, pts, r, M_WIRE)
wire("shield", 0.0, TOPZ, TOPZ2, r=WR*0.9)
for k, y in enumerate((-10.5, 0.0, 10.5)):
    yy = y if y else 10.5
    for s in ((1,) if y else ()):
        pass
for k, y in enumerate((-10.5, 10.5)):
    wire(f"ph{k}", y, ARMZ[0] - 2.5, ARMZ[1] - 2.5, r=WR*1.4)
# continuing spans out of the valley
for (xa, xb) in ((-990, -330), (330, 990)):
    za, zb_ = ZB[(float(xa), 0.0)] + HT + 4, ZB[(float(xb), 0.0)] + HT + 4
    wire(f"sh{xa}", 0.0, za, zb_, xa, xb, r=WR*0.9)
    for k, y in enumerate((-10.5, 10.5)):
        wire(f"ph{xa}{k}", y, ZB[(float(xa), 0.0)] + HT*0.72 - 2.5, ZB[(float(xb), 0.0)] + HT*0.72 - 2.5, xa, xb, r=WR*1.4)
# insulator strings
M_INS = principled("insul", (0.25, 0.32, 0.30), 0.15, coat=1.0)
for px in (-330, 330):
    for y in (-10.5, 10.5):
        z = ZB[(float(px), 0.0)] + HT*0.72
        for j in range(10):
            bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.16, depth=0.08, location=(px, y, z - 0.25*j))
            bpy.context.object.data.materials.append(M_INS)

# ------------------------------------------------------------------ marker balls (alternating orange / white / yellow, orange at the ends)
def ball_mat(name, col):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.38; b.inputs["Coat Weight"].default_value = 0.35
    b.inputs["Coat Roughness"].default_value = 0.25
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 3.0; nz.inputs["Detail"].default_value = 8
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.inputs[6].default_value = (*col, 1)
    mx.inputs[7].default_value = (col[0]*0.72, col[1]*0.70, col[2]*0.7, 1); mx.inputs[0].default_value = 0.5
    nt.links.new(nz.outputs["Fac"], mx.inputs[0]); nt.links.new(mx.outputs[2], b.inputs["Base Color"])
    return add_haze(m)
M_OR = ball_mat("orange", (0.95, 0.18, 0.012))
M_WH = ball_mat("white", (0.80, 0.80, 0.78))
M_YE = ball_mat("yellow", (0.95, 0.62, 0.02))
M_SEAM = principled("seam", (0.05, 0.05, 0.05), 0.6)
BR = 0.46
BALLS = []
bxs = [-330 + 60*k + 30 for k in range(11)]       # ~200 ft spacing
cols = [M_OR, M_WH, M_YE]
for k, bx in enumerate(bxs):
    m = M_OR if k in (0, len(bxs) - 1) else cols[k % 3]
    z = shield_z(bx)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=BR, location=(bx, 0, z))
    o = bpy.context.object; o.data.materials.append(m)
    for p in o.data.polygons: p.use_smooth = True
    # the two halves meet in a seam/flange around the wire, with bolts
    slope = (shield_z(bx + 0.5) - shield_z(bx - 0.5))
    bpy.ops.mesh.primitive_torus_add(major_radius=BR*0.995, minor_radius=0.018, major_segments=64, minor_segments=8, location=(bx, 0, z),
                                     rotation=(0, math.atan2(slope, 1.0), 0))
    bpy.context.object.data.materials.append(m)
    for a in (0, math.pi):
        for s in (-1, 1):
            bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=0.05, depth=0.14, location=(bx + s*0.40, 0.21*math.cos(a), z + 0.13*math.sin(a + 0.6)),
                                                rotation=(0, math.pi/2, 0))
            bpy.context.object.data.materials.append(M_SEAM)
    # rubber bushing where the wire enters
    for s in (-1, 1):
        bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.07, depth=0.12, location=(bx + s*(BR + 0.03), 0, shield_z(bx + s*(BR + 0.03))),
                                            rotation=(0, math.pi/2 + math.atan2(slope, 1.0), 0))
        bpy.context.object.data.materials.append(M_SEAM)
    BALLS.append(Vector((bx, 0, z)))
# a second line of balls on the next span going up the hill (far away)
for k in range(5):
    bx = 400 + 120*k; z = cat(bx, 330, 990, TOPZ2, ZB[(990.0, 0.0)] + HT + 4)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=BR, location=(bx, 0, z))
    bpy.context.object.data.materials.append(M_OR if k % 2 == 0 else M_WH)

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
SUNROT = float(os.environ.get("SUNROT", "210"))
SUNEL = float(os.environ.get("SUNEL", "4.5"))
set_sun(SUNEL, SUNROT, 3.6, (1.0, 0.58, 0.32), 0.16)

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

HERO = 6          # ball used for the close-ups
def pose(t):
    if SHOT == "A":
        k = ease(t/8.4)
        b = BALLS[3]
        cam_d.lens = lerp(26, 30, k)
        loc = b + Vector((lerp(-10, -7, k), lerp(-2.4, -2.0, k), lerp(-1.6, -1.2, k)))
        tgt = b + Vector((30, 0, lerp(-7, -5, k)))
        aim(loc, tgt, t, math.radians(0.06), fstop=8.0, fdist=(b - loc).length)
    elif SHOT == "B":
        u = (t - 8.4)/7.6; k = ease(u)
        b = BALLS[HERO]
        cam_d.lens = lerp(70, 85, k)
        a = math.radians(lerp(-62, -38, u))
        r = lerp(11.0, 9.0, k)
        loc = b + Vector((r*math.sin(a), -r*math.cos(a), lerp(-2.2, -1.2, k)))
        aim(loc, b + Vector((0, 0, 0.05)), t, math.radians(0.08), fstop=4.0)
    elif SHOT == "C":
        u = (t - 16.0)/7.4; k = ease(u)
        cam_d.lens = lerp(32, 36, k)
        loc = Vector((lerp(-262, -258, k), lerp(-8, -7, k), shield_z(-260) - lerp(5.5, 4.5, k)))
        tgt = Vector((lerp(-212, -200, k), 0, shield_z(-205) - 1.5))
        aim(loc, tgt, t, math.radians(0.05), fstop=8.0, fdist=25)
    else:
        u = (t - 23.4)/4.2; k = u
        cam_d.lens = 40
        x = lerp(-178, -140, k)
        loc = Vector((x, -5.0, shield_z(x) + 0.8))
        aim(loc, Vector((x + 45, 0, shield_z(x + 45) - 0.8)), t, math.radians(0.10), fstop=8.0, fdist=30)

# ------------------------------------------------------------------ render
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.cycles.samples = int(os.environ.get("SPP", "10")); sc.cycles.use_denoising = True; sc.cycles.use_adaptive_sampling = True
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transparent_max_bounces = 4
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.resolution_percentage = int(os.environ.get("PCT", "50"))
sc.render.use_persistent_data = True
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
sc.view_settings.exposure = float(os.environ.get("EXPO", "-0.2"))

def screen(p):
    v = world_to_camera_view(sc, cam, Vector(p)); return (v.x*RES[0], (1-v.y)*RES[1], v.z)
def shot_for(t):
    for k, (a, b) in SHOTS.items():
        if a <= t < b: return k
    return "D"
END = SHOTS["D"][1]
mode = sys.argv[sys.argv.index("--")+1] if "--" in sys.argv else "frames"
if mode == "test":
    for t in [float(x) for x in os.environ.get("TT", "3").split(",")]:
        SHOT = shot_for(t); pose(t); bpy.context.view_layer.update()
        sc.render.filepath = f"{OUT}/test_{t}.png"; bpy.ops.render.render(write_still=True)
elif mode == "meta":
    meta = {}
    for i in range(0, int(END*FPS)):
        t = i/FPS; SHOT = shot_for(t); pose(t); bpy.context.view_layer.update()
        meta[i] = {f"b{j}": screen(b) for j, b in enumerate(BALLS)}
        meta[i]["pyl"] = screen((-330, 0, TOPZ - 10))
    json.dump(meta, open(f"{OUT}/meta.json", "w"))
else:
    os.makedirs(f"{OUT}/frames", exist_ok=True)
    step = int(os.environ.get("STEP", "2"))
    i0 = int(os.environ.get("IFROM", "0")); i1 = int(os.environ.get("ITO", int(END*FPS)))
    for i in range(i0, i1, step):
        out = f"{OUT}/frames/f{i:04d}.png"
        if os.path.exists(out): continue
        t = i/FPS; SHOT = shot_for(t); pose(t); bpy.context.view_layer.update()
        sc.render.filepath = out; bpy.ops.render.render(write_still=True)
