import hashlib
import json
import runpy
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "models/clawd-airpods4-anc-v01.blend"
DESTINATION = ROOT / "models/clawd-airpods4-anc-v02.blend"
OUTPUT = ROOT / "exports/clawd-v02"


def rear_floor_wall(lid, validator, specification):
    surface = validator["tree"](lid)
    floor_y = 12.95 - specification["engraving_depth"]
    samples = []
    for column in range(237):
        for row in range(21):
            origin = Vector((-29.5 + column * 0.25, 20, 44.7 + row * 0.25))
            location, normal, triangle_index, distance = surface.ray_cast(origin, Vector((0, -1, 0)), 15)
            if location is None or abs(location.y - floor_y) > 0.0001:
                continue
            exit_location, exit_normal, exit_index, remaining = surface.ray_cast(location + Vector((0, -0.0001, 0)), Vector((0, -1, 0)), 40)
            if exit_location is not None:
                samples.append({"thickness_mm": remaining + 0.0001, "position_mm": list(location)})
    if not samples:
        raise RuntimeError("No engraved-floor wall samples found")
    samples.sort(key=lambda sample: sample["thickness_mm"])
    return {"sample_spacing_mm": 0.25, "samples": len(samples), "minimum_sampled_mm": samples[0]["thickness_mm"], "thinnest_samples": samples[:5], "scope": "Rear-to-front rays through engraved floors, not a certified global wall minimum"}


def outside_brand_surface_difference(original, revised, validator):
    maxima = []
    for source, target in ((original, revised), (revised, original)):
        surface = validator["tree"](target)
        distances = []
        for vertex in source.data.vertices:
            point = source.matrix_world @ vertex.co
            in_brand_region = point.y >= 11.9499 and 44.6999 <= point.z <= 49.7001
            if in_brand_region:
                continue
            location, normal, triangle_index, distance = surface.find_nearest(point)
            if location is None:
                raise RuntimeError("Missing comparison surface")
            distances.append(distance)
        maxima.append(max(distances, default=0))
    return {"bidirectional_vertex_to_surface_max_mm": maxima, "within_0_0001_mm": max(maxima) < 0.0001, "scope": "Outside the revised branding strip; construction also reuses original masters and cutters"}


