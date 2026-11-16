import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import bpy, bmesh, math, json, sys, os, random
from mathutils import Vector, Euler
from bpy_extras.object_utils import world_to_camera_view

FPS = 30
RES = (1080, 1920)
OUT = os.environ.get("OUT", QDIR)
SHOT = os.environ.get("SHOT", "A")
SHOTS = {"A": (0.0, 7.8), "B": (7.8, 17.9), "C": (17.9, 29.2)}
SHIPV = 14.0        # m/s carrier speed through the water (water moves past the static ship)
VAPP = 65.0         # m/s jet approach speed relative to the deck (~250 km/h airspeed)
TD = 21.0           # touchdown time
GS = math.radians(3.5)
DECK = 20.0
WIRES = [-110.0, -104.0, -98.0, -92.0]
XTD = -96.0         # main gear x at touchdown
HOOK_DX = -5.2      # hook tip relative to main gear
XCATCH = WIRES[2]   # wire 3
TCATCH = TD + (XTD + HOOK_DX - XCATCH) / -VAPP if False else TD + ((XCATCH - (XTD + HOOK_DX)) / VAPP)
TSTOP = 2.4

def ease(x):
    x = max(0.0, min(1.0, x)); return x*x*(3-2*x)
def lerp(a, b, k): return a + (b-a)*k

def jet_x(t):
    """main gear x position (deck coordinates)"""
    if t <= TCATCH: return XTD + VAPP*(t-TD)
    x0 = XTD + VAPP*(TCATCH-TD); tau = min(t-TCATCH, TSTOP)
    return x0 + VAPP*(tau - tau*tau/(2*TSTOP))
GEARH = 1.75
def jet_z(t):
    if t >= TD: return DECK + GEARH - 0.12*math.exp(-(t-TD)*6)*math.sin((t-TD)*25)
    return DECK + GEARH + math.tan(GS)*VAPP*(TD-t)
def throttle(t):
    if t < TD - 0.05: return 0.35 + 0.05*math.sin(t*1.3)
    if t < TCATCH + TSTOP + 1.2: return lerp(0.35, 1.0, ease((t-TD+0.05)/0.35))
    return lerp(1.0, 0.08, ease((t-(TCATCH+TSTOP+1.2))/1.5))

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; coll = sc.collection
rnd = random.Random(9)

