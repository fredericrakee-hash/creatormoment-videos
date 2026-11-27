import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
# Quiz #31 - Taipei 101 in a typhoon; the 660 t tuned mass damper sphere between floors 87-92 swings.
import bpy, bmesh, math, json, sys, os, random
from mathutils import Vector, Euler, noise
from bpy_extras.object_utils import world_to_camera_view

FPS = 30
RES = (1080, 1920)
OUT = os.environ.get("OUT", QDIR)
SHOT = "A"
SHOTS = {"A": (0.0, 10.6), "B": (10.6, 14.6), "C": (14.6, 21.6), "D": (21.6, 30.2), "E": (30.2, 34.6)}
END = 34.6
EXT = ("A", "B")
if "frames" in sys.argv:
    _st = int(os.environ.get("STEP", "2")); _a = int(os.environ.get("IFROM", "0")); _b = int(os.environ.get("ITO", int(END*FPS)))
    if all(os.path.exists(f"{OUT}/frames/f{i:04d}.png") for i in range(_a, _b, _st)): sys.exit(0)

def ease(x):
    x = max(0.0, min(1.0, x)); return x*x*(3-2*x)
def lerp(a, b, k): return a + (b-a)*k
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; coll = sc.collection
rnd = random.Random(31)
C_EXT = bpy.data.collections.new("ext"); coll.children.link(C_EXT)
C_INT = bpy.data.collections.new("int"); coll.children.link(C_INT)
CUR = [C_EXT]

HAZE = (0.42, 0.44, 0.48)
def add_haze(m, dist=2500.0, amt=0.85, col=None, strength=0.5):
    col = col or HAZE
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
def principled(name, color, rough=0.5, metal=0.0, emit=None, haze=False):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit[0], 1); b.inputs["Emission Strength"].default_value = emit[1]
    return add_haze(m) if haze else m
def noisy(name, col, col2, rough, scale, detail=10, metal=0.0, bump=0.3, haze=False):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = detail
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    cr = nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (*col, 1); cr.color_ramp.elements[1].color = (*col2, 1)
    cr.color_ramp.elements[0].position = 0.3; cr.color_ramp.elements[1].position = 0.7
    nt.links.new(nz.outputs["Fac"], cr.inputs[0]); nt.links.new(cr.outputs[0], b.inputs["Base Color"])
    if bump:
        nz2 = nt.nodes.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = scale*12; nz2.inputs["Detail"].default_value = 4
        nt.links.new(tc.outputs["Object"], nz2.inputs["Vector"])
        bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump
        nt.links.new(nz2.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs[0], b.inputs["Normal"])
    return add_haze(m) if haze else m
def link(o):
    for c in o.users_collection: c.objects.unlink(o)
    CUR[0].objects.link(o); return o
def mesh_obj(name, bm, mat, smooth=True, parent=None):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); CUR[0].objects.link(o); o.data.materials.append(mat)
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    if parent: o.parent = parent
    return o
