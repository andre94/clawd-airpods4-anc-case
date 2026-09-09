import hashlib
import json
import runpy
import struct
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "models/clawd-airpods4-anc-v01.blend"
OUTPUT = ROOT / "exports/clawd-dfm-diagnostics"


def thickness_samples(obj):
    obj.data.calc_loop_triangles()
    vertices = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    triangles = [tuple(triangle.vertices) for triangle in obj.data.loop_triangles]
    surface = BVHTree.FromPolygons(vertices, triangles, all_triangles=True, epsilon=0)
    samples = []
    for triangle_index, indices in enumerate(triangles):
        first, second, third = [vertices[index] for index in indices]
        cross = (second - first).cross(third - first)
        area = cross.length / 2
        if area < 1e-9:
            continue
        normal = cross.normalized()
        center = (first + second + third) / 3
        location, exit_normal, exit_index, distance = surface.ray_cast(center - normal * 0.0001, -normal, 150)
        if location is None or exit_index == triangle_index or normal.dot(exit_normal) > -0.5:
            continue
        if center.y > 12.45 and 43 < center.z < 51:
            region = "branding_band"
        elif 6.0 < center.y < 7.4 and center.z < 43:
            region = "hinge_cut_edge"
        else:
            region = "other"
        samples.append({"triangle": triangle_index, "thickness_mm": distance + 0.0001, "center_mm": list(center), "area_mm2": area, "region": region})
    samples.sort(key=lambda sample: sample["thickness_mm"])
    regions = {}
    for region in ("branding_band", "hinge_cut_edge", "other"):
        subset = [sample for sample in samples if sample["region"] == region]
        thin = [sample for sample in subset if sample["thickness_mm"] < 0.8]
        regions[region] = {
            "opposing_exit_samples": len(subset),
            "sampled_minimum_mm": min((sample["thickness_mm"] for sample in subset), default=None),
            "under_0_8_samples": len(thin),
            "under_0_8_triangle_area_mm2": sum(sample["area_mm2"] for sample in thin),
            "thinnest_examples": subset[:5],
        }
    return {"triangles": len(triangles), "regions": regions}


def engraving_islands(obj, spacing=0.05):
    obj.data.calc_loop_triangles()
    vertices = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    triangles = [tuple(triangle.vertices) for triangle in obj.data.loop_triangles]
    surface = BVHTree.FromPolygons(vertices, triangles, all_triangles=True, epsilon=0)
    width = int(60 / spacing) + 1
    height = int(8 / spacing) + 1
    raised = set()
    for column in range(width):
        for row in range(height):
            origin = Vector((-30 + column * spacing, 20, 43 + row * spacing))
            location, normal, triangle_index, distance = surface.ray_cast(origin, Vector((0, -1, 0)), 10)
            if location is not None and location.y > 12.9:
                raised.add((column, row))
    components = []
    while raised:
        component = {raised.pop()}
        pending = list(component)
        while pending:
            column, row = pending.pop()
            for neighbor in ((column - 1, row), (column + 1, row), (column, row - 1), (column, row + 1)):
                if neighbor in raised:
                    raised.remove(neighbor)
                    component.add(neighbor)
                    pending.append(neighbor)
        if any(column in (0, width - 1) or row in (0, height - 1) for column, row in component):
            continue
        columns = [point[0] for point in component]
        rows = [point[1] for point in component]
        components.append({
            "sampled_area_mm2": len(component) * spacing * spacing,
            "bbox_width_mm": (max(columns) - min(columns) + 1) * spacing,
            "bbox_height_mm": (max(rows) - min(rows) + 1) * spacing,
            "center_xz_mm": [-30 + (min(columns) + max(columns)) * spacing / 2, 43 + (min(rows) + max(rows)) * spacing / 2],
        })
    return {"grid_spacing_mm": spacing, "scope": "2D connected counter/island approximation at the unengraved back face; not minimum wall certification", "islands": sorted(components, key=lambda component: component["center_xz_mm"][0])}


def save_diagnostic_stl(path, vertices, triangles):
    with path.open("wb") as output:
        output.write(b"DIAGNOSTIC ONLY - DO NOT ORDER | Clawd lid | units mm".ljust(80, b" "))
        output.write(struct.pack("<I", len(triangles)))
        for triangle in triangles:
            points = [vertices[index] for index in triangle]
            normal = (points[1] - points[0]).cross(points[2] - points[0]).normalized()
            output.write(struct.pack("<12fH", *normal, *(coordinate for point in points for coordinate in point), 0))


