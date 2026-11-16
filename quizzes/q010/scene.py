import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import bpy, bmesh, math, json, sys, os, random
from mathutils import Vector, Euler
from bpy_extras.object_utils import world_to_camera_view

FPS = 30
RES = (1080, 1920)
OUT = os.environ.get("OUT", QDIR)
SHOT = os.environ.get("SHOT", "A")
SHOTS = {"A": (0.0, 5.2), "B": (5.2, 13.4), "C": (13.4, 25.6)}
WATER = -42.0
LANES = [(-7.0, 1), (-3.5, 1), (3.5, -1), (7.0, -1)]
FL, FW, FP = 0.70, 0.10, 0.22     # finger length, width, pitch
YJ = 9.6                          # joint half width

def ease(x):
    x = max(0.0, min(1.0, x)); return x*x*(3-2*x)
def lerp(a, b, k): return a + (b-a)*k

def gap_shift(t):
    """movement of the right deck (m). + = pulls apart"""
    if t < 13.4: return 0.0
    u = t - 13.4
    return -0.17*math.cos(2*math.pi*(u - 3.3)/5.6) * ease(u/0.8)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; coll = sc.collection
rnd = random.Random(21)

def principled(name, color, rough=0.5, metal=0.0, coat=0.0, emit=None, estr=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal; b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = estr
    return m
def noisy(name, col, rough, scale=0.3, amt=0.35, metal=0.0, col2=None, rough_var=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = 12
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs["Factor"].default_value = amt
    mix.inputs[6].default_value = (*col, 1); nt.links.new(nz.outputs["Fac"], mix.inputs[7])
    nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    if rough > 0.8 and metal == 0: b.inputs["Specular IOR Level"].default_value = 0.2
    if rough_var:
        mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[3].default_value = rough - rough_var; mr.inputs[4].default_value = rough + rough_var
        nt.links.new(nz.outputs["Fac"], mr.inputs[0]); nt.links.new(mr.outputs[0], b.inputs["Roughness"])
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.15
    n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = scale*40; n2.inputs["Detail"].default_value = 6
    nt.links.new(tc.outputs["Object"], n2.inputs["Vector"]); nt.links.new(n2.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs[0], b.inputs["Normal"])
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

M_ASPH = noisy("asphalt", (0.06, 0.06, 0.062), 0.9, scale=2.0, amt=0.55, rough_var=0.06)
M_LINE = principled("line", (0.72, 0.72, 0.68), 0.6)
M_STEEL = noisy("steel", (0.17, 0.155, 0.14), 0.55, scale=3.0, amt=0.6, metal=0.7, rough_var=0.15)
M_GIRD = noisy("girder", (0.13, 0.20, 0.22), 0.5, scale=0.05, amt=0.35, metal=0.3)
M_CONC = noisy("concrete", (0.33, 0.31, 0.28), 0.85, scale=0.08, amt=0.4)
M_DARK = principled("void", (0.005, 0.005, 0.005), 0.9)
M_BARR = noisy("barrier", (0.55, 0.55, 0.53), 0.5, scale=0.4, amt=0.2, metal=0.6)

# ------------------------------------------------------------------ deck: left (fixed) and right (moving) halves
right = bpy.data.objects.new("rightdeck", None); coll.objects.link(right)
for side, par in ((-1, None), (1, right)):
    # asphalt slab
    box(f"road{side}", (900, 2*YJ, 0.3), (side*(0.95 + 450), 0, -0.15), M_ASPH, par)
    # steel finger plate base
    box(f"plate{side}", (0.5, 2*YJ, 0.06), (side*0.7, 0, -0.03), M_STEEL, par)
    # sidewalk + barrier
    for s in (1, -1):
        box(f"curb{side}{s}", (900, 1.6, 0.25), (side*(0.3 + 450), s*(YJ + 0.8), 0.12), M_CONC, par)
        box(f"barr{side}{s}", (900, 0.25, 1.0), (side*(0.3 + 450), s*(YJ + 1.7), 0.6), M_BARR, par)
        box(f"rail{side}{s}", (900, 0.12, 0.12), (side*(0.3 + 450), s*(YJ + 1.7), 1.2), M_BARR, par)
    # girder below
    box(f"girder{side}", (900, 2*YJ - 2, 3.6), (side*(0.3 + 450), 0, -2.1), M_GIRD, par)
# fingers (single mesh per side)
for side, par in ((-1, None), (1, right)):
    bm = bmesh.new(); n = int(2*YJ/FP)
    for k in range(n):
        y = -YJ + FP*0.5 + k*FP + (0 if side < 0 else FP/2)
        if y > YJ - 0.05: continue
        x0 = side*0.45; x1 = side*(0.45 - FL)
        res = bmesh.ops.create_cube(bm, size=1.0)
        for v in res["verts"]:
            v.co.x = (x0 + x1)/2 + v.co.x*abs(x1 - x0) * (1.0 if True else 1)
            taper = 1.0 - 0.25*((v.co.x - min(x0, x1))/abs(x1 - x0) if side < 0 else (max(x0, x1) - v.co.x)/abs(x1 - x0))
            v.co.y = y + v.co.y*FW*taper; v.co.z = -0.02 + v.co.z*0.05
    me = bpy.data.meshes.new(f"fingers{side}"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(f"fingers{side}", me); coll.objects.link(o); o.data.materials.append(M_STEEL)
    md = o.modifiers.new("bv", 'BEVEL'); md.width = 0.008; md.segments = 2
    if par: o.parent = par
# dark void under the joint
box("void", (1.0, 2*YJ, 0.4), (0, 0, -0.32), M_DARK)
# lane markings (dashes) per side
for side, par in ((-1, None), (1, right)):
    for y in (-5.25, 0.0, 5.25):
        for k in range(60):
            x = side*(1.5 + k*12)
            if y == 0.0:
                box(f"cl{side}{k}", (11.5, 0.15, 0.012), (x + side*5, -0.12, 0.006), M_LINE, par)
                box(f"cr{side}{k}", (11.5, 0.15, 0.012), (x + side*5, 0.12, 0.006), M_LINE, par)
            else:
                box(f"d{side}{y}{k}", (3.0, 0.15, 0.012), (x, y, 0.006), M_LINE, par)
    for s in (1, -1):
        box(f"edge{side}{s}", (900, 0.2, 0.012), (side*(1.0 + 450), s*(YJ - 0.35), 0.006), M_LINE, par)
# lamp posts
M_LAMP = principled("lamp", (0.2, 0.21, 0.22), 0.4, 0.7)
for k in range(-20, 21):
    x = k*40 + 20
    for s in (1, -1):
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.09, depth=9, location=(x, s*(YJ + 1.7), 5.6))
        bpy.context.object.data.materials.append(M_LAMP)
        box(f"arm{k}{s}", (0.15, 1.6, 0.12), (x, s*(YJ + 0.9), 10.0), M_LAMP)
# piers + far substructure
for k in range(-6, 7):
    x = k*130
    box(f"pier{k}", (6, 12, -WATER + 5), (x, 0, (WATER - 4)/2 - 2), M_CONC)
    box(f"cap{k}", (7, 20, 2.2), (x, 0, -4.9), M_CONC)
# steel arch over the main span (makes it read as a big steel bridge)
bm = bmesh.new()
for s in (1, -1):
    pts = []
    for i in range(41):
        u = -1 + 2*i/40; x = 130 + u*120; z = 45*(1 - u*u) - 3
        pts.append((x, z))
    prev = None
    for (x, z) in pts:
        a = bm.verts.new((x, s*(YJ + 2.6), z)); b_ = bm.verts.new((x, s*(YJ + 2.6), z + 2.6))
        c = bm.verts.new((x, s*(YJ + 1.4), z + 2.6)); d = bm.verts.new((x, s*(YJ + 1.4), z))
        if prev:
            for (p, q) in ((0, 1), (1, 2), (2, 3), (3, 0)):
                bm.faces.new([prev[p], prev[q], (a, b_, c, d)[q], (a, b_, c, d)[p]])
        prev = (a, b_, c, d)
me = bpy.data.meshes.new("arch"); bm.to_mesh(me); bm.free()
arch = bpy.data.objects.new("arch", me); coll.objects.link(arch); arch.data.materials.append(M_GIRD)
for k in range(1, 24):
    x = 10 + k*10; u = (x - 130)/120; z = 45*(1 - u*u) - 3
    if z < 2: continue
    for s in (1, -1):
        bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.08, depth=z, location=(x, s*(YJ + 2.0), z/2))
        bpy.context.object.data.materials.append(M_BARR)
for k in range(0, 24, 2):
    x = 18 + k*10; u = (x - 130)/120; z = 45*(1 - u*u) - 1.5
    if z < 8: continue
    box(f"brace{k}", (1.0, 2*(YJ + 2.0), 0.9), (x, 0, z), M_GIRD)

# ------------------------------------------------------------------ vehicles
CARCOLS = [(0.6, 0.6, 0.62), (0.05, 0.05, 0.06), (0.35, 0.02, 0.02), (0.75, 0.75, 0.74), (0.04, 0.09, 0.22), (0.3, 0.3, 0.32), (0.15, 0.16, 0.18)]
M_GLASS = principled("glass", (0.01, 0.012, 0.015), 0.05, coat=1.0)
M_TIRE = principled("tire", (0.02, 0.02, 0.02), 0.85)
M_RIM = principled("rim", (0.6, 0.6, 0.62), 0.3, 0.9)
M_TAIL = principled("tail", (0.5, 0.0, 0.0), 0.3, emit=(1, 0.02, 0.0), estr=2.0)
M_HEAD = principled("head", (0.9, 0.9, 0.85), 0.2, emit=(1, 0.9, 0.75), estr=4.0)
M_TRUCK = principled("trailer", (0.8, 0.8, 0.78), 0.5)
def make_vehicle(name, kind, col):
    root = bpy.data.objects.new(name, None); coll.objects.link(root)
    paint = principled(name+"p", col, 0.3, 0.4, coat=0.8)
    wheels = []
    if kind == "car":
        L, W_, H_ = 4.5, 1.85, 0.75
        box(name+"b", (L, W_, H_), (0, 0, 0.33 + H_/2), paint, root, bevel=0.15)
        box(name+"c", (2.4, 1.6, 0.6), (-0.3, 0, 0.33 + H_ + 0.28), M_GLASS, root, bevel=0.18)
        box(name+"r", (1.9, 1.5, 0.08), (-0.4, 0, 0.33 + H_ + 0.6), paint, root, bevel=0.03)
        wx = [1.45, -1.45]; r = 0.34
        box(name+"tl", (0.05, 1.5, 0.12), (-L/2, 0, 0.85), M_TAIL, root)
        box(name+"hl", (0.05, 1.4, 0.1), (L/2, 0, 0.75), M_HEAD, root)
    else:
        L, W_ = 16.0, 2.5
        box(name+"cab", (2.3, W_, 2.7), (6.6, 0, 0.55 + 1.35), paint, root, bevel=0.12)
        box(name+"ws", (0.05, 2.2, 1.0), (7.76, 0, 2.4), M_GLASS, root)
        box(name+"tr", (13.2, W_, 3.0), (-1.2, 0, 1.2 + 1.5), M_TRUCK, root, bevel=0.05)
        box(name+"tl", (0.05, 2.0, 0.15), (-7.8, 0, 1.1), M_TAIL, root)
        wx = [6.4, 2.6, -5.0, -6.3, -7.6] if False else [6.4, 3.0, -4.6, -6.0]; r = 0.52
    for x in wx:
        for s in (1, -1):
            bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=r, depth=0.26, location=(x, s*(W_/2 - 0.1), r), rotation=(math.radians(90), 0, 0))
            w = bpy.context.object; w.data.materials.append(M_TIRE); w.parent = root; wheels.append((w, x))
            bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=r*0.62, depth=0.27, location=(x, s*(W_/2 - 0.1), r), rotation=(math.radians(90), 0, 0))
            h = bpy.context.object; h.data.materials.append(M_RIM); h.parent = root
    return root, wheels, L
