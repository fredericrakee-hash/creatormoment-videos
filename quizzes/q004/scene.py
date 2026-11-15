import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import bpy, bmesh, math, json, sys, os, random
from mathutils import Vector, Euler
from bpy_extras.object_utils import world_to_camera_view

FPS = 30
RES = (1080, 1920)
OUT = os.environ.get("OUT", QDIR)
SHOT = os.environ.get("SHOT", "A")
SHOTS = {"A": (0.0, 12.5), "B": (12.5, 22.0), "C": (22.0, 34.6)}

def ease(x):
    x = max(0.0, min(1.0, x)); return x*x*(3-2*x)
def lerp(a, b, k): return a + (b-a)*k

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; coll = sc.collection
rnd = random.Random(21)
exec(open(os.path.join(QDIR, "lib_air.py")).read())

P = make_airliner("JUMBO", (0.06, 0.13, 0.32))
GEARZ = 4.9                    # root height above ground when standing on its wheels

# ---------------- landing gear (group that can retract)
gear = bpy.data.objects.new("gear", None); coll.objects.link(gear); gear.parent = P
M_TYRE = principled("tyre", (0.02, 0.02, 0.02), 0.7)
M_STRUT = principled("strut", (0.55, 0.56, 0.58), 0.3, 0.8)
def leg(x, y, nwheels_x=2, nwheels_y=2, top=-2.4):
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.18, depth=2.0, location=(x, y, top-1.0))
    o = bpy.context.object; o.data.materials.append(M_STRUT); o.parent = gear
    for i in range(nwheels_x):
        for j in range(nwheels_y):
            bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.62, depth=0.45,
                location=(x + (i-(nwheels_x-1)/2)*1.4, y + (j-(nwheels_y-1)/2)*1.0, top-GEARZ+2.4+0.62), rotation=(math.pi/2, 0, 0))
            w = bpy.context.object; w.data.materials.append(M_TYRE); w.parent = gear
leg(27.0, 0, 1, 2, top=-2.0)
for y in (-2.0, 2.0): leg(-1.5, y)
for y in (-5.0, 5.0): leg(0.8, y)

# ---------------- fuel dump trails from both wing tips
def trail_mat():
    m = bpy.data.materials.new("fuelmist"); m.use_nodes = True; nt = m.node_tree
    for n_ in list(nt.nodes): nt.nodes.remove(n_)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    df = nt.nodes.new("ShaderNodeBsdfPrincipled"); df.inputs["Base Color"].default_value = (0.92, 0.93, 0.95, 1); df.inputs["Roughness"].default_value = 1.0
    tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mx = nt.nodes.new("ShaderNodeMixShader")
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); mp.name = "flow"
    mp.inputs["Scale"].default_value = (0.08, 1.0, 1.0)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 2.2; nz.inputs["Detail"].default_value = 14; nz.inputs["Roughness"].default_value = 0.7; nz.inputs["Distortion"].default_value = 1.2
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    gen = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Generated"], gen.inputs[0])
    # Generated Z: 0 at the nozzle end -> 1 at the far end (cone built along -X, see below)
    fade = nt.nodes.new("ShaderNodeMapRange"); fade.inputs[1].default_value = 0.0; fade.inputs[2].default_value = 1.0
    fade.inputs[3].default_value = 0.0; fade.inputs[4].default_value = 0.95
    nt.links.new(gen.outputs["Z"], fade.inputs[0])
    rp = nt.nodes.new("ShaderNodeMapRange"); rp.inputs[1].default_value = 0.3; rp.inputs[2].default_value = 0.7
    nt.links.new(nz.outputs["Fac"], rp.inputs[0])
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'
    nt.links.new(rp.outputs[0], mul.inputs[0]); nt.links.new(fade.outputs[0], mul.inputs[1])
    dens = nt.nodes.new("ShaderNodeMath"); dens.operation = 'MULTIPLY'; dens.name = "dens"; dens.inputs[1].default_value = 0.0
    nt.links.new(mul.outputs[0], dens.inputs[0])
    nt.links.new(dens.outputs[0], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(df.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs[0])
    return m
M_MIST = trail_mat()
trails = []
for s in (-1, 1):
    for layer, (r0, r1, L) in enumerate(((0.3, 5.0, 230), (0.5, 9.0, 280), (0.2, 3.0, 170))):
        # cone along local -Z, rotated so it points backwards (-X); Generated Z runs 0..1 from far end to tip, so flip
        bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=r1, radius2=r0, depth=1.0, location=(0, 0, 0), end_fill_type='NOTHING')
        c = bpy.context.object; c.name = f"trail{s}_{layer}"; c.data.materials.append(M_MIST)
        piv = bpy.data.objects.new(f"trailpiv{s}_{layer}", None); coll.objects.link(piv); piv.parent = P
        piv.location = (-17.6, s*30.6, 1.0); piv.rotation_euler = (s*math.radians(1.5*layer), -math.pi/2 + math.radians(2.5), 0)
        c.parent = piv; c.location = (0, 0, 0.5); c.rotation_euler = (math.pi, 0, 0)
        trails.append((piv, c, L))
