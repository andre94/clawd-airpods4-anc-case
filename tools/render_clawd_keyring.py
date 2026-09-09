import runpy
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "models/clawd-airpods4-anc-v03.blend"
OUTPUT = ROOT / "exports/clawd-v03/renders"


def main():
    if Path(bpy.data.filepath).resolve() != MODEL:
        raise RuntimeError("Open the saved v03 model in background Blender")
    renderer = runpy.run_path(str(ROOT / "tools/render_clawd_case.py"))
    camera, floor, device_body, device_lid = renderer["configure_studio"](revision="v03")
    scene = bpy.context.scene
    hardware = bpy.data.collections["09 | KEYRING HARDWARE PREVIEW | NOT FOR PRINT"]
    bpy.data.collections["01 | CLAWD PRINT PARTS | v03 UNVALIDATED"].hide_render = False
    bpy.data.collections["04 | FINISH PREVIEW | not extra print parts"].hide_render = False
    bpy.data.collections["05 | LOW COST FIT CHECK PAIR | unvalidated"].hide_render = True
    scene.cycles.samples = 48
    OUTPUT.mkdir(parents=True, exist_ok=True)
    views = {
        "keyring-front": {"position": (100, -190, 110), "target": (8, -3, 21), "scale": 118, "hardware": True},
        "keyring-hole-detail": {"position": (105, -135, 88), "target": (32, -8, 25.8), "scale": 32, "hardware": False},
        "keyring-detail": {"position": (105, -135, 95), "target": (42, -15, 25.8), "scale": 49, "hardware": True},
    }
    outputs = []
    for name, view in views.items():
        camera.location = view["position"]
        camera.rotation_euler = (Vector(view["target"]) - camera.location).to_track_quat("-Z", "Y").to_euler()
        camera.data.ortho_scale = view["scale"]
        hardware.hide_render = not view["hardware"]
        scene.render.filepath = str(OUTPUT / f"clawd-v03-{name}.png")
        bpy.context.view_layer.update()
        bpy.ops.render.render(write_still=True)
        outputs.append(scene.render.filepath)
    return {"images": outputs, "qualification": "Terracotta finish and brass split-ring envelopes are illustrative. The unpainted print exports contain only the plastic body and lid. No scene save or live-session changes."}


if __name__ == "__main__":
    RENDER_RESULT = main()
