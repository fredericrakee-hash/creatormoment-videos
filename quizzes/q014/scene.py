import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import bpy, bmesh, math, json, sys, os, random
from mathutils import Vector, Euler
from bpy_extras.object_utils import world_to_camera_view

FPS = 30
RES = (1080, 1920)
OUT = os.environ.get("OUT", QDIR)
SHOT = os.environ.get("SHOT", "A")
SHOTS = {"A": (0.0, 6.8), "B": (6.8, 15.2), "C": (15.2, 28.4)}
R_E = 637100.0          # Earth radius, scaled 1:10 (angular size like ~550 km altitude)
ALT = 55000.0

def ease(x):
    x = max(0.0, min(1.0, x)); return x*x*(3-2*x)
def lerp(a, b, k): return a + (b-a)*k

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; coll = sc.collection
rnd = random.Random(14)

def principled(name, color, rough=0.5, metal=0.0, coat=0.0, emit=None, estr=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal; b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = estr
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
def cyl(name, r, d, loc, mat, parent=None, rot=None, v=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=v, radius=r, depth=d, location=loc)
    o = bpy.context.object; o.name = name; o.data.materials.append(mat)
    if rot: o.rotation_euler = rot
    if parent: o.parent = parent
    for p in o.data.polygons: p.use_smooth = True
    return o

# ------------------------------------------------------------------ materials
def mli(name, col, rough=0.22):
    """crinkled multi-layer blanket: metallic film with strong wrinkle normals"""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Metallic"].default_value = 1.0
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 3.0; nz.inputs["Detail"].default_value = 10
    nz.inputs["Distortion"].default_value = 1.5
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    def ridge(scale, dist):
        n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = 4
        n.inputs["Distortion"].default_value = dist; nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
        a = nt.nodes.new("ShaderNodeMath"); a.operation = 'SUBTRACT'; a.inputs[1].default_value = 0.5
        nt.links.new(n.outputs["Fac"], a.inputs[0])
        b_ = nt.nodes.new("ShaderNodeMath"); b_.operation = 'ABSOLUTE'; nt.links.new(a.outputs[0], b_.inputs[0])
        c = nt.nodes.new("ShaderNodeMath"); c.operation = 'MULTIPLY_ADD'; c.inputs[1].default_value = -2.0; c.inputs[2].default_value = 1.0
        nt.links.new(b_.outputs[0], c.inputs[0])
        d = nt.nodes.new("ShaderNodeMath"); d.operation = 'POWER'; d.inputs[1].default_value = 5.0
        nt.links.new(c.outputs[0], d.inputs[0])
        return d
    r1 = ridge(1.3, 1.4); r2 = ridge(4.0, 1.8)
    ad = nt.nodes.new("ShaderNodeMath"); ad.operation = 'MULTIPLY_ADD'; ad.inputs[1].default_value = 0.45
    nt.links.new(r2.outputs[0], ad.inputs[0]); nt.links.new(r1.outputs[0], ad.inputs[2])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.5; bp.inputs["Distance"].default_value = 0.02
    nt.links.new(ad.outputs[0], bp.inputs["Height"]); nt.links.new(bp.outputs[0], b.inputs["Normal"])
    # colour + roughness variation
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs["Factor"].default_value = 0.35
    mix.inputs[6].default_value = (*col, 1); nt.links.new(nz.outputs["Fac"], mix.inputs[7])
    nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[3].default_value = rough*0.5; mr.inputs[4].default_value = rough*1.6
    nt.links.new(nz.outputs["Fac"], mr.inputs[0]); nt.links.new(mr.outputs[0], b.inputs["Roughness"])
    return m
M_GOLD = mli("gold", (1.0, 0.62, 0.22), 0.12)
M_SILV = mli("silver", (0.85, 0.86, 0.88), 0.18)
M_WHITE = principled("white", (0.75, 0.75, 0.73), 0.5)
M_DARK = principled("dark", (0.03, 0.03, 0.035), 0.5, 0.3)
M_ALU = principled("alu", (0.6, 0.6, 0.62), 0.35, 1.0)
M_NOZ = principled("noz", (0.25, 0.22, 0.2), 0.35, 1.0)
def cells_mat():
    m = bpy.data.materials.new("cells"); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.12; b.inputs["Coat Weight"].default_value = 1.0
    tc = nt.nodes.new("ShaderNodeTexCoord")
    br = nt.nodes.new("ShaderNodeTexBrick"); br.inputs["Scale"].default_value = 1.0
    br.inputs["Mortar Size"].default_value = 0.012; br.offset = 0.0
    br.inputs["Brick Width"].default_value = 0.16; br.inputs["Row Height"].default_value = 0.16
    br.inputs["Color1"].default_value = (0.012, 0.02, 0.06, 1); br.inputs["Color2"].default_value = (0.018, 0.028, 0.08, 1)
    br.inputs["Mortar"].default_value = (0.5, 0.5, 0.52, 1)
    nt.links.new(tc.outputs["Object"], br.inputs["Vector"]); nt.links.new(br.outputs["Color"], b.inputs["Base Color"])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[3].default_value = 0.0; mr.inputs[4].default_value = 1.0
    nt.links.new(br.outputs["Fac"], mr.inputs[0]); nt.links.new(mr.outputs[0], b.inputs["Metallic"])
    return m
M_CELLS = cells_mat()

# ------------------------------------------------------------------ satellite (origin = bus centre)
sat = bpy.data.objects.new("sat", None); coll.objects.link(sat)
def blanket(name, size, loc, mat, seed):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object; o.name = name; o.scale = size; o.parent = sat
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    md = o.modifiers.new("bv", 'BEVEL'); md.width = 0.06; md.segments = 3
    md = o.modifiers.new("sub", 'SUBSURF'); md.subdivision_type = 'SIMPLE'; md.levels = 5; md.render_levels = 5
    tx = bpy.data.textures.new(f"w{name}", 'CLOUDS'); tx.noise_scale = 0.12; tx.noise_depth = 2
    md = o.modifiers.new("d", 'DISPLACE'); md.texture = tx; md.strength = 0.015; md.texture_coords = 'LOCAL'
    tx2 = bpy.data.textures.new(f"n{name}", 'CLOUDS'); tx2.noise_scale = 0.35
    md = o.modifiers.new("d2", 'DISPLACE'); md.texture = tx2; md.strength = 0.025; md.texture_coords = 'LOCAL'
    o.data.materials.append(mat)
    for p in o.data.polygons: p.use_smooth = True
    return o
bus = blanket("bus", (2.2, 2.2, 2.9), (0, 0, 0), M_GOLD, 1)
# silver radiator panels on +x / -x
box("rad1", (0.03, 1.8, 2.2), (1.13, 0, 0.1), M_SILV, sat)
# top deck: dish, feed, antennas
box("deck", (2.0, 2.0, 0.05), (0, 0, 1.47), M_WHITE, sat)
bm = bmesh.new(); nr, ns = 24, 10
rings = []
for i in range(ns + 1):
    r = 1.0*i/ns
    rings.append([bm.verts.new((r*math.cos(2*math.pi*j/nr), r*math.sin(2*math.pi*j/nr), 0.35*r*r)) for j in range(nr)])
for i in range(ns):
    for j in range(nr):
        jj = (j+1) % nr; f = bm.faces.new([rings[i][j], rings[i][jj], rings[i+1][jj], rings[i+1][j]]); f.smooth = True
me = bpy.data.meshes.new("dish"); bm.to_mesh(me); bm.free()
dish = bpy.data.objects.new("dish", me); coll.objects.link(dish); dish.data.materials.append(M_WHITE)
dish.modifiers.new("s", 'SOLIDIFY').thickness = 0.03
dish.parent = sat; dish.location = (0.4, 0.0, 2.15); dish.rotation_euler = (0, math.radians(-35), 0)
cyl("dishpost", 0.06, 0.7, (0.35, 0, 1.75), M_ALU, sat)
cyl("feed", 0.04, 0.8, (0.62, 0, 2.6), M_ALU, sat, rot=(0, math.radians(-35), 0))
cyl("omni", 0.025, 0.9, (-0.7, 0.6, 1.9), M_ALU, sat)
box("tracker", (0.25, 0.25, 0.35), (-0.6, -0.6, 1.65), M_DARK, sat)
cyl("baffle", 0.1, 0.25, (-0.6, -0.6, 1.92), M_DARK, sat)
# bottom: engine + thrusters + gold-wrapped tank ring
cyl("eng", 0.28, 0.25, (0, 0, -1.55), M_GOLD, sat)
bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=0.32, radius2=0.12, depth=0.55, location=(0, 0, -1.92))
o = bpy.context.object; o.data.materials.append(M_NOZ); o.parent = sat
for k in range(4):
    a = k*math.pi/2 + math.pi/4
    cyl(f"thr{k}", 0.05, 0.16, (0.95*math.cos(a), 0.95*math.sin(a), -1.5), M_NOZ, sat)
