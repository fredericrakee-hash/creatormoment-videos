import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import bpy, bmesh, math, json, sys, os, random
from mathutils import Vector, Euler, Matrix
from bpy_extras.object_utils import world_to_camera_view

FPS = 30
RES = (1080, 1920)
OUT = os.environ.get("OUT", QDIR)
SHOT = os.environ.get("SHOT", "A")
A_END, B_START, B_END = 19.0, 19.0, 29.0

def ease(x):
    x = max(0.0, min(1.0, x)); return x*x*(3-2*x)
def lerp(a, b, k): return a + (b-a)*k

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
coll = sc.collection

# ---------------------------------------------------------------- materials
def principled(name, color, rough=0.4, metal=0.0, coat=0.0, emit=None, estr=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = estr
    return m

def sooty_white(name):
    """White booster paint with vertical soot streaks, heavier towards the engines and on one side."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.45
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (6, 6, 0.25)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 3.0; nz.inputs["Detail"].default_value = 10
    nz.inputs["Roughness"].default_value = 0.65
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep.inputs[0])
    # height factor: 1 at bottom (z=0) -> 0 at z=34
    hz = nt.nodes.new("ShaderNodeMapRange"); hz.inputs[1].default_value = 34; hz.inputs[2].default_value = 0
    nt.links.new(sep.outputs["Z"], hz.inputs[0])
    # side factor (soot heavier on +X side)
    sx = nt.nodes.new("ShaderNodeMapRange"); sx.inputs[1].default_value = -2.0; sx.inputs[2].default_value = 2.0
    sx.inputs[3].default_value = 0.35; sx.inputs[4].default_value = 1.0
    nt.links.new(sep.outputs["X"], sx.inputs[0])
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'
    nt.links.new(hz.outputs[0], mul.inputs[0]); nt.links.new(sx.outputs[0], mul.inputs[1])
    mul2 = nt.nodes.new("ShaderNodeMath"); mul2.operation = 'MULTIPLY'
    nt.links.new(mul.outputs[0], mul2.inputs[0]); nt.links.new(nz.outputs["Fac"], mul2.inputs[1])
    pw = nt.nodes.new("ShaderNodeMath"); pw.operation = 'MULTIPLY'; pw.inputs[1].default_value = 1.9
    nt.links.new(mul2.outputs[0], pw.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB"); cr = ramp.color_ramp
    cr.elements[0].position = 0.35; cr.elements[0].color = (0.85, 0.85, 0.84, 1)
    cr.elements[1].position = 0.95; cr.elements[1].color = (0.06, 0.05, 0.045, 1)
    e = cr.elements.new(0.62); e.color = (0.45, 0.40, 0.34, 1)
    nt.links.new(pw.outputs[0], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange"); rr.inputs[3].default_value = 0.4; rr.inputs[4].default_value = 0.85
    nt.links.new(pw.outputs[0], rr.inputs[0]); nt.links.new(rr.outputs[0], b.inputs["Roughness"])
    return m

M_BODY = sooty_white("body")
M_INTER = principled("interstage", (0.025, 0.025, 0.028), 0.55)
M_TI = principled("titanium", (0.42, 0.40, 0.38), 0.38, 1.0, emit=(1.0, 0.32, 0.06), estr=0.0)
M_DARK = principled("darkmetal", (0.05, 0.05, 0.055), 0.35, 0.8)
M_NOZ = principled("nozzle", (0.18, 0.13, 0.10), 0.3, 1.0)
M_LEG = principled("legs", (0.03, 0.03, 0.035), 0.4, 0.2)
M_FOOT = principled("foot", (0.6, 0.6, 0.62), 0.3, 1.0)

def link(ob, parent):
    ob.parent = parent; return ob

def smooth(ob):
    for p in ob.data.polygons: p.use_smooth = True

def cube(name, size, loc, mat, parent):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object; o.name = name; o.scale = size; o.data.materials.append(mat); return link(o, parent)

# ---------------------------------------------------------------- booster (z=0 at engine bells' exit plane)
booster = bpy.data.objects.new("booster", None); coll.objects.link(booster)
R = 1.83
bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=R, depth=33.0, location=(0, 0, 2.2+16.5))
o = bpy.context.object; o.data.materials.append(M_BODY); smooth(o); link(o, booster)
bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=R+0.01, depth=6.3, location=(0, 0, 35.2+3.15))
o = bpy.context.object; o.data.materials.append(M_INTER); smooth(o); link(o, booster)
# top ring / open interstage rim
bpy.ops.mesh.primitive_torus_add(major_radius=R-0.05, minor_radius=0.08, location=(0, 0, 41.5))
o = bpy.context.object; o.data.materials.append(M_DARK); link(o, booster)
# octaweb + heat shield
bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=R, depth=0.6, location=(0, 0, 1.9))
o = bpy.context.object; o.data.materials.append(M_DARK); smooth(o); link(o, booster)
# raceway along the side
cube("raceway", (0.25, 0.35, 32), (0, -R-0.1, 18.5), M_BODY, booster)
# 9 engines: 8 around + 1 centre
eng_pos = [(0, 0)] + [(1.25*math.cos(a), 1.25*math.sin(a)) for a in [i*math.pi/4 for i in range(8)]]
for (x, y) in eng_pos:
    bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=0.46, radius2=0.2, depth=1.5, location=(x, y, 0.9), end_fill_type='NOTHING')
    o = bpy.context.object; o.data.materials.append(M_NOZ); smooth(o)
    s = o.modifiers.new("s", 'SOLIDIFY'); s.thickness = 0.03; link(o, booster)

# grid fins: lattice panel built in local space (hinge at origin, panel extends +Y (span) and +X (chord))
def grid_fin(name):
    bm = bmesh.new()
    def box(cx, cy, cz, sx, sy, sz, rot=0.0):
        r = bmesh.ops.create_cube(bm, size=1.0)
        vs = r["verts"]
        for v in vs:
            v.co.x *= sx; v.co.y *= sy; v.co.z *= sz
            if rot:
                x, y = v.co.x, v.co.y
                v.co.x = x*math.cos(rot) - y*math.sin(rot); v.co.y = x*math.sin(rot) + y*math.cos(rot)
            v.co.x += cx; v.co.y += cy; v.co.z += cz
    W_, Hh, D = 1.25, 1.6, 0.32     # chord (x), span (y), depth (z, flow direction)
    t = 0.05
    # outer frame
    box(0, Hh/2, 0, W_, t, D); box(0, -Hh/2, 0, W_, t, D)
    box(W_/2, 0, 0, t, Hh, D); box(-W_/2, 0, 0, t, Hh, D)
    # diagonal lattice (+/-45 deg), each bar trimmed exactly to the frame
    for sgn in (1, -1):
        dx, dy = math.cos(sgn*math.pi/4), math.sin(sgn*math.pi/4)
        nx, ny = -dy, dx
        for kk in range(-9, 10):
            c = kk*0.13
            ss = []
            for (px, py, qx, qy) in ((W_/2, None, None, None), (-W_/2, None, None, None)):
                pass
            lo, hi = -10.0, 10.0
            # x limits
            if abs(dx) > 1e-6:
                a1 = (-W_/2 - c*nx)/dx; a2 = (W_/2 - c*nx)/dx
                lo = max(lo, min(a1, a2)); hi = min(hi, max(a1, a2))
            if abs(dy) > 1e-6:
                b1 = (-Hh/2 - c*ny)/dy; b2 = (Hh/2 - c*ny)/dy
                lo = max(lo, min(b1, b2)); hi = min(hi, max(b1, b2))
            if hi - lo < 0.05: continue
            mid = (lo+hi)/2
            box(c*nx + mid*dx, c*ny + mid*dy, 0, hi-lo, 0.03, D*0.92, sgn*math.pi/4)
    # root fitting
    box(0, -Hh/2-0.15, 0, 0.5, 0.3, 0.4)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob); ob.data.materials.append(M_TI)
    return ob

fins = []
for k in range(4):
    ang = k*math.pi/2 + math.pi/4
    hinge = bpy.data.objects.new(f"hinge{k}", None); coll.objects.link(hinge); link(hinge, booster)
    hinge.location = (math.cos(ang)*(R+0.05), math.sin(ang)*(R+0.05), 39.6)
    hinge.rotation_euler = (0, 0, ang)            # local +X points radially outward
    pivot = bpy.data.objects.new(f"pivot{k}", None); coll.objects.link(pivot); link(pivot, hinge)
    f = grid_fin(f"fin{k}"); link(f, pivot)
    # deployed layout in pivot space: span along +X (radial), flow along Z
    f.rotation_euler = (0, 0, -math.pi/2); f.location = (0.95, 0, 0)
    fins.append((hinge, pivot, f))

def set_fins(deploy, steer, glow):
    # deploy: 0 stowed (span pointing up along body) -> 1 deployed (span radial)
    for k, (h, p, f) in enumerate(fins):
        h.rotation_euler = (0, -(1-deploy)*math.pi/2, k*math.pi/2 + math.pi/4)
        p.rotation_euler = (steer*(1 if k % 2 else -1), 0, 0)
    M_TI.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = glow

# landing legs: 4 carbon legs hinged near the bottom, stowed along the body pointing up
legs = []
for k in range(4):
    ang = k*math.pi/2
    hg = bpy.data.objects.new(f"leghinge{k}", None); coll.objects.link(hg); link(hg, booster)
    hg.location = (math.cos(ang)*(R+0.12), math.sin(ang)*(R+0.12), 2.6)
    hg.rotation_euler = (0, 0, ang)
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.42, depth=9.5, location=(0, 0, 4.75))
    lg = bpy.context.object; lg.scale = (0.7, 1.4, 1); lg.data.materials.append(M_LEG); link(lg, hg)
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.65, depth=0.25, location=(0, 0, 9.5))
    ft = bpy.context.object; ft.data.materials.append(M_FOOT); link(ft, hg)
    legs.append(hg)

def set_legs(deploy):
    for k, hg in enumerate(legs):
        hg.rotation_euler = (0, deploy*math.radians(152), k*math.pi/2)

# engine flame (landing burn): emissive cones under the centre engine
def flame_mat():
    m = bpy.data.materials.new("flame"); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission"); tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader"); add = nt.nodes.new("ShaderNodeAddShader")
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB"); cr = ramp.color_ramp
    cr.elements[0].position = 0.0; cr.elements[0].color = (1.0, 0.45, 0.12, 1)
    cr.elements[1].position = 0.85; cr.elements[1].color = (1.0, 0.95, 0.85, 1)
    nt.links.new(sep.outputs["Z"], ramp.inputs[0])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 6
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    strength = nt.nodes.new("ShaderNodeMath"); strength.operation = 'MULTIPLY'; strength.inputs[1].default_value = 30
    nt.links.new(nz.outputs["Fac"], strength.inputs[0])
    nt.links.new(ramp.outputs[0], em.inputs["Color"]); nt.links.new(strength.outputs[0], em.inputs["Strength"])
    fac = nt.nodes.new("ShaderNodeMapRange"); fac.inputs[1].default_value = 0.0; fac.inputs[2].default_value = 1.0
    fac.inputs[3].default_value = 0.15; fac.inputs[4].default_value = 0.9
    nt.links.new(sep.outputs["Z"], fac.inputs[0])
    nt.links.new(fac.outputs[0], mix.inputs[0]); nt.links.new(em.outputs[0], mix.inputs[2]); nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(mix.outputs[0], out.inputs[0])
    return m
M_FLAME = flame_mat()
bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=1.5, radius2=0.3, depth=18, location=(0, 0, -9.0))
flame = bpy.context.object; flame.data.materials.append(M_FLAME); link(flame, booster)
bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=0.25, radius2=0.5, depth=4.5, location=(0, 0, -2.2))
core = bpy.context.object; core.data.materials.append(principled("core", (1, 0.9, 0.8), emit=(1.0, 0.85, 0.65), estr=60)); link(core, booster)
fl_d = bpy.data.lights.new("flamelight", 'POINT'); fl_d.color = (1.0, 0.6, 0.3); fl_d.shadow_soft_size = 3
fl = bpy.data.objects.new("flamelight", fl_d); coll.objects.link(fl); link(fl, booster); fl.location = (0, 0, -6)

def set_flame(k, t):
    on = k > 0.01
    for o in (flame, core): o.hide_render = not on
    f = 1 + 0.08*math.sin(t*61) + 0.05*math.sin(t*37)
    flame.scale = (k*f, k*f, (0.4 + 0.6*k)*f)
    core.scale = (k, k, k)
    fl_d.energy = 2.5e6*k

# ---------------------------------------------------------------- environment
wo = bpy.data.worlds.new("w"); sc.world = wo; wo.use_nodes = True
bg = wo.node_tree.nodes["Background"]
sky = wo.node_tree.nodes.new("ShaderNodeTexSky"); sky.sky_type = 'MULTIPLE_SCATTERING'
wo.node_tree.links.new(sky.outputs[0], bg.inputs[0])
sun_d = bpy.data.lights.new("sun", 'SUN'); sun_d.angle = math.radians(0.6)
sun = bpy.data.objects.new("sun", sun_d); coll.objects.link(sun)

def set_sun(el, rot, energy, color, sky_alt, bgs):
    sky.sun_elevation = math.radians(el); sky.sun_rotation = math.radians(rot)
    sky.altitude = sky_alt; sky.aerosol_density = 1.4; sky.sun_intensity = 0.5
    bg.inputs[1].default_value = bgs
    sun_d.energy = energy; sun_d.color = color
    sun.rotation_euler = Euler((math.radians(90-el), 0, math.radians(rot+90)))

cam_d = bpy.data.cameras.new("cam"); cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 36; cam_d.clip_end = 200000
cam = bpy.data.objects.new("cam", cam_d); coll.objects.link(cam); sc.camera = cam
rnd = random.Random(7)
SH = [(rnd.uniform(-1, 1), rnd.uniform(-1, 1)) for _ in range(400)]
def shake(t, amp, rate=3.0):
    i = int(t*rate); f = t*rate - i; a, b = SH[i % 400], SH[(i+1) % 400]; f = f*f*(3-2*f)
    return (a[0]+(b[0]-a[0])*f)*amp, (a[1]+(b[1]-a[1])*f)*amp

def aim(loc, tgt, t, amp):
    cam.location = loc
    e = (Vector(tgt)-Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sx, sy = shake(t, amp); e.x += sx; e.z += sy; cam.rotation_euler = e

if SHOT == "A":
    # ---------------- high altitude descent: booster stays near origin, clouds rise towards it
    set_sun(9, 40, 4.0, (1.0, 0.85, 0.7), 22000, 0.35)
    bpy.ops.mesh.primitive_plane_add(size=400000, location=(0, 0, -14000))
    deck = bpy.context.object
    cm = bpy.data.materials.new("clouds"); cm.use_nodes = True; nt = cm.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 1.0
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 0.00012; n1.inputs["Detail"].default_value = 14
    n1.inputs["Roughness"].default_value = 0.7; n1.inputs["Distortion"].default_value = 0.6
    nt.links.new(tc.outputs["Object"], n1.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB"); cr = ramp.color_ramp
    cr.elements[0].position = 0.42; cr.elements[0].color = (0.30, 0.36, 0.46, 1)
    cr.elements[1].position = 0.60; cr.elements[1].color = (1.1, 1.08, 1.06, 1)
    nt.links.new(n1.outputs["Fac"], ramp.inputs[0]); nt.links.new(ramp.outputs[0], b.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 1.0; bump.inputs["Distance"].default_value = 600
    nt.links.new(n1.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    deck.data.materials.append(cm)
    cam_d.lens = 40

    def pose(t):
        deck.location.z = lerp(-14000, -9000, t/A_END)
        deck.location.x = -t*40
        dep = ease((t-8.6)/1.8)
        steer = 0.0
        if t > 13.3:
            steer = math.radians(16)*math.sin((t-13.3)*1.6)*ease((t-13.3)/0.8)
        glow = 0.22*ease((t-9.0)/2.0)*(1-0.6*ease((t-14)/5))
        set_fins(dep, steer, glow)
        set_legs(0); set_flame(0, t)
        tilt = math.radians(3)*math.sin(t*0.4) + (steer*0.35)
        booster.location = (0, 0, 0); booster.rotation_euler = (tilt, math.radians(4), 0)
        ang = math.radians(lerp(-30, 35, t/A_END))
        k = ease((t-7.5)/3.5)
        d = lerp(lerp(80, 70, t/8), lerp(12, 9.5, (t-11)/8), k)
        loc = (d*math.sin(ang), -d*math.cos(ang), lerp(18, 31.5, k))
        bpy.context.view_layer.update()
        tgt = booster.matrix_world @ Vector((0, 0, lerp(22, 39.0, k)))
        loc = booster.matrix_world @ Vector(loc)
        aim(loc, tgt, t, math.radians(0.25))
else:
    # ---------------- landing on the droneship at sea
    set_sun(6, 230, 3.5, (1.0, 0.68, 0.45), 0, 0.16)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
    sea = bpy.context.object
    oc = sea.modifiers.new("ocean", 'OCEAN')
    oc.geometry_mode = 'GENERATE'; oc.size = 1.0; oc.spatial_size = 400; oc.resolution = 10
    oc.repeat_x = 4; oc.repeat_y = 4; oc.wave_scale = 4.0; oc.choppiness = 1.3; oc.wind_velocity = 16
    oc.random_seed = 3
    sea.location = (-800, -800, 0)
    wm = bpy.data.materials.new("water"); wm.use_nodes = True
    b = wm.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.002, 0.012, 0.02, 1); b.inputs["Roughness"].default_value = 0.12
    b.inputs["IOR"].default_value = 1.33
    sea.data.materials.append(wm)
    # far sea plane to the horizon
    bpy.ops.mesh.primitive_plane_add(size=200000, location=(0, 0, -0.3))
    far = bpy.context.object; far.data.materials.append(wm)
    # droneship (barge)
    ship = bpy.data.objects.new("ship", None); coll.objects.link(ship)
    M_DECK = bpy.data.materials.new("deck"); M_DECK.use_nodes = True; nt = M_DECK.node_tree
    bd = nt.nodes["Principled BSDF"]; bd.inputs["Roughness"].default_value = 0.7
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep.inputs[0])
    # landing target: ring + cross painted white on dark deck
    lx = nt.nodes.new("ShaderNodeMath"); lx.operation = 'ABSOLUTE'; nt.links.new(sep.outputs["X"], lx.inputs[0])
    ly = nt.nodes.new("ShaderNodeMath"); ly.operation = 'ABSOLUTE'; nt.links.new(sep.outputs["Y"], ly.inputs[0])
    vlen = nt.nodes.new("ShaderNodeVectorMath"); vlen.operation = 'LENGTH'; nt.links.new(tc.outputs["Object"], vlen.inputs[0])
    ring = nt.nodes.new("ShaderNodeMapRange"); ring.inputs[1].default_value = 13.6; ring.inputs[2].default_value = 14.6
    ring.interpolation_type = 'STEPPED'
    r1 = nt.nodes.new("ShaderNodeMath"); r1.operation = 'COMPARE'; r1.inputs[1].default_value = 14.1; r1.inputs[2].default_value = 0.5
    nt.links.new(vlen.outputs["Value"], r1.inputs[0])
    diff = nt.nodes.new("ShaderNodeMath"); diff.operation = 'SUBTRACT'
    nt.links.new(lx.outputs[0], diff.inputs[0]); nt.links.new(ly.outputs[0], diff.inputs[1])
    cross = nt.nodes.new("ShaderNodeMath"); cross.operation = 'COMPARE'; cross.inputs[1].default_value = 0.0; cross.inputs[2].default_value = 0.6
    nt.links.new(diff.outputs[0], cross.inputs[0])
    inside = nt.nodes.new("ShaderNodeMath"); inside.operation = 'LESS_THAN'; inside.inputs[1].default_value = 11.0
    nt.links.new(vlen.outputs["Value"], inside.inputs[0])
    cin = nt.nodes.new("ShaderNodeMath"); cin.operation = 'MULTIPLY'; nt.links.new(cross.outputs[0], cin.inputs[0]); nt.links.new(inside.outputs[0], cin.inputs[1])
    paint = nt.nodes.new("ShaderNodeMath"); paint.operation = 'MAXIMUM'; nt.links.new(r1.outputs[0], paint.inputs[0]); nt.links.new(cin.outputs[0], paint.inputs[1])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.4; nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    mixc = nt.nodes.new("ShaderNodeMix"); mixc.data_type = 'RGBA'
    mixc.inputs[6].default_value = (0.05, 0.05, 0.055, 1); mixc.inputs[7].default_value = (0.75, 0.74, 0.7, 1)
    nt.links.new(paint.outputs[0], mixc.inputs["Factor"])
    grime = nt.nodes.new("ShaderNodeMix"); grime.data_type = 'RGBA'; grime.blend_type = 'MULTIPLY'; grime.inputs["Factor"].default_value = 0.5
    nt.links.new(mixc.outputs[2], grime.inputs[6]); nt.links.new(nz.outputs["Color"], grime.inputs[7])
    nt.links.new(grime.outputs[2], bd.inputs["Base Color"])
    M_HULL = principled("hull", (0.08, 0.085, 0.09), 0.6, 0.3)
    M_YEL = principled("yellow", (0.8, 0.55, 0.05), 0.5)
    cube("deck", (90, 52, 0.4), (0, 0, 2.6), M_DECK, ship)
    cube("hull", (90, 52, 6.5), (0, 0, -0.9), M_HULL, ship)
    for sx in (-1, 1):
        cube(f"wall{sx}", (4, 52, 6), (sx*43, 0, 5.8), M_HULL, ship)          # blast walls at both ends
        for sy in (-1, 1):
            cube(f"pod{sx}{sy}", (8, 8, 4), (sx*40, sy*28, 0.5), M_HULL, ship)  # thruster pods
            cube(f"crane{sx}{sy}", (1.2, 1.2, 9), (sx*36, sy*23, 7.2), M_YEL, ship)
    for i in range(36):                                                     # railing posts
        x = -40 + i*80/35
        for sy in (-1, 1):
            cube(f"rail{i}{sy}", (0.12, 0.12, 1.2), (x, sy*25.7, 3.4), M_YEL, ship)
    cube("railtopL", (80, 0.1, 0.1), (0, -25.7, 4.0), M_YEL, ship); cube("railtopR", (80, 0.1, 0.1), (0, 25.7, 4.0), M_YEL, ship)
    # steam / exhaust cloud (volume)
    vm = bpy.data.materials.new("steam"); vm.use_nodes = True; nt = vm.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    pv = nt.nodes.new("ShaderNodeVolumePrincipled"); pv.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1); pv.inputs["Anisotropy"].default_value = 0.3
    tcv = nt.nodes.new("ShaderNodeTexCoord"); nzv = nt.nodes.new("ShaderNodeTexNoise"); nzv.inputs["Scale"].default_value = 1.6; nzv.inputs["Detail"].default_value = 6
    nt.links.new(tcv.outputs["Object"], nzv.inputs["Vector"])
    gr = nt.nodes.new("ShaderNodeTexGradient"); gr.gradient_type = 'SPHERICAL'; nt.links.new(tcv.outputs["Object"], gr.inputs["Vector"])
    mm = nt.nodes.new("ShaderNodeMath"); mm.operation = 'MULTIPLY'; nt.links.new(nzv.outputs["Fac"], mm.inputs[0]); nt.links.new(gr.outputs["Fac"], mm.inputs[1])
    dens = nt.nodes.new("ShaderNodeMath"); dens.operation = 'MULTIPLY'; dens.inputs[1].default_value = 0.0
    nt.links.new(mm.outputs[0], dens.inputs[0]); nt.links.new(dens.outputs[0], pv.inputs["Density"])
    nt.links.new(pv.outputs[0], nt.nodes["Material Output"].inputs["Volume"])
    puffs = []
    for i in range(7):
        a = i/7*2*math.pi
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1, location=(0, 0, 4))
        p = bpy.context.object; p.data.materials.append(vm); p.hide_render = True
        puffs.append((p, a, 0.7 + 0.6*rnd.random()))
    DENS = dens
    cam_d.lens = 105
    def by(t):        # booster base height above deck (z of engine exit plane)
        k = max(0.0, min(1.0, (t-B_START)/(25.6-B_START)))
        k = 1 - (1-k)**2     # decelerating
        return 3.0 + (1 - k) * 120
    def pose(t):
        z = by(t)
        booster.location = (0.8*(1-ease((t-B_START)/6.6)), 0, z)
        booster.rotation_euler = (math.radians(2)*(1-ease((t-B_START)/6)), 0, 0)
        set_fins(1.0, math.radians(4)*math.sin(t*2.1)*(t < 25.6), 0.0)
        set_legs(ease((t-23.0)/1.3))
        burn = ease((t-19.8)/0.4)*(1-ease((t-25.9)/0.25))
        set_flame(burn*(0.9 if t > 22 else 1.0), t)
        # exhaust/steam cloud billowing on the deck
        s = ease((t-22.8)/2.0)
        DENS.inputs[1].default_value = 0.10*s*(1-0.5*ease((t-27)/2))
        for p, a, f in puffs:
            grow = 3 + 11*ease((t-23.3)/(3.5*f))
            r = 6 + 14*ease((t-23.5)/4)
            p.hide_render = s <= 0.01
            p.location = (r*math.cos(a), r*math.sin(a), 3.0 + grow*0.25)
            p.scale = (grow, grow, grow*0.55)
        loc = (-120, -330, 9.0); tgt = (0, 0, lerp(75, 26, ease((t-B_START)/6.2)))
        aim(loc, tgt, t, math.radians(0.12))

# ---------------------------------------------------------------- render settings
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.cycles.samples = int(os.environ.get("SPP", "16")); sc.cycles.use_denoising = True
sc.cycles.use_adaptive_sampling = True
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2
sc.cycles.transparent_max_bounces = 8; sc.cycles.volume_bounces = 0
sc.cycles.volume_step_rate = 6.0; sc.cycles.volume_max_steps = 48
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.resolution_percentage = int(os.environ.get("PCT", "100"))
sc.render.use_persistent_data = True
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
sc.view_settings.exposure = float(os.environ.get("EXPO", "0.0"))

def screen(p):
    v = world_to_camera_view(sc, cam, Vector(p)); return (v.x*RES[0], (1-v.y)*RES[1], v.z)

mode = sys.argv[sys.argv.index("--")+1] if "--" in sys.argv else "frames"
t0, t1 = (0.0, A_END) if SHOT == "A" else (B_START, B_END)
if mode == "test":
    for t in [float(x) for x in os.environ.get("TT", "10").split(",")]:
        pose(t); bpy.context.view_layer.update()
        sc.render.filepath = f"{OUT}/test{SHOT}_{t}.png"; bpy.ops.render.render(write_still=True)
elif mode == "meta":
    meta = {}
    for i in range(int(t0*FPS), int(t1*FPS)):
        t = i/FPS; pose(t); bpy.context.view_layer.update()
        top = booster.matrix_world @ Vector((0, 0, 40)); bot = booster.matrix_world @ Vector((0, 0, 0))
        fs = [screen(f.matrix_world @ Vector((0, 0, 0))) for (_, _, f) in fins]
        fin = min(fs, key=lambda v: v[2]) if t < A_END else fs[0]
        meta[i] = {"top": screen(top), "bot": screen(bot), "fin": fin, "alt": booster.location.z}
    json.dump(meta, open(f"{OUT}/meta{SHOT}.json", "w"))
else:
    os.makedirs(f"{OUT}/frames", exist_ok=True)
    step = int(os.environ.get("STEP", "2"))
    for i in range(int(os.environ.get('IFROM', int(t0*FPS))), int(os.environ.get('ITO', int(t1*FPS))), step):
        out = f"{OUT}/frames/f{i:04d}.png"
        if os.path.exists(out): continue
        pose(i/FPS); bpy.context.view_layer.update()
        sc.render.filepath = out; bpy.ops.render.render(write_still=True)
