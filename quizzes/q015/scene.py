import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import bpy, bmesh, math, json, sys, os, random
from mathutils import Vector, Euler, Matrix
from bpy_extras.object_utils import world_to_camera_view

FPS = 30
RES = (1080, 1920)
OUT = os.environ.get("OUT", QDIR)
SHOT = os.environ.get("SHOT", "A")
SHOTS = {"A": (0.0, 7.4), "B": (7.4, 14.6), "C": (14.6, 21.0), "D": (21.0, 28.2)}
SPEED = 2.2                       # m/s (ice moves past the static ship)
BH = 11.0; KEEL = -7.5; DECK = 7.0; XA = -52.0; XB = 14.0; BRK = 2.8
def stem_x(z): return 38.0 + (z - KEEL)*1.9
XC = stem_x(0.0)                  # stem at the waterline (~52 m)

def ease(x):
    x = max(0.0, min(1.0, x)); return x*x*(3-2*x)
def lerp(a, b, k): return a + (b-a)*k
def S(t): return SPEED*t

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; coll = sc.collection
rnd = random.Random(15)

def principled(name, color, rough=0.5, metal=0.0, coat=0.0, emit=None, estr=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal; b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = estr
    return m
def box(name, size, loc, mat, parent=None, rot=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object; o.name = name; o.scale = size; o.data.materials.append(mat)
    if rot: o.rotation_euler = rot
    if parent: o.parent = parent
    return o
def cyl(name, r, d, loc, mat, parent=None, rot=None, v=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=v, radius=r, depth=d, location=loc)
    o = bpy.context.object; o.name = name; o.data.materials.append(mat)
    if rot: o.rotation_euler = rot
    if parent: o.parent = parent
    for p in o.data.polygons: p.use_smooth = True
    return o

# ------------------------------------------------------------------ hull
def fw(x, z):
    zz = max(0.0, (z - KEEL)/(DECK - KEEL))
    w = zz**0.13 if zz > 0 else 0.0
    xs = stem_x(z)
    if x > XB:
        u = min(1.0, (x - XB)/(xs - XB)); w *= math.sqrt(max(0.0, 1 - u**3.0))
        w *= 1 + 0.10*zz*min(1, (x - XB)/40)           # flare at the bow
    if x < -40: w *= 1 - 0.28*((-40 - x)/12)**2
    return w
def hw(x):                                             # waterline half-width
    return BH*fw(min(x, XC), 0.0) if x <= XC else 0.0

ship = bpy.data.objects.new("ship", None); coll.objects.link(ship)
stations = [XA + i*1.0 for i in range(int(stem_x(DECK) - XA) + 2)]
nz = 26
bm = bmesh.new(); rings = []
for x in stations:
    ring = []
    for j in range(nz + 1):
        z = KEEL + (DECK - KEEL)*j/nz
        xx = min(x, stem_x(z))
        ring.append((xx, max(BH*fw(xx, z), 0.05), z))
    rings.append(ring)
verts = []
for side in (1, -1):
    for ring in rings: verts.append([bm.verts.new((x, side*y, z)) for (x, y, z) in ring])
nst = len(rings)
for s in range(2):
    base = s*nst
    for i in range(nst - 1):
        for j in range(nz):
            a, b_, c, d = verts[base+i][j], verts[base+i+1][j], verts[base+i+1][j+1], verts[base+i][j+1]
            bm.faces.new([a, b_, c, d] if s == 0 else [d, c, b_, a])
for i in range(nst - 1):
    bm.faces.new([verts[i][0], verts[nst+i][0], verts[nst+i+1][0], verts[i+1][0]])
rs, rp = verts[0], verts[nst]
for j in range(nz): bm.faces.new(list(reversed([rs[j], rs[j+1], rp[j+1], rp[j]])))
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.02)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
me = bpy.data.meshes.new("hull"); bm.to_mesh(me); bm.free()
hull = bpy.data.objects.new("hull", me); coll.objects.link(hull); hull.parent = ship
for p in hull.data.polygons: p.use_smooth = True

hm = bpy.data.materials.new("hullpaint"); hm.use_nodes = True; nt = hm.node_tree
b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.5; b.inputs["Coat Weight"].default_value = 0.15
tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep.inputs[0])
nzA = nt.nodes.new("ShaderNodeTexNoise"); nzA.inputs["Scale"].default_value = 0.35; nzA.inputs["Detail"].default_value = 14; nzA.inputs["Roughness"].default_value = 0.7
mpA = nt.nodes.new("ShaderNodeMapping"); mpA.inputs["Scale"].default_value = (0.4, 1, 3)
nt.links.new(tc.outputs["Object"], mpA.inputs["Vector"]); nt.links.new(mpA.outputs["Vector"], nzA.inputs["Vector"])
# ice belt: scraped paint around the waterline
band = nt.nodes.new("ShaderNodeMapRange"); band.inputs[1].default_value = 0.0; band.inputs[2].default_value = 1.6
ab = nt.nodes.new("ShaderNodeMath"); ab.operation = 'ABSOLUTE'
off = nt.nodes.new("ShaderNodeMath"); off.operation = 'SUBTRACT'; off.inputs[1].default_value = -0.2
nt.links.new(sep.outputs["Z"], off.inputs[0]); nt.links.new(off.outputs[0], ab.inputs[0]); nt.links.new(ab.outputs[0], band.inputs[0])
scr = nt.nodes.new("ShaderNodeMath"); scr.operation = 'SUBTRACT'
nt.links.new(nzA.outputs["Fac"], scr.inputs[0]); nt.links.new(band.outputs[0], scr.inputs[1])
scr2 = nt.nodes.new("ShaderNodeMapRange"); scr2.inputs[1].default_value = 0.0; scr2.inputs[2].default_value = 0.08
nt.links.new(scr.outputs[0], scr2.inputs[0])
red = nt.nodes.new("ShaderNodeMix"); red.data_type = 'RGBA'; red.blend_type = 'MULTIPLY'; red.inputs["Factor"].default_value = 0.35
red.inputs[6].default_value = (0.42, 0.025, 0.018, 1); nt.links.new(nzA.outputs["Color"], red.inputs[7])
mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = 'RGBA'
mx.inputs[7].default_value = (0.09, 0.075, 0.07, 1)
nt.links.new(scr2.outputs[0], mx.inputs[0]); nt.links.new(red.outputs[2], mx.inputs[6])
nt.links.new(mx.outputs[2], b.inputs["Base Color"])
rr = nt.nodes.new("ShaderNodeMapRange"); rr.inputs[3].default_value = 0.42; rr.inputs[4].default_value = 0.75
nt.links.new(scr2.outputs[0], rr.inputs[0]); nt.links.new(rr.outputs[0], b.inputs["Roughness"])
hull.data.materials.append(hm)