def main(expected_existing_sha256=None):
    if Path(bpy.data.filepath).resolve() != BASELINE:
        raise RuntimeError("Open the saved v01 model in a separate background Blender process")
    if DESTINATION.exists() and hashlib.sha256(DESTINATION.read_bytes()).hexdigest() != expected_existing_sha256:
        raise RuntimeError("Do not overwrite an existing v02 model without its expected SHA-256")
    if abs(bpy.context.scene.unit_settings.scale_length - 0.001) > 1e-8:
        raise RuntimeError("Expected model coordinates in millimetres")
    parameters = json.loads((ROOT / "models/clawd-v02-parameters.json").read_text())
    builder = runpy.run_path(str(ROOT / "tools/build_clawd_case.py"))
    validator = runpy.run_path(str(ROOT / "tools/validate_clawd_case.py"))
    exporter = runpy.run_path(str(ROOT / "tools/export_clawd_case.py"))
    branding = runpy.run_path(str(ROOT / "tools/clawd_branding.py"))
    diagnostic = runpy.run_path(str(ROOT / "tools/diagnose_clawd_walls.py"))
    baseline_sha256 = hashlib.sha256(BASELINE.read_bytes()).hexdigest()
    preserved_names = ("CLAWD | body", "FIT CHECK | body", "FIT CHECK | lid", "CUT | body insertion clearance", "CUT | lid insertion clearance", "CUT | body rear hinge clearance", "CUT | lid rear hinge clearance")
    preserved = {name: validator["geometry_digest"](bpy.data.objects[name]) for name in preserved_names}
    tools = bpy.data.collections["03 | PARAMETRIC MASTERS AND CUTTERS | no export"]
    tools.hide_viewport = False
    original = bpy.data.objects["CLAWD | lid"]
    print_collection = original.users_collection[0]
    print_collection.name = "01 | CLAWD PRINT PARTS | v02 UNVALIDATED"
    archive = builder["new_collection"]("07 | ARCHIVED v01 LID | NO EXPORT")
    original.name = "ARCHIVED v01 | Clawd lid, thin-letter warning"
    builder["move_object"](original, archive)
    original.hide_render = True
    revised = builder["duplicate"](bpy.data.objects["MASTER | supplied Clawd silhouette, adapted proportions"], "CLAWD | lid", print_collection)
    for name in ("CUT | CLAWD remove lower", "CUT | lid insertion clearance", "CUT | lid rear hinge clearance"):
        builder["boolean"](revised, bpy.data.objects[name])
    cutter = branding["engrave_pixel_brand"](revised, tools, builder, parameters["back_text"])
    builder["clean_mesh"](revised)
    builder["finalize_print_mesh"](revised)
    revised.data.materials.clear()
    for material in original.data.materials:
        revised.data.materials.append(material)
    for polygon in revised.data.polygons:
        polygon.material_index = 0
    for key in ("release_status", "retention"):
        revised[key] = parameters[key]
    revised["units"] = "mm"
    revised["nominal_clearance_mm"] = parameters["nominal_normal_clearance"]
    revised["source_parameters"] = "models/clawd-v02-parameters.json"
    revision_report = {
        "release_status": parameters["release_status"],
        "baseline_blend_sha256": baseline_sha256,
        "revision_scope": parameters["revision_scope"],
        "preserved_geometry": {name: validator["geometry_digest"](bpy.data.objects[name]) == digest for name, digest in preserved.items()},
        "outside_brand_surface_difference": outside_brand_surface_difference(original, revised, validator),
        "engraved_floor_wall": rear_floor_wall(revised, validator, parameters["back_text"]),
        "normal_ray_diagnostic": diagnostic["thickness_samples"](revised),
        "brand_bounds_mm": builder["bounds"](cutter),
    }
    if not all(revision_report["preserved_geometry"].values()) or not revision_report["outside_brand_surface_difference"]["within_0_0001_mm"]:
        raise RuntimeError("Revision modified geometry outside its approved scope")
    if revision_report["engraved_floor_wall"]["minimum_sampled_mm"] < 2.0:
        raise RuntimeError("Less than 2 mm backing remains at an engraved-floor sample")
    qa_directory = OUTPUT / "qa"
    qa_directory.mkdir(parents=True, exist_ok=True)
    build = json.loads((ROOT / "exports/clawd-v01/qa/design-build.json").read_text())
    build["parameters"] = parameters
    build["brand_cutter_bounds_mm"] = builder["bounds"](cutter)
    build["print_part_bounds_mm"]["CLAWD | lid"] = builder["bounds"](revised)
    (qa_directory / "design-build.json").write_text(json.dumps(build, indent=2) + "\n")
    archive.hide_viewport = True
    archive.hide_render = True
    tools.hide_viewport = True
    bpy.context.scene.name = "Clawd AirPods 4 ANC | FIT PROTOTYPE v02"
    bpy.context.scene["source_revision"] = "v01"
    bpy.context.scene["revision_scope"] = parameters["revision_scope"]
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(DESTINATION))
    validation = validator["main"](revision="v02")
    if not validation["mesh_gate_passed"] or not validation["surrogate_fit_gate_passed"] or not validation["original_input_hashes_unchanged"]:
        raise RuntimeError("Digital validation failed; no print exports released")
    destination = OUTPUT / "clawd-prototype"
    destination.mkdir(parents=True, exist_ok=True)
    export_report = {"release_status": parameters["release_status"], "stl_units": "mm; select 100% scale", "files": {}, "round_trip": {}}
    items = []
    for part in ("body", "lid"):
        obj = bpy.data.objects[f"CLAWD | {part}"]
        vertices, triangles = exporter["export_geometry"](obj, invert=part == "lid")
        path = destination / f"clawd-prototype-{part}-v02-mm.stl"
        exporter["save_stl"](path, vertices, triangles, revision="v02")
        export_report["round_trip"][path.name] = exporter["check_round_trip"](path, validation["parts"][obj.name]["dimensions_mm"])
        export_report["files"][path.name] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size, "quantity": 1}
        items.append((f"CLAWD {part} - UNVALIDATED v02", vertices, triangles))
    pair_path = destination / "clawd-prototype-pair-v02-mm.3mf"
    exporter["save_3mf"](pair_path, items, 45, revision="v02")
    export_report["three_mf_validation"] = exporter["check_3mf"](pair_path, items)
    export_report["files"][pair_path.name] = {"sha256": hashlib.sha256(pair_path.read_bytes()).hexdigest(), "bytes": pair_path.stat().st_size, "quantity": "One body and one lid; alternative to the two STL files"}
    revision_report["v01_blend_file_unchanged"] = hashlib.sha256(BASELINE.read_bytes()).hexdigest() == baseline_sha256
    (qa_directory / "export-validation.json").write_text(json.dumps(export_report, indent=2) + "\n")
    (qa_directory / "revision-validation.json").write_text(json.dumps(revision_report, indent=2) + "\n")
    return {"blend": str(DESTINATION), "mesh_gate_passed": validation["mesh_gate_passed"], "surrogate_fit_gate_passed": validation["surrogate_fit_gate_passed"], "revision": revision_report, "exports": export_report}


if __name__ == "__main__":
    REVISION_RESULT = main()
