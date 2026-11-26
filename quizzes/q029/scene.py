import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
# Quiz #29 - Soyuz descent module touchdown on the Kazakh steppe (soft-landing motors fire ~0.8 m above ground)
import bpy, bmesh, math, json, sys, os, random
from mathutils import Vector, Euler, noise
from bpy_extras.object_utils import world_to_camera_view

FPS = 30
RES = (1080, 1920)
OUT = os.environ.get("OUT", QDIR)
SHOT = "A"
SHOTS = {"A": (0.0, 8.8), "B": (8.8, 17.6), "C": (17.6, 25.7), "D": (25.7, 33.5)}
T_FIRE = 21.6          # soft-landing motors fire (0.8 m above ground)
V_DESC = 7.2           # m/s under the main parachute
T_TOUCH = T_FIRE + 0.22
if "frames" in sys.argv:
    _st = int(os.environ.get("STEP", "2")); _a = int(os.environ.get("IFROM", "0")); _b = int(os.environ.get("ITO", int(33.5*FPS)))
    if all(os.path.exists(f"{OUT}/frames/f{i:04d}.png") for i in range(_a, _b, _st)): sys.exit(0)

def ease(x):
    x = max(0.0, min(1.0, x)); return x*x*(3-2*x)
def lerp(a, b, k): return a + (b-a)*k
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; coll = sc.collection
rnd = random.Random(29)

HAZE = (1.0, 0.74, 0.52)
def add_haze(m, dist=2500.0, amt=0.8, col=HAZE, strength=0.55):
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
def principled(name, color, rough=0.5, metal=0.0, emit=None, haze=True):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit[0], 1); b.inputs["Emission Strength"].default_value = emit[1]
    return add_haze(m) if haze else m
def noisy(name, col, col2, rough, scale, detail=10, metal=0.0, bump=0.3, haze=True):
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
def mesh_obj(name, bm, mat, smooth=True, parent=None):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); coll.objects.link(o); o.data.materials.append(mat)
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    if parent: o.parent = parent
    return o