# deck
M_DECK = principled("deck", (0.20, 0.23, 0.20), 0.75)
bmd = bmesh.new()
xs_ = [XA + k*1.0 for k in range(int(stem_x(DECK) - XA))] + [stem_x(DECK) - 0.3]
outl = [(x, max(0.05, BH*fw(x, DECK - 0.01))) for x in xs_]
vs_ = [bmd.verts.new((x, y, DECK)) for (x, y) in outl] + [bmd.verts.new((x, -y, DECK)) for (x, y) in reversed(outl)]
bmd.faces.new(vs_)
bmesh.ops.triangulate(bmd, faces=bmd.faces[:])
med = bpy.data.meshes.new("deck"); bmd.to_mesh(med); bmd.free()
deck = bpy.data.objects.new("deck", med); coll.objects.link(deck); deck.data.materials.append(M_DECK); deck.parent = ship
M_RED = principled("redsolid", (0.40, 0.03, 0.02), 0.5)
for s in (1, -1):
    for k in range(30):
        x = 30 + k*1.35
        if x > stem_x(DECK) - 1.5: break
        y = BH*fw(x, DECK - 0.01)
        ang = math.atan2(BH*fw(x + 0.5, DECK - 0.01) - BH*fw(x - 0.5, DECK - 0.01), 1.0)
        box(f"bw{s}{k}", (1.45, 0.15, 1.3), (x, s*(y - 0.1), DECK + 0.65), M_RED, ship, rot=(0, 0, s*ang))

