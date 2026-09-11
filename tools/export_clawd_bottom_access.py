import json
import runpy
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[1]
REVISION = "v04-bottom-access"
BASELINE_DIGEST = "21560813a069023961eba6db17c5ca5f40aa8737387f55ef79695ae24fd2e86d"
APPROVED_DIGEST = "bb031bed17fe1cbfba8442a1411f668d860277779b1489c44ae3fb4ee46e9959"


def main():
    destination = ROOT / "models" / f"clawd-airpods4-anc-{REVISION}.blend"
    output = ROOT / "exports" / REVISION
    if destination.exists():
        raise RuntimeError("Refusing to overwrite the prepared model")
    if abs(bpy.context.scene.unit_settings.scale_length - 0.001) > 1e-8:
        raise RuntimeError("Expected millimetre model coordinates")
    if bpy.data.actions or bpy.data.libraries:
        raise RuntimeError("Expected unanimated, self-contained public source")
    if any("DONOR" in obj.name for obj in bpy.data.objects):
        raise RuntimeError("Restricted donor geometry must not be redistributed")
    builder = runpy.run_path(str(ROOT / "tools/build_clawd_case.py"))
    validator = runpy.run_path(str(ROOT / "tools/validate_clawd_case.py"))
    exporter = runpy.run_path(str(ROOT / "tools/export_clawd_case.py"))
    body = bpy.data.objects["CLAWD | body"]
    lid = bpy.data.objects["CLAWD | lid"]
    before = validator["mesh_audit"](body)
    if before["geometry_sha256"] != BASELINE_DIGEST:
        raise RuntimeError("Body is not the approved public v04 baseline")
    protected = {
        obj.name: validator["geometry_digest"](obj)
        for obj in bpy.context.scene.objects
        if obj.type == "MESH" and obj != body
    }
    cutters = bpy.data.collections.new("14 | BOTTOM ACCESS CUTTERS | NO EXPORT")
    bpy.context.scene.collection.children.link(cutters)
    for side, minimum_x, maximum_x in (
        ("left", -11.5, -5.5),
        ("right", 5.5, 11.5),
    ):
        cutter = builder["box"](
            f"CUT | bottom access | {side} bridge",
            (minimum_x, -2.0, -15.0),
            (maximum_x, 2.0, 8.0),
            cutters,
            0.8,
        )
        cutter["export"] = False
        builder["boolean"](body, cutter)
    builder["clean_mesh"](body)
    builder["finalize_print_mesh"](body)
    after = validator["mesh_audit"](body)
    if after["geometry_sha256"] != APPROVED_DIGEST:
        raise RuntimeError("Export body differs from the approved bottom-access study")
    errors = (
        "boundary_edges",
        "non_manifold_edges",
        "inconsistently_oriented_edges",
        "loose_vertices",
        "degenerate_faces_below_1e-10_mm2",
        "nonadjacent_triangle_overlap_candidates",
    )
    assert after["connected_components"] == 1
    assert after["signed_volume_mm3"] > 0
    assert all(after[key] == 0 for key in errors)
    assert all(
        validator["geometry_digest"](bpy.data.objects[name]) == digest
        for name, digest in protected.items()
    )
    surface = validator["tree"](body)
    probes = [
        surface.ray_cast(Vector((horizontal, depth, -20)), Vector((0, 0, 1)), 28)[0]
        is None
        for horizontal in (-9.5, -8.5, -7.5, 7.5, 8.5, 9.5)
        for depth in (-1.5, 0.0, 1.5)
    ]
    assert all(probes)
    cutters.hide_viewport = True
    cutters.hide_render = True
    scene = bpy.context.scene
    scene["source_revision"] = REVISION
    scene["public_release"] = "2026-09-11 bottom-access update; physically unvalidated"
    scene["revision_scope"] = (
        "Remove two bottom bridges to join USB-C and side service windows. "
        "All other mesh geometry remains unchanged from v04."
    )
    body["bottom_access"] = scene["revision_scope"]
    body["source_parameters"] = "tools/export_clawd_bottom_access.py"
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(destination), compress=True)
    items = []
    round_trips = {}
    for name, obj, inverted in (("body", body, False), ("lid", lid, True)):
        vertices, triangles = exporter["export_geometry"](obj, invert=inverted)
        path = output / f"clawd-prototype-{name}-{REVISION}-mm.stl"
        exporter["save_stl"](path, vertices, triangles, revision="v04-bottom")
        dimensions = [
            max(vertex[axis] for vertex in vertices)
            - min(vertex[axis] for vertex in vertices)
            for axis in range(3)
        ]
        round_trips[name] = exporter["check_round_trip"](path, dimensions)
        items.append((name, vertices, triangles))
    pair = output / f"clawd-prototype-pair-{REVISION}-mm.3mf"
    exporter["save_3mf"](pair, items, 45.0, revision=REVISION)
    pair_check = exporter["check_3mf"](pair, items)
    viewer_scene = bpy.data.scenes.new("Bottom-access viewer in metres")
    viewer_scene.unit_settings.system = "METRIC"
    viewer_scene.unit_settings.scale_length = 1.0
    sources = [body, lid] + [
        obj for obj in scene.objects
        if obj.name.startswith("PREVIEW ONLY | black paint inside eye")
    ]
    assert len(sources) == 4
    for original in sources:
        mesh = original.data.copy()
        mesh.transform(Matrix.Scale(0.001, 4) @ original.matrix_world)
        duplicate = bpy.data.objects.new(original.name, mesh)
        viewer_scene.collection.objects.link(duplicate)
    bpy.context.window.scene = viewer_scene
    viewer = output / f"clawd-airpods4-anc-{REVISION}-viewer.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(viewer),
        export_format="GLB",
        use_active_scene=True,
        export_animations=False,
        export_extras=False,
        export_cameras=False,
        export_lights=False,
    )
    report = {
        "revision": REVISION,
        "baseline": "GitHub v0.4.0-alpha; no new GitHub release created",
        "before": before,
        "after": after,
        "approved_study_geometry_match": True,
        "other_mesh_geometry_unchanged": True,
        "bridge_access_probes_passed": sum(probes),
        "stl_round_trips": round_trips,
        "three_mf_check": pair_check,
        "viewer_mesh_count": len(sources),
        "viewer_units": "metres",
        "physical_tests_performed": [],
    }
    (output / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    RESULT = main()