def principled(name, color, rough=0.5, metal=0.0, coat=0.0, emit=None, estr=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal; b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = estr
    return m
def smooth(o):
    for p in o.data.polygons: p.use_smooth = True
def box(name, size, loc, mat, parent=None, rot=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object; o.name = name; o.scale = size; o.data.materials.append(mat)
    if rot: o.rotation_euler = rot
    if parent: o.parent = parent
    return o
def noisy(name, col, rough, scale=0.3, amt=0.35, metal=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    if rough > 0.9: b.inputs["Specular IOR Level"].default_value = 0.15
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = 10
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs["Factor"].default_value = amt
    mix.inputs[6].default_value = (*col, 1); nt.links.new(nz.outputs["Color"], mix.inputs[7])
    nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    return m

# ------------------------------------------------------------------ fighter jet (nose at +X, origin = main gear contact point raised by GEARH)
M_JET = noisy("jetpaint", (0.16, 0.175, 0.19), 0.45, scale=1.2, amt=0.22)
M_JETD = principled("jetdark", (0.14, 0.15, 0.17), 0.5)
M_GLASS = principled("canopy", (0.02, 0.025, 0.03), 0.04, coat=1.0)
M_NOZ = principled("nozzle", (0.12, 0.11, 0.10), 0.35, 0.9)
M_TIRE = principled("tire", (0.02, 0.02, 0.02), 0.8)
M_STRUT = principled("strut", (0.75, 0.75, 0.76), 0.3, 0.8)
M_HOOK = principled("hook", (0.8, 0.8, 0.78), 0.4, 0.6)
GLOWS = []
def glow_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    for n_ in list(nt.nodes): nt.nodes.remove(n_)
    out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission"); em.name = "em"
    em.inputs["Color"].default_value = (1.0, 0.42, 0.12, 1); em.inputs["Strength"].default_value = 5
    nt.links.new(em.outputs[0], out.inputs[0]); return m
def plume_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    for n_ in list(nt.nodes): nt.nodes.remove(n_)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission"); em.name = "em"; em.inputs["Color"].default_value = (1.0, 0.38, 0.1, 1)
    tr = nt.nodes.new("ShaderNodeBsdfTransparent"); ad = nt.nodes.new("ShaderNodeAddShader")
    tc = nt.nodes.new("ShaderNodeTexCoord"); sp = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Generated"], sp.inputs[0])
    pw = nt.nodes.new("ShaderNodeMath"); pw.operation = 'POWER'; pw.inputs[1].default_value = 2.5
    nt.links.new(sp.outputs["Z"], pw.inputs[0])
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'; mul.name = "k"; mul.inputs[1].default_value = 1.0
    nt.links.new(pw.outputs[0], mul.inputs[0]); nt.links.new(mul.outputs[0], em.inputs["Strength"])
    nt.links.new(em.outputs[0], ad.inputs[0]); nt.links.new(tr.outputs[0], ad.inputs[1]); nt.links.new(ad.outputs[0], out.inputs[0])
    return m
M_GLOW = glow_mat("glow"); M_PLUME = plume_mat("plume")

def make_jet(name, hook=True, gear=True, plume=True):
    root = bpy.data.objects.new(name, None); coll.objects.link(root)
    def add(o, m, sm=True):
        o.data.materials.append(m); o.parent = root
        if sm: smooth(o)
        return o
    # fuselage loft: (x, half-width, half-height, zc)
    prof = [(9.6, 0.05, 0.05, 0.55), (9.0, 0.30, 0.28, 0.50), (8.0, 0.55, 0.50, 0.50), (6.5, 0.72, 0.70, 0.55),
            (4.5, 0.90, 0.95, 0.65), (2.5, 1.40, 0.95, 0.6), (0.0, 1.5, 0.95, 0.55), (-3.0, 1.5, 0.90, 0.55),
            (-5.5, 1.38, 0.78, 0.5), (-7.0, 1.22, 0.66, 0.5), (-7.6, 1.15, 0.6, 0.5)]
    bm = bmesh.new(); seg = 32; rings = []
    for x, hw, hh, zc in prof:
        ring = []
        for i in range(seg):
            a = 2*math.pi*i/seg; c, s = math.cos(a), math.sin(a)
            # squarish cross-section
            sx = math.copysign(abs(c)**0.7, c); sz = math.copysign(abs(s)**0.85, s)
            ring.append(bm.verts.new((x, hw*sx, zc + hh*sz)))
        rings.append(ring)
    for j in range(len(rings)-1):
        for i in range(seg):
            bm.faces.new([rings[j][i], rings[j][(i+1) % seg], rings[j+1][(i+1) % seg], rings[j+1][i]])
    bm.faces.new(rings[0]); bm.faces.new(list(reversed(rings[-1])))
    me = bpy.data.meshes.new(name+"_fus"); bm.to_mesh(me); bm.free()
    fus = bpy.data.objects.new(name+"_fus", me); coll.objects.link(fus); add(fus, M_JET)
    # canopy
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1, location=(4.6, 0, 1.35))
    c = bpy.context.object; c.scale = (2.0, 0.6, 0.75); add(c, M_GLASS)
    # radome tip darker
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.32, radius2=0.04, depth=0.9, location=(9.3, 0, 0.53), rotation=(0, math.radians(90), 0))
    add(bpy.context.object, M_JETD)
    # wings / LEX / stabs as thin extruded polygons
    def plate(pts, z, thick, m, nm, mirror=True, rotx=0.0):
        for s in ((1, -1) if mirror else (1,)):
            bm = bmesh.new()
            top = [bm.verts.new((x, s*y, z+thick/2)) for x, y in pts]
            bot = [bm.verts.new((x, s*y, z-thick/2)) for x, y in pts]
            bm.faces.new(top if s > 0 else list(reversed(top))); bm.faces.new(list(reversed(bot)) if s > 0 else bot)
            n = len(pts)
            for i in range(n):
                f = [top[i], bot[i], bot[(i+1) % n], top[(i+1) % n]]
                bm.faces.new(f if s > 0 else list(reversed(f)))
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            me = bpy.data.meshes.new(nm); bm.to_mesh(me); bm.free()
            o = bpy.data.objects.new(nm, me); coll.objects.link(o); add(o, m, sm=False)
            if rotx: o.rotation_euler = (s*rotx, 0, 0)
    plate([(2.0, 1.2), (-3.6, 1.2), (-4.6, 6.2), (-3.4, 6.2)], 0.45, 0.14, M_JET, name+"_wing")
    plate([(6.5, 0.6), (2.0, 1.25), (-0.5, 1.3), (0.5, 0.6)], 0.62, 0.08, M_JET, name+"_lex")
    plate([(-5.6, 1.0), (-7.9, 1.0), (-8.4, 3.4), (-7.6, 3.4)], 0.35, 0.09, M_JET, name+"_stab")
    # twin canted fins
    for s in (1, -1):
        bm = bmesh.new()
        pts = [(-3.2, 0.0), (-6.9, 0.0), (-7.6, 3.4), (-6.3, 3.4)]
        th = 0.08
        top = [bm.verts.new((x, th/2, z)) for x, z in pts]; bot = [bm.verts.new((x, -th/2, z)) for x, z in pts]
        bm.faces.new(top); bm.faces.new(list(reversed(bot)))
        for i in range(4): bm.faces.new([top[i], bot[i], bot[(i+1) % 4], top[(i+1) % 4]])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(name+"_fin"); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new(name+"_fin", me); coll.objects.link(o); add(o, M_JET, sm=False)
        o.location = (0, s*1.0, 1.15); o.rotation_euler = (s*math.radians(-20), 0, 0)
    # intakes
    for s in (1, -1):
        box(name+"_intake", (2.2, 0.55, 0.75), (1.4, s*1.55, 0.05), M_JETD, root)
    # nozzles + glow + plume
    for s in (1, -1):
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.48, depth=1.0, location=(-8.0, s*0.55, 0.45), rotation=(0, math.radians(90), 0))
        add(bpy.context.object, M_NOZ)
        bpy.ops.mesh.primitive_circle_add(vertices=24, radius=0.40, fill_type='NGON', location=(-8.45, s*0.55, 0.45), rotation=(0, math.radians(-90), 0))
        add(bpy.context.object, M_GLOW, sm=False)
        if plume:
            bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.15, radius2=0.42, depth=4.5, location=(-10.7, s*0.55, 0.45), rotation=(0, math.radians(-90), 0))
            p = bpy.context.object; p.name = name+"_plume"; add(p, M_PLUME)
    # gear
    if gear:
        for (x, y, r, w) in ((-0.6, 1.6, 0.52, 0.36), (-0.6, -1.6, 0.52, 0.36), (6.6, 0.0, 0.36, 0.26)):
            bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=r, depth=w, location=(x, y, -GEARH + r), rotation=(math.radians(90), 0, 0))
            add(bpy.context.object, M_TIRE)
            bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.13, depth=GEARH - r + 0.4, location=(x, y*0.85, (-GEARH + r)/2 + 0.1))
            add(bpy.context.object, M_STRUT, sm=False)
    hk = None
    if hook:
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.07, depth=1.0, location=(0, 0, 0))
        hk = bpy.context.object; hk.name = name+"_hook"; add(hk, M_HOOK, sm=False)
        a = Vector((-6.2, 0, -0.2)); b = Vector((HOOK_DX, 0, -GEARH + 0.05))
        hk.location = (a+b)/2; hk.scale = (1, 1, (b-a).length)
        hk.rotation_euler = (b-a).to_track_quat('Z', 'Y').to_euler()
    return root, hk

