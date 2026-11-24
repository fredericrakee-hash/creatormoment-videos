import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import bpy, bmesh, math, json, sys, os, random
from mathutils import Vector, Euler, noise
from bpy_extras.object_utils import world_to_camera_view

FPS = 30
RES = (1080, 1920)
OUT = os.environ.get("OUT", QDIR)
SHOT = "A"
SHOTS = {"A": (0.0, 3.4), "B": (3.4, 12.9), "C": (12.9, 20.6), "D": (20.6, 32.2)}
END = SHOTS["D"][1]
if "frames" in sys.argv:
    _st = int(os.environ.get("STEP", "2")); _a = int(os.environ.get("IFROM", "0")); _b = int(os.environ.get("ITO", int(END*FPS)))
    if all(os.path.exists(f"{OUT}/frames/f{i:04d}.png") for i in range(_a, _b, _st)): sys.exit(0)

def ease(x):
    x = max(0.0, min(1.0, x)); return x*x*(3-2*x)
def lerp(a, b, k): return a + (b-a)*k
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; coll = sc.collection
rnd = random.Random(26)
bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
exec(open(os.path.join(QDIR, "lib_air.py")).read())

GZ = -4.35          # apron level (fuselage axis at z = 0)
JET = make_airliner("JET", (0.08, 0.22, 0.45), engines=False)

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
def lathe(name, prof, mat, parent=None, seg=72, cap=False):
    """profile [(x, r), ...] revolved around the X axis"""
    bm = bmesh.new(); rings = []
    for x, r in prof:
        rings.append([bm.verts.new((x, r*math.cos(2*math.pi*i/seg), r*math.sin(2*math.pi*i/seg))) for i in range(seg)])
    for a, b in zip(rings[:-1], rings[1:]):
        for i in range(seg): bm.faces.new([a[i], a[(i+1) % seg], b[(i+1) % seg], b[i]])
    return mesh_obj(name, bm, mat, True, parent)

# ------------------------------------------------------------------ materials
M_NAC = principled("nacelle", (0.80, 0.81, 0.83), 0.3, coat=0.5)
M_LIP = principled("lip", (0.75, 0.76, 0.78), 0.12, 1.0)
M_DUCT = principled("duct", (0.10, 0.105, 0.11), 0.55, 0.3)
M_BLADE = principled("blade", (0.38, 0.39, 0.42), 0.28, 1.0)
M_DARK = principled("darkcore", (0.012, 0.012, 0.014), 0.7)
M_RUB = principled("rubber", (0.02, 0.02, 0.02), 0.85)
M_STRUT = principled("strut", (0.55, 0.56, 0.58), 0.25, 0.9)
def spinner_mat():
    """glossy black cone with ONE white spiral arm (object coords, axis = local +X)"""
    m = bpy.data.materials.new("spinner"); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.22; b.inputs["Coat Weight"].default_value = 0.8
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep.inputs[0])
    at = nt.nodes.new("ShaderNodeMath"); at.operation = 'ARCTAN2'; nt.links.new(sep.outputs["Z"], at.inputs[0]); nt.links.new(sep.outputs["Y"], at.inputs[1])
    a1 = nt.nodes.new("ShaderNodeMath"); a1.operation = 'DIVIDE'; a1.inputs[1].default_value = 2*math.pi; nt.links.new(at.outputs[0], a1.inputs[0])
    # distance from the tip along the surface ~ use x (tip at x = SP_LEN, base at 0)
    xs = nt.nodes.new("ShaderNodeMath"); xs.operation = 'MULTIPLY'; xs.inputs[1].default_value = 1.35; nt.links.new(sep.outputs["X"], xs.inputs[0])
    ad = nt.nodes.new("ShaderNodeMath"); ad.operation = 'ADD'; nt.links.new(a1.outputs[0], ad.inputs[0]); nt.links.new(xs.outputs[0], ad.inputs[1])
    fr = nt.nodes.new("ShaderNodeMath"); fr.operation = 'FRACT'; nt.links.new(ad.outputs[0], fr.inputs[0])
    # band width grows towards the base (like the real decal)
    wd = nt.nodes.new("ShaderNodeMapRange"); wd.inputs[1].default_value = 0.0; wd.inputs[2].default_value = 0.55; wd.inputs[3].default_value = 0.30; wd.inputs[4].default_value = 0.13
    nt.links.new(sep.outputs["X"], wd.inputs[0])
    lt = nt.nodes.new("ShaderNodeMath"); lt.operation = 'LESS_THAN'; nt.links.new(fr.outputs[0], lt.inputs[0]); nt.links.new(wd.outputs[0], lt.inputs[1])
    # white tip dot
    tip = nt.nodes.new("ShaderNodeMath"); tip.operation = 'GREATER_THAN'; tip.inputs[1].default_value = 0.53; nt.links.new(sep.outputs["X"], tip.inputs[0])
    mx_ = nt.nodes.new("ShaderNodeMath"); mx_.operation = 'MAXIMUM'; nt.links.new(lt.outputs[0], mx_.inputs[0]); nt.links.new(tip.outputs[0], mx_.inputs[1])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'
    mix.inputs[6].default_value = (0.012, 0.012, 0.014, 1); mix.inputs[7].default_value = (0.85, 0.86, 0.86, 1)
    nt.links.new(mx_.outputs[0], mix.inputs[0]); nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    return m