VEH = []
for li, (y, d) in enumerate(LANES):
    n = 5
    for k in range(n):
        kind = "truck" if (li in (0, 3) and k % 3 == 1) else "car"
        root, wheels, L = make_vehicle(f"v{li}_{k}", kind, rnd.choice(CARCOLS))
        speed = (22 if kind == "truck" else rnd.uniform(25, 30))
        VEH.append(dict(root=root, wheels=wheels, y=y, d=d, x0=rnd.uniform(0, 400) + k*80, v=speed, L=L, kind=kind))
def place_vehicles(t, period=500.0, hide=False):
    for v in VEH:
        x = ((v["x0"] + v["v"]*t) % period) - period/2
        X = x*v["d"]
        # bump when an axle crosses the joint
        bz = 0.0
        for w, wx in v["wheels"]:
            ax = X + wx*v["d"]
            bz = max(bz, 0.012*math.exp(-(ax/0.3)**2))
        v["root"].location = (X, v["y"], bz)
        v["root"].rotation_euler = (0, 0, 0 if v["d"] > 0 else math.pi)
        v["root"].hide_render = hide
        for o in [v["root"]] + list(v["root"].children):
            o.hide_render = hide
# special hero car for shot B: rolls over the joint near the camera
hero, hero_w, _ = make_vehicle("hero", "car", (0.45, 0.02, 0.02))
hero_truck, ht_w, _ = make_vehicle("herotruck", "truck", (0.05, 0.12, 0.3))