def set_trails(k, t):
    on = k > 0.001
    for piv, c, L in trails:
        c.hide_render = not on
        length = max(1.0, L*k)
        piv.scale = (1.0, 1.0, length)
        c.location = (0, 0, 0.5)
    M_MIST.node_tree.nodes["dens"].inputs[1].default_value = 1.0*min(1.0, k*3)
    M_MIST.node_tree.nodes["flow"].inputs["Location"].default_value = (t*6.0, 0, 0)

# ---------------- sky / sun
wo = bpy.data.worlds.new("w"); sc.world = wo; wo.use_nodes = True
bg = wo.node_tree.nodes["Background"]
sky = wo.node_tree.nodes.new("ShaderNodeTexSky"); sky.sky_type = 'MULTIPLE_SCATTERING'
wo.node_tree.links.new(sky.outputs[0], bg.inputs[0])
sun_d = bpy.data.lights.new("sun", 'SUN'); sun_d.angle = math.radians(0.6)
sun = bpy.data.objects.new("sun", sun_d); coll.objects.link(sun)
def set_sun(el, rot, energy, color, alt, bgs):
    sky.sun_elevation = math.radians(el); sky.sun_rotation = math.radians(rot); sky.altitude = alt
    sky.aerosol_density = 1.5; sky.sun_intensity = 0.5; bg.inputs[1].default_value = bgs
    sun_d.energy = energy; sun_d.color = color; sun.rotation_euler = Euler((math.radians(90-el), 0, math.radians(rot+90)))

cam_d = bpy.data.cameras.new("cam"); cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 36; cam_d.clip_end = 200000
cam = bpy.data.objects.new("cam", cam_d); coll.objects.link(cam); sc.camera = cam
SH = [(rnd.uniform(-1, 1), rnd.uniform(-1, 1)) for _ in range(400)]
def shake(t, amp, rate=2.5):
    i = int(t*rate); f = t*rate - i; a, b_ = SH[i % 400], SH[(i+1) % 400]; f = f*f*(3-2*f)
    return (a[0]+(b_[0]-a[0])*f)*amp, (a[1]+(b_[1]-a[1])*f)*amp
