import os as _os; QDIR = _os.environ.get("QDIR", _os.path.dirname(_os.path.abspath(__file__)))
import bpy, bmesh, math, json, sys, os, random
from mathutils import Vector, Euler
from bpy_extras.object_utils import world_to_camera_view

FPS = 30
RES = (1080, 1920)
OUT = os.environ.get("OUT", QDIR)
SHOT = "A"
SHOTS = {"A": (0.0, 6.4), "B": (6.4, 16.2), "C": (16.2, 28.2)}
T_WATER = 7.0      # deluge opens
T_CORE = 17.4      # core engines ignite
T_LIFT = 21.0      # boosters ignite, liftoff
MZ = 10.0          # top of launch mount

def ease(x):
    x = max(0.0, min(1.0, x)); return x*x*(3-2*x)
def lerp(a, b, k): return a + (b-a)*k

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; coll = sc.collection
rnd = random.Random(11)

def principled(name, color, rough=0.5, metal=0.0, coat=0.0, emit=None, estr=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal; b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = estr
    return m
def noisy(name, col, rough, scale=0.3, amt=0.35, metal=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = 10
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs["Factor"].default_value = amt
    mix.inputs[6].default_value = (*col, 1); nt.links.new(nz.outputs["Fac"], mix.inputs[7])
    nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    return m
def box(name, size, loc, mat, parent=None, rot=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object; o.name = name; o.scale = size; o.data.materials.append(mat)
    if rot: o.rotation_euler = rot
    if parent: o.parent = parent
    return o
def cyl(r, d, loc, mat, parent=None, v=48, rot=None, smooth=True):
    bpy.ops.mesh.primitive_cylinder_add(vertices=v, radius=r, depth=d, location=loc)
    o = bpy.context.object; o.data.materials.append(mat)
    if rot: o.rotation_euler = rot
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    if parent: o.parent = parent
    return o
def cone(r1, r2, d, loc, mat, parent=None, v=48, open_=False):
    bpy.ops.mesh.primitive_cone_add(vertices=v, radius1=r1, radius2=r2, depth=d, location=loc, end_fill_type='NOTHING' if open_ else 'NGON')
    o = bpy.context.object; o.data.materials.append(mat)
    for p in o.data.polygons: p.use_smooth = True
    if parent: o.parent = parent
    return o

# ------------------------------------------------------------------ materials
def rocket_paint(name, base, band=None):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.45
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise")
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (3, 3, 0.15)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 2.0; nz.inputs["Detail"].default_value = 8
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs["Factor"].default_value = 0.18
    mix.inputs[6].default_value = (*base, 1); nt.links.new(nz.outputs["Fac"], mix.inputs[7])
    nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    return m
M_WHITE = rocket_paint("white", (0.82, 0.82, 0.8))
M_ORANGE = rocket_paint("foam", (0.40, 0.19, 0.075))
M_BLACK = principled("black", (0.025, 0.025, 0.028), 0.45)
M_NOZ = principled("nozzle", (0.16, 0.12, 0.10), 0.3, 1.0)
M_STEEL = noisy("steel", (0.22, 0.22, 0.23), 0.5, scale=0.5, amt=0.4, metal=0.6)
M_MOUNT = noisy("mount", (0.16, 0.165, 0.17), 0.6, scale=0.15, amt=0.45, metal=0.3)
M_CONC = noisy("concrete", (0.42, 0.40, 0.37), 0.85, scale=0.03, amt=0.4)
M_GRASS = noisy("grass", (0.075, 0.07, 0.035), 0.95, scale=0.006, amt=0.55)
M_RED = principled("red", (0.45, 0.06, 0.03), 0.5)
M_PIPE = noisy("pipe", (0.30, 0.31, 0.32), 0.45, scale=1.0, amt=0.3, metal=0.7)

# ------------------------------------------------------------------ rocket (z=0 at engine exit plane)
rocket = bpy.data.objects.new("rocket", None); coll.objects.link(rocket)
RC = 4.2
cyl(RC, 64, (0, 0, 2.5 + 32), M_ORANGE, rocket)                    # core stage (insulation foam)
cyl(RC + 0.02, 1.2, (0, 0, 2.5 + 0.6), M_BLACK, rocket)              # engine section ring
cyl(RC + 0.02, 1.0, (0, 0, 66.0), M_BLACK, rocket)
cone(RC, 2.6, 6, (0, 0, 69.5), M_WHITE, rocket)                      # interstage taper
cyl(2.6, 10, (0, 0, 77.5), M_WHITE, rocket)                          # upper stage
cone(2.6, 2.5, 3, (0, 0, 84.0), M_BLACK, rocket)                     # adapter
cone(2.5, 1.1, 4.5, (0, 0, 87.75), M_WHITE, rocket)                  # capsule fairing
cyl(0.35, 9, (0, 0, 94.5), M_WHITE, rocket, v=16)                    # escape tower
cone(0.9, 0.05, 2.0, (0, 0, 100.0), M_RED, rocket, v=16)
for k in range(4):                                                   # 4 core engines
    a = k*math.pi/2 + math.pi/4
    cone(1.15, 0.45, 3.2, (1.9*math.cos(a), 1.9*math.sin(a), 1.6), M_NOZ, rocket, v=32, open_=True)
# side boosters (white with black bands)
for s in (1, -1):
    y = s*(RC + 1.9 + 0.3)
    cyl(1.9, 54, (0, y, 3.4 + 27), M_WHITE, rocket)
    for zz in (12, 22, 32, 42): cyl(1.93, 0.6, (0, y, zz), M_BLACK, rocket)
    cone(1.9, 0.2, 5.5, (0, y, 3.4 + 54 + 2.75), M_WHITE, rocket)
    cyl(2.05, 3.0, (0, y, 3.4 + 1.5), M_BLACK, rocket)               # aft skirt
    cone(1.75, 0.9, 3.4, (0, y, 1.7), M_NOZ, rocket, v=32, open_=True)
    box(f"strut{s}", (0.6, 2.5, 0.6), (0, s*(RC + 0.9), 52), M_STEEL, rocket)
    box(f"struta{s}", (0.6, 2.5, 0.6), (0, s*(RC + 0.9), 8), M_STEEL, rocket)
rocket.location = (0, 0, MZ + 1.0)

# ------------------------------------------------------------------ flames
def flame_mat(name, c0, c1, strength):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission"); tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mix = nt.nodes.new("ShaderNodeMixShader")
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB"); cr = ramp.color_ramp
    cr.elements[0].position = 0.0; cr.elements[0].color = (*c0, 1); cr.elements[1].position = 0.9; cr.elements[1].color = (*c1, 1)
    nt.links.new(sep.outputs["Z"], ramp.inputs[0])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 5
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    st = nt.nodes.new("ShaderNodeMath"); st.operation = 'MULTIPLY'; st.inputs[1].default_value = strength
    nt.links.new(nz.outputs["Fac"], st.inputs[0])
    nt.links.new(ramp.outputs[0], em.inputs["Color"]); nt.links.new(st.outputs[0], em.inputs["Strength"])
    fac = nt.nodes.new("ShaderNodeMapRange"); fac.inputs[3].default_value = 0.1; fac.inputs[4].default_value = 0.95
    nt.links.new(sep.outputs["Z"], fac.inputs[0])
    nt.links.new(fac.outputs[0], mix.inputs[0]); nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    return m
M_FL_CORE = flame_mat("flcore", (1.0, 0.45, 0.15), (0.85, 0.85, 1.0), 25)
M_FL_SRB = flame_mat("flsrb", (1.0, 0.55, 0.2), (1.0, 0.97, 0.9), 60)
core_fl = []
for k in range(4):
    a = k*math.pi/2 + math.pi/4
    o = cone(1.6, 0.6, 22, (1.9*math.cos(a), 1.9*math.sin(a), -11), M_FL_CORE, rocket, v=24); core_fl.append(o)
srb_fl = []
for s in (1, -1):
    o = cone(4.0, 1.0, 34, (0, s*(RC + 2.2), -17), M_FL_SRB, rocket, v=24); srb_fl.append(o)
fl_d = bpy.data.lights.new("fl", 'POINT'); fl_d.color = (1.0, 0.62, 0.3); fl_d.shadow_soft_size = 6
fl = bpy.data.objects.new("fl", fl_d); coll.objects.link(fl)

# ------------------------------------------------------------------ launch mount, tower, pad
box("mount", (36, 30, MZ), (0, 0, MZ/2), M_MOUNT)
box("mount_top", (36.5, 30.5, 0.4), (0, 0, MZ + 0.2), M_STEEL)
box("hole", (14, 22, 0.5), (0, 0, MZ + 0.25), principled("hole", (0.003, 0.003, 0.003), 0.9))
for (x, y) in ((-6, -9), (-6, 9), (6, -9), (6, 9)):                  # hold-down posts under boosters
    box(f"post{x}{y}", (1.2, 1.2, 1.4), (x*0.2, y*0.7, MZ + 0.7), M_STEEL)
# tower: square truss next to the rocket (on +X side of the mount)
TX, TW, TH = 13.0, 9.0, 112.0
for (dx, dy) in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
    box(f"leg{dx}{dy}", (0.8, 0.8, TH), (TX + dx*TW/2, dy*TW/2, MZ + TH/2), M_STEEL)
for z in range(0, int(TH), 6):
    zz = MZ + z + 3
    for dy in (-1, 1):
        box(f"bx{z}{dy}", (TW, 0.45, 0.45), (TX, dy*TW/2, zz), M_STEEL)
        L = math.hypot(TW, 6)
        box(f"dx{z}{dy}", (L, 0.3, 0.3), (TX, dy*TW/2, zz + 3), M_STEEL, rot=(0, math.atan2(6, TW)*(1 if z % 12 else -1), 0))
    for dx in (-1, 1):
        box(f"by{z}{dx}", (0.45, TW, 0.45), (TX + dx*TW/2, 0, zz), M_STEEL)
        L = math.hypot(TW, 6)
        box(f"dy{z}{dx}", (0.3, L, 0.3), (TX + dx*TW/2, 0, zz + 3), M_STEEL, rot=(math.atan2(6, TW)*(1 if z % 12 else -1), 0, 0))
    if z % 18 == 0:
        box(f"floor{z}", (TW, TW, 0.25), (TX, 0, zz - 0.1), M_STEEL)
# access arm to the capsule (swings away before liftoff)
arm = bpy.data.objects.new("arm", None); coll.objects.link(arm); arm.location = (TX - TW/2, 0, MZ + 1 + 86)
box("armbox", (TX - TW/2 - 2.6, 2.4, 2.6), (-(TX - TW/2 - 2.6)/2, 0, 0), M_STEEL, arm)
box("tower_top", (TW + 1, TW + 1, 4), (TX, 0, MZ + TH + 2), M_STEEL)
cyl(0.25, 20, (TX, 0, MZ + TH + 14), M_STEEL, v=8)                   # lightning mast
# pad: concrete hardstand + flame trench + ground
bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=170, depth=1.0, location=(0, 0, -0.5))
bpy.context.object.data.materials.append(M_CONC); bpy.context.object.rotation_euler = (0, 0, math.pi/8)
box("trench", (16, 260, 2), (0, 0, -0.1), principled("trenchdark", (0.01, 0.01, 0.01), 0.9))
bpy.ops.mesh.primitive_plane_add(size=40000, location=(0, 0, -0.9)); bpy.context.object.data.materials.append(M_GRASS)
# water tower (spherical tank on legs) and the ocean far behind
WT = (-260, 230, 0)
bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=11, location=(WT[0], WT[1], 78))
bpy.context.object.data.materials.append(principled("wt", (0.75, 0.76, 0.76), 0.4, 0.4))
for k in range(8):
    a = k*math.pi/4
    cyl(0.7, 74, (WT[0] + 9*math.cos(a), WT[1] + 9*math.sin(a), 37), M_STEEL, v=8)
cyl(1.2, 78, (WT[0], WT[1], 39), M_STEEL, v=12)
# catenary lightning towers
for (x, y) in ((-150, -120), (150, -120), (0, 170)):
    cyl(1.6, 130, (x, y, 65), principled("lt", (0.6, 0.6, 0.6), 0.6), v=12)
# scrub / bushes on the ground
M_BUSH = noisy("bush", (0.05, 0.07, 0.03), 0.9, scale=0.2, amt=0.6)
for k in range(220):
    r = rnd.uniform(450, 1600); a = rnd.uniform(0, 2*math.pi)
    if math.hypot(r*math.cos(a) + 560, r*math.sin(a) + 960) < 500: continue
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=(r*math.cos(a), r*math.sin(a), 0))
    o = bpy.context.object; s = rnd.uniform(3, 8); o.scale = (s*rnd.uniform(1, 2.5), s, s*0.35); o.data.materials.append(M_BUSH)
