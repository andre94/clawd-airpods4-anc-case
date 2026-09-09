import hashlib
import json
import math
import runpy
from pathlib import Path

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "models/clawd-airpods4-anc-v02.blend"
DESTINATION = ROOT / "models/clawd-airpods4-anc-v03.blend"
OUTPUT = ROOT / "exports/clawd-v03"
HARDWARE_COLLECTION = "09 | KEYRING HARDWARE PREVIEW | NOT FOR PRINT"


def cylinder(name, center, axis, radial, radius, collection, builder, segments=128):
    vertical = Vector((0, 0, 1))
    vertices = [center + axis * offset + radius * (radial * math.cos(2 * math.pi * index / segments) + vertical * math.sin(2 * math.pi * index / segments)) for offset in (-20, 20) for index in range(segments)]
    faces = [(index, (index + 1) % segments, (index + 1) % segments + segments, index + segments) for index in range(segments)]
    faces.extend((tuple(reversed(range(segments))), tuple(range(segments, 2 * segments))))
    obj = builder["mesh_object"](name, vertices, faces, collection)
    builder["clean_mesh"](obj)
    obj["export"] = False
    obj.hide_render = True
    return obj


def rounded_bore(center, axis, radial, specification, collection, builder):
    radius = specification["bore_diameter"] / 2
    rounding = specification["entry_round_radius"]
    segments = specification["cylinder_segments"]
    half_length = specification["mouth_offset_from_sharp_corner"] / math.sqrt(2)
    vertical = Vector((0, 0, 1))

    def section(fraction, mirror):
        points = []
        for index in range(segments):
            angle = 2 * math.pi * index / segments
            cosine = math.cos(angle)
            circle_center = -half_length + cosine * (radius + rounding) + rounding * math.sqrt(1 + cosine * cosine)
            plane_angle = math.atan2(cosine, -1)
            if plane_angle > -math.pi / 2:
                plane_angle -= 2 * math.pi
            arc_angle = -math.pi / 2 + fraction * (plane_angle + math.pi / 2)
            station = mirror * (circle_center + rounding * math.cos(arc_angle))
            section_radius = radius + rounding + rounding * math.sin(arc_angle)
            points.append(center + station * axis + section_radius * (radial * cosine + vertical * math.sin(angle)))
        return points

    front_lip = section(1, 1)
    side_lip = section(1, -1)
    loops = [[point - axis * ((point - center).dot(axis) + 20) for point in front_lip]]
    loops.extend(section(index / specification["entry_round_segments"], 1) for index in range(specification["entry_round_segments"], -1, -1))
    loops.extend(section(index / specification["entry_round_segments"], -1) for index in range(specification["entry_round_segments"] + 1))
    loops.append([point + axis * (20 - (point - center).dot(axis)) for point in side_lip])
    vertices = [point for loop in loops for point in loop]
    faces = [(loop * segments + index, loop * segments + (index + 1) % segments, (loop + 1) * segments + (index + 1) % segments, (loop + 1) * segments + index) for loop in range(len(loops) - 1) for index in range(segments)]
    faces.extend((tuple(reversed(range(segments))), tuple(range(len(vertices) - segments, len(vertices)))))
    cutter = builder["mesh_object"]("CUT | v03 keyring bore with rounded entries", vertices, faces, collection)
    builder["clean_mesh"](cutter)
    cutter["export"] = False
    cutter.hide_render = True
    return cutter


def entry_openings(body, center, axis, outer_x, front_y, specification):
    radius = specification["bore_diameter"] / 2
    rounding = specification["entry_round_radius"]
    samples = {}
    for label, coordinate, plane in (("front", 1, front_y), ("right", 0, outer_x)):
        radii = []
        for vertex in body.data.vertices:
            point = vertex.co
            offset = point - center
            radial_distance = (offset - axis * offset.dot(axis)).length
            if abs(point[coordinate] - plane) < 0.00001 and radius - 0.01 < radial_distance < radius + 2 * rounding + 0.1:
                radii.append(radial_distance)
        if not radii:
            raise RuntimeError("No rounded mouth vertices found")
        expected = [radius + rounding * (1 - 1 / math.sqrt(2)), radius + rounding * (1 + 1 / math.sqrt(2))]
        samples[label] = {"vertices": len(radii), "radial_range_mm": [min(radii), max(radii)], "expected_radial_range_mm": expected, "matches_within_0_01_mm": abs(min(radii) - expected[0]) < 0.01 and abs(max(radii) - expected[1]) < 0.01}
    return {"nominal_meridian_round_radius_mm": rounding, "arc_segments": specification["entry_round_segments"], "mouths": samples, "scope": "Explicit tangent arcs in bore-axis meridian planes, not an overlap-clamped edge modifier or a certified constant-radius 3D fillet"}


