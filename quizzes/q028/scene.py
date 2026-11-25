import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
# Quiz #28 - runway numbers. A 747 lands on runway 27; the far end of the same runway says 09.
import bpy, bmesh, math, json, sys, os, random
from mathutils import Vector, Euler
from bpy_extras.object_utils import world_to_camera_view

FPS = 30
RES = (1080, 1920)
OUT = os.environ.get("OUT", QDIR)
SHOT = "A"
SHOTS = {"A": (0.0, 5.0), "B": (5.0, 13.6), "C": (13.6, 23.4), "D": (23.4, 31.6)}
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
rnd = random.Random(28)
bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
exec(open(os.path.join(QDIR, "lib_air.py")).read())

JET = make_airliner("JET", (0.55, 0.08, 0.10), engines=True)
M_RUB = principled("rubber", (0.02, 0.02, 0.02), 0.85)
M_STRUT = principled("strut", (0.55, 0.56, 0.58), 0.25, 0.9)
GEAR_DROP = 4.35   # fuselage axis to wheel bottom
def cyl(name, loc, r, depth, axis, mat, parent=None, verts=24):
    rot = {"x": (0, math.pi/2, 0), "y": (math.pi/2, 0, 0), "z": (0, 0, 0)}[axis]
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name; o.data.materials.append(mat)
    for p in o.data.polygons: p.use_smooth = True
    if parent: o.parent = parent
    return o
def gear(x, y, n_wheels, zt=-1.6):
    zc = -GEAR_DROP + 0.56
    cyl(f"g{x}{y}", (x, y, (zt + zc)/2), 0.13, zt - zc, "z", M_STRUT, JET, 16)
    for k in range(n_wheels):
        dx = (k // 2)*1.4 - (0.7 if n_wheels == 4 else 0); dy = (0.5 if k % 2 else -0.5)
        cyl(f"t{x}{y}{k}", (x + dx, y + dy, zc), 0.56, 0.4, "y", M_RUB, JET, 32)
for s in (1, -1): gear(-3.0, s*2.0, 4); gear(-1.0, s*5.5, 4)
gear(24.5, 0, 2, zt=-2.0)
# landing lights (wing roots) as small emissive spheres + spot lights
M_LL = principled("ll", (1, 1, 1), emit=(1.0, 0.93, 0.8), estr=60)
LL = []
for s in (1, -1):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.28, location=(5.0, s*4.5, -1.6)); o = bpy.context.object; o.data.materials.append(M_LL); o.parent = JET
    ld = bpy.data.lights.new(f"ll{s}", 'SPOT'); ld.energy = 2.5e5; ld.spot_size = math.radians(14); ld.color = (1.0, 0.92, 0.8); ld.shadow_soft_size = 0.2
    lo = bpy.data.objects.new(f"ll{s}", ld); coll.objects.link(lo); lo.parent = JET; lo.location = (5.4, s*4.5, -1.6)
    lo.rotation_euler = (0, math.radians(-86), 0)   # point forward (+X local) and slightly down
    LL.append(lo)