wm = bpy.data.materials.new("ocean"); wm.use_nodes = True
bw = wm.node_tree.nodes["Principled BSDF"]; bw.inputs["Base Color"].default_value = (0.004, 0.015, 0.025, 1); bw.inputs["Roughness"].default_value = 0.08
bpy.ops.mesh.primitive_plane_add(size=60000, location=(32000, 0, -0.6)); bpy.context.object.data.materials.append(wm)

# ------------------------------------------------------------------ water deluge: nozzles + jets (curves that grow)
M_SPRAY = bpy.data.materials.new("spray"); M_SPRAY.use_nodes = True; nt = M_SPRAY.node_tree
bs = nt.nodes["Principled BSDF"]; bs.inputs["Base Color"].default_value = (0.9, 0.93, 0.95, 1); bs.inputs["Roughness"].default_value = 0.4
bs.inputs["Transmission Weight"].default_value = 0.0; bs.inputs["Roughness"].default_value = 0.65
tcs = nt.nodes.new("ShaderNodeTexCoord"); mps = nt.nodes.new("ShaderNodeMapping"); mps.inputs["Scale"].default_value = (4.0, 4.0, 1.5)
nt.links.new(tcs.outputs["Object"], mps.inputs["Vector"])
nzs = nt.nodes.new("ShaderNodeTexNoise"); nzs.inputs["Scale"].default_value = 2.2; nzs.inputs["Detail"].default_value = 8
nt.links.new(mps.outputs["Vector"], nzs.inputs["Vector"])
rps = nt.nodes.new("ShaderNodeMapRange"); rps.inputs[1].default_value = 0.38; rps.inputs[2].default_value = 0.68
rps.inputs[3].default_value = 0.35; rps.inputs[4].default_value = 1.0
nt.links.new(nzs.outputs["Fac"], rps.inputs[0])
trs = nt.nodes.new("ShaderNodeBsdfTransparent"); mxs = nt.nodes.new("ShaderNodeMixShader")
nt.links.new(rps.outputs[0], mxs.inputs[0])
nt.links.new(trs.outputs[0], mxs.inputs[1]); nt.links.new(bs.outputs[0], mxs.inputs[2])
nt.links.new(mxs.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
# volumetric spray core inside each jet
M_JV = bpy.data.materials.new("jetvol"); M_JV.use_nodes = True; nt = M_JV.node_tree
nt.nodes.remove(nt.nodes["Principled BSDF"])
pvj = nt.nodes.new("ShaderNodeVolumePrincipled"); pvj.inputs["Color"].default_value = (0.95, 0.97, 1.0, 1)
tcj = nt.nodes.new("ShaderNodeTexCoord"); nzj = nt.nodes.new("ShaderNodeTexNoise"); nzj.inputs["Scale"].default_value = 1.5; nzj.inputs["Detail"].default_value = 6
nt.links.new(tcj.outputs["Object"], nzj.inputs["Vector"])
mrj = nt.nodes.new("ShaderNodeMapRange"); mrj.inputs[1].default_value = 0.4; mrj.inputs[2].default_value = 0.7; mrj.inputs[3].default_value = 0.0; mrj.inputs[4].default_value = 1.2
nt.links.new(nzj.outputs["Fac"], mrj.inputs[0]); nt.links.new(mrj.outputs[0], pvj.inputs["Density"])
nt.links.new(pvj.outputs[0], nt.nodes["Material Output"].inputs["Volume"])
JETS = []
NOZ = [(-17, -13), (-17, 13), (17, -13), (17, 13), (-17, 0), (0, -14.5), (0, 14.5)]
def jet_curve(name, pts, depth, mat, caps=False):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    cu.bevel_depth = depth; cu.bevel_resolution = 3; cu.use_fill_caps = caps
    cu.bevel_factor_mapping_end = 'SPLINE'
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts): sp.points[i].co = (p.x, p.y, p.z, 1)
    ob = bpy.data.objects.new(name, cu); coll.objects.link(ob); ob.data.materials.append(mat)
    return ob
