import hashlib
import json
import math
import runpy
from pathlib import Path

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "models/clawd-airpods4-anc-v03.blend"
DESTINATION = ROOT / "models/clawd-airpods4-anc-v04.blend"
OUTPUT = ROOT / "exports/clawd-v04"
PAD_COLLECTION = "11 | COMPLIANT PAD PREVIEW | NOT FOR PRINT"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hinge_transform(hinge, degrees):
    return Matrix.Translation(hinge) @ Matrix.Rotation(math.radians(-degrees), 4, "X") @ Matrix.Translation(-hinge)


def swept_rear_clearance(parameters, hinge, seam, collection, builder):
    specification = parameters["hinge_relief"]
    clearance = specification["motion_clearance"]
    half_width = parameters["character_body_width"] / 2 + clearance
    section = [Vector((0, depth, height)) for depth in (specification["front_y"], parameters["back_y"] + clearance) for height in (seam + parameters["cover_seam_gap"] / 2 - clearance, parameters["character_body_height"] + clearance)]
    step = specification["construction_step_degrees"]
    points = []
    for sample in range(round(specification["maximum_open_degrees"] / step) + 1):
        transform = hinge_transform(hinge, sample * step)
        for point in section:
            moved = transform @ point
            points.extend((Vector((-half_width, moved.y, moved.z)), Vector((half_width, moved.y, moved.z))))
    cutter = builder["convex_object"]("CUT | v04 conservative rear skirt motion envelope", points, collection)
    cutter["qualification"] = "Convex overestimate of a sampled, expanded rear-skirt rectangle; not a measured physical hinge envelope"
    return cutter


def clip_section(polygon, axis, boundary, keep_above):
    clipped = []
    for current, following in zip(polygon, polygon[1:] + polygon[:1]):
        current_inside = current[axis] >= boundary if keep_above else current[axis] <= boundary
        following_inside = following[axis] >= boundary if keep_above else following[axis] <= boundary
        if current_inside:
            clipped.append(current)
        if current_inside != following_inside:
            fraction = (boundary - current[axis]) / (following[axis] - current[axis])
            clipped.append(current.lerp(following, fraction))
    return clipped


def swept_device_clearance(reference, parameters, hinge, seam, collection, builder):
    specification = parameters["hinge_relief"]
    clearance = specification["motion_clearance"]
    bounds = builder["bounds"](reference)
    lower_y, upper_y = bounds["min"][1] - clearance, bounds["max"][1] + clearance
    lower_z, upper_z = bounds["min"][2] - clearance, bounds["max"][2] + clearance
    corners = [Vector((0, lower_y, lower_z)), Vector((0, upper_y, lower_z)), Vector((0, upper_y, upper_z)), Vector((0, lower_y, upper_z))]
    step = specification["construction_step_degrees"]
    points = []
    for sample in range(round(specification["maximum_open_degrees"] / step) + 1):
        transform = hinge_transform(hinge, sample * step).inverted()
        polygon = [transform @ point for point in corners]
        for axis, boundary, keep_above in ((1, specification["front_y"] - clearance, True), (1, parameters["back_y"] + clearance, False), (2, seam + parameters["cover_seam_gap"] / 2 - clearance, True), (2, parameters["character_body_height"] + clearance, False)):
            polygon = clip_section(polygon, axis, boundary, keep_above)
            if not polygon:
                break
        for point in polygon:
            points.extend((Vector((bounds["min"][0] - clearance, point.y, point.z)), Vector((bounds["max"][0] + clearance, point.y, point.z))))
    cutter = builder["convex_object"]("CUT | v04 fixed-device motion clearance inside lid", points, collection)
    cutter["qualification"] = "Expanded device-body box swept into lid coordinates and clipped to the rear skirt before convex enclosure; avoids filling irrelevant chords across the whole cap"
    return cutter


