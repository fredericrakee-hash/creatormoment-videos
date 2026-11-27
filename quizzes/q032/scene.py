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
bulb.data.transform(bulb.matrix_basis); bulb.matrix_basis.identity()
for p in bulb.data.polygons: p.use_smooth = True
BULB_TIP = Vector((L2 + 13, 0, -7.2))

# ================================================================== q032: ship in a dry dock, red underwater hull
SHOTS = {"A": (0.0, 8.6), "B": (8.6, 16.0), "C": (16.0, 23.9), "D": (23.9, 31.5)}
END = 31.5
if "frames" in sys.argv:
    _st = int(os.environ.get("STEP", "2")); _a = int(os.environ.get("IFROM", "0")); _b = int(os.environ.get("ITO", int(END*FPS)))
    if all(os.path.exists(f"{OUT}/frames/f{i:04d}.png") for i in range(_a, _b, _st)): sys.exit(0)
from mathutils import noise
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
# fresh-paint mask on the hull (x < FRESH and z < waterline): glossier, richer red
bsdf = b
src_col = bsdf.inputs["Base Color"].links[0].from_socket
fx = nt.nodes.new("ShaderNodeMath"); fx.operation = 'LESS_THAN'; FRESH = fx.inputs[1]; FRESH.default_value = -999.0
nt.links.new(sep.outputs["X"], fx.inputs[0])
fz = nt.nodes.new("ShaderNodeMath"); fz.operation = 'LESS_THAN'; fz.inputs[1].default_value = -0.2
nt.links.new(sep.outputs["Z"], fz.inputs[0])
fzl = nt.nodes.new("ShaderNodeMath"); fzl.operation = 'GREATER_THAN'; fzl.inputs[1].default_value = -9.0
nt.links.new(sep.outputs["Z"], fzl.inputs[0])
fm = nt.nodes.new("ShaderNodeMath"); fm.operation = 'MULTIPLY'; nt.links.new(fx.outputs[0], fm.inputs[0]); nt.links.new(fz.outputs[0], fm.inputs[1])
fm2 = nt.nodes.new("ShaderNodeMath"); fm2.operation = 'MULTIPLY'; nt.links.new(fm.outputs[0], fm2.inputs[0]); nt.links.new(fzl.outputs[0], fm2.inputs[1])
mxf = nt.nodes.new("ShaderNodeMix"); mxf.data_type = 'RGBA'; mxf.inputs[7].default_value = (0.42, 0.035, 0.03, 1)
nt.links.new(fm2.outputs[0], mxf.inputs[0]); nt.links.new(src_col, mxf.inputs[6]); nt.links.new(mxf.outputs[2], bsdf.inputs["Base Color"])
rf = nt.nodes.new("ShaderNodeMapRange"); rf.inputs[3].default_value = 0.62; rf.inputs[4].default_value = 0.28
nt.links.new(fm2.outputs[0], rf.inputs[0]); nt.links.new(rf.outputs[0], bsdf.inputs["Roughness"])
# weathered (faded, a bit of grime) old paint lower down: lighten the red slightly by noise
DOCK = -14.6                                   # dock floor (keel blocks 1.6 m high)
GROUND = 2.0                                   # quay level
def box(name, size, loc, mat, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name; o.scale = size; o.data.materials.append(mat); return o
def noisy(name, col, col2, rough, scale, bump=0.3, metal=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt_ = m.node_tree
    b_ = nt_.nodes["Principled BSDF"]; b_.inputs["Roughness"].default_value = rough; b_.inputs["Metallic"].default_value = metal
    tc_ = nt_.nodes.new("ShaderNodeTexCoord"); nz1 = nt_.nodes.new("ShaderNodeTexNoise")
    nz1.inputs["Scale"].default_value = scale; nz1.inputs["Detail"].default_value = 10
    nt_.links.new(tc_.outputs["Object"], nz1.inputs["Vector"])
    cr_ = nt_.nodes.new("ShaderNodeValToRGB"); cr_.color_ramp.elements[0].color = (*col, 1); cr_.color_ramp.elements[1].color = (*col2, 1)
    cr_.color_ramp.elements[0].position = 0.3; cr_.color_ramp.elements[1].position = 0.7
    nt_.links.new(nz1.outputs["Fac"], cr_.inputs[0]); nt_.links.new(cr_.outputs[0], b_.inputs["Base Color"])
    if bump:
        nz2 = nt_.nodes.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = scale*12; nz2.inputs["Detail"].default_value = 4
        nt_.links.new(tc_.outputs["Object"], nz2.inputs["Vector"])
        bp = nt_.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump
        nt_.links.new(nz2.outputs["Fac"], bp.inputs["Height"]); nt_.links.new(bp.outputs[0], b_.inputs["Normal"])
    return m
M_CONC = noisy("conc", (0.24, 0.23, 0.21), (0.40, 0.38, 0.35), 0.85, 0.05, bump=0.2)
M_WET = noisy("wetfloor", (0.10, 0.10, 0.10), (0.26, 0.25, 0.23), 0.25, 0.03, bump=0.05)
M_WOOD = noisy("block", (0.16, 0.10, 0.05), (0.30, 0.20, 0.10), 0.8, 0.8, bump=0.3)
M_STEEL = principled("steelk", (0.32, 0.33, 0.35), 0.4, 0.8)
M_YEL = principled("yellow", (0.75, 0.48, 0.03), 0.45, 0.2)
M_DECK = principled("deck2", (0.20, 0.22, 0.20), 0.8)
M_WHITE = principled("white", (0.82, 0.82, 0.80), 0.45)
M_WIN = principled("win", (0.02, 0.03, 0.04), 0.05, coat=1.0)
M_HATCH = principled("hatch", (0.05, 0.12, 0.22), 0.55, 0.2)
# dock basin: floor, stepped side walls (altars), head wall, gate
DL0, DL1, DW = -165.0, 175.0, 34.0
box("dockfloor", (DL1 - DL0 + 40, 2*DW + 20, 1.0), ((DL0 + DL1)/2, 0, DOCK - 0.5), M_WET)
for s in (-1, 1):
    for k in range(5):
        h = (GROUND - DOCK)*(k + 1)/5
        box(f"altar{s}{k}", (DL1 - DL0, 3.0, h), ((DL0 + DL1)/2, s*(DW + 1.5 + k*2.0), DOCK + h/2), M_CONC)
    box(f"quay{s}", (DL1 - DL0 + 300, 400, GROUND - DOCK), ((DL0 + DL1)/2, s*(DW + 10 + 200), DOCK + (GROUND - DOCK)/2), M_CONC)
box("headwall", (40, 2*DW + 40, GROUND - DOCK), (DL0 - 20, 0, DOCK + (GROUND - DOCK)/2), M_CONC)
box("gate", (8, 2*DW + 6, GROUND - DOCK + 1.0), (DL1 + 4, 0, DOCK + (GROUND - DOCK + 1.0)/2), principled("gate", (0.08, 0.09, 0.1), 0.6, 0.4))
box("gatedeck", (9, 2*DW + 8, 0.6), (DL1 + 4, 0, GROUND + 0.8), M_STEEL)
# keel blocks + side blocks
for k in range(-30, 31):
    x = k*4.0
    if abs(x) > 122: continue
    box(f"kb{k}", (1.2, 2.4, 1.6), (x, 0, DOCK + 0.8), M_WOOD)
    if k % 3 == 0 and abs(x) < 95:
        for s in (-1, 1):
            box(f"sb{k}{s}", (1.4, 1.6, 2.2), (x, s*11.0, DOCK + 1.1), M_WOOD)
# shores (props) against the hull sides
for k in range(-6, 7):
    x = k*16.0 + 4
    for s in (1,):
        bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=0.25, depth=12, location=(x, s*(DW - 6.5), DOCK + 4.5), rotation=(s*math.radians(-58), 0, 0))
        bpy.context.object.data.materials.append(M_WOOD)
# sea beyond the gate
wm = principled("sea", (0.03, 0.06, 0.08), 0.12)
bpy.ops.mesh.primitive_plane_add(size=6000, location=(DL1 + 3010, 0, -0.6)); bpy.context.object.data.materials.append(wm)
# ship upper works (no cargo: hatch covers)
box("deck", (188, 2*BH - 1, 0.6), (-34, 0, DECK), M_DECK)
for bx in range(14):
    x0 = -108 + bx*13.0
    if 28 < x0 < 46: continue
    w_ = width(x0 + 6)
    box(f"hc{bx}", (12.0, 2*BH*w_ - 6, 1.6), (x0 + 6, 0, DECK + 1.1), M_HATCH)
box("house", (14, 34, 36), (37, 0, DECK + 18), M_WHITE)
box("bridge", (9, 46, 4), (40, 0, DECK + 37), M_WHITE)
box("bridgewin", (9.2, 46.2, 1.4), (40, 0, DECK + 37.6), M_WIN)
for k in range(9):
    box(f"housewin{k}", (14.2, 30, 0.6), (37, 0, DECK + 4 + k*3.6), M_WIN)
box("funnel", (10, 8, 20), (-118, 0, DECK + 10), principled("funnel", (0.05, 0.05, 0.06), 0.5))
box("aftdeck", (18, 34, 12), (-115, 0, DECK + 6), M_WHITE)
bpy.ops.mesh.primitive_cylinder_add(radius=0.5, depth=14, location=(L2 - 10, 0, DECK + 9)); bpy.context.object.data.materials.append(M_WHITE)
# propeller + rudder at the stern (visible in the dock)
bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=1.2, depth=3.0, location=(-L2 + 3, 0, -8.5), rotation=(0, math.radians(90), 0)); bpy.context.object.data.materials.append(principled("bronze", (0.55, 0.36, 0.16), 0.3, 1.0))
for k in range(5):
    a = 2*math.pi*k/5
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-L2 + 2.5, 2.6*math.cos(a), -8.5 + 2.6*math.sin(a)), rotation=(a + math.radians(25), 0, 0))
    o = bpy.context.object; o.scale = (0.9, 0.18, 4.2); o.rotation_euler = (a + math.pi/2, math.radians(25), 0); o.data.materials.append(bpy.data.materials["bronze"])
