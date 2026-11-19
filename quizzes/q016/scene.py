import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import bpy, bmesh, math, json, sys, os, random
from mathutils import Vector, Euler
from bpy_extras.object_utils import world_to_camera_view

FPS = 30
RES = (1080, 1920)
OUT = os.environ.get("OUT", QDIR)
SHOT = os.environ.get("SHOT", "A")
SHOTS = {"A": (0.0, 7.5), "B": (7.5, 13.2), "C": (13.2, 21.0), "D": (21.0, 25.2)}
BAND = 0.07          # solid black band (m)
GRAD = 0.085          # dot gradient width (m)
PITCH = 0.0065        # dot spacing (m)

def ease(x):
    x = max(0.0, min(1.0, x)); return x*x*(3-2*x)
def lerp(a, b, k): return a + (b-a)*k

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; coll = sc.collection
rnd = random.Random(16)

def principled(name, color, rough=0.5, metal=0.0, coat=0.0, emit=None, estr=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal; b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = estr
    return m
def box(name, size, loc, mat, rot=None, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object; o.name = name; o.scale = size; o.data.materials.append(mat)
    if rot: o.rotation_euler = rot
    if bevel:
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        md = o.modifiers.new("bv", 'BEVEL'); md.width = bevel; md.segments = 3
    return o
def cyl(name, r, d, loc, mat, rot=None, v=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=v, radius=r, depth=d, location=loc)
    o = bpy.context.object; o.name = name; o.data.materials.append(mat)
    if rot: o.rotation_euler = rot
    for p in o.data.polygons: p.use_smooth = True
    return o
def mesh_obj(name, bm, mat, smooth=True):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); coll.objects.link(o); o.data.materials.append(mat)
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    return o

# ------------------------------------------------------------------ materials
def paint():
    m = bpy.data.materials.new("paint"); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.30, 0.31, 0.33, 1); b.inputs["Metallic"].default_value = 0.7
    b.inputs["Roughness"].default_value = 0.32; b.inputs["Coat Weight"].default_value = 1.0; b.inputs["Coat Roughness"].default_value = 0.02
    return m
M_PAINT = paint()
M_BLACKPL = principled("blackpl", (0.015, 0.015, 0.016), 0.55)
M_TYRE = principled("tyre", (0.02, 0.02, 0.02), 0.8)
M_RIM = principled("rim", (0.5, 0.5, 0.52), 0.25, 1.0)
M_TINT = principled("tint", (0.005, 0.006, 0.008), 0.03, coat=1.0)
M_DASH = principled("dash", (0.02, 0.02, 0.022), 0.7)
M_HEAD = principled("headliner", (0.42, 0.40, 0.37), 0.9)
M_CHROME = principled("chrome", (0.8, 0.8, 0.8), 0.08, 1.0)

