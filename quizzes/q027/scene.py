import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
# Quiz #27 - submarine anechoic tiles. Submarine surfaces at dusk; close-ups of the rubber tiles; missing tiles.
import bpy, bmesh, math, json, sys, os, random
from mathutils import Vector, Euler
from bpy_extras.object_utils import world_to_camera_view

FPS = 30
RES = (1080, 1920)
OUT = os.environ.get("OUT", QDIR)
SHOT = "A"
SHOTS = {"A": (0.0, 5.0), "B": (5.0, 14.0), "C": (14.0, 23.6), "D": (23.6, 33.2)}
END = SHOTS["D"][1]
SPEED = 3.0       # m/s, water flows past the (static) boat
if "frames" in sys.argv:
    _st = int(os.environ.get("STEP", "2")); _a = int(os.environ.get("IFROM", "0")); _b = int(os.environ.get("ITO", int(END*FPS)))
    if all(os.path.exists(f"{OUT}/frames/f{i:04d}.png") for i in range(_a, _b, _st)): sys.exit(0)

def ease(x):
    x = max(0.0, min(1.0, x)); return x*x*(3-2*x)
def lerp(a, b, k): return a + (b-a)*k
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; coll = sc.collection
rnd = random.Random(27)

def principled(name, color, rough=0.5, metal=0.0, coat=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal; b.inputs["Coat Weight"].default_value = coat
    return m

# ------------------------------------------------------------------ tile material (UV: u = metres along, v = metres around)
TILE = 0.55
def tile_mat():
    m = bpy.data.materials.new("tiles"); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    uv = nt.nodes.new("ShaderNodeUVMap"); uv.uv_map = "UVMap"
    br = nt.nodes.new("ShaderNodeTexBrick"); br.offset = 0.0; br.squash = 1.0
    br.inputs["Scale"].default_value = 1.0/TILE; br.inputs["Mortar Size"].default_value = 0.012; br.inputs["Mortar Smooth"].default_value = 0.2
    br.inputs["Bias"].default_value = 0.0
    br.inputs["Brick Width"].default_value = 1.0; br.inputs["Row Height"].default_value = 1.0
    br.inputs["Color1"].default_value = (0, 0, 0, 1); br.inputs["Color2"].default_value = (1, 1, 1, 1); br.inputs["Mortar"].default_value = (0, 0, 0, 1)
    nt.links.new(uv.outputs["UV"], br.inputs["Vector"])
    # second brick node only for the seam mask
    br2 = nt.nodes.new("ShaderNodeTexBrick"); br2.offset = 0.0; br2.squash = 1.0
    br2.inputs["Scale"].default_value = 1.0/TILE; br2.inputs["Mortar Size"].default_value = 0.012; br2.inputs["Mortar Smooth"].default_value = 0.2
    br2.inputs["Brick Width"].default_value = 1.0; br2.inputs["Row Height"].default_value = 1.0
    nt.links.new(uv.outputs["UV"], br2.inputs["Vector"])
    # per-tile random shade (Color output of br with bias spread) -> slight tone variation
    br3 = nt.nodes.new("ShaderNodeTexBrick"); br3.offset = 0.0; br3.squash = 1.0
    br3.inputs["Scale"].default_value = 1.0/TILE; br3.inputs["Mortar Size"].default_value = 0.0
    br3.inputs["Color1"].default_value = (0.007, 0.007, 0.008, 1); br3.inputs["Color2"].default_value = (0.011, 0.011, 0.012, 1)
    br3.inputs["Brick Width"].default_value = 1.0; br3.inputs["Row Height"].default_value = 1.0
    nt.links.new(uv.outputs["UV"], br3.inputs["Vector"])
    # missing tiles only inside a cluster region (noise) -> gate
    snp = nt.nodes.new("ShaderNodeVectorMath"); snp.operation = 'SNAP'; snp.inputs[1].default_value = (TILE, TILE, 1.0)
    nt.links.new(uv.outputs["UV"], snp.inputs[0])
    cen = nt.nodes.new("ShaderNodeVectorMath"); cen.operation = 'ADD'; cen.inputs[1].default_value = (TILE/2, TILE/2, 0.0)
    nt.links.new(snp.outputs[0], cen.inputs[0])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.09; nz.inputs["Detail"].default_value = 2
    nt.links.new(cen.outputs[0], nz.inputs["Vector"])
    g1 = nt.nodes.new("ShaderNodeMath"); g1.operation = 'GREATER_THAN'; g1.inputs[1].default_value = 0.63
    nt.links.new(nz.outputs["Fac"], g1.inputs[0])
    # a guaranteed cluster around UV (10, 12.2) = starboard upper side, shown in close-up C
    dv = nt.nodes.new("ShaderNodeVectorMath"); dv.operation = 'DISTANCE'; dv.inputs[1].default_value = (10.0, 12.2, 0.0)
    nt.links.new(cen.outputs[0], dv.inputs[0])
    nz3 = nt.nodes.new("ShaderNodeTexNoise"); nz3.inputs["Scale"].default_value = 0.6
    nt.links.new(cen.outputs[0], nz3.inputs["Vector"])
    dd = nt.nodes.new("ShaderNodeMath"); dd.operation = 'MULTIPLY_ADD'; dd.inputs[1].default_value = 1.2; dd.inputs[2].default_value = 0.7
    nt.links.new(nz3.outputs["Fac"], dd.inputs[0])
    g2 = nt.nodes.new("ShaderNodeMath"); g2.operation = 'LESS_THAN'
    nt.links.new(dv.outputs["Value"], g2.inputs[0]); nt.links.new(dd.outputs[0], g2.inputs[1])
    sepc = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(br.outputs["Color"], sepc.inputs[0])
    r1 = nt.nodes.new("ShaderNodeMath"); r1.operation = 'GREATER_THAN'; r1.inputs[1].default_value = 0.5
    nt.links.new(sepc.outputs[0], r1.inputs[0])
    r2 = nt.nodes.new("ShaderNodeMath"); r2.operation = 'GREATER_THAN'; r2.inputs[1].default_value = 0.88
    nt.links.new(sepc.outputs[0], r2.inputs[0])
    a1 = nt.nodes.new("ShaderNodeMath"); a1.operation = 'MULTIPLY'; nt.links.new(r1.outputs[0], a1.inputs[0]); nt.links.new(g2.outputs[0], a1.inputs[1])
    a2 = nt.nodes.new("ShaderNodeMath"); a2.operation = 'MULTIPLY'; nt.links.new(r2.outputs[0], a2.inputs[0]); nt.links.new(g1.outputs[0], a2.inputs[1])
    mm = nt.nodes.new("ShaderNodeMath"); mm.operation = 'MAXIMUM'; nt.links.new(a1.outputs[0], mm.inputs[0]); nt.links.new(a2.outputs[0], mm.inputs[1])
    # missing = dull grey-green primer with glue residue
    nz2 = nt.nodes.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = 18; nz2.inputs["Detail"].default_value = 8
    nt.links.new(uv.outputs["UV"], nz2.inputs["Vector"])
    cr = nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (0.035, 0.042, 0.038, 1); cr.color_ramp.elements[1].color = (0.075, 0.075, 0.065, 1)
    nt.links.new(nz2.outputs["Fac"], cr.inputs[0])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'
    nt.links.new(mm.outputs[0], mix.inputs[0]); nt.links.new(br3.outputs["Color"], mix.inputs[6]); nt.links.new(cr.outputs[0], mix.inputs[7])
    # seams darker
    sep2 = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(br2.outputs["Color"], sep2.inputs[0])
    mortar = nt.nodes.new("ShaderNodeMath"); mortar.operation = 'LESS_THAN'; mortar.inputs[1].default_value = 0.01
    nt.links.new(br2.outputs["Fac"], mortar.inputs[0])
    mix2 = nt.nodes.new("ShaderNodeMix"); mix2.data_type = 'RGBA'; mix2.inputs[7].default_value = (0.0, 0.0, 0.0, 1)
    nt.links.new(mix.outputs[2], mix2.inputs[6]); nt.links.new(br2.outputs["Fac"], mix2.inputs[0])
    nt.links.new(mix2.outputs[2], b.inputs["Base Color"])
    # roughness: rubber matte, wet sheen
    rr = nt.nodes.new("ShaderNodeMapRange"); rr.inputs[3].default_value = 0.5; rr.inputs[4].default_value = 0.7
    nt.links.new(mm.outputs[0], rr.inputs[0]); nt.links.new(rr.outputs[0], b.inputs["Roughness"])
    # bump: tiles stand proud, missing ones recessed
    bsum = nt.nodes.new("ShaderNodeMath"); bsum.operation = 'SUBTRACT'
    nt.links.new(br2.outputs["Fac"], bsum.inputs[0]); nt.links.new(mm.outputs[0], bsum.inputs[1])
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.6; bump.inputs["Distance"].default_value = 0.03
    nt.links.new(bsum.outputs[0], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m
M_TILE = tile_mat()

def mesh_obj(name, bm, mat, smooth=True, parent=None):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); coll.objects.link(o); o.data.materials.append(mat)
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    if parent: o.parent = parent
    return o

# ------------------------------------------------------------------ hull: lathe around X with metric UVs
HL = 104.0; R = 5.0
def hull_r(x):
    # x from -HL/2 (stern) to +HL/2 (bow)
    xb = HL/2 - 9.0
    if x > xb:
        u = (x - xb)/9.0; return R*math.sqrt(max(0.0, 1 - u**2.2))
    xs = -HL/2 + 30.0
    if x < xs:
        u = (xs - x)/30.0; return R*(1 - 0.92*u**1.6)
    return R
def build_hull():
    bm = bmesh.new(); seg = 96
    xs = [(-HL/2) + k*0.75 for k in range(int(HL/0.75) + 1)]
    xs[-1] = HL/2 - 0.001
    rings = []
    for x in xs:
        r = max(0.05, hull_r(x))
        rings.append([bm.verts.new((x, r*math.cos(2*math.pi*i/seg), r*math.sin(2*math.pi*i/seg))) for i in range(seg)])
    uvl = bm.loops.layers.uv.new("UVMap")
    for ri in range(len(rings) - 1):
        a, b = rings[ri], rings[ri+1]
        ra, rb = max(0.05, hull_r(xs[ri])), max(0.05, hull_r(xs[ri+1]))
        for i in range(seg):
            f = bm.faces.new([a[i], a[(i+1) % seg], b[(i+1) % seg], b[i]])
            # v = arc length measured around with the main radius (tiles keep size), offset so seams aren't on top
            cs = [(xs[ri], i, ra), (xs[ri], i+1, ra), (xs[ri+1], i+1, rb), (xs[ri+1], i, rb)]
            for lp, (x, ii, rr) in zip(f.loops, cs):
                lp[uvl].uv = (x, (ii/seg)*2*math.pi*R)
    return mesh_obj("hull", bm, M_TILE, True)
hull = build_hull()
root = bpy.data.objects.new("subRoot", None); coll.objects.link(root); hull.parent = root

def box_uv(name, x0, x1, y0, y1, z0, z1, mat, parent, bev=0.2):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(x1-x0, y1-y0, z1-z0), verts=bm.verts)
    bmesh.ops.translate(bm, vec=((x0+x1)/2, (y0+y1)/2, (z0+z1)/2), verts=bm.verts)
    if bev > 0: bmesh.ops.bevel(bm, geom=bm.edges[:]+bm.verts[:], offset=bev, segments=3, affect='EDGES', profile=0.5)
    uvl = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        n = f.normal
        for lp in f.loops:
            co = lp.vert.co
            if abs(n.y) > 0.5: lp[uvl].uv = (co.x, co.z)
            elif abs(n.x) > 0.5: lp[uvl].uv = (co.y, co.z)
            else: lp[uvl].uv = (co.x, co.y)
    return mesh_obj(name, bm, mat, True, parent)