# ------------------------------------------------------------------ runway
RL = 3000.0; HW = 22.5; X27 = RL/2; X09 = -RL/2
DECAL_L = 260.0; PPM = 10
from PIL import Image as _I, ImageDraw as _D, ImageFont as _F, ImageFilter as _IF
FD = "/usr/share/fonts/opentype/inter/"
def decal(txt, path):
    """image: columns = metres from the threshold along the landing direction, rows = pilot's left -> right"""
    W_, H_ = int(DECAL_L*PPM), int(2*HW*PPM)
    im = _I.new("L", (W_, H_), 0); d = _D.Draw(im)
    def R(d0, d1, l0, l1): d.rectangle([d0*PPM, (l0 + HW)*PPM, d1*PPM, (l1 + HW)*PPM], fill=255)
    # edge lines
    R(0, DECAL_L, -HW + 0.3, -HW + 1.2); R(0, DECAL_L, HW - 1.2, HW - 0.3)
    # threshold piano keys (4 + 4) 1.8 m wide, 30 m long, starting 6 m in
    for side in (-1, 1):
        for k in range(4):
            l0 = side*(3.0 + k*3.6) if side > 0 else -(3.0 + k*3.6) - 1.8
            R(6, 36, l0, l0 + 1.8)
    # designation number: 18 m tall digits, 12 m after the keys
    fnt = _F.truetype(FD + "InterDisplay-Black.otf", 300)
    tw = d.textlength(txt, font=fnt)
    tim = _I.new("L", (int(tw) + 40, 360), 0); _D.Draw(tim).text((20, 0), txt, font=fnt, fill=255)
    bb = tim.getbbox(); tim = tim.crop(bb)
    gap = 40
    # widen spacing: draw digits separately
    digs = []
    for ch in txt:
        g = _I.new("L", (300, 360), 0); _D.Draw(g).text((10, 0), ch, font=fnt, fill=255); digs.append(g.crop(g.getbbox()))
    th = 27.0*PPM; widths = [int(g.width*th/g.height*0.55) for g in digs]
    sp = int(3.0*PPM); total = sum(widths) + sp*(len(digs) - 1)
    canvas = _I.new("L", (total, int(th)), 0); x = 0
    for g, w in zip(digs, widths):
        canvas.paste(g.resize((w, int(th)), _I.LANCZOS), (x, 0)); x += w + sp
    rot = canvas.rotate(-90, expand=True)     # text 'up' -> +columns (along landing direction), reading -> +rows
    c0 = int(48*PPM); r0 = int(H_/2 - rot.height/2)
    im.paste(rot, (c0, r0), rot)
    # centreline dashes 36 m / 24 m gap starting at 80 m
    dd = 80.0
    while dd < DECAL_L:
        R(dd, min(DECAL_L, dd + 36), -0.45, 0.45); dd += 60
    # touchdown zone bars (3 pairs) at 150 m
    for side in (-1, 1):
        for k in range(3):
            l0 = side*(6.0 + k*1.8) - (0.9 if side < 0 else 0) - (1.8*0 if side > 0 else 0)
            R(150, 172, side*5 + (0 if side > 0 else -0.9) + side*k*1.8, side*5 + (0.9 if side > 0 else 0) + side*k*1.8)
    im = im.filter(_IF.GaussianBlur(0.8))
    im.save(path); return path
P27 = decal("27", f"{OUT}/decal27.png"); P09 = decal("09", f"{OUT}/decal09.png")

def asphalt_mat(name, img_path):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.8
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.08; nz.inputs["Detail"].default_value = 12
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    cr = nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (0.035, 0.035, 0.036, 1); cr.color_ramp.elements[1].color = (0.09, 0.088, 0.085, 1)
    nt.links.new(nz.outputs["Fac"], cr.inputs[0])
    # tyre rubber deposits darken the touchdown zone around the centre
    if img_path:
        tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = bpy.data.images.load(img_path); tx.image.colorspace_settings.name = 'Non-Color'
        tx.extension = 'CLIP'
        nt.links.new(tc.outputs["UV"], tx.inputs["Vector"])
        wear = nt.nodes.new("ShaderNodeTexNoise"); wear.inputs["Scale"].default_value = 2.5; wear.inputs["Detail"].default_value = 8
        nt.links.new(tc.outputs["Object"], wear.inputs["Vector"])
        wr = nt.nodes.new("ShaderNodeMapRange"); wr.inputs[1].default_value = 0.3; wr.inputs[2].default_value = 0.6; wr.inputs[3].default_value = 0.65; wr.inputs[4].default_value = 1.0
        nt.links.new(wear.outputs["Fac"], wr.inputs[0])
        mm = nt.nodes.new("ShaderNodeMath"); mm.operation = 'MULTIPLY'
        nt.links.new(tx.outputs["Color"], mm.inputs[0]); nt.links.new(wr.outputs[0], mm.inputs[1])
        mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.inputs[7].default_value = (0.78, 0.78, 0.76, 1)
        nt.links.new(mm.outputs[0], mix.inputs[0]); nt.links.new(cr.outputs[0], mix.inputs[6])
        nt.links.new(mix.outputs[2], b.inputs["Base Color"])
        rg = nt.nodes.new("ShaderNodeMapRange"); rg.inputs[3].default_value = 0.8; rg.inputs[4].default_value = 0.55
        nt.links.new(mm.outputs[0], rg.inputs[0]); nt.links.new(rg.outputs[0], b.inputs["Roughness"])
    else:
        nt.links.new(cr.outputs[0], b.inputs["Base Color"])
    return m

