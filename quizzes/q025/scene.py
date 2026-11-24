import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import bpy, bmesh, math, json, sys, os, random
from mathutils import Vector, Euler, Matrix, noise
from bpy_extras.object_utils import world_to_camera_view

FPS = 30
RES = (1080, 1920)
OUT = os.environ.get("OUT", QDIR)
SHOT = "A"
SHOTS = {"A": (0.0, 7.4), "B": (7.4, 14.9), "C": (14.9, 23.5), "D": (23.5, 31.5)}
if "frames" in sys.argv:
    _st = int(os.environ.get("STEP", "2")); _a = int(os.environ.get("IFROM", "0")); _b = int(os.environ.get("ITO", int(31.5*FPS)))
    if all(os.path.exists(f"{OUT}/frames/f{i:04d}.png") for i in range(_a, _b, _st)): sys.exit(0)

def ease(x):
    x = max(0.0, min(1.0, x)); return x*x*(3-2*x)
def lerp(a, b, k): return a + (b-a)*k
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; coll = sc.collection
rnd = random.Random(25)
bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'

HAZE = (1.0, 0.72, 0.50)
def add_haze(m, dist=1500.0, amt=0.85, col=HAZE, strength=0.5):
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
def box(name, x0, x1, y0, y1, z0, z1, mat, parent=None, bev=0.03, seg=2):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(x1-x0, y1-y0, z1-z0), verts=bm.verts)
    bmesh.ops.translate(bm, vec=((x0+x1)/2, (y0+y1)/2, (z0+z1)/2), verts=bm.verts)
    if bev > 0:
        bmesh.ops.bevel(bm, geom=bm.edges[:]+bm.verts[:], offset=bev, segments=seg, affect='EDGES', profile=0.5)
    return mesh_obj(name, bm, mat, smooth=bev > 0, parent=parent)
def cyl(name, loc, r, depth, axis, mat, parent=None, verts=24):
    rot = {"x": (0, math.pi/2, 0), "y": (math.pi/2, 0, 0), "z": (0, 0, 0)}[axis]
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name; o.data.materials.append(mat)
    for p in o.data.polygons: p.use_smooth = True
    if parent: o.parent = parent
    return o
def axis(a, b, da, ia, ib, db):
    out = []; v = a
    while v < b:
        out.append(v); v += da if (v < ia or v > ib) else db
    return out

# ------------------------------------------------------------------ track geometry (along x)
ZT = 0.0                 # top of the sleepers
GAUGE = 1.435
RAIL_Y = (-(GAUGE/2 + 0.035), GAUGE/2 + 0.035)
XA, XB = -1400.0, 1400.0
def ground_h(x, y):
    d = abs(y)
    h = -0.75
    k = clamp((d - 5.2)/6)
    h += -0.25*ease(k) + 0.25*ease(clamp((d - 14)/10))
    h += 1.6*noise.fractal(Vector((x/160, y/160, 0.3)), 0.6, 2.0, 4)*clamp((d - 8)/30)
    h += 30*max(0.0, noise.fractal(Vector((x/900, y/900, 2.0)), 0.5, 2.0, 4) + 0.1)*clamp((d - 250)/500)
    return h
def ballast_h(y):
    d = abs(y)
    if d < 1.75: return ZT - 0.02
    return ZT - 0.02 - (d - 1.75)/1.5          # 1:1.5 shoulder down to the ground
# ground
XS = axis(-3000, 3000, 40, -400, 400, 4.0)
YS = axis(-2500, 2500, 40, -60, 60, 0.6)
bm = bmesh.new(); vs = []
for y in YS: vs.append([bm.verts.new((x, y, max(ground_h(x, y), ballast_h(y) - 0.04) if abs(y) < 5 else ground_h(x, y))) for x in XS])
for j in range(len(YS) - 1):
    for i in range(len(XS) - 1):
        bm.faces.new([vs[j][i], vs[j][i+1], vs[j+1][i+1], vs[j+1][i]])
