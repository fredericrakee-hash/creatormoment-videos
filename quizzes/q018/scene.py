import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import bpy, bmesh, math, json, sys, os, random
from mathutils import Vector, Euler, noise
from bpy_extras.object_utils import world_to_camera_view

FPS = 30
RES = (1080, 1920)
OUT = os.environ.get("OUT", QDIR)
SHOT = "A"
SHOTS = {"A": (0.0, 10.0), "B": (10.0, 18.6), "C": (18.6, 24.6), "D": (24.6, 29.4)}
V = 95.0          # m/s ground speed
ALT = 120.0

def ease(x):
    x = max(0.0, min(1.0, x)); return x*x*(3-2*x)
def lerp(a, b, k): return a + (b-a)*k
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; coll = sc.collection
rnd = random.Random(18)

HAZE = (1.0, 0.55, 0.34)
def add_haze(m, dist=2500.0, amt=0.92, col=HAZE, strength=0.35):
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
def principled(name, color, rough=0.5, metal=0.0, coat=0.0, haze=True):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal; b.inputs["Coat Weight"].default_value = coat
    return add_haze(m) if haze else m
def mesh_obj(name, bm, mat, smooth=True, parent=None):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); coll.objects.link(o); o.data.materials.append(mat)
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    if parent: o.parent = parent
    return o