# superstructure
M_WHITE = principled("white", (0.80, 0.79, 0.75), 0.45)
M_WIN = principled("win", (0.015, 0.02, 0.03), 0.04, coat=1.0)
M_YEL = principled("yel", (0.75, 0.48, 0.04), 0.45)
M_BLK = principled("blk", (0.02, 0.02, 0.02), 0.6)
M_ORG = principled("org", (0.85, 0.25, 0.02), 0.5)
M_GREY = principled("grey", (0.35, 0.35, 0.36), 0.5, 0.6)
box("house1", (26, 18, 4.0), (14, 0, DECK + 2.0), M_WHITE, ship)
box("house2", (20, 16, 3.6), (16, 0, DECK + 5.8), M_WHITE, ship)
box("house3", (14, 14, 3.4), (19, 0, DECK + 9.3), M_WHITE, ship)
box("bridge", (8, 21, 3.4), (22, 0, DECK + 12.7), M_WHITE, ship)
box("bridgewin", (8.15, 21.15, 1.5), (22, 0, DECK + 13.1), M_WIN, ship)
for k, z in enumerate((2.3, 6.0, 9.5)):
    w = (18, 16, 14)[k]; L = (26, 20, 14)[k]; xc = (14, 16, 19)[k]
    box(f"win{k}", (L - 3, w + 0.08, 0.7), (xc, 0, DECK + z), M_WIN, ship)
    box(f"winf{k}", (0.12, w - 3, 0.7), (xc + L/2 + 0.02, 0, DECK + z), M_WIN, ship)
box("bridgetop", (9, 22, 0.4), (22, 0, DECK + 14.6), M_WHITE, ship)
cyl("mast", 0.35, 9, (19, 0, DECK + 19.0), M_WHITE, ship)
box("yard", (0.3, 6, 0.3), (19, 0, DECK + 21.5), M_WHITE, ship)
cyl("radome", 0.9, 1.2, (16, 3, DECK + 15.6), M_WHITE, ship)
cyl("radar", 0.1, 4, (21, -2, DECK + 16.5), M_BLK, ship, rot=(math.radians(90), 0, 0))
box("funnelbase", (10, 10, 6), (-6, 0, DECK + 3.0), M_WHITE, ship)
box("funnel", (7, 8, 8), (-7, 0, DECK + 9.0), M_YEL, ship)
box("funneltop", (7.1, 8.1, 1.5), (-7, 0, DECK + 13.6), M_BLK, ship)
box("aftdeckhouse", (14, 16, 3.4), (-24, 0, DECK + 1.7), M_WHITE, ship)
box("helideck", (18, 20, 0.5), (-41, 0, DECK + 3.8), M_GREY, ship)
for s in (1, -1):
    for x in (-48, -42, -36):
        cyl(f"hp{s}{x}", 0.25, 3.6, (x, s*8, DECK + 1.8), M_GREY, ship)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=1, location=(4, s*10.4, DECK + 2.6))
    o = bpy.context.object; o.scale = (3.4, 1.1, 1.0); o.data.materials.append(M_ORG); o.parent = ship
    cyl(f"crane{s}", 0.5, 6, (34, s*5.5, DECK + 3), M_YEL, ship)
box("winch", (3, 4, 1.4), (48, 0, DECK + 0.7), M_GREY, ship)
for k, (hx, hy) in enumerate(((40, 0), (34, 0), (-30, 6), (-30, -6), (6, 7), (6, -7))):
    box(f"hatch{k}", (3.2, 3.2, 0.5), (hx, hy, DECK + 0.25), M_GREY, ship)