M_SPIN = spinner_mat()

# ------------------------------------------------------------------ detailed turbofan (axis along +X, intake at the front)
FANS = []
def engine(name, ex, ey, ez):
    root = bpy.data.objects.new(name, None); coll.objects.link(root); root.location = (ex, ey, ez); root.parent = JET
    R = 1.12; L = 4.8
    # outer cowl (lip at x = +2.4) and inner duct
    outer = [(2.42, 1.02), (2.38, 1.08), (2.25, 1.13), (1.8, 1.17), (0.5, 1.18), (-0.8, 1.14), (-1.9, 1.02), (-2.4, 0.92)]
    lathe(name + "cowl", outer, M_NAC, root)
    lip = [(2.42, 1.02), (2.43, 0.99), (2.40, 0.96), (2.3, 0.94)]
    lathe(name + "lip", lip, M_LIP, root)
    inner = [(2.3, 0.94), (1.9, 0.935), (1.5, 0.93), (0.2, 0.9), (-1.0, 0.8)]
    lathe(name + "duct", inner, M_DUCT, root)
    # dark core behind the fan
    cyl(name + "core", (1.05, 0, 0), 0.92, 0.05, "x", M_DARK, root, 48)
    # exhaust nozzle + plug
    lathe(name + "noz", [(-2.4, 0.92), (-2.9, 0.78), (-3.1, 0.7)], M_LIP, root)
    lathe(name + "plug", [(-2.6, 0.55), (-3.2, 0.45), (-3.9, 0.15), (-4.0, 0.02)], M_LIP, root)
    # rotating group: fan + spinner
    rot = bpy.data.objects.new(name + "rot", None); coll.objects.link(rot); rot.parent = root; rot.location = (1.55, 0, 0)
    NB = 24
    bm = bmesh.new()
    for k in range(NB):
        a0 = 2*math.pi*k/NB
        prev = None
        for j in range(7):
            r = 0.30 + (0.915 - 0.30)*j/6
            tw = math.radians(lerp(58, 22, j/6))        # blade twist
            chord = lerp(0.20, 0.30, j/6)
            sweep = 0.06*(j/6)**2
            ca, sa = math.cos(a0 + sweep*1.6), math.sin(a0 + sweep*1.6)
            pts = []
            for s_ in (-0.5, 0.5):
                dx = s_*chord*math.cos(tw); dt = s_*chord*math.sin(tw)
                # tangential offset dt along the circle direction
                y = r*ca - dt*sa; z = r*sa + dt*ca
                pts.append(bm.verts.new((dx - sweep, y, z)))
            if prev:
                bm.faces.new([prev[0], prev[1], pts[1], pts[0]])
            prev = pts
    o = mesh_obj(name + "fan", bm, M_BLADE, True, rot)
    sol = o.modifiers.new("s", 'SOLIDIFY'); sol.thickness = 0.012
    cyl(name + "hub", (-0.05, 0, 0), 0.31, 0.3, "x", M_DUCT, rot, 48)
    # spinner (ogive, tip pointing forward) — material uses local coords: base x=0, tip x≈0.56
    prof = [(0.0, 0.315)] + [(0.56*u, 0.315*math.sqrt(max(0.0, 1 - u**1.6))) for u in (0.15, 0.3, 0.45, 0.6, 0.72, 0.82, 0.9, 0.95, 0.985, 1.0)]
    sp = lathe(name + "spin", prof, M_SPIN, rot, seg=96)
    sp.location = (0.08, 0, 0)
    # pylon to the wing
    box(name + "pyl", -2.6, 1.2, -0.15, 0.15, 1.05, 1.75, M_NAC, root, 0.07)
    FANS.append(rot)
    return root
