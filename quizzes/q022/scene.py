import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import bpy, bmesh, math, json, sys, os, random
from mathutils import Vector, Euler
from bpy_extras.object_utils import world_to_camera_view

FPS = 30
RES = (1080, 1920)
OUT = os.environ.get("OUT", QDIR)
SHOT = "A"
SHOTS = {"A": (0.0, 7.0), "B": (7.0, 16.4), "C": (16.4, 22.5), "D": (22.5, 31.0)}
T_IGN = 18.2       # engines ignite
T_LIFT = 20.4      # liftoff
MZ = 8.0          # top of launch mount

def ease(x):
    x = max(0.0, min(1.0, x)); return x*x*(3-2*x)
def lerp(a, b, k): return a + (b-a)*k

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; coll = sc.collection
rnd = random.Random(11)

def principled(name, color, rough=0.5, metal=0.0, coat=0.0, emit=None, estr=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal; b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = estr
    return m
def noisy(name, col, rough, scale=0.3, amt=0.35, metal=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = 10
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs["Factor"].default_value = amt
    mix.inputs[6].default_value = (*col, 1); nt.links.new(nz.outputs["Fac"], mix.inputs[7])
    nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    return m
def box(name, size, loc, mat, parent=None, rot=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object; o.name = name; o.scale = size; o.data.materials.append(mat)
    if rot: o.rotation_euler = rot
    if parent: o.parent = parent
    return o
def cyl(r, d, loc, mat, parent=None, v=48, rot=None, smooth=True):
    bpy.ops.mesh.primitive_cylinder_add(vertices=v, radius=r, depth=d, location=loc)
    o = bpy.context.object; o.data.materials.append(mat)
    if rot: o.rotation_euler = rot
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    if parent: o.parent = parent
    return o
def cone(r1, r2, d, loc, mat, parent=None, v=48, open_=False):
    bpy.ops.mesh.primitive_cone_add(vertices=v, radius1=r1, radius2=r2, depth=d, location=loc, end_fill_type='NOTHING' if open_ else 'NGON')
    o = bpy.context.object; o.data.materials.append(mat)
    for p in o.data.polygons: p.use_smooth = True
    if parent: o.parent = parent
    return o

# ------------------------------------------------------------------ materials
def rocket_paint(name, base, band=None):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.45
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise")
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (3, 3, 0.15)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 2.0; nz.inputs["Detail"].default_value = 8
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs["Factor"].default_value = 0.18
    mix.inputs[6].default_value = (*base, 1); nt.links.new(nz.outputs["Fac"], mix.inputs[7])
    nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    return m
M_WHITE = rocket_paint("white", (0.82, 0.82, 0.8))
M_ORANGE = rocket_paint("foam", (0.40, 0.19, 0.075))
M_BLACK = principled("black", (0.025, 0.025, 0.028), 0.45)
M_NOZ = principled("nozzle", (0.16, 0.12, 0.10), 0.3, 1.0)
M_STEEL = noisy("steel", (0.22, 0.22, 0.23), 0.5, scale=0.5, amt=0.4, metal=0.6)
M_MOUNT = noisy("mount", (0.16, 0.165, 0.17), 0.6, scale=0.15, amt=0.45, metal=0.3)
M_CONC = noisy("concrete", (0.42, 0.40, 0.37), 0.85, scale=0.03, amt=0.4)
M_GRASS = noisy("grass", (0.075, 0.07, 0.035), 0.95, scale=0.006, amt=0.55)
M_RED = principled("red", (0.45, 0.06, 0.03), 0.5)
M_PIPE = noisy("pipe", (0.30, 0.31, 0.32), 0.45, scale=1.0, amt=0.3, metal=0.7)

def flame_mat(name, c0, c1, strength):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission"); tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mix = nt.nodes.new("ShaderNodeMixShader")
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB"); cr = ramp.color_ramp
    cr.elements[0].position = 0.0; cr.elements[0].color = (*c0, 1); cr.elements[1].position = 0.9; cr.elements[1].color = (*c1, 1)
    nt.links.new(sep.outputs["Z"], ramp.inputs[0])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 5
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    st = nt.nodes.new("ShaderNodeMath"); st.operation = 'MULTIPLY'; st.inputs[1].default_value = strength
    nt.links.new(nz.outputs["Fac"], st.inputs[0])
    nt.links.new(ramp.outputs[0], em.inputs["Color"]); nt.links.new(st.outputs[0], em.inputs["Strength"])
    fac = nt.nodes.new("ShaderNodeMapRange"); fac.inputs[3].default_value = 0.1; fac.inputs[4].default_value = 0.95
    nt.links.new(sep.outputs["Z"], fac.inputs[0])
    nt.links.new(fac.outputs[0], mix.inputs[0]); nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    return m
def steam_mat():
    m = bpy.data.materials.new("steam"); m.use_nodes = True; nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep.inputs[0])
    dif = nt.nodes.new("ShaderNodeBsdfDiffuse"); dif.inputs["Color"].default_value = (0.92, 0.9, 0.88, 1)
    trl = nt.nodes.new("ShaderNodeBsdfTranslucent"); trl.inputs["Color"].default_value = (0.95, 0.85, 0.75, 1)
    m1 = nt.nodes.new("ShaderNodeMixShader"); m1.inputs[0].default_value = 0.35
    nt.links.new(dif.outputs[0], m1.inputs[1]); nt.links.new(trl.outputs[0], m1.inputs[2])
    # warm glow from the engines on the lower part
    hz = nt.nodes.new("ShaderNodeMapRange"); hz.inputs[1].default_value = -0.2; hz.inputs[2].default_value = -1.0
    nt.links.new(sep.outputs["Z"], hz.inputs[0])
    gl = nt.nodes.new("ShaderNodeMath"); gl.operation = 'MULTIPLY'; gl.inputs[1].default_value = 0.0
    nt.links.new(hz.outputs[0], gl.inputs[0])
    emi = nt.nodes.new("ShaderNodeEmission"); emi.inputs["Color"].default_value = (1.0, 0.5, 0.2, 1)
    nt.links.new(gl.outputs[0], emi.inputs["Strength"])
    add = nt.nodes.new("ShaderNodeAddShader"); nt.links.new(m1.outputs[0], add.inputs[0]); nt.links.new(emi.outputs[0], add.inputs[1])
    # soft edges
    lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.5
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 3.0; nz.inputs["Detail"].default_value = 4
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    ad = nt.nodes.new("ShaderNodeMath"); ad.operation = 'ADD'
    nt.links.new(lw.outputs["Facing"], ad.inputs[0]); nt.links.new(nz.outputs["Fac"], ad.inputs[1])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[1].default_value = 0.95; mr.inputs[2].default_value = 1.35
    nt.links.new(ad.outputs[0], mr.inputs[0])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    m2 = nt.nodes.new("ShaderNodeMixShader"); nt.links.new(mr.outputs[0], m2.inputs[0])
    nt.links.new(add.outputs[0], m2.inputs[1]); nt.links.new(tr.outputs[0], m2.inputs[2])
    nt.links.new(m2.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    return m, gl
def vol_mat(name, col, scale, EMK=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    pv = nt.nodes.new("ShaderNodeVolumePrincipled"); pv.inputs["Color"].default_value = (*col, 1); pv.inputs["Anisotropy"].default_value = 0.25
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = 5
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    gr = nt.nodes.new("ShaderNodeTexGradient"); gr.gradient_type = 'SPHERICAL'; nt.links.new(tc.outputs["Object"], gr.inputs["Vector"])
    mm = nt.nodes.new("ShaderNodeMath"); mm.operation = 'MULTIPLY'; nt.links.new(nz.outputs["Fac"], mm.inputs[0]); nt.links.new(gr.outputs["Fac"], mm.inputs[1])
    pw = nt.nodes.new("ShaderNodeMath"); pw.operation = 'POWER'; pw.inputs[1].default_value = 0.8; nt.links.new(mm.outputs[0], pw.inputs[0])
    dens = nt.nodes.new("ShaderNodeMath"); dens.operation = 'MULTIPLY'; dens.inputs[1].default_value = 0.0
    nt.links.new(pw.outputs[0], dens.inputs[0]); nt.links.new(dens.outputs[0], pv.inputs["Density"])
    em = nt.nodes.new("ShaderNodeMath"); em.operation = 'MULTIPLY'; em.inputs[1].default_value = EMK
    nt.links.new(pw.outputs[0], em.inputs[0]); nt.links.new(em.outputs[0], pv.inputs["Emission Strength"])
    pv.inputs["Emission Color"].default_value = (1.0, 0.86, 0.7, 1)
    nt.links.new(pv.outputs[0], nt.nodes["Material Output"].inputs["Volume"])
    return m, dens
# ------------------------------------------------------------------ world
wo = bpy.data.worlds.new("w"); sc.world = wo; wo.use_nodes = True
bg = wo.node_tree.nodes["Background"]
sky = wo.node_tree.nodes.new("ShaderNodeTexSky"); sky.sky_type = 'MULTIPLE_SCATTERING'
wo.node_tree.links.new(sky.outputs[0], bg.inputs[0])
sun_d = bpy.data.lights.new("sun", 'SUN'); sun_d.angle = math.radians(0.6)
sun = bpy.data.objects.new("sun", sun_d); coll.objects.link(sun)
def set_sun(el, rot, energy, color, bgs):
    sky.sun_elevation = math.radians(el); sky.sun_rotation = math.radians(rot)
    sky.altitude = 10; sky.aerosol_density = 1.6; sky.sun_intensity = 0.5
    sun.rotation_euler = Euler((math.radians(90 - el), 0, math.radians(rot + 90)))
    sun_d.energy = energy; sun_d.color = color; bg.inputs[1].default_value = bgs
set_sun(5, 50, 3.8, (1.0, 0.66, 0.42), 0.22)

# ------------------------------------------------------------------ camera
cam_d = bpy.data.cameras.new("cam"); cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 36; cam_d.clip_end = 100000; cam_d.clip_start = 0.1
cam = bpy.data.objects.new("cam", cam_d); coll.objects.link(cam); sc.camera = cam
SH = [(rnd.uniform(-1, 1), rnd.uniform(-1, 1)) for _ in range(400)]
def shake(t, amp, rate=2.5):
    i = int(t*rate); f = t*rate - i; a, b_ = SH[i % 400], SH[(i+1) % 400]; f = f*f*(3-2*f)
    return (a[0]+(b_[0]-a[0])*f)*amp, (a[1]+(b_[1]-a[1])*f)*amp
def aim(loc, tgt, t, amp):
    cam.location = loc
    e = (Vector(tgt)-Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sx, sy = shake(t, amp); e.x += sx; e.z += sy; cam.rotation_euler = e

# ------------------------------------------------------------------ materials
M_WHITE = rocket_paint("white", (0.80, 0.79, 0.76))
M_BLACK = principled("black", (0.02, 0.02, 0.022), 0.5)
M_SOOT = noisy("soot", (0.05, 0.045, 0.04), 0.7, scale=0.8, amt=0.6)
M_NOZ = principled("nozzle", (0.10, 0.08, 0.07), 0.35, 1.0)
M_STEEL = noisy("steel", (0.22, 0.22, 0.23), 0.5, scale=0.5, amt=0.4, metal=0.6)
M_MOUNT = noisy("mount", (0.16, 0.165, 0.17), 0.6, scale=0.15, amt=0.45, metal=0.3)
M_CONC = noisy("concrete", (0.42, 0.40, 0.37), 0.85, scale=0.03, amt=0.4)
M_GRASS = noisy("grass", (0.075, 0.07, 0.035), 0.95, scale=0.006, amt=0.55)

def frost_mat(name, patchy=True):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (0.86, 0.9, 0.95, 1); b.inputs["Roughness"].default_value = 0.7
    b.inputs["Subsurface Weight"].default_value = 0.15
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nzf = nt.nodes.new("ShaderNodeTexNoise"); nzf.inputs["Scale"].default_value = 3.5; nzf.inputs["Detail"].default_value = 12; nzf.inputs["Roughness"].default_value = 0.75
    nt.links.new(tc.outputs["Object"], nzf.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 1.0; bump.inputs["Distance"].default_value = 0.12
    nz2 = nt.nodes.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = 30.0; nz2.inputs["Detail"].default_value = 6
    nt.links.new(tc.outputs["Object"], nz2.inputs["Vector"])
    hs = nt.nodes.new("ShaderNodeMath"); hs.operation = 'ADD'; nt.links.new(nzf.outputs["Fac"], hs.inputs[0]); nt.links.new(nz2.outputs["Fac"], hs.inputs[1])
    nt.links.new(hs.outputs[0], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    # subtle colour variation
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs["Factor"].default_value = 0.6
    mx.inputs[6].default_value = (0.9, 0.94, 1.0, 1); nt.links.new(nzf.outputs["Fac"], mx.inputs[7]); nt.links.new(mx.outputs[2], b.inputs["Base Color"])
    if patchy:
        mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1.6, 1.6, 0.35)
        nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
        nzp = nt.nodes.new("ShaderNodeTexNoise"); nzp.inputs["Scale"].default_value = 1.6; nzp.inputs["Detail"].default_value = 8
        nt.links.new(mp.outputs["Vector"], nzp.inputs["Vector"])
        rp = nt.nodes.new("ShaderNodeMapRange"); rp.inputs[1].default_value = 0.37; rp.inputs[2].default_value = 0.39
        nt.links.new(nzp.outputs["Fac"], rp.inputs[0]); nt.links.new(rp.outputs[0], b.inputs["Alpha"])
    return m
M_FROST = frost_mat("frost"); M_FLAKE = frost_mat("flake", patchy=False)

# ------------------------------------------------------------------ rocket (z=0 at engine exit plane)
rocket = bpy.data.objects.new("rocket", None); coll.objects.link(rocket)
R = 1.83
cyl(R, 40.4, (0, 0, 21.8), M_WHITE, rocket, v=64)                  # first stage
cyl(R + 0.01, 2.6, (0, 0, 2.9), M_SOOT, rocket, v=64)               # engine section / octaweb skirt
cyl(R + 0.01, 6.5, (0, 0, 45.25), M_BLACK, rocket, v=64)            # interstage
cyl(R, 9.6, (0, 0, 53.3), M_WHITE, rocket, v=64)                    # second stage
cone(R, 2.6, 0.8, (0, 0, 58.5), M_WHITE, rocket, v=64)              # fairing adapter
cyl(2.6, 5.6, (0, 0, 61.7), M_WHITE, rocket, v=64)                  # fairing
cone(2.6, 1.6, 5.0, (0, 0, 67.0), M_WHITE, rocket, v=64)
cone(1.6, 0.35, 4.2, (0, 0, 71.6), M_WHITE, rocket, v=64)
bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=0.35, location=(0, 0, 73.7)); bpy.context.object.data.materials.append(M_WHITE); bpy.context.object.parent = rocket
cyl(R + 0.012, 0.15, (0, 0, 18.2), principled("seam", (0.3, 0.3, 0.3), 0.5), rocket, v=64)   # tank dome weld line
# frost shells: LOX tank of stage 1, LOX tank of stage 2 (thicker at the bottom)
fr1 = cyl(R + 0.035, 21.0, (0, 0, 29.0), M_FROST, rocket, v=96)
fr2 = cyl(R + 0.035, 4.2, (0, 0, 51.0), M_FROST, rocket, v=96)
# landing legs (folded) and grid fins (stowed)
for k in range(4):
    a = k*math.pi/2 + math.pi/4
    lg = box(f"leg{k}", (0.32, 0.9, 9.6), ((R + 0.18)*math.cos(a), (R + 0.18)*math.sin(a), 6.8), M_BLACK, rocket)
    lg.rotation_euler = (0, 0, a)
    gf = box(f"gf{k}", (0.15, 1.4, 1.2), ((R + 0.1)*math.cos(a + math.pi/4), (R + 0.1)*math.sin(a + math.pi/4), 47.5), M_STEEL, rocket)
    gf.rotation_euler = (0, 0, a + math.pi/4)
# 9 engines
for k in range(9):
    if k == 8: x, y = 0, 0
    else: x, y = 1.25*math.cos(k*math.pi/4), 1.25*math.sin(k*math.pi/4)
    cone(0.5, 0.22, 1.5, (x, y, 0.75), M_NOZ, rocket, v=24, open_=True)
rocket.location = (0, 0, MZ + 1.0)

# ------------------------------------------------------------------ flames + light
M_FL = flame_mat("fl", (1.0, 0.5, 0.18), (1.0, 0.92, 0.8), 40)
flame = cone(2.6, 0.9, 30, (0, 0, -15), M_FL, rocket, v=32)
fl_d = bpy.data.lights.new("fl", 'POINT'); fl_d.color = (1.0, 0.6, 0.28); fl_d.shadow_soft_size = 5
fl = bpy.data.objects.new("fl", fl_d); coll.objects.link(fl)

# ------------------------------------------------------------------ pad
box("mount", (14, 14, MZ), (0, 0, MZ/2), M_MOUNT)
box("mount_top", (14.5, 14.5, 0.4), (0, 0, MZ + 0.2), M_STEEL)
box("hole", (6, 6, 0.5), (0, 0, MZ + 0.25), principled("hole", (0.003, 0.003, 0.003), 0.9))
for k in range(4):
    a = k*math.pi/2 + math.pi/4
    box(f"clamp{k}", (0.9, 0.9, 1.6), (3.0*math.cos(a), 3.0*math.sin(a), MZ + 0.8), M_STEEL)
TX, TW, TH = 7.2, 3.6, 66.0
for (dx, dy) in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
    box(f"tl{dx}{dy}", (0.45, 0.45, TH), (TX + dx*TW/2, dy*TW/2, MZ + TH/2), M_STEEL)
for z in range(0, int(TH), 4):
    zz = MZ + z + 2
    for dy in (-1, 1):
        box(f"bx{z}{dy}", (TW, 0.25, 0.25), (TX, dy*TW/2, zz), M_STEEL)
        L_ = math.hypot(TW, 4); box(f"dx{z}{dy}", (L_, 0.18, 0.18), (TX, dy*TW/2, zz + 2), M_STEEL, rot=(0, math.atan2(4, TW)*(1 if z % 8 else -1), 0))
    for dx in (-1, 1):
        box(f"by{z}{dx}", (0.25, TW, 0.25), (TX + dx*TW/2, 0, zz), M_STEEL)
        L_ = math.hypot(TW, 4); box(f"dy{z}{dx}", (0.18, L_, 0.18), (TX + dx*TW/2, 0, zz + 2), M_STEEL, rot=(math.atan2(4, TW)*(1 if z % 8 else -1), 0, 0))
for zz in (MZ + 20, MZ + 44):
    box(f"arm{zz}", (TX - TW/2 - R, 0.5, 0.5), ((TX - TW/2 + R)/2 + 0.05, 0, zz), M_STEEL)
bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=120, depth=1.0, location=(0, 0, -0.5))
bpy.context.object.data.materials.append(M_CONC); bpy.context.object.rotation_euler = (0, 0, math.pi/8)
box("trench", (10, 120, 2), (0, 60, -0.1), principled("trenchdark", (0.01, 0.01, 0.01), 0.9))
bpy.ops.mesh.primitive_plane_add(size=40000, location=(0, 0, -0.9)); bpy.context.object.data.materials.append(M_GRASS)
for (x, y) in ((-90, -70), (90, -70), (0, 110)):
    cyl(1.2, 100, (x, y, 50), principled("lt", (0.6, 0.6, 0.6), 0.6), v=12)
WT = (-200, 180, 0)
bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=9, location=(WT[0], WT[1], 60))
bpy.context.object.data.materials.append(principled("wt", (0.75, 0.76, 0.76), 0.4, 0.4))
for k in range(8):
    a = k*math.pi/4; cyl(0.6, 58, (WT[0] + 7*math.cos(a), WT[1] + 7*math.sin(a), 29), M_STEEL, v=8)
M_BUSH = noisy("bush", (0.05, 0.07, 0.03), 0.9, scale=0.2, amt=0.6)
for k in range(260):
    r = rnd.uniform(160, 1400); a = rnd.uniform(0, 2*math.pi)
    if math.sin(a) < 0.2 and r < 1000: continue
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=(r*math.cos(a), r*math.sin(a), 0))
    o = bpy.context.object; s = rnd.uniform(3, 8); o.scale = (s*rnd.uniform(1, 2.5), s, s*0.35); o.data.materials.append(M_BUSH)
wm = bpy.data.materials.new("ocean"); wm.use_nodes = True
bw = wm.node_tree.nodes["Principled BSDF"]; bw.inputs["Base Color"].default_value = (0.004, 0.015, 0.025, 1); bw.inputs["Roughness"].default_value = 0.08
bpy.ops.mesh.primitive_plane_add(size=60000, location=(31000, 0, -0.6)); bpy.context.object.data.materials.append(wm)

# ------------------------------------------------------------------ vapour wisps, exhaust clouds, ice flakes
M_STEAM, D_STEAM = steam_mat()
def puff(r=1.0, sub=4):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=1, location=(0, 0, -80))
    o = bpy.context.object; o.data.materials.append(M_STEAM)
    for pp in o.data.polygons: pp.use_smooth = True
    tx = bpy.data.textures.new(f"cl{o.name}", 'CLOUDS'); tx.noise_scale = 0.45; tx.noise_depth = 3
    dm = o.modifiers.new("d", 'DISPLACE'); dm.texture = tx; dm.strength = 0.45; dm.texture_coords = 'LOCAL'
    o.rotation_euler = (rnd.uniform(0, 6), rnd.uniform(0, 6), rnd.uniform(0, 6)); return o
WISPS = []
for k in range(10):
    WISPS.append(dict(ob=puff(), ph=k/10, z=rnd.choice([40.5, 41.0, 49.0, 52.5]), a=rnd.uniform(-0.6, 0.6)))
PUFFS = []
for i in range(20):
    PUFFS.append(dict(ob=puff(sub=5), f=rnd.uniform(0.7, 1.3), dz=rnd.uniform(-0.3, 0.6), dx=rnd.uniform(-1, 1),
                      lag=rnd.uniform(0, 1.2), g=rnd.uniform(0.25, 1.0), side=1 if i % 4 else -1))
FLAKES = []
for k in range(260):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1, location=(0, 0, -100))
    o = bpy.context.object; o.data.materials.append(M_FLAKE)
    s = rnd.uniform(0.3, 0.9) if k % 5 else rnd.uniform(0.9, 1.8)
    o.scale = (s, s*rnd.uniform(0.5, 1.0), s*0.12)
    if k % 5 == 0: zr = rnd.uniform(49.2, 52.5)
    else: zr = rnd.uniform(19, 39)
    a = rnd.uniform(-math.pi*0.95, -math.pi*0.05) if k % 4 else rnd.uniform(-math.pi, math.pi)
    FLAKES.append(dict(ob=o, tr=T_LIFT + 0.4 + rnd.uniform(0, 9.5), a=a, zr=zr, vr=rnd.uniform(0.6, 2.5),
                       spin=Vector((rnd.uniform(-4, 4), rnd.uniform(-4, 4), rnd.uniform(-3, 3))), r0=Euler((rnd.uniform(0, 6), rnd.uniform(0, 6), rnd.uniform(0, 6)))))