def main():
    if Path(bpy.data.filepath).resolve() != BASELINE:
        raise RuntimeError("Open the saved v01 model in a separate background process")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    builder = runpy.run_path(str(ROOT / "tools/build_clawd_case.py"))
    exporter = runpy.run_path(str(ROOT / "tools/export_clawd_case.py"))
    validator = runpy.run_path(str(ROOT / "tools/validate_clawd_case.py"))
    branding = runpy.run_path(str(ROOT / "tools/clawd_branding.py"))
    original_hash = hashlib.sha256(BASELINE.read_bytes()).hexdigest()
    original_body_digest = validator["geometry_digest"](bpy.data.objects["CLAWD | body"])
    tools = bpy.data.collections["03 | PARAMETRIC MASTERS AND CUTTERS | no export"]
    tools.hide_viewport = False
    diagnostic = builder["new_collection"]("07 | DFM DIAGNOSTICS | NOT FOR ORDER")
    pristine = builder["duplicate"](bpy.data.objects["MASTER | supplied Clawd silhouette, adapted proportions"], "DIAGNOSTIC | Clawd lid without text", diagnostic)
    for name in ("CUT | CLAWD remove lower", "CUT | lid insertion clearance", "CUT | lid rear hinge clearance"):
        builder["boolean"](pristine, bpy.data.objects[name])
    enlarged = builder["duplicate"](pristine, "DIAGNOSTIC | Clawd lid enlarged text", diagnostic)
    builder["PARAMETERS"]["back_text"]["height"] = 4.5
    builder["engrave_brand"](enlarged, diagnostic)
    pixel_shallow = builder["duplicate"](pristine, "DIAGNOSTIC | pixel text depth 0.45", diagnostic)
    pixel_deep = builder["duplicate"](pristine, "DIAGNOSTIC | pixel text depth 1.0", diagnostic)
    for obj, depth in ((pixel_shallow, 0.45), (pixel_deep, 1.0)):
        branding["engrave_pixel_brand"](obj, diagnostic, builder, {"content": "andreabalbo.com", "center_z": 47.2, "pixel_pitch": 1.0, "engraving_depth": depth})
    report = {
        "status": "DIAGNOSTIC_VARIANTS_NOT_AUTHORIZED_FOR_MANUFACTURE",
        "normal_ray_scope": "Triangle-centroid inward rays; opposing exit normals only. Sharp edges taper to zero, so sampled minima are not certified wall dimensions.",
        "baseline_blend_sha256": original_hash,
        "parts": {},
        "exports": {},
    }
    for obj, label in ((bpy.data.objects["CLAWD | lid"], "v01_original"), (bpy.data.objects["FIT CHECK | lid"], "v01_fit_lid"), (pristine, "no_text"), (enlarged, "text_height_4_5"), (pixel_shallow, "pixel_depth_0_45"), (pixel_deep, "pixel_depth_1_0")):
        if obj in (pristine, enlarged, pixel_shallow, pixel_deep):
            builder["clean_mesh"](obj)
            builder["finalize_print_mesh"](obj)
        report["parts"][label] = {"mesh": validator["mesh_audit"](obj), "thickness": thickness_samples(obj), "letter_counters": engraving_islands(obj)}
        if obj in (pristine, enlarged, pixel_shallow, pixel_deep):
            vertices, triangles = exporter["export_geometry"](obj, invert=True)
            path = OUTPUT / f"DIAGNOSTIC-NOT-FOR-ORDER-clawd-lid-{label}-mm.stl"
            save_diagnostic_stl(path, vertices, triangles)
            round_trip = exporter["check_round_trip"](path, report["parts"][label]["mesh"]["dimensions_mm"])
            report["exports"][label] = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "round_trip": round_trip}
    report["body_unchanged"] = validator["geometry_digest"](bpy.data.objects["CLAWD | body"]) == original_body_digest
    report["v01_blend_file_unchanged"] = hashlib.sha256(BASELINE.read_bytes()).hexdigest() == original_hash
    (OUTPUT / "diagnosis.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    DIAGNOSTIC_RESULT = main()