jet, hook = make_jet("jet")
HOOK_TIP_LOCAL = Vector((HOOK_DX, 0, -GEARH + 0.05))

# ------------------------------------------------------------------ carrier (deck at z=DECK, stern at x=-165, bow at +165)
M_HULL = noisy("hull", (0.16, 0.17, 0.18), 0.6, scale=0.06, amt=0.4)
M_DECK = noisy("deck", (0.05, 0.052, 0.056), 0.95, scale=0.25, amt=0.5)
M_WHITE = principled("mkw", (0.75, 0.75, 0.72), 0.7)
M_YEL = principled("mky", (0.75, 0.55, 0.06), 0.7)
M_ISL = noisy("island", (0.11, 0.115, 0.12), 0.55, scale=0.2, amt=0.25)
M_WIN = principled("win", (0.02, 0.025, 0.03), 0.06, coat=1.0)
M_CABLE = principled("cable", (0.32, 0.30, 0.28), 0.35, 0.8)

def deck_halfwidth(x):
    if x > 120: return lerp(36, 14, ((x-120)/45)**1.3)
    return 36.0
bm = bmesh.new(); xs = [-165 + i*5 for i in range(67)]
for (z, f) in ((DECK, 1.0), (DECK-12, 0.82), (0.0, 0.62), (-11, 0.5)):
    pass