box("rudder", (6, 1.0, 11), (-L2 - 4, 0, -6.5), hm)
# gantry crane on rails along the dock
CR = []
for s in (-1, 1):
    CR.append(box(f"crleg{s}", (3, 3, 58), (-20, s*(DW + 14), GROUND + 29), M_YEL))
CR.append(box("crbeam", (5, 2*(DW + 18), 6), (-20, 0, GROUND + 60), M_YEL))
CR.append(box("crtrolley", (8, 8, 4), (-20, 10, GROUND + 56), M_YEL))
# quayside clutter: containers/sheds, light masts
for k in range(10):
    box(f"shed{k}", (12, 30, 8), (-140 + k*32, -(DW + 60), GROUND + 4), principled(f"shed{k}", (0.3, 0.32, 0.34) if k % 2 else (0.5, 0.48, 0.44), 0.7))
for k in range(-4, 5):
    for s in (-1, 1):
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.3, depth=26, location=(k*40, s*(DW + 22), GROUND + 13)); bpy.context.object.data.materials.append(M_STEEL)
# boom lift with a painter (shot C)
LIFT = bpy.data.objects.new("lift", None); coll.objects.link(LIFT)
def child(o, p=LIFT): o.parent = p; return o
child(box("liftbase", (5, 2.4, 1.4), (0, 0, 0.9), M_YEL))
for k in (-1, 1):
    child(box(f"wheel{k}", (0.9, 2.6, 0.9), (k*1.8, 0, 0.45), principled("tyre", (0.02, 0.02, 0.02), 0.8)))
