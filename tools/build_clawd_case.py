import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[1]
PARAMETERS = json.loads((ROOT / "models/clawd-v01-parameters.json").read_text())
REPORT_DIRECTORY = ROOT / "exports" / "clawd-v01" / "qa"
REFERENCE_BLEND = ROOT / "models/clawd-airpods4-anc-reference-study-v01.blend"


def new_collection(name):
    target = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(target)
    return target


def move_object(obj, target):
    for previous in tuple(obj.users_collection):
        previous.objects.unlink(obj)
    target.objects.link(obj)


def activate(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def material(name, color, roughness=0.5):
    shader = bpy.data.materials.new(name)
    shader.use_nodes = True
    rgba = tuple(((int(color[index:index + 2], 16) / 255 + 0.055) / 1.055) ** 2.4 for index in (0, 2, 4)) + (1,)
    shader.diffuse_color = rgba
    principled = shader.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = rgba
    principled.inputs["Roughness"].default_value = roughness
    return shader


def mesh_object(name, vertices, faces, target):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    target.objects.link(obj)
    return obj


def world_points(obj):
    return [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]


def bounds(obj):
    points = world_points(obj)
    minimum = [min(point[axis] for point in points) for axis in range(3)]
    maximum = [max(point[axis] for point in points) for axis in range(3)]
    return {"min": minimum, "max": maximum, "dimensions": [maximum[axis] - minimum[axis] for axis in range(3)]}


def clean_mesh(obj):
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    bmesh.ops.remove_doubles(mesh, verts=list(mesh.verts), dist=0.00001)
    bmesh.ops.dissolve_degenerate(mesh, edges=list(mesh.edges), dist=0.000001)
    bmesh.ops.recalc_face_normals(mesh, faces=list(mesh.faces))
    mesh.to_mesh(obj.data)
    mesh.free()
    obj.data.update()


def finalize_print_mesh(obj):
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    for iteration in range(2):
        bmesh.ops.triangulate(mesh, faces=list(mesh.faces), quad_method="BEAUTY", ngon_method="BEAUTY")
        bmesh.ops.remove_doubles(mesh, verts=list(mesh.verts), dist=0.0001)
        bmesh.ops.dissolve_degenerate(mesh, edges=list(mesh.edges), dist=0.0001)
    bmesh.ops.triangulate(mesh, faces=list(mesh.faces), quad_method="BEAUTY", ngon_method="BEAUTY")
    bmesh.ops.recalc_face_normals(mesh, faces=list(mesh.faces))
    mesh.to_mesh(obj.data)
    mesh.free()
    obj.data.update()


def convex_object(name, points, target):
    mesh = bmesh.new()
    for point in points:
        mesh.verts.new(point)
    bmesh.ops.remove_doubles(mesh, verts=list(mesh.verts), dist=0.00002)
    hull = bmesh.ops.convex_hull(mesh, input=list(mesh.verts), use_existing_faces=False)
    unused = list(set(hull.get("geom_interior", []) + hull.get("geom_unused", [])))
    if unused:
        bmesh.ops.delete(mesh, geom=unused, context="VERTS")
    bmesh.ops.recalc_face_normals(mesh, faces=list(mesh.faces))
    data = bpy.data.meshes.new(name)
    mesh.to_mesh(data)
    mesh.free()
    obj = bpy.data.objects.new(name, data)
    target.objects.link(obj)
    return obj


def offset_points(obj, distance):
    obj.data.update()
    return [vertex.co + vertex.normal * distance for vertex in obj.data.vertices]


def duplicate(obj, name, target):
    copied = obj.copy()
    copied.data = obj.data.copy()
    copied.name = name
    target.objects.link(copied)
    return copied


def bevel(obj, width, segments=4):
    activate(obj)
    modifier = obj.modifiers.new("Manufacturing edge radius", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def box(name, minimum, maximum, target, radius=0):
    vertices = [(horizontal, depth, height) for height in (minimum[2], maximum[2]) for depth in (minimum[1], maximum[1]) for horizontal in (minimum[0], maximum[0])]
    faces = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    obj = mesh_object(name, vertices, faces, target)
    if radius:
        bevel(obj, radius)
    return obj


def boolean(obj, cutter, operation="DIFFERENCE"):
    activate(obj)
    modifier = obj.modifiers.new(f"{operation}: {cutter.name}", "BOOLEAN")
    modifier.operation = operation
    modifier.solver = "EXACT"
    modifier.object = cutter
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    if not obj.data.polygons:
        raise ValueError(f"Boolean emptied {obj.name}: {cutter.name}")


def clawd_outline(source):
    mesh = bmesh.new()
    mesh.from_mesh(source.data)
    floor_faces = {face for face in mesh.faces if all(abs(vertex.co.z) < 0.00001 for vertex in face.verts)}
    boundary = [edge for edge in mesh.edges if sum(face in floor_faces for face in edge.link_faces) == 1]
    adjacency = {}
    for edge in boundary:
        for vertex in edge.verts:
            adjacency.setdefault(vertex, []).append(edge.other_vert(vertex))
    start = min(adjacency, key=lambda vertex: (vertex.co.x, vertex.co.y))
    outline = []
    previous = None
    current = start
    while True:
        outline.append(tuple(current.co))
        following = next(vertex for vertex in adjacency[current] if vertex != previous)
        previous, current = current, following
        if current == start:
            break
        if len(outline) > len(boundary):
            raise ValueError("Unable to traverse the Clawd silhouette")
    mesh.free()
    return outline


def character_solid(source, target):
    profile = []
    for horizontal, vertical, depth in clawd_outline(source):
        mapped_x = horizontal * PARAMETERS["character_body_width"] / 54
        mapped_z = (vertical + 13) * (PARAMETERS["character_body_height"] / 39 if vertical >= -13 else PARAMETERS["leg_length"] / 13)
        profile.append((mapped_x, mapped_z))
    vertices = [(horizontal, depth, height) for depth in (PARAMETERS["front_y"], PARAMETERS["back_y"]) for horizontal, height in profile]
    count = len(profile)
    faces = [tuple(range(count - 1, -1, -1)), tuple(range(count, count * 2))]
    faces.extend((index, (index + 1) % count, (index + 1) % count + count, index + count) for index in range(count))
    obj = mesh_object("MASTER | supplied Clawd silhouette, adapted proportions", vertices, faces, target)
    clean_mesh(obj)
    bevel(obj, PARAMETERS["edge_radius"])
    return obj


def make_device_envelopes(target):
    lid_parent = bpy.data.objects["nJoEOlgGwcdXBHJ"]
    lid_parent.location = (0, 0, 0)
    lid_parent.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()
    raw_body = world_points(bpy.data.objects["fWIbryXWNsOdjxC"])
    raw_lid = world_points(bpy.data.objects["bTVaRraRjrgTKif"])
    raw_combined = raw_body + raw_lid
    minima = Vector(tuple(min(point[axis] for point in raw_combined) for axis in range(3)))
    maxima = Vector(tuple(max(point[axis] for point in raw_combined) for axis in range(3)))
    extents = maxima - minima
    scale = Vector((PARAMETERS["apple_case"]["width"] / extents.x, PARAMETERS["apple_case"]["depth"] / extents.y, PARAMETERS["apple_case"]["height"] / extents.z))
    def calibrate(point):
        return Vector(((point.x - (maxima.x + minima.x) / 2) * scale.x, (point.y - (maxima.y + minima.y) / 2) * scale.y, (point.z - minima.z) * scale.z + PARAMETERS["case_bottom_z"]))
    body = convex_object("REFERENCE | calibrated body envelope, not metrology", [calibrate(point) for point in raw_body], target)
    lid = convex_object("REFERENCE | calibrated lid envelope, not metrology", [calibrate(point) for point in raw_lid], target)
    body_top = bounds(body)["max"][2]
    lid_bottom = bounds(lid)["min"][2]
    seam = (body_top + lid_bottom) / 2
    hinge = calibrate(Vector((0, 9.593735464768328, 10.952773722273937)))
    body["source_object"] = "fWIbryXWNsOdjxC"
    lid["source_object"] = "bTVaRraRjrgTKif"
    for obj in (body, lid):
        obj["warning"] = "Convex visual surrogate, not a manufacturer CAD model or physical measurement"
    metadata = {"raw_closed_dimensions_mm": list(extents), "axis_calibration_factors": list(scale), "body_envelope_mm": bounds(body), "lid_envelope_mm": bounds(lid), "nominal_cover_seam_z_mm": seam, "visual_model_hinge_pivot_mm": list(hinge), "hinge_source_angle_degrees": 115, "shape_accuracy": "UNVERIFIED; external manufacturer dimensions do not validate local contours or hinge kinematics"}
    return body, lid, seam, hinge, metadata


def insertion_cavity(reference, name, direction, target):
    expanded = offset_points(reference, PARAMETERS["nominal_normal_clearance"])
    swept = expanded + [point + Vector((0, 0, direction * 80)) for point in expanded]
    cutter = convex_object(name, swept, target)
    cutter["design_intent"] = "Axial insertion envelope removes nominal rigid-shell undercuts"
    return cutter


def common_access_cutters(target, seam):
    front = PARAMETERS["front_access"]
    service = PARAMETERS["bottom_service_opening"]
    hinge = PARAMETERS["hinge_relief"]
    front_cut = box("CUT | direct LED and pairing access", (-front["width"] / 2, -23, front["lower_z"]), (front["width"] / 2, -7, seam + 4), target, front["corner_radius"])
    bottom_cut = box("CUT | USB-C and ANC speaker service opening", (-service["width"] / 2, -service["depth"] / 2, -15), (service["width"] / 2, service["depth"] / 2, service["upper_z"]), target, service["corner_radius"])
    body_hinge = box("CUT | body rear hinge clearance", (-45, hinge["front_y"], hinge["body_lower_z"]), (45, 25, 60), target, 0.5)
    lid_hinge = box("CUT | lid rear hinge clearance", (-45, hinge["front_y"], 20), (45, 25, hinge["lid_upper_z"]), target, 0.5)
    return front_cut, bottom_cut, body_hinge, lid_hinge


def engrave_brand(lid, target):
    specification = PARAMETERS["back_text"]
    font = bpy.data.curves.new("Back branding | editable text", "FONT")
    font.body = specification["content"]
    font.align_x = "CENTER"
    font.align_y = "CENTER"
    font.font = bpy.data.fonts.load("/System/Library/Fonts/Supplemental/Arial Bold.ttf")
    font.extrude = 0.25
    font.resolution_u = 10
    editable = bpy.data.objects.new("BRAND | andreabalbo.com editable master", font)
    target.objects.link(editable)
    editable.rotation_euler = (math.pi / 2, 0, math.pi)
    bpy.context.view_layer.update()
    scaling = specification["height"] / editable.dimensions.z
    editable.scale = (scaling, scaling, 1)
    editable.location = (0, PARAMETERS["back_y"] - specification["engraving_depth"] + 0.25, specification["center_z"])
    cutter = duplicate(editable, "CUT | back brand engraving", target)
    activate(cutter)
    bpy.ops.object.convert(target="MESH")
    cutter = bpy.context.object
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    boolean(lid, cutter)
    return editable, cutter


def make_pair(master, prefix, target, cutters, cavities, seam, tools):
    body = duplicate(master, f"{prefix} | body", target)
    lid = duplicate(master, f"{prefix} | lid", target)
    gap = PARAMETERS["cover_seam_gap"]
    upper = box(f"CUT | {prefix} remove upper", (-55, -35, seam - gap / 2), (55, 35, 80), tools)
    lower = box(f"CUT | {prefix} remove lower", (-55, -35, -30), (55, 35, seam + gap / 2), tools)
    boolean(body, upper)
    boolean(lid, lower)
    boolean(body, cavities[0])
    boolean(lid, cavities[1])
    boolean(body, cutters[0])
    boolean(body, cutters[1])
    boolean(body, cutters[2])
    boolean(lid, cutters[3])
    return body, lid


def add_preview_details(body, lid, target, tools, paint):
    specification = PARAMETERS["eyes"]
    for center in specification["centers_x"]:
        eye = box("CUT | square recessed eye", (center - specification["width"] / 2, PARAMETERS["front_y"] - 1.0, specification["center_z"] - specification["height"] / 2), (center + specification["width"] / 2, PARAMETERS["front_y"] + specification["recess_depth"], specification["center_z"] + specification["height"] / 2), tools, 0.16)
        boolean(body, eye)
        inset = box("PREVIEW ONLY | black paint inside eye", (center - specification["width"] / 2 + 0.2, PARAMETERS["front_y"] + specification["recess_depth"] - 0.008, specification["center_z"] - specification["height"] / 2 + 0.2), (center + specification["width"] / 2 - 0.2, PARAMETERS["front_y"] + specification["recess_depth"] + 0.005, specification["center_z"] + specification["height"] / 2 - 0.2), target, 0.04)
        inset.data.materials.append(paint)
        inset["export"] = False
        inset["note"] = "Render-only paint indication, not a separate printable insert"
    return engrave_brand(lid, tools)


def main():
    if Path(bpy.data.filepath).resolve() != REFERENCE_BLEND.resolve():
        raise RuntimeError("Open the project reference-study file in a separate Blender process before building")
    REPORT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.name = "Clawd AirPods 4 ANC | FIT PROTOTYPE v01"
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 0.001
    scene.unit_settings.length_unit = "MILLIMETERS"
    original_collections = list(scene.collection.children)
    solids = new_collection("01 | CLAWD PRINT PARTS | v01 UNVALIDATED")
    reference = new_collection("02 | CALIBRATED DEVICE SURROGATES | display only")
    tools = new_collection("03 | PARAMETRIC MASTERS AND CUTTERS | no export")
    preview = new_collection("04 | FINISH PREVIEW | not extra print parts")
    fit = new_collection("05 | LOW COST FIT CHECK PAIR | unvalidated")
    terracotta = material("Terracotta PA12 | color intent only", "C87558", 0.48)
    ivory = material("White device surrogate", "F4F4F0", 0.24)
    paint = material("Black eye paint | optional finish", "171B1F", 0.5)
    fit_material = material("Undyed PA12 fit check", "C7D5D2", 0.65)
    body_reference, lid_reference, seam, hinge, metadata = make_device_envelopes(reference)
    for target in original_collections:
        target.hide_render = True
        target.hide_viewport = True
    for obj in (body_reference, lid_reference):
        obj.data.materials.append(ivory)
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
    body_cavity = insertion_cavity(body_reference, "CUT | body insertion clearance", 1, tools)
    lid_cavity = insertion_cavity(lid_reference, "CUT | lid insertion clearance", -1, tools)
    master = character_solid(bpy.data.objects["Clawd supplied STL | raw units"], tools)
    cutters = common_access_cutters(tools, seam)
    body, lid = make_pair(master, "CLAWD", solids, cutters, (body_cavity, lid_cavity), seam, tools)
    editable_text, text_cutter = add_preview_details(body, lid, preview, tools, paint)
    plain_master = box("MASTER | simplified fit check exterior", (-28, PARAMETERS["front_y"], 0), (28, PARAMETERS["back_y"], PARAMETERS["character_body_height"]), tools, PARAMETERS["edge_radius"])
    fit_body, fit_lid = make_pair(plain_master, "FIT CHECK", fit, cutters, (body_cavity, lid_cavity), seam, tools)
    for obj in (body, lid, fit_body, fit_lid):
        clean_mesh(obj)
        finalize_print_mesh(obj)
        obj.data.materials.clear()
        obj.data.materials.append(terracotta if obj in (body, lid) else fit_material)
        for polygon in obj.data.polygons:
            polygon.material_index = 0
        obj["release_status"] = PARAMETERS["release_status"]
        obj["units"] = "mm"
        obj["nominal_clearance_mm"] = PARAMETERS["nominal_normal_clearance"]
        obj["source_parameters"] = "models/clawd-v01-parameters.json"
        obj["retention"] = PARAMETERS["retention"]
    metadata["parameters"] = PARAMETERS
    metadata["master_dimensions_mm"] = bounds(master)
    metadata["brand_cutter_bounds_mm"] = bounds(text_cutter)
    metadata["print_part_bounds_mm"] = {obj.name: bounds(obj) for obj in (body, lid, fit_body, fit_lid)}
    (REPORT_DIRECTORY / "design-build.json").write_text(json.dumps(metadata, indent=2) + "\n")
    scene["release_status"] = PARAMETERS["release_status"]
    scene["hinge_pivot_mm"] = list(hinge)
    scene["physical_tests"] = "Not performed. No fit, retention, wireless charging, impact resistance or hinge guarantee."
    tools.hide_render = True
    tools.hide_viewport = True
    fit.hide_render = True
    fit.hide_viewport = True
    for area in bpy.context.screen.areas if bpy.context.screen else []:
        if area.type == "VIEW_3D":
            area.spaces.active.clip_end = 10000
            area.spaces.active.clip_start = 0.1
            area.spaces.active.region_3d.view_distance = 130
            area.spaces.active.region_3d.view_location = Vector((0, 0, 22))
    activate(body)
    bpy.ops.file.pack_all()
    output_path = ROOT / "models/clawd-airpods4-anc-v01.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(output_path))
    return {"blend_file": str(output_path), "parameters": str(ROOT / "models/clawd-v01-parameters.json"), "parts": metadata["print_part_bounds_mm"], "nominal_seam": seam, "hinge_pivot": list(hinge), "release_status": PARAMETERS["release_status"]}


if __name__ == "__main__":
    BUILD_RESULT = main()