levels = [(DECK, 1.0), (DECK-1.5, 0.98), (DECK-12, 0.80), (1.0, 0.62), (-11.0, 0.52)]
rows = []
for (z, f) in levels:
    row = []
    for x in xs:
        hw = deck_halfwidth(x)*f if z < DECK-1 or True else deck_halfwidth(x)
        if z < DECK-1 and x > 100: hw = max(0.6, hw*(1 - ((x-100)/70)**2*0.7))
        row.append((bm.verts.new((x, hw, z)), bm.verts.new((x, -hw, z))))
    rows.append(row)
for li in range(len(rows)-1):
    for i in range(len(xs)-1):
        a, b, c, d = rows[li][i][0], rows[li][i+1][0], rows[li+1][i+1][0], rows[li+1][i][0]
        bm.faces.new([a, b, c, d])
        a, b, c, d = rows[li][i][1], rows[li][i+1][1], rows[li+1][i+1][1], rows[li+1][i][1]
        bm.faces.new([d, c, b, a])
for i in range(len(xs)-1):
    bm.faces.new([rows[0][i][1], rows[0][i+1][1], rows[0][i+1][0], rows[0][i][0]])
    bm.faces.new([rows[-1][i][0], rows[-1][i+1][0], rows[-1][i+1][1], rows[-1][i][1]])
for i in (0, len(xs)-1):
    for li in range(len(rows)-1):
        f = [rows[li][i][0], rows[li][i][1], rows[li+1][i][1], rows[li+1][i][0]]
        bm.faces.new(f if i == 0 else list(reversed(f)))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
me = bpy.data.meshes.new("carrier"); bm.to_mesh(me); bm.free()
carrier = bpy.data.objects.new("carrier", me); coll.objects.link(carrier)
carrier.data.materials.append(M_HULL); carrier.data.materials.append(M_DECK)
for p in carrier.data.polygons:
    if p.center.z > DECK-0.1 and abs(p.normal.z) > 0.9: p.material_index = 1
# markings
mk = []
for k in range(40):
    x = -160 + k*8.0
    if x > 150: break
    mk.append(box(f"cl{k}", (4.2, 0.35, 0.02), (x, 0, DECK+0.01), M_WHITE))
for s in (1, -1):
    mk.append(box(f"edge{s}", (300, 0.3, 0.02), (-15, s*28.0, DECK+0.01), M_YEL))
for k in range(8):
    mk.append(box(f"stern{k}", (0.6, 4.0, 0.02), (-150, -21 + k*6, DECK+0.01), M_WHITE))
mk.append(box("aimbox", (0.4, 14, 0.02), (-101, 0, DECK+0.012), M_WHITE))
# arresting cables + sheaves
cables = []
for wx in WIRES:
    bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=0.045, depth=1.0)
    cA = bpy.context.object; cA.data.materials.append(M_CABLE)
    bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=0.045, depth=1.0)
    cB = bpy.context.object; cB.data.materials.append(M_CABLE)
    cables.append((wx, cA, cB))
    for s in (1, -1):
        box(f"sheave{wx}{s}", (0.8, 0.8, 0.35), (wx, s*16.5, DECK+0.17), M_HULL)
def seg(o, a, b):
    a, b = Vector(a), Vector(b); o.location = (a+b)/2; o.scale = (1, 1, (b-a).length)
    o.rotation_euler = (b-a).to_track_quat('Z', 'Y').to_euler()