def grass_mat():
    m = bpy.data.materials.new("grass"); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.9
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.02; nz.inputs["Detail"].default_value = 10
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    cr = nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (0.03, 0.05, 0.012, 1); cr.color_ramp.elements[1].color = (0.13, 0.11, 0.035, 1)
    cr.color_ramp.elements[0].position = 0.35; cr.color_ramp.elements[1].position = 0.7
    nt.links.new(nz.outputs["Fac"], cr.inputs[0]); nt.links.new(cr.outputs[0], b.inputs["Base Color"])
    nz2 = nt.nodes.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = 40; nz2.inputs["Detail"].default_value = 4
    nt.links.new(tc.outputs["Object"], nz2.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.5
    nt.links.new(nz2.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs[0], b.inputs["Normal"])
    return add_haze(m)
mesh_obj("ground", bm, grass_mat())

# ballast bed mesh (shader detail) + instanced stones near the cameras
def ballast_mat(scale=30.0):
    m = bpy.data.materials.new("ballast"); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.45
    tc = nt.nodes.new("ShaderNodeTexCoord")
    vo = nt.nodes.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = scale; vo.feature = 'F1'
    nt.links.new(tc.outputs["Object"], vo.inputs["Vector"])
    vo2 = nt.nodes.new("ShaderNodeTexVoronoi"); vo2.inputs["Scale"].default_value = scale; vo2.feature = 'DISTANCE_TO_EDGE'
    nt.links.new(tc.outputs["Object"], vo2.inputs["Vector"])
    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (0.10, 0.10, 0.10, 1); cr.color_ramp.elements[1].color = (0.36, 0.34, 0.31, 1)
    nt.links.new(vo.outputs["Color"], cr.inputs[0])
    sh = nt.nodes.new("ShaderNodeMapRange"); sh.inputs[1].default_value = 0.0; sh.inputs[2].default_value = 0.15; sh.inputs[3].default_value = 0.55; sh.inputs[4].default_value = 1.0
    nt.links.new(vo2.outputs["Distance"], sh.inputs[0])
    mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs[0].default_value = 1.0
    nt.links.new(cr.outputs[0], mul.inputs[6]); nt.links.new(sh.outputs[0], mul.inputs[7])
    nt.links.new(mul.outputs[2], b.inputs["Base Color"])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 1.0; bp.inputs["Distance"].default_value = 0.03
    nt.links.new(sh.outputs[0], bp.inputs["Height"]); nt.links.new(bp.outputs[0], b.inputs["Normal"])
    return add_haze(m)
M_BAL = ballast_mat()
bm = bmesh.new(); prev = None
YB = [-4.6, -3.2, -1.75, -0.6, 0.6, 1.75, 3.2, 4.6]
for x in axis(XA, XB + 1, 4.0, -200, 200, 0.5):
    ring = [bm.verts.new((x, y, ballast_h(y) + 0.02*noise.noise(Vector((x*0.7, y*0.7, 3.0))))) for y in YB]
    if prev:
        for i in range(len(YB) - 1): bm.faces.new([prev[i], prev[i+1], ring[i+1], ring[i]])
    prev = ring
mesh_obj("ballastbed", bm, M_BAL, smooth=False)

# stone meshes: irregular, angular (crushed)
STONE_COLS = ((0.30, 0.29, 0.27), (0.22, 0.21, 0.20), (0.40, 0.38, 0.35), (0.26, 0.24, 0.22), (0.34, 0.31, 0.27))
def stone_mat(name, col):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.38
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 60; nz.inputs["Detail"].default_value = 8
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    # per-instance colour variation
    oi = nt.nodes.new("ShaderNodeObjectInfo")
    mx0 = nt.nodes.new("ShaderNodeMath"); mx0.operation = 'MULTIPLY'; mx0.inputs[1].default_value = 0.6
    nt.links.new(oi.outputs["Random"], mx0.inputs[0])
    ad = nt.nodes.new("ShaderNodeMath"); ad.operation = 'ADD'; ad.inputs[1].default_value = 0.7; nt.links.new(mx0.outputs[0], ad.inputs[0])
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.inputs[6].default_value = (*col, 1)
    mx.inputs[7].default_value = (col[0]*0.7, col[1]*0.68, col[2]*0.66, 1)
    nt.links.new(nz.outputs["Fac"], mx.inputs[0])
    mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs[0].default_value = 1.0
    nt.links.new(mx.outputs[2], mul.inputs[6])
    cmb = nt.nodes.new("ShaderNodeCombineXYZ"); nt.links.new(ad.outputs[0], cmb.inputs[0]); nt.links.new(ad.outputs[0], cmb.inputs[1]); nt.links.new(ad.outputs[0], cmb.inputs[2])
    nt.links.new(cmb.outputs[0], mul.inputs[7])
    nt.links.new(mul.outputs[2], b.inputs["Base Color"])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.35
    nt.links.new(nz.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs[0], b.inputs["Normal"])
    return add_haze(m)
stone_coll = bpy.data.collections.new("stones"); sc.collection.children.link(stone_coll); stone_coll.instance_offset = (0, 0, -500)
for k in range(10):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
    r2 = random.Random(k)
    # crushed look: cut with random planes
    for _ in range(5):
        n = Vector((r2.uniform(-1, 1), r2.uniform(-1, 1), r2.uniform(-1, 1))).normalized()
        d = r2.uniform(0.45, 0.8)
        for v in bm.verts:
            s = v.co.dot(n)
            if s > d: v.co -= n*(s - d)
    bmesh.ops.scale(bm, vec=(r2.uniform(0.8, 1.2), r2.uniform(0.7, 1.0), r2.uniform(0.5, 0.75)), verts=bm.verts)
    me = bpy.data.meshes.new(f"st{k}"); bm.to_mesh(me); bm.free()
    me.materials.append(stone_mat(f"stm{k}", STONE_COLS[k % 5]))
    o = bpy.data.objects.new(f"st{k}", me); stone_coll.objects.link(o); o.location = (0, 0, -500)
NSTONE = int(os.environ.get("NSTONE", "380000"))
def stone_patch(name, xa, xb, count):
    bm = bmesh.new(); prev = None
    for x in axis(xa, xb + 0.01, 0.5, -1e9, 1e9, 0.5):
        ring = [bm.verts.new((x, y, ballast_h(y) - 0.005)) for y in (-4.4, -3.2, -1.75, -0.6, 0.6, 1.75, 3.2, 4.4)]
        if prev:
            for i in range(7): bm.faces.new([prev[i], prev[i+1], ring[i+1], ring[i]])
        prev = ring
    o = mesh_obj(name, bm, M_BAL, smooth=False)
    ps = o.modifiers.new("ps", 'PARTICLE_SYSTEM').particle_system
    st = ps.settings; st.type = 'HAIR'; st.count = count; st.hair_length = 1.0
    st.render_type = 'COLLECTION'; st.instance_collection = stone_coll; st.use_collection_pick_random = True
    st.particle_size = 0.042; st.size_random = 0.5
    st.use_rotations = True; st.rotation_mode = 'NONE'; st.rotation_factor_random = 1.0; st.phase_factor_random = 2.0
    st.emit_from = 'FACE'; st.use_emit_random = True; st.distribution = 'RAND'; ps.seed = 7 if name == "patchA" else 13
    st.use_advanced_hair = True
    return o
stone_patch("patchA", -40, 30, int(NSTONE*0.75))

# sleepers + rails + fastenings
M_CONC = principled("concrete", (0.26, 0.25, 0.24), 0.5)
M_RAILS = principled("railside", (0.075, 0.042, 0.028), 0.7, 0.3)
M_RAILTOP = principled("railtop", (0.78, 0.77, 0.75), 0.05, 1.0)
M_CLIP = principled("clip", (0.10, 0.10, 0.10), 0.5, 0.6)
bm = bmesh.new(); bm2 = bmesh.new()
x = XA
while x < XB:
    near = -220 < x < 220
    g = bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(0.28, 2.6, 0.2), verts=g["verts"])
    bmesh.ops.translate(bm, vec=(x, 0, ZT - 0.1), verts=g["verts"])
    if near:
        for y in RAIL_Y:
            for s in (-1, 1):
                g2 = bmesh.ops.create_cube(bm2, size=1.0)
                bmesh.ops.scale(bm2, vec=(0.08, 0.10, 0.06), verts=g2["verts"])
                bmesh.ops.translate(bm2, vec=(x, y + s*0.11, ZT + 0.04), verts=g2["verts"])
    x += 0.6
