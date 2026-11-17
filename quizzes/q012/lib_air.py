def principled(name, color, rough=0.3, metal=0.0, coat=0.0, emit=None, estr=0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = estr
    return m

def livery(name, accent):
    """White fuselage, grey belly, accent cheatline + subtle panel noise."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.28; b.inputs["Coat Weight"].default_value = 0.6
    b.inputs["Coat Roughness"].default_value = 0.08
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[1].default_value = -2.0; mr.inputs[2].default_value = 2.0
    nt.links.new(sep.outputs["Z"], mr.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB"); cr = ramp.color_ramp; cr.interpolation = 'LINEAR'
    cr.elements[0].position = 0.0; cr.elements[0].color = (0.42, 0.44, 0.48, 1)
    cr.elements[1].position = 0.27; cr.elements[1].color = (0.45, 0.47, 0.5, 1)
    for pos, col in [(0.29, (0.82, 0.83, 0.85, 1)), (0.40, (0.86, 0.87, 0.89, 1)), (0.405, (*accent, 1)),
                     (0.455, (*accent, 1)), (0.46, (0.86, 0.87, 0.89, 1)), (1.0, (0.88, 0.89, 0.91, 1))]:
        e = cr.elements.new(pos); e.color = col
    nt.links.new(mr.outputs[0], ramp.inputs[0])
    # subtle grime/panel variation
    noise = nt.nodes.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 3.0
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
    mix.inputs["Factor"].default_value = 0.12
    nt.links.new(ramp.outputs[0], mix.inputs[6]); nt.links.new(noise.outputs["Color"], mix.inputs[7])
    nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    return m

def smooth(ob):
    for p in ob.data.polygons: p.use_smooth = True

def link(ob, parent):
    ob.parent = parent; return ob

# ---------------- aircraft ----------------
def make_airliner(name, accent):
    root = bpy.data.objects.new(name, None); sc.collection.objects.link(root)
    paint = livery(name+"_paint", accent)
    white = principled(name+"_white", (0.86, 0.87, 0.89), 0.3, coat=0.5)
    wingm = principled(name+"_wing", (0.62, 0.64, 0.67), 0.4, 0.2)
    metal = principled(name+"_metal", (0.7, 0.71, 0.73), 0.25, 0.9)
    dark = principled(name+"_dark", (0.02, 0.02, 0.025), 0.2)
    glass = principled(name+"_glass", (0.01, 0.012, 0.02), 0.03, coat=1.0)
    tailm = principled(name+"_tail", accent, 0.3, coat=0.5)

    # fuselage: lofted rings along X (nose at +X)
    prof = [(-30.0, 0.18, 1.4), (-28.2, 0.75, 1.25), (-25, 1.45, 1.05), (-21, 2.1, 0.7), (-16, 2.5, 0.3), (-11, 2.6, 0.0),
            (22, 2.6, 0.0), (25, 2.52, -0.06), (27.5, 2.3, -0.15), (29.3, 1.95, -0.26), (30.7, 1.5, -0.38),
            (31.7, 1.05, -0.48), (32.4, 0.55, -0.56), (32.8, 0.06, -0.62)]
    bm = bmesh.new(); seg = 40; rings = []
    for x, r, zc in prof:
        ring = []
        for i in range(seg):
            a = 2*math.pi*i/seg
            ring.append(bm.verts.new((x, r*math.cos(a), zc + r*1.04*math.sin(a))))
        rings.append(ring)
    for j in range(len(rings)-1):
        for i in range(seg):
            bm.faces.new([rings[j][i], rings[j][(i+1) % seg], rings[j+1][(i+1) % seg], rings[j+1][i]])
    bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    me = bpy.data.meshes.new(name+"_fus"); bm.to_mesh(me); bm.free()
    fus = bpy.data.objects.new(name+"_fus", me); sc.collection.objects.link(fus)
    fus.data.materials.append(paint); smooth(fus)
    fus.modifiers.new("ws", 'WEIGHTED_NORMAL'); link(fus, root)

    def add(ob, m):
        sc.collection.objects.link(ob) if ob.name not in sc.collection.objects else None
        ob.data.materials.append(m); smooth(ob); return link(ob, root)

    # cockpit windows: thin dark band shaped by a scaled, flattened sphere intersecting nose
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1, location=(26.6, 0, 3.45))
    w = bpy.context.object; w.scale = (1.2, 1.25, 0.3); w.rotation_euler = (0, math.radians(18), 0)
    w.data.materials.append(glass); smooth(w); link(w, root)
    # cabin windows (both sides)
    for side in (-1, 1):
        for i in range(48):
            x = 25.0 - i*0.98
            if -1.5 < x < 0.6: continue   # over-wing exits gap
            bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=8, radius=0.17, location=(x, side*2.595, 0.6))
            o = bpy.context.object; o.scale = (0.85, 0.25, 1.25); o.data.materials.append(glass); link(o, root)
        # doors outline hint
        bpy.ops.mesh.primitive_cube_add(size=1, location=(24.0, side*2.59, 0.35))
        o = bpy.context.object; o.scale = (0.9, 0.02, 1.8); o.data.materials.append(principled(name+f"_door{side}", (0.7, 0.71, 0.74), 0.4)); link(o, root)

    def wing(pts, thick, m, nm):
        me = bpy.data.meshes.new(nm); me.from_pydata([Vector(p) for p in pts], [], [list(range(len(pts)))])
        ob = bpy.data.objects.new(nm, me); sc.collection.objects.link(ob)
        s = ob.modifiers.new("s", 'SOLIDIFY'); s.thickness = thick; s.offset = 0
        b = ob.modifiers.new("b", 'BEVEL'); b.width = thick*0.45; b.segments = 3
        ob.data.materials.append(m); smooth(ob); return link(ob, root)

    for side in (-1, 1):
        s = side
        # main wing with sweep + dihedral
        wing([(7.0, s*2.2, -1.4), (-5.5, s*2.2, -1.4), (-17.5, s*31.0, 1.0), (-14.9, s*31.0, 1.0)], 0.6, wingm, f"{name}_wing{s}")
        wing([(-14.9, s*31.0, 1.0), (-17.5, s*31.0, 1.0), (-19.0, s*31.4, 3.6), (-17.9, s*31.4, 3.6)], 0.22, tailm, f"{name}_wl{s}")
        # flap track fairings
        for k, y in enumerate((6, 11, 17, 23)):
            x0 = -5.5 - (y-2.2)/(31-2.2)*12.0
            bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.22, depth=2.2, location=(x0-0.6, s*y, -1.4 + (y-2.2)*(2.4/28.8) - 0.4), rotation=(0, math.pi/2, 0))
            o = bpy.context.object; o.scale = (1, 1, 1); o.data.materials.append(wingm); smooth(o); link(o, root)
        # engine: nacelle + intake lip + fan + exhaust cone + pylon
        for (ey, ez, ex) in ((s*9.5, -2.6, 2.4), (s*17.5, -1.7, -2.8)):
            bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=1.12, depth=4.6, location=(ex, ey, ez), rotation=(0, math.pi/2, 0))
            o = bpy.context.object; o.data.materials.append(white); smooth(o); link(o, root)
            bpy.ops.mesh.primitive_torus_add(major_radius=1.05, minor_radius=0.14, major_segments=40, minor_segments=12, location=(ex+2.3, ey, ez), rotation=(0, math.pi/2, 0))
            o = bpy.context.object; o.data.materials.append(metal); smooth(o); link(o, root)
            bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.98, depth=0.05, location=(ex+2.1, ey, ez), rotation=(0, math.pi/2, 0))
            o = bpy.context.object; o.data.materials.append(dark); link(o, root)
            bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.6, radius2=0.1, depth=1.6, location=(ex-3.0, ey, ez), rotation=(0, -math.pi/2, 0))
            o = bpy.context.object; o.data.materials.append(metal); smooth(o); link(o, root)
            bpy.ops.mesh.primitive_cube_add(size=1, location=(ex-0.4, ey, ez+1.15))
            o = bpy.context.object; o.scale = (3.4, 0.35, 0.9); o.data.materials.append(white); link(o, root)
        # horizontal stabiliser
        wing([(-22.5, s*1.0, 1.3), (-27.5, s*1.0, 1.3), (-31.5, s*10.5, 2.4), (-29.4, s*10.5, 2.4)], 0.32, wingm, f"{name}_hs{s}")
        # nav light + strobe
        col = (0.1, 1, 0.25) if s == 1 else (1, 0.08, 0.05)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.18, location=(-16.6, s*31.15, 1.1))
        o = bpy.context.object; o.data.materials.append(principled(f"{name}_nav{s}", col, emit=col, estr=40)); link(o, root)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.16, location=(-17.4, s*31.15, 1.1))
        o = bpy.context.object; o.name = f"{name}_strobe{s}"
        sm = principled(f"{name}_strobe{s}", (1, 1, 1), emit=(1, 1, 1), estr=0); o.data.materials.append(sm); link(o, root)

    # vertical fin (in XZ plane) + rudder line
    me = bpy.data.meshes.new(name+"_fin")
    me.from_pydata([Vector(p) for p in [(-18.5, 0, 1.8), (-27.5, 0, 1.8), (-31.5, 0, 13.5), (-28.2, 0, 13.5)]], [], [[0, 1, 2, 3]])
    fin = bpy.data.objects.new(name+"_fin", me); sc.collection.objects.link(fin)
    m_ = fin.modifiers.new("s", 'SOLIDIFY'); m_.thickness = 0.45; m_.offset = 0
    m_ = fin.modifiers.new("b", 'BEVEL'); m_.width = 0.18; m_.segments = 3
    fin.data.materials.append(tailm); smooth(fin); link(fin, root)
    # red beacon on top + belly
    for zb in (2.05, -2.05):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.18, location=(4.0, 0, zb*1.3))
        o = bpy.context.object; o.name = f"{name}_beacon{int(zb>0)}"
        o.data.materials.append(principled(f"{name}_beacon{int(zb>0)}", (1, 0.05, 0.02), emit=(1, 0.05, 0.02), estr=0)); link(o, root)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1, location=(17.5, 0, 1.6))
    hump = bpy.context.object; hump.scale = (12.5, 1.95, 2.35); hump.data.materials.append(paint); smooth(hump); link(hump, root)
    for side in (-1, 1):
        for i in range(10):
            bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=6, radius=0.15, location=(25.0 - i*1.0, side*1.72, 3.05))
            o = bpy.context.object; o.scale = (0.85, 0.3, 1.2); o.data.materials.append(glass); link(o, root)
    return root