ENG = [engine("engL", 2.4, 9.5, -2.6), engine("engR", 2.4, -9.5, -2.6)]

# landing gear (simple but believable)
def gear(x, y, n_wheels, zt=-1.6):
    zc = GZ + 0.56
    cyl(f"g{x}{y}", (x, y, (zt + zc)/2), 0.11, zt - zc, "z", M_STRUT, JET, 16)
    for k in range(n_wheels):
        dx = (k // 2)*1.3 - (0.65 if n_wheels == 4 else 0); dy = (0.42 if k % 2 else -0.42)
        cyl(f"t{x}{y}{k}", (x + dx, y + dy, zc), 0.56, 0.36, "y", M_RUB, JET, 32)
        cyl(f"h{x}{y}{k}", (x + dx, y + dy*1.45, zc), 0.30, 0.02, "y", M_STRUT, JET, 24)
for s in (1, -1): gear(-2.0, s*4.2, 2)
gear(24.5, 0, 2, zt=-2.0)

# ------------------------------------------------------------------ apron, terminal, props
HAZE = (1.0, 0.70, 0.48)
def apron_mat():
    m = bpy.data.materials.new("apron"); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.75
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.6; nz.inputs["Detail"].default_value = 12
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    cr = nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (0.20, 0.20, 0.20, 1); cr.color_ramp.elements[1].color = (0.36, 0.35, 0.33, 1)
    nt.links.new(nz.outputs["Fac"], cr.inputs[0])
    # concrete slab joints every 5 m
    br = nt.nodes.new("ShaderNodeTexBrick"); br.inputs["Scale"].default_value = 0.2; br.inputs["Mortar Size"].default_value = 0.004
    br.offset = 0.0; br.inputs["Color1"].default_value = (1, 1, 1, 1); br.inputs["Color2"].default_value = (1, 1, 1, 1); br.inputs["Mortar"].default_value = (0.35, 0.35, 0.35, 1)
    br.inputs["Brick Width"].default_value = 1.0; br.inputs["Row Height"].default_value = 1.0
    nt.links.new(tc.outputs["Object"], br.inputs["Vector"])
    mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs[0].default_value = 1.0
    nt.links.new(cr.outputs[0], mul.inputs[6]); nt.links.new(br.outputs["Color"], mul.inputs[7])
    nt.links.new(mul.outputs[2], b.inputs["Base Color"])
    return m
bpy.ops.mesh.primitive_plane_add(size=6000, location=(0, 0, GZ)); ap = bpy.context.object; ap.data.materials.append(apron_mat())
M_YEL = principled("yellow", (0.75, 0.52, 0.04), 0.6)
box("lead", -400, 400, -0.12, 0.12, GZ, GZ + 0.004, M_YEL, bev=0)      # lead-in line under the fuselage
box("stop", 22.0, 22.25, -6, 6, GZ, GZ + 0.004, M_YEL, bev=0)
M_RED = principled("redline", (0.6, 0.05, 0.03), 0.6)
for s in (1, -1):
    box(f"ring{s}", -30, 60, s*22 - 0.1, s*22 + 0.1, GZ, GZ + 0.004, M_RED, bev=0)
# terminal building far behind (+X / -Y side), glass front with warm lights
M_TERM = principled("term", (0.30, 0.31, 0.33), 0.4, 0.3)
M_TGL = principled("tglass", (0.02, 0.03, 0.04), 0.05, coat=1.0, emit=(1.0, 0.75, 0.45), estr=1.5)
box("terminal", 60, 95, -260, 160, GZ, GZ + 18, M_TERM, bev=0.2)
box("tglass", 59.8, 60.2, -255, 155, GZ + 4, GZ + 15, M_TGL, bev=0)
for k in range(-12, 9):
    box(f"mul{k}", 59.6, 59.9, k*20 - 0.4, k*20 + 0.4, GZ + 4, GZ + 15, M_TERM, bev=0)
# jet bridge
box("bridge", 22, 46, 5.2, 8.2, GZ + 3.6, GZ + 6.4, principled("bridge", (0.55, 0.56, 0.58), 0.4, 0.4), bev=0.1)
cyl("bridgeleg", (40, 6.7, GZ + 1.8), 0.25, 3.6, "z", M_STRUT, None, 16)
# safety cones around the engine + a tug + GPU cart
M_CONE = principled("cone", (0.9, 0.22, 0.02), 0.5)
M_STRIPE = principled("cstripe", (0.85, 0.85, 0.85), 0.35)
for k, (cx, cy) in enumerate(((9.5, 12.6), (9.5, 6.2), (-4.5, 13.8), (6.8, 15.4), (14.5, 16.0))):
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.17, radius2=0.03, depth=0.72, location=(cx, cy, GZ + 0.38))
    o = bpy.context.object; o.data.materials.append(M_CONE)
    cyl(f"cs{k}", (cx, cy, GZ + 0.45), 0.105, 0.09, "z", M_STRIPE, None, 24)
    box(f"cb{k}", cx - 0.21, cx + 0.21, cy - 0.21, cy + 0.21, GZ, GZ + 0.04, M_CONE, bev=0.01)