def glass_mat():
    """thin glass + baked-on ceramic frit (band + halftone dots fading inwards)"""
    m = bpy.data.materials.new("windshield"); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent"); tr.inputs[0].default_value = (0.80, 0.86, 0.84, 1)
    gl = nt.nodes.new("ShaderNodeBsdfGlossy"); gl.inputs["Roughness"].default_value = 0.01
    fr = nt.nodes.new("ShaderNodeLayerWeight"); fr.inputs["Blend"].default_value = 0.12
    glass = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(fr.outputs[0], glass.inputs[0]); nt.links.new(tr.outputs[0], glass.inputs[1]); nt.links.new(gl.outputs[0], glass.inputs[2])
    # frit: black ceramic seen through the glass -> black base + glass reflection on top
    fb = nt.nodes.new("ShaderNodeBsdfPrincipled"); fb.inputs["Base Color"].default_value = (0.008, 0.008, 0.009, 1)
    fb.inputs["Roughness"].default_value = 0.4; fb.inputs["Coat Weight"].default_value = 1.0; fb.inputs["Coat Roughness"].default_value = 0.01
    # mask
    um = nt.nodes.new("ShaderNodeAttribute"); um.attribute_name = "um"; um.attribute_type = 'GEOMETRY'
    vm = nt.nodes.new("ShaderNodeAttribute"); vm.attribute_name = "vm"; vm.attribute_type = 'GEOMETRY'
    ed = nt.nodes.new("ShaderNodeAttribute"); ed.attribute_name = "edge"; ed.attribute_type = 'GEOMETRY'
    def M(op, a, b=None, c=None):
        n = nt.nodes.new("ShaderNodeMath"); n.operation = op
        for i, v in enumerate((a, b, c)):
            if v is None: continue
            if isinstance(v, (int, float)): n.inputs[i].default_value = v
            else: nt.links.new(v, n.inputs[i])
        return n.outputs[0]
    # cell-local coords (hex-ish: offset every 2nd row)
    row = M('FLOOR', M('DIVIDE', vm.outputs["Fac"], PITCH))
    shift = M('MULTIPLY', M('MODULO', row, 2.0), 0.5)
    cu = M('SUBTRACT', M('FRACT', M('ADD', M('DIVIDE', um.outputs["Fac"], PITCH), shift)), 0.5)
    cv = M('SUBTRACT', M('FRACT', M('DIVIDE', vm.outputs["Fac"], PITCH)), 0.5)
    dist = M('SQRT', M('ADD', M('MULTIPLY', cu, cu), M('MULTIPLY', cv, cv)))
    # dot radius (in cell units) shrinks from 0.6 at the band to 0 at BAND+GRAD
    g = M('DIVIDE', M('SUBTRACT', ed.outputs["Fac"], BAND), GRAD)
    rad = M('MULTIPLY', M('SUBTRACT', 1.0, M('MINIMUM', M('MAXIMUM', g, 0.0), 1.0)), 0.62)
    dot = M('SUBTRACT', 1.0, M('MINIMUM', M('MAXIMUM', M('MULTIPLY', M('SUBTRACT', dist, rad), 60.0), 0.0), 1.0))
    solid = M('LESS_THAN', ed.outputs["Fac"], BAND)
    mask = M('MAXIMUM', solid, M('MULTIPLY', dot, M('GREATER_THAN', rad, 0.02)))
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(mask, mix.inputs[0]); nt.links.new(glass.outputs[0], mix.inputs[1]); nt.links.new(fb.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    return m
M_GLASS = glass_mat()

# ------------------------------------------------------------------ car body (x forward, y left, z up)
def top_z(x):
    if x > 2.05: return lerp(0.80, 0.62, (x - 2.05)/0.25)
    if x > 0.50: return lerp(0.98, 0.84, (x - 0.50)/1.55)
    if x > -1.65: return 1.00
    return lerp(1.00, 0.92, (-1.65 - x)/0.65)
def half_w(x):
    if x > 1.7: return 0.90*math.sqrt(max(0.05, 1 - ((x - 1.7)/0.62)**2))
    if x < -1.9: return 0.90*math.sqrt(max(0.05, 1 - ((-1.9 - x)/0.45)**2))
    return 0.90
bm = bmesh.new(); rings = []
NS = 48
xs = [2.3 - i*0.05 for i in range(93)]
for x in xs:
    zt, zb, w = top_z(x), 0.28, half_w(x)
    zc = (zt + zb)/2; hz = (zt - zb)/2
    ring = []
    for j in range(NS):
        a = 2*math.pi*j/NS
        c, s = math.cos(a), math.sin(a)
        y = w*math.copysign(abs(c)**(2/5.0), c); z = zc + hz*math.copysign(abs(s)**(2/3.2), s)
        ring.append(bm.verts.new((x, y, z)))
    rings.append(ring)
for i in range(len(rings) - 1):
    for j in range(NS):
        jj = (j + 1) % NS
        bm.faces.new([rings[i][j], rings[i][jj], rings[i+1][jj], rings[i+1][j]])
bm.faces.new(rings[0]); bm.faces.new(list(reversed(rings[-1])))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
body = mesh_obj("body", bm, M_PAINT)
md = body.modifiers.new("sub", 'SUBSURF'); md.levels = 1; md.render_levels = 2

# windshield surface
WX0, WX1, WZ0, WZ1 = 0.52, -0.36, 1.00, 1.43
def ws_point(u, v):
    """u: -1..1 across (+ = left), v: 0..1 bottom -> top"""
    x = lerp(WX0, WX1, v) - 0.10*u*u + 0.03*math.sin(math.pi*v)
    y = u*lerp(0.80, 0.66, v)
    z = lerp(WZ0, WZ1, v) + 0.025*(1 - u*u) - 0.02*u*u*v
    return Vector((x, y, z))
def ws_normal(u, v):
    du = ws_point(u + 0.001, v) - ws_point(u - 0.001, v)
    dv = ws_point(u, v + 0.001) - ws_point(u, v - 0.001)
    n = dv.cross(du).normalized()
    return n if n.z > 0 else -n
NU, NV = 160, 90
bm = bmesh.new(); grid = []
lay_u = bm.verts.layers.float.new("um"); lay_v = bm.verts.layers.float.new("vm"); lay_e = bm.verts.layers.float.new("edge")
for j in range(NV + 1):
    v = j/NV; row = []
    for i in range(NU + 1):
        u = -1 + 2*i/NU; row.append(bm.verts.new(ws_point(u, v)))
    grid.append(row)
for j in range(NV):
    for i in range(NU):
        bm.faces.new([grid[j][i], grid[j][i+1], grid[j+1][i+1], grid[j+1][i]])
# arc lengths in metres
for j in range(NV + 1):
    v = j/NV; acc = 0.0; prev = None
    for i in range(NU + 1):
        p = grid[j][i].co
        if prev is not None: acc += (p - prev).length
        prev = p.copy(); grid[j][i][lay_u] = acc
for i in range(NU + 1):
    acc = 0.0; prev = None
    for j in range(NV + 1):
        p = grid[j][i].co
        if prev is not None: acc += (p - prev).length
        prev = p.copy(); grid[j][i][lay_v] = acc
for j in range(NV + 1):
    for i in range(NU + 1):
        vx = grid[j][i]
        wtot = grid[j][NU][lay_u]; htot = grid[NV][i][lay_v]
        dl = min(vx[lay_u], wtot - vx[lay_u]); db = vx[lay_v]; dt = htot - vx[lay_v]
        vx[lay_e] = min(dl, db*1.6, dt*0.75)       # top band is wider, bottom narrower
bpy.ops.object.select_all(action='DESELECT')
ws = mesh_obj("windshield", bm, M_GLASS)
# A-pillars + roof edge + cowl
def tube(name, pts, r, mat):
    bm = bmesh.new(); prev = None; n = 12
    for k, p in enumerate(pts):
        t_ = (pts[min(k+1, len(pts)-1)] - pts[max(k-1, 0)]).normalized()
        a_ = t_.cross(Vector((0, 0, 1))); a_ = a_.normalized() if a_.length > 1e-4 else Vector((1, 0, 0))
        b_ = t_.cross(a_)
        ring = [bm.verts.new(p + r*(math.cos(2*math.pi*i/n)*a_ + math.sin(2*math.pi*i/n)*b_)) for i in range(n)]
        if prev:
            for i in range(n):
                bm.faces.new([prev[i], prev[(i+1) % n], ring[(i+1) % n], ring[i]])
        prev = ring
    return mesh_obj(name, bm, mat)
for s in (1, -1):
    tube(f"apillar{s}", [ws_point(s*1.0, v) + Vector((0, s*0.03, 0.005)) for v in [k/20 for k in range(21)]], 0.045, M_PAINT)
tube("roofedge", [ws_point(u, 1.0) + Vector((-0.03, 0, 0.012)) for u in [-1 + k/20 for k in range(41)]], 0.04, M_PAINT)
tube("cowl", [ws_point(u, 0.0) + Vector((0.05, 0, -0.005)) for u in [-1 + k/20 for k in range(41)]], 0.035, M_BLACKPL)
# cabin (greenhouse) behind the windshield: tinted side glass + roof
bm = bmesh.new(); rings = []
for k in range(26):
    x = lerp(WX1 + 0.02, -1.75, k/25)
    zr = 1.43 + 0.02*math.sin(math.pi*k/25) - (0.0 if k < 20 else 0.12*((k - 20)/5)**2)
    xb = lerp(WX0, -1.85, k/25)
    ring = [bm.verts.new((xb, 0.80, 1.0)), bm.verts.new((x, 0.66, zr)), bm.verts.new((x, -0.66, zr)), bm.verts.new((xb, -0.80, 1.0))]
    rings.append(ring)
for i in range(len(rings) - 1):
    for j in range(3):
        bm.faces.new([rings[i][j], rings[i+1][j], rings[i+1][j+1], rings[i][j+1]])
cab = mesh_obj("cabin", bm, M_TINT, smooth=False)
cab.data.materials.append(M_PAINT)
for p in cab.data.polygons:
    if abs(p.normal.z) > 0.8: p.material_index = 1
# headliner inside (slightly lower) for the interior shot
bpy.ops.mesh.primitive_plane_add(size=1, location=(-1.05, 0, 1.40)); hl = bpy.context.object
hl.scale = (1.3, 1.3, 1); hl.data.materials.append(M_HEAD)
# B-pillar
for s in (1, -1):
    pass
# wipers, mirror, wheels, lights
for k, yy in enumerate((0.42, -0.18)):
    box(f"wiper{k}", (0.025, 0.62, 0.018), (WX0 - 0.03, yy, WZ0 + 0.02), M_BLACKPL, rot=(0, math.radians(-23), math.radians(4)))
for s in (1, -1):
    box(f"mirror{s}", (0.16, 0.20, 0.11), (0.42, s*1.02, 1.05), M_PAINT, bevel=0.03)
    box(f"mirrorglass{s}", (0.005, 0.17, 0.08), (0.335, s*1.02, 1.05), M_CHROME)
for sx in (1.40, -1.45):
    for s in (1, -1):
        cyl(f"tyre{sx}{s}", 0.34, 0.24, (sx, s*0.80, 0.34), M_TYRE, rot=(math.radians(90), 0, 0))
        cyl(f"rim{sx}{s}", 0.22, 0.25, (sx, s*0.80, 0.34), M_RIM, rot=(math.radians(90), 0, 0))
for s in (1, -1):
    box(f"head{s}", (0.10, 0.36, 0.07), (2.22, s*0.58, 0.74), principled(f"hl{s}", (0.6, 0.6, 0.6), 0.05, 0.5, coat=1.0), rot=(0, math.radians(-25), s*math.radians(-14)))
# dashboard + rear-view mirror (inside)
box("dash", (0.55, 1.5, 0.2), (0.32, 0, 0.90), M_DASH)
box("dashtop", (0.35, 1.45, 0.06), (0.25, 0, 1.00), M_DASH)
cyl("rvmstem", 0.01, 0.05, (ws_point(0, 0.93).x - 0.02, 0, ws_point(0, 0.93).z - 0.03), M_DASH)
box("rvm", (0.04, 0.22, 0.06), (ws_point(0, 0.93).x - 0.04, 0, ws_point(0, 0.93).z - 0.07), M_DASH, bevel=0.012)
# third-visor dots behind the mirror: small frit patch (separate glass sliver with its own edge field)
for s in (1, -1):
    box(f"seat{s}", (0.5, 0.5, 0.65), (-1.25, s*0.38, 0.72), principled(f"seat{s}", (0.10, 0.09, 0.08), 0.85), rot=(0, math.radians(-12), 0))
box("wheel", (0.04, 0.36, 0.36), (0.05, 0.38, 1.0), M_DASH, rot=(0, math.radians(-25), 0))

# ------------------------------------------------------------------ environment: car park at golden hour
def asphalt():
    m = bpy.data.materials.new("asphalt"); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.75
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 60; nz.inputs["Detail"].default_value = 8
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.inputs[6].default_value = (0.035, 0.035, 0.037, 1); mx.inputs[7].default_value = (0.09, 0.085, 0.08, 1)
    nt.links.new(nz.outputs["Fac"], mx.inputs[0]); nt.links.new(mx.outputs[2], b.inputs["Base Color"])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.4
    nt.links.new(nz.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs[0], b.inputs["Normal"])
    return m
bpy.ops.mesh.primitive_plane_add(size=140, location=(0, 0, 0)); ground = bpy.context.object; ground.data.materials.append(asphalt())
bpy.ops.mesh.primitive_plane_add(size=6000, location=(0, 0, -0.02)); field = bpy.context.object
field.data.materials.append(principled("field", (0.09, 0.08, 0.04), 0.9))
M_LINE = principled("line", (0.7, 0.7, 0.68), 0.7)
for k in range(-4, 5):
    box(f"line{k}", (5.0, 0.12, 0.004), (0.2, 1.35 + k*2.7, 0.002), M_LINE)
# other parked cars (simple dark/silver blocks, they stay out of focus) + trees + buildings far away
for k, (x, y, c) in enumerate(((0.3, 2.9, (0.5, 0.5, 0.52)), (0.0, -2.8, (0.25, 0.04, 0.03)), (-0.4, 5.6, (0.8, 0.8, 0.78)),
                               (6.5, 1.5, (0.1, 0.1, 0.12)), (6.8, -1.3, (0.4, 0.42, 0.45)), (7.0, 4.2, (0.05, 0.06, 0.08)))):
    mc = principled(f"car{k}", c, 0.3, 0.5, coat=1.0)
    box(f"oc{k}", (4.4, 1.8, 0.75), (x, y, 0.62), mc, bevel=0.2)
    box(f"ocb{k}", (2.2, 1.5, 0.5), (x - 0.3, y, 1.22), M_TINT, bevel=0.15)
M_TREE = principled("tree", (0.03, 0.05, 0.02), 0.9)
for k in range(0):
    a = rnd.uniform(-math.pi, math.pi); r = rnd.uniform(40, 120)
    x, y = r*math.cos(a), r*math.sin(a)
    if abs(a) < 0.5 and r < 70: continue
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=rnd.uniform(3, 6), location=(x, y, rnd.uniform(4, 7)))
    o = bpy.context.object; o.scale = (1, 1, 1.3); o.data.materials.append(M_TREE)
    cyl(f"trunk{k}", 0.3, 4, (x, y, 2), M_TREE, v=8)