BOOM = child(box("boom", (0.6, 0.6, 1.0), (0, 0, 0), M_YEL))
BASKET = bpy.data.objects.new("basket", None); coll.objects.link(BASKET); BASKET.parent = LIFT
child(box("bfloor", (1.4, 2.4, 0.15), (0, 0, 0), M_YEL), BASKET)
for (xx, yy, sx, sy) in ((0.7, 0, 0.06, 2.4), (-0.7, 0, 0.06, 2.4), (0, 1.2, 1.4, 0.06), (0, -1.2, 1.4, 0.06)):
    child(box("brail", (sx, sy, 0.06), (xx, yy, 1.1), M_YEL), BASKET)
    child(box("bpost", (0.06, 0.06, 1.1), (xx, yy if sy < 1 else 1.15, 0.55), M_YEL), BASKET)
M_SUIT = principled("suit", (0.55, 0.56, 0.58), 0.85)
def body(par, x, y):
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.2, depth=0.85, location=(x, y, 0.5)); child(bpy.context.object, par).data.materials.append(M_SUIT)
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.24, depth=0.7, location=(x, y, 1.25)); child(bpy.context.object, par).data.materials.append(M_SUIT)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.13, location=(x, y, 1.72)); child(bpy.context.object, par).data.materials.append(principled("skin", (0.35, 0.22, 0.15), 0.6))
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.16, location=(x, y, 1.8)); o = child(bpy.context.object, par); o.scale = (1, 1, 0.6); o.data.materials.append(principled("helmet", (0.85, 0.85, 0.82), 0.35))
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.06, depth=0.7, location=(x - 0.0, y + 0.35, 1.3), rotation=(math.radians(90), 0, 0)); child(bpy.context.object, par).data.materials.append(M_SUIT)
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.03, depth=0.9, location=(x, y + 0.75, 1.3), rotation=(math.radians(90), 0, 0)); child(bpy.context.object, par).data.materials.append(M_STEEL)
body(BASKET, 0.0, -0.4)
# spray mist puffs
def mist_mat():
    m = bpy.data.materials.new("mist"); m.use_nodes = True; nt_ = m.node_tree; nt_.nodes.remove(nt_.nodes["Principled BSDF"])
    tc_ = nt_.nodes.new("ShaderNodeTexCoord"); nz1 = nt_.nodes.new("ShaderNodeTexNoise"); nz1.inputs["Scale"].default_value = 3; nz1.inputs["Detail"].default_value = 6
    nt_.links.new(tc_.outputs["Object"], nz1.inputs["Vector"])
    lw = nt_.nodes.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.5
    ad = nt_.nodes.new("ShaderNodeMath"); ad.operation = 'MULTIPLY'; nt_.links.new(lw.outputs["Facing"], ad.inputs[0]); nt_.links.new(nz1.outputs["Fac"], ad.inputs[1])
    inv = nt_.nodes.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0; nt_.links.new(ad.outputs[0], inv.inputs[1])
    pw = nt_.nodes.new("ShaderNodeMath"); pw.operation = 'MULTIPLY'; pw.inputs[1].default_value = 0.1; nt_.links.new(inv.outputs[0], pw.inputs[0])
    df = nt_.nodes.new("ShaderNodeBsdfTranslucent"); df.inputs["Color"].default_value = (0.9, 0.45, 0.4, 1)
    em = nt_.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (0.6, 0.2, 0.15, 1); em.inputs["Strength"].default_value = 0.3
    a_ = nt_.nodes.new("ShaderNodeAddShader"); nt_.links.new(df.outputs[0], a_.inputs[0]); nt_.links.new(em.outputs[0], a_.inputs[1])
    tr = nt_.nodes.new("ShaderNodeBsdfTransparent"); mx_ = nt_.nodes.new("ShaderNodeMixShader")
    nt_.links.new(pw.outputs[0], mx_.inputs[0]); nt_.links.new(tr.outputs[0], mx_.inputs[1]); nt_.links.new(a_.outputs[0], mx_.inputs[2])
    nt_.links.new(mx_.outputs[0], nt_.nodes["Material Output"].inputs["Surface"])
    return m