def quad(name, pts, uvs, mat):
    bm = bmesh.new(); vs = [bm.verts.new(p) for p in pts]; f = bm.faces.new(vs)
    ul = bm.loops.layers.uv.new("UVMap")
    for lp, uv in zip(f.loops, uvs): lp[ul].uv = uv
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); coll.objects.link(o); o.data.materials.append(mat); return o
M_ASP = asphalt_mat("asphalt", None)
# middle section with plain asphalt; centreline dashes as thin boxes
quad("rwmid", [(X09 + DECAL_L, -HW, 0), (X27 - DECAL_L, -HW, 0), (X27 - DECAL_L, HW, 0), (X09 + DECAL_L, HW, 0)], [(0, 0)]*4, M_ASP)
M_PAINT = principled("paint", (0.72, 0.72, 0.70), 0.6)
x = X09 + DECAL_L + 20
while x < X27 - DECAL_L - 36:
    quad(f"cl{int(x)}", [(x, -0.45, 0.01), (x + 36, -0.45, 0.01), (x + 36, 0.45, 0.01), (x, 0.45, 0.01)], [(0, 0)]*4, M_PAINT); x += 60
for s in (-1, 1):
    quad(f"edge{s}", [(X09 + DECAL_L, s*(HW - 1.2), 0.01), (X27 - DECAL_L, s*(HW - 1.2), 0.01), (X27 - DECAL_L, s*(HW - 0.3), 0.01), (X09 + DECAL_L, s*(HW - 0.3), 0.01)], [(0, 0)]*4, M_PAINT)
# 27 end (pilot heading -X): u = (X27 - x)/L, image row = (y + HW)/(2HW) -> v = 1 - row
M27 = asphalt_mat("rw27", P27)
quad("rw27", [(X27, -HW, 0), (X27 - DECAL_L, -HW, 0), (X27 - DECAL_L, HW, 0), (X27, HW, 0)], [(0, 1), (1, 1), (1, 0), (0, 0)], M27)
# 09 end (pilot heading +X): u = (x - X09)/L, row = (HW - y)/(2HW) -> v = (y + HW)/(2HW)
M09 = asphalt_mat("rw09", P09)
quad("rw09", [(X09, -HW, 0), (X09 + DECAL_L, -HW, 0), (X09 + DECAL_L, HW, 0), (X09, HW, 0)], [(0, 0), (1, 0), (1, 1), (0, 1)], M09)
# paved blast pads / overrun with yellow chevrons kept simple: darker asphalt
for xe, sgn in ((X27, 1), (X09, -1)):
    quad(f"pad{sgn}", [(xe, -HW, -0.01), (xe + sgn*60, -HW, -0.01), (xe + sgn*60, HW, -0.01), (xe, HW, -0.01)], [(0, 0)]*4, M_ASP)