def loft(name, sections, mat, parent=None, cap=True):
    """sections: list of rings (lists of Vector), same length"""
    bm = bmesh.new(); rings = [[bm.verts.new(p) for p in r] for r in sections]; n = len(rings[0])
    for a, b in zip(rings[:-1], rings[1:]):
        for i in range(n):
            bm.faces.new([a[i], a[(i+1) % n], b[(i+1) % n], b[i]])
    if cap:
        bm.faces.new(rings[0]); bm.faces.new(list(reversed(rings[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_obj(name, bm, mat, parent=parent)

# ------------------------------------------------------------------ the transport plane (x forward, y left, z up), origin at the wing root
PLANE = bpy.data.objects.new("plane", None); coll.objects.link(PLANE)
def camo():
    m = bpy.data.materials.new("grey"); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.55; b.inputs["Metallic"].default_value = 0.15
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.6; nz.inputs["Detail"].default_value = 8
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.inputs[6].default_value = (0.075, 0.082, 0.088, 1); mx.inputs[7].default_value = (0.11, 0.12, 0.125, 1)
    nt.links.new(nz.outputs["Fac"], mx.inputs[0]); nt.links.new(mx.outputs[2], b.inputs["Base Color"])
    br = nt.nodes.new("ShaderNodeTexBrick"); br.inputs["Scale"].default_value = 0.6; br.inputs["Mortar Size"].default_value = 0.006
    nt.links.new(tc.outputs["Object"], br.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.15
    nt.links.new(br.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs[0], b.inputs["Normal"])
    return add_haze(m)
M_GREY = camo()
M_DARK = principled("dark", (0.03, 0.03, 0.035), 0.5)
M_GLASS = principled("glass", (0.01, 0.012, 0.015), 0.05, coat=1.0)
NR = 28
def fus_section(x):
    """centre z, half-width, half-height"""
    if x > 12.0:
        k = (x - 12.0)/3.6; f = math.sqrt(max(0.0, 1 - k*k))
        return -0.35*k, 2.15*max(f, 0.02), 2.15*max(f, 0.02)*0.95
    if x > -5.5:
        return 0.0, 2.15, 2.15
    k = (-5.5 - x)/11.0
    return 1.45*k**0.9, 2.15*(1 - 0.78*k), 2.15*(1 - 0.80*k)
secs = []
for i in range(80):
    x = lerp(15.55, -16.5, i/79)
    zc, w, h = fus_section(x)
    ring = []
    for j in range(NR):
        a = 2*math.pi*j/NR
        c, s = math.cos(a), math.sin(a)
        bot = 0.85 if s < 0 else 1.0
        ring.append(Vector((x, w*c, zc + h*s*bot)))
    secs.append(ring)
fus = loft("fuselage", secs, M_GREY, PLANE)
# cockpit windows: dark band on the nose
for s in (1, -1):
    bm = bmesh.new()
    pts = []
    for i in range(7):
        x = lerp(13.6, 11.6, i/6); zc, w, h = fus_section(x)
        a = math.radians(lerp(38, 60, 0.5))
        pts.append((x, s*w*math.cos(a)*1.01, zc + h*math.sin(a)*1.01))
    for i in range(6):
        x0, x1 = pts[i][0], pts[i+1][0]
        v = [bm.verts.new(p) for p in ((x0, pts[i][1], pts[i][2] - 0.22), (x1, pts[i+1][1], pts[i+1][2] - 0.22),
                                         (x1, pts[i+1][1]*0.86, pts[i+1][2] + 0.18), (x0, pts[i][1]*0.86, pts[i][2] + 0.18))]
        bm.faces.new(v)
    mesh_obj(f"cockpit{s}", bm, M_GLASS, parent=PLANE)
# radome tip a bit darker
bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.5, location=(15.4, 0, -0.3))
o = bpy.context.object; o.scale = (0.6, 1, 1); o.data.materials.append(M_DARK); o.parent = PLANE
def airfoil(name, le_root, te_root, le_tip, te_tip, span_axis, t_root, t_tip, mat, z_root=0, z_tip=0, n=24):
    secs = []
    for j in range(9):
        k = j/8
        L = lerp(le_root, le_tip, k); T = lerp(te_root, te_tip, k)
        sp = lerp(span_axis[0], span_axis[1], k); z0 = lerp(z_root, z_tip, k); tt = lerp(t_root, t_tip, k)
        ring = []
        for i in range(n):
            a = 2*math.pi*i/n; u = 0.5*(1 + math.cos(a))
            th = 5*tt*(0.2969*math.sqrt(u) - 0.126*u - 0.3516*u*u + 0.2843*u**3 - 0.1036*u**4)*(1 if math.sin(a) >= 0 else -0.6)
            c = L - T
            ring.append((L - c*u, sp, z0 + th*c))
        secs.append(ring)
    return secs
def place(secs, axis):
    out = []
    for r in secs:
        if axis == 'y': out.append([Vector((p[0], p[1], p[2])) for p in r])
        else: out.append([Vector((p[0], p[2], p[1])) for p in r])
    return out
for s in (1, -1):
    w = airfoil("wing", 2.4, -2.1, 0.6, -1.2, (s*1.6, s*20.2), 0.17, 0.12, M_GREY, 2.05, 2.25)
    loft(f"wing{s}", place(w, 'y'), M_GREY, PLANE)
    w = airfoil("hstab", -11.2, -14.6, -12.8, -14.8, (s*0.6, s*8.0), 0.12, 0.10, M_GREY, 1.6, 1.7)
    loft(f"hstab{s}", place(w, 'y'), M_GREY, PLANE)
fin = airfoil("fin", -9.0, -14.0, -13.2, -15.6, (1.6, 9.6), 0.12, 0.10, M_GREY, 0, 0)
loft("fin", place(fin, 'z'), M_GREY, PLANE)
# engine nacelles + propeller discs
PROPS = []
M_PROP = bpy.data.materials.new("propdisc"); M_PROP.use_nodes = True; nt = M_PROP.node_tree
for n_ in list(nt.nodes): nt.nodes.remove(n_)
po = nt.nodes.new("ShaderNodeOutputMaterial"); pt = nt.nodes.new("ShaderNodeBsdfTransparent")
pd = nt.nodes.new("ShaderNodeBsdfDiffuse"); pd.inputs[0].default_value = (0.02, 0.02, 0.02, 1)
pm = nt.nodes.new("ShaderNodeMixShader"); pm.inputs[0].default_value = 0.22
nt.links.new(pt.outputs[0], pm.inputs[1]); nt.links.new(pd.outputs[0], pm.inputs[2]); nt.links.new(pm.outputs[0], po.inputs[0])
for y in (5.2, 10.4, -5.2, -10.4):
    secs = []
    for i in range(14):
        x = lerp(4.6, -3.2, i/13); k = i/13
        r = 0.62*math.sqrt(max(0.05, min(1, (4.7 - x)/0.9)))*(1 - 0.45*max(0, (k - 0.6)/0.4))
        zc = 1.55 - 0.35*max(0, 1 - k*3)
        secs.append([Vector((x, y + r*math.cos(2*math.pi*j/16), zc + 1.25*r*math.sin(2*math.pi*j/16))) for j in range(16)])
    loft(f"nac{y}", secs, M_GREY, PLANE)
    bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=0.42, depth=0.9, location=(5.0, y, 1.35), rotation=(0, math.pi/2, 0))
    o = bpy.context.object; o.data.materials.append(M_DARK); o.parent = PLANE
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=2.05, depth=0.03, location=(4.75, y, 1.35), rotation=(0, math.pi/2, 0))
    o = bpy.context.object; o.data.materials.append(M_PROP); o.parent = PLANE
# landing gear sponsons
for s in (1, -1):
    secs = []
    for i in range(10):
        x = lerp(3.5, -4.0, i/9); k = abs(i/9 - 0.5)*2; r = 0.9*math.sqrt(max(0.05, 1 - k**3))
        secs.append([Vector((x, s*1.9 + s*r*0.5*math.cos(2*math.pi*j/12), -1.0 + r*0.9*math.sin(2*math.pi*j/12))) for j in range(12)])
    loft(f"sponson{s}", secs, M_GREY, PLANE)
# flare dispensers: small dark panels on the rear fuselage sides
DISP = []
for s in (1, -1):
    for dx in (0.0, 0.9):
        x = -6.4 - dx; zc, w, h = fus_section(x)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, s*(w*0.86), zc - h*0.45))
        o = bpy.context.object; o.scale = (0.7, 0.12, 0.45); o.data.materials.append(M_DARK); o.parent = PLANE
        DISP.append((Vector((x, s*(w*0.92), zc - h*0.5)), s))