M_MIST = mist_mat()
bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
for v in bm.verts: v.co *= 1 + 0.2*noise.noise(v.co*1.7)
puff_me = bpy.data.meshes.new("puff"); bm.to_mesh(puff_me); bm.free()
MIST = []
pr = random.Random(5)
for k in range(14):
    o = bpy.data.objects.new(f"mist{k}", puff_me); coll.objects.link(o); o.data.materials.append(M_MIST)
    MIST.append((o, pr.random(), pr.uniform(-1, 1), pr.uniform(-1, 1)))

# ------------------------------------------------------------------ environment
wo = bpy.data.worlds.new("w"); sc.world = wo; wo.use_nodes = True
bg = wo.node_tree.nodes["Background"]
sky = wo.node_tree.nodes.new("ShaderNodeTexSky"); sky.sky_type = 'MULTIPLE_SCATTERING'
wo.node_tree.links.new(sky.outputs[0], bg.inputs[0])
SUNROT = float(os.environ.get("SUNROT", "-100")); SUNEL = float(os.environ.get("SUNEL", "16"))
sky.sun_elevation = math.radians(SUNEL); sky.sun_rotation = math.radians(SUNROT); sky.altitude = 0; sky.aerosol_density = 1.8; sky.sun_intensity = 0.5
bg.inputs[1].default_value = 0.2
sun_d = bpy.data.lights.new("sun", 'SUN'); sun_d.energy = 3.8; sun_d.color = (1.0, 0.68, 0.44); sun_d.angle = math.radians(0.6)
sun = bpy.data.objects.new("sun", sun_d); coll.objects.link(sun)
sun.rotation_euler = Euler((math.radians(90 - SUNEL), 0, math.radians(SUNROT + 90)))
for s_ in (-1, 1):
    for kx in range(-3, 4):
        d_ = bpy.data.lights.new(f"fill{s_}{kx}", 'AREA'); d_.size = 30; d_.energy = 9000; d_.color = (1.0, 0.85, 0.7)
        o_ = bpy.data.objects.new(f"fill{s_}{kx}", d_); coll.objects.link(o_); o_.location = (kx*40, s_*30, DOCK + 1.0)
        o_.rotation_euler = (Vector((0, 0, -6)) - Vector((0, s_*30, DOCK + 1.0))).to_track_quat('-Z', 'Y').to_euler()