def box(name, size, loc, mat, parent=None, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = link(bpy.context.object); o.name = name; o.scale = size; o.data.materials.append(mat)
    if parent: o.parent = parent
    return o
def cyl(name, loc, r, depth, mat, parent=None, verts=24, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    o = link(bpy.context.object); o.name = name; o.data.materials.append(mat)
    for p in o.data.polygons: p.use_smooth = True
    if parent: o.parent = parent
    return o
def frustum(bm, z0, z1, w0, w1, x=0.0, y=0.0, cham=0.18):
    """square frustum with chamfered corners (8-sided ring) from z0 (half-width w0) to z1 (w1)"""
    rings = []
    for z, w in ((z0, w0), (z1, w1)):
        c = w*cham
        pts = [(w, -w+c), (w, w-c), (w-c, w), (-w+c, w), (-w, w-c), (-w, -w+c), (-w+c, -w), (w-c, -w)]
        rings.append([bm.verts.new((x+px, y+py, z)) for px, py in pts])
    for k in range(8):
        bm.faces.new([rings[0][k], rings[0][(k+1) % 8], rings[1][(k+1) % 8], rings[1][k]])
    bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[1])
def tube(bm, p, q, r, n=6):
    d = q - p; L = d.length
    if L < 1e-4: return
    z = d.normalized(); x = z.cross(Vector((0, 0, 1)) if abs(z.z) < 0.9 else Vector((1, 0, 0))).normalized(); y = z.cross(x)
    a0 = [bm.verts.new(p + (x*math.cos(2*math.pi*k/n) + y*math.sin(2*math.pi*k/n))*r) for k in range(n)]
    a1 = [bm.verts.new(q + (x*math.cos(2*math.pi*k/n) + y*math.sin(2*math.pi*k/n))*r) for k in range(n)]
    for k in range(n): bm.faces.new([a0[k], a0[(k+1) % n], a1[(k+1) % n], a1[k]])

# =================================================================== EXTERIOR
CUR[0] = C_EXT
def glass_mat():
    m = bpy.data.materials.new("glass"); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.05, 0.11, 0.10, 1); b.inputs["Roughness"].default_value = 0.12; b.inputs["Metallic"].default_value = 0.7
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep.inputs[0])
    # floor lines (every 4.2 m): thin dark mullion bands
    wv = nt.nodes.new("ShaderNodeTexWave"); wv.wave_type = 'BANDS'; wv.bands_direction = 'Z'; wv.inputs["Scale"].default_value = 1.0
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1/4.2/1.0, 1/4.2, 1/4.2*0.5)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); nt.links.new(mp.outputs[0], wv.inputs["Vector"])
    # lit windows: random warm cells
    vor = nt.nodes.new("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = 1.0
    mp2 = nt.nodes.new("ShaderNodeMapping"); mp2.inputs["Scale"].default_value = (1/2.2, 1/2.2, 1/4.2)
    nt.links.new(tc.outputs["Object"], mp2.inputs["Vector"]); nt.links.new(mp2.outputs[0], vor.inputs["Vector"])
    rr = nt.nodes.new("ShaderNodeMath"); rr.operation = 'GREATER_THAN'; rr.inputs[1].default_value = 0.9
    sepc = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(vor.outputs["Color"], sepc.inputs[0]); nt.links.new(sepc.outputs[0], rr.inputs[0])
    rm = nt.nodes.new("ShaderNodeMath"); rm.operation = 'GREATER_THAN'; rm.inputs[1].default_value = 0.25; nt.links.new(wv.outputs["Fac"], rm.inputs[0])
    mm = nt.nodes.new("ShaderNodeMath"); mm.operation = 'MULTIPLY'; nt.links.new(rr.outputs[0], mm.inputs[0]); nt.links.new(rm.outputs[0], mm.inputs[1])
    ms = nt.nodes.new("ShaderNodeMath"); ms.operation = 'MULTIPLY'; ms.inputs[1].default_value = 1.2; nt.links.new(mm.outputs[0], ms.inputs[0])
    b.inputs["Emission Color"].default_value = (1.0, 0.78, 0.5, 1); nt.links.new(ms.outputs[0], b.inputs["Emission Strength"])
    cr = nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (0.012, 0.016, 0.016, 1); cr.color_ramp.elements[0].position = 0.12
    cr.color_ramp.elements[1].color = (0.06, 0.13, 0.12, 1); cr.color_ramp.elements[1].position = 0.2
    nt.links.new(wv.outputs["Fac"], cr.inputs[0]); nt.links.new(cr.outputs[0], b.inputs["Base Color"])
    return add_haze(m, 3500, 0.75)
M_GLASS = glass_mat()
M_FRAME = principled("frame", (0.2, 0.24, 0.24), 0.4, 0.6, haze=True)
TOWER = bpy.data.objects.new("tower", None); C_EXT.objects.link(TOWER)
bm = bmesh.new()
# podium/base: floors 1-25, tapering inwards
frustum(bm, 0, 26, 40, 40)
frustum(bm, 26, 108, 34, 27, cham=0.2)
# 8 flared sections of 8 floors each
z = 108.0
SEG_H = 33.6
for s in range(8):
    frustum(bm, z, z + SEG_H, 24.5, 30.5, cham=0.22); z += SEG_H
TOP0 = z   # ~377 m
frustum(bm, z, z + 18, 22, 22, cham=0.25); z += 18
frustum(bm, z, z + 12, 18, 16, cham=0.3); z += 12
frustum(bm, z, z + 20, 12, 11, cham=0.3); z += 20
frustum(bm, z, z + 14, 8, 7, cham=0.3); z += 14
frustum(bm, z, z + 10, 5, 4, cham=0.3); z += 10
TW = mesh_obj("tw", bm, M_GLASS, smooth=False, parent=TOWER)
bm = bmesh.new()
z = 108.0
for s in range(9):
    frustum(bm, z - 0.8, z + 0.8, 31.0 if s else 28, 31.2 if s else 28.2, cham=0.22); z += SEG_H
mesh_obj("ledges", bm, M_FRAME, smooth=False, parent=TOWER)
SPIRE_Z = z
spire = cyl("spire", (0, 0, 451 + 30), 1.6, 60, M_FRAME, TOWER, 12)
cyl("spire2", (0, 0, 451 + 62), 0.6, 8, M_FRAME, TOWER, 8)
TOP = 508.0
# corner "ruyi" ornaments on the podium
for sx in (-1, 1):
    for sy in (-1, 1):
        o = cyl("ruyi", (sx*30, sy*30, 112), 4, 1.2, M_FRAME, TOWER, 16, rot=(0, math.radians(90), math.radians(45*sx*sy)))

# city blocks
M_CITY = []
for k, col in enumerate(((0.16, 0.16, 0.16), (0.22, 0.21, 0.2), (0.12, 0.13, 0.14), (0.3, 0.29, 0.27))):
    m = bpy.data.materials.new(f"city{k}"); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1); b.inputs["Roughness"].default_value = 0.7
    tc = nt.nodes.new("ShaderNodeTexCoord")
    vor = nt.nodes.new("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = 0.4
    nt.links.new(tc.outputs["Generated"] if False else tc.outputs["Object"], vor.inputs["Vector"])
    sp = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(vor.outputs["Color"], sp.inputs[0])
    g = nt.nodes.new("ShaderNodeMath"); g.operation = 'GREATER_THAN'; g.inputs[1].default_value = 0.9; nt.links.new(sp.outputs[1], g.inputs[0])
    gm = nt.nodes.new("ShaderNodeMath"); gm.operation = 'MULTIPLY'; gm.inputs[1].default_value = 1.6; nt.links.new(g.outputs[0], gm.inputs[0])
    b.inputs["Emission Color"].default_value = (1.0, 0.75, 0.45, 1); nt.links.new(gm.outputs[0], b.inputs["Emission Strength"])
    M_CITY.append(add_haze(m, 2500, 0.85))
cbm = [bmesh.new() for _ in M_CITY]
for i in range(-40, 41):
    for j in range(-40, 41):
        x, y = i*55 + rnd.uniform(-8, 8), j*55 + rnd.uniform(-8, 8)
        d = math.hypot(x, y)
        if d < 90 or rnd.random() < 0.15: continue
        if y > 900 and x > -600: continue   # leave room for the camera hill (Elephant Mountain side)
        h = rnd.choice([12, 18, 24, 30, 36, 45, 60, 80]) * (1.3 if d < 700 else 1.0)
        w = rnd.uniform(14, 34); l = rnd.uniform(14, 40)
        r = bmesh.ops.create_cube(cbm[rnd.randrange(4)], size=1.0)
        for v in r["verts"]: v.co.x = v.co.x*w + x; v.co.y = v.co.y*l + y; v.co.z = (v.co.z + 0.5)*h
for k, b_ in enumerate(cbm): mesh_obj(f"city{k}", b_, M_CITY[k], smooth=False)
bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=20000)
mesh_obj("groundp", bm, principled("gnd", (0.05, 0.05, 0.05), 0.9, haze=True), smooth=False)
# mountains behind
M_MTN = noisy("mtn", (0.03, 0.05, 0.035), (0.07, 0.09, 0.06), 0.9, 0.003, bump=0.0)
add_haze(M_MTN, 9000, 0.8)
for k in range(9):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1, location=(-6000 + k*1500 + rnd.uniform(-300, 300), -6500 - rnd.uniform(0, 2500), -200))
    o = link(bpy.context.object); o.scale = (rnd.uniform(1400, 2400), 900, rnd.uniform(500, 900)); o.data.materials.append(M_MTN)