M_TUG = principled("tug", (0.75, 0.55, 0.05), 0.45, coat=0.3)
box("tug", 30, 35, -15.4, -13, GZ + 0.5, GZ + 1.8, M_TUG, bev=0.1)
box("tugcab", 30.5, 32, -15.2, -13.2, GZ + 1.8, GZ + 2.9, principled("tugglass", (0.02, 0.025, 0.03), 0.05, coat=1.0), bev=0.05)
for wx in (30.9, 34.1):
    for wy in (-13.0, -15.4): cyl(f"tw{wx}{wy}", (wx, wy, GZ + 0.45), 0.45, 0.35, "y", M_RUB, None, 24)
# distant airliners (silhouettes) for depth
for k, (x, y) in enumerate(((-180, -150), (-260, 120), (140, -330))):
    o = bpy.data.objects.new(f"far{k}", None); coll.objects.link(o)
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0); bmesh.ops.scale(bm, vec=(60, 5.2, 5.4), verts=bm.verts)
    mesh_obj(f"farf{k}", bm, principled(f"farm{k}", (0.7, 0.7, 0.72), 0.4), True).location = (x, y, GZ + 4.5)
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0); bmesh.ops.scale(bm, vec=(9, 0.6, 11), verts=bm.verts)
    mesh_obj(f"fart{k}", bm, principled(f"fartm{k}", (0.1, 0.2, 0.4), 0.4), False).location = (x - 26, y, GZ + 12)

# ------------------------------------------------------------------ fan rotation
T_START = 13.3          # starter engaged
def fan_w(t):
    """rad/s of the fan — slow windmill, then spool up to an (artistically slowed) idle"""
    w = 0.55
    if t > T_START: w += 15.5*ease((t - T_START)/4.5)
    return w
_ANG = [0.0]; _DT = 1/300.0
def fan_ang(t):
    n = int(t/_DT)
    while len(_ANG) <= n + 1: _ANG.append(_ANG[-1] + fan_w(len(_ANG)*_DT)*_DT)
    return _ANG[n]
def place_fans(t, frame=None):
    for o in FANS:
        o.rotation_euler = (-fan_ang(t), 0, 0)
        if frame is not None:
            o.keyframe_insert("rotation_euler", index=0, frame=frame)
            o.rotation_euler = (-fan_ang(t + 1/FPS), 0, 0); o.keyframe_insert("rotation_euler", index=0, frame=frame + 1)