for (nx, ny) in NOZ:
    cyl(0.55, 2.5, (nx, ny, MZ + 1.25), M_PIPE, v=16)
    tgt = Vector((nx*0.18, ny*0.18, MZ + 0.4))
    d = (tgt - Vector((nx, ny, MZ + 2.6))); hd = Vector((d.x, d.y, 0)).normalized()
    barrel = cyl(0.5, 1.8, (nx + hd.x*0.6, ny + hd.y*0.6, MZ + 2.9), M_PIPE, v=16)
    barrel.rotation_euler = (Vector((hd.x, hd.y, 0.9)).normalized()).to_track_quat('Z', 'Y').to_euler()
    p0 = Vector((nx + hd.x*1.3, ny + hd.y*1.3, MZ + 3.4))
    horiz = (Vector((tgt.x, tgt.y, 0)) - Vector((p0.x, p0.y, 0))).length
    side = Vector((-hd.y, hd.x, 0))
    def path(jx, jy, apex, spread, n=28):
        pts = []
        for i in range(n):
            u = i/(n-1)
            p = p0 + hd*horiz*u + side*(jx*spread*u*u*1.5)
            p.z = lerp(p0.z, tgt.z, u) + apex*4*u*(1-u) + jy*0.8*spread*u*u
            pts.append(p)
        return pts
    for s in range(24):
        ob = jet_curve(f"jet{nx}{ny}{s}", path(rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(4.0, 5.8), 2.8),
                       rnd.uniform(0.3, 0.45) if s < 3 else rnd.uniform(0.05, 0.16), M_SPRAY)
        JETS.append((ob, rnd.uniform(0, 0.3)))