# storm clouds: noise-alpha layers that drift
def cloud_mat(name, scale, dens, col, emit=0.25):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = 10; nz.inputs["Roughness"].default_value = 0.62
    nt.links.new(mp.outputs[0], nz.inputs["Vector"])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[1].default_value = dens; mr.inputs[2].default_value = dens + 0.22
    nt.links.new(nz.outputs["Fac"], mr.inputs[0])
    dif = nt.nodes.new("ShaderNodeBsdfDiffuse"); dif.inputs["Color"].default_value = (*col, 1)
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (*col, 1); em.inputs["Strength"].default_value = emit
    ad = nt.nodes.new("ShaderNodeAddShader"); nt.links.new(dif.outputs[0], ad.inputs[0]); nt.links.new(em.outputs[0], ad.inputs[1])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mx = nt.nodes.new("ShaderNodeMixShader"); nt.links.new(mr.outputs[0], mx.inputs[0])
    nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(ad.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    m.blend_method = 'BLEND' if hasattr(m, "blend_method") else None
    return m, mp.inputs["Location"]
CLOUDS = []
for k, (zc, sc_, d_, col, sz) in enumerate(((1400, 0.00035, 0.30, (0.30, 0.31, 0.34), 160000), (900, 0.0006, 0.42, (0.36, 0.36, 0.38), 60000),
                                          (470, 0.0025, 0.52, (0.45, 0.45, 0.47), 2400), (430, 0.003, 0.55, (0.5, 0.5, 0.52), 2400))):
    m, loc = cloud_mat(f"cl{k}", sc_*1000/1000, d_, col)
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=sz/2)
    o = mesh_obj(f"cloud{k}", bm, m, smooth=False); o.location = (0, 0, zc)
    o.visible_shadow = False
    CLOUDS.append((o, loc, sc_))

