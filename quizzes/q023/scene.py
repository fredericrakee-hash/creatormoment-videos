import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import bpy, bmesh, math, json, sys, os, random
from mathutils import Vector, Euler
from bpy_extras.object_utils import world_to_camera_view

FPS = 30
RES = (1080, 1920)
OUT = os.environ.get("OUT", QDIR)
SHOT = "A"
SHOTS = {"A": (0.0, 4.2), "B": (4.2, 12.6), "C": (12.6, 21.0), "D": (21.0, 26.6)}

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

# ------------------------------------------------------------------ blended winglets (replace the flat plates)
for o in list(P.children):
    if "_wl" in o.name: o.hide_render = True
def wl_center(u):
    """u 0..1 along the winglet span -> (y, z, theta)"""
    R = 0.9; ub = 0.38
    if u < ub:
        th = (math.pi/2*0.93)*(u/ub)
        return 31.0 + R*math.sin(th), 1.0 + R*(1 - math.cos(th)), th
    th = math.pi/2*0.93
    y0, z0 = 31.0 + R*math.sin(th), 1.0 + R*(1 - math.cos(th))
    L = (u - ub)/(1 - ub)*2.2
    return y0 + L*math.cos(th), z0 + L*math.sin(th), th
def wl_chord(u):
    xl = lerp(-14.9, -18.3, u**0.8); xt = lerp(-17.5, -19.25, u)
    return xl, xt
WL_TIP = []
def blended_winglet(s):
    bm = bmesh.new(); NC = 28; rings = []
    for j in range(31):
        u = j/30
        y, z, th = wl_center(u); xl, xt = wl_chord(u); c = xl - xt
        ny, nz = -math.sin(th), math.cos(th)
        ring = []; lower = []
        for i in range(NC):
            w = 0.5*(1 - math.cos(math.pi*i/(NC - 1)))
            tt = 5*0.09*(0.2969*math.sqrt(w) - 0.126*w - 0.3516*w*w + 0.2843*w**3 - 0.1036*w**4)
            tt = max(tt, 0.002/c)
            ring.append((lerp(xl, xt, w), s*(y + ny*tt*c), z + nz*tt*c))
        for i in range(NC - 2, 0, -1):
            w = 0.5*(1 - math.cos(math.pi*i/(NC - 1)))
            tt = 5*0.09*(0.2969*math.sqrt(w) - 0.126*w - 0.3516*w*w + 0.2843*w**3 - 0.1036*w**4)
            tt = max(tt, 0.002/c)
            lower.append((lerp(xl, xt, w), s*(y - ny*tt*c), z - nz*tt*c))
        rings.append([bm.verts.new(v) for v in ring + lower])
    n = len(rings[0])
    for j in range(len(rings) - 1):
        for i in range(n):
            f = [rings[j][i], rings[j][(i+1) % n], rings[j+1][(i+1) % n], rings[j+1][i]]
            bm.faces.new(f if s > 0 else list(reversed(f)))
    bm.faces.new(list(reversed(rings[-1])) if s > 0 else rings[-1])
    me = bpy.data.meshes.new(f"bwl{s}"); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(f"bwl{s}", me); coll.objects.link(ob)
    ob.data.materials.append(bpy.data.materials["JET_tail"])
    for p in ob.data.polygons: p.use_smooth = True
    ob.parent = P
    y, z, th = wl_center(1.0); xl, xt = wl_chord(1.0)
    WL_TIP.append(Vector((xt + 0.1, s*y, z)))
for s in (1, -1):
    blended_winglet(s)
TIP = WL_TIP[0]
for o in list(P.children):
    if o.type == 'MESH' and o.data.materials and ("_nav" in o.data.materials[0].name or "_strobe" in o.data.materials[0].name):
        o.location = (o.location.x + 0.1, o.location.y*0.985, o.location.z - 0.05)
        o.scale = (0.45, 0.45, 0.45)
        if "_nav" in o.data.materials[0].name:
            o.data.materials[0].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 6

