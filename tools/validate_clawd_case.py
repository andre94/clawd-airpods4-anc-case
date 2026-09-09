import hashlib
import json
import math
import struct
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "exports/clawd-v01/qa"
PART_NAMES = ["CLAWD | body", "CLAWD | lid", "FIT CHECK | body", "FIT CHECK | lid"]


def triangle_data(obj, matrix=None):
    transform = obj.matrix_world if matrix is None else matrix @ obj.matrix_world
    obj.data.calc_loop_triangles()
    vertices = [transform @ vertex.co for vertex in obj.data.vertices]
    triangles = [tuple(triangle.vertices) for triangle in obj.data.loop_triangles]
    return vertices, triangles


def tree(obj, matrix=None):
    vertices, triangles = triangle_data(obj, matrix)
    return BVHTree.FromPolygons(vertices, triangles, all_triangles=True, epsilon=0.000001)


def geometry_digest(obj):
    vertices, triangles = triangle_data(obj)
    digest = hashlib.sha256()
    for vertex in vertices:
        digest.update(struct.pack("<3f", *vertex))
    for triangle in triangles:
        digest.update(struct.pack("<3I", *triangle))
    return digest.hexdigest()


def mesh_audit(obj):
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    remaining = set(mesh.verts)
    connected_components = 0
    while remaining:
        connected_components += 1
        pending = [remaining.pop()]
        while pending:
            vertex = pending.pop()
            for edge in vertex.link_edges:
                neighbor = edge.other_vert(vertex)
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    pending.append(neighbor)
    vertices, triangles = triangle_data(obj)
    minimum = [min(vertex[axis] for vertex in vertices) for axis in range(3)]
    maximum = [max(vertex[axis] for vertex in vertices) for axis in range(3)]
    bvh = BVHTree.FromPolygons(vertices, triangles, all_triangles=True, epsilon=0)
    intersections = set()
    for first, second in bvh.overlap(bvh):
        if first >= second or set(triangles[first]) & set(triangles[second]):
            continue
        intersections.add((first, second))
    report = {
        "geometry_sha256": geometry_digest(obj),
        "vertices": len(mesh.verts),
        "triangles": len(triangles),
        "connected_components": connected_components,
        "boundary_edges": sum(edge.is_boundary for edge in mesh.edges),
        "non_manifold_edges": sum(not edge.is_manifold for edge in mesh.edges),
        "inconsistently_oriented_edges": sum(edge.is_manifold and not edge.is_contiguous for edge in mesh.edges),
        "loose_vertices": sum(not vertex.link_faces for vertex in mesh.verts),
        "degenerate_faces_below_1e-10_mm2": sum(face.calc_area() < 1e-10 for face in mesh.faces),
        "signed_volume_mm3": mesh.calc_volume(signed=True),
        "surface_area_mm2": sum(face.calc_area() for face in mesh.faces),
        "dimensions_mm": [maximum[axis] - minimum[axis] for axis in range(3)],
        "nonadjacent_triangle_overlap_candidates": len(intersections),
        "overlap_candidate_examples": sorted(intersections)[:12],
    }
    mesh.free()
    return report


def intersection_volume(first, second):
    temporary = first.copy()
    temporary.data = first.data.copy()
    bpy.context.scene.collection.objects.link(temporary)
    temporary.hide_viewport = False
    temporary.hide_set(False)
    bpy.context.view_layer.objects.active = temporary
    modifier = temporary.modifiers.new("Verification intersection", "BOOLEAN")
    modifier.operation = "INTERSECT"
    modifier.solver = "EXACT"
    modifier.object = second
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    mesh = bmesh.new()
    mesh.from_mesh(temporary.data)
    volume = abs(mesh.calc_volume(signed=True)) if mesh.faces else 0
    face_count = len(mesh.faces)
    mesh.free()
    data = temporary.data
    bpy.data.objects.remove(temporary, do_unlink=True)
    bpy.data.meshes.remove(data)
    return {"volume_mm3": volume, "faces": face_count}


def ray_intervals(obj, origin, direction):
    bvh = tree(obj)
    current = Vector(origin)
    direction = Vector(direction).normalized()
    start = current.copy()
    hits = []
    for count in range(30):
        location, normal, index, distance = bvh.ray_cast(current, direction, 150)
        if location is None:
            break
        travelled = (location - start).length
        if not hits or travelled - hits[-1] > 0.001:
            hits.append(travelled)
        current = location + direction * 0.002
    return [round(hits[index + 1] - hits[index], 5) for index in range(0, len(hits) - 1, 2)]