# =================================================================== INTERIOR (damper chamber)
CUR[0] = C_INT
IZ = 0.0       # sphere centre at rest = (0,0,0); chamber floor (walkway) at z = -1.2
R = 2.75
L_PEND = 11.5   # cable length
M_GOLD = bpy.data.materials.new("gold"); M_GOLD.use_nodes = True; nt = M_GOLD.node_tree; b = nt.nodes["Principled BSDF"]
b.inputs["Base Color"].default_value = (1.0, 0.60, 0.20, 1); b.inputs["Metallic"].default_value = 1.0; b.inputs["Roughness"].default_value = 0.26
tc = nt.nodes.new("ShaderNodeTexCoord"); nzg = nt.nodes.new("ShaderNodeTexNoise"); nzg.inputs["Scale"].default_value = 6; nzg.inputs["Detail"].default_value = 8
nt.links.new(tc.outputs["Object"], nzg.inputs["Vector"])
mrg = nt.nodes.new("ShaderNodeMapRange"); mrg.inputs[3].default_value = 0.18; mrg.inputs[4].default_value = 0.36
nt.links.new(nzg.outputs["Fac"], mrg.inputs[0]); nt.links.new(mrg.outputs[0], b.inputs["Roughness"])
M_DARK = principled("dark", (0.025, 0.025, 0.028), 0.5, 0.6)
M_STEEL = principled("steel", (0.35, 0.36, 0.38), 0.35, 1.0)
M_CONC = noisy("conc", (0.16, 0.155, 0.15), (0.26, 0.25, 0.24), 0.85, 0.6, bump=0.15)
M_FLOOR = noisy("floor", (0.12, 0.115, 0.11), (0.2, 0.19, 0.18), 0.35, 0.8, bump=0.05)
M_BEAM = principled("beam", (0.12, 0.13, 0.14), 0.45, 0.8)
M_RAIL = principled("rail", (0.5, 0.5, 0.52), 0.3, 1.0)
M_WIN = bpy.data.materials.new("winint"); M_WIN.use_nodes = True; nt = M_WIN.node_tree
nt.nodes.remove(nt.nodes["Principled BSDF"]); emw = nt.nodes.new("ShaderNodeEmission")
tcw = nt.nodes.new("ShaderNodeTexCoord"); nzw = nt.nodes.new("ShaderNodeTexNoise"); nzw.inputs["Scale"].default_value = 0.25; nzw.inputs["Detail"].default_value = 6
WIN_LOC = nt.nodes.new("ShaderNodeMapping"); nt.links.new(tcw.outputs["Object"], WIN_LOC.inputs["Vector"]); nt.links.new(WIN_LOC.outputs[0], nzw.inputs["Vector"])
crw = nt.nodes.new("ShaderNodeValToRGB"); crw.color_ramp.elements[0].color = (0.18, 0.2, 0.24, 1); crw.color_ramp.elements[1].color = (0.55, 0.56, 0.6, 1)
nt.links.new(nzw.outputs["Fac"], crw.inputs[0]); nt.links.new(crw.outputs[0], emw.inputs["Color"]); emw.inputs["Strength"].default_value = 1.6
nt.links.new(emw.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
WIN_LOC = WIN_LOC.inputs["Location"]

INT = bpy.data.objects.new("interior", None); C_INT.objects.link(INT); INT.location = (0, 0, 0)
BALL = bpy.data.objects.new("ball", None); C_INT.objects.link(BALL)
# stacked plates (41 plates, small gaps)
bm = bmesh.new(); NPL = 41; n = 72
for p in range(NPL):
    z0 = -R + p*(2*R/NPL) + 0.012; z1 = z0 + 2*R/NPL - 0.024
    rr = []
    for z_ in (z0, z1):
        zc = max(-R + 0.01, min(R - 0.01, z_))
        r_ = math.sqrt(max(0.04, R*R - zc*zc))
        rr.append([bm.verts.new((r_*math.cos(2*math.pi*k/n), r_*math.sin(2*math.pi*k/n), z_)) for k in range(n)])
    for k in range(n): bm.faces.new([rr[0][k], rr[0][(k+1) % n], rr[1][(k+1) % n], rr[1][k]])
    bm.faces.new(list(reversed(rr[0]))); bm.faces.new(rr[1])
mesh_obj("plates", bm, M_GOLD, parent=BALL)
# core plug + cradle ring at the equator (cable anchors)
cyl("cradle", (0, 0, 0.0), R + 0.18, 0.5, M_DARK, BALL, 72)
cyl("plug", (0, 0, -R - 0.25), 0.7, 0.6, M_DARK, BALL, 32)
cyl("pin", (0, 0, -R - 1.0), 0.28, 1.2, M_STEEL, BALL, 24)
NCAB = 8
CAB_BALL = [Vector(((R + 0.3)*math.cos(2*math.pi*(k + 0.5)/NCAB), (R + 0.3)*math.sin(2*math.pi*(k + 0.5)/NCAB), 0.1)) for k in range(NCAB)]
CAB_TOP = [Vector((4.2*math.cos(2*math.pi*(k + 0.5)/NCAB), 4.2*math.sin(2*math.pi*(k + 0.5)/NCAB), L_PEND)) for k in range(NCAB)]
for k in range(NCAB):
    cyl(f"clamp{k}", CAB_BALL[k], 0.22, 0.6, M_STEEL, BALL, 12)
# hydraulic dampers: 8 struts from the lower cradle to the floor ring
DMP_BALL = [Vector(((R*0.6)*math.cos(2*math.pi*k/8), (R*0.6)*math.sin(2*math.pi*k/8), -R*0.8)) for k in range(8)]
DMP_FLOOR = [Vector((6.5*math.cos(2*math.pi*k/8), 6.5*math.sin(2*math.pi*k/8), -R - 2.6)) for k in range(8)]
cyl("lowring", (0, 0, -R*0.8), R*0.62, 0.35, M_DARK, BALL, 48)
CABLES = bpy.data.objects.new("cables", bpy.data.meshes.new("cables")); C_INT.objects.link(CABLES); CABLES.data.materials.append(M_STEEL)
DAMP_C = bpy.data.objects.new("dampc", bpy.data.meshes.new("dampc")); C_INT.objects.link(DAMP_C); DAMP_C.data.materials.append(M_DARK)
DAMP_R = bpy.data.objects.new("dampr", bpy.data.meshes.new("dampr")); C_INT.objects.link(DAMP_R); DAMP_R.data.materials.append(M_STEEL)
# chamber: floor slab (lower pit), walkway ring at the equator, walls, ceiling, beams, windows
FL = -R - 2.6
box("pit", (30, 30, 0.4), (0, 0, FL - 0.2), M_CONC)
cyl("bumper", (0, 0, FL + 0.7), 1.4, 1.4, M_DARK, None, 32)
for k in range(8):
    cyl(f"dmount{k}", DMP_FLOOR[k] + Vector((0, 0, -0.1)), 0.45, 0.5, M_STEEL, None, 16)
WALK_Z = -1.1
bm = bmesh.new(); n = 64; ri, ro = 6.0, 10.5
def _ring(r, z): return [bm.verts.new((r*math.cos(2*math.pi*k/n), r*math.sin(2*math.pi*k/n), z)) for k in range(n)]
it, ot, ib, ob = _ring(ri, WALK_Z), _ring(ro, WALK_Z), _ring(ri, WALK_Z - 0.35), _ring(ro, WALK_Z - 0.35)
for k in range(n):
    k1 = (k+1) % n
    bm.faces.new([it[k], ot[k], ot[k1], it[k1]]); bm.faces.new([ib[k], ib[k1], ob[k1], ob[k]])
    bm.faces.new([it[k], it[k1], ib[k1], ib[k]]); bm.faces.new([ot[k], ob[k], ob[k1], ot[k1]])
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
WALKWAY = mesh_obj("walkway", bm, M_FLOOR, smooth=False)
# glass balustrade + handrail
bm = bmesh.new()
for k in range(n):
    a0, a1 = 2*math.pi*k/n, 2*math.pi*(k+1)/n
    tube(bm, Vector((ri*math.cos(a0), ri*math.sin(a0), WALK_Z + 1.1)), Vector((ri*math.cos(a1), ri*math.sin(a1), WALK_Z + 1.1)), 0.035)
    if k % 4 == 0: tube(bm, Vector((ri*math.cos(a0), ri*math.sin(a0), WALK_Z)), Vector((ri*math.cos(a0), ri*math.sin(a0), WALK_Z + 1.1)), 0.03)
mesh_obj("rail", bm, M_RAIL)
M_BGLASS = bpy.data.materials.new("bglass"); M_BGLASS.use_nodes = True; _nt = M_BGLASS.node_tree; _nt.nodes.remove(_nt.nodes["Principled BSDF"])
_tr = _nt.nodes.new("ShaderNodeBsdfTransparent"); _gl = _nt.nodes.new("ShaderNodeBsdfGlossy"); _gl.inputs["Roughness"].default_value = 0.05
_fr = _nt.nodes.new("ShaderNodeLayerWeight"); _fr.inputs["Blend"].default_value = 0.25
_mx = _nt.nodes.new("ShaderNodeMixShader"); _nt.links.new(_fr.outputs["Fresnel"], _mx.inputs[0]); _nt.links.new(_tr.outputs[0], _mx.inputs[1]); _nt.links.new(_gl.outputs[0], _mx.inputs[2])
_nt.links.new(_mx.outputs[0], _nt.nodes["Material Output"].inputs["Surface"])
bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=ri, depth=1.0, location=(0, 0, WALK_Z + 0.55), end_fill_type='NOTHING')
o = link(bpy.context.object); o.data.materials.append(M_BGLASS)
# walls (octagon-ish box), windows on two sides, ceiling with beams
WALL = 14.0; CEIL = L_PEND + 0.6
for k in range(4):
    a = k*math.pi/2
    loc = (WALL*math.cos(a), WALL*math.sin(a), (FL + CEIL)/2)
    box(f"wall{k}", (0.6, 2*WALL, CEIL - FL), loc, M_CONC, rot=(0, 0, a))