M_BLD = principled("bld", (0.35, 0.33, 0.30), 0.8)
M_TL = principled("treeline", (0.025, 0.035, 0.018), 0.95)
for k in range(140):
    a = 2*math.pi*k/140 + rnd.uniform(-0.02, 0.02); r = rnd.uniform(160, 260)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=rnd.uniform(8, 16), location=(r*math.cos(a), r*math.sin(a), rnd.uniform(-2, 4)))
    o = bpy.context.object; o.scale = (1, 1, rnd.uniform(0.6, 1.0)); o.data.materials.append(M_TL)
for k in range(0):
    a = rnd.uniform(-math.pi, math.pi); r = rnd.uniform(150, 300)
    box(f"bld{k}", (rnd.uniform(20, 60), rnd.uniform(20, 60), rnd.uniform(8, 30)), (r*math.cos(a), r*math.sin(a), 10), M_BLD)
for k in range(5):
    x = rnd.uniform(-20, 20); y = rnd.choice((-1, 1))*rnd.uniform(10, 25)
    cyl(f"lamp{k}", 0.08, 7, (x, y, 3.5), M_RIM, v=8)

wo = bpy.data.worlds.new("w"); sc.world = wo; wo.use_nodes = True
bg = wo.node_tree.nodes["Background"]
sky = wo.node_tree.nodes.new("ShaderNodeTexSky"); sky.sky_type = 'MULTIPLE_SCATTERING'
wo.node_tree.links.new(sky.outputs[0], bg.inputs[0])
sky.altitude = 0; sky.aerosol_density = 1.6; sky.sun_intensity = 0.5
sun_d = bpy.data.lights.new("sun", 'SUN'); sun_d.angle = math.radians(0.6)
sun = bpy.data.objects.new("sun", sun_d); coll.objects.link(sun)
def set_sun(el, rot, energy, color, bgs):
    sky.sun_elevation = math.radians(el); sky.sun_rotation = math.radians(rot)
    sun.rotation_euler = Euler((math.radians(90 - el), 0, math.radians(rot + 90)))
    sun_d.energy = energy; sun_d.color = color; bg.inputs[1].default_value = bgs