# extra blanket patches (silver + gold), with "stitches"
blanket("patch1", (0.9, 0.04, 1.1), (0.4, -1.12, -0.5), M_SILV, 2)
blanket("patch2", (0.7, 0.05, 0.8), (-0.5, 1.12, 0.6), M_GOLD, 3)
# solar arrays on +/-y
arrays = []
for s in (1, -1):
    root = bpy.data.objects.new(f"wing{s}", None); coll.objects.link(root); root.parent = sat
    root.location = (0, s*1.1, 0.0)
    cyl(f"yoke{s}", 0.05, 1.2, (0, s*0.6, 0), M_ALU, root, rot=(math.radians(90), 0, 0))
    box(f"drv{s}", (0.3, 0.2, 0.3), (0, s*0.1, 0), M_DARK, root)
    for k in range(3):
        y = s*(1.2 + 1.0 + k*2.06)
        box(f"pan{s}{k}", (0.03, 2.0, 2.6), (0, y, 0), M_CELLS, root)
        box(f"panb{s}{k}", (0.012, 2.0, 2.6), (0.022, y, 0), M_WHITE, root)
        box(f"frm{s}{k}", (0.045, 2.02, 0.03), (0, y, 1.3), M_ALU, root)
        box(f"frm2{s}{k}", (0.045, 2.02, 0.03), (0, y, -1.3), M_ALU, root)
    arrays.append(root)