def access_cutters(parameters, collection, builder):
    front = parameters["front_access"]
    front_window = builder["box"]("CUT | v04 bounded LED and pairing window", (-front["width"] / 2, -23, front["center_z"] - front["height"] / 2), (front["width"] / 2, -7, front["center_z"] + front["height"] / 2), collection, front["corner_radius"])
    service = parameters["bottom_access"]
    usb = service["usb_c"]
    bottom = [builder["box"]("CUT | v04 USB-C service window", (-usb["width"] / 2, -usb["depth"] / 2, -15), (usb["width"] / 2, usb["depth"] / 2, service["upper_z"]), collection, usb["corner_radius"])]
    speakers = service["speaker_windows"]
    for center in speakers["centers_x"]:
        bottom.append(builder["box"](f"CUT | v04 speaker service window {center:+g}", (center - speakers["width"] / 2, -speakers["depth"] / 2, -15), (center + speakers["width"] / 2, speakers["depth"] / 2, service["upper_z"]), collection, speakers["corner_radius"]))
    hinge = parameters["hinge_relief"]
    body_hinge = builder["box"]("CUT | v04 local body hinge window", (-hinge["width"] / 2, hinge["front_y"], hinge["body_lower_z"]), (hinge["width"] / 2, 25, 60), collection, 0.5)
    lid_hinge = builder["box"]("CUT | v04 local lid hinge window", (-hinge["width"] / 2, hinge["front_y"], 20), (hinge["width"] / 2, 25, hinge["lid_upper_z"]), collection, 0.5)
    return front_window, bottom, body_hinge, lid_hinge


def pad_seats(part, label, reference, parameters, collection, previews, builder):
    specification = parameters["retention_pads"]
    expanded = builder["offset_points"](reference, specification["seat_normal_clearance"])
    direction = 1 if label == "body" else -1
    seat_envelope = builder["convex_object"](f"CUT | v04 {label} pad seat envelope", expanded + [point + Vector((0, 0, direction * 80)) for point in expanded], collection)
    inner = builder["offset_points"](reference, 0.06)
    pad_inner = builder["convex_object"](f"CUT | v04 {label} seated pad inner envelope", inner + [point + Vector((0, 0, direction * 80)) for point in inner], collection)
    side = specification[f"{label}_side_seats"]
    masks = []
    for sign in (-1, 1):
        minimum_x, maximum_x = (-35, -19) if sign < 0 else (19, 35)
        mask = builder["box"](f"CUT | v04 {label} side seat mask {sign:+d}", (minimum_x, -side["depth_width"] / 2, side["lower_z"]), (maximum_x, side["depth_width"] / 2, side["upper_z"]), collection, 0.5)
        masks.append((f"{label} {'left' if sign < 0 else 'right'} side", mask, (sign, 0, 0)))
    if label == "lid":
        roof = specification["lid_roof_seat"]
        mask = builder["box"]("CUT | v04 lid roof seat mask", (-roof["width"] / 2, -roof["depth"] / 2, roof["lower_z"]), (roof["width"] / 2, roof["depth"] / 2, 55), collection, 0.5)
        masks.append(("lid roof", mask, (0, 0, 1)))
    seats = []
    shader = bpy.data.materials.get("v04 compliant pad charcoal") or builder["material"]("v04 compliant pad charcoal", "333B3F", 0.85)
    for name, mask, direction in masks:
        pocket = builder["duplicate"](seat_envelope, f"CUT | v04 {name} recessed pad seat", collection)
        builder["boolean"](pocket, mask, "INTERSECT")
        builder["boolean"](part, pocket)
        preview = builder["duplicate"](pocket, f"PAD PREVIEW ONLY | {name}", previews)
        builder["boolean"](preview, pad_inner)
        builder["clean_mesh"](preview)
        builder["finalize_print_mesh"](preview)
        preview.data.materials.clear()
        preview.data.materials.append(shader)
        preview["export"] = False
        preview["part"] = label
        preview["qualification"] = "Illustrative seated/compressed pad envelope, not a rigid print part, flat cutting pattern or retention-force simulation"
        seats.append({"name": name, "pocket": pocket, "preview": preview, "normal": Vector(direction), "mask": mask})
    return seats