# ------------------------------------------------------------------ environment
wo = bpy.data.worlds.new("w"); sc.world = wo; wo.use_nodes = True
bg = wo.node_tree.nodes["Background"]
sky = wo.node_tree.nodes.new("ShaderNodeTexSky"); sky.sky_type = 'MULTIPLE_SCATTERING'
wo.node_tree.links.new(sky.outputs[0], bg.inputs[0])
sky.altitude = 0; sky.aerosol_density = 1.5; sky.sun_intensity = 0.5
bg.inputs[1].default_value = 0.17
sun_d = bpy.data.lights.new("sun", 'SUN'); sun_d.angle = math.radians(0.6)
sun = bpy.data.objects.new("sun", sun_d); coll.objects.link(sun)
def set_sun(el, rot, energy, color, bgs):
    sky.sun_elevation = math.radians(el); sky.sun_rotation = math.radians(rot)
    sun.rotation_euler = Euler((math.radians(90 - el), 0, math.radians(rot + 90)))
    sun_d.energy = energy; sun_d.color = color; bg.inputs[1].default_value = bgs
set_sun(9, 215, 3.4, (1.0, 0.72, 0.5), 0.17)
# water
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, WATER))
sea = bpy.context.object; sea.name = "sea"
oc = sea.modifiers.new("ocean", 'OCEAN')
oc.geometry_mode = 'GENERATE'; oc.size = 1.0; oc.spatial_size = 300; oc.resolution = 10
oc.repeat_x = 6; oc.repeat_y = 6; oc.wave_scale = 0.6; oc.choppiness = 1.0; oc.wind_velocity = 8; oc.random_seed = 4
wm = bpy.data.materials.new("water"); wm.use_nodes = True
b = wm.node_tree.nodes["Principled BSDF"]
b.inputs["Base Color"].default_value = (0.005, 0.02, 0.025, 1); b.inputs["Roughness"].default_value = 0.12; b.inputs["IOR"].default_value = 1.33
sea.data.materials.append(wm); sea.location = (-900, -900, WATER)
bpy.ops.mesh.primitive_plane_add(size=200000, location=(0, 0, WATER - 0.3)); bpy.context.object.data.materials.append(wm)
# distant hills / shore
M_HILL = noisy("hill", (0.05, 0.07, 0.04), 0.9, scale=0.004, amt=0.5)
for k in range(14):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1, location=(rnd.uniform(-2500, 2500), rnd.choice([1, -1])*rnd.uniform(1600, 2600) if k % 3 else 2400, WATER - 10))
    h = bpy.context.object; h.scale = (rnd.uniform(400, 900), rnd.uniform(300, 600), rnd.uniform(60, 160)); h.data.materials.append(M_HILL)