def cyl(name, loc, r, depth, mat, parent=None, verts=24, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name; o.data.materials.append(mat)
    for p in o.data.polygons: p.use_smooth = True
    if parent: o.parent = parent
    return o
def lathe(name, prof, mat, parent=None, n=64):
    bm = bmesh.new(); rings = []
    for (r, z) in prof:
        rings.append([bm.verts.new((r*math.cos(2*math.pi*k/n), r*math.sin(2*math.pi*k/n), z)) for k in range(n)])
    for a, b_ in zip(rings[:-1], rings[1:]):
        for k in range(n):
            bm.faces.new([a[k], a[(k+1) % n], b_[(k+1) % n], b_[k]])
    return mesh_obj(name, bm, mat, True, parent)

# ------------------------------------------------------------------ steppe
def ground_h(x, y):
    d = math.hypot(x, y)
    h = 0.25*noise.fractal(Vector((x/40, y/40, 0.3)), 0.6, 2.0, 4)
    h += 2.5*noise.fractal(Vector((x/900, y/900, 1.7)), 0.5, 2.0, 4)*clamp((d - 150)/400)
    return h - 0.25*noise.fractal(Vector((0, 0, 0.3)), 0.6, 2.0, 4)
def axis(a, b, da, ia, ib, db):
    out = []; v = a
    while v < b:
        out.append(v); v += da if (v < ia or v > ib) else db
    return out
XS = [-30000, -15000] + axis(-6000, 6000, 60, -120, 120, 1.0) + [6000, 15000, 30000]; YS = list(XS)
bm = bmesh.new(); vs = []
for y in YS: vs.append([bm.verts.new((x, y, ground_h(x, y))) for x in XS])
for j in range(len(YS) - 1):
    for i in range(len(XS) - 1):
        bm.faces.new([vs[j][i], vs[j][i+1], vs[j+1][i+1], vs[j+1][i]])
M_STEPPE = noisy("steppe", (0.05, 0.042, 0.022), (0.15, 0.12, 0.055), 0.95, 0.02, bump=0.4)
_n = M_STEPPE.node_tree; _cr = [n for n in _n.nodes if n.type == "VALTORGB"][0]
_tc = [n for n in _n.nodes if n.type == "TEX_COORD"][0]
_hf = _n.nodes.new("ShaderNodeTexNoise"); _hf.inputs["Scale"].default_value = 3.0; _hf.inputs["Detail"].default_value = 8
_n.links.new(_tc.outputs["Object"], _hf.inputs["Vector"])
_mm = _n.nodes.new("ShaderNodeMix"); _mm.data_type = "RGBA"; _mm.blend_type = "MULTIPLY"; _mm.inputs[0].default_value = 0.7
_n.links.new(_cr.outputs[0], _mm.inputs[6]); _n.links.new(_hf.outputs["Color"], _mm.inputs[7])
_n.links.new(_mm.outputs[2], _n.nodes["Principled BSDF"].inputs["Base Color"])
# scorch ring under the capsule (shows after touchdown)
nt = M_STEPPE.node_tree; bsdf = nt.nodes["Principled BSDF"]
src = bsdf.inputs["Base Color"].links[0].from_socket
tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep.inputs[0])
ln = nt.nodes.new("ShaderNodeVectorMath"); ln.operation = 'LENGTH'
cmb = nt.nodes.new("ShaderNodeCombineXYZ"); nt.links.new(sep.outputs["X"], cmb.inputs[0]); nt.links.new(sep.outputs["Y"], cmb.inputs[1])
nt.links.new(cmb.outputs[0], ln.inputs[0])
nzs = nt.nodes.new("ShaderNodeTexNoise"); nzs.inputs["Scale"].default_value = 1.5; nt.links.new(tc.outputs["Object"], nzs.inputs["Vector"])
adn = nt.nodes.new("ShaderNodeMath"); adn.operation = 'MULTIPLY_ADD'; adn.inputs[1].default_value = 1.4
nt.links.new(nzs.outputs["Fac"], adn.inputs[0]); nt.links.new(ln.outputs["Value"], adn.inputs[2])
mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[1].default_value = 2.2; mr.inputs[2].default_value = 4.0; mr.inputs[3].default_value = 1.0; mr.inputs[4].default_value = 0.0
nt.links.new(adn.outputs[0], mr.inputs[0])
SCORCH = nt.nodes.new("ShaderNodeMath"); SCORCH.operation = 'MULTIPLY'; SCORCH.inputs[1].default_value = 0.0
nt.links.new(mr.outputs[0], SCORCH.inputs[0])
mxs = nt.nodes.new("ShaderNodeMix"); mxs.data_type = 'RGBA'; mxs.inputs[7].default_value = (0.03, 0.025, 0.02, 1)
nt.links.new(SCORCH.outputs[0], mxs.inputs[0]); nt.links.new(src, mxs.inputs[6]); nt.links.new(mxs.outputs[2], bsdf.inputs["Base Color"])
mesh_obj("ground", bm, M_STEPPE, smooth=True)

# dry grass tufts near the touchdown point (instanced)
tuft_coll = bpy.data.collections.new("tufts"); sc.collection.children.link(tuft_coll); tuft_coll.instance_offset = (0, 0, -500)
GRASS_COLS = ((0.36, 0.27, 0.12), (0.24, 0.19, 0.08), (0.42, 0.33, 0.17), (0.17, 0.15, 0.06))
for k in range(6):
    r2 = random.Random(100 + k); bm = bmesh.new()
    for b_ in range(14):
        a = r2.uniform(0, 6.283); lean = r2.uniform(0.15, 0.7); hgt = r2.uniform(0.35, 1.0); w = 0.025
        ca, sa = math.cos(a), math.sin(a)
        p0 = [bm.verts.new((-w*sa, w*ca, -0.05)), bm.verts.new((w*sa, -w*ca, -0.05))]
        tip = bm.verts.new((ca*lean*hgt, sa*lean*hgt, hgt))
        bm.faces.new([p0[0], p0[1], tip])
    me = bpy.data.meshes.new(f"tuft{k}"); bm.to_mesh(me); bm.free()
    me.materials.append(principled(f"gr{k}", GRASS_COLS[k % 4], 0.8))
    o = bpy.data.objects.new(f"tuft{k}", me); tuft_coll.objects.link(o); o.location = (0, 0, -500)