box("ceil", (2*WALL, 2*WALL, 0.6), (0, 0, CEIL + 0.3), M_CONC)
for k in range(-3, 4):
    box(f"beamx{k}", (2*WALL, 0.5, 0.9), (0, k*4.0, CEIL - 0.45), M_BEAM)
for k in (-1, 1):
    box(f"beamy{k}", (0.6, 2*WALL, 1.2), (k*4.2, 0, CEIL - 0.9), M_BEAM)
# columns
for sx in (-1, 1):
    for sy in (-1, 1):
        box(f"col{sx}{sy}", (1.2, 1.2, CEIL - FL), (sx*11.5, sy*11.5, (FL + CEIL)/2), M_BEAM)
# windows (stormy daylight) on the -y and +x walls
for (cx, cy, rz) in ((0, -WALL + 0.35, 0), (WALL - 0.35, 0, math.pi/2)):
    for j in range(-2, 3):
        o = box(f"win{cx}{j}", (3.6, 0.05, 5.0), (cx + (j*4.6 if rz == 0 else 0), cy + (j*4.6 if rz else 0), WALK_Z + 3.2), M_WIN, rot=(0, 0, rz))
        o.visible_shadow = False
        box(f"mul{cx}{j}", (0.3, 0.3, 5.4), (cx + (j*4.6 + 2.3 if rz == 0 else 0), cy + (j*4.6 + 2.3 if rz else 0), WALK_Z + 3.2), M_BEAM, rot=(0, 0, rz))
