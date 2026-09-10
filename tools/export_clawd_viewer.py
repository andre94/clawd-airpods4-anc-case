import json
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "models/clawd-airpods4-anc-v04.blend"
OUTPUT = ROOT / "exports/clawd-v04/viewer/clawd-airpods4-anc-v04-viewer.glb"


def main():
    if not bpy.app.background or Path(bpy.data.filepath).resolve() != MODEL:
        raise RuntimeError("Open the public v04 model in background Blender")
    if abs(bpy.context.scene.unit_settings.scale_length - 0.001) > 1e-8:
        raise RuntimeError("Expected millimetre source coordinates")
    if OUTPUT.exists():
        raise FileExistsError("Viewer already exists; preserve reviewed deliverables")
    names = (
        "CLAWD | body", "CLAWD | lid",
        "PREVIEW ONLY | black paint inside eye",
        "PREVIEW ONLY | black paint inside eye.001",
    )
    originals = [bpy.data.objects[name] for name in names]
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    scene = bpy.data.scenes.new("Public viewer | metres | no device or hardware")
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    bpy.context.window.scene = scene
    for original in originals:
        duplicate = original.copy()
        duplicate.data = original.data.copy()
        duplicate.parent = None
        duplicate.matrix_world = Matrix.Scale(0.001, 4) @ original.matrix_world
        for key in list(duplicate.keys()):
            del duplicate[key]
        scene.collection.objects.link(duplicate)
        duplicate.hide_viewport = False
        duplicate.hide_render = False
        duplicate.hide_set(False)
        duplicate.select_set(True)
    bpy.context.view_layer.update()
    bounds = [obj.matrix_world @ Vector(corner) for obj in scene.objects for corner in obj.bound_box]
    dimensions = [(max(point[axis] for point in bounds) - min(point[axis] for point in bounds)) * 1000 for axis in range(3)]
    if any(abs(actual - expected) > 0.01 for actual, expected in zip(dimensions, (75.77778, 26.9, 59.6))):
        raise RuntimeError(f"Unexpected viewer dimensions: {dimensions}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(OUTPUT), export_format="GLB", use_selection=True, use_active_scene=True,
                              export_yup=True, export_animations=False, export_extras=False,
                              export_cameras=False, export_lights=False)
    report = {"mesh_objects": 4, "gltf_units": "metres", "source_dimensions_mm": dimensions,
              "contents": list(names), "excluded": ["device", "ring", "pads", "cutters", "references"],
              "qualification": "Visualization only; use STL/3MF for printing. Physical validation NOT PERFORMED"}
    (OUTPUT.parent / "viewer-validation.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    print(json.dumps(main()))