def seat_measurements(part, reference, seats, validator):
    shell_tree = BVHTree.FromPolygons(*validator["triangle_data"](part), all_triangles=True, epsilon=0)
    device_tree = BVHTree.FromPolygons(*validator["triangle_data"](reference), all_triangles=True, epsilon=0)
    result = []
    for seat in seats:
        normal = seat["normal"]
        mask = seat["mask"]
        corners = [mask.matrix_world @ Vector(corner) for corner in mask.bound_box]
        minimum = Vector(tuple(min(corner[axis] for corner in corners) for axis in range(3)))
        maximum = Vector(tuple(max(corner[axis] for corner in corners) for axis in range(3)))
        primary = next(axis for axis in range(3) if normal[axis])
        axes = [axis for axis in range(3) if axis != primary]
        samples = []
        for first in (0.21, 0.49, 0.79):
            for second in (0.21, 0.49, 0.79):
                origin = Vector((0, 0, 0))
                for axis, fraction in zip(axes, (first, second)):
                    origin[axis] = minimum[axis] + fraction * (maximum[axis] - minimum[axis])
                if primary == 2:
                    origin.z = 40
                device_hit = device_tree.ray_cast(origin, normal, 80)
                seat_hit = shell_tree.ray_cast(origin, normal, 80)
                if device_hit[0] is None or seat_hit[0] is None:
                    raise RuntimeError(f"Missing pad-seat ray: {seat['name']}")
                outer_hit = shell_tree.ray_cast(seat_hit[0] + normal * 0.001, normal, 80)
                if outer_hit[0] is None or seat_hit[1].dot(normal) >= 0 or outer_hit[1].dot(normal) <= 0:
                    raise RuntimeError(f"Pad seat breaks through the shell: {seat['name']}")
                samples.append({"gap_mm": seat_hit[3] - device_hit[3], "wall_mm": outer_hit[3] + 0.001})
        result.append({"name": seat["name"], "sample_count": len(samples), "axis_gap_range_mm": [min(sample["gap_mm"] for sample in samples), max(sample["gap_mm"] for sample in samples)], "minimum_axis_wall_mm": min(sample["wall_mm"] for sample in samples), "qualification": "Axis-aligned sample rays over the seat; not a global minimum, finished-pad specification or force calculation"})
    return result


def dense_motion_screen(body, lid, device_body, device_lid, hinge, validator, seats):
    stationary = {"body": validator["tree"](body), "device body": validator["tree"](device_body)}
    ring_objects = [obj for obj in bpy.data.objects if obj.name.startswith("DISPLAY ONLY | keyring coil")]
    stationary.update({obj.name: validator["tree"](obj) for obj in ring_objects})
    stationary.update({seat["name"]: validator["tree"](seat["preview"]) for seat in seats["body"]})
    collisions = []
    for degrees in range(116):
        transform = hinge_transform(hinge, degrees)
        moving = {"lid": validator["tree"](lid, transform), "device lid": validator["tree"](device_lid, transform)}
        moving.update({seat["name"]: validator["tree"](seat["preview"], transform) for seat in seats["lid"]})
        for fixed_name, fixed in stationary.items():
            for moving_name, moved in moving.items():
                if fixed_name == "device body" and moving_name == "device lid":
                    continue
                overlaps = fixed.overlap(moved)
                if overlaps:
                    collisions.append({"degrees": degrees, "pair": f"{fixed_name} / {moving_name}", "overlap_pairs": len(overlaps)})
    return {"poses": 116, "step_degrees": 1, "range_degrees": [0, 115], "collisions": collisions, "qualification": "Discrete surface collision screen on calibrated visual surrogates and positioned ring; real hinge and hardware motion remain unqualified"}