# nav/anti-collision lights
for s, c in ((1, (1, 0.05, 0.02)), (-1, (0.05, 1, 0.1))):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, location=(0.3, s*20.25, 2.3))
    o = bpy.context.object; o.parent = PLANE
    m = bpy.data.materials.new(f"nav{s}"); m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = (*c, 1)
    m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 30
    o.data.materials.append(m)

def plane_pos(t): return Vector((V*t, 0.0, ALT + 1.5*math.sin(t*0.35)))
def plane_rot(t): return Euler((math.radians(1.2*math.sin(t*0.5)), math.radians(-2.0), 0))

# ------------------------------------------------------------------ flares: precomputed trajectories
SALVOS = [5.0 + 0.24*n for n in range(14)] + [11.2 + 0.24*n for n in range(22)] + [19.0 + 0.24*n for n in range(12)] + [25.3, 25.95, 26.6, 27.25]
FL = []
GRAV = Vector((0, 0, -9.81))
for ts in SALVOS:
    for (dp, s) in DISP[0:1] + DISP[2:3]:
        if rnd.random() < 0.15 and ts < 24: continue
        p0 = plane_pos(ts) + dp + Vector((0, 0, 0))
        v0 = Vector((V*0.98, s*rnd.uniform(26, 36), rnd.uniform(-14, -4)))
        pts = []; p = p0.copy(); v = v0.copy(); dt = 1/120
        life = rnd.uniform(4.2, 5.2)
        for i in range(int(life*120) + 1):
            if i % 4 == 0: pts.append(p.copy())
            a = GRAV - v*(0.0065*v.length)
            v += a*dt; p += v*dt
        FL.append({"t0": ts, "life": life, "pts": pts, "seed": rnd.random()})
def flare_state(f, t):
    age = t - f["t0"]
    if age < 0: return None
    n = len(f["pts"]); idx = min(int(age*30), n - 1)
    return age, idx

