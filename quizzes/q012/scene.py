import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import bpy, bmesh, math, json, sys, os, random
from mathutils import Vector, Euler
from bpy_extras.object_utils import world_to_camera_view

FPS = 30
RES = (1080, 1920)
OUT = os.environ.get("OUT", QDIR)
SHOT = "A"
SHOTS = {"A": (0.0, 4.2), "B": (4.2, 12.6), "C": (12.6, 21.0), "D": (21.0, 25.9)}

def ease(x):
    x = max(0.0, min(1.0, x)); return x*x*(3-2*x)
def lerp(a, b, k): return a + (b-a)*k

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; coll = sc.collection
rnd = random.Random(31)
exec(open(os.path.join(QDIR, "lib_air.py")).read())

P = make_airliner("JET", (0.55, 0.08, 0.06))

# ------------------------------------------------------------------ proper airfoil wings (replace the flat plates)
def wing_mat():
    m = bpy.data.materials.new("wingpanel"); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Metallic"].default_value = 0.1; b.inputs["Roughness"].default_value = 0.42
    b.inputs["Coat Weight"].default_value = 0.2; b.inputs["Coat Roughness"].default_value = 0.1
    tc = nt.nodes.new("ShaderNodeTexCoord")
    br = nt.nodes.new("ShaderNodeTexBrick"); br.inputs["Scale"].default_value = 1.1; br.inputs["Mortar Size"].default_value = 0.004
    br.inputs["Color1"].default_value = (0.60, 0.62, 0.65, 1); br.inputs["Color2"].default_value = (0.56, 0.58, 0.61, 1)
    br.inputs["Mortar"].default_value = (0.5, 0.51, 0.53, 1); br.offset = 0.5; br.squash = 1.0
    nt.links.new(tc.outputs["Object"], br.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.8; nz.inputs["Detail"].default_value = 8
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs["Factor"].default_value = 0.15
    nt.links.new(br.outputs["Color"], mix.inputs[6]); nt.links.new(nz.outputs["Fac"], mix.inputs[7])
    nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.25; bump.inputs["Distance"].default_value = 0.01
    nt.links.new(br.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m
M_WING = wing_mat()
def te(y):   # trailing edge point of the right wing (y>0) at span y
    k = (y - 2.2)/28.8
    return Vector((lerp(-5.5, -17.5, k), y, lerp(-1.4, 1.0, k)))
def le(y):
    k = (y - 2.2)/28.8
    return Vector((lerp(7.0, -14.9, k), y, lerp(-1.4, 1.0, k)))
def airfoil_wing(s):
    bm = bmesh.new(); NC = 36; rings = []
    ys = [2.2 + 28.8*j/24 for j in range(25)]
    for y in ys:
        L, T = le(y), te(y); c = (L - T).length
        tc_ = lerp(0.12, 0.09, (y - 2.2)/28.8)
        ring = []
        for i in range(NC):
            u = 0.5*(1 - math.cos(math.pi*i/(NC - 1)))       # 0 = LE, 1 = TE
            th = 5*tc_*(0.2969*math.sqrt(u) - 0.126*u - 0.3516*u*u + 0.2843*u**3 - 0.1036*u**4)
            th = max(th, 0.0012/c)
            p = L + (T - L)*u
            ring.append((p.x, s*y, p.z + th*c + 0.012*c*math.sin(math.pi*u)))
        lower = []
        for i in range(NC - 2, 0, -1):
            u = 0.5*(1 - math.cos(math.pi*i/(NC - 1)))
            th = 5*tc_*(0.2969*math.sqrt(u) - 0.126*u - 0.3516*u*u + 0.2843*u**3 - 0.1036*u**4)
            th = max(th, 0.0012/c)
            p = L + (T - L)*u
            lower.append((p.x, s*y, p.z - th*c*0.85 + 0.012*c*math.sin(math.pi*u)))
        rings.append([bm.verts.new(v) for v in ring + lower])
    n = len(rings[0])
    for j in range(len(rings) - 1):
        for i in range(n):
            f = [rings[j][i], rings[j][(i+1) % n], rings[j+1][(i+1) % n], rings[j+1][i]]
            bm.faces.new(f if s > 0 else list(reversed(f)))
    bm.faces.new(rings[-1] if s > 0 else list(reversed(rings[-1])))
    me = bpy.data.meshes.new(f"afw{s}"); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(f"afw{s}", me); coll.objects.link(ob); ob.data.materials.append(M_WING)
    for p in ob.data.polygons: p.use_smooth = True
    ob.parent = P
    return ob
for o in list(P.children):
    if o.active_material and o.active_material.name == "JET_wing": o.hide_render = True
for s in (1, -1):
    airfoil_wing(s)

# ------------------------------------------------------------------ static wicks
M_WICK = principled("wick", (0.015, 0.015, 0.017), 0.45)
M_WBASE = principled("wbase", (0.35, 0.36, 0.38), 0.3, 0.9)
def wick(p, d=Vector((-1, 0.06, 0)), L=0.34):
    d = d.normalized(); q = d.to_track_quat('Z', 'Y').to_euler()
    bpy.ops.mesh.primitive_cube_add(size=1, location=p + d*0.03)
    b = bpy.context.object; b.scale = (0.03, 0.09, 0.022); b.rotation_euler = (0, 0, math.atan2(d.y, d.x) + math.pi/2)
    b.data.materials.append(M_WBASE); b.parent = P
    bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=0.011, radius2=0.006, depth=L, location=p + d*(0.05 + L/2))
    r = bpy.context.object; r.rotation_euler = q; r.data.materials.append(M_WICK); r.parent = P
    for pp in r.data.polygons: pp.use_smooth = True
    tip = p + d*(0.05 + L)
    for k in range(7):
        a = 2*math.pi*k/7
        off = Vector((0, math.cos(a), math.sin(a)))*0.006
        dd = (d + Vector((0, math.cos(a), math.sin(a)))*0.35).normalized()
        bpy.ops.mesh.primitive_cylinder_add(vertices=4, radius=0.0012, depth=0.03, location=tip + off + dd*0.015)
        f = bpy.context.object; f.rotation_euler = dd.to_track_quat('Z', 'Y').to_euler(); f.data.materials.append(M_WICK); f.parent = P
WICK_Y = [20.5, 23.2, 25.9, 28.6, 30.7]
for s in (1, -1):
    for y in WICK_Y:
        p = te(y); wick(Vector((p.x + 0.02, s*y, p.z)), Vector((-1, s*0.05, 0)))
    for k in (0.35, 0.75):          # winglet trailing edge
        p = Vector((lerp(-17.5, -19.0, k), s*lerp(31.0, 31.4, k), lerp(1.0, 3.6, k)))
        wick(p, Vector((-1, 0, 0.15)), 0.3)
    for k in (0.7, 0.95):           # horizontal stabiliser trailing edge
        p = Vector((lerp(-27.5, -31.5, k) - 0.05, s*lerp(1.0, 10.5, k), lerp(1.3, 2.4, k)))
        wick(p, Vector((-1, s*0.05, 0)), 0.3)
for k in (0.6, 0.85):               # fin / rudder trailing edge
    p = Vector((lerp(-27.5, -31.5, k) - 0.2, 0, lerp(1.8, 13.5, k)))
    wick(p, Vector((-1, 0, -0.1)), 0.3)

# ------------------------------------------------------------------ rain streaks (C)
M_RAIN = bpy.data.materials.new("rain"); M_RAIN.use_nodes = True; nt = M_RAIN.node_tree
br_ = nt.nodes["Principled BSDF"]; br_.inputs["Base Color"].default_value = (0.85, 0.88, 0.92, 1); br_.inputs["Roughness"].default_value = 0.3
trr = nt.nodes.new("ShaderNodeBsdfTransparent"); mxr = nt.nodes.new("ShaderNodeMixShader"); mxr.inputs[0].default_value = 0.3
nt.links.new(br_.outputs[0], mxr.inputs[1]); nt.links.new(trr.outputs[0], mxr.inputs[2])
nt.links.new(mxr.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
RAIN = []
for k in range(260):
    bpy.ops.mesh.primitive_cylinder_add(vertices=4, radius=0.004, depth=0.9, location=(0, 0, 0), rotation=(0, math.pi/2 - 0.08, 0))
    o = bpy.context.object; o.data.materials.append(M_RAIN); o.hide_render = True
    RAIN.append((o, rnd.uniform(0, 12), rnd.uniform(-1.2, 1.6), rnd.uniform(-0.9, 1.0)))
# cloud wisps rushing past (C): soft noise cards
M_WISP = bpy.data.materials.new("wisp"); M_WISP.use_nodes = True; nt = M_WISP.node_tree
for n_ in list(nt.nodes): nt.nodes.remove(n_)
ow = nt.nodes.new("ShaderNodeOutputMaterial"); dfw = nt.nodes.new("ShaderNodeBsdfDiffuse"); dfw.inputs["Color"].default_value = (0.8, 0.82, 0.86, 1)
trw = nt.nodes.new("ShaderNodeBsdfTransparent"); mxw = nt.nodes.new("ShaderNodeMixShader")
tcw = nt.nodes.new("ShaderNodeTexCoord"); nzw = nt.nodes.new("ShaderNodeTexNoise"); nzw.inputs["Scale"].default_value = 2.0; nzw.inputs["Detail"].default_value = 6
nt.links.new(tcw.outputs["Generated"], nzw.inputs["Vector"])
grw = nt.nodes.new("ShaderNodeTexGradient"); grw.gradient_type = 'SPHERICAL'
mpw = nt.nodes.new("ShaderNodeMapping"); mpw.inputs["Location"].default_value = (-0.5, -0.5, 0); mpw.inputs["Scale"].default_value = (2, 2, 2)
nt.links.new(tcw.outputs["Generated"], mpw.inputs["Vector"]); nt.links.new(mpw.outputs[0], grw.inputs["Vector"])
mlw = nt.nodes.new("ShaderNodeMath"); mlw.operation = 'MULTIPLY'; nt.links.new(nzw.outputs["Fac"], mlw.inputs[0]); nt.links.new(grw.outputs["Fac"], mlw.inputs[1])
mrw = nt.nodes.new("ShaderNodeMapRange"); mrw.inputs[1].default_value = 0.1; mrw.inputs[2].default_value = 0.5; mrw.inputs[4].default_value = 0.85
nt.links.new(mlw.outputs[0], mrw.inputs[0])
nt.links.new(mrw.outputs[0], mxw.inputs[0]); nt.links.new(trw.outputs[0], mxw.inputs[1]); nt.links.new(dfw.outputs[0], mxw.inputs[2])
nt.links.new(mxw.outputs[0], ow.inputs["Surface"])
WISPS = []
for k in range(10):
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
    o = bpy.context.object; o.data.materials.append(M_WISP); o.hide_render = True
    WISPS.append((o, rnd.uniform(0, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(6, 14)))

# ------------------------------------------------------------------ world: sky mixed with cloud-grey
wo = bpy.data.worlds.new("w"); sc.world = wo; wo.use_nodes = True
bg = wo.node_tree.nodes["Background"]
sky = wo.node_tree.nodes.new("ShaderNodeTexSky"); sky.sky_type = 'MULTIPLE_SCATTERING'
fogmix = wo.node_tree.nodes.new("ShaderNodeMix"); fogmix.data_type = 'RGBA'
wo.node_tree.links.new(sky.outputs[0], fogmix.inputs[6]); fogmix.inputs[7].default_value = (0.42, 0.45, 0.5, 1)
wo.node_tree.links.new(fogmix.outputs[2], bg.inputs[0])
sun_d = bpy.data.lights.new("sun", 'SUN'); sun_d.angle = math.radians(0.6)
sun = bpy.data.objects.new("sun", sun_d); coll.objects.link(sun)
def set_sun(el, rot, energy, color, bgs, fog=0.0):
    sky.sun_elevation = math.radians(el); sky.sun_rotation = math.radians(rot); sky.altitude = 1500
    sky.aerosol_density = 2.2; sky.sun_intensity = 0.5; bg.inputs[1].default_value = bgs
    fogmix.inputs["Factor"].default_value = fog
    sun_d.energy = energy; sun_d.color = color; sun.rotation_euler = Euler((math.radians(90 - el), 0, math.radians(rot + 90)))
deck = cloud_deck(-900) if False else None
bpy.ops.mesh.primitive_plane_add(size=600000, location=(0, 0, -2500))
deck = bpy.context.object
cm = bpy.data.materials.new("clouds"); cm.use_nodes = True; nt = cm.node_tree
b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 1.0
tc = nt.nodes.new("ShaderNodeTexCoord")
n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 0.00025; n1.inputs["Detail"].default_value = 14
n1.inputs["Roughness"].default_value = 0.7; n1.inputs["Distortion"].default_value = 0.6
nt.links.new(tc.outputs["Object"], n1.inputs["Vector"])
ramp = nt.nodes.new("ShaderNodeValToRGB"); cr = ramp.color_ramp
cr.elements[0].position = 0.42; cr.elements[0].color = (0.16, 0.18, 0.26, 1)
cr.elements[1].position = 0.56; cr.elements[1].color = (1.3, 1.2, 1.1, 1)
nt.links.new(n1.outputs["Fac"], ramp.inputs[0]); nt.links.new(ramp.outputs[0], b.inputs["Base Color"])
bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 1.0; bump.inputs["Distance"].default_value = 800
nt.links.new(n1.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
deck.data.materials.append(cm)

cam_d = bpy.data.cameras.new("cam"); cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 36; cam_d.clip_end = 200000; cam_d.clip_start = 0.02
cam = bpy.data.objects.new("cam", cam_d); coll.objects.link(cam); sc.camera = cam
SH = [(rnd.uniform(-1, 1), rnd.uniform(-1, 1)) for _ in range(400)]
def shake(t, amp, rate=2.5):
    i = int(t*rate); f = t*rate - i; a, b_ = SH[i % 400], SH[(i+1) % 400]; f = f*f*(3-2*f)
    return (a[0]+(b_[0]-a[0])*f)*amp, (a[1]+(b_[1]-a[1])*f)*amp
def aim(loc, tgt, t, amp, rate=2.5):
    cam.location = loc
    e = (Vector(tgt)-Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sx, sy = shake(t, amp, rate); e.x += sx; e.z += sy; cam.rotation_euler = e
def strobes(t):
    st = t % 1.2; on_s = st < 0.05 or 0.12 < st < 0.17; on_b = (t % 1.0) < 0.12
    for o in P.children:
        if "strobe" in o.name: o.active_material.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 600 if on_s else 0
        if "beacon" in o.name: o.active_material.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 120 if on_b else 2

V = 230.0   # airspeed m/s -> scenery moves -X
def pose(t):
    strobes(t)
    deck.location = (-V*t % 20000, 0, -2500)
    deck.hide_render = SHOT == "C"
    rain_on = SHOT == "C"; wisp_on = SHOT == "C"
    for o, ph, a, bb in RAIN: o.hide_render = not rain_on
    for o, *_ in WISPS: o.hide_render = not wisp_on
    if SHOT == "A":
        set_sun(2.5, 30, 3.8, (1.0, 0.62, 0.38), 0.22)
        k = ease(t/4.2)
        cam_d.lens = lerp(40, 52, k)
        loc = (lerp(-75, -62, k), lerp(58, 50, k), lerp(14, 12, k))
        tgt = (lerp(-6, -12, k), lerp(8, 16, k), 0)
        aim(loc, tgt, t, math.radians(0.15))
    elif SHOT == "B":
        set_sun(2.5, 30, 3.8, (1.0, 0.62, 0.38), 0.22)
        k = ease((t - 4.2)/8.4)
        p = te(lerp(21.0, 21.8, k)); q = te(lerp(25.0, 25.6, k))
        cam_d.lens = lerp(24, 27, k)
        loc = (p.x + 0.1, p.y, p.z + 1.35)
        tgt = (q.x - 0.25, q.y, q.z - 0.2)
        aim(loc, tgt, t, math.radians(0.18), 4.0)
    elif SHOT == "C":
        set_sun(18, 30, 0.5, (0.9, 0.92, 1.0), 1.0, fog=0.92)
        k = ease((t - 12.6)/8.4)
        p = te(25.9)
        cam_d.lens = lerp(34, 40, k)
        loc = (p.x - lerp(0.75, 0.62, k), p.y - 0.42, p.z + 0.2)
        tgt = (p.x - 0.22, p.y + 0.05, p.z - 0.01)
        aim(loc, tgt, t, math.radians(0.35), 6.0)
        c = Vector(loc)
        for o, ph, a, bb in RAIN:
            u = ((ph - t*9.0) % 12.0) - 6.0       # metres along -X relative to camera
            o.location = (c.x + 1.2 + u, c.y + 0.25 + a*1.0, c.z + bb*0.8)
        for o, ph, a, bb, sz in WISPS:
            u = ((ph*60 - t*45.0) % 60.0) - 20.0
            o.location = (c.x + u, c.y + 6 + a*5, c.z + bb*3); o.scale = (sz, sz, 1)
            o.rotation_euler = (math.pi/2, 0, 0)
    else:
        set_sun(2.5, 30, 3.8, (1.0, 0.62, 0.38), 0.22, fog=0.3*(1 - ease((t - 21.0)/2.0)))
        k = ease((t - 21.0)/4.6)
        cam_d.lens = lerp(30, 34, k)
        loc = (lerp(-62, -58, k), lerp(-24, -20, k), lerp(-4, -2, k))
        tgt = (-22, 2, 3)
        aim(loc, tgt, t, math.radians(0.15))

# ------------------------------------------------------------------ render
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.cycles.samples = int(os.environ.get("SPP", "10")); sc.cycles.use_denoising = True; sc.cycles.use_adaptive_sampling = True
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transparent_max_bounces = 6
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.resolution_percentage = int(os.environ.get("PCT", "50"))
sc.render.use_persistent_data = True
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
sc.view_settings.exposure = float(os.environ.get("EXPO", "0.0"))

def screen(p):
    v = world_to_camera_view(sc, cam, Vector(p)); return (v.x*RES[0], (1-v.y)*RES[1], v.z)
def shot_for(t):
    for k, (a, b) in SHOTS.items():
        if a <= t < b: return k
    return "D"
mode = sys.argv[sys.argv.index("--")+1] if "--" in sys.argv else "frames"
END = SHOTS["D"][1]
if mode == "test":
    for t in [float(x) for x in os.environ.get("TT", "3").split(",")]:
        SHOT = shot_for(t); pose(t); bpy.context.view_layer.update()
        sc.render.filepath = f"{OUT}/test_{t}.png"; bpy.ops.render.render(write_still=True)
elif mode == "meta":
    meta = {}
    for i in range(0, int(END*FPS)):
        t = i/FPS; SHOT = shot_for(t); pose(t); bpy.context.view_layer.update()
        ws = [screen(te(y) + Vector((-0.3, 0, 0))) for y in WICK_Y]
        meta[i] = {"wicks": ws, "w26": screen(te(25.9) + Vector((-0.25, 0, 0))), "wing": screen(te(26) + Vector((3, 0, 0))),
                   "tail": screen((-31, 0, 12))}
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