# lights
def area(name, loc, size, energy, col, rot=(0, 0, 0)):
    d = bpy.data.lights.new(name, 'AREA'); d.size = size; d.energy = energy; d.color = col
    o = bpy.data.objects.new(name, d); C_INT.objects.link(o); o.location = loc; o.rotation_euler = rot; return o
for k in range(4):
    a = k*math.pi/2 + math.pi/4
    sp = bpy.data.lights.new(f"spot{k}", 'SPOT'); sp.energy = 9000; sp.spot_size = math.radians(40); sp.color = (1.0, 0.82, 0.6); sp.shadow_soft_size = 0.4
    o = bpy.data.objects.new(f"spot{k}", sp); C_INT.objects.link(o); o.location = (9*math.cos(a), 9*math.sin(a), CEIL - 1.2)
    o.rotation_euler = (Vector((0, 0, 0)) - o.location).to_track_quat('-Z', 'Y').to_euler()
area("fillwin", (0, -WALL + 1.5, WALK_Z + 3.5), 12, 2500, (0.75, 0.82, 0.95), rot=(math.radians(90), 0, 0))
area("fillwin2", (WALL - 1.5, 0, WALK_Z + 3.5), 12, 1800, (0.75, 0.82, 0.95), rot=(math.radians(90), 0, math.radians(90)))
area("pitlight", (0, 0, FL + 0.3), 14, 1100, (1.0, 0.8, 0.6), rot=(math.radians(180), 0, 0))
area("walklight", (0, 0, WALK_Z + 4.0), 18, 600, (1.0, 0.88, 0.75))
area("toplight", (0, 0, CEIL - 1.5), 6, 900, (1.0, 0.86, 0.7))