# ------------------------------------------------------------------ Earth (scaled), clouds, atmosphere rim
earth_c = Vector((0, 0, -(R_E + ALT)))
def earth_mat():
    m = bpy.data.materials.new("earth"); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 3.5; nz.inputs["Detail"].default_value = 14; nz.inputs["Roughness"].default_value = 0.62
    nt.links.new(tc.outputs["Generated"], nz.inputs["Vector"])
    land = nt.nodes.new("ShaderNodeMapRange"); land.inputs[1].default_value = 0.53; land.inputs[2].default_value = 0.56
    nt.links.new(nz.outputs["Fac"], land.inputs[0])
    nz2 = nt.nodes.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = 40; nz2.inputs["Detail"].default_value = 10
    nt.links.new(tc.outputs["Generated"], nz2.inputs["Vector"])
    lc = nt.nodes.new("ShaderNodeMix"); lc.data_type = 'RGBA'
    lc.inputs[6].default_value = (0.06, 0.07, 0.03, 1); lc.inputs[7].default_value = (0.22, 0.16, 0.09, 1)
    nt.links.new(nz2.outputs["Fac"], lc.inputs[0])
    col = nt.nodes.new("ShaderNodeMix"); col.data_type = 'RGBA'
    col.inputs[6].default_value = (0.004, 0.018, 0.06, 1)
    nt.links.new(lc.outputs[2], col.inputs[7]); nt.links.new(land.outputs[0], col.inputs[0])
    nt.links.new(col.outputs[2], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange"); rr.inputs[3].default_value = 0.25; rr.inputs[4].default_value = 0.9
    nt.links.new(land.outputs[0], rr.inputs[0]); nt.links.new(rr.outputs[0], b.inputs["Roughness"])
    return m
bpy.ops.mesh.primitive_uv_sphere_add(segments=256, ring_count=128, radius=R_E, location=earth_c)
earth = bpy.context.object; earth.data.materials.append(earth_mat())
for p in earth.data.polygons: p.use_smooth = True
def cloud_mat():
    m = bpy.data.materials.new("clouds"); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (0.9, 0.9, 0.92, 1); b.inputs["Roughness"].default_value = 0.9
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 9; nz.inputs["Detail"].default_value = 15; nz.inputs["Roughness"].default_value = 0.65
    nz.inputs["Distortion"].default_value = 0.4
    nt.links.new(tc.outputs["Generated"], nz.inputs["Vector"])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[1].default_value = 0.5; mr.inputs[2].default_value = 0.68
    nt.links.new(nz.outputs["Fac"], mr.inputs[0]); nt.links.new(mr.outputs[0], b.inputs["Alpha"])
    return m
bpy.ops.mesh.primitive_uv_sphere_add(segments=256, ring_count=128, radius=R_E*1.0015, location=earth_c)
clouds = bpy.context.object; clouds.data.materials.append(cloud_mat())
for p in clouds.data.polygons: p.use_smooth = True
def atmo_mat():
    m = bpy.data.materials.new("atmo"); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL': nt.nodes.remove(n)
    out = nt.nodes["Material Output"]
    lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.35
    pw = nt.nodes.new("ShaderNodeMath"); pw.operation = 'POWER'; pw.inputs[1].default_value = 3.0
    nt.links.new(lw.outputs["Facing"], pw.inputs[0])
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (0.25, 0.5, 1.0, 1)
    st = nt.nodes.new("ShaderNodeMath"); st.operation = 'MULTIPLY'; st.inputs[1].default_value = 2.2
    nt.links.new(pw.outputs[0], st.inputs[0]); nt.links.new(st.outputs[0], em.inputs["Strength"])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent"); add = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(tr.outputs[0], add.inputs[0]); nt.links.new(em.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs["Surface"])
    return m
bpy.ops.mesh.primitive_uv_sphere_add(segments=256, ring_count=128, radius=R_E*1.012, location=earth_c)
atmo = bpy.context.object; atmo.data.materials.append(atmo_mat())
for p in atmo.data.polygons: p.use_smooth = True
atmo.visible_shadow = False; clouds.visible_shadow = True

# ------------------------------------------------------------------ lighting
wo = bpy.data.worlds.new("w"); sc.world = wo; wo.use_nodes = True
wo.node_tree.nodes["Background"].inputs[0].default_value = (0, 0, 0, 1)
sun_d = bpy.data.lights.new("sun", 'SUN'); sun_d.angle = math.radians(0.53); sun_d.energy = 6.0
sun_d.color = (1.0, 0.97, 0.92)
sun = bpy.data.objects.new("sun", sun_d); coll.objects.link(sun)
sun.rotation_euler = Euler((math.radians(62), 0, math.radians(-35)))
# earthshine: soft bluish fill from below
es_d = bpy.data.lights.new("es", 'AREA'); es_d.size = 40; es_d.energy = 9000; es_d.color = (0.55, 0.7, 1.0)
es = bpy.data.objects.new("es", es_d); coll.objects.link(es); es.location = (0, 0, -30)
# visible sun disc (glow) far away in the sun direction
M_SUND = principled("sund", (1, 1, 1), 1.0, emit=(1.0, 0.95, 0.85), estr=60.0)
sdir = sun.rotation_euler.to_matrix() @ Vector((0, 0, 1))
bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=9000, location=sdir*1.0e6)
sdisc = bpy.context.object; sdisc.data.materials.append(M_SUND); sdisc.visible_shadow = False

