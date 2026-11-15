import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import bpy, bmesh, math, json, sys, os, random
from mathutils import Vector, Euler
from bpy_extras.object_utils import world_to_camera_view

FPS = 30
RES = (1080, 1920)
OUT = os.environ.get("OUT", QDIR)
SHOT = os.environ.get("SHOT", "A")
SHOTS = {"A": (0.0, 7.4), "B": (7.4, 12.0), "C": (12.0, 28.2)}
SPEED = 9.0        # m/s, the water moves past the (static) ship

def ease(x):
    x = max(0.0, min(1.0, x)); return x*x*(3-2*x)
def lerp(a, b, k): return a + (b-a)*k

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; coll = sc.collection
rnd = random.Random(11)

def principled(name, color, rough=0.5, metal=0.0, coat=0.0, emit=None, estr=0.0, alpha=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal; b.inputs["Coat Weight"].default_value = coat
    b.inputs["Alpha"].default_value = alpha
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = estr
    return m

# ------------------------------------------------------------------ hull
L2 = 130.0; BH = 20.0; KEEL = -13.0; DECK = 14.0
def width(x):
    if x > 55: return max(0.04, 1 - ((x-55)/(L2-55))**1.7)
    if x < -105: return 1 - 0.25*((-105-x)/25)**2
    return 1.0
def vpow(x):
    if x > 55: return lerp(0.12, 0.9, ((x-55)/(L2-55)))
    if x < -100: return lerp(0.12, 0.5, (-100-x)/30)
    return 0.12
def stem_x(z):
    return L2 + 0.28*(z - KEEL) - 3

stations = [-L2 + i*4 for i in range(int((2*L2)/4)+1)]
nz = 22
bm = bmesh.new(); rings = []
for x in stations:
    ring = []
    for j in range(nz+1):
        z = KEEL + (DECK-KEEL)*j/nz
        zz = (z-KEEL)/(DECK-KEEL)
        xx = min(x, stem_x(z)) if x > 100 else x
        wy = BH*width(xx)*(zz**vpow(xx) if zz > 0 else 0.0)
        wy = max(wy, 0.3)
        # flare: wider near the deck at the bow
        if xx > 80: wy *= 1 + 0.12*zz*((xx-80)/50)
        ring.append((xx, wy, z))
    rings.append(ring)
verts = []
for side in (1, -1):
    for ring in rings:
        verts.append([bm.verts.new((x, side*y, z)) for (x, y, z) in ring])
nst = len(rings)
for s in range(2):
    base = s*nst
    for i in range(nst-1):
        for j in range(nz):
            a, b, c, d = verts[base+i][j], verts[base+i+1][j], verts[base+i+1][j+1], verts[base+i][j+1]
            bm.faces.new([a, b, c, d] if s == 0 else [d, c, b, a])
# bottom (join keel lines) and stem/transom closures
for i in range(nst-1):
    bm.faces.new([verts[i][0], verts[nst+i][0], verts[nst+i+1][0], verts[i+1][0]])
for i in (0, nst-1):
    ring_s, ring_p = verts[i], verts[nst+i]
    for j in range(nz):
        f = [ring_s[j], ring_s[j+1], ring_p[j+1], ring_p[j]]
        bm.faces.new(f if i == nst-1 else list(reversed(f)))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
me = bpy.data.meshes.new("hull"); bm.to_mesh(me); bm.free()
hull = bpy.data.objects.new("hull", me); coll.objects.link(hull)
for p in hull.data.polygons: p.use_smooth = True

hm = bpy.data.materials.new("hullpaint"); hm.use_nodes = True; nt = hm.node_tree
b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.55
tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep.inputs[0])
mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[1].default_value = -13; mr.inputs[2].default_value = 14
nt.links.new(sep.outputs["Z"], mr.inputs[0])
ramp = nt.nodes.new("ShaderNodeValToRGB"); cr = ramp.color_ramp; cr.interpolation = 'CONSTANT'
cr.elements[0].position = 0.0; cr.elements[0].color = (0.32, 0.03, 0.025, 1)          # red antifouling
cr.elements[1].position = 0.475; cr.elements[1].color = (0.015, 0.015, 0.018, 1)      # black boot-top
e = cr.elements.new(0.53); e.color = (0.008, 0.02, 0.05, 1)                            # navy topsides
nt.links.new(mr.outputs[0], ramp.inputs[0])
nz_ = nt.nodes.new("ShaderNodeTexNoise"); nz_.inputs["Scale"].default_value = 0.08; nz_.inputs["Detail"].default_value = 8
mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1, 1, 6)
nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], nz_.inputs["Vector"])
mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs["Factor"].default_value = 0.45
nt.links.new(ramp.outputs[0], mix.inputs[6]); nt.links.new(nz_.outputs["Color"], mix.inputs[7])
nt.links.new(mix.outputs[2], b.inputs["Base Color"])
hull.data.materials.append(hm)