for s_ in (1, -1):
    for k in range(40):
        x = -50 + k*2.2
        if x > 28: break
        cyl(f"rail{s_}{k}", 0.05, 1.1, (x, s_*(BH*fw(x, DECK) - 0.25), DECK + 0.55), M_WHITE, ship, v=6)
    box(f"railtop{s_}", (78, 0.08, 0.08), (-11, s_*(BH - 0.25), DECK + 1.1), M_WHITE, ship)

# ------------------------------------------------------------------ ice sheet with the channel cut out
def ice_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.55
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); mp.name = "flow"
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 0.02; n1.inputs["Detail"].default_value = 10; n1.inputs["Roughness"].default_value = 0.6
    nt.links.new(mp.outputs["Vector"], n1.inputs["Vector"])
    vo = nt.nodes.new("ShaderNodeTexVoronoi"); vo.feature = 'DISTANCE_TO_EDGE'; vo.inputs["Scale"].default_value = 0.012
    nt.links.new(mp.outputs["Vector"], vo.inputs["Vector"])
    ridge = nt.nodes.new("ShaderNodeMapRange"); ridge.inputs[1].default_value = 0.0; ridge.inputs[2].default_value = 0.05
    ridge.inputs[3].default_value = 0.0; ridge.inputs[4].default_value = 0.0
    nt.links.new(vo.outputs["Distance"], ridge.inputs[0])
    c1 = nt.nodes.new("ShaderNodeMix"); c1.data_type = 'RGBA'
    c1.inputs[6].default_value = (0.42, 0.52, 0.62, 1); c1.inputs[7].default_value = (0.72, 0.75, 0.79, 1)
    nt.links.new(n1.outputs["Fac"], c1.inputs[0])
    n3 = nt.nodes.new("ShaderNodeTexNoise"); n3.inputs["Scale"].default_value = 0.05; n3.inputs["Detail"].default_value = 12; n3.inputs["Roughness"].default_value = 0.65
    nt.links.new(mp.outputs["Vector"], n3.inputs["Vector"])
    bare = nt.nodes.new("ShaderNodeMapRange"); bare.inputs[1].default_value = 0.56; bare.inputs[2].default_value = 0.62
    nt.links.new(n3.outputs["Fac"], bare.inputs[0])
    c2 = nt.nodes.new("ShaderNodeMix"); c2.data_type = 'RGBA'; c2.inputs[7].default_value = (0.20, 0.32, 0.40, 1)
    nt.links.new(bare.outputs[0], c2.inputs[0]); nt.links.new(c1.outputs[2], c2.inputs[6])
    crk = nt.nodes.new("ShaderNodeMapRange"); crk.inputs[1].default_value = 0.0; crk.inputs[2].default_value = 0.012
    crk.inputs[3].default_value = 0.8; crk.inputs[4].default_value = 0.0
    nt.links.new(vo.outputs["Distance"], crk.inputs[0])
    c3 = nt.nodes.new("ShaderNodeMix"); c3.data_type = 'RGBA'; c3.inputs[7].default_value = (0.10, 0.18, 0.24, 1)
    nt.links.new(crk.outputs[0], c3.inputs[0]); nt.links.new(c2.outputs[2], c3.inputs[6])
    nt.links.new(c2.outputs[2], b.inputs["Base Color"])
    rg = nt.nodes.new("ShaderNodeMapRange"); rg.inputs[3].default_value = 0.75; rg.inputs[4].default_value = 0.12
    nt.links.new(bare.outputs[0], rg.inputs[0]); nt.links.new(rg.outputs[0], b.inputs["Roughness"])
    n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 0.6; n2.inputs["Detail"].default_value = 8
    nt.links.new(mp.outputs["Vector"], n2.inputs["Vector"])
    ad = nt.nodes.new("ShaderNodeMath"); ad.operation = 'MULTIPLY_ADD'; ad.inputs[1].default_value = 0.25
    nt.links.new(n2.outputs["Fac"], ad.inputs[0]); nt.links.new(ridge.outputs[0], ad.inputs[2])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.35; bp.inputs["Distance"].default_value = 0.3
    nt.links.new(ad.outputs[0], bp.inputs["Height"]); nt.links.new(bp.outputs[0], b.inputs["Normal"])
    return m