# ------------------------------------------------------------------ mist / steam volumes
def vol_mat(name, col, scale, EMK=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    pv = nt.nodes.new("ShaderNodeVolumePrincipled"); pv.inputs["Color"].default_value = (*col, 1); pv.inputs["Anisotropy"].default_value = 0.25
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = 5
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    gr = nt.nodes.new("ShaderNodeTexGradient"); gr.gradient_type = 'SPHERICAL'; nt.links.new(tc.outputs["Object"], gr.inputs["Vector"])
    mm = nt.nodes.new("ShaderNodeMath"); mm.operation = 'MULTIPLY'; nt.links.new(nz.outputs["Fac"], mm.inputs[0]); nt.links.new(gr.outputs["Fac"], mm.inputs[1])
    pw = nt.nodes.new("ShaderNodeMath"); pw.operation = 'POWER'; pw.inputs[1].default_value = 0.8; nt.links.new(mm.outputs[0], pw.inputs[0])
    dens = nt.nodes.new("ShaderNodeMath"); dens.operation = 'MULTIPLY'; dens.inputs[1].default_value = 0.0
    nt.links.new(pw.outputs[0], dens.inputs[0]); nt.links.new(dens.outputs[0], pv.inputs["Density"])
    em = nt.nodes.new("ShaderNodeMath"); em.operation = 'MULTIPLY'; em.inputs[1].default_value = EMK
    nt.links.new(pw.outputs[0], em.inputs[0]); nt.links.new(em.outputs[0], pv.inputs["Emission Strength"])
    pv.inputs["Emission Color"].default_value = (1.0, 0.86, 0.7, 1)
    nt.links.new(pv.outputs[0], nt.nodes["Material Output"].inputs["Volume"])
    return m, dens
M_MIST, D_MIST = vol_mat("mist", (0.95, 0.96, 0.98), 1.4)
def steam_mat():
    m = bpy.data.materials.new("steam"); m.use_nodes = True; nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep.inputs[0])
    dif = nt.nodes.new("ShaderNodeBsdfDiffuse"); dif.inputs["Color"].default_value = (0.92, 0.9, 0.88, 1)
    trl = nt.nodes.new("ShaderNodeBsdfTranslucent"); trl.inputs["Color"].default_value = (0.95, 0.85, 0.75, 1)
    m1 = nt.nodes.new("ShaderNodeMixShader"); m1.inputs[0].default_value = 0.35
    nt.links.new(dif.outputs[0], m1.inputs[1]); nt.links.new(trl.outputs[0], m1.inputs[2])
    # warm glow from the engines on the lower part
    hz = nt.nodes.new("ShaderNodeMapRange"); hz.inputs[1].default_value = -0.2; hz.inputs[2].default_value = -1.0
    nt.links.new(sep.outputs["Z"], hz.inputs[0])
    gl = nt.nodes.new("ShaderNodeMath"); gl.operation = 'MULTIPLY'; gl.inputs[1].default_value = 0.0
    nt.links.new(hz.outputs[0], gl.inputs[0])
    emi = nt.nodes.new("ShaderNodeEmission"); emi.inputs["Color"].default_value = (1.0, 0.5, 0.2, 1)
    nt.links.new(gl.outputs[0], emi.inputs["Strength"])
    add = nt.nodes.new("ShaderNodeAddShader"); nt.links.new(m1.outputs[0], add.inputs[0]); nt.links.new(emi.outputs[0], add.inputs[1])
    # soft edges
    lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.5
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 3.0; nz.inputs["Detail"].default_value = 4
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    ad = nt.nodes.new("ShaderNodeMath"); ad.operation = 'ADD'
    nt.links.new(lw.outputs["Facing"], ad.inputs[0]); nt.links.new(nz.outputs["Fac"], ad.inputs[1])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[1].default_value = 0.95; mr.inputs[2].default_value = 1.35
    nt.links.new(ad.outputs[0], mr.inputs[0])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    m2 = nt.nodes.new("ShaderNodeMixShader"); nt.links.new(mr.outputs[0], m2.inputs[0])
    nt.links.new(add.outputs[0], m2.inputs[1]); nt.links.new(tr.outputs[0], m2.inputs[2])
    nt.links.new(m2.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    return m, gl
M_STEAM, D_STEAM = steam_mat()
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1, location=(0, 0, MZ + 1.5))
mist = bpy.context.object; mist.scale = (20, 17, 4.5); mist.data.materials.append(M_MIST)
M_WSHEET = principled("wsheet", (0.03, 0.04, 0.05), 0.06)
M_WSHEET.node_tree.nodes["Principled BSDF"].inputs["Coat Weight"].default_value = 1.0
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, MZ + 0.42))
wsheet = bpy.context.object; wsheet.scale = (35.5, 29.5, 1); wsheet.data.materials.append(M_WSHEET)
PUFFS = []
for i in range(22):
    side = 1 if i % 2 == 0 else -1
    kind = "srb" if i >= 8 else "core"
    PUFFS.append(dict(side=side, kind=kind, f=rnd.uniform(0.7, 1.3), dz=rnd.uniform(-0.3, 0.6), dx=rnd.uniform(-1, 1), lag=rnd.uniform(0, 0.6), g=rnd.uniform(0.2, 1.0)))