# bulbous bow
bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1, location=(L2 - 4, 0, -7.2))
bulb = bpy.context.object; bulb.scale = (17, 4.6, 5.0); bulb.data.materials.append(hm)
for p in bulb.data.polygons: p.use_smooth = True
BULB_TIP = Vector((L2 + 13, 0, -7.2))

# deck, containers, superstructure, funnel, details
def box(name, size, loc, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object; o.name = name; o.scale = size; o.data.materials.append(mat); return o
M_DECK = principled("deck", (0.25, 0.25, 0.26), 0.8)
box("deck", (188, 2*BH-1, 0.6), (-34, 0, DECK), M_DECK)
pal = [(0.03, 0.18, 0.42), (0.55, 0.06, 0.04), (0.08, 0.30, 0.15), (0.75, 0.74, 0.70), (0.40, 0.40, 0.42),
       (0.75, 0.32, 0.05), (0.05, 0.36, 0.48), (0.50, 0.40, 0.08), (0.12, 0.12, 0.14)]
cmat = [principled(f"cont{i}", c, 0.6, 0.15) for i, c in enumerate(pal)]
cbm = {i: bmesh.new() for i in range(len(pal))}
for bx in range(16):
    x0 = -112 + bx*13.0
    if 28 < x0 < 46: continue                      # deckhouse gap
    taper = width(x0+6)
    rows = int(16*taper)
    for r in range(rows):
        y = (r - (rows-1)/2)*2.5
        h = rnd.choice([5, 6, 6, 7, 7, 8]) if x0 < 80 else rnd.choice([3, 4, 5])
        for tier in range(h):
            ci = rnd.randrange(len(pal))
            res = bmesh.ops.create_cube(cbm[ci], size=1.0)
            for v in res["verts"]:
                v.co.x = v.co.x*12.0 + x0 + 6; v.co.y = v.co.y*2.38 + y; v.co.z = v.co.z*2.5 + DECK + 1.5 + tier*2.6
for ci, b_ in cbm.items():
    m_ = bpy.data.meshes.new(f"cont{ci}"); b_.to_mesh(m_); b_.free()
    o = bpy.data.objects.new(f"cont{ci}", m_); coll.objects.link(o); o.data.materials.append(cmat[ci])
M_WHITE = principled("white", (0.82, 0.82, 0.80), 0.45)
M_WIN = principled("win", (0.02, 0.03, 0.04), 0.05, coat=1.0)
box("house", (14, 34, 36), (37, 0, DECK + 18), M_WHITE)
box("bridge", (9, 46, 4), (40, 0, DECK + 37), M_WHITE)
box("bridgewin", (9.2, 46.2, 1.4), (40, 0, DECK + 37.6), M_WIN)
for k in range(9):
    box(f"housewin{k}", (14.2, 30, 0.6), (37, 0, DECK + 4 + k*3.6), M_WIN)
box("funnel", (10, 8, 20), (-118, 0, DECK + 10), principled("funnel", (0.05, 0.05, 0.06), 0.5))
box("aftdeck", (18, 34, 12), (-115, 0, DECK + 6), M_WHITE)
bmd = bmesh.new()
outline = [(x, BH*width(x)) for x in [60 + k*2.5 for k in range(28)]]
vs_ = [bmd.verts.new((x, y, DECK+0.2)) for (x, y) in outline] + [bmd.verts.new((x, -y, DECK+0.2)) for (x, y) in reversed(outline)]
bmd.faces.new(vs_)
med = bpy.data.meshes.new("bowdeck"); bmd.to_mesh(med); bmd.free()
bowdeck = bpy.data.objects.new("bowdeck", med); coll.objects.link(bowdeck); bowdeck.data.materials.append(M_DECK)
box("bulwark", (8, 2*BH*width(L2-10)+0.5, 2.2), (L2-12, 0, DECK + 1.1), principled("bulw", (0.02, 0.05, 0.11), 0.5))
bpy.ops.mesh.primitive_cylinder_add(radius=0.5, depth=14, location=(L2-10, 0, DECK + 9))
bpy.context.object.data.materials.append(M_WHITE)
for s in (-1, 1):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(L2 - 24, s*10.6, 9.0))
    a_ = bpy.context.object; a_.scale = (1.8, 0.5, 1.2); a_.data.materials.append(principled("anchor", (0.04, 0.04, 0.04), 0.6, 0.5))