bm = bmesh.new(); vv = []
gx = axis(-70, 70.01, 2.0, -1e9, 1e9, 2.0)
for y in gx: vv.append([bm.verts.new((x, y, ground_h(x, y))) for x in gx])
for j in range(len(gx) - 1):
    for i in range(len(gx) - 1): bm.faces.new([vv[j][i], vv[j][i+1], vv[j+1][i+1], vv[j+1][i]])
patch = mesh_obj("tuftpatch", bm, M_STEPPE)
ps = patch.modifiers.new("ps", 'PARTICLE_SYSTEM').particle_system
st = ps.settings; st.type = 'HAIR'; st.count = int(os.environ.get("NTUFT", "320000")); st.hair_length = 1.0
st.render_type = 'COLLECTION'; st.instance_collection = tuft_coll; st.use_collection_pick_random = True
st.particle_size = 0.28; st.size_random = 0.7
st.use_rotations = True; st.rotation_mode = 'NONE'; st.rotation_factor_random = 0.15; st.phase_factor_random = 2.0
st.emit_from = 'FACE'; st.use_emit_random = True; st.distribution = 'RAND'; st.use_advanced_hair = True
patch.hide_render = False

# ------------------------------------------------------------------ descent module ("headlight" shape, scorched)
CAP = bpy.data.objects.new("capsule", None); coll.objects.link(CAP)
M_CHAR = noisy("char", (0.035, 0.026, 0.02), (0.20, 0.13, 0.08), 0.75, 1.6, detail=14, bump=0.6)
M_BOT = noisy("bottom", (0.16, 0.15, 0.14), (0.30, 0.29, 0.27), 0.5, 3.0, metal=0.5, bump=0.2)
M_NOZ = principled("noz", (0.05, 0.05, 0.05), 0.4, 0.8)
M_HATCH = principled("hatch", (0.08, 0.07, 0.06), 0.6, 0.4)
prof = [(0.98, 0.12), (1.08, 0.22), (1.10, 0.36), (1.07, 0.6), (1.0, 0.95), (0.9, 1.3), (0.76, 1.62), (0.6, 1.86), (0.42, 2.02), (0.35, 2.06)]
lathe("cap_side", prof, M_CHAR, CAP)
lathe("cap_bottom", [(0.0, 0.04), (0.5, 0.06), (0.85, 0.1), (0.98, 0.12)], M_BOT, CAP)
lathe("cap_top", [(0.35, 2.06), (0.33, 2.12), (0.0, 2.14)], M_HATCH, CAP)
NOZZLES = []
for k in range(6):
    a = k*math.pi/3 + 0.3
    p = (0.55*math.cos(a), 0.55*math.sin(a), 0.03)
    cyl(f"noz{k}", p, 0.07, 0.06, M_NOZ, CAP, 16); NOZZLES.append(Vector(p))
# window + antenna stubs
cyl("win", (1.0*math.cos(2.4), 1.0*math.sin(2.4), 1.05), 0.11, 0.06, principled("glass", (0.01, 0.01, 0.012), 0.05), CAP, 20, rot=(0, math.radians(80), 2.4))
# riser attachment point (capsule-local)
ATT = Vector((0.0, 0.0, 2.15))

# soft-landing flash: emissive jets + light
M_JET = bpy.data.materials.new("jet"); M_JET.use_nodes = True; nt = M_JET.node_tree
nt.nodes.remove(nt.nodes["Principled BSDF"])
em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (1.0, 0.72, 0.42, 1); JET_E = em.inputs["Strength"]; JET_E.default_value = 0.0
nt.links.new(em.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
JETS = []
for k, p in enumerate(NOZZLES):
    bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=0.05, radius2=0.22, depth=0.8, location=(p.x, p.y, p.z - 0.4))
    o = bpy.context.object; o.data.materials.append(M_JET); o.parent = CAP; JETS.append(o)
fl_d = bpy.data.lights.new("flash", 'POINT'); fl_d.color = (1.0, 0.7, 0.4); fl_d.shadow_soft_size = 0.6; fl_d.energy = 0
FLASH = bpy.data.objects.new("flash", fl_d); coll.objects.link(FLASH)