def projected_exposure(parts, originals, references, validator):
    groups = {"v03": list(originals.values()), "v04": list(parts.values()), "device": references}
    surfaces = {name: [BVHTree.FromPolygons(*validator["triangle_data"](obj), all_triangles=True, epsilon=0) for obj in objects] for name, objects in groups.items()}
    records = {}
    for face in ("front", "rear", "bottom"):
        visible = {"v03": 0, "v04": 0}
        device_pixels = 0
        for column in range(104):
            horizontal = -26 + (column + 0.371) * 0.5
            for row in range(44 if face == "bottom" else 96):
                position = (-11 if face == "bottom" else 2) + (row + 0.419) * 0.5
                if face == "bottom":
                    origin, direction = Vector((horizontal, position, -25)), Vector((0, 0, 1))
                else:
                    origin = Vector((horizontal, -40 if face == "front" else 40, position))
                    direction = Vector((0, 1 if face == "front" else -1, 0))
                hits = [surface.ray_cast(origin, direction, 120) for surface in surfaces["device"]]
                device_distances = [hit[3] for hit in hits if hit[0] is not None]
                if not device_distances:
                    continue
                device_pixels += 1
                nearest_device = min(device_distances)
                for revision in visible:
                    hits = [surface.ray_cast(origin, direction, 120) for surface in surfaces[revision]]
                    if not any(hit[0] is not None and hit[3] < nearest_device - 0.0001 for hit in hits):
                        visible[revision] += 1
        records[face] = {"projected_device_area_mm2": device_pixels * 0.25, "exposed_area_mm2": {revision: count * 0.25 for revision, count in visible.items()}, "exposure_reduction_percent": 100 * (1 - visible["v04"] / visible["v03"]) if visible["v03"] else 0}
    return {"grid_step_mm": 0.5, "views": records, "qualification": "Orthographic ray samples of the closed surrogate, excluding removable pads. Not true surface area, full 3D coverage, sealing or protection certification."}


def export_pair(parts, validation, parameters, exporter):
    destination = OUTPUT / "clawd-prototype"
    destination.mkdir(parents=True, exist_ok=True)
    report = {"release_status": parameters["release_status"], "units": "millimeter; 100 percent scale", "quantity": "ONE body and ONE lid. The 3MF is an alternative to the STL pair. Soft pads and metal hardware are not included.", "files": {}, "round_trip": {}}
    items = []
    for label, part in parts.items():
        vertices, triangles = exporter["export_geometry"](part, invert=label == "lid")
        path = destination / f"clawd-prototype-{label}-v04-mm.stl"
        exporter["save_stl"](path, vertices, triangles, revision="v04")
        report["round_trip"][path.name] = exporter["check_round_trip"](path, validation["parts"][part.name]["dimensions_mm"])
        report["files"][path.name] = {"sha256": digest(path), "bytes": path.stat().st_size, "quantity": 1}
        items.append((f"CLAWD {label} - UNVALIDATED v04", vertices, triangles))
    path = destination / "clawd-prototype-pair-v04-mm.3mf"
    exporter["save_3mf"](path, items, 45, revision="v04")
    report["three_mf_validation"] = exporter["check_3mf"](path, items)
    report["files"][path.name] = {"sha256": digest(path), "bytes": path.stat().st_size}
    return report