# grass
def grass_mat():
    m = bpy.data.materials.new("grass"); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.95
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.02; nz.inputs["Detail"].default_value = 14
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    cr = nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (0.05, 0.07, 0.025, 1); cr.color_ramp.elements[1].color = (0.16, 0.15, 0.06, 1)
    nt.links.new(nz.outputs["Fac"], cr.inputs[0]); nt.links.new(cr.outputs[0], b.inputs["Base Color"])
    nz2 = nt.nodes.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = 3.0; nz2.inputs["Detail"].default_value = 10
    nt.links.new(tc.outputs["Object"], nz2.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.5
    nt.links.new(nz2.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m
bpy.ops.mesh.primitive_plane_add(size=40000, location=(0, 0, -0.04)); bpy.context.object.data.materials.append(grass_mat())

# runway edge lights + approach lights (bars on poles beyond each threshold)
M_EDGE = principled("edgel", (1, 1, 1), emit=(1.0, 0.85, 0.6), estr=25)
M_POLE = principled("pole", (0.25, 0.25, 0.26), 0.5, 0.5)
for xx in range(int(X09), int(X27) + 1, 60):
    for s in (-1, 1):
        cyl(f"el{xx}{s}", (xx, s*(HW + 1.5), 0.25), 0.12, 0.5, "z", M_EDGE, None, 8)
M_THR = principled("thrl", (0.1, 1, 0.2), emit=(0.2, 1.0, 0.3), estr=25)
for xe in (X27, X09):
    for k in range(-9, 10):
        cyl(f"th{xe}{k}", (xe + (1 if xe > 0 else -1)*0.8, k*2.4, 0.15), 0.15, 0.3, "z", M_THR, None, 8)
M_APP = principled("appl", (1, 1, 1), emit=(1.0, 0.92, 0.75), estr=20)
for xe, sgn in ((X27, 1), (X09, -1)):
    for k in range(1, 26):
        x = xe + sgn*k*30; h = 0.5 + k*30*0.03
        cyl(f"ap{xe}{k}", (x, 0, h/2), 0.12, h, "z", M_POLE, None, 8)
        for j in range(-2, 3):
            cyl(f"apl{xe}{k}{j}", (x, j*1.0, h + 0.1), 0.09, 0.2, "z", M_APP, None, 8)

# distant tree line + hangars for depth
M_TREE = principled("trees", (0.03, 0.045, 0.02), 0.9)
for k in range(60):
    ang = rnd.uniform(0, 2*math.pi); d = rnd.uniform(1900, 2600)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=1, location=(d*math.cos(ang)*1.3, d*math.sin(ang), 4))
    o = bpy.context.object; o.scale = (rnd.uniform(60, 140), rnd.uniform(40, 90), rnd.uniform(18, 30)); o.data.materials.append(M_TREE)
M_HANG = principled("hangar", (0.22, 0.23, 0.25), 0.5, 0.4)
for k in range(5):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-600 + k*140, 420, 12)); o = bpy.context.object; o.scale = (110, 70, 24); o.data.materials.append(M_HANG)
bpy.ops.mesh.primitive_cube_add(size=1, location=(200, 520, 18)); o = bpy.context.object; o.scale = (500, 60, 36); o.data.materials.append(principled("term", (0.2, 0.21, 0.23), 0.4, 0.3))
bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=6, depth=50, location=(450, 470, 25)); bpy.context.object.data.materials.append(M_HANG)
bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=11, depth=8, location=(450, 470, 54)); bpy.context.object.data.materials.append(principled("cab", (0.02, 0.03, 0.04), 0.05, coat=1.0))

# ------------------------------------------------------------------ sky + sun
wo = bpy.data.worlds.new("w"); sc.world = wo; wo.use_nodes = True
bg = wo.node_tree.nodes["Background"]
sky = wo.node_tree.nodes.new("ShaderNodeTexSky"); sky.sky_type = 'MULTIPLE_SCATTERING'
wo.node_tree.links.new(sky.outputs[0], bg.inputs[0])
SUNROT = float(os.environ.get("SUNROT", "-60")); SUNEL = float(os.environ.get("SUNEL", "6"))
sky.sun_elevation = math.radians(SUNEL); sky.sun_rotation = math.radians(SUNROT); sky.altitude = 0; sky.aerosol_density = 1.8; sky.sun_intensity = 0.5
bg.inputs[1].default_value = 0.22
sun_d = bpy.data.lights.new("sun", 'SUN'); sun_d.energy = 3.6; sun_d.color = (1.0, 0.64, 0.40); sun_d.angle = math.radians(0.6)
sun = bpy.data.objects.new("sun", sun_d); coll.objects.link(sun)
sun.rotation_euler = Euler((math.radians(90 - SUNEL), 0, math.radians(SUNROT + 90)))
# haze for aerial depth
vol = bpy.data.materials.new("haze")  # (kept simple: grade.py adds horizon haze)

# ------------------------------------------------------------------ aircraft motion
GS = math.tan(math.radians(3.0)); XTD = X27 - 330.0; V0 = 75.0; T_TD = (2400 - XTD)/V0
def jet_state(t):
    if t < T_TD:
        x = 2400 - V0*t; h = (x - XTD)*GS
        # flare in the last ~40 m of height loss: soften the touchdown
        h = max(0.0, h); fl = clamp((t - (T_TD - 4.0))/4.0)
        pitch = lerp(2.5, 6.0, ease(fl))
    else:
        dt = t - T_TD; a = 2.2
        dx = V0*dt - 0.5*a*dt*dt if dt < V0/a else V0*V0/(2*a)
        x = XTD - dx; h = 0.0; pitch = lerp(6.0, 0.0, ease(dt/4.0))
    return x, h, pitch
