import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import bpy, bmesh, math, json, sys, os, random
from mathutils import Vector, Euler
from bpy_extras.object_utils import world_to_camera_view

FPS = 30
RES = (1080, 1920)
OUT = os.environ.get("OUT", QDIR)
SHOT = "A"
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
        fz_ = 1 - (1 - min(zz/0.22, 1.0))**2.5
        wy = BH*width(xx)*((fz_**(vpow(xx)/0.12)) if zz > 0 else 0.0)
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
e = cr.elements.new(0.53); e.color = (0.025, 0.045, 0.075, 1)                            # navy topsides
nt.links.new(mr.outputs[0], ramp.inputs[0])
nz_ = nt.nodes.new("ShaderNodeTexNoise"); nz_.inputs["Scale"].default_value = 0.08; nz_.inputs["Detail"].default_value = 8
mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1, 1, 6)
nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], nz_.inputs["Vector"])
mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs["Factor"].default_value = 0.45
nt.links.new(ramp.outputs[0], mix.inputs[6]); nt.links.new(nz_.outputs["Color"], mix.inputs[7])
st_ = nt.nodes.new("ShaderNodeTexNoise"); st_.inputs["Scale"].default_value = 0.9; st_.inputs["Detail"].default_value = 6
mps_ = nt.nodes.new("ShaderNodeMapping"); mps_.inputs["Scale"].default_value = (2.5, 2.5, 0.08)
nt.links.new(tc.outputs["Object"], mps_.inputs["Vector"]); nt.links.new(mps_.outputs["Vector"], st_.inputs["Vector"])
rs_ = nt.nodes.new("ShaderNodeValToRGB"); rs_.color_ramp.elements[0].position = 0.55; rs_.color_ramp.elements[0].color = (1, 1, 1, 1)
rs_.color_ramp.elements[1].position = 0.75; rs_.color_ramp.elements[1].color = (0.55, 0.38, 0.28, 1)
nt.links.new(st_.outputs["Fac"], rs_.inputs[0])
mx2 = nt.nodes.new("ShaderNodeMix"); mx2.data_type = 'RGBA'; mx2.blend_type = 'MULTIPLY'; mx2.inputs["Factor"].default_value = 0.8
nt.links.new(mix.outputs[2], mx2.inputs[6]); nt.links.new(rs_.outputs[0], mx2.inputs[7])
nt.links.new(mx2.outputs[2], b.inputs["Base Color"])
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

# ================================================================== q021 additions: Plimsoll / load line mark
SHOTS = {"A": (0.0, 9.0), "B": (9.0, 14.8), "C": (14.8, 23.0), "D": (23.0, 31.4)}
MS = 1.5                                   # mark scale (slightly larger than real for legibility)
MX = -10.0                                 # x of the circle centre (amidships)
from PIL import Image as _I, ImageDraw as _D, ImageFont as _F, ImageFilter as _IF
import numpy as _np
TW_, TH_ = 3.0*MS, 1.5*MS                  # decal size in m (x from MX-0.75*MS, z from -0.6*MS)
PXM = 2400/TW_
def _decal():
    im = _I.new("RGBA", (2400, int(TH_*PXM)), (0, 0, 0, 0)); d = _D.Draw(im)
    def X(x): return (x*MS + 0.75*MS)*PXM
    def Z(z): return im.height - (z*MS + 0.6*MS)*PXM
    th = 0.025*MS*PXM; col = (238, 236, 228, 255)
    r = 0.15
    d.ellipse([X(-r), Z(r), X(r), Z(-r)], outline=col, width=int(th))
    d.rectangle([X(-0.225), Z(0) - th, X(0.225), Z(0)], fill=col)          # bar: upper edge at z=0 (summer)
    f = _F.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(0.16*MS*PXM))
    d.text((X(-0.17), Z(0.02)), "L", font=f, fill=col, anchor="rb"); d.text((X(0.17), Z(0.02)), "R", font=f, fill=col, anchor="lb")
    vx = 0.54
    d.rectangle([X(vx) - th/2, Z(0.55), X(vx) + th/2, Z(-0.33)], fill=col)
    fs = _F.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(0.095*MS*PXM))
    for z, lab, side in ((0.25, "T", 1), (0.0, "S", 1), (-0.25, "W", 1), (-0.33, "WNA", 1), (0.25, "F", -1), (0.50, "TF", -1)):
        x0, x1 = (vx, vx + 0.23) if side > 0 else (vx - 0.23, vx)
        d.rectangle([X(x0), Z(z) - th, X(x1), Z(z)], fill=col)
        if side > 0: d.text((X(x1) + 8, Z(z) - th/2), lab, font=fs, fill=col, anchor="lm")
        else: d.text((X(x0) - 8, Z(z) - th/2), lab, font=fs, fill=col, anchor="rm")
    # worn paint
    a = _np.asarray(im).astype(_np.float32)
    rng_ = _np.random.default_rng(3); nz_ = rng_.random(a.shape[:2])
    nz_ = _np.asarray(_I.fromarray((nz_*255).astype(_np.uint8)).filter(_IF.GaussianBlur(3)), _np.float32)/255
    a[..., 3] *= _np.clip((nz_ - 0.38)*6, 0.55, 1.0)
    p = f"{OUT}/decal.png"; _I.fromarray(a.astype(_np.uint8)).save(p); return p