mesh_obj("sleepers", bm, M_CONC, smooth=False)
mesh_obj("clips", bm2, M_CLIP, smooth=False)
def rail(y):
    prof = [(-0.075, 0.0), (0.075, 0.0), (0.075, 0.012), (0.012, 0.03), (0.010, 0.13), (0.036, 0.14), (0.036, 0.172), (-0.036, 0.172), (-0.036, 0.14), (-0.010, 0.13), (-0.012, 0.03), (-0.075, 0.012)]
    bm = bmesh.new(); rings = []
    for x in axis(XA, XB + 1, 10.0, -300, 300, 2.0):
        rings.append([bm.verts.new((x, y + py, ZT + pz)) for (py, pz) in prof])
    n = len(prof)
    for a, b_ in zip(rings[:-1], rings[1:]):
        for i in range(n):
            f = bm.faces.new([a[i], a[(i+1) % n], b_[(i+1) % n], b_[i]])
            f.material_index = 1 if i in (6,) else 0
    me = bpy.data.meshes.new("rail"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("rail", me); coll.objects.link(o); me.materials.append(M_RAILS); me.materials.append(M_RAILTOP)
    return o
for y in RAIL_Y: rail(y)

# telegraph poles, trees in the fields
M_WOOD = principled("wood", (0.10, 0.07, 0.05), 0.85)
for k in range(-30, 31):
    x = k*45.0 + 12
    cyl(f"pole{k}", (x, -7.5, ground_h(x, -7.5) + 4.0), 0.12, 8.5, "z", M_WOOD, verts=10)
    box(f"arm{k}", x - 0.06, x + 0.06, -8.4, -6.6, ground_h(x, -7.5) + 7.6, ground_h(x, -7.5) + 7.75, M_WOOD, bev=0)
M_LEAF = principled("leaf", (0.035, 0.05, 0.015), 0.85)
bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=4.0)
for v in bm.verts: v.co *= 1 + 0.25*noise.noise(v.co*0.6)
bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, 5.0))
leaf_me = bpy.data.meshes.new("leaf"); bm.to_mesh(leaf_me); bm.free(); leaf_me.materials.append(M_LEAF)
for k in range(int(os.environ.get("NTREES", "2500"))):
    # hedgerows / tree lines along field edges + scattered
    if k % 3 == 0:
        x = rnd.uniform(-2000, 2000); y = rnd.choice((-1, 1))*rnd.choice((60, 140, 260, 420)) + rnd.uniform(-4, 4)
    else:
        x = rnd.choice((-1, 1))*rnd.choice((90.0, 310.0, 700.0)) + rnd.uniform(-5, 5) + rnd.choice((0, 400, -400)); y = rnd.uniform(-1500, 1500)
    if abs(y) < 25: continue
    o = bpy.data.objects.new(f"tr{k}", leaf_me); coll.objects.link(o)
    s = rnd.uniform(0.7, 1.5)
    o.location = (x, y, ground_h(x, y) - 0.5); o.scale = (s, s, s*rnd.uniform(0.8, 1.3)); o.rotation_euler.z = rnd.uniform(0, 6.3)