def main(revision="v01"):
    expected = ROOT / f"models/clawd-airpods4-anc-{revision}.blend"
    output = ROOT / f"exports/clawd-{revision}/qa"
    if Path(bpy.data.filepath).resolve() != expected.resolve():
        raise RuntimeError(f"Validation is restricted to this project's {revision} model")
    for target in bpy.context.scene.collection.children:
        if target.name.startswith("05"):
            target.hide_viewport = False
    build = json.loads((output / "design-build.json").read_text())
    parts = [bpy.data.objects[name] for name in PART_NAMES]
    body = bpy.data.objects["CLAWD | body"]
    lid = bpy.data.objects["CLAWD | lid"]
    device_body = bpy.data.objects["REFERENCE | calibrated body envelope, not metrology"]
    device_lid = bpy.data.objects["REFERENCE | calibrated lid envelope, not metrology"]
    report = {"status": "DIGITAL_CHECKS_ONLY_PHYSICAL_QUALIFICATION_PENDING", "units": "millimeter", "parts": {obj.name: mesh_audit(obj) for obj in parts}}
    report["parameters_sha256"] = hashlib.sha256((ROOT / f"models/clawd-{revision}-parameters.json").read_bytes()).hexdigest()
    report["closed_device_intersections"] = {f"{part.name} / {device.name}": intersection_volume(part, device) for part in parts for device in (device_body, device_lid)}
    stationary_tree = tree(body)
    hinge = Vector(build["visual_model_hinge_pivot_mm"])
    opening_results = []
    for step in range(47):
        degrees = step * 2.5
        transform = Matrix.Translation(hinge) @ Matrix.Rotation(math.radians(-degrees), 4, "X") @ Matrix.Translation(-hinge)
        lid_overlaps = stationary_tree.overlap(tree(lid, transform))
        device_overlaps = stationary_tree.overlap(tree(device_lid, transform))
        opening_results.append({"degrees": degrees, "cover_surface_overlap_pairs": len(lid_overlaps), "device_lid_surface_overlap_pairs": len(device_overlaps)})
    report["hinge_sweep"] = {"pivot_mm": list(hinge), "angle_range_degrees": [0, 115], "step_degrees": 2.5, "tested_poses": len(opening_results), "colliding_poses": [item for item in opening_results if item["cover_surface_overlap_pairs"] or item["device_lid_surface_overlap_pairs"]], "qualification": "Discrete surrogate-geometry screen; actual hinge location, continuous motion and hand clearance are not validated"}
    insertion_results = {}
    for part, device, direction in ((body, device_body, 1), (lid, device_lid, -1)):
        part_tree = tree(part)
        failures = []
        for distance in range(0, 66):
            transform = Matrix.Translation(Vector((0, 0, distance * direction)))
            overlaps = part_tree.overlap(tree(device, transform))
            if overlaps:
                failures.append({"translation_mm": distance * direction, "surface_overlap_pairs": len(overlaps)})
        insertion_results[part.name] = {"tested_poses": 66, "step_mm": 1, "colliding_poses": failures}
    report["axial_insertion_screen"] = insertion_results
    wall_samples = {}
    for horizontal in (-18, -10, 0, 10, 18):
        for height in (12, 20, 26):
            wall_samples[f"body_x{horizontal}_z{height}"] = ray_intervals(body, (horizontal, 30, height), (0, -1, 0))
    for horizontal in (-19.8, 19.8):
        wall_samples[f"eye_floor_x{horizontal}"] = ray_intervals(body, (horizontal, -30, 26), (0, 1, 0))
    for horizontal in (-18, 0, 18):
        wall_samples[f"lid_back_x{horizontal}_z47.2"] = ray_intervals(lid, (horizontal, 30, 47.2), (0, -1, 0))
    report["selected_wall_sections_mm"] = wall_samples
    report["wall_check_scope"] = "Selected axis-aligned sections only, not a certified global minimum-wall analysis; bevel/engraving/hinge edges need printer review"
    baseline = json.loads((ROOT / "exports/reference-audit/asset-audit.json").read_text())["input_hashes"]
    report["original_input_hashes_unchanged"] = all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest for name, digest in baseline.items())
    report["physical_tests_performed"] = []
    report["outstanding_physical_tests"] = ["Actual dimensions, lid seam and hinge axis", "Finished PA12 clearance and insertion/removal forces", "Body and especially separate-lid retention, with removable liners if needed", "Full real lid opening and earbud removal", "USB-C cable moulding clearance", "ANC Find My speaker audibility", "Front LED visibility and pairing/reset tap operation", "Qi and Apple Watch charging alignment, attachment and temperature", "Material, paint and liner compatibility with the device finish"]
    report["mesh_gate_passed"] = all(part["connected_components"] == 1 and part["boundary_edges"] == 0 and part["non_manifold_edges"] == 0 and part["inconsistently_oriented_edges"] == 0 and part["loose_vertices"] == 0 and part["degenerate_faces_below_1e-10_mm2"] == 0 and part["signed_volume_mm3"] > 0 and part["nonadjacent_triangle_overlap_candidates"] == 0 for part in report["parts"].values())
    report["surrogate_fit_gate_passed"] = all(check["volume_mm3"] < 0.00001 for check in report["closed_device_intersections"].values()) and not report["hinge_sweep"]["colliding_poses"] and all(not check["colliding_poses"] for check in insertion_results.values())
    (output / "geometry-validation.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    VALIDATION_RESULT = main()