# sail (fin): streamlined plan view built by extruding an airfoil outline vertically
def sail():
    bm = bmesh.new()
    Ls = 11.0; Wd = 1.3
    prof = []
    for k in range(25):
        u = k/24; x = 30.0 - u*Ls       # front at x=30
        th = Wd*(1.25*math.sqrt(u) - 0.35*u - 0.9*u**3 + 0.0)
        prof.append((x, max(0.18, th)))
    pts = [(x, y) for x, y in prof] + [(x, -y) for x, y in reversed(prof)]
    z0, z1 = R - 0.6, R + 7.2
    bot = [bm.verts.new((x, y, z0)) for x, y in pts]; top = [bm.verts.new((x, y, z1)) for x, y in pts]
    n = len(pts)
    for i in range(n): bm.faces.new([bot[i], bot[(i+1) % n], top[(i+1) % n], top[i]])
    bm.faces.new(top[::-1])
    uvl = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for lp in f.loops:
            co = lp.vert.co; lp[uvl].uv = (co.x + co.y*0.3, co.z)
    o = mesh_obj("sail", bm, M_TILE, True, root)
    bv = o.modifiers.new("b", 'BEVEL'); bv.width = 0.25; bv.segments = 3
    # sail planes
    for s in (1, -1):
        box_uv(f"splane{s}", 24.0, 26.6, s*1.0, s*4.6, R + 4.2, R + 4.5, M_TILE, root, 0.12)
    # masts / periscopes at the top
    M_MAST = principled("mast", (0.03, 0.03, 0.035), 0.45, 0.3)
    for k, (dx, h) in enumerate(((27.0, 2.6), (25.5, 1.8), (23.6, 1.2))):
        bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=0.16, depth=h, location=(dx, 0, R + 7.2 + h/2))
        bpy.context.object.data.materials.append(M_MAST); bpy.context.object.parent = root
