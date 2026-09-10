import json
import math
import runpy
from pathlib import Path

import bpy
import numpy
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "models/clawd-airpods4-anc-v04.blend"
OUTPUT = ROOT / "exports/clawd-v04/renders"


def comparison_image(before_path, after_path, destination):
    before = bpy.data.images.load(str(before_path), check_existing=False)
    after = bpy.data.images.load(str(after_path), check_existing=False)
    if tuple(before.size) != tuple(after.size):
        raise RuntimeError("Comparison render dimensions differ")
    width, height = before.size
    before.colorspace_settings.name = "Non-Color"
    after.colorspace_settings.name = "Non-Color"
    first = numpy.empty(width * height * 4, dtype=numpy.float32)
    second = numpy.empty_like(first)
    before.pixels.foreach_get(first)
    after.pixels.foreach_get(second)
    separator = numpy.full((height, 16, 4), 0.9, dtype=numpy.float32)
    separator[:, :, 3] = 1
    pixels = numpy.concatenate((first.reshape(height, width, 4), separator, second.reshape(height, width, 4)), axis=1)
    image = bpy.data.images.new("v03 left - v04 right | coverage comparison", width=width * 2 + 16, height=height, alpha=True)
    image.colorspace_settings.name = "Non-Color"
    image.pixels.foreach_set(pixels.ravel())
    image.filepath_raw = str(destination)
    image.file_format = "PNG"
    image.save()
    for temporary in (before, after, image):
        bpy.data.images.remove(temporary)


def main(views=None):
    if not bpy.app.background or Path(bpy.data.filepath).resolve() != MODEL:
        raise RuntimeError("Open saved v04 in a separate background Blender process")
    renderer = runpy.run_path(str(ROOT / "tools/render_clawd_case.py"))
    camera, floor, device_body, device_lid = renderer["configure_studio"](revision="v04")
    scene = bpy.context.scene
    scene.cycles.samples = 40
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 1020
    scene.render.resolution_percentage = 100
    body = bpy.data.objects["CLAWD | body"]
    lid = bpy.data.objects["CLAWD | lid"]
    original_body = bpy.data.objects["ARCHIVED v03 | Clawd body before full wrap"]
    original_lid = bpy.data.objects["ARCHIVED v03 | Clawd lid before full wrap"]
    archive = bpy.data.collections["10 | ARCHIVED v03 SHELLS | NO EXPORT"]
    hardware = bpy.data.collections["09 | KEYRING HARDWARE PREVIEW | NOT FOR PRINT"]
    pads = bpy.data.collections["11 | COMPLIANT PAD PREVIEW | NOT FOR PRINT"]
    build = json.loads((ROOT / "exports/clawd-v04/qa/design-build.json").read_text())
    hinge = Vector(build["visual_model_hinge_pivot_mm"])
    shots = {
        "front": {"position": (100, -190, 110), "target": (8, -3, 21), "scale": 118, "hardware": True},
        "rear": {"position": (-100, 190, 110), "target": (0, 0, 23), "scale": 105},
        "rear-v03-baseline": {"position": (-100, 190, 110), "target": (0, 0, 23), "scale": 105, "baseline": True},
        "underside": {"position": (65, -140, -120), "target": (0, 0, 7), "scale": 98, "no_floor": True},
        "open": {"position": (100, -180, 140), "target": (0, 5, 29), "scale": 115, "angle": 110},
        "pad-seats": {"position": (95, -185, 155), "target": (0, 6, 32), "scale": 120, "angle": 105, "lift": 12, "hide_device": True}
    }
    paths = {}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name in (views or shots):
        shot = shots[name]
        baseline = shot.get("baseline", False)
        archive.hide_render = not baseline
        original_body.hide_render = not baseline
        original_lid.hide_render = not baseline
        body.hide_render = baseline
        lid.hide_render = baseline
        pads.hide_render = baseline
        hardware.hide_render = not shot.get("hardware", False)
        floor.hide_render = shot.get("no_floor", False)
        camera.location = shot["position"]
        camera.rotation_euler = (Vector(shot["target"]) - camera.location).to_track_quat("-Z", "Y").to_euler()
        camera.data.ortho_scale = shot["scale"]
        angle = shot.get("angle", 0)
        rotation = Matrix.Translation(hinge) @ Matrix.Rotation(math.radians(-angle), 4, "X") @ Matrix.Translation(-hinge)
        transform = Matrix.Translation((0, 0, shot.get("lift", 0))) @ rotation
        lid.matrix_world = transform
        for obj in pads.objects:
            obj.matrix_world = transform if obj.get("part") == "lid" else Matrix.Identity(4)
        for obj in device_body:
            obj.hide_render = shot.get("hide_device", False)
        for obj in device_lid:
            obj.hide_render = shot.get("hide_device", False)
            obj.matrix_world = rotation
        scene.render.filepath = str(OUTPUT / f"clawd-v04-{name}.png")
        bpy.context.view_layer.update()
        bpy.ops.render.render(write_still=True)
        paths[name] = scene.render.filepath
    if "rear" in paths and "rear-v03-baseline" in paths:
        destination = OUTPUT / "clawd-v04-rear-before-after.png"
        comparison_image(paths["rear-v03-baseline"], paths["rear"], destination)
        paths["rear-before-after"] = str(destination)
    return {"images": paths, "comparison_order": "v03 LEFT, v04 RIGHT", "qualification": "Actual shell geometry; colour, hardware and seated pad envelopes are illustrative. No scene save or live-session changes."}


if __name__ == "__main__":
    RENDER_RESULT = main()