# ------------------------------------------------------------------ sky + sun
wo = bpy.data.worlds.new("w"); sc.world = wo; wo.use_nodes = True
bg = wo.node_tree.nodes["Background"]
sky = wo.node_tree.nodes.new("ShaderNodeTexSky"); sky.sky_type = 'MULTIPLE_SCATTERING'
wo.node_tree.links.new(sky.outputs[0], bg.inputs[0])
sky.altitude = 0; sky.aerosol_density = 1.8; sky.sun_intensity = 0.5
sun_d = bpy.data.lights.new("sun", 'SUN'); sun_d.angle = math.radians(0.6)
sun = bpy.data.objects.new("sun", sun_d); coll.objects.link(sun)
def set_sun(el, rot, energy, color, bgs):
    sky.sun_elevation = math.radians(el); sky.sun_rotation = math.radians(rot)
    sun.rotation_euler = Euler((math.radians(90 - el), 0, math.radians(rot + 90)))
    sun_d.energy = energy; sun_d.color = color; bg.inputs[1].default_value = bgs
SUNROT = float(os.environ.get("SUNROT", "120"))
SUNEL = float(os.environ.get("SUNEL", "4.5"))
set_sun(SUNEL, SUNROT, 3.6, (1.0, 0.62, 0.38), 0.2)

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

EL = Vector((2.4, 9.5, -2.6))             # left engine centre
SPT = EL + Vector((1.55 + 0.08 + 0.56, 0, 0))   # spinner tip
def pose(t):
    if SHOT == "A":
        k = ease(t/3.4)
        cam_d.lens = lerp(30, 33, k)
        loc = Vector((lerp(25, 23, k), lerp(17, 16, k), GZ + 1.3))
        tgt = Vector((4, 6, -2.0))
        aim(loc, tgt, t, math.radians(0.05), fstop=8, fdist=(EL - loc).length)
    elif SHOT == "B":
        u = (t - 3.4)/9.5; k = ease(u)
        cam_d.lens = lerp(40, 55, k)
        loc = Vector((lerp(9.5, 8.0, k), lerp(11.6, 10.4, k), lerp(-2.95, -2.75, k)))
        tgt = SPT + Vector((-0.25, 0, -0.05))
        aim(loc, tgt, t, math.radians(0.05), fstop=4.0, fdist=(SPT - loc).length)
    elif SHOT == "C":
        u = (t - 12.9)/7.7; k = ease(u)
        cam_d.lens = lerp(50, 42, k)
        loc = Vector((lerp(7.6, 8.4, k), lerp(9.0, 9.3, k), lerp(-2.45, -2.55, k)))
        tgt = SPT + Vector((-0.3, 0, 0))
        spool = clamp((t - T_START)/1.5)
        aim(loc, tgt, t, math.radians(0.05 + 0.06*spool), fstop=3.5, fdist=(SPT - loc).length, rate=1.6 + 2*spool)
    else:
        u = (t - 20.6)/11.6; k = ease(u)
        cam_d.lens = lerp(70, 85, k)
        loc = Vector((lerp(55, 50, k), lerp(20, 19, k), GZ + 1.6))
        tgt = Vector((EL.x, EL.y, EL.z + 0.3))
        aim(loc, tgt, t, math.radians(0.04), fstop=5.6, fdist=(EL - loc).length)

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
sc.view_settings.exposure = float(os.environ.get("EXPO", "-0.2"))

def screen(p):
    v = world_to_camera_view(sc, cam, Vector(p)); return (v.x*RES[0], (1-v.y)*RES[1], v.z)
def shot_for(t):
    for k, (a, b) in SHOTS.items():
        if a <= t < b: return k
    return "D"
def setup(t, frame=None):
    global SHOT
    SHOT = shot_for(t); place_fans(t, frame)
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
        meta[i] = {"spinner": screen(SPT + Vector((-0.2, 0, 0.12))), "fan": screen(EL + Vector((1.55, 0, 0.75))),
                   "engine": screen(EL + Vector((2.4, 0, 0))), "cone": screen((9.5, 12.6, GZ + 0.7))}
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