# ------------------------------------------------------------------ freight train
M_LOCO = principled("loco", (0.55, 0.30, 0.03), 0.35, 0.2, coat=0.6)
M_LOCO2 = principled("loco2", (0.03, 0.04, 0.06), 0.4, 0.2, coat=0.4)
M_STEEL = principled("steel", (0.06, 0.06, 0.06), 0.55, 0.6)
M_GLASS = principled("glass", (0.01, 0.012, 0.015), 0.04, coat=1.0)
M_HEAD = principled("head", (1, 0.95, 0.85), 0.2, emit=((1.0, 0.9, 0.75), 60.0))
M_WHEEL = principled("wheel", (0.14, 0.10, 0.08), 0.45, 0.8)
M_HOLE = principled("hole", (0.005, 0.005, 0.005), 0.9)
M_MARK = principled("mark", (0.85, 0.85, 0.8), 0.5)
CONT_COLS = [(0.08, 0.20, 0.38), (0.45, 0.06, 0.04), (0.12, 0.28, 0.12), (0.45, 0.40, 0.35), (0.50, 0.25, 0.05), (0.08, 0.20, 0.38), (0.30, 0.30, 0.32), (0.45, 0.06, 0.04)]
CARS = []
WHEELS = []
def bogie(name, x, parent):
    box(name, x - 1.6, x + 1.6, -1.1, 1.1, 0.55, 0.95, M_STEEL, parent, 0.03)
    for ax in (x - 1.0, x + 1.0):
        for y in (-GAUGE/2 - 0.03, GAUGE/2 + 0.03):
            e = bpy.data.objects.new(name + f"w{ax}{y}", None); coll.objects.link(e); e.parent = parent; e.location = (ax, y, ZT + 0.172 + 0.46)
            cyl(name + f"wh{ax}{y}", (0, 0, 0), 0.46, 0.13, "y", M_WHEEL, e, 48)
            sg = 1 if y > 0 else -1
            cyl(name + f"fl{ax}{y}", (0, -sg*0.075, 0), 0.49, 0.025, "y", M_WHEEL, e, 48)
            cyl(name + f"hub{ax}{y}", (0, sg*0.07, 0), 0.13, 0.05, "y", M_STEEL, e, 24)
            for h in range(6):
                a_ = h*math.pi/3
                cyl(name + f"ho{ax}{y}{h}", (0.27*math.cos(a_), sg*0.066, 0.27*math.sin(a_)), 0.055, 0.01, "y", M_HOLE, e, 16)
            box(name + f"mk{ax}{y}", -0.012, 0.012, sg*0.064 - 0.003, sg*0.064 + 0.003, 0.33, 0.44, M_MARK, e, 0)
            WHEELS.append(e)