for p in PUFFS:
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=5, radius=1, location=(0, 0, -50))
    o = bpy.context.object; o.data.materials.append(M_STEAM)
    for pp in o.data.polygons: pp.use_smooth = True
    tx = bpy.data.textures.new(f"cl{len(PUFFS)}", 'CLOUDS'); tx.noise_scale = 0.45; tx.noise_depth = 3
    dm = o.modifiers.new("d", 'DISPLACE'); dm.texture = tx; dm.strength = 0.45; dm.mid_level = 0.5; dm.texture_coords = 'LOCAL'
    tx2 = bpy.data.textures.new(f"cm{len(PUFFS)}", 'CLOUDS'); tx2.noise_scale = 0.15; tx2.noise_depth = 2
    dm2 = o.modifiers.new("d2", 'DISPLACE'); dm2.texture = tx2; dm2.strength = 0.08; dm2.texture_coords = 'LOCAL'
    o.rotation_euler = (rnd.uniform(0, 6), rnd.uniform(0, 6), rnd.uniform(0, 6))
    p["ob"] = o

# ------------------------------------------------------------------ world
wo = bpy.data.worlds.new("w"); sc.world = wo; wo.use_nodes = True
bg = wo.node_tree.nodes["Background"]
sky = wo.node_tree.nodes.new("ShaderNodeTexSky"); sky.sky_type = 'MULTIPLE_SCATTERING'
wo.node_tree.links.new(sky.outputs[0], bg.inputs[0])
sun_d = bpy.data.lights.new("sun", 'SUN'); sun_d.angle = math.radians(0.6)
sun = bpy.data.objects.new("sun", sun_d); coll.objects.link(sun)
def set_sun(el, rot, energy, color, bgs):
    sky.sun_elevation = math.radians(el); sky.sun_rotation = math.radians(rot)
    sky.altitude = 10; sky.aerosol_density = 1.6; sky.sun_intensity = 0.5
    sun.rotation_euler = Euler((math.radians(90 - el), 0, math.radians(rot + 90)))
    sun_d.energy = energy; sun_d.color = color; bg.inputs[1].default_value = bgs