M_SHEET = ice_mat("sheet")
def chan_w(x):
    if x > XC: return 0.0
    if x > 0: return hw(x) + BRK
    return BH + BRK
bm = bmesh.new()
xs = sorted(set([-60000, -12000, -3000, -2000, -1200, -800] + list(range(-640, int(XC) + 1, 4)) + [XC, XC + 4, 120, 300, 800, 1600, 3000, 12000, 60000]))
cols = [60000, 12000, 3000, 1200, 400, 120, 40, 20]
for xi in range(len(xs) - 1):
    x0, x1 = xs[xi], xs[xi+1]
    w0 = chan_w(x0) if x0 >= -640 else 0.0; w1 = chan_w(x1) if x1 >= -640 else 0.0
    for s in (1, -1):
        pts0 = [s*c for c in cols] + [s*w0]; pts1 = [s*c for c in cols] + [s*w1]
        for k in range(len(pts0) - 1):
            a = bm.verts.new((x0, pts0[k], 0.12)); b_ = bm.verts.new((x1, pts1[k], 0.12))
            c = bm.verts.new((x1, pts1[k+1], 0.12)); d = bm.verts.new((x0, pts0[k+1], 0.12))
            bm.faces.new([a, b_, c, d])
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
for f in bm.faces:
    if f.normal.z < 0: f.normal_flip()
me = bpy.data.meshes.new("sheet"); bm.to_mesh(me); bm.free()
sheet = bpy.data.objects.new("sheet", me); coll.objects.link(sheet); sheet.data.materials.append(M_SHEET)
bm = bmesh.new()
for s in (1, -1):
    prev = None
    for x in list(range(-640, int(XC) + 1, 2)) + [XC]:
        w = chan_w(x)
        a = bm.verts.new((x, s*w, 0.12)); c = bm.verts.new((x, s*w, -0.9))
        if prev: bm.faces.new([prev[0], a, c, prev[1]])
        prev = (a, c)
me = bpy.data.meshes.new("rim"); bm.to_mesh(me); bm.free()
rim = bpy.data.objects.new("rim", me); coll.objects.link(rim)
M_ICEBLUE = principled("iceblue", (0.30, 0.55, 0.62), 0.25)
rim.data.materials.append(M_ICEBLUE)