M_FLARE = bpy.data.materials.new("flare"); M_FLARE.use_nodes = True; nt = M_FLARE.node_tree
for n_ in list(nt.nodes): nt.nodes.remove(n_)
fo = nt.nodes.new("ShaderNodeOutputMaterial"); fe = nt.nodes.new("ShaderNodeEmission")
fe.inputs[0].default_value = (1.0, 0.86, 0.62, 1); fe.inputs[1].default_value = 300
nt.links.new(fe.outputs[0], fo.inputs[0])
def smoke_mat():
    m = bpy.data.materials.new("smoke"); m.use_nodes = True; nt = m.node_tree
    for n_ in list(nt.nodes): nt.nodes.remove(n_)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    pb = nt.nodes.new("ShaderNodeBsdfPrincipled"); pb.inputs["Base Color"].default_value = (0.62, 0.60, 0.58, 1); pb.inputs["Roughness"].default_value = 1.0
    pb.inputs["Emission Color"].default_value = (1.0, 0.75, 0.45, 1)
    at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "glow"; at.attribute_type = 'GEOMETRY'
    gm = nt.nodes.new("ShaderNodeMath"); gm.operation = 'MULTIPLY'; gm.inputs[1].default_value = 10.0
    nt.links.new(at.outputs["Fac"], gm.inputs[0]); nt.links.new(gm.outputs[0], pb.inputs["Emission Strength"])
    al = nt.nodes.new("ShaderNodeAttribute"); al.attribute_name = "alpha"; al.attribute_type = 'GEOMETRY'
    # soft edges: facing ratio
    lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.5
    inv = nt.nodes.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    nt.links.new(lw.outputs["Facing"], inv.inputs[1])
    pw = nt.nodes.new("ShaderNodeMath"); pw.operation = 'POWER'; pw.inputs[1].default_value = 1.6; nt.links.new(inv.outputs[0], pw.inputs[0])
    tc = nt.nodes.new("ShaderNodeTexCoord"); nzs = nt.nodes.new("ShaderNodeTexNoise"); nzs.inputs["Scale"].default_value = 0.25; nzs.inputs["Detail"].default_value = 6
    nt.links.new(tc.outputs["Object"], nzs.inputs["Vector"])
    nm = nt.nodes.new("ShaderNodeMapRange"); nm.inputs[1].default_value = 0.3; nm.inputs[2].default_value = 0.7; nm.inputs[3].default_value = 0.35; nm.inputs[4].default_value = 1.0
    nt.links.new(nzs.outputs["Fac"], nm.inputs[0])
    m0 = nt.nodes.new("ShaderNodeMath"); m0.operation = 'MULTIPLY'; nt.links.new(pw.outputs[0], m0.inputs[0]); nt.links.new(nm.outputs[0], m0.inputs[1])
    ml = nt.nodes.new("ShaderNodeMath"); ml.operation = 'MULTIPLY'; nt.links.new(al.outputs["Fac"], ml.inputs[0]); nt.links.new(m0.outputs[0], ml.inputs[1])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(ml.outputs[0], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(pb.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs[0])
    return m
M_SMOKE = smoke_mat()
DYN = []
def build_flares(t):
    global DYN
    for o in DYN:
        me = o.data if o.type == 'MESH' else None
        ld = o.data if o.type == 'LIGHT' else None
        bpy.data.objects.remove(o, do_unlink=True)
        if me: bpy.data.meshes.remove(me)
        if ld: bpy.data.lights.remove(ld)
    DYN = []
    bm = bmesh.new(); lg = bm.verts.layers.float.new("glow"); la = bm.verts.layers.float.new("alpha")
    heads = []
    for f in FL:
        st = flare_state(f, t)
        if st is None: continue
        age, idx = st
        if age > 14: continue
        burning = age < f["life"]
        hi = min(idx, int(f["life"]*30))
        pts = f["pts"][:hi + 1]
        if burning: heads.append((pts[-1], age, f))
        if len(pts) < 2: continue
        NS = 10; prev = None
        for j, p in enumerate(pts):
            pa = age - j/30.0                                    # how long ago this bit of smoke was laid down
            pa = max(0.0, pa)
            r = 0.25 + 0.75*math.sqrt(pa) + 0.12*pa
            tt = (pts[min(j+1, len(pts)-1)] - pts[max(j-1, 0)])
            if tt.length < 1e-6: tt = Vector((1, 0, 0))
            tt.normalize()
            a_ = tt.cross(Vector((0, 0, 1))).normalized(); b_ = tt.cross(a_)
            # drift + puffiness
            off = Vector((0, 0, 0.4*pa)) + 0.25*r*Vector((noise.noise(Vector((j*0.3, f["seed"]*50, 0))), noise.noise(Vector((j*0.3, f["seed"]*50, 5))), 0))
            ring = []
            for i in range(NS):
                aa = 2*math.pi*i/NS
                rr = r*(1 + 0.18*noise.noise(Vector((j*0.4, i*0.9, f["seed"]*30))))
                v = bm.verts.new(p + off + rr*(math.cos(aa)*a_ + math.sin(aa)*b_))
                d_head = (len(pts) - 1 - j)/30.0
                v[lg] = (math.exp(-d_head*2.2) if burning else 0.0)
                v[la] = clamp(0.62*math.exp(-pa/7.0)*clamp(j/1.5))
                ring.append(v)
            if prev:
                for i in range(NS):
                    bm.faces.new([prev[i], prev[(i+1) % NS], ring[(i+1) % NS], ring[i]])
            prev = ring
    if len(bm.verts):
        o = mesh_obj("smoke", bm, M_SMOKE); DYN.append(o)
    else:
        bm.free()
    for k, (p, age, f) in enumerate(heads):
        fl = 1.0 + 0.25*math.sin(age*53 + f["seed"]*10)
        s = 0.45*fl*(1 - 0.3*clamp((age - f["life"] + 0.6)/0.6))
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=s, location=p)
        o = bpy.context.object; o.data.materials.append(M_FLARE); o.visible_shadow = False; DYN.append(o)
        ld = bpy.data.lights.new(f"fl{k}", 'POINT'); ld.energy = float(os.environ.get('FLE','1.2e4'))*fl; ld.color = (1.0, 0.8, 0.55); ld.shadow_soft_size = 0.5
        lo = bpy.data.objects.new(f"fl{k}", ld); coll.objects.link(lo); lo.location = p; DYN.append(lo)