# ------------------------------------------------------------------ wingtip vortex (condensation spiral, shot C/D)
M_VX = bpy.data.materials.new("vortex"); M_VX.use_nodes = True; nt = M_VX.node_tree
for n_ in list(nt.nodes): nt.nodes.remove(n_)
ov = nt.nodes.new("ShaderNodeOutputMaterial"); dfv = nt.nodes.new("ShaderNodeBsdfDiffuse"); dfv.inputs["Color"].default_value = (0.95, 0.93, 0.92, 1)
trv = nt.nodes.new("ShaderNodeBsdfTransparent"); mxv = nt.nodes.new("ShaderNodeMixShader")
atv = nt.nodes.new("ShaderNodeAttribute"); atv.attribute_name = "fade"; atv.attribute_type = 'GEOMETRY'
tcv = nt.nodes.new("ShaderNodeTexCoord"); nzv = nt.nodes.new("ShaderNodeTexNoise"); nzv.inputs["Scale"].default_value = 1.6; nzv.inputs["Detail"].default_value = 6
nt.links.new(tcv.outputs["Object"], nzv.inputs["Vector"])
mrv = nt.nodes.new("ShaderNodeMapRange"); mrv.inputs[1].default_value = 0.35; mrv.inputs[2].default_value = 0.7
nt.links.new(nzv.outputs["Fac"], mrv.inputs[0])
lwv = nt.nodes.new("ShaderNodeLayerWeight"); lwv.inputs["Blend"].default_value = 0.5
inv = nt.nodes.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
nt.links.new(lwv.outputs["Facing"], inv.inputs[1])
m1 = nt.nodes.new("ShaderNodeMath"); m1.operation = 'MULTIPLY'; nt.links.new(mrv.outputs[0], m1.inputs[0]); nt.links.new(atv.outputs["Fac"], m1.inputs[1])
m2 = nt.nodes.new("ShaderNodeMath"); m2.operation = 'MULTIPLY'; nt.links.new(m1.outputs[0], m2.inputs[0]); nt.links.new(inv.outputs[0], m2.inputs[1])
VXGAIN = nt.nodes.new("ShaderNodeMath"); VXGAIN.operation = 'MULTIPLY'; VXGAIN.inputs[1].default_value = 0.85
nt.links.new(m2.outputs[0], VXGAIN.inputs[0])
nt.links.new(VXGAIN.outputs[0], mxv.inputs[0]); nt.links.new(trv.outputs[0], mxv.inputs[1]); nt.links.new(dfv.outputs[0], mxv.inputs[2])
nt.links.new(mxv.outputs[0], ov.inputs["Surface"])
M_VX.blend_method = 'BLEND' if hasattr(M_VX, "blend_method") else None
VX = []
def vortex_strand(s, phase, LEN=90.0):
    bm = bmesh.new(); fl = bm.verts.layers.float.new("fade"); n = 10; prev = None; N = 260
    for k in range(N + 1):
        u = k/N; d = LEN*u
        hr = lerp(0.25, 2.2, u**0.5)            # helix radius grows downstream
        ang = phase + 1.6*math.log(1 + d*0.8)        # tight twist near the tip, loosening further back
        c = Vector((-d, hr*math.cos(ang), hr*math.sin(ang)))
        tr = lerp(0.05, 0.55, u**0.7)            # strand thickness
        f = min(1.0, u*25)*(1 - u)**1.3
        ring = []
        for i in range(n):
            a = 2*math.pi*i/n
            v = bm.verts.new(c + Vector((0, tr*math.cos(a), tr*math.sin(a)))); v[fl] = f; ring.append(v)
        if prev:
            for i in range(n):
                bm.faces.new([prev[i], prev[(i+1) % n], ring[(i+1) % n], ring[i]])
        prev = ring
    me = bpy.data.meshes.new("vx"); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new("vx", me); coll.objects.link(ob); ob.data.materials.append(M_VX)
    for p in ob.data.polygons: p.use_smooth = True
    ob.location = WL_TIP[0 if s > 0 else 1]; ob.hide_render = True
    VX.append((ob, s))
for s in (1, -1):
    for ph in (0.0, 2.1, 4.2):
        vortex_strand(s, ph)

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
    vx_on = SHOT in ("C", "D")
    for ob, s in VX:
        ob.hide_render = not vx_on
        ob.rotation_euler = (-s*t*2.2, 0, 0)          # strands spin around the vortex core
    VXGAIN.inputs[1].default_value = 0.85 if SHOT == "C" else 0.55
    set_sun(2.5, 30, 3.8, (1.0, 0.62, 0.38), 0.22)
    if SHOT == "A":
        k = ease(t/4.2)
        cam_d.lens = lerp(25, 29, k)
        loc = (lerp(-80, -68, k), lerp(62, 56, k), lerp(15, 12, k))
        tgt = (lerp(2, -4, k), lerp(4, 10, k), 0.5)
        aim(loc, tgt, t, math.radians(0.15))
    elif SHOT == "B":
        k = ease((t - 4.2)/8.4)
        cam_d.lens = lerp(26, 30, k)
        loc = (lerp(-11.5, -12.5, k), lerp(25.5, 26.6, k), lerp(2.9, 2.6, k))
        tgt = (-17.2, 31.7, lerp(2.0, 2.4, k))
        aim(loc, tgt, t, math.radians(0.18), 4.0)
    elif SHOT == "C":
        k = ease((t - 12.6)/8.4)
        cam_d.lens = lerp(26, 30, k)
        loc = (lerp(-40, -37, k), lerp(49, 48, k), lerp(-3.0, -2.2, k))
        tgt = (lerp(-26, -23, k), 31.8, 3.4)
        aim(loc, tgt, t, math.radians(0.2), 3.0)
    else:
        k = ease((t - 21.0)/5.6)
        cam_d.lens = lerp(34, 38, k)
        loc = (lerp(105, 98, k), lerp(64, 58, k), lerp(-12, -10, k))
        tgt = (-8, 4, 1.5)
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
        meta[i] = {"tip": screen(TIP), "wl": screen(Vector((-17.6, 31.9, 2.6))), "vx": screen(TIP + Vector((-12, 0, 0)))}
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