SUNROT = float(os.environ.get("SUNROT", "300"))
set_sun(4.5, SUNROT, 3.6, (1.0, 0.58, 0.32), 0.16)

# ------------------------------------------------------------------ camera
cam_d = bpy.data.cameras.new("cam"); cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 36; cam_d.clip_end = 10000; cam_d.clip_start = 0.01
cam = bpy.data.objects.new("cam", cam_d); coll.objects.link(cam); sc.camera = cam
SH = [(rnd.uniform(-1, 1), rnd.uniform(-1, 1)) for _ in range(400)]
def shake(t, amp, rate=1.6):
    i = int(t*rate); f = t*rate - i; a, b_ = SH[i % 400], SH[(i+1) % 400]; f = f*f*(3-2*f)
    return (a[0]+(b_[0]-a[0])*f)*amp, (a[1]+(b_[1]-a[1])*f)*amp
def aim(loc, tgt, t, amp, fstop=None):
    cam.location = loc
    e = (Vector(tgt)-Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sx, sy = shake(t, amp); e.x += sx; e.z += sy; cam.rotation_euler = e
    if fstop:
        cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = fstop
        cam_d.dof.focus_distance = (Vector(tgt) - Vector(loc)).length
    else:
        cam_d.dof.use_dof = False

def u_at(dist_from_left_edge, v):
    """u parameter at a given distance (m) in from the left (+y) edge"""
    W = 2*lerp(0.80, 0.66, v)*1.04
    return 1 - 2*dist_from_left_edge/W
def pose(t):
    if SHOT == "A":
        k = ease(t/7.5)
        cam_d.lens = lerp(32, 45, k)
        loc = Vector((lerp(3.3, 2.2, k), lerp(1.1, 0.75, k), lerp(1.85, 1.65, k)))
        tgt = ws_point(lerp(0.35, 0.6, k), lerp(0.45, 0.35, k))
        aim(loc, tgt, t, math.radians(0.05), fstop=lerp(5.6, 4.0, k))
    elif SHOT == "B":
        u_ = (t - 7.5)/5.7; k = ease(u_)
        cam_d.lens = 42
        d = lerp(0.04, 0.17, k)                       # slide from the solid band across the dots into clear glass
        v = 0.75
        p = ws_point(u_at(d, v), v); n = ws_normal(u_at(d, v), v)
        side = Vector((0, 1, 0))
        loc = p - n*0.22 + side*0.03 - Vector((0.10, 0, 0))
        aim(loc, p, t, math.radians(0.03), fstop=5.6)
    elif SHOT == "C":
        u_ = (t - 13.2)/7.8; k = ease(u_)
        cam_d.lens = lerp(24, 30, k)
        loc = Vector((lerp(-0.62, -0.55, k), lerp(0.22, 0.14, k), 1.20))
        tgt = ws_point(lerp(0.28, 0.12, k), 0.86)
        aim(loc, tgt, t, math.radians(0.06), fstop=4.0)
    else:
        u_ = (t - 21.0)/4.2; k = ease(u_)
        cam_d.lens = lerp(65, 80, k)
        p = ws_point(0.98, 0.22)
        loc = p + Vector((lerp(0.95, 0.75, k), lerp(0.70, 0.55, k), lerp(0.30, 0.24, k)))
        aim(loc, p, t, math.radians(0.03), fstop=3.2)

# ------------------------------------------------------------------ render
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.cycles.samples = int(os.environ.get("SPP", "10")); sc.cycles.use_denoising = True; sc.cycles.use_adaptive_sampling = True
sc.cycles.max_bounces = 6; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 3; sc.cycles.transparent_max_bounces = 8
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.resolution_percentage = int(os.environ.get("PCT", "50"))
sc.render.use_persistent_data = True
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
sc.view_settings.exposure = float(os.environ.get("EXPO", "-0.3"))

def screen(p):
    v = world_to_camera_view(sc, cam, Vector(p)); return (v.x*RES[0], (1-v.y)*RES[1], v.z)
def shot_for(t):
    for k, (a, b) in SHOTS.items():
        if a <= t < b: return k
    return "D"
END = SHOTS["D"][1]
mode = sys.argv[sys.argv.index("--")+1] if "--" in sys.argv else "frames"
if mode == "test":
    for t in [float(x) for x in os.environ.get("TT", "3").split(",")]:
        SHOT = shot_for(t); pose(t); bpy.context.view_layer.update()
        sc.render.filepath = f"{OUT}/test_{t}.png"; bpy.ops.render.render(write_still=True)
elif mode == "meta":
    meta = {}
    for i in range(0, int(END*FPS)):
        t = i/FPS; SHOT = shot_for(t); pose(t); bpy.context.view_layer.update()
        meta[i] = {"band": screen(ws_point(u_at(0.03, 0.3), 0.3)), "dots": screen(ws_point(u_at(0.09, 0.3), 0.3)),
                   "edge": screen(ws_point(0.99, 0.22)), "top": screen(ws_point(0.0, 0.96))}
    json.dump(meta, open(f"{OUT}/meta.json", "w"))
else:
    os.makedirs(f"{OUT}/frames", exist_ok=True)
    step = int(os.environ.get("STEP", "3"))
    i0 = int(os.environ.get("IFROM", "0")); i1 = int(os.environ.get("ITO", int(END*FPS)))
    for i in range(i0, i1, step):
        out = f"{OUT}/frames/f{i:04d}.png"
        if os.path.exists(out): continue
        t = i/FPS; SHOT = shot_for(t); pose(t); bpy.context.view_layer.update()
        sc.render.filepath = out; bpy.ops.render.render(write_still=True)