# =================================================================== sky + sun
wo = bpy.data.worlds.new("w"); sc.world = wo; wo.use_nodes = True
bg = wo.node_tree.nodes["Background"]
sky = wo.node_tree.nodes.new("ShaderNodeTexSky"); sky.sky_type = 'MULTIPLE_SCATTERING'
wo.node_tree.links.new(sky.outputs[0], bg.inputs[0])
sky.altitude = 0; sky.aerosol_density = 3.0; sky.sun_intensity = 0.35
sun_d = bpy.data.lights.new("sun", 'SUN'); sun_d.angle = math.radians(4)
sun = bpy.data.objects.new("sun", sun_d); C_EXT.objects.link(sun)
SUNROT = float(os.environ.get("SUNROT", "-60")); SUNEL = float(os.environ.get("SUNEL", "4"))
sky.sun_elevation = math.radians(SUNEL); sky.sun_rotation = math.radians(SUNROT)
sun.rotation_euler = Euler((math.radians(90 - SUNEL), 0, math.radians(SUNROT + 90)))
sun_d.energy = 1.6; sun_d.color = (1.0, 0.62, 0.40); bg.inputs[1].default_value = 0.22

# =================================================================== motion
PER = 6.8
def bldg(t):
    """building drift at the top (m), gusty"""
    g = 0.6*math.sin(2*math.pi*t/PER) + 0.25*math.sin(2*math.pi*t/2.9 + 1.0)
    return g
def ball_amp(t):
    if t < 14.6: return 0.15
    if t < 21.6: return lerp(0.18, 0.4, ease((t - 14.6)/7.0))
    if t < 30.2: return lerp(0.45, 1.0, ease((t - 21.6)/4.0))
    return lerp(0.9, 0.6, ease((t - 30.2)/4.0))
def ball_off(t):
    a = ball_amp(t)
    x = a*math.sin(2*math.pi*t/PER)
    y = 0.25*a*math.sin(2*math.pi*t/PER + 1.3)
    return Vector((x, y, (x*x + y*y)/(2*L_PEND)))
def place(t, frame=None):
    # tower lean (exaggerated a little so it reads)
    TOWER.rotation_euler = (0.0, math.radians(0.12)*bldg(t), 0.0)
    for o, loc, s in CLOUDS:
        v = 34.0 if o.location.z < 600 else 12.0
        loc.default_value = (t*v, t*v*0.35, 0)
    WIN_LOC.default_value = (t*1.2, 0, 0)
    off = ball_off(t)
    BALL.location = off
    BALL.rotation_euler = (-off.y/L_PEND, off.x/L_PEND, 0)
    bpy.context.view_layer.update()
    mw = BALL.matrix_world
    bm = bmesh.new()
    for k in range(NCAB):
        p = mw @ CAB_BALL[k]
        for s in (-0.12, 0.12):
            side = Vector((-math.sin(2*math.pi*(k + 0.5)/NCAB), math.cos(2*math.pi*(k + 0.5)/NCAB), 0))*s
            tube(bm, p + side*0.6, CAB_TOP[k] + side*0.6, 0.045, 8)
    me = CABLES.data; me.clear_geometry(); bm.to_mesh(me); bm.free()
    bmc = bmesh.new(); bmr = bmesh.new()
    for k in range(8):
        p = mw @ DMP_BALL[k]; q = DMP_FLOOR[k]; mid = p + (q - p)*0.45
        tube(bmc, q, mid, 0.26, 12); tube(bmr, mid - (q - p).normalized()*0.3, p, 0.11, 10)
    for m_, b_ in ((DAMP_C, bmc), (DAMP_R, bmr)):
        me = m_.data; me.clear_geometry(); b_.to_mesh(me); b_.free()
        for p_ in me.polygons: p_.use_smooth = True

# =================================================================== camera
cam_d = bpy.data.cameras.new("cam"); cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 36; cam_d.clip_end = 40000; cam_d.clip_start = 0.1
cam = bpy.data.objects.new("cam", cam_d); coll.objects.link(cam); sc.camera = cam
SH = [(rnd.uniform(-1, 1), rnd.uniform(-1, 1)) for _ in range(400)]
def shake(t, amp, rate=1.6):
    i = int(t*rate); f = t*rate - i; a, b_ = SH[i % 400], SH[(i+1) % 400]; f = f*f*(3-2*f)
    return (a[0]+(b_[0]-a[0])*f)*amp, (a[1]+(b_[1]-a[1])*f)*amp