# foam: bow wave + wake sheets with noise transparency
def foam_mat(name, scale=0.15):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    for n_ in list(nt.nodes): nt.nodes.remove(n_)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    df = nt.nodes.new("ShaderNodeBsdfPrincipled"); df.inputs["Base Color"].default_value = (0.95, 0.96, 0.97, 1); df.inputs["Roughness"].default_value = 0.9
    tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mx = nt.nodes.new("ShaderNodeMixShader")
    tc = nt.nodes.new("ShaderNodeTexCoord"); mpn = nt.nodes.new("ShaderNodeMapping"); mpn.name = "flow"
    nt.links.new(tc.outputs["Object"], mpn.inputs["Vector"])
    n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = scale; n1.inputs["Detail"].default_value = 14; n1.inputs["Roughness"].default_value = 0.72
    nt.links.new(mpn.outputs["Vector"], n1.inputs["Vector"])
    gr = nt.nodes.new("ShaderNodeAttribute"); gr.attribute_name = "fade"; gr.attribute_type = "GEOMETRY"
    rp = nt.nodes.new("ShaderNodeValToRGB"); rp.color_ramp.elements[0].position = 0.44; rp.color_ramp.elements[1].position = 0.58
    nt.links.new(n1.outputs["Fac"], rp.inputs[0])
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'
    nt.links.new(rp.outputs[0], mul.inputs[0]); nt.links.new(gr.outputs["Fac"], mul.inputs[1])
    nt.links.new(mul.outputs[0], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(df.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs[0])
    return m
def foam_strip(name, pts, mat):
    """pts: list of (x, y_inner, y_outer, z, fade) along the hull; builds a strip mesh with a 'fade' attribute."""
    bm = bmesh.new(); prev = None; fades = []
    for (x, yi, yo, z, f) in pts:
        a = bm.verts.new((x, yi, z)); m_ = bm.verts.new((x, (yi*0.6+yo*0.4), z*0.55+0.4)); b_ = bm.verts.new((x, yo, 0.5)); fades += [f, f*0.85, f*0.15]
        if prev:
            bm.faces.new([prev[0], prev[1], m_, a]); bm.faces.new([prev[1], prev[2], b_, m_])
        prev = (a, m_, b_)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    at = me.attributes.new("fade", 'FLOAT', 'POINT')
    for k, v in enumerate(fades): at.data[k].value = v
    o = bpy.data.objects.new(name, me); coll.objects.link(o); o.data.materials.append(mat); return o
FOAM = foam_mat("foam")
for s in (-1, 1):
    pts = []
    for k in range(60):
        x = L2 + 6 - k*4.5
        hb = BH*width(min(x, L2-1))*1.0
        spread = 4 + k*0.9
        pts.append((x, s*(hb + 0.1), s*(hb + spread), 1.6 + 4.5*math.exp(-k/5), max(0.0, 1 - k/45)))
    foam_strip(f"foam{s}", pts, FOAM)
# stern wake
pts = []
for k in range(70):
    x = -L2 - k*6
    w = 16 + k*1.2
    pts.append((x, -w, w, 0.9, max(0.0, 0.9 - k/70)))
wake = foam_strip("wake", [(x, yi, yo, z, f) for (x, yi, yo, z, f) in pts], FOAM)

def set_flow(t):
    FOAM.node_tree.nodes["flow"].inputs["Location"].default_value = (SPEED*t, 0, 0)

# ------------------------------------------------------------------ environment
wo = bpy.data.worlds.new("w"); sc.world = wo; wo.use_nodes = True
bg = wo.node_tree.nodes["Background"]
sky = wo.node_tree.nodes.new("ShaderNodeTexSky"); sky.sky_type = 'MULTIPLE_SCATTERING'
wo.node_tree.links.new(sky.outputs[0], bg.inputs[0])
sky.sun_elevation = math.radians(7); sky.sun_rotation = math.radians(250); sky.altitude = 0; sky.aerosol_density = 1.5; sky.sun_intensity = 0.5
bg.inputs[1].default_value = 0.16
sun_d = bpy.data.lights.new("sun", 'SUN'); sun_d.energy = 3.6; sun_d.color = (1.0, 0.70, 0.48); sun_d.angle = math.radians(0.6)
sun = bpy.data.objects.new("sun", sun_d); coll.objects.link(sun)
sun.rotation_euler = Euler((math.radians(83), 0, math.radians(250+90)))

cam_d = bpy.data.cameras.new("cam"); cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 36; cam_d.clip_end = 100000
cam = bpy.data.objects.new("cam", cam_d); coll.objects.link(cam); sc.camera = cam
SH = [(rnd.uniform(-1, 1), rnd.uniform(-1, 1)) for _ in range(400)]
def shake(t, amp, rate=2.5):
    i = int(t*rate); f = t*rate - i; a, b_ = SH[i % 400], SH[(i+1) % 400]; f = f*f*(3-2*f)
    return (a[0]+(b_[0]-a[0])*f)*amp, (a[1]+(b_[1]-a[1])*f)*amp
def aim(loc, tgt, t, amp):
    cam.location = loc
    e = (Vector(tgt)-Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sx, sy = shake(t, amp); e.x += sx; e.z += sy; cam.rotation_euler = e

def make_ocean():
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
    sea = bpy.context.object
    oc = sea.modifiers.new("ocean", 'OCEAN')
    oc.geometry_mode = 'GENERATE'; oc.size = 1.0; oc.spatial_size = 300; oc.resolution = 12
    oc.repeat_x = 6; oc.repeat_y = 6; oc.wave_scale = 2.6; oc.choppiness = 1.5; oc.wind_velocity = 15; oc.random_seed = 5
    wm = bpy.data.materials.new("water"); wm.use_nodes = True
    b = wm.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.003, 0.016, 0.025, 1); b.inputs["Roughness"].default_value = 0.16; b.inputs["IOR"].default_value = 1.33
    sea.data.materials.append(wm)
    bpy.ops.mesh.primitive_plane_add(size=200000, location=(0, 0, -0.4)); bpy.context.object.data.materials.append(wm)
    return sea, oc

# ship gentle pitching
def ship_motion(t):
    pitch = math.radians(0.35)*math.sin(t*0.55); roll = math.radians(0.5)*math.sin(t*0.37 + 1)
    for o in coll.objects:
        if o.name.startswith(("foam", "wake", "cam", "sun", "sea", "Plane", "ray", "dust", "fog", "surf")) or o.type in ('CAMERA', 'LIGHT'):
            continue
        if o.parent is None and o.name != "shipRoot":
            o.parent = shipRoot
    shipRoot.rotation_euler = (roll, pitch, 0); shipRoot.location.z = 0.25*math.sin(t*0.6)

shipRoot = bpy.data.objects.new("shipRoot", None); coll.objects.link(shipRoot)
for o in list(coll.objects):
    if o.type == 'MESH' and not o.name.startswith(("foam", "wake")) and o.name != "shipRoot":
        o.parent = shipRoot

if SHOT in ("A", "C"):
    sea, oc = make_ocean()
    def pose(t):
        oc.time = t*0.9
        sea.location = (-900 - (SPEED*t) % 300, -900, 0)
        set_flow(t)
        shipRoot.rotation_euler = (math.radians(0.5)*math.sin(t*0.37+1), math.radians(0.35)*math.sin(t*0.55), 0)
        shipRoot.location.z = 0.25*math.sin(t*0.6)
        if SHOT == "A":
            cam_d.lens = 35
            k = ease(t/7.4)
            loc = (lerp(250, 215, k), lerp(-62, -48, k), lerp(14.0, 9.0, k))
            tgt = (lerp(40, 100, k), 0, lerp(20, 8, k))
            aim(loc, tgt, t, math.radians(0.15))
        else:
            k1 = ease((t-12.0)/2.0); k2 = ease((t-23.5)/4.5)
            cam_d.lens = lerp(60, 32, k2)
            loc = (lerp(lerp(210, 205, k1), 330, k2), lerp(-140, -330, k2), lerp(26.0, 20.0, k2))
            tgt = (lerp(120, 20, k2), 0, lerp(-6.0, 10, k2))
            aim(loc, tgt, t, math.radians(0.1))
else:
    # ---------------- underwater
    bg.inputs[1].default_value = 0.0
    wo.node_tree.nodes.remove(sky)
    bg.inputs[0].default_value = (0.004, 0.035, 0.045, 1); bg.inputs[1].default_value = 1.0
    # water surface seen from below
    bpy.ops.mesh.primitive_plane_add(size=6000, location=(0, 0, 0.0)); surf = bpy.context.object; surf.name = "surf"
    sm = bpy.data.materials.new("surf"); sm.use_nodes = True; nt = sm.node_tree
    for n_ in list(nt.nodes): nt.nodes.remove(n_)
    out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission")
    tc = nt.nodes.new("ShaderNodeTexCoord"); vo = nt.nodes.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 0.08
    vo.feature = 'SMOOTH_F1' if hasattr(vo, "feature") else vo.feature
    mpn = nt.nodes.new("ShaderNodeMapping"); mpn.name = "flow"; nt.links.new(tc.outputs["Object"], mpn.inputs["Vector"]); nt.links.new(mpn.outputs["Vector"], vo.inputs["Vector"])
    rp = nt.nodes.new("ShaderNodeValToRGB"); rp.color_ramp.elements[0].color = (0.25, 0.75, 0.85, 1); rp.color_ramp.elements[1].color = (0.05, 0.25, 0.32, 1)
    nt.links.new(vo.outputs["Distance"], rp.inputs[0]); nt.links.new(rp.outputs[0], em.inputs["Color"]); em.inputs["Strength"].default_value = 3.0
    nt.links.new(em.outputs[0], out.inputs[0]); surf.data.materials.append(sm)
    SURF_FLOW = mpn
    # light shafts
    rm = bpy.data.materials.new("ray"); rm.use_nodes = True; nt = rm.node_tree
    for n_ in list(nt.nodes): nt.nodes.remove(n_)
    out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission"); tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    ad = nt.nodes.new("ShaderNodeAddShader"); em.inputs["Color"].default_value = (0.5, 0.9, 1.0, 1)
    tc = nt.nodes.new("ShaderNodeTexCoord"); sp = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Generated"], sp.inputs[0])
    st = nt.nodes.new("ShaderNodeMath"); st.operation = 'MULTIPLY'; st.inputs[1].default_value = 0.05
    nt.links.new(sp.outputs["Z"], st.inputs[0]); nt.links.new(st.outputs[0], em.inputs["Strength"])
    nt.links.new(em.outputs[0], ad.inputs[0]); nt.links.new(tr.outputs[0], ad.inputs[1]); nt.links.new(ad.outputs[0], out.inputs[0])
    for k in range(14):
        x = rnd.uniform(100, 230); y = rnd.uniform(-60, 30)
        bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=rnd.uniform(2.5, 5), radius2=0.6, depth=40, location=(x, y, -20))
        r_ = bpy.context.object; r_.name = f"ray{k}"; r_.rotation_euler = (rnd.uniform(-0.15, 0.15), rnd.uniform(-0.15, 0.15), 0)
        r_.data.materials.append(rm)
    # floating particles
    dm = principled("dust", (0.6, 0.8, 0.8), 0.8, emit=(0.5, 0.8, 0.85), estr=1.2)
    dust = []
    for k in range(260):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=rnd.uniform(0.03, 0.09), location=(rnd.uniform(138, 200), rnd.uniform(-45, 5), rnd.uniform(-22, -1)))
        d_ = bpy.context.object; d_.name = f"dust{k}"; d_.data.materials.append(dm); dust.append((d_, d_.location.copy()))
    # fog volume
    bpy.ops.mesh.primitive_cube_add(size=1, location=(160, -20, -21.5)); fog = bpy.context.object; fog.name = "fog"; fog.scale = (900, 900, 44)
    fm = bpy.data.materials.new("fog"); fm.use_nodes = True; nt = fm.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    vs = nt.nodes.new("ShaderNodeVolumePrincipled"); vs.inputs["Color"].default_value = (0.15, 0.55, 0.6, 1)
    vs.inputs["Density"].default_value = float(os.environ.get("FOGD", "0.011")); vs.inputs["Absorption Color"].default_value = (0.0, 0.25, 0.3, 1)
    nt.links.new(vs.outputs[0], nt.nodes["Material Output"].inputs["Volume"]); fog.data.materials.append(fm)
    sun_d.energy = 2.0; sun_d.color = (0.7, 0.95, 1.0)
    for o in coll.objects:
        if o.name.startswith(("foam", "wake")): o.hide_render = True
    cam_d.lens = 28
    def pose(t):
        k = ease((t-7.4)/4.6)
        SURF_FLOW.inputs["Location"].default_value = (SPEED*t, 0, 0)
        for d_, p0 in dust:
            d_.location = (p0.x - ((SPEED*0.6*t) % 60), p0.y, p0.z)
        shipRoot.rotation_euler = (0, math.radians(0.35)*math.sin(t*0.55), 0)
        loc = (lerp(176, 168, k), lerp(-34, -27, k), lerp(-4.5, -9.5, k))
        tgt = (lerp(132, 128, k), 0, lerp(-6.5, -7.5, k))
        aim(loc, tgt, t, math.radians(0.2))