def water_mat():
    m = bpy.data.materials.new("water"); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.06
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); mp.name = "flow"
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 0.5; n1.inputs["Detail"].default_value = 8
    nt.links.new(mp.outputs["Vector"], n1.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.12
    nt.links.new(n1.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs[0], b.inputs["Normal"])
    n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 0.25; n2.inputs["Detail"].default_value = 12; n2.inputs["Roughness"].default_value = 0.7
    nt.links.new(mp.outputs["Vector"], n2.inputs["Vector"])
    rp = nt.nodes.new("ShaderNodeMapRange"); rp.inputs[1].default_value = 0.44; rp.inputs[2].default_value = 0.58
    nt.links.new(n2.outputs["Fac"], rp.inputs[0])
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = 'RGBA'
    mx.inputs[6].default_value = (0.004, 0.012, 0.016, 1); mx.inputs[7].default_value = (0.55, 0.62, 0.66, 1)
    nt.links.new(rp.outputs[0], mx.inputs[0]); nt.links.new(mx.outputs[2], b.inputs["Base Color"])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[3].default_value = 0.05; mr.inputs[4].default_value = 0.7
    nt.links.new(rp.outputs[0], mr.inputs[0]); nt.links.new(mr.outputs[0], b.inputs["Roughness"])
    return m
M_WATER = water_mat()
bpy.ops.mesh.primitive_plane_add(size=2000, location=(-300, 0, 0.0))
water = bpy.context.object; water.data.materials.append(M_WATER)

# ------------------------------------------------------------------ broken floes (linked-mesh instances)
def floe_mat():
    m = bpy.data.materials.new("floe"); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.45
    geo = nt.nodes.new("ShaderNodeNewGeometry"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    tr = nt.nodes.new("ShaderNodeVectorTransform"); tr.vector_type = 'NORMAL'; tr.convert_from = 'WORLD'; tr.convert_to = 'OBJECT'
    nt.links.new(geo.outputs["Normal"], tr.inputs[0]); nt.links.new(tr.outputs[0], sep.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[1].default_value = 0.55; mr.inputs[2].default_value = 0.8
    nt.links.new(sep.outputs["Z"], mr.inputs[0])
    tc = nt.nodes.new("ShaderNodeTexCoord"); n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 0.8; n1.inputs["Detail"].default_value = 8
    nt.links.new(tc.outputs["Object"], n1.inputs["Vector"])
    top = nt.nodes.new("ShaderNodeMix"); top.data_type = 'RGBA'
    top.inputs[6].default_value = (0.55, 0.62, 0.70, 1); top.inputs[7].default_value = (0.78, 0.80, 0.83, 1)
    nt.links.new(n1.outputs["Fac"], top.inputs[0])
    side = nt.nodes.new("ShaderNodeMix"); side.data_type = 'RGBA'
    side.inputs[6].default_value = (0.30, 0.50, 0.58, 1)
    nt.links.new(mr.outputs[0], side.inputs[0]); nt.links.new(top.outputs[2], side.inputs[7])
    nt.links.new(side.outputs[2], b.inputs["Base Color"])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.3
    n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 4; n2.inputs["Detail"].default_value = 6
    nt.links.new(tc.outputs["Object"], n2.inputs["Vector"]); nt.links.new(n2.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs[0], b.inputs["Normal"])
    return m
M_FLOE = floe_mat()
TH = 1.1
shapes = []
for k in range(10):
    bm = bmesh.new(); n = rnd.randint(5, 7)
    angs = sorted(rnd.uniform(0, 2*math.pi) for _ in range(n))
    top, bot = [], []
    for a in angs:
        r = rnd.uniform(0.75, 1.0)
        top.append(bm.verts.new((r*math.cos(a), r*math.sin(a), 0.12)))
        bot.append(bm.verts.new((r*math.cos(a)*0.97, r*math.sin(a)*0.97, 0.12 - TH)))
    bm.faces.new(top); bm.faces.new(list(reversed(bot)))
    for i in range(n):
        j = (i + 1) % n; bm.faces.new([top[i], bot[i], bot[j], top[j]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(f"floe{k}"); bm.to_mesh(me); bm.free(); me.materials.append(M_FLOE)
    shapes.append(me)
XCON = {}
def xcon_of(y):
    k = round(abs(y), 1)
    if k not in XCON:
        xc = XC
        xx = XC
        while xx > 0:
            if hw(xx) >= min(abs(y), BH*0.97): xc = xx; break
            xx -= 0.25
        else: xc = 0.0
        XCON[k] = xc
    return XCON[k]
floes = []
X0, X1 = -640.0, XC + S(28.5) + 6
x = X0
while x < X1:
    y = -BH - BRK
    while y < BH + BRK:
        sz = rnd.uniform(2.4, 4.6)
        o = bpy.data.objects.new("f", shapes[rnd.randrange(10)]); coll.objects.link(o)
        o.scale = (sz*rnd.uniform(0.8, 1.3), sz*rnd.uniform(0.8, 1.2), 1.0)
        floes.append({"o": o, "X": x + rnd.uniform(-0.6, 0.6), "y": y + rnd.uniform(-0.4, 0.4), "rz": rnd.uniform(0, 6.28),
                      "dz": rnd.uniform(-0.08, 0.08), "r1": rnd.uniform(-1, 1), "r2": rnd.uniform(-1, 1), "r3": rnd.random(), "sz": sz})
        y += sz*0.92
    x += rnd.uniform(2.3, 3.0)

rubble = []
for k in range(450):
    X = rnd.uniform(-640, 520); side = rnd.choice((1, -1))
    y = side*(BH + BRK + 2 + abs(rnd.gauss(0, 1))*rnd.choice((6, 25, 90)))
    if rnd.random() < 0.35:              # pressure ridge lines
        X = rnd.choice((-300, -120, 80, 260, 410)) + rnd.uniform(-4, 4) + abs(y)*0.4
    if math.hypot(X - (XC + 44 + S(7.4)), y + 46) < 18: continue
    o = bpy.data.objects.new("r", shapes[rnd.randrange(10)]); coll.objects.link(o)
    sz = rnd.uniform(0.5, 1.6); o.scale = (sz, sz*rnd.uniform(0.6, 1.0), rnd.uniform(0.3, 0.6))
    o.rotation_euler = (rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), rnd.uniform(0, 6.28))
    rubble.append((o, X, y, rnd.uniform(0.0, 0.35)))
def rubble_pose(t):
    for o, X, y, z in rubble: o.location = (X - S(t), y, z)

def floe_pose(f, t):
    xs = f["X"] - S(t); y = f["y"]; o = f["o"]
    a = xcon_of(y) - xs                               # metres since the bow reached this floe
    if a < 0 or xs > XC + 0.5:
        o.hide_render = True; return
    o.hide_render = False
    sgn = 1 if y >= 0 else -1
    if xs > XA and abs(y) < hw(xs) + BRK:
        # pressed down by the hull and tipped along its side
        k = ease(a/5.0)
        under = abs(y) < hw(xs) - 1.5
        tilt = math.radians(70 if under else 35)*k*(0.6 + 0.4*f["r3"])
        z = -(1.2 if under else 0.35)*k - (4.0 if under and a > 10 else 0)
        o.location = (xs, y + sgn*0.6*k, z)
        o.rotation_euler = (sgn*tilt, f["r1"]*0.3*k, f["rz"])
        return
    behind = max(0.0, XA - xs)
    k = ease(a/4.0)
    bob = math.sin(t*0.9 + f["r3"]*6.28)*0.05
    tilt = (f["r1"]*math.radians(6) + f["r2"]*math.radians(5)*math.exp(-behind/80))*k
    z = -0.03*k + bob - (0.14 if f["r3"] < 0.2 else 0)*k
    if 0 < behind < 25: z -= 0.3*(1 - behind/25)
    o.location = (xs, y, z + f["dz"])
    o.rotation_euler = (tilt, f["r2"]*math.radians(8)*k, f["rz"] + f["r1"]*0.4*k)

# ------------------------------------------------------------------ environment
wo = bpy.data.worlds.new("w"); sc.world = wo; wo.use_nodes = True
bg = wo.node_tree.nodes["Background"]
sky = wo.node_tree.nodes.new("ShaderNodeTexSky"); sky.sky_type = 'MULTIPLE_SCATTERING'
wo.node_tree.links.new(sky.outputs[0], bg.inputs[0])
sky.altitude = 0; sky.aerosol_density = 1.4; sky.sun_intensity = 0.5
sun_d = bpy.data.lights.new("sun", 'SUN'); sun_d.angle = math.radians(0.6)
sun = bpy.data.objects.new("sun", sun_d); coll.objects.link(sun)
def set_sun(el, rot, energy, color, bgs):
    sky.sun_elevation = math.radians(el); sky.sun_rotation = math.radians(rot)
    sun.rotation_euler = Euler((math.radians(90 - el), 0, math.radians(rot + 90)))
    sun_d.energy = energy; sun_d.color = color; bg.inputs[1].default_value = bgs
SUNROT = float(os.environ.get("SUNROT", "120"))
set_sun(8, SUNROT, 3.6, (1.0, 0.68, 0.45), 0.18)

# ------------------------------------------------------------------ camera
cam_d = bpy.data.cameras.new("cam"); cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 36; cam_d.clip_end = 100000; cam_d.clip_start = 0.1
cam = bpy.data.objects.new("cam", cam_d); coll.objects.link(cam); sc.camera = cam
SH = [(rnd.uniform(-1, 1), rnd.uniform(-1, 1)) for _ in range(400)]
def shake(t, amp, rate=1.8):
    i = int(t*rate); f = t*rate - i; a, b_ = SH[i % 400], SH[(i+1) % 400]; f = f*f*(3-2*f)
    return (a[0]+(b_[0]-a[0])*f)*amp, (a[1]+(b_[1]-a[1])*f)*amp
def aim(loc, tgt, t, amp):
    cam.location = loc
    e = (Vector(tgt)-Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sx, sy = shake(t, amp); e.x += sx; e.z += sy; cam.rotation_euler = e

FLOWS = [m.node_tree.nodes["flow"] for m in (M_SHEET, M_WATER)]
def ship_pose(t):
    ph = math.sin(t*0.55)
    ship.rotation_euler = (math.radians(0.15)*math.sin(t*0.4), -math.radians(0.6 + 0.5*ph), 0)
    ship.location = (0, 0, 0.25 + 0.2*ph)
def cam_pose(t):
    cam_d.dof.use_dof = False
    if SHOT == "A":
        k = ease(t/7.4)
        cam_d.lens = lerp(45, 52, k)
        loc = (lerp(175, 160, k), lerp(-120, -105, k), lerp(62, 55, k))
        tgt = (lerp(5, 10, k), 0, 0)
        aim(loc, tgt, t, math.radians(0.05))
    elif SHOT == "B":
        u = t - 7.4; k = ease(u/7.2)
        cam_d.lens = 46
        loc = (XC + 44 - S(t) + S(7.4), -46, 3.0)     # standing on the ice, the bow comes towards us
        tgt = (XC - 6, 0, lerp(3.5, 4.0, k))
        aim(loc, tgt, t, math.radians(0.06))
    elif SHOT == "C":
        u = t - 14.6; k = ease(u/6.4)
        cam_d.lens = lerp(28, 32, k)
        loc = (lerp(XC + 30, XC + 24, k), lerp(-14, -10, k), lerp(70, 74, k))
        tgt = (lerp(XC - 4, XC - 8, k), 0, 0)
        aim(loc, tgt, t, math.radians(0.08))
    else:
        u = t - 21.0; k = ease(u/7.2)
        cam_d.lens = lerp(40, 34, k)
        loc = (lerp(-150, -170, k), lerp(26, 30, k), lerp(42, 58, k))
        tgt = (lerp(10, 0, k), 0, 0)
        aim(loc, tgt, t, math.radians(0.05))
def pose(t):
    for fl in FLOWS: fl.inputs["Location"].default_value = (S(t), 0, 0)
    ship_pose(t)
    for f in floes: floe_pose(f, t)
    rubble_pose(t)
    cam_pose(t)

# ------------------------------------------------------------------ render
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.cycles.samples = int(os.environ.get("SPP", "10")); sc.cycles.use_denoising = True; sc.cycles.use_adaptive_sampling = True
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transparent_max_bounces = 4
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.resolution_percentage = int(os.environ.get("PCT", "50"))
sc.render.use_persistent_data = True
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
sc.view_settings.exposure = float(os.environ.get("EXPO", "-0.8"))

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
        t = i/FPS; SHOT = shot_for(t); ship_pose(t); cam_pose(t); bpy.context.view_layer.update()
        M = ship.matrix_world
        meta[i] = {"bow": screen(M @ Vector((XC - 2, -3, 1.0))), "stem": screen(M @ Vector((stem_x(4.0), 0, 4.0))),
                   "hull": screen(M @ Vector((10, -BH, 2.0))), "chan": screen((-70, 0, 0)), "ship": screen(M @ Vector((10, 0, 12)))}
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
