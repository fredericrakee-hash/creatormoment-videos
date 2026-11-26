import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
# Quiz #30 - gas-fired switch heaters burning at a snowy rail junction in Chicago (winter dusk)
import bpy, bmesh, math, json, sys, os, random
from mathutils import Vector, Euler, noise
from bpy_extras.object_utils import world_to_camera_view

FPS = 30
RES = (1080, 1920)
OUT = os.environ.get("OUT", QDIR)
SHOT = "A"
SHOTS = {"A": (0.0, 6.6), "B": (6.6, 14.9), "C": (14.9, 20.0), "D": (20.0, 28.8)}
T_IGN = 9.3           # burners light up (in sequence along the rails)
if "frames" in sys.argv:
    _st = int(os.environ.get("STEP", "2")); _a = int(os.environ.get("IFROM", "0")); _b = int(os.environ.get("ITO", int(28.8*FPS)))
    if all(os.path.exists(f"{OUT}/frames/f{i:04d}.png") for i in range(_a, _b, _st)): sys.exit(0)

def ease(x):
    x = max(0.0, min(1.0, x)); return x*x*(3-2*x)
def lerp(a, b, k): return a + (b-a)*k
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; coll = sc.collection
rnd = random.Random(30)

HAZE = (0.55, 0.60, 0.75)
def add_haze(m, dist=900.0, amt=0.85, col=HAZE, strength=0.32):
    nt = m.node_tree; out = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]
    src = out.inputs["Surface"].links[0].from_socket
    cd = nt.nodes.new("ShaderNodeCameraData")
    mth = nt.nodes.new("ShaderNodeMath"); mth.operation = 'DIVIDE'; mth.inputs[1].default_value = -dist
    nt.links.new(cd.outputs["View Distance"], mth.inputs[0])
    ex = nt.nodes.new("ShaderNodeMath"); ex.operation = 'EXPONENT'; nt.links.new(mth.outputs[0], ex.inputs[0])
    inv = nt.nodes.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0; nt.links.new(ex.outputs[0], inv.inputs[1])
    sc_ = nt.nodes.new("ShaderNodeMath"); sc_.operation = 'MULTIPLY'; sc_.inputs[1].default_value = amt; nt.links.new(inv.outputs[0], sc_.inputs[0])
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs[0].default_value = (*col, 1); em.inputs[1].default_value = strength
    mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(sc_.outputs[0], mx.inputs[0]); nt.links.new(src, mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    return m
def principled(name, color, rough=0.5, metal=0.0, emit=None, haze=True, coat=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = (*emit[0], 1); b.inputs["Emission Strength"].default_value = emit[1]
    return add_haze(m) if haze else m
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
def cyl(name, loc, r, depth, axis_, mat, parent=None, verts=24):
    rot = {"x": (0, math.pi/2, 0), "y": (math.pi/2, 0, 0), "z": (0, 0, 0)}[axis_]
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name; o.data.materials.append(mat)
    for p in o.data.polygons: p.use_smooth = True
    if parent: o.parent = parent
    return o
def axis(a, b, da, ia, ib, db):
    out = []; v = a
    while v < b:
        out.append(v); v += da if (v < ia or v > ib) else db
    return out

# ------------------------------------------------------------------ track layout (main line along x, diverging to +y from x = 0)
GAUGE = 1.435; HG = GAUGE/2 + 0.035; ZT = 0.0
R_DIV = 190.0
def div_y(x): return 0.0 if x <= 0 else R_DIV - math.sqrt(max(0.0, R_DIV*R_DIV - x*x))
def div_dir(x):
    if x <= 0: return 0.0
    return math.atan2(x, math.sqrt(max(1.0, R_DIV*R_DIV - x*x)))
XA, XB = -900.0, 900.0
XD_END = 120.0

# ------------------------------------------------------------------ snow ground
def snow_h(x, y):
    d = min(abs(y), abs(y - div_y(max(0.0, min(x, XD_END)))) if x > 0 else abs(y))
    h = 0.03*noise.fractal(Vector((x/3, y/3, 0.3)), 0.6, 2.0, 3) - 0.035*clamp(1 - abs(d - 0.75)/0.25)
    h += -0.25*clamp((d - 3.4)/1.5) + 0.25*clamp((d - 6)/4)
    h += 0.4*clamp((d - 6)/6)*noise.fractal(Vector((x/40, y/40, 1.3)), 0.5, 2.0, 3)
    return h
XS = [-20000, -8000] + axis(-3000, 3000, 30, -150, 200, 0.5) + [3000, 4500, 8000, 20000]
YS = [-20000, -8000] + axis(-3000, 3000, 30, -40, 60, 0.5) + [3000, 8000, 20000]
bm = bmesh.new(); vs = []
for y in YS: vs.append([bm.verts.new((x, y, snow_h(x, y) if abs(x) < 3000 and abs(y) < 3000 else -0.3)) for x in XS])
for j in range(len(YS) - 1):
    for i in range(len(XS) - 1):
        bm.faces.new([vs[j][i], vs[j][i+1], vs[j+1][i+1], vs[j+1][i]])
def snow_mat():
    m = bpy.data.materials.new("snow"); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.55
    b.inputs["Subsurface Weight"].default_value = 0.2; b.inputs["Subsurface Radius"].default_value = (0.4, 0.5, 0.7)
    b.inputs["Specular IOR Level"].default_value = 0.6
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.8; nz.inputs["Detail"].default_value = 8
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    cr = nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (0.62, 0.66, 0.72, 1); cr.color_ramp.elements[1].color = (0.86, 0.88, 0.92, 1)
    nt.links.new(nz.outputs["Fac"], cr.inputs[0])
    # melted, wet patches next to the burners (revealed as they burn)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep.inputs[0])
    # distance from the switch strip: |y| < 2.6 and -3 < x < 16  -> mask
    def band(sock, lo, hi, soft):
        a = nt.nodes.new("ShaderNodeMapRange"); a.inputs[1].default_value = lo - soft; a.inputs[2].default_value = lo; nt.links.new(sock, a.inputs[0])
        b_ = nt.nodes.new("ShaderNodeMapRange"); b_.inputs[1].default_value = hi + soft; b_.inputs[2].default_value = hi; nt.links.new(sock, b_.inputs[0])
        mm = nt.nodes.new("ShaderNodeMath"); mm.operation = 'MULTIPLY'; nt.links.new(a.outputs[0], mm.inputs[0]); nt.links.new(b_.outputs[0], mm.inputs[1])
        return mm.outputs[0]
    bx = band(sep.outputs["X"], -3.0, 16.0, 1.5); by = band(sep.outputs["Y"], -2.4, 2.4 + 0.0, 1.2)
    mk = nt.nodes.new("ShaderNodeMath"); mk.operation = 'MULTIPLY'; nt.links.new(bx, mk.inputs[0]); nt.links.new(by, mk.inputs[1])
    nz2 = nt.nodes.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = 2.0; nt.links.new(tc.outputs["Object"], nz2.inputs["Vector"])
    mk2 = nt.nodes.new("ShaderNodeMath"); mk2.operation = 'MULTIPLY_ADD'; mk2.inputs[1].default_value = 1.0
    nt.links.new(mk.outputs[0], mk2.inputs[0]); nt.links.new(nz2.outputs["Fac"], mk2.inputs[2])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[1].default_value = 1.15; mr.inputs[2].default_value = 1.3; nt.links.new(mk2.outputs[0], mr.inputs[0])
    melt = nt.nodes.new("ShaderNodeMath"); melt.operation = 'MULTIPLY'; melt.inputs[1].default_value = 0.0
    nt.links.new(mr.outputs[0], melt.inputs[0])
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.inputs[7].default_value = (0.05, 0.045, 0.04, 1)
    nt.links.new(melt.outputs[0], mx.inputs[0]); nt.links.new(cr.outputs[0], mx.inputs[6]); nt.links.new(mx.outputs[2], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange"); rr.inputs[3].default_value = 0.55; rr.inputs[4].default_value = 0.12
    nt.links.new(melt.outputs[0], rr.inputs[0]); nt.links.new(rr.outputs[0], b.inputs["Roughness"])
    nz3 = nt.nodes.new("ShaderNodeTexNoise"); nz3.inputs["Scale"].default_value = 60; nz3.inputs["Detail"].default_value = 4
    nt.links.new(tc.outputs["Object"], nz3.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.25
    nt.links.new(nz3.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs[0], b.inputs["Normal"])
    return add_haze(m), melt.inputs[1]
M_SNOW, MELT = snow_mat()
mesh_obj("ground", bm, M_SNOW)

# ------------------------------------------------------------------ sleepers (snow-covered tops), rails
M_TIE = principled("tie", (0.07, 0.055, 0.045), 0.8)
M_TIESNOW = principled("tiesnow", (0.8, 0.83, 0.88), 0.6)
M_RAILS = principled("railside", (0.06, 0.035, 0.025), 0.7, 0.3)
M_RAILTOP = principled("railtop", (0.75, 0.75, 0.75), 0.08, 1.0)
M_PIPE = principled("pipe", (0.10, 0.09, 0.08), 0.5, 0.6)
def path_main(x, side): return Vector((x, side*HG, ZT))
def path_div(x, side):
    a = div_dir(x); return Vector((x - side*HG*math.sin(a), div_y(x) + side*HG*math.cos(a), ZT))
PROF = [(-0.075, 0.0), (0.075, 0.0), (0.075, 0.012), (0.012, 0.03), (0.010, 0.13), (0.036, 0.14), (0.036, 0.172), (-0.036, 0.172), (-0.036, 0.14), (-0.010, 0.13), (-0.012, 0.03), (-0.075, 0.012)]
def rail(name, fn, xs):
    bm = bmesh.new(); rings = []
    for x in xs:
        c = fn(x); a = div_dir(x) if fn is not path_main else 0.0
        n = Vector((-math.sin(a), math.cos(a), 0))
        rings.append([bm.verts.new(c + n*py + Vector((0, 0, pz))) for (py, pz) in PROF])
    nn = len(PROF)
    for a_, b_ in zip(rings[:-1], rings[1:]):
        for i in range(nn):
            f = bm.faces.new([a_[i], a_[(i+1) % nn], b_[(i+1) % nn], b_[i]]); f.material_index = 1 if i == 6 else 0
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); coll.objects.link(o); me.materials.append(M_RAILS); me.materials.append(M_RAILTOP)
    return o
XM = axis(XA, XB + 1, 10.0, -150, 200, 1.0)
for s in (-1, 1): rail(f"main{s}", lambda x, s=s: path_main(x, s), XM)
XDV = axis(0.0, XD_END + 0.1, 1.0, -1e9, 1e9, 1.0)
# diverging outer rail (left, +y) starts at the points; inner diverging rail starts after the frog area (x ~ 26)
rail("divL", lambda x: path_div(x, 1), XDV)
rail("divR", lambda x: path_div(x, -1), [x for x in XDV if x >= 24.0])
# switch blades (points): thin rails from x=0..11 hugging the stock rails, then following the diverging line
def blade(name, fn, x0, x1):
    return rail(name, fn, axis(x0, x1 + 0.01, 0.5, -1e9, 1e9, 0.5))
blade("bladeA", lambda x: path_main(x, 1) + Vector((0, -0.09*clamp(x/11), 0)), 0.0, 11.0)
blade("bladeB", lambda x: path_div(x, -1) + Vector((0, 0.07*(1 - clamp(x/11)), 0)), 0.0, 11.0)
# frog + check rails (simple)
box("frog", 22.0, 26.0, -0.85, -0.55, 0.0, 0.17, M_RAILS, bev=0.01)
# sleepers: long ties in the switch area
bm = bmesh.new(); bm2 = bmesh.new(); x = XA
while x < XB:
    L = 2.6 + (clamp(x/30)*2.4 if 0 <= x <= 40 else 0.0)
    yc = (div_y(x) if 0 <= x <= 40 else 0)*0.5 if x > 0 else 0
    g = bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(0.26, L, 0.18), verts=g["verts"]); bmesh.ops.translate(bm, vec=(x, yc, ZT - 0.09), verts=g["verts"])
    if -200 < x < 260:
        g = bmesh.ops.create_cube(bm2, size=1.0)
        bmesh.ops.scale(bm2, vec=(0.3, L - 0.1, 0.05), verts=g["verts"]); bmesh.ops.translate(bm2, vec=(x + 0.01, yc, ZT + 0.015), verts=g["verts"])
    x += 0.6
mesh_obj("ties", bm, M_TIE, smooth=False)
mesh_obj("tiesnow", bm2, M_TIESNOW, smooth=False)
# diverging track sleepers
bm = bmesh.new(); bm2 = bmesh.new()
for x in axis(40.0, XD_END, 0.6, -1e9, 1e9, 0.6):
    c = Vector((x, div_y(x), ZT - 0.09)); a = div_dir(x)
    g = bmesh.ops.create_cube(bm, size=1.0); bmesh.ops.scale(bm, vec=(0.26, 2.6, 0.18), verts=g["verts"])
    bmesh.ops.rotate(bm, verts=g["verts"], cent=(0, 0, 0), matrix=Euler((0, 0, a)).to_matrix()); bmesh.ops.translate(bm, vec=c, verts=g["verts"])
mesh_obj("ties2", bm, M_TIE, smooth=False)

# ------------------------------------------------------------------ gas burners along the switch (both sides of each stock rail)
M_FLAME = bpy.data.materials.new("flame"); M_FLAME.use_nodes = True; nt = M_FLAME.node_tree
nt.nodes.remove(nt.nodes["Principled BSDF"])
tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Generated"], sep.inputs[0])
cr = nt.nodes.new("ShaderNodeValToRGB")
cr.color_ramp.elements[0].color = (0.35, 0.45, 1.0, 1); cr.color_ramp.elements[1].color = (1.0, 0.22, 0.02, 1)
cr.color_ramp.elements[0].position = 0.0; cr.color_ramp.elements[1].position = 0.35
nt.links.new(sep.outputs["Z"], cr.inputs[0])
emf = nt.nodes.new("ShaderNodeEmission"); nt.links.new(cr.outputs[0], emf.inputs["Color"])
FLAME_E = emf.inputs["Strength"]; FLAME_E.default_value = 4.0
lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.45
nzf = nt.nodes.new("ShaderNodeTexNoise"); nzf.inputs["Scale"].default_value = 6.0; nt.links.new(tc.outputs["Object"], nzf.inputs["Vector"])
ad = nt.nodes.new("ShaderNodeMath"); ad.operation = 'MULTIPLY_ADD'; ad.inputs[1].default_value = 0.6
nt.links.new(nzf.outputs["Fac"], ad.inputs[0]); nt.links.new(lw.outputs["Facing"], ad.inputs[2])
mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[1].default_value = 0.55; mr.inputs[2].default_value = 1.1; mr.inputs[3].default_value = 1.0; mr.inputs[4].default_value = 0.0
nt.links.new(ad.outputs[0], mr.inputs[0])
tr = nt.nodes.new("ShaderNodeBsdfTransparent")
mx = nt.nodes.new("ShaderNodeMixShader"); nt.links.new(mr.outputs[0], mx.inputs[0])
nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(emf.outputs[0], mx.inputs[2])
nt.links.new(mx.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
# flame tongue mesh (teardrop)
bm = bmesh.new(); n = 10; rings = []
for j in range(9):
    u = j/8.0; r = 0.085*math.sin(math.pi*min(1.0, u*1.15 + 0.05))**0.8*(1 - 0.5*u); z = u
    rings.append([bm.verts.new((r*math.cos(2*math.pi*k/n), r*math.sin(2*math.pi*k/n), z)) for k in range(n)])
for a_, b_ in zip(rings[:-1], rings[1:]):
    for k in range(n): bm.faces.new([a_[k], a_[(k+1) % n], b_[(k+1) % n], b_[k]])
flame_me = bpy.data.meshes.new("flame"); bm.to_mesh(flame_me); bm.free(); flame_me.materials.append(M_FLAME)
for p in flame_me.polygons: p.use_smooth = True
FLAMES = []; fr = random.Random(3)
BURNER_LINES = [(1, HG + 0.16), (1, HG - 0.20), (-1, -HG - 0.16), (-1, -HG + 0.20)]
for (s, yy) in BURNER_LINES:
    cyl(f"gas{s}{yy}", (6.5, yy, ZT + 0.03), 0.03, 17.5, "x", M_PIPE, verts=10)
    x = -2.0
    while x < 15.0:
        o = bpy.data.objects.new("fl", flame_me); coll.objects.link(o)
        FLAMES.append({"ob": o, "x": x, "y": yy + fr.uniform(-0.03, 0.03), "ph": fr.uniform(0, 6.28), "h": fr.uniform(0.3, 0.55), "f": fr.uniform(7, 13)})
        x += fr.uniform(0.18, 0.28)
FL_LIGHTS = []
for k in range(5):
    for yy in (-0.9, 0.9):
        ld = bpy.data.lights.new(f"fl{k}{yy}", 'POINT'); ld.color = (1.0, 0.5, 0.16); ld.shadow_soft_size = 0.3; ld.energy = 0
        lo = bpy.data.objects.new(f"fl{k}{yy}", ld); coll.objects.link(lo); lo.location = (-0.5 + k*3.6, yy, 0.35)
        FL_LIGHTS.append((ld, -0.5 + k*3.6, fr.uniform(0, 6.28)))
# heat shimmer / steam rising from the melting snow (soft puffs)
M_STEAM = bpy.data.materials.new("steam"); M_STEAM.use_nodes = True; nt = M_STEAM.node_tree
nt.nodes.remove(nt.nodes["Principled BSDF"])
pv = nt.nodes.new("ShaderNodeVolumePrincipled"); pv.inputs["Color"].default_value = (0.8, 0.8, 0.82, 1); pv.inputs["Anisotropy"].default_value = 0.3
tc2 = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.5; nt.links.new(tc2.outputs["Object"], nz.inputs["Vector"])
gr = nt.nodes.new("ShaderNodeTexGradient"); gr.gradient_type = 'SPHERICAL'; nt.links.new(tc2.outputs["Object"], gr.inputs["Vector"])
mm = nt.nodes.new("ShaderNodeMath"); mm.operation = 'MULTIPLY'; nt.links.new(nz.outputs["Fac"], mm.inputs[0]); nt.links.new(gr.outputs["Fac"], mm.inputs[1])
dn = nt.nodes.new("ShaderNodeMath"); dn.operation = 'MULTIPLY'; dn.inputs[1].default_value = 0.0; nt.links.new(mm.outputs[0], dn.inputs[0])
nt.links.new(dn.outputs[0], pv.inputs["Density"]); nt.links.new(pv.outputs[0], nt.nodes["Material Output"].inputs["Volume"])
STEAM_D = dn.inputs[1]
STEAMS = []
for k in range(0):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.0)
    o = bpy.context.object; o.data.materials.append(M_STEAM); STEAMS.append((o, fr.uniform(-1, 15), fr.choice((-1, 1)), fr.random()))

# ------------------------------------------------------------------ signals, poles, distant city skyline, trees
M_POLE = principled("pole", (0.12, 0.12, 0.13), 0.5, 0.6)
M_RED = principled("red", (0.2, 0.0, 0.0), 0.3, emit=((1.0, 0.08, 0.04), 30.0))
M_GRN = principled("grn", (0.0, 0.2, 0.05), 0.3, emit=((0.1, 1.0, 0.45), 30.0))
for (x, y, cols) in ((-28.0, -3.0, (M_GRN, M_RED)), (42.0, -3.2, (M_RED, M_RED)), (-130.0, 3.0, (M_RED, M_GRN))):
    cyl(f"sig{x}", (x, y, 2.6), 0.1, 5.2, "z", M_POLE, verts=12)
    box(f"sigh{x}", x - 0.2, x + 0.2, y - 0.3, y + 0.3, 4.6, 5.8, principled(f"sb{x}", (0.02, 0.02, 0.02), 0.6), bev=0.05)
    for k, m in enumerate(cols):
        cyl(f"sl{x}{k}", (x - 0.21, y, 5.4 - k*0.4), 0.11, 0.03, "x", m, verts=16)
M_BLD = principled("bld", (0.05, 0.055, 0.07), 0.6)
M_WIN = principled("win", (0.1, 0.08, 0.05), 0.5, emit=((1.0, 0.75, 0.45), 4.0), haze=False)
br = random.Random(12)
for k in range(70):
    x = br.uniform(5200, 6400); y = br.uniform(-1600, 2000)
    w = br.uniform(25, 60); h = br.choice((40, 60, 90, 120, 160, 220, 300, 420)) if abs(y) < 500 else br.uniform(15, 60)
    box(f"b{k}", x - w/2, x + w/2, y - w/2, y + w/2, -1, h, M_BLD, bev=0)
    # lit window bands facing the camera (-x side)
    for j in range(int(h/12)):
        if br.random() < 0.25:
            box(f"bw{k}{j}", x - w/2 - 0.3, x - w/2 - 0.1, y - w/2 + 2, y + w/2 - 2, 4 + j*12, 6 + j*12, M_WIN, bev=0)
M_TREE = principled("tree", (0.035, 0.03, 0.03), 0.9)
bm = bmesh.new()
for k in range(260):
    x = br.uniform(-1500, 1500); y = br.choice((-1, 1))*br.uniform(30, 400)
    if 0 < x < 200 and 0 < y < 60: continue
    h = br.uniform(6, 14)
    g = bmesh.ops.create_cone(bm, cap_ends=True, segments=7, radius1=h*0.28, radius2=0.2, depth=h*0.8)
    bmesh.ops.translate(bm, vec=(x, y, h*0.55), verts=g["verts"])
mesh_obj("trees", bm, M_TREE, smooth=False)

# ------------------------------------------------------------------ commuter train (stainless bi-level cars, cab car leading, heading -x)
M_SS = principled("ss", (0.62, 0.63, 0.65), 0.28, 1.0)
M_SSD = principled("ssd", (0.35, 0.36, 0.38), 0.35, 1.0)
M_GL = principled("gl", (0.02, 0.025, 0.03), 0.05, coat=1.0)
M_GLIT = principled("glit", (0.1, 0.09, 0.07), 0.1, emit=((1.0, 0.85, 0.6), 2.5))
M_HEAD = principled("head", (1, 1, 1), 0.2, emit=((1.0, 0.92, 0.8), 80.0), haze=False)
M_DARK = principled("dark", (0.02, 0.02, 0.025), 0.6)
M_WH = principled("wh", (0.1, 0.09, 0.08), 0.5, 0.8)
CARS = []; WHEELS = []
def car(k, cab):
    P = bpy.data.objects.new(f"car{k}", None); coll.objects.link(P)
    L = 25.9
    box(f"body{k}", -L/2, L/2, -1.55, 1.55, 1.0, 4.75, M_SS, P, 0.12, 3)
    box(f"roof{k}", -L/2 + 0.3, L/2 - 0.3, -1.4, 1.4, 4.75, 4.85, M_SSD, P, 0.05)
    for s in (-1, 1):
        for row, (z0, z1) in enumerate(((1.6, 2.4), (3.3, 4.1))):
            for j in range(14):
                x0 = -L/2 + 1.6 + j*1.62
                box(f"w{k}{s}{row}{j}", x0, x0 + 1.25, s*1.55 - 0.03, s*1.55 + 0.03, z0, z1, M_GLIT if (j + row + k) % 3 else M_GL, P, 0.02)
        for dx in (-L/2 + 1.0, L/2 - 1.3):
            box(f"dr{k}{s}{dx}", dx, dx + 0.35, s*1.55 - 0.02, s*1.55 + 0.02, 1.1, 3.0, M_SSD, P, 0)
        box(f"skirt{k}{s}", -L/2 + 3, L/2 - 3, s*1.4 - 0.03, s*1.4 + 0.03, 0.55, 1.0, M_DARK, P, 0)
    for bx in (-L/2 + 2.6, L/2 - 2.6):
        box(f"bog{k}{bx}", bx - 1.4, bx + 1.4, -1.1, 1.1, 0.45, 0.95, M_DARK, P, 0.03)
        for ax in (bx - 0.95, bx + 0.95):
            for y in (-HG + 0.04, HG - 0.04):
                e = bpy.data.objects.new(f"we{k}{ax}{y}", None); coll.objects.link(e); e.parent = P; e.location = (ax, y, ZT + 0.172 + 0.45)
                cyl(f"wh{k}{ax}{y}", (0, 0, 0), 0.45, 0.13, "y", M_WH, e, 24); WHEELS.append(e)
    if cab:
        # front end at -L/2 (train heads to -x)
        box(f"cabw{k}", -L/2 - 0.05, -L/2 + 0.02, -1.2, 1.2, 3.4, 4.3, M_GL, P, 0.02)
        for s in (-1, 1):
            box(f"hl{k}{s}", -L/2 - 0.08, -L/2, s*0.9 - 0.15, s*0.9 + 0.15, 1.5, 1.75, M_HEAD, P, 0.02)
        box(f"dl{k}", -L/2 - 0.08, -L/2, -0.18, 0.18, 4.45, 4.62, M_HEAD, P, 0.02)
        box(f"plow{k}", -L/2 - 0.5, -L/2 + 0.2, -1.4, 1.4, 0.3, 1.0, M_DARK, P, 0.05)
        sp = bpy.data.lights.new("headspot", 'SPOT'); sp.energy = 4000; sp.spot_size = math.radians(50); sp.color = (1.0, 0.93, 0.8); sp.shadow_soft_size = 0.2
        so = bpy.data.objects.new("headspot", sp); coll.objects.link(so); so.parent = P; so.location = (-L/2 - 0.3, 0, 1.6); so.rotation_euler = (0, -math.radians(95), 0)
    CARS.append((P, L))
for k in range(4): car(k, k == 0)
# train moves -x along the main line: passes the switch around t ~ 16-19
V_TR = 14.0
def front_x(t): return 8.0 + V_TR*(17.6 - t)
def place_train(t, frame=None):
    x = front_x(t)
    for (P, L) in CARS:
        P.location = (x + L/2, 0, ZT)
        if frame is not None:
            P.keyframe_insert("location", frame=frame)
            P.location = (x + L/2 - V_TR/FPS, 0, ZT); P.keyframe_insert("location", frame=frame + 1)
            P.location = (x + L/2, 0, ZT)
        x += L + 1.0
    ang = -(200.0 - front_x(t))/0.45
    for e in WHEELS: e.rotation_euler = (0, ang, 0)

# ------------------------------------------------------------------ sky + sun (winter dusk)
wo = bpy.data.worlds.new("w"); sc.world = wo; wo.use_nodes = True
bg = wo.node_tree.nodes["Background"]
sky = wo.node_tree.nodes.new("ShaderNodeTexSky"); sky.sky_type = 'MULTIPLE_SCATTERING'
wo.node_tree.links.new(sky.outputs[0], bg.inputs[0])
sky.altitude = 0; sky.aerosol_density = 2.2; sky.sun_intensity = 0.35
sun_d = bpy.data.lights.new("sun", 'SUN'); sun_d.angle = math.radians(0.6)
sun = bpy.data.objects.new("sun", sun_d); coll.objects.link(sun)
SUNROT = float(os.environ.get("SUNROT", "200")); SUNEL = float(os.environ.get("SUNEL", "1.5"))
sky.sun_elevation = math.radians(SUNEL); sky.sun_rotation = math.radians(SUNROT)
sun.rotation_euler = Euler((math.radians(90 - SUNEL), 0, math.radians(SUNROT + 90)))
sun_d.energy = 1.6; sun_d.color = (1.0, 0.55, 0.32); bg.inputs[1].default_value = float(os.environ.get("BGS", "0.35"))

# ------------------------------------------------------------------ animation of burners
def ign(x, t):
    # burners light up in a wave from the far end towards the camera side
    return clamp((t - (T_IGN + (15.0 - x)*0.06))/0.35)
def update_fire(t):
    MELT.default_value = 0.9*clamp((t - T_IGN - 1.5)/9.0)
    for f in FLAMES:
        k = ign(f["x"], t); o = f["ob"]
        if k <= 0: o.hide_render = True; continue
        o.hide_render = False
        fl = 0.75 + 0.25*math.sin(t*f["f"] + f["ph"]) + 0.12*math.sin(t*f["f"]*2.3 + 2*f["ph"])
        h = f["h"]*fl*k
        lean = 0.04*math.sin(t*1.3 + f["ph"]*0.2)
        o.location = (f["x"], f["y"], ZT + 0.04); o.scale = (1.0 + 0.2*k, 1.0, max(0.02, h)); o.rotation_euler = (lean, 0.08, 0)
    for ld, x, ph in FL_LIGHTS:
        ld.energy = 30*ign(x, t)*(0.85 + 0.15*math.sin(t*11 + ph))
    for o, x, s, ph in STEAMS:
        u = (t*0.15 + ph) % 1.0; k = ign(x, t)
        o.hide_render = k <= 0
        r = 0.4 + 1.4*u
        o.location = (x + 0.8*u, s*1.3, 0.3 + 3.0*u); o.scale = (r, r*0.8, r*0.8)
    STEAM_D.default_value = 0.35*clamp((t - T_IGN - 1.0)/2.0)

# ------------------------------------------------------------------ camera
cam_d = bpy.data.cameras.new("cam"); cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 36; cam_d.clip_end = 40000; cam_d.clip_start = 0.05
cam = bpy.data.objects.new("cam", cam_d); coll.objects.link(cam); sc.camera = cam
SH = [(rnd.uniform(-1, 1), rnd.uniform(-1, 1)) for _ in range(400)]
def shake(t, amp, rate=1.6):
    i = int(t*rate); f = t*rate - i; a, b_ = SH[i % 400], SH[(i+1) % 400]; f = f*f*(3-2*f)
    return (a[0]+(b_[0]-a[0])*f)*amp, (a[1]+(b_[1]-a[1])*f)*amp
def aim(loc, tgt, t, amp, fstop=None, rate=1.6):
    cam.location = loc
    e = (Vector(tgt)-Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sx, sy = shake(t, amp, rate); e.x += sx; e.z += sy; cam.rotation_euler = e
    if fstop:
        cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = fstop; cam_d.dof.focus_distance = (Vector(tgt) - Vector(loc)).length
    else:
        cam_d.dof.use_dof = False
def pose(t):
    if SHOT == "A":
        k = ease(t/6.6); cam_d.lens = lerp(50, 56, k)
        aim(Vector((lerp(-70, -66, k), lerp(-14, -13, k), lerp(6.0, 5.6, k))), Vector((30, 3, 1.5)), t, math.radians(0.03), fstop=11)
    elif SHOT == "B":
        k = ease((t - 6.6)/8.3); cam_d.lens = lerp(35, 40, k)
        aim(Vector((lerp(-6.5, -5.5, k), lerp(-2.6, -2.4, k), lerp(0.75, 0.65, k))), Vector((8, 0.4, 0.15)), t, math.radians(0.03), fstop=5.6)
    elif SHOT == "C":
        k = ease((t - 14.9)/5.1); cam_d.lens = lerp(45, 48, k)
        aim(Vector((-10.0, -5.2, 1.0)), Vector((lerp(10, 4, k), 0.0, 1.6)), t, math.radians(0.05), fstop=8)
    else:
        k = ease((t - 20.0)/8.8); cam_d.lens = lerp(30, 34, k)
        aim(Vector((lerp(30, 27, k), lerp(-11, -10, k), lerp(6.5, 5.5, k))), Vector((2, 0.5, 0.0)), t, math.radians(0.03), fstop=11)

# ------------------------------------------------------------------ render
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.cycles.samples = int(os.environ.get("SPP", "10")); sc.cycles.use_denoising = True; sc.cycles.use_adaptive_sampling = True
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transparent_max_bounces = 8
sc.cycles.volume_bounces = 0; sc.cycles.volume_step_rate = 6.0; sc.cycles.volume_max_steps = 24
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.resolution_percentage = int(os.environ.get("PCT", "50"))
sc.render.use_persistent_data = True
sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5; sc.render.motion_blur_position = 'START'
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
sc.view_settings.exposure = float(os.environ.get("EXPO", "0.0"))

def screen(p):
    v = world_to_camera_view(sc, cam, Vector(p)); return (v.x*RES[0], (1-v.y)*RES[1], v.z)
def shot_for(t):
    for k, (a, b) in SHOTS.items():
        if a <= t < b: return k
    return "D"
END = SHOTS["D"][1]
def setup(t, frame=None):
    global SHOT
    SHOT = shot_for(t)
    if frame is not None: sc.frame_set(frame)
    place_train(t, frame); update_fire(t); pose(t); bpy.context.view_layer.update()
mode = sys.argv[sys.argv.index("--")+1] if "--" in sys.argv else "frames"
if mode == "test":
    for t in [float(x) for x in os.environ.get("TT", "3").split(",")]:
        setup(t, int(round(t*FPS)))
        sc.render.filepath = f"{OUT}/test_{t}.png"; bpy.ops.render.render(write_still=True)
elif mode == "meta":
    meta = {}
    for i in range(0, int(END*FPS)):
        t = i/FPS; setup(t)
        meta[i] = {"switch": screen((3.0, 0.0, 0.1)), "split": screen((40.0, div_y(40.0)*0.5, 0.2)), "flames": screen((5.0, -HG - 0.16, 0.3)),
                   "train": screen((front_x(t) + 4, 0, 3.0)), "points": screen((1.5, HG - 0.05, 0.17))}
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