# ------------------------------------------------------------------ camera
cam_d = bpy.data.cameras.new("cam"); cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 36; cam_d.clip_end = 5e6; cam_d.clip_start = 0.02
cam = bpy.data.objects.new("cam", cam_d); coll.objects.link(cam); sc.camera = cam
SH = [(rnd.uniform(-1, 1), rnd.uniform(-1, 1)) for _ in range(400)]
def shake(t, amp, rate=1.5):
    i = int(t*rate); f = t*rate - i; a, b_ = SH[i % 400], SH[(i+1) % 400]; f = f*f*(3-2*f)
    return (a[0]+(b_[0]-a[0])*f)*amp, (a[1]+(b_[1]-a[1])*f)*amp
def aim(loc, tgt, t, amp, roll=0.0):
    cam.location = loc
    q = (Vector(tgt)-Vector(loc)).to_track_quat('-Z', 'Y')
    e = q.to_euler()
    sx, sy = shake(t, amp); e.x += sx; e.z += sy
    cam.rotation_euler = e
    if roll:
        cam.rotation_mode = 'QUATERNION'
        from mathutils import Quaternion
        cam.rotation_quaternion = e.to_quaternion() @ Quaternion((0, 0, 1), roll)
        cam.rotation_mode = 'XYZ'

def pose(t):
    sat.rotation_euler = (math.radians(8), math.radians(-6), math.radians(20) + t*math.radians(1.6))
    clouds.rotation_euler = (0, 0, t*0.00002)
    cam_d.dof.use_dof = False
    if SHOT == "A":
        k = ease(t/6.8)
        cam_d.lens = lerp(55, 62, k)
        loc = (lerp(-26, -23, k), lerp(-14, -13, k), lerp(9, 8, k))
        tgt = (0, lerp(-0.5, 0.0, k), lerp(-2.5, -1.8, k))
        aim(loc, tgt, t, math.radians(0.05))
    elif SHOT == "B":
        u = (t - 6.8)/8.4; k = ease(u)
        cam_d.lens = 40
        cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = 2.8
        # slide along the gold bus surface (world coords from the satellite's local frame)
        sat.rotation_euler = (math.radians(8), math.radians(-6), math.radians(20) + 6.8*math.radians(1.6))
        bpy.context.view_layer.update()
        M = sat.matrix_world
        loc = M @ Vector((lerp(0.9, -0.7, k), -2.35, lerp(1.75, 1.55, k)))
        tgt = M @ Vector((lerp(0.5, -0.45, k), -1.1, lerp(0.55, 0.0, k)))
        cam_d.dof.focus_distance = (Vector(tgt) - Vector(loc)).length
        aim(loc, tgt, t, math.radians(0.04))
    else:
        u = (t - 15.2)/13.2; k = ease(u)
        cam_d.lens = lerp(32, 40, k)
        ang = math.radians(lerp(-70, -20, k))
        rad = lerp(11, 17, k)
        loc = (rad*math.cos(ang), rad*math.sin(ang), lerp(2.0, 5.5, k))
        tgt = (0, 0, lerp(0.4, -1.6, k))
        aim(loc, tgt, t, math.radians(0.05))

# ------------------------------------------------------------------ render
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.cycles.samples = int(os.environ.get("SPP", "10")); sc.cycles.use_denoising = True; sc.cycles.use_adaptive_sampling = True
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 3; sc.cycles.transparent_max_bounces = 6
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.resolution_percentage = int(os.environ.get("PCT", "50"))
sc.render.use_persistent_data = True
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
sc.view_settings.exposure = float(os.environ.get("EXPO", "-0.5"))

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
        M = sat.matrix_world
        meta[i] = {"bus": screen(M @ Vector((0.3, -1.1, 0.3))), "panel": screen(M @ Vector((0, -5.3, 0.6))),
                   "dish": screen(M @ Vector((0.4, 0, 2.3)))}
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