def place_jet(t):
    x, h, pitch = jet_state(t)
    JET.location = (x, 0, GEAR_DROP + h + 0.05)
    JET.rotation_euler = (0, math.radians(-pitch), math.pi)   # nose towards -X, pitch up

# ------------------------------------------------------------------ camera
cam_d = bpy.data.cameras.new("cam"); cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 36; cam_d.clip_end = 60000; cam_d.clip_start = 0.1
cam = bpy.data.objects.new("cam", cam_d); coll.objects.link(cam); sc.camera = cam
SH = [(rnd.uniform(-1, 1), rnd.uniform(-1, 1)) for _ in range(400)]
def shake(t, amp, rate=1.8):
    i = int(t*rate); f = t*rate - i; a, b_ = SH[i % 400], SH[(i+1) % 400]; f = f*f*(3-2*f)
    return (a[0]+(b_[0]-a[0])*f)*amp, (a[1]+(b_[1]-a[1])*f)*amp
def aim(loc, tgt, t, amp, fstop=None, fdist=None, rate=1.8):
    cam.location = loc
    e = (Vector(tgt)-Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sx, sy = shake(t, amp, rate); e.x += sx; e.z += sy; cam.rotation_euler = e
    if fstop:
        cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = fstop
        cam_d.dof.focus_distance = fdist or (Vector(tgt) - Vector(loc)).length
    else: cam_d.dof.use_dof = False

def pose(t):
    place_jet(t)
    jx, jh, _ = jet_state(t)
    jp = Vector((jx, 0, GEAR_DROP + jh))
    if SHOT == "A":
        k = ease(t/5.0); cam_d.lens = lerp(135, 150, k)
        loc = Vector((1640, -420, 7))
        aim(loc, jp + Vector((-6, 0, -1)), t, math.radians(0.03))
    elif SHOT == "B":
        k = ease((t - 5.0)/8.6); cam_d.lens = 22
        loc = Vector((lerp(1532, 1518, k), lerp(16, 14, k), lerp(12.5, 11.0, k)))
        tgt = Vector((1430, 0, 0))
        near = clamp(1 - abs(jx - loc.x)/120)
        aim(loc, tgt, t, math.radians(0.05 + 0.25*near), rate=1.8 + 5*near)
    elif SHOT == "C":
        k = ease((t - 13.6)/9.8); cam_d.lens = lerp(24, 26, k)
        loc = Vector((lerp(-1585, -1545, k), lerp(-14, -8, k), lerp(30, 22, k)))
        tgt = Vector((lerp(-1440, -1450, k), 0, 0))
        aim(loc, tgt, t, math.radians(0.05))
    else:
        k = ease((t - 23.4)/8.2); cam_d.lens = lerp(42, 48, k)
        loc = Vector((jx + lerp(230, 170, k), -190, lerp(80, 65, k)))
        aim(loc, jp + Vector((-20, 0, -10)), t, math.radians(0.04))

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
    SHOT = shot_for(t)
    if frame is not None:
        # keyframe jet for motion blur
        place_jet(t); JET.keyframe_insert("location", frame=frame); JET.keyframe_insert("rotation_euler", frame=frame)
        place_jet(t + 1/FPS); JET.keyframe_insert("location", frame=frame + 1); JET.keyframe_insert("rotation_euler", frame=frame + 1)
        sc.frame_set(frame)
    pose(t); bpy.context.view_layer.update()
mode = sys.argv[sys.argv.index("--")+1] if "--" in sys.argv else "frames"
if mode == "test":
    for t in [float(x) for x in os.environ.get("TT", "3").split(",")]:
        setup(t, int(round(t*FPS))); sc.render.filepath = f"{OUT}/test_{t}.png"; bpy.ops.render.render(write_still=True)
elif mode == "meta":
    meta = {}
    for i in range(0, int(END*FPS)):
        t = i/FPS; setup(t)
        jx, jh, _ = jet_state(t)
        meta[i] = {"jet": screen((jx, 0, GEAR_DROP + jh + 2)), "n27": screen((X27 - 57, 0, 0)), "n09": screen((X09 + 57, 0, 0)),
                   "keys27": screen((X27 - 21, 8, 0)), "rw": screen((0, 0, 0))}
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