# ------------------------------------------------------------------ main parachute (orange/white gores)
M_CHW = bpy.data.materials.new("chw"); M_CHO = bpy.data.materials.new("cho")
for m, col in ((M_CHW, (0.85, 0.84, 0.8)), (M_CHO, (0.85, 0.22, 0.03))):
    m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1); b.inputs["Roughness"].default_value = 0.7; b.inputs["Sheen Weight"].default_value = 0.3
    trl = nt.nodes.new("ShaderNodeBsdfTranslucent"); trl.inputs["Color"].default_value = (*col, 1)
    mx = nt.nodes.new("ShaderNodeMixShader"); mx.inputs[0].default_value = 0.35
    out = nt.nodes["Material Output"]
    nt.links.new(b.outputs[0], mx.inputs[1]); nt.links.new(trl.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], out.inputs["Surface"])
    add_haze(m)
CH_R = 17.5; NG = 24; LINES_L = 26.0
CHUTE = bpy.data.objects.new("chute", None); coll.objects.link(CHUTE)
def chute_mesh(infl=1.0):
    bm = bmesh.new(); n = NG*4; rings = []
    for j in range(13):
        u = j/12.0                      # 0 = apex vent, 1 = skirt
        th = lerp(0.12, 1.25, u)
        r = CH_R*math.sin(th)*lerp(1.0, 0.92, u)
        z = CH_R*0.62*math.cos(th)*infl
        ring = []
        for k in range(n):
            a = 2*math.pi*k/n
            scal = 1.0 - 0.035*(1 - math.cos(2*math.pi*(k % 4)/4))*u     # scalloped gores
            ring.append(bm.verts.new((r*scal*math.cos(a), r*scal*math.sin(a), z)))
        rings.append(ring)
    for j in range(12):
        for k in range(n):
            f = bm.faces.new([rings[j][k], rings[j][(k+1) % n], rings[j+1][(k+1) % n], rings[j+1][k]])
            f.material_index = (k//4) % 2
    me = bpy.data.meshes.new("canopy"); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    return me
canopy_me = chute_mesh()
canopy_me.materials.append(M_CHW); canopy_me.materials.append(M_CHO)
CANOPY = bpy.data.objects.new("canopy", canopy_me); coll.objects.link(CANOPY); CANOPY.parent = CHUTE
SKIRT = [Vector((CH_R*math.sin(1.25)*0.92*math.cos(2*math.pi*k/NG), CH_R*math.sin(1.25)*0.92*math.sin(2*math.pi*k/NG), CH_R*0.62*math.cos(1.25))) for k in range(NG)]
M_LINE = principled("line", (0.75, 0.72, 0.66), 0.7)
LINES = bpy.data.objects.new("lines", bpy.data.meshes.new("lines")); coll.objects.link(LINES); LINES.data.materials.append(M_LINE)
def tube(bm, p, q, r):
    d = q - p; L = d.length
    if L < 1e-4: return
    z = d.normalized(); x = z.cross(Vector((0, 0, 1)) if abs(z.z) < 0.9 else Vector((1, 0, 0))).normalized(); y = z.cross(x)
    a0 = [bm.verts.new(p + (x*math.cos(2*math.pi*k/4) + y*math.sin(2*math.pi*k/4))*r) for k in range(4)]
    a1 = [bm.verts.new(q + (x*math.cos(2*math.pi*k/4) + y*math.sin(2*math.pi*k/4))*r) for k in range(4)]
    for k in range(4): bm.faces.new([a0[k], a0[(k+1) % 4], a1[(k+1) % 4], a1[k]])

# ------------------------------------------------------------------ dust cloud puffs + grass fire
def puff_mat(name, col, glow=False):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    tc = nt.nodes.new("ShaderNodeTexCoord")
    dif = nt.nodes.new("ShaderNodeBsdfDiffuse"); dif.inputs["Color"].default_value = (*col, 1)
    trl = nt.nodes.new("ShaderNodeBsdfTranslucent"); trl.inputs["Color"].default_value = (col[0]*1.1, col[1], col[2]*0.9, 1)
    m1 = nt.nodes.new("ShaderNodeMixShader"); m1.inputs[0].default_value = 0.65
    nt.links.new(dif.outputs[0], m1.inputs[1]); nt.links.new(trl.outputs[0], m1.inputs[2])
    amb = nt.nodes.new("ShaderNodeEmission"); amb.inputs["Color"].default_value = (col[0], col[1]*0.95, col[2]*0.9, 1); amb.inputs["Strength"].default_value = 0.35
    add0 = nt.nodes.new("ShaderNodeAddShader"); nt.links.new(m1.outputs[0], add0.inputs[0]); nt.links.new(amb.outputs[0], add0.inputs[1])
    emi = nt.nodes.new("ShaderNodeEmission"); emi.inputs["Color"].default_value = (1.0, 0.55, 0.25, 1); emi.inputs["Strength"].default_value = 0.0
    add = nt.nodes.new("ShaderNodeAddShader"); nt.links.new(add0.outputs[0], add.inputs[0]); nt.links.new(emi.outputs[0], add.inputs[1])
    lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.5
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 2.5; nz.inputs["Detail"].default_value = 5
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    ad = nt.nodes.new("ShaderNodeMath"); ad.operation = 'ADD'
    nt.links.new(lw.outputs["Facing"], ad.inputs[0]); nt.links.new(nz.outputs["Fac"], ad.inputs[1])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[1].default_value = 0.65; mr.inputs[2].default_value = 1.5
    nt.links.new(ad.outputs[0], mr.inputs[0])
    op = nt.nodes.new("ShaderNodeMath"); op.operation = 'MAXIMUM'; op.inputs[1].default_value = 0.0
    nt.links.new(mr.outputs[0], op.inputs[0])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    m2 = nt.nodes.new("ShaderNodeMixShader"); nt.links.new(op.outputs[0], m2.inputs[0])
    nt.links.new(add.outputs[0], m2.inputs[1]); nt.links.new(tr.outputs[0], m2.inputs[2])
    nt.links.new(m2.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    return m, emi.inputs["Strength"], op.inputs[1]
def vol_mat(name, col, scale):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    pv = nt.nodes.new("ShaderNodeVolumePrincipled"); pv.inputs["Color"].default_value = (*col, 1); pv.inputs["Anisotropy"].default_value = 0.55
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = 5
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    gr = nt.nodes.new("ShaderNodeTexGradient"); gr.gradient_type = 'SPHERICAL'; nt.links.new(tc.outputs["Object"], gr.inputs["Vector"])
    mm = nt.nodes.new("ShaderNodeMath"); mm.operation = 'MULTIPLY'; nt.links.new(nz.outputs["Fac"], mm.inputs[0]); nt.links.new(gr.outputs["Fac"], mm.inputs[1])
    pw = nt.nodes.new("ShaderNodeMath"); pw.operation = 'POWER'; pw.inputs[1].default_value = 1.2; nt.links.new(mm.outputs[0], pw.inputs[0])
    dens = nt.nodes.new("ShaderNodeMath"); dens.operation = 'MULTIPLY'; dens.inputs[1].default_value = 0.0
    nt.links.new(pw.outputs[0], dens.inputs[0]); nt.links.new(dens.outputs[0], pv.inputs["Density"])
    em = nt.nodes.new("ShaderNodeMath"); em.operation = 'MULTIPLY'; em.inputs[1].default_value = 0.0
    nt.links.new(pw.outputs[0], em.inputs[0]); nt.links.new(em.outputs[0], pv.inputs["Emission Strength"])
    pv.inputs["Emission Color"].default_value = (1.0, 0.6, 0.3, 1)
    nt.links.new(pv.outputs[0], nt.nodes["Material Output"].inputs["Volume"])
    return m, em.inputs[1], dens.inputs[1]
M_DUST, DUST_GLOW, DUST_FADE = puff_mat("dust", (0.80, 0.66, 0.50))
M_SMOKE, _, SMOKE_FADE = puff_mat("smoke", (0.45, 0.43, 0.42))
bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
for v in bm.verts: v.co *= 1 + 0.18*noise.noise(v.co*1.7)
puff_me = bpy.data.meshes.new("puff"); bm.to_mesh(puff_me); bm.free()
for p in puff_me.polygons: p.use_smooth = True
PUFFS = []
pr = random.Random(7)
for k in range(70):
    o = bpy.data.objects.new(f"puff{k}", puff_me.copy()); coll.objects.link(o); o.data.materials.append(M_DUST)
    PUFFS.append({"ob": o, "a": pr.uniform(0, 6.283), "sp": pr.uniform(0.5, 1.0), "f": pr.uniform(0.5, 1.0), "dz": pr.uniform(0.0, 0.7), "lag": pr.uniform(0, 0.12)})
SMOKES = []
for k in range(10):
    o = bpy.data.objects.new(f"smoke{k}", puff_me.copy()); coll.objects.link(o); o.data.materials.append(M_SMOKE)
    SMOKES.append({"ob": o, "ph": pr.random(), "x": pr.uniform(-1, 1)})
# little grass fires (show in shot D)
M_FIRE = bpy.data.materials.new("fire"); M_FIRE.use_nodes = True; nt = M_FIRE.node_tree
nt.nodes.remove(nt.nodes["Principled BSDF"])
emf = nt.nodes.new("ShaderNodeEmission"); emf.inputs["Color"].default_value = (1.0, 0.45, 0.12, 1); FIRE_E = emf.inputs["Strength"]; FIRE_E.default_value = 0
nt.links.new(emf.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
FIRES = []
FIRE_SPOTS = [(2.6, -1.2), (3.1, -0.4), (2.2, -2.0), (-2.4, 1.9), (-1.6, 2.6), (3.4, 0.6)]
for k, (fx, fy) in enumerate(FIRE_SPOTS):
    for j in range(5):
        bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=0.08, radius2=0.0, depth=0.4, location=(fx + pr.uniform(-0.25, 0.25), fy + pr.uniform(-0.25, 0.25), ground_h(fx, fy) + 0.15))
        o = bpy.context.object; o.data.materials.append(M_FIRE); FIRES.append((o, pr.random()*6.28, o.location.copy()))
fire_d = bpy.data.lights.new("fire", 'POINT'); fire_d.color = (1.0, 0.5, 0.2); fire_d.energy = 0; fire_d.shadow_soft_size = 0.5
FIREL = bpy.data.objects.new("firel", fire_d); coll.objects.link(FIREL); FIREL.location = (2.8, -0.8, 0.6)

# ------------------------------------------------------------------ sky + sun
wo = bpy.data.worlds.new("w"); sc.world = wo; wo.use_nodes = True
bg = wo.node_tree.nodes["Background"]
sky = wo.node_tree.nodes.new("ShaderNodeTexSky"); sky.sky_type = 'MULTIPLE_SCATTERING'
wo.node_tree.links.new(sky.outputs[0], bg.inputs[0])
sky.altitude = 0; sky.aerosol_density = 1.8; sky.sun_intensity = 0.5
sun_d = bpy.data.lights.new("sun", 'SUN'); sun_d.angle = math.radians(0.6)
sun = bpy.data.objects.new("sun", sun_d); coll.objects.link(sun)
SUNROT = float(os.environ.get("SUNROT", "45")); SUNEL = float(os.environ.get("SUNEL", "6"))
sky.sun_elevation = math.radians(SUNEL); sky.sun_rotation = math.radians(SUNROT)
sun.rotation_euler = Euler((math.radians(90 - SUNEL), 0, math.radians(SUNROT + 90)))
sun_d.energy = 3.6; sun_d.color = (1.0, 0.66, 0.40); bg.inputs[1].default_value = 0.15

# ------------------------------------------------------------------ motion
WIND = Vector((0.9, 0.35, 0.0))          # gentle drift (m/s)
def cap_z(t):
    if t < T_FIRE: return 0.8 + V_DESC*(T_FIRE - t)
    if t < T_TOUCH:
        u = (t - T_FIRE)/(T_TOUCH - T_FIRE)
        return 0.8*(1 - (u*0.9 + 0.1*u*u))
    return 0.0
def drift(t):
    tt = min(t, T_TOUCH)
    return WIND*(tt - T_TOUCH)
def place(t, frame=None):
    d = drift(t)
    sway = 0.04*math.sin(t*0.9) if t < T_TOUCH else 0.0
    CAP.location = (d.x, d.y, ground_h(d.x, d.y) + cap_z(t))
    CAP.rotation_euler = (sway, 0.03*math.cos(t*0.7) if t < T_TOUCH else 0.0, 0.4 + 0.05*t if t < T_TOUCH else 0.4 + 0.05*T_TOUCH)
    if frame is not None:
        CAP.keyframe_insert("location", frame=frame)
        CAP.location = (drift(t + 1/FPS).x, drift(t + 1/FPS).y, ground_h(d.x, d.y) + cap_z(t + 1/FPS)); CAP.keyframe_insert("location", frame=frame + 1)
        CAP.location = (d.x, d.y, ground_h(d.x, d.y) + cap_z(t))
    # chute: above the capsule while descending; afterwards drifts downwind, sinks and deflates
    top = Vector(CAP.location) + Vector((0, 0, 2.15))
    if t < T_TOUCH:
        c = top + Vector((0.6*math.sin(t*0.5), 0.4*math.cos(t*0.6), LINES_L + 10.0)); infl = 1.0 + 0.03*math.sin(t*2.1)
        tilt = (0.05*math.sin(t*0.5), 0.05*math.cos(t*0.6))
    else:
        u = t - T_TOUCH; k = ease(u/7.0)
        c = top + Vector((lerp(0.6*math.sin(T_TOUCH*0.5), 30, k), lerp(0, 12, k), lerp(LINES_L + 10.0, 3.0, ease(u/7.0))))
        infl = lerp(1.0, 0.25, ease(u/6.0)); tilt = (0.0, lerp(0, 0.25, k))
    CHUTE.location = c; CHUTE.rotation_euler = (tilt[0], tilt[1], 0.2*t)
    CANOPY.scale = (1.0 + 0.1*(1 - infl), 1.0 + 0.1*(1 - infl), infl)
    bpy.context.view_layer.update()
    # suspension lines: skirt -> confluence -> riser -> capsule top
    mw = CANOPY.matrix_world
    conf = top + (c - top)*0.28
    bm = bmesh.new()
    for p in SKIRT: tube(bm, mw @ p, conf, 0.012 if SHOT in ("C", "D") else 0.025)
    tube(bm, conf, top, 0.03)
    me = LINES.data; me.clear_geometry(); bm.to_mesh(me); bm.free()
    # flash
    u = t - T_FIRE
    k = clamp(u/0.02)*(1 - clamp((u - 0.16)/0.1)) if u > 0 else 0.0
    JET_E.default_value = 260.0*k
    for o in JETS: o.hide_render = k <= 0.01; o.scale = (1, 1, 0.6 + 0.6*k)
    FLASH.location = (CAP.location.x, CAP.location.y, max(0.15, CAP.location.z - 0.3)); fl_d.energy = 90000*k
    DUST_GLOW.default_value = 5.0*clamp(1 - (u - 0.05)/0.35) if u > 0 else 0.0
    SCORCH.inputs[1].default_value = 0.85*clamp(u/0.3) if u > 0 else 0.0
    # dust puffs
    for p in PUFFS:
        ob = p["ob"]; v = u - p["lag"]
        if v <= 0 or SHOT == "D": ob.hide_render = True; continue
        ob.hide_render = False
        reach = 6.5*p["sp"]*(1 - math.exp(-v/0.6)) + 0.3*v
        r = (0.6 + 2.0*p["f"]*(1 - math.exp(-v/0.9)))*(1 + 0.1*v)
        x = CAP.location.x + (1.0 + reach)*math.cos(p["a"]) + WIND.x*0.6*v
        y = CAP.location.y + (1.0 + reach)*math.sin(p["a"]) + WIND.y*0.6*v
        ob.location = (x, y, ground_h(x, y) + r*0.35 + p["dz"]*r*1.4 + 0.25*v)
        ob.scale = (r*1.4, r*1.4, r*0.9)
    DUST_FADE.default_value = (0.9 + 0.1*clamp((u - 4.0)/3.0)) if SHOT == "D" else min(0.97, 0.25 + clamp((u - 2.5)/8.0)*0.65 + clamp((u - 3.6)/1.8)*0.6) if u > 0 else 0.0
    # grass fires + smoke in shot D
    fk = clamp((t - 25.0)/1.5)
    FIRE_E.default_value = 14.0*fk; fire_d.energy = 120*fk*(0.85 + 0.15*math.sin(t*23))
    for o, ph, base in FIRES:
        o.hide_render = fk <= 0
        s = 0.7 + 0.5*abs(math.sin(t*9 + ph)) + 0.3*abs(math.sin(t*17 + 2*ph))
        o.scale = (1, 1, s); o.location = (base.x, base.y, base.z + 0.2*(s - 1))
    for s_ in SMOKES:
        ob = s_["ob"]; ph = (t*0.12 + s_["ph"]) % 1.0
        ob.hide_render = True
        fx, fy = FIRE_SPOTS[int(s_["ph"]*6) % 6]
        r = 0.3 + 1.4*ph
        ob.location = (fx + WIND.x*4*ph + s_["x"]*0.3, fy + WIND.y*4*ph, ground_h(fx, fy) + 0.5 + 5*ph); ob.scale = (r, r, r*0.8)
    SMOKE_FADE.default_value = 0.8 + 0.2*(1 - fk)

# ------------------------------------------------------------------ camera
cam_d = bpy.data.cameras.new("cam"); cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 36; cam_d.clip_end = 30000; cam_d.clip_start = 0.05
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
    cl = Vector(CAP.location)
    if SHOT == "A":
        # wide telephoto from the ground: chute + capsule against the warm sky
        k = ease(t/8.8); cam_d.lens = lerp(125, 135, k)
        aim(Vector((-620, -790, 2.5)), Vector((cl.x, cl.y, cl.z*0.62 + 8)), t, math.radians(0.02))
        cam_d.dof.use_dof = False
    elif SHOT == "B":
        # from a recovery helicopter, slightly above, tracking the descent
        k = ease((t - 8.8)/8.8); cam_d.lens = lerp(55, 62, k)
        loc = cl + Vector((lerp(-34, -30, k), lerp(-38, -33, k), lerp(4, 3, k)))
        aim(loc, cl + Vector((0, 0, lerp(6.0, 8.0, k))), t, math.radians(0.07), rate=2.2)
        cam_d.dof.use_dof = False
    elif SHOT == "C":
        # ground camera, low, telephoto
        k = ease((t - 17.6)/8.1); cam_d.lens = lerp(62, 70, k)
        loc = Vector((-26, -40, 1.1))
        tz = max(1.2, cl.z*0.55 + 1.0)
        tz = lerp(tz, 1.6, ease((t - 21.0)/1.2))
        tgt = Vector((cl.x, cl.y, tz))
        aim(loc, tgt, t, math.radians(0.03 + 0.25*clamp(1 - abs(t - T_TOUCH - 0.2)/0.5)), rate=1.6 + 6*clamp(1 - abs(t - T_TOUCH - 0.2)/0.5))
        cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = 5.6; cam_d.dof.focus_distance = (tgt - loc).length
    else:
        k = ease((t - 25.7)/7.8); cam_d.lens = lerp(38, 42, k)
        loc = cl + Vector((lerp(-6, -5, k), lerp(-20, -18, k), lerp(2.6, 2.3, k)))
        aim(loc, cl + Vector((2.0, 0.0, 1.0)), t, math.radians(0.04))
        cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = 8; cam_d.dof.focus_distance = (cl - loc).length

# ------------------------------------------------------------------ render
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.cycles.samples = int(os.environ.get("SPP", "10")); sc.cycles.use_denoising = True; sc.cycles.use_adaptive_sampling = True
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transparent_max_bounces = 8
sc.cycles.volume_bounces = 0; sc.cycles.volume_step_rate = 6.0; sc.cycles.volume_max_steps = 32
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.resolution_percentage = int(os.environ.get("PCT", "50"))
sc.render.use_persistent_data = True
sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5; sc.render.motion_blur_position = 'START'
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
sc.view_settings.exposure = float(os.environ.get("EXPO", "-0.55"))

def screen(p):
    v = world_to_camera_view(sc, cam, Vector(p)); return (v.x*RES[0], (1-v.y)*RES[1], v.z)
def shot_for(t):
    for k, (a, b) in SHOTS.items():
        if a <= t < b: return k
    return "D"
END = SHOTS["D"][1]
def setup(t, frame=None):
    global SHOT
    SHOT = shot_for(t)
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
        c = Vector(CAP.location)
        meta[i] = {"cap": screen(c + Vector((0, 0, 1.1))), "chute": screen(Vector(CHUTE.location) + Vector((0, 0, 5))),
                   "bottom": screen(c + Vector((0, 0, -0.3))), "fire": screen((2.8, -1.0, 0.4)), "alt": cap_z(t)}
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