def aim(loc, tgt, t, amp):
    cam.location = loc
    e = (Vector(tgt)-Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sx, sy = shake(t, amp); e.x += sx; e.z += sy; cam.rotation_euler = e

def strobes(t):
    st = t % 1.2; on_s = st < 0.05 or 0.12 < st < 0.17; on_b = (t % 1.0) < 0.12
    for o in P.children:
        if "strobe" in o.name: o.active_material.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 600 if on_s else 0
        if "beacon" in o.name: o.active_material.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 120 if on_b else 2

def cloud_deck(z):
    bpy.ops.mesh.primitive_plane_add(size=400000, location=(0, 0, z))
    deck = bpy.context.object
    cm = bpy.data.materials.new("clouds"); cm.use_nodes = True; nt = cm.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 1.0
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 0.0009; n1.inputs["Detail"].default_value = 14
    n1.inputs["Roughness"].default_value = 0.7; n1.inputs["Distortion"].default_value = 0.6
    nt.links.new(tc.outputs["Object"], n1.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB"); cr = ramp.color_ramp
    cr.elements[0].position = 0.40; cr.elements[0].color = (0.33, 0.36, 0.46, 1)
    cr.elements[1].position = 0.56; cr.elements[1].color = (1.5, 1.45, 1.4, 1)
    nt.links.new(n1.outputs["Fac"], ramp.inputs[0]); nt.links.new(ramp.outputs[0], b.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 1.0; bump.inputs["Distance"].default_value = 200
    nt.links.new(n1.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    deck.data.materials.append(cm); return deck

if SHOT == "A":
    # ---------------- runway takeoff at golden hour
    set_sun(7, 40, 3.4, (1.0, 0.72, 0.5), 0, 0.18)
    bpy.ops.mesh.primitive_plane_add(size=60000, location=(0, 0, 0)); ground = bpy.context.object
    gm = bpy.data.materials.new("grass"); gm.use_nodes = True; nt = gm.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.95
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.02; nz.inputs["Detail"].default_value = 12
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    rp = nt.nodes.new("ShaderNodeValToRGB"); rp.color_ramp.elements[0].color = (0.05, 0.08, 0.025, 1); rp.color_ramp.elements[1].color = (0.18, 0.2, 0.07, 1)
    nt.links.new(nz.outputs["Fac"], rp.inputs[0]); nt.links.new(rp.outputs[0], b.inputs["Base Color"])
    ground.data.materials.append(gm)
    # runway with markings (procedural)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(500, 0, 0.03)); rw = bpy.context.object; rw.scale = (3600, 60, 1)
    rm = bpy.data.materials.new("runway"); rm.use_nodes = True; nt = rm.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.75
    tc = nt.nodes.new("ShaderNodeTexCoord"); sp = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sp.inputs[0])
    # object coords: x in [-0.5,0.5]*3600, y in [-0.5,0.5]*60 -> convert to metres
    xm = nt.nodes.new("ShaderNodeMath"); xm.operation = 'MULTIPLY'; xm.inputs[1].default_value = 3600; nt.links.new(sp.outputs["X"], xm.inputs[0])
    ym = nt.nodes.new("ShaderNodeMath"); ym.operation = 'MULTIPLY'; ym.inputs[1].default_value = 60; nt.links.new(sp.outputs["Y"], ym.inputs[0])
    ay = nt.nodes.new("ShaderNodeMath"); ay.operation = 'ABSOLUTE'; nt.links.new(ym.outputs[0], ay.inputs[0])
    centre = nt.nodes.new("ShaderNodeMath"); centre.operation = 'LESS_THAN'; centre.inputs[1].default_value = 0.45; nt.links.new(ay.outputs[0], centre.inputs[0])
    dash = nt.nodes.new("ShaderNodeMath"); dash.operation = 'PINGPONG'; dash.inputs[1].default_value = 30; nt.links.new(xm.outputs[0], dash.inputs[0])
    dashon = nt.nodes.new("ShaderNodeMath"); dashon.operation = 'GREATER_THAN'; dashon.inputs[1].default_value = 12; nt.links.new(dash.outputs[0], dashon.inputs[0])
    cl = nt.nodes.new("ShaderNodeMath"); cl.operation = 'MULTIPLY'; nt.links.new(centre.outputs[0], cl.inputs[0]); nt.links.new(dashon.outputs[0], cl.inputs[1])
    edge = nt.nodes.new("ShaderNodeMath"); edge.operation = 'COMPARE'; edge.inputs[1].default_value = 28.6; edge.inputs[2].default_value = 0.45
    nt.links.new(ay.outputs[0], edge.inputs[0])
    paint = nt.nodes.new("ShaderNodeMath"); paint.operation = 'MAXIMUM'; nt.links.new(cl.outputs[0], paint.inputs[0]); nt.links.new(edge.outputs[0], paint.inputs[1])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.3; nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    mixc = nt.nodes.new("ShaderNodeMix"); mixc.data_type = 'RGBA'
    mixc.inputs[6].default_value = (0.06, 0.06, 0.065, 1); mixc.inputs[7].default_value = (0.8, 0.8, 0.78, 1)
    nt.links.new(paint.outputs[0], mixc.inputs["Factor"])
    gr = nt.nodes.new("ShaderNodeMix"); gr.data_type = 'RGBA'; gr.blend_type = 'MULTIPLY'; gr.inputs["Factor"].default_value = 0.35
    nt.links.new(mixc.outputs[2], gr.inputs[6]); nt.links.new(nz.outputs["Color"], gr.inputs[7])
    nt.links.new(gr.outputs[2], b.inputs["Base Color"]); rw.data.materials.append(rm)
    # runway edge lights + distant airport buildings and tree line
    lm = principled("rwylight", (1, 0.95, 0.8), emit=(1, 0.9, 0.7), estr=30)
    for i in range(70):
        for s in (-1, 1):
            bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=4, radius=0.25, location=(-1100 + i*60, s*31.5, 0.35))
            bpy.context.object.data.materials.append(lm)
    bm_ = principled("bld", (0.35, 0.36, 0.38), 0.7); tm = principled("trees", (0.03, 0.05, 0.03), 0.9)
    for i in range(18):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(rnd.uniform(-1500, 1500), rnd.uniform(700, 1200), 0))
        o = bpy.context.object; o.scale = (rnd.uniform(40, 160), rnd.uniform(30, 80), rnd.uniform(10, 40)); o.data.materials.append(bm_)
    for i in range(160):
        a = rnd.uniform(0, 2*math.pi); r = rnd.uniform(2500, 4000)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=(r*math.cos(a), r*math.sin(a), 0))
        o = bpy.context.object; o.scale = (rnd.uniform(40, 120), rnd.uniform(40, 120), rnd.uniform(15, 35)); o.data.materials.append(tm)
    X0, ACC, TROT, TLIFT = -330.0, 8.6, 7.4, 8.3
    def xpos(t): return X0 + 0.5*ACC*max(0, t-0.5)**2
    def pose(t):
        x = xpos(t)
        pitch = math.radians(10)*ease((t-TROT)/1.2)
        climb = 0.0 if t < TLIFT else 0.5*7.0*(t-TLIFT)**2 + 6.0*(t-TLIFT)
        P.location = (x, 0, GEARZ + climb + max(0, math.sin(pitch))*-1.5)
        P.rotation_euler = (0, -pitch, 0)
        k = ease((t-10.0)/2.0)
        gear.scale = (1, 1, 1 - 0.92*k); gear.location = (0, 0, 2.2*k)
        set_trails(0, t); strobes(t)
        cam_d.lens = lerp(95, 70, ease((t-6)/5))
        loc = (40, -170, 6.0)
        aim(loc, (x + 10, 0, P.location.z + 16), t, math.radians(0.12))