def outside_anchor_difference(original, revised, validator):
    maxima = []
    for source, target in ((original, revised), (revised, original)):
        surface = validator["tree"](target)
        distances = []
        for vertex in source.data.vertices:
            point = source.matrix_world @ vertex.co
            if point.x >= 26.5 and point.y <= -2.5 and 22.8 <= point.z <= 28.8:
                continue
            location, normal, triangle_index, distance = surface.find_nearest(point)
            if location is None:
                raise RuntimeError("Missing comparison surface")
            distances.append(distance)
        maxima.append(max(distances, default=0))
    return {"bidirectional_vertex_to_surface_max_mm": maxima, "within_0_0001_mm": max(maxima) < 0.0001, "scope": "Outside x >= 26.5, y <= -2.5, z 22.8 to 28.8 mm; not a physical tolerance measurement"}


def bore_sections(body, center, axis, radial, validator):
    vertices, triangles = validator["triangle_data"](body)
    surface = BVHTree.FromPolygons(vertices, triangles, all_triangles=True, epsilon=0)
    vertical = Vector((0, 0, 1))
    diameters = []
    for station in (-2.5, 0, 2.5):
        for index in range(32):
            angle = math.pi * (index + 0.37) / 32
            direction = radial * math.cos(angle) + vertical * math.sin(angle)
            hits = [surface.ray_cast(center + station * axis, sign * direction, 15) for sign in (-1, 1)]
            if any(hit[0] is None for hit in hits):
                raise RuntimeError("Missing bore-section surface")
            diameters.append(sum(hit[3] for hit in hits))
    web_samples = []
    for height_offset in (-0.5, 0.025, 0.5):
        location, normal, triangle_index, distance = surface.ray_cast(center + height_offset * vertical, radial, 15)
        if location is None:
            raise RuntimeError("Missing inner corner-web surface")
        outer, normal, triangle_index, remaining = surface.ray_cast(location + 0.001 * radial, radial, 15)
        if outer is None:
            raise RuntimeError("Missing outer corner-web surface")
        web_samples.append({"z_mm": center.z + height_offset, "wall_mm": remaining + 0.001, "inner_mm": list(location), "outer_mm": list(outer)})
    return {"diameter_sample_count": len(diameters), "minimum_sampled_diameter_mm": min(diameters), "maximum_sampled_diameter_mm": max(diameters), "minimum_central_corner_section_mm": min(sample["wall_mm"] for sample in web_samples), "central_section_samples": web_samples, "scope": "Three central shaft stations and three rays in the corner bisector plane. The local central web is NOT a global minimum wall; open bore lips taper. No strength certification."}


def torus(name, center, major_radius, wire_radius, collection, builder):
    major_segments = 192
    minor_segments = 32
    vertices = []
    faces = []
    for major_index in range(major_segments):
        major_angle = 2 * math.pi * major_index / major_segments
        for minor_index in range(minor_segments):
            minor_angle = 2 * math.pi * minor_index / minor_segments
            radius = major_radius + wire_radius * math.cos(minor_angle)
            vertices.append(center + Vector((radius * math.cos(major_angle), radius * math.sin(major_angle), wire_radius * math.sin(minor_angle))))
            next_major = (major_index + 1) % major_segments
            next_minor = (minor_index + 1) % minor_segments
            faces.append((major_index * minor_segments + minor_index, next_major * minor_segments + minor_index, next_major * minor_segments + next_minor, major_index * minor_segments + next_minor))
    obj = builder["mesh_object"](name, vertices, faces, collection)
    builder["clean_mesh"](obj)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    obj["export"] = False
    obj["qualification"] = "Simplified metal hardware envelope only; NOT a print part or exact hardware CAD"
    return obj