sail()
# stern planes + rudder (cruciform)
for (ys, zs) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
    x0 = -HL/2 + 3.0
    if ys: box_uv(f"st{ys}{zs}", x0, x0 + 4.0, ys*0.9, ys*4.8, -0.15, 0.15, M_TILE, root, 0.1)
    else: box_uv(f"st{ys}{zs}", x0, x0 + 4.0, -0.15, 0.15, zs*0.9, zs*5.2, M_TILE, root, 0.1)
# deck hatch outlines (subtle) — a flat casing strip along the top
box_uv("casing", -30, 40, -1.6, 1.6, R - 0.35, R + 0.12, M_TILE, root, 0.3)

# ------------------------------------------------------------------ sea
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
sea = bpy.context.object; sea.name = "sea"
oc = sea.modifiers.new("ocean", 'OCEAN')
oc.geometry_mode = 'GENERATE'; oc.size = 1.0; oc.spatial_size = 70; oc.resolution = 16
oc.repeat_x = 12; oc.repeat_y = 12; oc.wave_scale = 0.9; oc.choppiness = 1.4; oc.wind_velocity = 10; oc.random_seed = 3
wm = bpy.data.materials.new("water"); wm.use_nodes = True
bw = wm.node_tree.nodes["Principled BSDF"]
bw.inputs["Base Color"].default_value = (0.004, 0.016, 0.022, 1); bw.inputs["Roughness"].default_value = 0.1; bw.inputs["IOR"].default_value = 1.33
_nt = wm.node_tree
_tc = _nt.nodes.new("ShaderNodeTexCoord"); _mp = _nt.nodes.new("ShaderNodeMapping"); _mp.name = "wflow"
_nt.links.new(_tc.outputs["Object"], _mp.inputs["Vector"])
_nz = _nt.nodes.new("ShaderNodeTexNoise"); _nz.inputs["Scale"].default_value = 0.35; _nz.inputs["Detail"].default_value = 10; _nz.inputs["Roughness"].default_value = 0.6
_nt.links.new(_mp.outputs["Vector"], _nz.inputs["Vector"])
_bp = _nt.nodes.new("ShaderNodeBump"); _bp.inputs["Strength"].default_value = 0.35; _bp.inputs["Distance"].default_value = 0.4
_nt.links.new(_nz.outputs["Fac"], _bp.inputs["Height"]); _nt.links.new(_bp.outputs["Normal"], bw.inputs["Normal"])
sea.data.materials.append(wm)
sea.location = (-420, -420, 0)
bpy.ops.mesh.primitive_plane_add(size=200000, location=(0, 0, -0.35)); bpy.context.object.name = "seafar"; bpy.context.object.data.materials.append(wm)

