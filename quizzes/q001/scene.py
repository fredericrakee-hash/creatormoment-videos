import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import bpy, bmesh, math, json, sys, os, random
from mathutils import Vector, Euler
from bpy_extras.object_utils import world_to_camera_view

FPS = 30
END = float(os.environ.get("END", "27.2"))
RES = (1080, 1920)
OUT = os.environ.get("OUT", ""+QDIR+"")

def ease(x):
    x = max(0, min(1, x)); return x*x*(3-2*x)

MEET = 24.5
def X(t): return -70 + 70*(t/MEET)
def ZL(t): return 34*ease((t-15.8)/4.2)
def ZR(t): return -34*ease((t-17.3)/4.2)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

# ---------------- materials ----------------
def principled(name, color, rough=0.3, metal=0.0, coat=0.0, emit=None, estr=0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = estr
    return m

def livery(name, accent):
    """White fuselage, grey belly, accent cheatline + subtle panel noise."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.28; b.inputs["Coat Weight"].default_value = 0.6
    b.inputs["Coat Roughness"].default_value = 0.08
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[1].default_value = -2.0; mr.inputs[2].default_value = 2.0
    nt.links.new(sep.outputs["Z"], mr.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB"); cr = ramp.color_ramp; cr.interpolation = 'LINEAR'
    cr.elements[0].position = 0.0; cr.elements[0].color = (0.42, 0.44, 0.48, 1)
    cr.elements[1].position = 0.27; cr.elements[1].color = (0.45, 0.47, 0.5, 1)
    for pos, col in [(0.29, (0.82, 0.83, 0.85, 1)), (0.40, (0.86, 0.87, 0.89, 1)), (0.405, (*accent, 1)),
                     (0.455, (*accent, 1)), (0.46, (0.86, 0.87, 0.89, 1)), (1.0, (0.88, 0.89, 0.91, 1))]:
        e = cr.elements.new(pos); e.color = col
    nt.links.new(mr.outputs[0], ramp.inputs[0])
    # subtle grime/panel variation
    noise = nt.nodes.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 3.0
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
    mix.inputs["Factor"].default_value = 0.12
    nt.links.new(ramp.outputs[0], mix.inputs[6]); nt.links.new(noise.outputs["Color"], mix.inputs[7])
    nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    return m

def smooth(ob):
    for p in ob.data.polygons: p.use_smooth = True

def link(ob, parent):
    ob.parent = parent; return ob

# ---------------- aircraft ----------------
def make_airliner(name, accent):
    root = bpy.data.objects.new(name, None); sc.collection.objects.link(root)
    paint = livery(name+"_paint", accent)
    white = principled(name+"_white", (0.86, 0.87, 0.89), 0.3, coat=0.5)
    wingm = principled(name+"_wing", (0.62, 0.64, 0.67), 0.4, 0.2)
    metal = principled(name+"_metal", (0.7, 0.71, 0.73), 0.25, 0.9)
    dark = principled(name+"_dark", (0.02, 0.02, 0.025), 0.2)
    glass = principled(name+"_glass", (0.01, 0.012, 0.02), 0.03, coat=1.0)
    tailm = principled(name+"_tail", accent, 0.3, coat=0.5)

    # fuselage: lofted rings along X (nose at +X)
    prof = [(-24.0, 0.15, 1.1), (-22.5, 0.6, 1.0), (-20, 1.15, 0.85), (-17, 1.65, 0.55), (-13, 1.95, 0.25), (-9, 2.0, 0.0),
            (12, 2.0, 0.0), (14.5, 1.95, -0.05), (16.5, 1.8, -0.12), (18.0, 1.55, -0.2), (19.2, 1.2, -0.3),
            (20.0, 0.85, -0.38), (20.6, 0.45, -0.45), (20.9, 0.05, -0.5)]
    bm = bmesh.new(); seg = 40; rings = []
    for x, r, zc in prof:
        ring = []
        for i in range(seg):
            a = 2*math.pi*i/seg
            ring.append(bm.verts.new((x, r*math.cos(a), zc + r*1.04*math.sin(a))))
        rings.append(ring)
    for j in range(len(rings)-1):
        for i in range(seg):
            bm.faces.new([rings[j][i], rings[j][(i+1) % seg], rings[j+1][(i+1) % seg], rings[j+1][i]])
    bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    me = bpy.data.meshes.new(name+"_fus"); bm.to_mesh(me); bm.free()
    fus = bpy.data.objects.new(name+"_fus", me); sc.collection.objects.link(fus)
    fus.data.materials.append(paint); smooth(fus)
    fus.modifiers.new("ws", 'WEIGHTED_NORMAL'); link(fus, root)

    def add(ob, m):
        sc.collection.objects.link(ob) if ob.name not in sc.collection.objects else None
        ob.data.materials.append(m); smooth(ob); return link(ob, root)

    # cockpit windows: thin dark band shaped by a scaled, flattened sphere intersecting nose
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1, location=(18.0, 0, 0.95))
    w = bpy.context.object; w.scale = (1.15, 1.42, 0.32); w.rotation_euler = (0, math.radians(14), 0)
    w.data.materials.append(glass); smooth(w); link(w, root)
    # cabin windows (both sides)
    for side in (-1, 1):
        for i in range(30):
            x = 13.0 - i*0.98
            if -1.5 < x < 0.2: continue   # over-wing exits gap
            bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=8, radius=0.16, location=(x, side*1.995, 0.55))
            o = bpy.context.object; o.scale = (0.85, 0.25, 1.25); o.data.materials.append(glass); link(o, root)
        # doors outline hint
        bpy.ops.mesh.primitive_cube_add(size=1, location=(14.3, side*1.99, 0.35))
        o = bpy.context.object; o.scale = (0.9, 0.02, 1.8); o.data.materials.append(principled(name+f"_door{side}", (0.7, 0.71, 0.74), 0.4)); link(o, root)

    def wing(pts, thick, m, nm):
        me = bpy.data.meshes.new(nm); me.from_pydata([Vector(p) for p in pts], [], [list(range(len(pts)))])
        ob = bpy.data.objects.new(nm, me); sc.collection.objects.link(ob)
        s = ob.modifiers.new("s", 'SOLIDIFY'); s.thickness = thick; s.offset = 0
        b = ob.modifiers.new("b", 'BEVEL'); b.width = thick*0.45; b.segments = 3
        ob.data.materials.append(m); smooth(ob); return link(ob, root)

    for side in (-1, 1):
        s = side
        # main wing with sweep + dihedral
        wing([(5.0, s*1.6, -1.0), (-4.5, s*1.6, -1.0), (-11.2, s*17.0, 0.5), (-8.9, s*17.0, 0.5)], 0.55, wingm, f"{name}_wing{s}")
        # winglet
        wing([(-8.9, s*17.0, 0.5), (-11.2, s*17.0, 0.5), (-12.6, s*17.25, 3.0), (-11.6, s*17.25, 3.0)], 0.22, tailm, f"{name}_wl{s}")
        # flap track fairings
        for k, y in enumerate((4.5, 8.5, 12.5)):
            x0 = -4.5 - (y-1.6)/(17-1.6)*6.7
            bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.22, depth=2.2, location=(x0-0.6, s*y, -0.9 + (y-1.6)*0.1), rotation=(0, math.pi/2, 0))
            o = bpy.context.object; o.scale = (1, 1, 1); o.data.materials.append(wingm); smooth(o); link(o, root)
        # engine: nacelle + intake lip + fan + exhaust cone + pylon
        ey, ez, ex = s*6.0, -2.0, 1.8
        bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=1.12, depth=4.6, location=(ex, ey, ez), rotation=(0, math.pi/2, 0))
        o = bpy.context.object; o.data.materials.append(white); smooth(o); link(o, root)
        bpy.ops.mesh.primitive_torus_add(major_radius=1.05, minor_radius=0.14, major_segments=40, minor_segments=12, location=(ex+2.3, ey, ez), rotation=(0, math.pi/2, 0))
        o = bpy.context.object; o.data.materials.append(metal); smooth(o); link(o, root)
        bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.98, depth=0.05, location=(ex+2.1, ey, ez), rotation=(0, math.pi/2, 0))
        o = bpy.context.object; o.data.materials.append(dark); link(o, root)
        bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.6, radius2=0.1, depth=1.6, location=(ex-3.0, ey, ez), rotation=(0, -math.pi/2, 0))
        o = bpy.context.object; o.data.materials.append(metal); smooth(o); link(o, root)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(ex-0.4, ey, ez+1.15))
        o = bpy.context.object; o.scale = (3.4, 0.35, 0.9); o.data.materials.append(white); link(o, root)
        # horizontal stabiliser
        wing([(-17.5, s*0.8, 1.0), (-21.5, s*0.8, 1.0), (-24.6, s*7.6, 1.9), (-23.0, s*7.6, 1.9)], 0.3, wingm, f"{name}_hs{s}")
        # nav light + strobe
        col = (0.1, 1, 0.25) if s == 1 else (1, 0.08, 0.05)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.18, location=(-10.6, s*17.15, 0.6))
        o = bpy.context.object; o.data.materials.append(principled(f"{name}_nav{s}", col, emit=col, estr=40)); link(o, root)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.16, location=(-11.4, s*17.15, 0.6))
        o = bpy.context.object; o.name = f"{name}_strobe{s}"
        sm = principled(f"{name}_strobe{s}", (1, 1, 1), emit=(1, 1, 1), estr=0); o.data.materials.append(sm); link(o, root)

    # vertical fin (in XZ plane) + rudder line
    me = bpy.data.meshes.new(name+"_fin")
    me.from_pydata([Vector(p) for p in [(-14.5, 0, 1.4), (-21.8, 0, 1.4), (-25.0, 0, 10.2), (-22.4, 0, 10.2)]], [], [[0, 1, 2, 3]])
    fin = bpy.data.objects.new(name+"_fin", me); sc.collection.objects.link(fin)
    m_ = fin.modifiers.new("s", 'SOLIDIFY'); m_.thickness = 0.45; m_.offset = 0
    m_ = fin.modifiers.new("b", 'BEVEL'); m_.width = 0.18; m_.segments = 3
    fin.data.materials.append(tailm); smooth(fin); link(fin, root)
    # red beacon on top + belly
    for zb in (2.05, -2.05):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.16, location=(2.0, 0, zb))
        o = bpy.context.object; o.name = f"{name}_beacon{int(zb>0)}"
        o.data.materials.append(principled(f"{name}_beacon{int(zb>0)}", (1, 0.05, 0.02), emit=(1, 0.05, 0.02), estr=0)); link(o, root)
    return root

L = make_airliner("L", (0.04, 0.16, 0.55))   # deep blue airline
R = make_airliner("R", (0.62, 0.08, 0.06))   # dark red airline

def set_lights(root, t, phase):
    # strobes: double flash every 1.2 s ; beacon 1 Hz
    st = ((t + phase) % 1.2)
    on_s = st < 0.05 or 0.12 < st < 0.17
    on_b = ((t + phase*0.7) % 1.0) < 0.12
    for o in root.children:
        if "strobe" in o.name:
            o.active_material.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 600 if on_s else 0
        if "beacon" in o.name:
            o.active_material.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 120 if on_b else 2

# ---------------- environment ----------------
wo = bpy.data.worlds.new("w"); sc.world = wo; wo.use_nodes = True
bg = wo.node_tree.nodes["Background"]
sky = wo.node_tree.nodes.new("ShaderNodeTexSky")
sky.sky_type = 'MULTIPLE_SCATTERING'
SUNEL = float(os.environ.get("SUNEL","3")); SUNROT = float(os.environ.get("SUNROT","60"))
sky.sun_elevation = math.radians(SUNEL); sky.sun_rotation = math.radians(SUNROT)
sky.altitude = 10000; sky.air_density = 1.0; sky.aerosol_density = 1.6; sky.sun_intensity = 0.6
wo.node_tree.links.new(sky.outputs[0], bg.inputs[0]); bg.inputs[1].default_value = 0.45

sun_d = bpy.data.lights.new("sun", 'SUN'); sun_d.energy = 3.2; sun_d.color = (1.0, 0.68, 0.45); sun_d.angle = math.radians(0.6)
sun = bpy.data.objects.new("sun", sun_d); sc.collection.objects.link(sun)
sun.rotation_euler = Euler((math.radians(90-SUNEL), 0, math.radians(SUNROT+90)))

# cloud deck far below: large plane, noise-driven
bpy.ops.mesh.primitive_plane_add(size=60000, location=(0, 0, -1500))
deck = bpy.context.object
cm = bpy.data.materials.new("clouds"); cm.use_nodes = True; nt = cm.node_tree
b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 1.0
tc = nt.nodes.new("ShaderNodeTexCoord")
n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 0.0012; n1.inputs["Distortion"].default_value = 0.6; n1.inputs["Detail"].default_value = 12; n1.inputs["Roughness"].default_value = 0.7
nt.links.new(tc.outputs["Object"], n1.inputs["Vector"])
ramp = nt.nodes.new("ShaderNodeValToRGB"); cr = ramp.color_ramp
cr.elements[0].position = 0.40; cr.elements[0].color = (0.33, 0.36, 0.46, 1)
cr.elements[1].position = 0.56; cr.elements[1].color = (1.6, 1.55, 1.5, 1)
nt.links.new(n1.outputs["Fac"], ramp.inputs[0]); nt.links.new(ramp.outputs[0], b.inputs["Base Color"])
bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 1.0; bump.inputs["Distance"].default_value = 160
nt.links.new(n1.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
b.inputs["Subsurface Weight"].default_value = 0.0
deck.data.materials.append(cm)

# ---------------- camera ----------------
cam_d = bpy.data.cameras.new("cam"); cam_d.lens = 85; cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 36
cam_d.clip_end = 80000
cam = bpy.data.objects.new("cam", cam_d); sc.collection.objects.link(cam); sc.camera = cam
C0, T0 = Vector((-260, -420, -38)), Vector((0, 0, 0))
C1, T1 = Vector((-170, -290, -24)), Vector((0, 0, 0))
rnd = random.Random(5)
SHAKE = [(rnd.uniform(-1, 1), rnd.uniform(-1, 1)) for _ in range(200)]
def shake(t, amp):
    i = int(t*4); f = t*4 - i
    a = SHAKE[i % 200]; b = SHAKE[(i+1) % 200]; f = f*f*(3-2*f)
    return (a[0]+(b[0]-a[0])*f)*amp, (a[1]+(b[1]-a[1])*f)*amp

def pitch(fz, t):
    dz = (fz(t+0.05)-fz(t-0.05))/0.1
    return max(-0.13, min(0.13, math.atan2(dz, 45)))

def pose(t):
    x = X(t)
    L.location = (x, 0, ZL(t)); L.rotation_euler = (0, -pitch(ZL, t), 0)
    R.location = (-x, 0, ZR(t)); R.rotation_euler = (0, -pitch(ZR, t), math.pi)
    k = ease(t/24.0)
    cl = C0.lerp(C1, k); ct = T0.lerp(T1, k)
    cam.location = cl
    e = (ct-cl).to_track_quat('-Z', 'Y').to_euler()
    sx, sy = shake(t, math.radians(0.12))
    e.x += sx; e.z += sy
    cam.rotation_euler = e
    set_lights(L, t, 0.0); set_lights(R, t, 0.55)
    # cloud deck drift for parallax
    deck.location.x = -t*6

sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = int(os.environ.get("SPP", "12"))
sc.cycles.use_denoising = True
sc.cycles.max_bounces = 3; sc.cycles.diffuse_bounces = 1; sc.cycles.glossy_bounces = 2
sc.cycles.use_adaptive_sampling = True
sc.render.film_transparent = False
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.resolution_percentage = int(os.environ.get("PCT", "67"))
sc.render.use_persistent_data = True
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = os.environ.get('LOOK','AgX - Medium High Contrast')
sc.view_settings.exposure = float(os.environ.get("EXPO", "-0.3"))
sc.render.fps = FPS

def screen(p):
    v = world_to_camera_view(sc, cam, Vector(p))
    return (v.x*RES[0], (1-v.y)*RES[1])

mode = sys.argv[sys.argv.index("--")+1] if "--" in sys.argv else "frames"
if mode == "test":
    for t in [float(x) for x in os.environ.get('TT', '8,19').split(',')]:
        pose(t); bpy.context.view_layer.update()
        sc.render.filepath = f"{OUT}/test_{t}.png"; bpy.ops.render.render(write_still=True)
elif mode == "meta":
    meta = {}
    for i in range(int(END*FPS)):
        t = i/FPS; pose(t); bpy.context.view_layer.update()
        meta[i] = {"L": screen((X(t), 0, ZL(t))), "R": screen((-X(t), 0, ZR(t)))}
    json.dump(meta, open(f"{OUT}/meta.json", "w"))
else:
    os.makedirs(f"{OUT}/frames", exist_ok=True)
    step = int(os.environ.get("STEP", "2"))
    for i in range(0, int(END*FPS), step):
        out = f"{OUT}/frames/f{i:04d}.png"
        if os.path.exists(out): continue
        pose(i/FPS); bpy.context.view_layer.update()
        sc.render.filepath = out; bpy.ops.render.render(write_still=True)
