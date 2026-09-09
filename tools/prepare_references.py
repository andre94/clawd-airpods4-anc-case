import json
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]


def move_to_collection(obj, collection):
    for previous in tuple(obj.users_collection):
        previous.objects.unlink(obj)
    collection.objects.link(obj)


def main():
    if not bpy.app.background or bpy.data.filepath:
        raise RuntimeError("Use a fresh background Blender process, not an interactive scene")
    destination = ROOT / "models/clawd-airpods4-anc-reference-study-v01.blend"
    if destination.exists():
        raise FileExistsError("The reference scene already exists")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = "Open source references | CC BY 4.0 | NOT METROLOGY"
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 0.001
    scene.unit_settings.length_unit = "MILLIMETERS"
    character_collection = bpy.data.collections.new("CLAWD_ORIGINAL")
    scene.collection.children.link(character_collection)
    bpy.ops.wm.stl_import(filepath=str(ROOT / "assets/reference/clawd.stl"))
    character = bpy.context.object
    character.name = "Clawd supplied STL | raw units"
    character["license"] = "CC-BY-4.0"
    character["attribution"] = "Simple Claude Code Mascot - Clawd by akmiller01; see THIRD_PARTY_NOTICES.md"
    move_to_collection(character, character_collection)
    reference_collection = bpy.data.collections.new("AIRPODS_VISUAL_REFERENCE_NOT_METROLOGY")
    scene.collection.children.link(reference_collection)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(ROOT / "assets/reference/airpods-4/source/AirPods 4.fbx"), use_image_search=True)
    imported = set(bpy.data.objects) - before
    for obj in imported:
        move_to_collection(obj, reference_collection)
        obj["license"] = "CC-BY-4.0"
        obj["attribution"] = "AirPods 4 by Falah3D; see THIRD_PARTY_NOTICES.md"
        obj["metrology_warning"] = "Visual model, not measured or manufacturer CAD"
    for image in bpy.data.images:
        if image.source == "FILE":
            candidate = ROOT / "assets/reference/airpods-4/textures" / Path(image.filepath).name
            if candidate.is_file():
                image.filepath = str(candidate)
    destination.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(destination))
    print(json.dumps({"open_reference_objects": len(imported) + 1, "restricted_donor_objects": 0}))


if __name__ == "__main__":
    main()