cam_d = bpy.data.cameras.new("cam"); cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 36; cam_d.clip_end = 100000; cam_d.clip_start = 0.1
cam = bpy.data.objects.new("cam", cam_d); coll.objects.link(cam); sc.camera = cam
SH = [(rnd.uniform(-1, 1), rnd.uniform(-1, 1)) for _ in range(400)]
def shake(t, amp, rate=1.8):
    i = int(t*rate); f = t*rate - i; a, b_ = SH[i % 400], SH[(i+1) % 400]; f = f*f*(3-2*f)
    return (a[0]+(b_[0]-a[0])*f)*amp, (a[1]+(b_[1]-a[1])*f)*amp
def aim(loc, tgt, t, amp, rate=1.8):
    cam.location = loc
    e = (Vector(tgt)-Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sx, sy = shake(t, amp, rate); e.x += sx; e.z += sy; cam.rotation_euler = e

# ------------------------------------------------------------------ motion
LX0 = 40.0     # lift drives towards -x while painting (shot C)
def hull_y(x, z):
    zz = (z - KEEL)/(DECK - KEEL); fz_ = 1 - (1 - min(max(zz, 0)/0.22, 1.0))**2.5
    return BH*width(x)*fz_
def place(t):
    u = clamp((t - 16.0)/7.9)
    lx = LX0 - 7.0*u
    LIFT.location = (lx, -(BH + 7.5), DOCK)
    # basket about 5 m up, close to the hull side
    bz = 5.0 + 0.4*math.sin(t*0.7)
    BASKET.location = (0, 3.6, bz)
    BASKET.rotation_euler = (0, 0, 0)
    # boom from base to basket
    p0 = Vector((0, -0.5, 1.6)); p1 = Vector((0, 3.4, bz)); d = p1 - p0
    BOOM.location = (p0 + p1)/2; BOOM.scale = (0.6, 0.6, d.length)
    BOOM.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    # nozzle point (world) and freshly painted region grows behind the painter
    nz_w = Vector((lx, -(BH + 7.5) + 3.6 - 0.4 + 0.75 + 0.6, DOCK + bz + 1.3))
    global NOZ, SPT
    NOZ = nz_w; SPT = Vector((lx + 0.5, -hull_y(lx, DOCK + bz + 1.3) - 0.2, DOCK + bz + 1.6))
    FRESH.default_value = (lx + 3.0) if t >= 16.0 else -999.0
    on = False  # mist drawn in comp (puff stack rendered black)
    for o, ph, ax, az in MIST:
        o.hide_render = not on
        v = (t*1.3 + ph) % 1.0
        r = 0.2 + 0.9*v
        o.location = nz_w + Vector((ax*0.6*v - 0.8*v, 1.8*v + 0.3, az*0.8*v + 0.3*v))
        o.scale = (r, r*0.7, r)
def pose(t):
    cam_d.dof.use_dof = False
    if SHOT == "A":
        k = ease(t/8.6); cam_d.lens = lerp(26, 29, k)
        aim(Vector((lerp(205, 198, k), lerp(-58, -54, k), GROUND + 36)), Vector((lerp(96, 90, k), -6, -7)), t, math.radians(0.05))
    elif SHOT == "B":
        k = ease((t - 8.6)/7.4); cam_d.lens = lerp(16, 17, k)
        loc = Vector((lerp(150, 140, k), -15.0, DOCK + 1.7))
        aim(loc, Vector((60, 2, -4)), t, math.radians(0.08))
    elif SHOT == "C":
        k = ease((t - 16.0)/7.9); cam_d.lens = lerp(32, 34, k)
        lx = LIFT.location.x
        loc = Vector((lx - 24, -32.0, DOCK + 2.4))
        aim(loc, Vector((lx - 3, -(BH + 2), DOCK + 6.5)), t, math.radians(0.07))
        cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = 6.0; cam_d.dof.focus_distance = 22
    else:
        k = ease((t - 23.9)/7.6); cam_d.lens = lerp(36, 33, k)
        aim(Vector((lerp(-215, -205, k), lerp(-96, -90, k), GROUND + 40)), Vector((lerp(-108, -100, k), -8, -7)), t, math.radians(0.05))

# ------------------------------------------------------------------ render
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.cycles.samples = int(os.environ.get("SPP", "10")); sc.cycles.use_denoising = True; sc.cycles.use_adaptive_sampling = True
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transparent_max_bounces = 8
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.resolution_percentage = int(os.environ.get("PCT", "50"))
sc.render.use_persistent_data = True
sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5; sc.render.motion_blur_position = 'START'
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
sc.view_settings.exposure = float(os.environ.get("EXPO", "-0.45"))
def screen(p):
    v = world_to_camera_view(sc, cam, Vector(p)); return (v.x*RES[0], (1-v.y)*RES[1], v.z)
def shot_for(t):
    for k, (a, b_) in SHOTS.items():
        if a <= t < b_: return k
    return "D"
def setup(t, frame=None):
    global SHOT
    SHOT = shot_for(t)
    LIFT.hide_render = SHOT not in ("C",)
    for o in LIFT.children_recursive: o.hide_render = SHOT not in ("C",)
    if frame is not None: sc.frame_set(frame)
    place(t); pose(t); bpy.context.view_layer.update()
mode = sys.argv[sys.argv.index("--")+1] if "--" in sys.argv else "frames"
if mode == "test":
    for t in [float(x) for x in os.environ.get("TT", "3").split(",")]:
        setup(t, int(round(t*FPS)))
        sc.render.filepath = f"{OUT}/test_{t}.png"; bpy.ops.render.render(write_still=True)
elif mode == "meta":
    meta = {}
    for i in range(0, int(END*FPS)):
        t = i/FPS; setup(t)
        meta[i] = {"red": screen(Vector((0, -BH*0.9, -7))), "redB": screen(Vector((95, -BH*0.6, -10))), "wl": screen(Vector((-60, -BH, 0.0))),
                   "bow": screen(BULB_TIP), "keel": screen(Vector((40, 0, DOCK + 1.0))), "lift": screen(Vector(LIFT.location) + Vector((0, 3.6, 7.0))),
                   "fresh": screen(Vector((LIFT.location.x + 6, -BH + 0.5, DOCK + 7))), "noz": screen(NOZ), "spt": screen(SPT), "shot": SHOT}
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