# ------------------------------------------------------------------ desert
def sand():
    m = bpy.data.materials.new("sand"); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.9
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.004; nz.inputs["Detail"].default_value = 8
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    cr = nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (0.30, 0.17, 0.08, 1); cr.color_ramp.elements[1].color = (0.52, 0.33, 0.17, 1)
    nt.links.new(nz.outputs["Fac"], cr.inputs[0]); nt.links.new(cr.outputs[0], b.inputs["Base Color"])
    wv = nt.nodes.new("ShaderNodeTexWave"); wv.inputs["Scale"].default_value = 0.6; wv.inputs["Distortion"].default_value = 6
    nt.links.new(tc.outputs["Object"], wv.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.12
    nt.links.new(wv.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs[0], b.inputs["Normal"])
    return add_haze(m)
def dune(x, y):
    h = 0.0
    h += 16*max(0.0, noise.noise(Vector((x/420, y/260, 0.5))))**1.3
    h += 6*noise.fractal(Vector((x/140, y/120, 2.1)), 0.6, 2.0, 3)
    h += 25*clamp((abs(y) - 1500)/2500)*(1 + noise.noise(Vector((x/900, 3.3, 0))))
    return h
NX, NY = 260, 200
bm = bmesh.new(); vs = []
for j in range(NY + 1):
    v_ = j/NY; y = math.copysign((abs(2*v_ - 1)**1.6)*6000, 2*v_ - 1); row = []
    for i in range(NX + 1):
        x = lerp(-3000, 6000, i/NX); row.append(bm.verts.new((x, y, dune(x, y))))
    vs.append(row)
for j in range(NY):
    for i in range(NX):
        bm.faces.new([vs[j][i], vs[j][i+1], vs[j+1][i+1], vs[j+1][i]])
mesh_obj("desert", bm, sand())
bpy.ops.mesh.primitive_plane_add(size=400000, location=(0, 0, -3)); bpy.context.object.data.materials.append(sand())

# ------------------------------------------------------------------ sky
wo = bpy.data.worlds.new("w"); sc.world = wo; wo.use_nodes = True
bg = wo.node_tree.nodes["Background"]
sky = wo.node_tree.nodes.new("ShaderNodeTexSky"); sky.sky_type = 'MULTIPLE_SCATTERING'
wo.node_tree.links.new(sky.outputs[0], bg.inputs[0])
sky.altitude = 0; sky.aerosol_density = 2.2; sky.sun_intensity = 0.5
sun_d = bpy.data.lights.new("sun", 'SUN'); sun_d.angle = math.radians(0.6)
sun = bpy.data.objects.new("sun", sun_d); coll.objects.link(sun)
def set_sun(el, rot, energy, color, bgs):
    sky.sun_elevation = math.radians(el); sky.sun_rotation = math.radians(rot)
    sun.rotation_euler = Euler((math.radians(90 - el), 0, math.radians(rot + 90)))
    sun_d.energy = energy; sun_d.color = color; bg.inputs[1].default_value = bgs
SUNROT = float(os.environ.get("SUNROT", "330"))
set_sun(float(os.environ.get("SUNEL", "1.5")), SUNROT, 2.2, (1.0, 0.48, 0.24), float(os.environ.get("BGS", "0.10")))

# ------------------------------------------------------------------ camera
cam_d = bpy.data.cameras.new("cam"); cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 36; cam_d.clip_end = 1000000; cam_d.clip_start = 0.1
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
        cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = fstop; cam_d.dof.focus_distance = (Vector(tgt) - Vector(loc)).length
    else:
        cam_d.dof.use_dof = False
def place_plane(t):
    PLANE.location = plane_pos(t); PLANE.rotation_euler = plane_rot(t)
def pose(t):
    P = plane_pos(t)
    if SHOT == "A":
        k = ease(t/10.0)
        cam_d.lens = lerp(45, 38, k)
        loc = P + Vector((lerp(-10, -40, k), lerp(-85, -95, k), lerp(-10, -14, k)))
        aim(loc, P + Vector((lerp(0, -16, k), 0, lerp(0, -8, k))), t, math.radians(0.10))
    elif SHOT == "B":
        u = (t - 10.0)/8.6; k = ease(u)
        cam_d.lens = lerp(40, 46, k)
        loc = P + Vector((lerp(-110, -125, k), lerp(-140, -125, k), lerp(38, 30, k)))
        aim(loc, P + Vector((lerp(-28, -40, k), 0, -12)), t, math.radians(0.10))
    elif SHOT == "C":
        cam_d.lens = 38
        loc = Vector((V*21.4 - 120, -330, dune(V*21.4 - 120, -330) + 2.0))
        aim(loc, P + Vector((-70, 0, -25)), t, math.radians(0.05))
    else:
        u = (t - 24.6)/4.8; k = ease(u)
        cam_d.lens = lerp(26, 30, k)
        loc = P + Vector((lerp(5, 2, k), lerp(-15.5, -15, k), lerp(-5.2, -5.6, k)))
        aim(loc, P + Vector((-12, -3, -2.2)), t, math.radians(0.12))

# ------------------------------------------------------------------ render
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.cycles.samples = int(os.environ.get("SPP", "10")); sc.cycles.use_denoising = True; sc.cycles.use_adaptive_sampling = True
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 1; sc.cycles.glossy_bounces = 1; sc.cycles.transparent_max_bounces = 24
sc.cycles.use_light_tree = True
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
def setup(t):
    global SHOT
    SHOT = shot_for(t); place_plane(t); pose(t); build_flares(t); bpy.context.view_layer.update()
END = SHOTS["D"][1]
mode = sys.argv[sys.argv.index("--")+1] if "--" in sys.argv else "frames"
if mode == "test":
    for t in [float(x) for x in os.environ.get("TT", "3").split(",")]:
        setup(t); sc.render.filepath = f"{OUT}/test_{t}.png"; bpy.ops.render.render(write_still=True)
elif mode == "meta":
    meta = {}
    for i in range(0, int(END*FPS)):
        t = i/FPS; SHOT = shot_for(t); place_plane(t); pose(t); bpy.context.view_layer.update()
        mw = PLANE.matrix_world
        meta[i] = {"plane": screen(mw @ Vector((0, 0, 0))), "disp": screen(mw @ DISP[2][0]), "tail": screen(mw @ Vector((-14, 0, 1)))}
        hs = []
        for f in FL:
            st = flare_state(f, t)
            if st and st[0] < f["life"]: hs.append(screen(f["pts"][st[1]]))
        meta[i]["flares"] = hs[:6]
    json.dump(meta, open(f"{OUT}/meta.json", "w"))
else:
    os.makedirs(f"{OUT}/frames", exist_ok=True)
    step = int(os.environ.get("STEP", "2"))
    i0 = int(os.environ.get("IFROM", "0")); i1 = int(os.environ.get("ITO", int(END*FPS)))
    for i in range(i0, i1, step):
        out = f"{OUT}/frames/f{i:04d}.png"
        if os.path.exists(out): continue
        setup(i/FPS); sc.render.filepath = out; bpy.ops.render.render(write_still=True)