for s in (-1, 1):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1, location=(s*1100, 0, WATER - 20))
    h = bpy.context.object; h.scale = (380, 900, 70); h.data.materials.append(M_HILL)

# ------------------------------------------------------------------ camera
cam_d = bpy.data.cameras.new("cam"); cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 36; cam_d.clip_end = 100000; cam_d.clip_start = 0.02
cam = bpy.data.objects.new("cam", cam_d); coll.objects.link(cam); sc.camera = cam
SH = [(rnd.uniform(-1, 1), rnd.uniform(-1, 1)) for _ in range(400)]
def shake(t, amp, rate=2.5):
    i = int(t*rate); f = t*rate - i; a, b_ = SH[i % 400], SH[(i+1) % 400]; f = f*f*(3-2*f)
    return (a[0]+(b_[0]-a[0])*f)*amp, (a[1]+(b_[1]-a[1])*f)*amp
def aim(loc, tgt, t, amp):
    cam.location = loc
    e = (Vector(tgt)-Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sx, sy = shake(t, amp); e.x += sx; e.z += sy; cam.rotation_euler = e

def place_hero(obj, wheels, x, y, d=1):
    bz = 0.0
    for w, wx in wheels:
        ax = x + wx*d - gap_shift(0)
        bz = max(bz, 0.015*math.exp(-(ax/0.25)**2))
    obj.location = (x, y, bz); obj.rotation_euler = (0, 0, 0 if d > 0 else math.pi)

def pose(t):
    oc.time = t*0.7
    right.location.x = gap_shift(t)
    if SHOT == "A":
        place_vehicles(t)
        place_hero(hero, hero_w, -900, 0); place_hero(hero_truck, ht_w, -950, 0)
        k = ease(t/5.2)
        cam_d.lens = lerp(38, 44, k)
        loc = (lerp(-120, -95, k), lerp(-75, -62, k), lerp(14, 10, k))
        tgt = (lerp(80, 70, k), 0, lerp(8, 5, k))
        aim(loc, tgt, t, math.radians(0.1))
    elif SHOT == "B":
        place_vehicles(t)
        # keep random traffic away from the camera lane
        for v in VEH:
            if v["y"] == -7.0 and abs(v["root"].location.x) < 60: v["root"].location.x += 120
        place_hero(hero, hero_w, 26*(t - 8.0), -7.0)
        place_hero(hero_truck, ht_w, 21*(11.6 - t), 3.5, d=-1)
        k = ease((t-5.2)/8.2)
        cam_d.lens = lerp(24, 30, k)
        loc = (lerp(-2.6, -1.8, k), lerp(-9.35, -9.3, k), lerp(0.4, 0.55, k))
        tgt = (lerp(1.2, 0.8, k), lerp(-4.5, -4.0, k), 0.15)
        aim(loc, tgt, t, math.radians(0.12))
    else:
        place_vehicles(t, hide=True)
        hero.location = (-900, 0, 0); hero_truck.location = (-950, 0, 0)
        for o in list(hero.children) + list(hero_truck.children): o.hide_render = True
        # time-lapse: sun races across the sky, colour shifts
        u = (t - 13.4)/12.2
        ph = (t - 13.4)*2*math.pi/3.5
        el = 32 + 22*math.sin(ph)
        set_sun(el, 120 + (t - 13.4)*55, lerp(2.0, 2.8, max(0, math.sin(ph))), (1.0, lerp(0.72, 0.95, max(0, math.sin(ph))), lerp(0.5, 0.88, max(0, math.sin(ph)))), 0.2)
        k = ease(u)
        cam_d.lens = lerp(26, 30, k)
        loc = (lerp(-0.9, -0.7, k), lerp(-6.4, -5.9, k), lerp(1.45, 1.25, k))
        tgt = (0.02, lerp(-4.2, -4.0, k), 0.0)
        aim(loc, tgt, t, math.radians(0.05))

# ------------------------------------------------------------------ render
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.cycles.samples = int(os.environ.get("SPP", "10")); sc.cycles.use_denoising = True; sc.cycles.use_adaptive_sampling = True
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transparent_max_bounces = 6
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.resolution_percentage = int(os.environ.get("PCT", "50"))
sc.render.use_persistent_data = True
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
sc.view_settings.exposure = float(os.environ.get("EXPO", "-0.3"))

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
        g = gap_shift(t)
        meta[i] = {"joint": screen((0, -6.0, 0.0)), "jl": screen((-0.37, -2.6, 0.03)), "jr": screen((0.37 + g, -2.6, 0.03)),
                   "comb": screen((0, -4.0, 0.0)), "shift": g}
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