def loco():
    P = bpy.data.objects.new("loco", None); coll.objects.link(P)
    L = 22.0
    box("ldeck", -L/2, L/2, -1.55, 1.55, 1.15, 1.45, M_LOCO2, P, 0.02)
    box("lhood", -L/2 + 0.4, L/2 - 4.2, -1.25, 1.25, 1.45, 4.3, M_LOCO, P, 0.06)
    box("lcab", L/2 - 4.2, L/2 - 0.6, -1.5, 1.5, 1.45, 4.6, M_LOCO, P, 0.08, 3)
    box("lnose", L/2 - 0.8, L/2 + 0.2, -1.4, 1.4, 1.45, 3.1, M_LOCO, P, 0.15, 3)
    box("lwind", L/2 - 0.63, L/2 - 0.55, -1.3, 1.3, 3.5, 4.3, M_GLASS, P, 0.01)
    for s in (-1, 1):
        box(f"lswin{s}", L/2 - 3.6, L/2 - 1.2, s*1.5 - 0.02, s*1.5 + 0.02, 3.4, 4.2, M_GLASS, P, 0)
        box(f"lhl{s}", L/2 + 0.15, L/2 + 0.25, s*0.6 - 0.15, s*0.6 + 0.15, 2.2, 2.45, M_HEAD, P, 0.02)
        box(f"lrail{s}", -L/2 + 0.5, L/2 - 1.0, s*1.52 - 0.02, s*1.52 + 0.02, 2.4, 2.45, principled(f"hr{s}", (0.9, 0.7, 0.1), 0.4), P, 0)
        box(f"lfuel{s}", -3.5, 3.5, s*0.9 - 0.5, s*0.9 + 0.5, 0.65, 1.15, M_LOCO2, P, 0.15)
        for k in range(14):
            box(f"lv{s}{k}", -L/2 + 1.5 + k*1.05, -L/2 + 1.9 + k*1.05, s*1.26 - 0.01, s*1.26 + 0.01, 2.0, 4.0, M_LOCO2, P, 0)
    box("lstripe", -L/2, L/2, -1.56, 1.56, 1.45, 1.6, M_LOCO2, P, 0)
    box("lpilot", L/2 + 0.1, L/2 + 0.6, -1.4, 1.4, 0.35, 1.2, M_LOCO2, P, 0.05)
    box("lroof", -L/2 + 2, -L/2 + 7, -0.9, 0.9, 4.3, 4.6, M_LOCO2, P, 0.05)
    bogie("lb1", L/2 - 4.5, P); bogie("lb2", -L/2 + 4.5, P)
    CARS.append((P, L))
def wagon(k):
    P = bpy.data.objects.new(f"car{k}", None); coll.objects.link(P)
    L = 18.0
    box(f"cdeck{k}", -L/2, L/2, -1.35, 1.35, 1.05, 1.3, M_STEEL, P, 0.02)
    col = CONT_COLS[k % len(CONT_COLS)]
    mc = principled(f"cont{k}", col, 0.55, 0.3)
    box(f"ct{k}", -6.1, 6.1, -1.22, 1.22, 1.3, 3.9, mc, P, 0.02)
    for j in range(40):
        box(f"cr{k}{j}", -6.0 + j*0.3, -5.9 + j*0.3, -1.25, 1.25, 1.35, 3.85, mc, P, 0)
    if k % 2 == 0:   # double-stack on every other car
        mc2 = principled(f"cont2{k}", CONT_COLS[(k + 3) % len(CONT_COLS)], 0.55, 0.3)
        box(f"ct2{k}", -6.1, 6.1, -1.22, 1.22, 3.92, 6.5, mc2, P, 0.02)
    bogie(f"cb1{k}", L/2 - 2.0, P); bogie(f"cb2{k}", -L/2 + 2.0, P)
    CARS.append((P, L))
loco()
NCARS = 8
for k in range(NCARS): wagon(k)
T_BITE = 21.6
def front_x(t):
    x = 0.022*max(0.0, t - 7.8)
    if t > T_BITE: x += 0.5*0.42*(t - T_BITE)**2
    return x