DECAL = _decal()
dm = bpy.data.materials.new("decal"); dm.use_nodes = True; nt = dm.node_tree
bd = nt.nodes["Principled BSDF"]; bd.inputs["Roughness"].default_value = 0.5
it = nt.nodes.new("ShaderNodeTexImage"); it.image = bpy.data.images.load(DECAL)
nt.links.new(it.outputs["Color"], bd.inputs["Base Color"]); nt.links.new(it.outputs["Alpha"], bd.inputs["Alpha"])
for side in (-1, 1):
    bpy.ops.mesh.primitive_plane_add(size=1, location=(MX + (0.75*MS) - 0.75*MS + 0.75*MS, side*(BH + 0.03), -0.6*MS + TH_/2))
    dec = bpy.context.object; dec.name = f"decal{side}"
    dec.scale = (TW_, TH_, 1); dec.rotation_euler = (math.radians(90), 0, 0 if side < 0 else math.pi)
    dec.location.x = MX - 0.75*MS + TW_/2 if side < 0 else MX + 0.75*MS - TW_/2
    dec.data.materials.append(dm)

# quay, crane, container on the hook (starboard side, +y)
M_CONC = principled("quay", (0.33, 0.32, 0.30), 0.85)
box("quay", (900, 80, 9), (0, BH + 3 + 40, -2.5), M_CONC)
M_CR = principled("crane", (0.30, 0.34, 0.38), 0.5, 0.5)
cranes = []
for cx in (-55.0, 25.0):
    for dx in (-9, 9):
        for yy in (BH + 10, BH + 40):
            box(f"cl{cx}{dx}{yy}", (1.6, 1.6, 48), (cx + dx, yy, 26), M_CR)
        box(f"cb{cx}{dx}", (1.4, 30, 1.4), (cx + dx, BH + 25, 12), M_CR)
    box(f"cport{cx}", (20, 1.6, 2), (cx, BH + 10, 50), M_CR)
    box(f"cport2{cx}", (20, 1.6, 2), (cx, BH + 40, 50), M_CR)
    box(f"boom{cx}", (0.8, 110, 1.0), (cx - 2.9, BH + 5, 52.5), M_CR); box(f"boomb{cx}", (0.8, 110, 1.0), (cx + 2.9, BH + 5, 52.5), M_CR)
    box(f"boomt{cx}", (0.8, 110, 1.0), (cx - 2.9, BH + 5, 55.5), M_CR); box(f"boomu{cx}", (0.8, 110, 1.0), (cx + 2.9, BH + 5, 55.5), M_CR)
    box(f"boomr{cx}", (6.6, 110, 0.4), (cx, BH + 5, 52.2), M_CR)
    for yy in (BH + 10, BH + 40):
        for dx in (-9, 9):
            for zz in (8, 24, 40):
                bb = box(f"cbr{cx}{dx}{yy}{zz}", (0.5, 0.5, 18), (cx + dx, yy, zz), M_CR); bb.rotation_euler = (0, 0, 0)
        for zz in (8, 24, 40):
            bb = box(f"cbx{cx}{yy}{zz}", (0.5, 0.5, 23), (cx, yy, zz + 8), M_CR); bb.rotation_euler = (0, math.radians(52*(1 if zz % 16 else -1)), 0)
    for yy in range(-30, 75, 8):
        bb = box(f"cbb{cx}{yy}", (0.4, 0.4, 5.0), (cx - 2.9, BH + 5 + yy - 50, 54), M_CR); bb.rotation_euler = (math.radians(55), 0, 0)
        bb = box(f"cbc{cx}{yy}", (0.4, 0.4, 5.0), (cx + 2.9, BH + 5 + yy - 50, 54), M_CR); bb.rotation_euler = (math.radians(55), 0, 0)
    box(f"mach{cx}", (14, 12, 7), (cx, BH + 46, 57), principled("mach", (0.75, 0.74, 0.70), 0.5))
    box(f"apex{cx}", (2, 2, 22), (cx, BH + 40, 66), M_CR)
    cranes.append(cx)
trolley = box("trolley", (5, 5, 2), (25, -5, 51.5), principled("trol", (0.2, 0.2, 0.2), 0.5))
spreader = box("hookbox", (12.2, 2.44, 2.6), (25, -5, 30), cmat[1])
cables = [box(f"cab{k}", (0.08, 0.08, 1), (25 + k, -5, 40), principled("cab", (0.05, 0.05, 0.05), 0.4)) for k in (-2, 2)]
# hide sea-going foam in harbour shots
FOAMS = [o for o in coll.objects if o.name.startswith(("foam", "wake"))]

