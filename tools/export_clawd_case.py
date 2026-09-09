import hashlib
import json
import math
import runpy
import struct
import xml.etree.ElementTree as ElementTree
import zipfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "exports/clawd-v01"
CORE_NAMESPACE = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"


def export_geometry(obj, invert=False):
    rotation = Matrix.Rotation(math.pi, 4, "X") if invert else Matrix.Identity(4)
    vertices = [rotation @ obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    lowest = min(vertex.z for vertex in vertices)
    vertices = [Vector((vertex.x, vertex.y, vertex.z - lowest)) for vertex in vertices]
    obj.data.calc_loop_triangles()
    triangles = [tuple(triangle.vertices) for triangle in obj.data.loop_triangles]
    return vertices, triangles


def save_stl(path, vertices, triangles, revision="v01"):
    header = f"Clawd {revision} UNVALIDATED FIT PROTOTYPE | units mm | no auto scaling".encode("ascii")
    with path.open("wb") as output:
        output.write(header.ljust(80, b" "))
        output.write(struct.pack("<I", len(triangles)))
        for triangle in triangles:
            points = [vertices[index] for index in triangle]
            normal = (points[1] - points[0]).cross(points[2] - points[0]).normalized()
            output.write(struct.pack("<12fH", *normal, *(coordinate for point in points for coordinate in point), 0))


def save_3mf(path, items, translation, revision="v01"):
    ElementTree.register_namespace("", CORE_NAMESPACE)
    model = ElementTree.Element(f"{{{CORE_NAMESPACE}}}model", {"unit": "millimeter", "{http://www.w3.org/XML/1998/namespace}lang": "en-US"})
    for name, value in {"Title": f"Clawd {revision} - UNVALIDATED FIT PROTOTYPE", "Description": "Two separate shells. Digital validation only. Finished-part fit, retention and charging require physical qualification. No automatic scaling.", "Application": "Project-local Blender MCP design workflow", "ReleaseStatus": "NOT FOR FINAL PRODUCTION"}.items():
        ElementTree.SubElement(model, f"{{{CORE_NAMESPACE}}}metadata", {"name": name}).text = value
    resources = ElementTree.SubElement(model, f"{{{CORE_NAMESPACE}}}resources")
    build = ElementTree.SubElement(model, f"{{{CORE_NAMESPACE}}}build")
    for index, (name, vertices, triangles) in enumerate(items, 1):
        obj = ElementTree.SubElement(resources, f"{{{CORE_NAMESPACE}}}object", {"id": str(index), "type": "model", "name": name})
        mesh = ElementTree.SubElement(obj, f"{{{CORE_NAMESPACE}}}mesh")
        vertex_list = ElementTree.SubElement(mesh, f"{{{CORE_NAMESPACE}}}vertices")
        for vertex in vertices:
            ElementTree.SubElement(vertex_list, f"{{{CORE_NAMESPACE}}}vertex", {axis: format(vertex[coordinate], ".9g") for coordinate, axis in enumerate(("x", "y", "z"))})
        triangle_list = ElementTree.SubElement(mesh, f"{{{CORE_NAMESPACE}}}triangles")
        for triangle in triangles:
            ElementTree.SubElement(triangle_list, f"{{{CORE_NAMESPACE}}}triangle", {f"v{coordinate + 1}": str(vertex) for coordinate, vertex in enumerate(triangle)})
        offset = -translation if index == 1 else translation
        ElementTree.SubElement(build, f"{{{CORE_NAMESPACE}}}item", {"objectid": str(index), "transform": f"1 0 0 0 1 0 0 0 1 {offset} 0 0"})
    content_types = '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>'
    relationships = '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", relationships)
        archive.writestr("3D/3dmodel.model", ElementTree.tostring(model, encoding="utf-8", xml_declaration=True))


def check_round_trip(path, expected_dimensions):
    before = set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=str(path), global_scale=1, use_scene_unit=False)
    imported = list(set(bpy.data.objects) - before)
    if len(imported) != 1:
        raise ValueError("Expected one imported solid per STL")
    obj = imported[0]
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    dimensions = [max(vertex.co[axis] for vertex in mesh.verts) - min(vertex.co[axis] for vertex in mesh.verts) for axis in range(3)]
    check = {"dimensions_mm": dimensions, "non_manifold_edges": sum(not edge.is_manifold for edge in mesh.edges), "boundary_edges": sum(edge.is_boundary for edge in mesh.edges), "degenerate_faces": sum(face.calc_area() < 1e-10 for face in mesh.faces), "signed_volume_mm3": mesh.calc_volume(signed=True), "scale_matches_within_0_001_mm": all(abs(actual - expected) < 0.001 for actual, expected in zip(dimensions, expected_dimensions))}
    mesh.free()
    data = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.meshes.remove(data)
    if check["non_manifold_edges"] or check["degenerate_faces"] or check["signed_volume_mm3"] <= 0 or not check["scale_matches_within_0_001_mm"]:
        raise ValueError(f"STL round-trip failed: {path.name}: {check}")
    return check