def wheel_w(t):
    v = 0.022 + (0.42*(t - T_BITE) if t > T_BITE else 0.0)
    roll = v/0.46 if t > 7.8 else 0.0
    spin = 13.0*clamp((t - 7.9)/1.0)*(1 - clamp((t - (T_BITE - 0.3))/0.6))
    return max(roll, spin) if t > 7.8 else 0.0
_ANG = [0.0]; _DT = 1/300.0
def wheel_ang(t):
    n = int(t/_DT)
    while len(_ANG) <= n + 1: _ANG.append(_ANG[-1] + wheel_w(len(_ANG)*_DT)*_DT)
    return _ANG[n]
def place_train(t, frame=None):
    x = front_x(t)
    for (P, L) in CARS:
        P.location = (x - L/2, 0, ZT)
        x -= L + 1.0
    if frame is None:
        for e in WHEELS: e.rotation_euler = (0, wheel_ang(t), 0)
    else:
        for e in WHEELS:
            e.rotation_euler = (0, wheel_ang(t), 0); e.keyframe_insert("rotation_euler", index=1, frame=frame)
            e.rotation_euler = (0, wheel_ang(t + 1/FPS), 0); e.keyframe_insert("rotation_euler", index=1, frame=frame + 1)
def axle_x(t): return front_x(t) - 3.5
TRAIN_LEN = sum(L + 1.0 for _, L in CARS)

# ------------------------------------------------------------------ sanding gear on the front axle (+y side, both front wheels)
LOCO = CARS[0][0]
AXL = 7.5                      # front axle, loco-local x
M_SAND = principled("sand", (0.50, 0.36, 0.19), 0.85)
M_SANDW = principled("sandwet", (0.30, 0.21, 0.12), 0.5)
M_PIPE = principled("pipe", (0.04, 0.04, 0.045), 0.5, 0.6)
JET_T0 = 17.5
NOZ = {}; TGT = {}
for sg in (1, -1):
    yy_ = sg*0.7525
    NOZ[sg] = Vector((AXL + 0.52, yy_, 0.32)); TGT[sg] = Vector((AXL + 0.24, yy_, 0.176))
    # vertical pipe from the bogie frame, then angled nozzle towards the wheel/rail contact
    top = Vector((AXL + 0.72, yy_, 1.0)); bend = Vector((AXL + 0.66, yy_, 0.46))
    for nm, a_, b_ in (("p1", top, bend), ("p2", bend, NOZ[sg])):
        d_ = b_ - a_; o = cyl(f"sp{nm}{sg}", (a_ + b_)/2, 0.022, d_.length + 0.02, "z", M_PIPE, LOCO, 16)
        o.rotation_euler = d_.to_track_quat('Z', 'Y').to_euler()
    cyl(f"spb{sg}", bend, 0.026, 0.06, "z", M_PIPE, LOCO, 16)
    o = cyl(f"spn{sg}", NOZ[sg], 0.03, 0.05, "z", M_PIPE, LOCO, 16)
    o.rotation_euler = (TGT[sg] - NOZ[sg]).to_track_quat('Z', 'Y').to_euler()
    box(f"sbox{sg}", AXL + 0.5, AXL + 1.05, yy_ - 0.22, yy_ + 0.22, 0.98, 1.15, M_PIPE, LOCO, 0.02)
# grains: one point cloud per side, instanced with a tiny chip
bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
gme = bpy.data.meshes.new("grain"); bm.to_mesh(gme); bm.free(); gme.materials.append(M_SAND)
JETS = []
grng = random.Random(5)
GR = [(grng.random(), grng.gauss(0, 1), grng.gauss(0, 1), grng.uniform(0.6, 1.4)) for _ in range(4200)]
SPL = [(grng.random(), grng.uniform(0, 6.283), grng.uniform(0.2, 1.0)) for _ in range(700)]
for sg in (1, -1):
    me = bpy.data.meshes.new(f"jet{sg}"); o = bpy.data.objects.new(f"jet{sg}", me); coll.objects.link(o); o.parent = LOCO
    o.instance_type = 'VERTS'
    g = bpy.data.objects.new(f"grain{sg}", gme); coll.objects.link(g); g.parent = o; g.scale = (0.0017,)*3
    JETS.append((sg, o, me))