elif SHOT == "B":
    # ---------------- climb above the clouds, warning, banked turn back
    set_sun(8, 40, 3.6, (1.0, 0.74, 0.52), 6000, 0.32)
    deck = cloud_deck(-1800)
    def pose(t):
        tt = t - 12.5
        bank = math.radians(26)*ease((t-19.6)/1.6)
        P.location = (tt*80.0, 0, tt*9.0); P.rotation_euler = (bank, -math.radians(7)*(1-0.5*ease((t-19.6)/1.6)), math.radians(8)*ease((t-20.2)/2.0))
        set_trails(0, t); strobes(t)
        gear.scale = (1, 1, 0.08); gear.location = (0, 0, 2.2)
        cam_d.lens = 40
        off = Vector((lerp(70, 40, ease(tt/9.5)), -lerp(95, 110, ease(tt/9.5)), lerp(-14, -6, ease(tt/9.5))))
        aim(P.location + off, P.location + Vector((6, 0, 1)), t, math.radians(0.18))
else:
    # ---------------- fuel dump
    set_sun(9, 40, 3.6, (1.0, 0.76, 0.55), 4000, 0.32)
    deck = cloud_deck(-1400)
    def pose(t):
        tt = t - 22.0
        P.location = (tt*80.0, 0, 0); P.rotation_euler = (math.radians(2)*math.sin(t*0.5), -math.radians(2), 0)
        k = ease((t-24.0)/7.0)
        set_trails(k, t); strobes(t)
        gear.scale = (1, 1, 0.08); gear.location = (0, 0, 2.2)
        cam_d.lens = 38
        # camera behind and above the left wing tip, slowly sweeping round
        a = lerp(-0.25, 0.25, ease(tt/12.6))
        off = Vector((-150 - 20*ease(tt/12.6), -120 + 25*ease(tt/12.6), -22 + 6*ease(tt/12.6)))
        aim(P.location + off, P.location + Vector((-28, 0, -2)), t, math.radians(0.15))

# ---------------- render settings
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.cycles.samples = int(os.environ.get("SPP", "12")); sc.cycles.use_denoising = True; sc.cycles.use_adaptive_sampling = True
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transparent_max_bounces = 24
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.resolution_percentage = int(os.environ.get("PCT", "60"))
sc.render.use_persistent_data = True
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
sc.view_settings.exposure = float(os.environ.get("EXPO", "0.0"))

def screen(p):
    v = world_to_camera_view(sc, cam, Vector(p)); return (v.x*RES[0], (1-v.y)*RES[1], v.z)

t0, t1 = SHOTS[SHOT]
mode = sys.argv[sys.argv.index("--")+1] if "--" in sys.argv else "frames"
if mode == "test":
    for t in [float(x) for x in os.environ.get("TT", str((t0+t1)/2)).split(",")]:
        pose(t); bpy.context.view_layer.update()
        sc.render.filepath = f"{OUT}/test{SHOT}_{t}.png"; bpy.ops.render.render(write_still=True)
elif mode == "meta":
    meta = {}
    for i in range(int(round(t0*FPS)), int(round(t1*FPS))):
        t = i/FPS; pose(t); bpy.context.view_layer.update()
        mw = P.matrix_world
        meta[i] = {"plane": screen(P.location), "tipL": screen(mw @ Vector((-17.6, -30.6, 1.0))), "tipR": screen(mw @ Vector((-17.6, 30.6, 1.0))),
                   "alt": P.location.z, "x": P.location.x}
    json.dump(meta, open(f"{OUT}/meta{SHOT}.json", "w"))
else:
    os.makedirs(f"{OUT}/frames", exist_ok=True)
    step = int(os.environ.get("STEP", "2"))
    for i in range(int(os.environ.get("IFROM", int(round(t0*FPS)))), int(os.environ.get("ITO", int(round(t1*FPS)))), step):
        out = f"{OUT}/frames/f{i:04d}.png"
        if os.path.exists(out): continue
        pose(i/FPS); bpy.context.view_layer.update()
        sc.render.filepath = out; bpy.ops.render.render(write_still=True)