set_sun(4.5, -160, 4.0, (1.0, 0.64, 0.40), 0.22)
ACC = 4.0
def rocket_z(t):
    u = max(0.0, t - T_LIFT); return MZ + 1.0 + 0.5*ACC*u*u

def pose(t):
    rz = rocket_z(t)
    rocket.location = (0, 0, rz)
    ki = ease((t - T_IGN)/0.5); kl = ease((t - T_IGN - 0.6)/1.2)
    flame.hide_render = ki <= 0.01
    f = 1 + 0.06*math.sin(t*53) + 0.03*math.sin(t*31)
    flame.scale = (ki*f*(0.8 + 0.2*kl), ki*f*(0.8 + 0.2*kl), ki*f*(0.6 + 0.4*kl))
    fl.location = (0, 0, rz - 6); fl_d.energy = 1.4e7*ki
    # pre-launch venting: wisps drift downwind (+x) and sink a bit
    for w in WISPS:
        p = (t*0.22 + w["ph"]) % 1.0
        on = t < T_LIFT + 1.5
        ob = w["ob"]; ob.hide_render = (not on) or p > 0.92
        s = 0.5 + 3.2*p
        ob.location = (R*math.cos(w["a"]) + 1.0 + 11*p, R*math.sin(w["a"]) - 1.0, rz + w["z"] - 3.0*p)
        ob.scale = (s*1.4, s, s*0.8)
    # exhaust clouds from the trench and around the mount
    for p in PUFFS:
        u = t - (T_IGN + 0.2 + p["lag"]); ob = p["ob"]
        if u <= 0: ob.hide_render = True; continue
        ob.hide_render = False
        reach = (90 if p["side"] > 0 else 35)*p["g"]*(1 - math.exp(-u/2.6))
        r = (3.5 + 6.5*p["f"]*(1 - math.exp(-u/2.0)))*(1.0 + 0.4*kl)*(1.0 if p["side"] > 0 else 0.7)
        ob.location = (p["dx"]*(4 + 0.25*reach), p["side"]*(9 + reach), r*0.45 + p["dz"]*r + 0.5*u)
        ob.scale = (r*1.2, r, r*0.8)
    D_STEAM.inputs[1].default_value = 6.0*ki
    # shedding ice
    for fk in FLAKES:
        ob = fk["ob"]; u = t - fk["tr"]
        if u <= 0 or u > 9: ob.hide_render = True; continue
        v0 = ACC*(fk["tr"] - T_LIFT)
        z = rocket_z(fk["tr"]) + fk["zr"] + v0*(1 - math.exp(-1.5*u))/1.5 - 0.5*9.81*u*u
        if z < MZ + 0.5: ob.hide_render = True; continue
        ob.hide_render = False
        rr = R + 0.1 + fk["vr"]*u
        ob.location = (rr*math.cos(fk["a"]), rr*math.sin(fk["a"]), z)
        ob.rotation_euler = Euler((fk["r0"].x + fk["spin"].x*u, fk["r0"].y + fk["spin"].y*u, fk["r0"].z + fk["spin"].z*u))
    # camera
    if SHOT == "A":
        k = ease(t/7.0); cam_d.lens = lerp(130, 145, k)
        aim((-150, -820, 6), (0, 0, lerp(42, 44, k)), t, math.radians(0.03))
    elif SHOT == "B":
        k = ease((t - 7.0)/9.4); cam_d.lens = 300
        aim((-30, -115, 10), (0, 0, lerp(31, 49, k)), t, math.radians(0.02))
    elif SHOT == "C":
        k = ease((t - 16.4)/6.1); cam_d.lens = lerp(70, 76, k)
        tz = 40 + max(0, rz - MZ - 1)*0.6
        aim((-90, -400, 4), (0, 0, tz), t, math.radians(0.03 + 0.12*ease((t - T_IGN)/0.6)))
    else:
        cam_d.lens = 190
        tz = rz + 26
        aim((-70, -330, 45), (0, 0, tz), t, math.radians(0.06))

# ------------------------------------------------------------------ render
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.cycles.samples = int(os.environ.get("SPP", "10")); sc.cycles.use_denoising = True; sc.cycles.use_adaptive_sampling = True
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transparent_max_bounces = 6
sc.cycles.volume_bounces = 0; sc.cycles.volume_step_rate = 8.0; sc.cycles.volume_max_steps = 24
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
        meta[i] = {"frost": screen(rocket.matrix_world @ Vector((-R, 0, 30))), "frost2": screen(rocket.matrix_world @ Vector((-R, 0, 51))), "fall": screen((-4.0, -3.0, rocket_z(t) + 10)), "base": screen((0, 0, rocket_z(t))), "top": screen((0, 0, rocket_z(t) + 74)), "alt": rocket_z(t) - MZ - 1}
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