shipRoot = bpy.data.objects.new("shipRoot", None); coll.objects.link(shipRoot)
SKIP = ("foam", "wake", "quay", "cl", "cb", "cport", "boom", "mach", "apex", "trolley", "hookbox", "cab")
for o in list(coll.objects):
    if o.type == 'MESH' and not o.name.startswith(SKIP) and o.name != "shipRoot":
        o.parent = shipRoot
HARBOR = [o for o in coll.objects if o.name.startswith(SKIP[2:])]

# calm harbour water / open sea
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
sea = bpy.context.object; sea.name = "sea"
oc = sea.modifiers.new("ocean", 'OCEAN')
oc.geometry_mode = 'GENERATE'; oc.size = 1.0; oc.spatial_size = 120; oc.resolution = 14
oc.repeat_x = 6; oc.repeat_y = 6; oc.wave_scale = 0.9; oc.choppiness = 1.0; oc.wind_velocity = 9; oc.random_seed = 7
wm = bpy.data.materials.new("water"); wm.use_nodes = True
bw = wm.node_tree.nodes["Principled BSDF"]
bw.inputs["Base Color"].default_value = (0.004, 0.018, 0.024, 1); bw.inputs["Roughness"].default_value = 0.12; bw.inputs["IOR"].default_value = 1.33
sea.data.materials.append(wm)
bpy.ops.mesh.primitive_plane_add(size=200000, location=(0, 0, -0.3)); bpy.context.object.name = "seafar"; bpy.context.object.data.materials.append(wm)

sky.sun_elevation = math.radians(4); sky.sun_rotation = math.radians(-125); sky.aerosol_density = 2.4; bg.inputs[1].default_value = 0.2
sun.rotation_euler = Euler((math.radians(82), 0, math.radians(-35)))
sun_d.energy = 4.2; sun_d.color = (1.0, 0.62, 0.38)

def ship_z(t):
    if SHOT == "A": return 3.6
    if SHOT == "B": return 0.75
    if SHOT == "C": return lerp(4.2, 0.0, ease((t - 15.6)/6.4))
    return 0.0

def pose(t):
    harbor = SHOT != "D"
    for o in HARBOR: o.hide_render = not harbor
    for o in FOAMS: o.hide_render = harbor
    oc.time = t*0.8
    if harbor:
        sea.location = (-360, -360, 0); oc.wave_scale = 0.35 if SHOT in ("B", "C") else 0.6
    else:
        sea.location = (-900 - (SPEED*t) % 120, -900, 0); oc.wave_scale = 1.6; oc.spatial_size = 200
        set_flow(t)
    rz = ship_z(t) + 0.06*math.sin(t*0.6)
    shipRoot.location = (0, 0, rz)
    shipRoot.rotation_euler = (math.radians(0.25)*math.sin(t*0.37 + 1), math.radians(0.15)*math.sin(t*0.5), 0)
    # container being lowered in shot A
    u = ease((t - 0.5)/8.0)
    spreader.location = (25, -5, lerp(42, 30, u))
    for c, k in zip(cables, (-2, 2)):
        top = 51; bot = spreader.location.z + 1.3; c.location = (25 + k, -5, (top + bot)/2); c.scale = (0.08, 0.08, top - bot)
    if SHOT == "A":
        k = ease(t/9.0); cam_d.lens = lerp(30, 33, k)
        aim((lerp(-90, -75, k), -175, 3.0), (lerp(-14, -8, k), 0, lerp(30, 27, k)), t, math.radians(0.06))
    elif SHOT == "B":
        k = ease((t - 9.0)/5.8); cam_d.lens = lerp(46, 52, k)
        aim((MX + lerp(1.4, 1.0, k), -BH - 11, 1.2), (MX + 0.55, 0, 0.95), t, math.radians(0.05))
    elif SHOT == "C":
        k = ease((t - 14.8)/8.2); cam_d.lens = 44
        aim((MX + 0.8, -BH - 22, 1.6), (MX + 0.6, 0, lerp(2.6, 1.6, k)), t, math.radians(0.05))
    else:
        k = ease((t - 23.0)/8.4); cam_d.lens = lerp(58, 52, k)
        aim((lerp(330, 300, k), lerp(-270, -250, k), 7), (lerp(30, 10, k), 0, 12), t, math.radians(0.08))

# ------------------------------------------------------------------ render
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.cycles.samples = int(os.environ.get("SPP", "10")); sc.cycles.use_denoising = True; sc.cycles.use_adaptive_sampling = True
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transparent_max_bounces = 8
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
        mw = shipRoot.matrix_world
        meta[i] = {"circle": screen(mw @ Vector((MX, -BH, 0))), "ladder": screen(mw @ Vector((MX + 0.54*MS + 0.15, -BH, 0.12*MS))),
                   "box": screen(spreader.location), "ship": screen(mw @ Vector((0, -BH, 8))), "wl": screen((MX, -BH, 0))}
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