def aim(loc, tgt, t, amp, rate=1.6):
    cam.location = loc
    e = (Vector(tgt)-Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sx, sy = shake(t, amp, rate); e.x += sx; e.z += sy; cam.rotation_euler = e
def pose(t):
    cam_d.dof.use_dof = False
    if SHOT == "A":
        k = ease(t/10.6); cam_d.lens = lerp(150, 172, k)
        aim(Vector((350, 3400, 190)), Vector((0, 0, 268)), t, math.radians(0.012), 2.0)
    elif SHOT == "B":
        k = ease((t - 10.6)/4.0); cam_d.lens = lerp(300, 330, k)
        aim(Vector((420, 3300, 210)), Vector((0, 0, lerp(395, 405, k))), t, math.radians(0.01), 2.4)
    elif SHOT == "C":
        k = ease((t - 14.6)/7.0); cam_d.lens = lerp(24, 28, k)
        loc = Vector((lerp(-9.6, -8.2, k), lerp(-5.6, -4.6, k), WALK_Z + 1.65))
        aim(loc, Vector((0, 0, lerp(-0.2, 0.6, k))), t, math.radians(0.15))
        cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = 4.0; cam_d.dof.focus_distance = (loc - Vector((0, 0, 0))).length - 2.5
    elif SHOT == "D":
        k = ease((t - 21.6)/8.6); cam_d.lens = lerp(20, 22, k)
        loc = Vector((lerp(3.6, 3.2, k), lerp(-8.6, -8.0, k), FL + 0.9))
        aim(loc, Vector((0, 0, 1.2)), t, math.radians(0.2), 1.8)
    else:
        k = ease((t - 30.2)/4.4); cam_d.lens = lerp(30, 32, k)
        loc = Vector((lerp(8.8, 9.3, k), lerp(5.4, 4.6, k), WALK_Z + 1.6))
        aim(loc, Vector((0, 0, -0.6)), t, math.radians(0.12))
        cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = 5.6; cam_d.dof.focus_distance = loc.length - 2.7

# =================================================================== render
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.cycles.samples = int(os.environ.get("SPP", "10")); sc.cycles.use_denoising = True; sc.cycles.use_adaptive_sampling = True
sc.cycles.max_bounces = 5; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 3; sc.cycles.transparent_max_bounces = 8; sc.cycles.transmission_bounces = 2
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.resolution_percentage = int(os.environ.get("PCT", "50"))
sc.render.use_persistent_data = True
sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5; sc.render.motion_blur_position = 'START'
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
EXPO = float(os.environ.get("EXPO", "-0.3"))

def screen(p):
    v = world_to_camera_view(sc, cam, Vector(p)); return (v.x*RES[0], (1-v.y)*RES[1], v.z)
def shot_for(t):
    for k, (a, b) in SHOTS.items():
        if a <= t < b: return k
    return "E"
def setup(t, frame=None):
    global SHOT
    SHOT = shot_for(t)
    ext = SHOT in EXT
    C_EXT.hide_render = not ext; C_INT.hide_render = ext
    bg.inputs[1].default_value = 0.22 if ext else 0.0
    sc.view_settings.exposure = EXPO + (0.0 if ext else 0.05)
    if frame is not None: sc.frame_set(frame)
    place(t, frame); pose(t); bpy.context.view_layer.update()
mode = sys.argv[sys.argv.index("--")+1] if "--" in sys.argv else "frames"
if mode == "test":
    for t in [float(x) for x in os.environ.get("TT", "3").split(",")]:
        setup(t, int(round(t*FPS)))
        sc.render.filepath = f"{OUT}/test_{t}.png"; bpy.ops.render.render(write_still=True)
elif mode == "meta":
    meta = {}
    for i in range(0, int(END*FPS)):
        t = i/FPS; setup(t)
        meta[i] = {"top": screen(Vector((0, 0, 430))), "spire": screen(Vector((0, 0, 500))), "mid": screen(Vector((0, 0, 395))),
                   "ball": screen(Vector(BALL.location) + Vector((0, 0, R*0.6))), "ballc": screen(Vector(BALL.location)),
                   "damp": screen(DMP_FLOOR[1]*0.6 + Vector((0, 0, -R - 0.6))), "cable": screen(CAB_TOP[3]*0.5 + Vector((0, 0, L_PEND*0.55))),
                   "off": ball_off(t).x, "shot": SHOT}
    json.dump(meta, open(f"{OUT}/meta.json", "w"))
else:
    import time as _tm
    os.makedirs(f"{OUT}/frames", exist_ok=True)
    step = int(os.environ.get("STEP", "2"))
    i0 = int(os.environ.get("IFROM", "0")); i1 = int(os.environ.get("ITO", int(END*FPS)))
    for i in range(i0, i1, step):
        out = f"{OUT}/frames/f{i:04d}.png"
        if os.path.exists(out): continue
        _t0 = _tm.time(); setup(i/FPS, i)
        sc.render.filepath = out; bpy.ops.render.render(write_still=True)
        print(f"TIMING f{i} {_tm.time()-_t0:.1f}s", flush=True)