def set_cables(hook_pt, caught):
    for wx, cA, cB in cables:
        if caught and wx == XCATCH:
            mid = (hook_pt.x, hook_pt.y, DECK + 0.12)
        else:
            mid = (wx, 0, DECK + 0.12)
        seg(cA, (wx, 16.3, DECK+0.12), mid); seg(cB, (wx, -16.3, DECK+0.12), mid)
# island (starboard)
box("island", (34, 10, 22), (35, 31, DECK+11), M_ISL)
box("island2", (22, 9, 8), (37, 31, DECK+26), M_ISL)
box("bridgewin", (22.2, 9.2, 1.2), (37, 31, DECK+27.6), M_WIN)
box("islandwin", (34.2, 10.2, 0.9), (35, 31, DECK+18), M_WIN)
bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.6, depth=16, location=(40, 31, DECK+38)); bpy.context.object.data.materials.append(M_ISL)
box("radar1", (0.4, 7, 3.2), (32, 31, DECK+33), M_ISL, rot=(0, 0, 0.6))
box("radar2", (5, 0.3, 4), (44, 31, DECK+31.5), M_ISL)
# parked jets near the bow / island
parked = []
for k, (x, y, yaw) in enumerate(((95, 22, 2.5), (108, 22, 2.5), (121, 21, 2.5), (60, 20, 2.4), (82, -24, -0.4))):
    r, _ = make_jet(f"park{k}", hook=False, gear=True, plume=False)
    r.location = (x, y, DECK + GEARH); r.rotation_euler = (0, 0, yaw); parked.append(r)
# a tractor + deck crew boxes for scale
M_CREW_Y = principled("crewy", (0.8, 0.6, 0.05), 0.7); M_CREW_G = principled("crewg", (0.1, 0.45, 0.12), 0.7)
for k, (x, y, m) in enumerate(((-60, 29.5, M_CREW_Y), (-58, 30.5, M_CREW_G), (-20, 30.0, M_CREW_Y), (-150, -29, M_CREW_G), (-148, -30, M_CREW_Y), (-35, -30, M_CREW_G))):
    box(f"crew{k}", (0.45, 0.35, 1.75), (x, y, DECK+0.88), m)
box("tractor", (3.2, 2.0, 1.4), (-28, 32, DECK+0.7), principled("tug", (0.75, 0.75, 0.72), 0.5))
# LSO platform / port catwalk rail
box("catwalk", (120, 2.5, 0.3), (-80, -37.5, DECK-1.2), M_HULL)

# ------------------------------------------------------------------ sea
wo = bpy.data.worlds.new("w"); sc.world = wo; wo.use_nodes = True
bg = wo.node_tree.nodes["Background"]
sky = wo.node_tree.nodes.new("ShaderNodeTexSky"); sky.sky_type = 'MULTIPLE_SCATTERING'
wo.node_tree.links.new(sky.outputs[0], bg.inputs[0])
SUNROT = float(os.environ.get("SUNROT", "205"))
sky.sun_elevation = math.radians(8); sky.sun_rotation = math.radians(SUNROT); sky.altitude = 0; sky.aerosol_density = 1.4; sky.sun_intensity = 0.5
bg.inputs[1].default_value = 0.17
sun_d = bpy.data.lights.new("sun", 'SUN'); sun_d.energy = 3.4; sun_d.color = (1.0, 0.72, 0.5); sun_d.angle = math.radians(0.6)
sun = bpy.data.objects.new("sun", sun_d); coll.objects.link(sun)
sun.rotation_euler = Euler((math.radians(82), 0, math.radians(SUNROT+90)))

bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
sea = bpy.context.object; sea.name = "sea"
oc = sea.modifiers.new("ocean", 'OCEAN')
oc.geometry_mode = 'GENERATE'; oc.size = 1.0; oc.spatial_size = 400; oc.resolution = 12
oc.repeat_x = 8; oc.repeat_y = 8; oc.wave_scale = 1.6; oc.choppiness = 1.3; oc.wind_velocity = 12; oc.random_seed = 3
wm = bpy.data.materials.new("water"); wm.use_nodes = True
b = wm.node_tree.nodes["Principled BSDF"]
b.inputs["Base Color"].default_value = (0.003, 0.016, 0.025, 1); b.inputs["Roughness"].default_value = 0.14; b.inputs["IOR"].default_value = 1.33
sea.data.materials.append(wm)
bpy.ops.mesh.primitive_plane_add(size=200000, location=(0, 0, -0.5)); bpy.context.object.data.materials.append(wm)
# wake foam
FOAM = bpy.data.materials.new("foam"); FOAM.use_nodes = True; nt = FOAM.node_tree
for n_ in list(nt.nodes): nt.nodes.remove(n_)
out = nt.nodes.new("ShaderNodeOutputMaterial")
df = nt.nodes.new("ShaderNodeBsdfPrincipled"); df.inputs["Base Color"].default_value = (0.92, 0.94, 0.95, 1); df.inputs["Roughness"].default_value = 0.9
tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mx = nt.nodes.new("ShaderNodeMixShader")
tc = nt.nodes.new("ShaderNodeTexCoord"); mpn = nt.nodes.new("ShaderNodeMapping"); mpn.name = "flow"
nt.links.new(tc.outputs["Object"], mpn.inputs["Vector"])
n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 0.12; n1.inputs["Detail"].default_value = 12; n1.inputs["Roughness"].default_value = 0.7
nt.links.new(mpn.outputs["Vector"], n1.inputs["Vector"])
gr = nt.nodes.new("ShaderNodeAttribute"); gr.attribute_name = "fade"; gr.attribute_type = "GEOMETRY"
rp = nt.nodes.new("ShaderNodeValToRGB"); rp.color_ramp.elements[0].position = 0.45; rp.color_ramp.elements[1].position = 0.6
nt.links.new(n1.outputs["Fac"], rp.inputs[0])
mul = nt.nodes.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'
nt.links.new(rp.outputs[0], mul.inputs[0]); nt.links.new(gr.outputs["Fac"], mul.inputs[1])
nt.links.new(mul.outputs[0], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(df.outputs[0], mx.inputs[2])
nt.links.new(mx.outputs[0], out.inputs[0])
def strip(name, pts):
    bm = bmesh.new(); prev = None; fades = []
    for (x, yi, yo, z, f) in pts:
        a = bm.verts.new((x, yi, z)); b_ = bm.verts.new((x, yo, 0.4)); fades += [f, f*0.2]
        if prev: bm.faces.new([prev[0], prev[1], b_, a])
        prev = (a, b_)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    at = me.attributes.new("fade", 'FLOAT', 'POINT')
    for k, v in enumerate(fades): at.data[k].value = v
    o = bpy.data.objects.new(name, me); coll.objects.link(o); o.data.materials.append(FOAM); return o
for s in (1, -1):
    strip(f"bowfoam{s}", [(165 - k*6, s*(18 + k*0.35), s*(22 + k*1.1), 1.2 + 2.5*math.exp(-k/4), max(0, 1 - k/40)) for k in range(55)])
strip("wake", [(-166 - k*8, -18 - k*0.8, 18 + k*0.8, 0.8, max(0, 0.95 - k/80)) for k in range(80)])

# ------------------------------------------------------------------ camera
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

def pose(t):
    oc.time = t*0.8
    sea.location = (-1600 - (SHIPV*t) % 400, -1600, 0)
    FOAM.node_tree.nodes["flow"].inputs["Location"].default_value = (SHIPV*t, 0, 0)
    x, z = jet_x(t), jet_z(t)
    jet.location = (x, 0.0 if t >= TD else 0.6*math.sin(t*0.7)*min(1, (TD-t)/6), z)
    if t < TD:
        jet.rotation_euler = (math.radians(1.5)*math.sin(t*0.9), -math.radians(7.5) + math.radians(0.6)*math.sin(t*1.1), 0)
    else:
        k = ease((t-TD)/0.25)
        dec = ease((t-TCATCH)/0.3)*(1-ease((t-TCATCH-TSTOP)/0.4))
        jet.rotation_euler = (0, lerp(-math.radians(7.5), math.radians(1.5)*dec, k), 0)
    thr = throttle(t)
    M_GLOW.node_tree.nodes["em"].inputs["Strength"].default_value = 1.5 + 32*thr
    M_PLUME.node_tree.nodes["k"].inputs[1].default_value = 0.05 + 1.8*thr**2
    bpy.context.view_layer.update()
    hp = jet.matrix_world @ HOOK_TIP_LOCAL
    set_cables(hp, t >= TCATCH)
    for o in coll.objects:
        if o.name.startswith("jet_plume"): o.hide_render = (SHOT == "A")
    if SHOT == "A":
        k = ease(t/7.8)
        cam_d.lens = lerp(70, 85, k)
        jp = Vector((x, 0, z))
        loc = jp + Vector((lerp(-72, -60, k), lerp(-9, -7, k), lerp(6, 4.5, k)))
        tgt = jp + Vector((lerp(40, 30, k), lerp(4, 3, k), lerp(-4.5, -3.5, k)))
        aim(loc, tgt, t, math.radians(0.18))
    elif SHOT == "B":
        k = ease((t-7.8)/10.1)
        cam_d.lens = lerp(220, 120, k)
        loc = (lerp(-78, -82, k), lerp(-9.0, -8.0, k), DECK + 2.1)
        jp = Vector((x - 2, 0, z - 0.5))
        tgt = Vector((jp.x, jp.y, jp.z - lerp(18, 6, k)))
        aim(loc, tgt, t, math.radians(0.12))
    else:
        k1 = ease((t-17.9)/3.3); k2 = ease((t-23.6)/5.6)
        cam_d.lens = lerp(lerp(85, 48, k1), 50, k2)
        loc = (lerp(-62, -34, k2), lerp(-36.5, -15, k2), lerp(DECK + 1.4, DECK + 1.6, k2))
        jp = Vector((x + lerp(3.0, 0.0, k2), 0, z - 0.9))
        tgt = Vector((jp.x - lerp(0, 3.5, k2), 0, lerp(jp.z, DECK + 1.4, k2)))
        aim(loc, tgt, t, math.radians(0.14 + 0.25*math.exp(-max(0, t-TD)*2.5)*(t > TD)))

# ------------------------------------------------------------------ render
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.cycles.samples = int(os.environ.get("SPP", "12")); sc.cycles.use_denoising = True; sc.cycles.use_adaptive_sampling = True
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transparent_max_bounces = 10
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.resolution_percentage = int(os.environ.get("PCT", "50"))
sc.render.use_persistent_data = True
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
sc.view_settings.exposure = float(os.environ.get("EXPO", "-0.4"))

def screen(p):
    v = world_to_camera_view(sc, cam, Vector(p)); return (v.x*RES[0], (1-v.y)*RES[1], v.z)

def shot_for(t):
    for k, (a, b) in SHOTS.items():
        if a <= t < b: return k
    return "C"
mode = sys.argv[sys.argv.index("--")+1] if "--" in sys.argv else "frames"
if mode == "test":
    for t in [float(x) for x in os.environ.get("TT", "4").split(",")]:
        SHOT = shot_for(t); pose(t)
        sc.render.filepath = f"{OUT}/test_{t}.png"; bpy.ops.render.render(write_still=True)
elif mode == "meta":
    meta = {}
    for i in range(0, int(SHOTS["C"][1]*FPS)):
        t = i/FPS; SHOT = shot_for(t); pose(t)
        mw = jet.matrix_world
        meta[i] = {"hook": screen(mw @ HOOK_TIP_LOCAL), "noz": screen(mw @ Vector((-8.6, 0, 0.45))),
                   "jet": screen(mw @ Vector((0, 0, 0.5))), "nose": screen(mw @ Vector((9.5, 0, 0.5))),
                   "wire": screen((XCATCH, -8, DECK + 0.1)), "wire0": screen((WIRES[0], -9, DECK+0.1)),
                   "thr": throttle(t), "kmh": max(0.0, (jet_x(t+0.01)-jet_x(t))/0.01*3.6 + (0 if t >= TD else 0))}
    json.dump(meta, open(f"{OUT}/meta.json", "w"))
else:
    os.makedirs(f"{OUT}/frames", exist_ok=True)
    step = int(os.environ.get("STEP", "2"))
    i0 = int(os.environ.get("IFROM", "0")); i1 = int(os.environ.get("ITO", int(SHOTS["C"][1]*FPS)))
    for i in range(i0, i1, step):
        out = f"{OUT}/frames/f{i:04d}.png"
        if os.path.exists(out): continue
        t = i/FPS; SHOT = shot_for(t); pose(t)
        sc.render.filepath = out; bpy.ops.render.render(write_still=True)