def hardware_preview_and_screen(body, center, radial, specification, build, builder, validator, tools):
    reference = specification["reference_ring"]
    collection = builder["new_collection"](HARDWARE_COLLECTION)
    shader = builder["material"]("Illustrative brass keyring | not printed", "BA9860", roughness=0.25)
    shader.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 0.85
    major_radius = (reference["inner_diameter"] + reference["wire_diameter"]) / 2
    ring_center = center + radial * (major_radius - reference["centering_offset"])
    lid = bpy.data.objects["CLAWD | lid"]
    device_body = bpy.data.objects["REFERENCE | calibrated body envelope, not metrology"]
    device_lid = bpy.data.objects["REFERENCE | calibrated lid envelope, not metrology"]
    hinge = Vector(build["visual_model_hinge_pivot_mm"])
    results = []
    for coil_index in range(reference["coils"]):
        coil_center = ring_center + Vector((0, 0, (coil_index - (reference["coils"] - 1) / 2) * reference["wire_diameter"]))
        preview = torus(f"DISPLAY ONLY | keyring coil {coil_index + 1}", coil_center, major_radius, reference["wire_diameter"] / 2, collection, builder)
        preview.data.materials.append(shader)
        probe = torus(f"CHECK ONLY | inflated keyring coil {coil_index + 1}", coil_center, major_radius, reference["wire_diameter"] / 2 + reference["additional_radial_clearance_probe"], tools, builder)
        probe.hide_render = True
        intersections = {target.name: validator["intersection_volume"](probe, target) for target in (body, lid, device_body, device_lid)}
        stationary = validator["tree"](probe)
        collisions = []
        for step in range(47):
            degrees = step * 2.5
            transform = Matrix.Translation(hinge) @ Matrix.Rotation(math.radians(-degrees), 4, "X") @ Matrix.Translation(-hinge)
            if stationary.overlap(validator["tree"](lid, transform)) or stationary.overlap(validator["tree"](device_lid, transform)):
                collisions.append(degrees)
        results.append({"coil": coil_index + 1, "center_mm": list(coil_center), "inflated_wire_diameter_mm": reference["wire_diameter"] + 2 * reference["additional_radial_clearance_probe"], "closed_intersections": intersections, "hinge_tested_poses": 47, "hinge_colliding_degrees": collisions})
    passed = all(not item["hinge_colliding_degrees"] and all(check["volume_mm3"] < 0.00001 for check in item["closed_intersections"].values()) for item in results)
    return {"reference": reference, "coils": results, "positioned_envelope_gate_passed": passed, "scope": "Stationary, simplified two-coil mesh envelope and sampled surrogate lid motion only. No threading, split-ring elasticity, ring swing, clasp geometry, manufactured tolerances, load or wear validation."}


def print_exports(validation, exporter, parameters):
    destination = OUTPUT / "clawd-prototype"
    destination.mkdir(parents=True, exist_ok=True)
    report = {"release_status": parameters["release_status"], "stl_units": "mm; select 100% scale", "hardware_exported": False, "files": {}, "round_trip": {}}
    items = []
    for part in ("body", "lid"):
        obj = bpy.data.objects[f"CLAWD | {part}"]
        vertices, triangles = exporter["export_geometry"](obj, invert=part == "lid")
        path = destination / f"clawd-prototype-{part}-v03-mm.stl"
        exporter["save_stl"](path, vertices, triangles, revision="v03")
        report["round_trip"][path.name] = exporter["check_round_trip"](path, validation["parts"][obj.name]["dimensions_mm"])
        report["files"][path.name] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size, "quantity": 1, "dimensions_mm": validation["parts"][obj.name]["dimensions_mm"]}
        items.append((f"CLAWD {part} - UNVALIDATED v03", vertices, triangles))
    pair_path = destination / "clawd-prototype-pair-v03-mm.3mf"
    exporter["save_3mf"](pair_path, items, 45, revision="v03")
    report["three_mf_validation"] = exporter["check_3mf"](pair_path, items)
    report["files"][pair_path.name] = {"sha256": hashlib.sha256(pair_path.read_bytes()).hexdigest(), "bytes": pair_path.stat().st_size, "quantity": "One body and one lid; alternative to the two STLs, not additional items"}
    return report