def update_jets(t):
    on = clamp((t - JET_T0)/0.12)
    for sg, o, me in JETS:
        me.clear_geometry()
        if on <= 0 or t > 23.6:
            continue
        n0, tg = NOZ[sg], TGT[sg]; d_ = tg - n0
        side = Vector((0, 1, 0)); up = d_.cross(side).normalized()
        vs = []
        for (ph, a_, b_, sp) in GR:
            u = (ph + t*9.0*sp) % 1.0
            if u > on*1.2: continue
            p = n0 + d_*u + side*(a_*0.006 + a_*0.018*u) + up*(b_*0.005 + b_*0.014*u)
            vs.append(p)
        for (ph, ang, sp) in SPL:      # bouncing grains around the contact patch
            u = (ph + t*3.0) % 1.0
            r = 0.03 + 0.09*u*sp
            p = Vector((tg.x + r*math.cos(ang), tg.y + 0.5*r*math.sin(ang), 0.176 + 0.05*u*(1 - u)*sp*4))
            vs.append(p)
        me.from_pydata([tuple(v) for v in vs], [], []); me.update()
# a thin layer on the railhead under the jet (moves with the loco) + a crushed trail behind the wheel (fixed)
LAYERS = []
for sg in (1, -1):
    yy_ = sg*0.7525
    o = box(f"slay{sg}", AXL + 0.05, AXL + 0.44, yy_ - 0.034, yy_ + 0.034, 0.172, 0.177, M_SAND, LOCO, 0.002)
    LAYERS.append(o)
    tr = box(f"strail{sg}", -0.5, 0.5, yy_ - 0.03, yy_ + 0.03, 0.1722, 0.1745, M_SANDW, None, 0)
    LAYERS.append(tr)
def update_layers(t):
    k = clamp((t - JET_T0 - 0.1)/0.4)
    x0 = front_x(JET_T0) - 3.5 + 0.1; x1 = axle_x(t) + 0.1
    for o in LAYERS:
        if o.name.startswith("slay"):
            o.hide_render = k <= 0; o.scale = (1, 1, max(k, 0.01))
        else:
            ln = max(0.0, x1 - x0)
            o.hide_render = ln < 0.02 or k <= 0
            o.location = (x0 + ln/2, 0, 0); o.scale = (max(ln, 0.01), 1, 1)

# wet autumn leaves on sleepers, ballast and a few on the railheads
M_LEAVES = [principled(f"lf{c}", col, 0.35) for c, col in enumerate(((0.45, 0.14, 0.02), (0.30, 0.10, 0.02), (0.55, 0.30, 0.04), (0.20, 0.08, 0.02)))]
lr = random.Random(9)
for c in range(4):
    bm = bmesh.new()
    for k in range(260):
        if k < 18:
            x = lr.uniform(-3.0, 3.0); y = lr.choice(RAIL_Y) + lr.uniform(-0.02, 0.02); z = 0.1745
        else:
            x = lr.uniform(-9, 7); y = lr.uniform(-2.6, 2.6); z = (0.003 if abs(y) < 1.3 and (x % 0.6) < 0.16 else ballast_h(y) + 0.015)
            if abs(abs(y) - 0.75) < 0.06: continue
        a = lr.uniform(0, 6.28); sx, sy = lr.uniform(0.03, 0.05), lr.uniform(0.02, 0.035)
        ca, sa = math.cos(a), math.sin(a)
        pts = [(-sx, 0), (0, sy), (sx, 0), (0, -sy)]
        vv = [bm.verts.new((x + px*ca - py*sa, y + px*sa + py*ca, z + lr.uniform(0, 0.004))) for px, py in pts]
        bm.faces.new(vv)
    mesh_obj(f"leaves{c}", bm, M_LEAVES[c], smooth=False)

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
SUNROT = float(os.environ.get("SUNROT", "307"))
SUNEL = float(os.environ.get("SUNEL", "6"))
set_sun(SUNEL, SUNROT, 3.8, (1.0, 0.62, 0.36), 0.17)

# ------------------------------------------------------------------ camera
cam_d = bpy.data.cameras.new("cam"); cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 36; cam_d.clip_end = 20000; cam_d.clip_start = 0.02
cam = bpy.data.objects.new("cam", cam_d); coll.objects.link(cam); sc.camera = cam
SH = [(rnd.uniform(-1, 1), rnd.uniform(-1, 1)) for _ in range(400)]
def shake(t, amp, rate=1.6):
    i = int(t*rate); f = t*rate - i; a, b_ = SH[i % 400], SH[(i+1) % 400]; f = f*f*(3-2*f)
    return (a[0]+(b_[0]-a[0])*f)*amp, (a[1]+(b_[1]-a[1])*f)*amp