# foam (bow wave + wash along the hull + spill when surfacing)
def foam_mat(name, scale=0.25, lo=0.44, hi=0.58):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    for n_ in list(nt.nodes): nt.nodes.remove(n_)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    df = nt.nodes.new("ShaderNodeBsdfPrincipled"); df.inputs["Base Color"].default_value = (0.92, 0.94, 0.95, 1); df.inputs["Roughness"].default_value = 0.85
    tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mx = nt.nodes.new("ShaderNodeMixShader")
    tc = nt.nodes.new("ShaderNodeTexCoord"); mpn = nt.nodes.new("ShaderNodeMapping"); mpn.name = "flow"
    nt.links.new(tc.outputs["Object"], mpn.inputs["Vector"])
    n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = scale; n1.inputs["Detail"].default_value = 14; n1.inputs["Roughness"].default_value = 0.72
    nt.links.new(mpn.outputs["Vector"], n1.inputs["Vector"])
    gr = nt.nodes.new("ShaderNodeAttribute"); gr.attribute_name = "fade"; gr.attribute_type = "GEOMETRY"
    rp = nt.nodes.new("ShaderNodeValToRGB"); rp.color_ramp.elements[0].position = lo; rp.color_ramp.elements[1].position = hi
    nt.links.new(n1.outputs["Fac"], rp.inputs[0])
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'; mul.name = "amt"
    nt.links.new(rp.outputs[0], mul.inputs[0]); nt.links.new(gr.outputs["Fac"], mul.inputs[1])
    mul2 = nt.nodes.new("ShaderNodeMath"); mul2.operation = 'MULTIPLY'; mul2.name = "gain"; mul2.inputs[1].default_value = 1.0
    nt.links.new(mul.outputs[0], mul2.inputs[0])
    nt.links.new(mul2.outputs[0], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(df.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs[0])
    return m
def foam_strip(name, pts, mat, parent=None):
    """pts: list of (x, y_inner, y_outer, z_inner, fade)"""
    bm = bmesh.new(); prev = None; fades = []
    for (x, yi, yo, z, f) in pts:
        a = bm.verts.new((x, yi, z)); m_ = bm.verts.new((x, yi*0.6 + yo*0.4, z*0.5 + 0.12)); b_ = bm.verts.new((x, yo, 0.12)); fades += [f, f*0.8, f*0.1]
        if prev:
            bm.faces.new([prev[0], prev[1], m_, a]); bm.faces.new([prev[1], prev[2], b_, m_])
        prev = (a, m_, b_)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    at = me.attributes.new("fade", 'FLOAT', 'POINT')
    for k, v in enumerate(fades): at.data[k].value = v
    o = bpy.data.objects.new(name, me); coll.objects.link(o); o.data.materials.append(mat)
    if parent: o.parent = parent
    return o
FOAM = foam_mat("foam", lo=0.50, hi=0.62)
FOAMS = []
for s in (-1, 1):
    pts = []
    for k in range(70):
        x = HL/2 + 2 - k*2.2
        hb = max(0.2, hull_r(min(x, HL/2 - 0.2)))*0.98
        spread = 1.0 + k*0.12
        pts.append((x, s*(hb + 0.05), s*(hb + spread), 0.3 + 1.2*math.exp(-k/5), max(0.0, 0.7 - k/40)))
    FOAMS.append(foam_strip(f"foam{s}", pts, FOAM))
pts = []
for k in range(60):
    x = -HL/2 - k*4
    w = 3 + k*0.7
    pts.append((x, -w, w, 0.2, max(0.0, 0.8 - k/60)))
FOAMS.append(foam_strip("wake", pts, FOAM))
# surfacing spill: white water sheet on top of the hull draining off (shot A)
SPILL = foam_mat("spill", scale=0.35, lo=0.40, hi=0.55)
spts = []
for k in range(50):
    x = HL/2 - 4 - k*1.9
    spts.append((x, -0.1, -(R + 3.5), R + 0.25, 1.0))
sp1 = foam_strip("spillL", spts, SPILL, root)
sp2 = foam_strip("spillR", [(x, -yi, -yo, z, f) for (x, yi, yo, z, f) in spts], SPILL, root)

def set_flow(t):
    FOAM.node_tree.nodes["flow"].inputs["Location"].default_value = (SPEED*t, 0, 0)
    SPILL.node_tree.nodes["flow"].inputs["Location"].default_value = (0, 0, -1.6*t)

# ------------------------------------------------------------------ sky + sun (dusk)
wo = bpy.data.worlds.new("w"); sc.world = wo; wo.use_nodes = True
bg = wo.node_tree.nodes["Background"]
sky = wo.node_tree.nodes.new("ShaderNodeTexSky"); sky.sky_type = 'MULTIPLE_SCATTERING'
wo.node_tree.links.new(sky.outputs[0], bg.inputs[0])
SUNROT = float(os.environ.get("SUNROT", "-50")); SUNEL = float(os.environ.get("SUNEL", "4.0"))
sky.sun_elevation = math.radians(SUNEL); sky.sun_rotation = math.radians(SUNROT); sky.altitude = 0; sky.aerosol_density = 2.2; sky.sun_intensity = 0.5
bg.inputs[1].default_value = 0.2
sun_d = bpy.data.lights.new("sun", 'SUN'); sun_d.energy = 3.4; sun_d.color = (1.0, 0.60, 0.36); sun_d.angle = math.radians(0.6)
sun = bpy.data.objects.new("sun", sun_d); coll.objects.link(sun)
sun.rotation_euler = Euler((math.radians(90 - SUNEL), 0, math.radians(SUNROT + 90)))
# ------------------------------------------------------------------ camera
cam_d = bpy.data.cameras.new("cam"); cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 36; cam_d.clip_end = 100000; cam_d.clip_start = 0.05
cam = bpy.data.objects.new("cam", cam_d); coll.objects.link(cam); sc.camera = cam
SH = [(rnd.uniform(-1, 1), rnd.uniform(-1, 1)) for _ in range(400)]
def shake(t, amp, rate=1.8):
    i = int(t*rate); f = t*rate - i; a, b_ = SH[i % 400], SH[(i+1) % 400]; f = f*f*(3-2*f)
    return (a[0]+(b_[0]-a[0])*f)*amp, (a[1]+(b_[1]-a[1])*f)*amp
def aim(loc, tgt, t, amp, fstop=None, fdist=None):
    cam.location = loc
    e = (Vector(tgt)-Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sx, sy = shake(t, amp); e.x += sx; e.z += sy; cam.rotation_euler = e
    if fstop:
        cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = fstop
        cam_d.dof.focus_distance = fdist or (Vector(tgt) - Vector(loc)).length
    else: cam_d.dof.use_dof = False

ZREST = -1.7      # hull axis below the waterline when surfaced (top of hull ~4 m above water)
def sub_z(t):
    if SHOT == "A": return lerp(-7.5, ZREST, ease((t - 0.2)/4.2))
    return ZREST
MISS = Vector((14.0, -0.0, 0.0))   # placeholder, computed below
def pose(t):
    set_flow(t)
    oc.time = t*0.9
    sea.location = (-420 - (SPEED*t) % 70, -420, 0)
    z = sub_z(t) + 0.12*math.sin(t*0.7)
    root.location = (0, 0, z)
    root.rotation_euler = (math.radians(0.8)*math.sin(t*0.45 + 1), math.radians(0.5 if SHOT != "A" else lerp(3.0, 0.4, ease(t/4.5)))*1.0, 0)
    # spill only while surfacing
    g = (1 - ease((t - 2.5)/2.2)) if SHOT == "A" else 0.0
    SPILL.node_tree.nodes["gain"].inputs[1].default_value = g
    for o in (sp1, sp2): o.hide_render = g <= 0.01
    if SHOT == "A":
        k = ease(t/5.0); cam_d.lens = lerp(40, 46, k)
        aim((lerp(95, 88, k), -58, 3.5), (15, 0, 1.6), t, math.radians(0.06))
    elif SHOT == "B":
        k = ease((t - 5.0)/9.0); cam_d.lens = lerp(32, 36, k)
        loc = Vector((lerp(-8, 4, k), -R - 4.0, 3.4))
        tgt = Vector((lerp(6, 18, k), -2.0, 1.6))
        aim(loc, tgt, t, math.radians(0.07), fstop=5.6, fdist=(tgt - loc).length*0.75)
    elif SHOT == "C":
        k = ease((t - 14.0)/9.6); cam_d.lens = lerp(32, 36, k)
        tgt = Vector(MISS_T) + Vector((0, 0, z))
        loc = tgt + Vector((lerp(-2.4, -1.4, k), -4.2, 1.6))
        aim(loc, tgt, t, math.radians(0.06), fstop=4.0, fdist=(tgt - loc).length)
    else:
        k = ease((t - 23.6)/9.6); cam_d.lens = lerp(55, 60, k)
        aim((lerp(150, 135, k), -95, 5.0), (lerp(10, 0, k), 0, 2.5), t, math.radians(0.05))

# location of a cluster of missing tiles on the starboard (-y) side for shot C — found by scanning the noise later; default
MISS_T = tuple(float(v) for v in os.environ.get("MISS", "10,-3.83,3.21").split(","))

# ------------------------------------------------------------------ render
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.cycles.samples = int(os.environ.get("SPP", "10")); sc.cycles.use_denoising = True; sc.cycles.use_adaptive_sampling = True
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transparent_max_bounces = 8
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.resolution_percentage = int(os.environ.get("PCT", "50"))
sc.render.use_persistent_data = True
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
sc.view_settings.exposure = float(os.environ.get("EXPO", "-0.25"))

def screen(p):
    v = world_to_camera_view(sc, cam, Vector(p)); return (v.x*RES[0], (1-v.y)*RES[1], v.z)
def shot_for(t):
    for k, (a, b) in SHOTS.items():
        if a <= t < b: return k
    return "D"
def setup(t):
    global SHOT
    SHOT = shot_for(t); pose(t); bpy.context.view_layer.update()
mode = sys.argv[sys.argv.index("--")+1] if "--" in sys.argv else "frames"
if mode == "test":
    for t in [float(x) for x in os.environ.get("TT", "3").split(",")]:
        setup(t); sc.render.filepath = f"{OUT}/test_{t}.png"; bpy.ops.render.render(write_still=True)
elif mode == "meta":
    oc.show_viewport = False; oc.show_render = False
    meta = {}
    for i in range(0, int(END*FPS)):
        t = i/FPS; setup(t); mw = root.matrix_world
        meta[i] = {"tiles": screen(mw @ Vector((14, -3.6, 3.4))), "miss": screen(mw @ Vector(MISS_T)),
                   "sail": screen(mw @ Vector((26, 0, R + 4))), "sub": screen(mw @ Vector((0, 0, R)))}
    json.dump(meta, open(f"{OUT}/meta.json", "w"))
else:
    import time as _tm
    os.makedirs(f"{OUT}/frames", exist_ok=True)
    step = int(os.environ.get("STEP", "2"))
    i0 = int(os.environ.get("IFROM", "0")); i1 = int(os.environ.get("ITO", int(END*FPS)))
    for i in range(i0, i1, step):
        out = f"{OUT}/frames/f{i:04d}.png"
        if os.path.exists(out): continue
        _t0 = _tm.time(); setup(i/FPS)
        sc.render.filepath = out; bpy.ops.render.render(write_still=True)
        print(f"TIMING f{i} {_tm.time()-_t0:.1f}s", flush=True)