def main(expected_existing_sha256=None):
    if Path(bpy.data.filepath).resolve() != BASELINE:
        raise RuntimeError("Open the saved v02 model in a separate background Blender process")
    if DESTINATION.exists() and hashlib.sha256(DESTINATION.read_bytes()).hexdigest() != expected_existing_sha256:
        raise RuntimeError("Do not overwrite an existing v03 model without its expected SHA-256")
    if abs(bpy.context.scene.unit_settings.scale_length - 0.001) > 1e-8:
        raise RuntimeError("Expected model coordinates in millimetres")
    parameters = json.loads((ROOT / "models/clawd-v03-parameters.json").read_text())
    specification = parameters["keyring_anchor"]
    if abs(specification["axis_xy_degrees"] - 45) > 0.00001:
        raise RuntimeError("The symmetric corner-entry construction requires a 45 degree bore")
    builder = runpy.run_path(str(ROOT / "tools/build_clawd_case.py"))
    validator = runpy.run_path(str(ROOT / "tools/validate_clawd_case.py"))
    exporter = runpy.run_path(str(ROOT / "tools/export_clawd_case.py"))
    baseline_sha256 = hashlib.sha256(BASELINE.read_bytes()).hexdigest()
    preserved_names = ("CLAWD | lid", "FIT CHECK | body", "FIT CHECK | lid", "CUT | body insertion clearance", "CUT | lid insertion clearance", "CUT | body rear hinge clearance", "CUT | lid rear hinge clearance", "REFERENCE | calibrated body envelope, not metrology", "REFERENCE | calibrated lid envelope, not metrology")
    preserved = {name: validator["geometry_digest"](bpy.data.objects[name]) for name in preserved_names}
    build = json.loads((ROOT / "exports/clawd-v02/qa/design-build.json").read_text())
    original = bpy.data.objects["CLAWD | body"]
    if original.matrix_world != Matrix.Identity(4):
        raise RuntimeError("Expected the body mesh in world millimetres")
    original_bounds = builder["bounds"](original)
    outer_x = original_bounds["max"][0]
    front_y = parameters["front_y"]
    offset = specification["mouth_offset_from_sharp_corner"]
    angle = math.radians(specification["axis_xy_degrees"])
    axis = Vector((math.cos(angle), math.sin(angle), 0))
    radial = Vector((axis.y, -axis.x, 0))
    center = Vector((outer_x - offset / 2, front_y + offset / 2, specification["center_z"]))
    print_collection = original.users_collection[0]
    print_collection.name = "01 | CLAWD PRINT PARTS | v03 UNVALIDATED"
    archive = builder["new_collection"]("08 | ARCHIVED v02 BODY | NO EXPORT")
    original.name = "ARCHIVED v02 | Clawd body without keyring hole"
    builder["move_object"](original, archive)
    revised = builder["duplicate"](original, "CLAWD | body", print_collection)
    original.hide_render = True
    original["export"] = False
    tools = bpy.data.collections["03 | PARAMETRIC MASTERS AND CUTTERS | no export"]
    tools.hide_viewport = False
    cutter = rounded_bore(center, axis, radial, specification, tools, builder)
    builder["boolean"](revised, cutter)
    builder["clean_mesh"](revised)
    builder["finalize_print_mesh"](revised)
    for key in ("release_status", "retention"):
        revised[key] = parameters[key]
    revised["source_parameters"] = "models/clawd-v03-parameters.json"
    revised["keyring_anchor"] = "4 mm diagonal corner bore, no load rating; see parameter file and QA"
    for polygon in revised.data.polygons:
        polygon.material_index = 0
    buffer_radius = specification["bore_diameter"] / 2 + 2 * specification["entry_round_radius"] + specification["cavity_buffer_screen"]
    cavity_probe = cylinder("CHECK ONLY | keyring cavity buffer", center, axis, radial, buffer_radius, tools, builder, specification["cylinder_segments"])
    cavity_intersection = validator["intersection_volume"](cavity_probe, bpy.data.objects["CUT | body insertion clearance"])
    revision_report = {
        "release_status": parameters["release_status"],
        "baseline_blend_sha256": baseline_sha256,
        "revision_scope": parameters["revision_scope"],
        "preserved_geometry": {name: validator["geometry_digest"](bpy.data.objects[name]) == digest for name, digest in preserved.items()},
        "outside_anchor_surface_difference": outside_anchor_difference(original, revised, validator),
        "plastic_bounds_unchanged": original_bounds == builder["bounds"](revised),
        "bore_center_mm": list(center),
        "bore_axis": list(axis),
        "sharp_face_mouth_centers_mm": [[outer_x - offset, front_y, center.z], [outer_x, front_y + offset, center.z]],
        "nominal_centerline_length_inside_block_mm": offset * math.sqrt(2),
        "mouth_rounding": entry_openings(revised, center, axis, outer_x, front_y, specification),
        "sections": bore_sections(revised, center, axis, radial, validator),
        "cavity_buffer_screen": {"probe_radius_mm": buffer_radius, "intersection": cavity_intersection, "scope": "Expanded bore mesh against insertion-clearance cutter, including 0.6 mm radial entry-rounding allowance; not a global wall or manufactured-tolerance certification"},
        "hardware": hardware_preview_and_screen(revised, center, radial, specification, build, builder, validator, tools),
        "physical_tests_performed": [],
    }
    if not all(revision_report["preserved_geometry"].values()) or not revision_report["outside_anchor_surface_difference"]["within_0_0001_mm"] or not revision_report["plastic_bounds_unchanged"]:
        raise RuntimeError("Keyring change exceeded its intended geometry scope")
    if not all(mouth["matches_within_0_01_mm"] for mouth in revision_report["mouth_rounding"]["mouths"].values()):
        raise RuntimeError("The rounded entry geometry does not match its nominal opening sizes")
    if revision_report["sections"]["minimum_sampled_diameter_mm"] < 3.998 or revision_report["sections"]["minimum_central_corner_section_mm"] < specification["minimum_central_corner_section"]:
        raise RuntimeError(f"Keyring local section gate failed: {revision_report['sections']}")
    if cavity_intersection["volume_mm3"] >= 0.00001 or not revision_report["hardware"]["positioned_envelope_gate_passed"]:
        raise RuntimeError("Keyring cavity buffer or reference hardware clearance screen failed")
    qa_directory = OUTPUT / "qa"
    qa_directory.mkdir(parents=True, exist_ok=True)
    build["parameters"] = parameters
    build["print_part_bounds_mm"]["CLAWD | body"] = builder["bounds"](revised)
    build["keyring_bore_center_mm"] = list(center)
    (qa_directory / "design-build.json").write_text(json.dumps(build, indent=2) + "\n")
    archive.hide_viewport = True
    archive.hide_render = True
    tools.hide_viewport = True
    bpy.context.scene.name = "Clawd AirPods 4 ANC | FIT AND KEYRING PROTOTYPE v03"
    bpy.context.scene["source_revision"] = "v02"
    bpy.context.scene["revision_scope"] = parameters["revision_scope"]
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(DESTINATION))
    validation = validator["main"](revision="v03")
    if not validation["mesh_gate_passed"] or not validation["surrogate_fit_gate_passed"] or not validation["original_input_hashes_unchanged"]:
        raise RuntimeError("Digital validation failed; no print exports released")
    validation["outstanding_physical_tests"].extend(("Actual split-ring dimensions, threading and articulation without scratching", "PA12 anchor pull, twist, snag and wear tests using an empty cover or dummy", "Whole-device retention during carrying; keyring does not lock the charging case or separate cover lid"))
    (qa_directory / "geometry-validation.json").write_text(json.dumps(validation, indent=2) + "\n")
    export_report = print_exports(validation, exporter, parameters)
    revision_report["v02_blend_file_unchanged"] = hashlib.sha256(BASELINE.read_bytes()).hexdigest() == baseline_sha256
    (qa_directory / "export-validation.json").write_text(json.dumps(export_report, indent=2) + "\n")
    (qa_directory / "revision-validation.json").write_text(json.dumps(revision_report, indent=2) + "\n")
    return {"blend": str(DESTINATION), "mesh_gate_passed": validation["mesh_gate_passed"], "surrogate_fit_gate_passed": validation["surrogate_fit_gate_passed"], "revision": revision_report, "exports": export_report}


if __name__ == "__main__":
    REVISION_RESULT = main()