def check_3mf(path, expected_items):
    with zipfile.ZipFile(path) as archive:
        bad_member = archive.testzip()
        if bad_member:
            raise ValueError(f"Corrupt 3MF entry: {bad_member}")
        root = ElementTree.fromstring(archive.read("3D/3dmodel.model"))
        namespace = {"m": CORE_NAMESPACE}
        objects = root.findall("m:resources/m:object", namespace)
        if root.get("unit") != "millimeter" or len(objects) != len(expected_items):
            raise ValueError("3MF units or object count mismatch")
        counts = []
        for obj, expected in zip(objects, expected_items):
            vertex_count = len(obj.findall("m:mesh/m:vertices/m:vertex", namespace))
            triangle_count = len(obj.findall("m:mesh/m:triangles/m:triangle", namespace))
            if vertex_count != len(expected[1]) or triangle_count != len(expected[2]):
                raise ValueError("3MF mesh count mismatch")
            counts.append({"name": obj.get("name"), "vertices": vertex_count, "triangles": triangle_count})
        return {"unit": root.get("unit"), "objects": counts, "zip_crc_check_passed": True}


def main():
    if Path(bpy.data.filepath).resolve() != (ROOT / "models/clawd-airpods4-anc-v01.blend").resolve():
        raise RuntimeError("Only export the validated project v01 model")
    report = json.loads((OUTPUT / "qa/geometry-validation.json").read_text())
    if not report["mesh_gate_passed"] or not report["surrogate_fit_gate_passed"] or not report["original_input_hashes_unchanged"]:
        raise RuntimeError("Export requires passing digital geometry checks; physical release remains blocked")
    digest_function = runpy.run_path(str(ROOT / "tools/validate_clawd_case.py"))["geometry_digest"]
    if report["parameters_sha256"] != hashlib.sha256((ROOT / "models/clawd-v01-parameters.json").read_bytes()).hexdigest():
        raise RuntimeError("Parameters changed after validation; rebuild and revalidate before exporting")
    for name, part in report["parts"].items():
        if part["geometry_sha256"] != digest_function(bpy.data.objects[name]):
            raise RuntimeError(f"Geometry changed after validation: {name}")
    results = {"release_status": "UNVALIDATED FIT PROTOTYPE - NOT FINAL PRODUCTION", "stl_units": "mm by convention; select mm and 100% scale in the printer uploader", "three_mf_units": "millimeter explicitly encoded", "files": {}, "round_trip": {}, "three_mf_validation": {}}
    for folder, prefix, spacing in (("clawd-prototype", "CLAWD", 45), ("fit-check", "FIT CHECK", 32)):
        destination = OUTPUT / folder
        destination.mkdir(parents=True, exist_ok=True)
        items = []
        for part in ("body", "lid"):
            obj = bpy.data.objects[f"{prefix} | {part}"]
            vertices, triangles = export_geometry(obj, invert=part == "lid")
            path = destination / f"{folder}-{part}-v01-mm.stl"
            save_stl(path, vertices, triangles)
            results["round_trip"][str(path.relative_to(OUTPUT))] = check_round_trip(path, report["parts"][obj.name]["dimensions_mm"])
            results["files"][str(path.relative_to(OUTPUT))] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size, "dimensions_mm": report["parts"][obj.name]["dimensions_mm"], "quantity": 1}
            items.append((f"{prefix} {part} - UNVALIDATED v01", vertices, triangles))
        pair_path = destination / f"{folder}-pair-v01-mm.3mf"
        save_3mf(pair_path, items, spacing)
        results["three_mf_validation"][str(pair_path.relative_to(OUTPUT))] = check_3mf(pair_path, items)
        results["files"][str(pair_path.relative_to(OUTPUT))] = {"sha256": hashlib.sha256(pair_path.read_bytes()).hexdigest(), "bytes": pair_path.stat().st_size, "part_count": 2, "quantity": "one body and one lid; do not additionally print duplicate STL files"}
    (OUTPUT / "qa/export-validation.json").write_text(json.dumps(results, indent=2) + "\n")
    return results


if __name__ == "__main__":
    EXPORT_RESULT = main()