def aim(loc, tgt, t, amp, fstop=None, fdist=None, rate=1.6):
    cam.location = loc
    e = (Vector(tgt)-Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sx, sy = shake(t, amp, rate); e.x += sx; e.z += sy; cam.rotation_euler = e
    if fstop:
        cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = fstop
        cam_d.dof.focus_distance = fdist or (Vector(tgt) - Vector(loc)).length
    else:
        cam_d.dof.use_dof = False

def pose(t):
    if SHOT == "A":
        k = ease(t/7.4)
        cam_d.lens = lerp(38, 42, k)
        loc = Vector((lerp(13, 11, k), lerp(4.6, 4.2, k), lerp(1.7, 1.5, k)))
        tgt = Vector((-8, -3.5, 2.0))
        aim(loc, tgt, t, math.radians(0.06), fstop=8, fdist=(Vector((-6, 0, 2)) - loc).length)
    elif SHOT == "B":
        u = (t - 7.4)/7.5; k = ease(u); ax = axle_x(t)
        cam_d.lens = lerp(40, 46, k)
        loc = Vector((ax + lerp(1.9, 1.5, k), lerp(2.3, 2.0, k), lerp(0.48, 0.42, k)))
        tgt = Vector((ax - 0.15, 0.75, 0.40))
        aim(loc, tgt, t, math.radians(0.05 + 0.10*clamp((t - 8.2)/0.8)), fstop=4.0, fdist=(tgt - loc).length, rate=1.6 + 3*clamp((t - 8.2)/0.8))
    elif SHOT == "C":
        u = (t - 14.9)/8.6; k = ease(u); ax = axle_x(t)
        cam_d.lens = lerp(52, 60, k)
        loc = Vector((ax + lerp(1.45, 1.25, k), lerp(1.55, 1.42, k), lerp(0.34, 0.30, k)))
        tgt = Vector((ax + 0.30, 0.75, 0.25))
        aim(loc, tgt, t, math.radians(0.05), fstop=3.2, fdist=(tgt - loc).length)
    else:
        u = (t - 23.5)/8.0; k = ease(u)
        cam_d.lens = lerp(34, 38, k)
        loc = Vector((lerp(16, 18, k), lerp(11.5, 11.0, k), 1.9))
        tgt = Vector((front_x(t) - 9, 0, 1.9))
        aim(loc, tgt, t, math.radians(0.06), fstop=8, fdist=(tgt - loc).length)

# ------------------------------------------------------------------ render
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.cycles.samples = int(os.environ.get("SPP", "10")); sc.cycles.use_denoising = True; sc.cycles.use_adaptive_sampling = True
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transparent_max_bounces = 4
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.resolution_percentage = int(os.environ.get("PCT", "50"))
sc.render.use_persistent_data = True
sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5; sc.render.motion_blur_position = 'START'
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
sc.view_settings.exposure = float(os.environ.get("EXPO", "-0.3"))

def screen(p):
    v = world_to_camera_view(sc, cam, Vector(p)); return (v.x*RES[0], (1-v.y)*RES[1], v.z)
def shot_for(t):
    for k, (a, b) in SHOTS.items():
        if a <= t < b: return k
    return "D"
END = SHOTS["D"][1]
def setup(t, frame=None):
    global SHOT
    SHOT = shot_for(t); place_train(t, frame); update_jets(t); update_layers(t)
    if frame is not None: sc.frame_set(frame)
    pose(t); bpy.context.view_layer.update()
mode = sys.argv[sys.argv.index("--")+1] if "--" in sys.argv else "frames"
if mode == "test":
    for t in [float(x) for x in os.environ.get("TT", "3").split(",")]:
        setup(t, int(round(t*FPS)))
        sc.render.filepath = f"{OUT}/test_{t}.png"; bpy.ops.render.render(write_still=True)
elif mode == "meta":
    meta = {}
    for i in range(0, int(END*FPS)):
        t = i/FPS; setup(t)
        ax = axle_x(t)
        meta[i] = {"loco": screen((front_x(t) - 6, 0, 3.5)), "rail": screen((front_x(t) + 6, RAIL_Y[1], ZT + 0.17)),
                   "wheel": screen((ax, 0.82, 0.632)), "contact": screen((ax + 0.05, 0.7525, 0.18)),
                   "nozzle": screen((ax + 0.52, 0.7525, 0.32)), "leaf": screen((ax + 1.0, 0.7525, 0.175))}
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