def main(expected_existing_sha256=None):
    if not bpy.app.background or Path(bpy.data.filepath).resolve() != BASELINE:
        raise RuntimeError("Open the saved project v03 in a separate background Blender process")
    if DESTINATION.exists() and digest(DESTINATION) != expected_existing_sha256:
        raise RuntimeError("Do not overwrite an existing v04 without its expected SHA-256")
    if bpy.context.scene.unit_settings.system != "METRIC" or abs(bpy.context.scene.unit_settings.scale_length - 0.001) > 1e-8:
        raise RuntimeError("Expected existing millimetre model coordinates")
    parameters = json.loads((ROOT / "models/clawd-v04-parameters.json").read_text())
    builder = runpy.run_path(str(ROOT / "tools/build_clawd_case.py"))
    validator = runpy.run_path(str(ROOT / "tools/validate_clawd_case.py"))
    exporter = runpy.run_path(str(ROOT / "tools/export_clawd_case.py"))
    baseline_hash = digest(BASELINE)
    protected_files = {str(path.relative_to(ROOT)): digest(path) for path in (ROOT / "models").glob("*.blend") if path != DESTINATION}
    original_hashes = json.loads((ROOT / "exports/reference-audit/asset-audit.json").read_text())["input_hashes"]
    protected_names = ("CUT | body insertion clearance", "CUT | lid insertion clearance", "CUT | robust pixel andreabalbo.com", "CUT | v03 keyring bore with rounded entries", "REFERENCE | calibrated body envelope, not metrology", "REFERENCE | calibrated lid envelope, not metrology", "FIT CHECK | body", "FIT CHECK | lid")
    protected = {name: validator["geometry_digest"](bpy.data.objects[name]) for name in protected_names}
    tools = bpy.data.collections["03 | PARAMETRIC MASTERS AND CUTTERS | no export"]
    tools.hide_viewport = False
    archive = builder["new_collection"]("10 | ARCHIVED v03 SHELLS | NO EXPORT")
    previews = builder["new_collection"](PAD_COLLECTION)
    originals = {}
    for label in ("body", "lid"):
        original = bpy.data.objects[f"CLAWD | {label}"]
        originals[label] = original
        if label == "body":
            print_collection = original.users_collection[0]
            print_collection.name = "01 | CLAWD PRINT PARTS | v04 UNVALIDATED"
        original.name = f"ARCHIVED v03 | Clawd {label} before full wrap"
        builder["move_object"](original, archive)
        original.hide_render = True
        original["export"] = False
    master = bpy.data.objects["MASTER | supplied Clawd silhouette, adapted proportions"]
    parts = {label: builder["duplicate"](master, f"CLAWD | {label}", print_collection) for label in ("body", "lid")}
    build = json.loads((ROOT / "exports/clawd-v03/qa/design-build.json").read_text())
    seam = build["nominal_cover_seam_z_mm"]
    hinge = Vector(build["visual_model_hinge_pivot_mm"])
    front, bottom, body_hinge, lid_hinge = access_cutters(parameters, tools, builder)
    motion_cutter = swept_rear_clearance(parameters, hinge, seam, tools, builder)
    for name in ("CUT | CLAWD remove upper", "CUT | body insertion clearance"):
        builder["boolean"](parts["body"], bpy.data.objects[name])
    for cutter in (front, *bottom, body_hinge, motion_cutter):
        builder["boolean"](parts["body"], cutter)
    for name in ("CUT | square recessed eye", "CUT | square recessed eye.001", "CUT | v03 keyring bore with rounded entries"):
        builder["boolean"](parts["body"], bpy.data.objects[name])
    for name in ("CUT | CLAWD remove lower", "CUT | lid insertion clearance", "CUT | robust pixel andreabalbo.com"):
        builder["boolean"](parts["lid"], bpy.data.objects[name])
    builder["boolean"](parts["lid"], lid_hinge)
    device_motion = swept_device_clearance(bpy.data.objects["REFERENCE | calibrated body envelope, not metrology"], parameters, hinge, seam, tools, builder)
    builder["boolean"](parts["lid"], device_motion)
    seats = {}
    for label, part in parts.items():
        reference = bpy.data.objects[f"REFERENCE | calibrated {label} envelope, not metrology"]
        seats[label] = pad_seats(part, label, reference, parameters, tools, previews, builder)
        builder["clean_mesh"](part)
        builder["finalize_print_mesh"](part)
        part.data.materials.clear()
        for material in originals[label].data.materials:
            part.data.materials.append(material)
        for polygon in part.data.polygons:
            polygon.material_index = 0
        part["units"] = "mm"
        part["source_parameters"] = "models/clawd-v04-parameters.json"
        part["release_status"] = parameters["release_status"]
        part["retention"] = parameters["retention"]
        part["nominal_clearance_mm"] = parameters["nominal_normal_clearance"]
        part["export"] = True
    device_body = bpy.data.objects["REFERENCE | calibrated body envelope, not metrology"]
    device_lid = bpy.data.objects["REFERENCE | calibrated lid envelope, not metrology"]
    measurements = {label: seat_measurements(part, bpy.data.objects[f"REFERENCE | calibrated {label} envelope, not metrology"], seats[label], validator) for label, part in parts.items()}
    audits = {label: validator["mesh_audit"](part) for label, part in parts.items()}
    motion = dense_motion_screen(parts["body"], parts["lid"], device_body, device_lid, hinge, validator, seats)
    audit_errors = ("boundary_edges", "non_manifold_edges", "inconsistently_oriented_edges", "loose_vertices", "degenerate_faces_below_1e-10_mm2", "nonadjacent_triangle_overlap_candidates")
    mesh_gate = all(audit["connected_components"] == 1 and audit["signed_volume_mm3"] > 0 and all(audit[key] == 0 for key in audit_errors) for audit in audits.values())
    report = {"release_status": parameters["release_status"], "baseline_sha256": baseline_hash, "parts": audits, "pad_seats": measurements, "dense_hinge_screen": motion, "projected_exposure": projected_exposure(parts, originals, [device_body, device_lid], validator), "protected_geometry": {name: validator["geometry_digest"](bpy.data.objects[name]) == original for name, original in protected.items()}, "physical_tests_performed": [], "mesh_gate_passed": mesh_gate}
    qa = OUTPUT / "qa"
    qa.mkdir(parents=True, exist_ok=True)
    (qa / "coverage-revision-validation.json").write_text(json.dumps(report, indent=2) + "\n")
    if not mesh_gate or motion["collisions"]:
        return {"saved": False, "reason": "Geometry or hinge screen failed", "mesh_gate": mesh_gate, "audits": audits, "collisions": motion["collisions"][:12], "report": str(qa / "coverage-revision-validation.json")}
    if not all(report["protected_geometry"].values()) or min(seat["minimum_axis_wall_mm"] for records in measurements.values() for seat in records) < 2.0:
        raise RuntimeError("Protected geometry changed or a pad-seat wall sample is below 2 mm")
    build["parameters"] = parameters
    build["print_part_bounds_mm"] = {part.name: builder["bounds"](part) for part in parts.values()}
    build["historical_fit_check_parts"] = "Unchanged v03 fit-check meshes are archived context, not representative of v04 retention or export parts"
    (qa / "design-build.json").write_text(json.dumps(build, indent=2) + "\n")
    archive.hide_render = True
    archive.hide_viewport = True
    tools.hide_render = True
    tools.hide_viewport = True
    for obj in tools.objects:
        obj.hide_render = True
    scene = bpy.context.scene
    scene.name = "Clawd AirPods 4 ANC | FULL WRAP AND PAD RETENTION v04"
    scene["release_status"] = parameters["release_status"]
    scene["source_revision"] = "v03"
    scene["revision_scope"] = parameters["revision_scope"]
    scene["retention"] = parameters["retention"]
    scene["physical_tests"] = "Not performed; actual fit, pad retention, device finish, charging, hinge and anchor qualification required"
    builder["activate"](parts["body"])
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(DESTINATION))
    validation = validator["main"](revision="v04")
    if not validation["mesh_gate_passed"] or not validation["surrogate_fit_gate_passed"] or not validation["original_input_hashes_unchanged"]:
        raise RuntimeError("Digital validation failed; no print exports released")
    validation["outstanding_physical_tests"].extend(("Install two body pads and three lid pads; measure actual seat gaps before choosing thickness", "Qualify friction retention and, if needed, a finish-compatible removable roof adhesive pad", "Test lid-cap removal, opening and repeated cycles over a soft surface before keyring carrying", "Verify actual rear-hinge hardware clearance and reduced service-window access"))
    (qa / "geometry-validation.json").write_text(json.dumps(validation, indent=2) + "\n")
    report["export"] = export_pair(parts, validation, parameters, exporter)
    report["preserved_model_files"] = {name: digest(ROOT / name) == original for name, original in protected_files.items()}
    report["original_inputs_unchanged"] = all(digest(ROOT / name) == original for name, original in original_hashes.items())
    if not all(report["preserved_model_files"].values()) or not report["original_inputs_unchanged"]:
        raise RuntimeError("Preserved input changed during this operation")
    (qa / "coverage-revision-validation.json").write_text(json.dumps(report, indent=2) + "\n")
    (qa / "export-validation.json").write_text(json.dumps(report["export"], indent=2) + "\n")
    return {"saved": True, "blend": str(DESTINATION), "blend_sha256": digest(DESTINATION), "mesh_gate_passed": validation["mesh_gate_passed"], "surrogate_fit_gate_passed": validation["surrogate_fit_gate_passed"], "hinge_poses_passed": motion["poses"], "pad_seats": measurements, "projected_exposure": report["projected_exposure"], "exports": str(OUTPUT / "clawd-prototype"), "baseline_models_unchanged": all(report["preserved_model_files"].values()), "original_inputs_unchanged": report["original_inputs_unchanged"]}


if __name__ == "__main__":
    REVISION_RESULT = main()