# ------------------------------------------------------------------ render
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.cycles.samples = int(os.environ.get("SPP", "14")); sc.cycles.use_denoising = True; sc.cycles.use_adaptive_sampling = True
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transparent_max_bounces = 10
sc.cycles.volume_bounces = 0; sc.cycles.volume_step_rate = 6.0; sc.cycles.volume_max_steps = 48
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
        mw = shipRoot.matrix_world
        meta[i] = {"bulb_tip": screen(mw @ BULB_TIP), "bulb_c": screen(mw @ Vector((L2-4, 0, -7.2))),
                   "bulb_top": screen(mw @ Vector((L2-4, 0, -2.2))), "bulb_bot": screen(mw @ Vector((L2-4, 0, -12.2))),
                   "bulb_back": screen(mw @ Vector((L2-21, 0, -7.2))),
                   "stem_wl": screen(mw @ Vector((stem_x(0), 0, 0))), "aft_wl": screen(mw @ Vector((-60, 0, 0))),
                   "fwd_wl": screen(mw @ Vector((L2+60, 0, 0)))}
    json.dump(meta, open(f"{OUT}/meta{SHOT}.json", "w"))
else:
    os.makedirs(f"{OUT}/frames", exist_ok=True)
    step = int(os.environ.get("STEP", "2"))
    for i in range(int(os.environ.get("IFROM", int(round(t0*FPS)))), int(os.environ.get("ITO", int(round(t1*FPS)))), step):
        out = f"{OUT}/frames/f{i:04d}.png"
        if os.path.exists(out): continue
        pose(i/FPS); bpy.context.view_layer.update()
        sc.render.filepath = out; bpy.ops.render.render(write_still=True)
