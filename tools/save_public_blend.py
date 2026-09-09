import json
import runpy
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]


def save_public_copy():
    if not bpy.app.background or not bpy.data.filepath:
        raise RuntimeError("Open a project v03 model in a separate background Blender process")
    source = Path(bpy.data.filepath).resolve()
    destination = ROOT / "models/clawd-airpods4-anc-v03.blend"
    if source.name != destination.name or destination.exists():
        raise RuntimeError("Expected v03 source and a new public destination; never overwrite either")
    if abs(bpy.context.scene.unit_settings.scale_length - 0.001) > 1e-8:
        raise RuntimeError("Expected native millimetre model coordinates")
    validator = runpy.run_path(str(ROOT / "tools/validate_clawd_case.py"))
    protected = ("CLAWD | body", "CLAWD | lid", "FIT CHECK | body", "FIT CHECK | lid")
    digests = {name: validator["geometry_digest"](bpy.data.objects[name]) for name in protected}
    removed = []
    for collection in list(bpy.data.collections):
        if collection.name.startswith(("DONOR_", "07 | ARCHIVED", "08 | ARCHIVED")):
            for obj in list(collection.objects):
                removed.append(obj.name)
                bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.collections.remove(collection)
    for obj in bpy.data.objects:
        if "DONOR" in obj.name.upper() or "source_3mf" in obj:
            raise RuntimeError("Restricted donor data remains in the public scene")
        if any(collection.name == "AIRPODS_VISUAL_REFERENCE_NOT_METROLOGY" for collection in obj.users_collection):
            obj["license"] = "CC-BY-4.0"
            obj["attribution"] = "AirPods 4 by Falah3D; see THIRD_PARTY_NOTICES.md"
        elif obj.name == "Clawd supplied STL | raw units":
            obj["license"] = "CC-BY-4.0"
            obj["attribution"] = "Simple Claude Code Mascot - Clawd by akmiller01; see THIRD_PARTY_NOTICES.md"
        else:
            obj["license"] = "CC-BY-SA-4.0 for project adaptations; upstream components retain CC-BY-4.0"
    for image in bpy.data.images:
        if image.source == "FILE":
            candidate = ROOT / "assets/reference/airpods-4/textures" / Path(image.filepath).name
            if candidate.is_file():
                image.filepath = str(candidate)
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)
    if bpy.data.libraries:
        raise RuntimeError("External linked libraries must be reviewed before redistribution")
    for name, digest in digests.items():
        if validator["geometry_digest"](bpy.data.objects[name]) != digest:
            raise RuntimeError(f"Public cleanup changed protected geometry: {name}")
    scene = bpy.context.scene
    scene["public_release"] = "v0.3.0-alpha; unvalidated prototype"
    scene["license_notice"] = "CC-BY-SA-4.0 project adaptations, CC-BY-4.0 source assets; see LICENSE.md and THIRD_PARTY_NOTICES.md"
    scene["restricted_donor_geometry_included"] = False
    scene["source_revision"] = "v03"
    scene.render.filepath = "//../docs/images/clawd-v03-preview.png"
    bpy.ops.file.pack_all()
    for image in bpy.data.images:
        if image.source == "FILE" and image.packed_file:
            image.filepath = "//../assets/reference/airpods-4/textures/" + Path(image.filepath).name
    bpy.ops.wm.save_as_mainfile(filepath=str(destination), relative_remap=False)
    audit = {
        "release": "v0.3.0-alpha",
        "source_revision": "v03",
        "geometry_sha256_unchanged": digests,
        "removed_object_count": len(removed),
        "remaining_donor_objects": 0,
        "external_linked_libraries": 0,
        "native_coordinates": "millimetres; scene scale_length 0.001",
        "physical_validation": "NOT PERFORMED",
    }
    (ROOT / "exports/clawd-v03/qa/publication-audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    return audit


if __name__ == "__main__":
    print(json.dumps(save_public_copy()))