set_sun(5, 50, 3.8, (1.0, 0.66, 0.42), 0.22)

# ------------------------------------------------------------------ camera
cam_d = bpy.data.cameras.new("cam"); cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 36; cam_d.clip_end = 100000; cam_d.clip_start = 0.1
cam = bpy.data.objects.new("cam", cam_d); coll.objects.link(cam); sc.camera = cam
SH = [(rnd.uniform(-1, 1), rnd.uniform(-1, 1)) for _ in range(400)]
def shake(t, amp, rate=2.5):
    i = int(t*rate); f = t*rate - i; a, b_ = SH[i % 400], SH[(i+1) % 400]; f = f*f*(3-2*f)
    return (a[0]+(b_[0]-a[0])*f)*amp, (a[1]+(b_[1]-a[1])*f)*amp
def aim(loc, tgt, t, amp):
    cam.location = loc
    e = (Vector(tgt)-Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sx, sy = shake(t, amp); e.x += sx; e.z += sy; cam.rotation_euler = e

def rocket_z(t):
    u = max(0.0, t - T_LIFT); return MZ + 1.0 + 0.5*3.5*u*u

def pose(t):
    # rocket + arm
    rocket.location = (0, 0, rocket_z(t))
    arm.rotation_euler = (0, 0, -math.radians(80)*ease((t - 5.0)/4.0))
    # water jets
    w = ease((t - T_WATER)/1.4)
    for ob, lag in JETS:
        k = ease((t - T_WATER - lag)/1.0)
        ob.hide_render = k <= 0.01
        ob.data.bevel_factor_end = max(0.02, k)
        ob.data.bevel_depth = ob.data.bevel_depth   # keep
    D_MIST.inputs[1].default_value = 0.25*ease((t - T_WATER - 0.8)/2.5)
    mist.hide_render = t < T_WATER + 0.8
    wsheet.hide_render = t < T_WATER + 1.0
    D_MIST.inputs[1].default_value = 0.5*ease((t - T_WATER - 0.8)/2.5)
    # engines
    kc = ease((t - T_CORE)/0.6)
    ks = ease((t - T_LIFT)/0.3)
    for o in core_fl:
        o.hide_render = kc <= 0.01
        f = 1 + 0.07*math.sin(t*53 + o.location.x) + 0.04*math.sin(t*31)
        o.scale = (kc*f, kc*f, kc*f)
    for o in srb_fl:
        o.hide_render = ks <= 0.01
        f = 1 + 0.06*math.sin(t*47 + o.location.y)
        o.scale = (ks*f, ks*f, ks*f)
    fl.location = (0, 0, rocket_z(t) - 8)
    fl_d.energy = 4e6*kc + 1.6e7*ks
    # steam clouds: billow out of the trench on both sides + around the mount
    any_ = False
    for i, p in enumerate(PUFFS):
        t0 = (T_CORE + 0.3 if p["kind"] == "core" else T_LIFT + 0.1) + p["lag"]
        u = t - t0
        ob = p["ob"]
        if u <= 0: ob.hide_render = True; continue
        any_ = True; ob.hide_render = False
        reach = (70 if p["kind"] == "core" else 190)*p["g"]*(1 - math.exp(-u/2.4))
        r = (10 + 16*p["f"]*(1 - math.exp(-u/2.0)))*(1.0 if p["kind"] == "core" else 1.9)
        ob.location = (p["dx"]*(8 + 0.25*reach), p["side"]*(20 + reach), r*0.55 + p["dz"]*r + 0.8*u)
        ob.scale = (r*1.2, r, r*0.8)
    D_STEAM.inputs[1].default_value = 3.0*ease((t - T_CORE)/0.5) + 6.0*ease((t - T_LIFT)/0.4)
    # camera
    if SHOT == "A":
        k = ease(t/6.4)
        cam_d.lens = lerp(120, 135, k)
        loc = (lerp(-560, -540, k), lerp(-960, -940, k), 8)
        tgt = (0, 0, lerp(48, 52, k))
        aim(loc, tgt, t, math.radians(0.06))
    elif SHOT == "B":
        k = ease((t - 6.4)/9.8)
        cam_d.lens = lerp(26, 29, k)
        loc = (lerp(-31, -29, k), lerp(-37, -35, k), lerp(MZ + 9.5, MZ + 10, k))
        tgt = (lerp(-1, 0, k), lerp(-2, -1, k), lerp(MZ + 5.0, MZ + 4.0, k))
        aim(loc, tgt, t, math.radians(0.12))
    else:
        k = ease((t - 16.2)/12.0)
        cam_d.lens = lerp(62, 55, k)
        loc = (-300, -420, 10)
        tz = lerp(38, 50, k) + max(0, rocket_z(t) - MZ - 1)*0.75
        aim(loc, (0, 0, tz), t, math.radians(0.08 + 0.25*ease((t - T_LIFT - 0.4)/0.8)*(1 - 0.5*ease((t - 25)/3))))

# ------------------------------------------------------------------ render
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.cycles.samples = int(os.environ.get("SPP", "10")); sc.cycles.use_denoising = True; sc.cycles.use_adaptive_sampling = True
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transparent_max_bounces = 6
sc.cycles.volume_bounces = 0; sc.cycles.volume_step_rate = 8.0; sc.cycles.volume_max_steps = 24
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
    return "C"
mode = sys.argv[sys.argv.index("--")+1] if "--" in sys.argv else "frames"
END = SHOTS["C"][1]
if mode == "test":
    for t in [float(x) for x in os.environ.get("TT", "3").split(",")]:
        SHOT = shot_for(t); pose(t); bpy.context.view_layer.update()
        sc.render.filepath = f"{OUT}/test_{t}.png"; bpy.ops.render.render(write_still=True)
elif mode == "meta":
    meta = {}
    for i in range(0, int(END*FPS)):
        t = i/FPS; SHOT = shot_for(t); pose(t); bpy.context.view_layer.update()
        meta[i] = {"noz": screen((-17 + 1.2, -13 + 1.0, MZ + 3.4)), "base": screen((0, 0, rocket_z(t))),
                   "top": screen((0, 0, rocket_z(t) + 100)), "alt": rocket_z(t) - MZ - 1}
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
