import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "exports/clawd-v01/renders"


def assign_material(obj, shader):
    obj.data.materials.clear()
    obj.data.materials.append(shader)
    for polygon in obj.data.polygons:
        polygon.material_index = 0


def display_device(target, revision="v01"):
    source_collection = bpy.data.collections["AIRPODS_VISUAL_REFERENCE_NOT_METROLOGY"]
    source_collection.hide_viewport = False
    bpy.context.view_layer.update()
    build = json.loads((ROOT / f"exports/clawd-{revision}/qa/design-build.json").read_text())
    scale = Vector(build["axis_calibration_factors"])
    body_source = bpy.data.objects["fWIbryXWNsOdjxC"]
    lid_source = bpy.data.objects["bTVaRraRjrgTKif"]
    all_points = [obj.matrix_world @ vertex.co for obj in (body_source, lid_source) for vertex in obj.data.vertices]
    minima = Vector(tuple(min(point[axis] for point in all_points) for axis in range(3)))
    maxima = Vector(tuple(max(point[axis] for point in all_points) for axis in range(3)))
    body_parts = []
    lid_parts = []
    for original in list(source_collection.objects):
        if original.type != "MESH":
            continue
        parent = original.parent
        belongs_to_lid = False
        while parent:
            if parent.name == "nJoEOlgGwcdXBHJ":
                belongs_to_lid = True
                break
            parent = parent.parent
        points = [original.matrix_world @ vertex.co for vertex in original.data.vertices]
        if not belongs_to_lid and max(point.z for point in points) > 14:
            continue
        vertices = [((point.x - (minima.x + maxima.x) / 2) * scale.x, (point.y - (minima.y + maxima.y) / 2) * scale.y, (point.z - minima.z) * scale.z + build["parameters"]["case_bottom_z"]) for point in points]
        mesh = bpy.data.meshes.new(f"Display {original.name}")
        mesh.from_pydata(vertices, [], [tuple(polygon.vertices) for polygon in original.data.polygons])
        mesh.update()
        copy = bpy.data.objects.new(f"DISPLAY ONLY | {'lid' if belongs_to_lid else 'body'} | {original.name}", mesh)
        target.objects.link(copy)
        for shader in original.data.materials:
            if shader:
                copy.data.materials.append(shader)
        if not copy.data.materials:
            copy.data.materials.append(bpy.data.materials["White device surrogate"])
        for polygon, source_polygon in zip(copy.data.polygons, original.data.polygons):
            polygon.material_index = min(source_polygon.material_index, len(copy.data.materials) - 1)
            polygon.use_smooth = source_polygon.use_smooth
        copy["export"] = False
        copy["note"] = "Supplied FBX display reconstruction; not printed or used for physical validation"
        (lid_parts if belongs_to_lid else body_parts).append(copy)
    source_collection.hide_viewport = True
    return body_parts, lid_parts


def configure_studio(revision="v01"):
    scene = bpy.context.scene
    previous = bpy.data.collections.get("06 | STUDIO AND SOURCE DEVICE DISPLAY | no export")
    if previous:
        for obj in list(previous.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(previous)
    target = bpy.data.collections.new("06 | STUDIO AND SOURCE DEVICE DISPLAY | no export")
    scene.collection.children.link(target)
    for obj in scene.objects:
        if obj.name.startswith("REFERENCE | calibrated"):
            obj.hide_render = True
    bpy.data.collections["02 | CALIBRATED DEVICE SURROGATES | display only"].hide_viewport = True
    body_parts, lid_parts = display_device(target, revision=revision)
    camera_data = bpy.data.cameras.new("Presentation camera")
    camera = bpy.data.objects.new("Presentation camera", camera_data)
    target.objects.link(camera)
    scene.camera = camera
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 106
    camera_data.clip_end = 2000
    camera_data.clip_start = 0.1
    for name, location, power, size in (("Key softbox", (-85, -110, 150), 250000, 110), ("Fill softbox", (95, -50, 85), 95000, 95), ("Rear softbox", (45, 90, 140), 210000, 85)):
        light_data = bpy.data.lights.new(name, "AREA")
        light_data.energy = power
        light_data.shape = "DISK"
        light_data.size = size
        light = bpy.data.objects.new(name, light_data)
        target.objects.link(light)
        light.location = location
        light.rotation_euler = (Vector((0, 0, 22)) - light.location).to_track_quat("-Z", "Y").to_euler()
    floor_mesh = bpy.data.meshes.new("Studio floor")
    floor_mesh.from_pydata([(-300, -300, -8.08), (300, -300, -8.08), (300, 300, -8.08), (-300, 300, -8.08)], [], [(0, 1, 2, 3)])
    floor = bpy.data.objects.new("Studio floor | not a print part", floor_mesh)
    target.objects.link(floor)
    floor_material = bpy.data.materials.new("Warm porcelain backdrop")
    floor_material.use_nodes = True
    floor_material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.56, 0.52, 0.46, 1)
    floor_material.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.85
    floor.data.materials.append(floor_material)
    world = bpy.data.worlds.new("Clawd neutral studio")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.62, 0.65, 0.7, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35
    scene.world = world
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 6
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 1300
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    return camera, floor, body_parts, lid_parts


def render_views(names, save_scene=False, revision="v01"):
    expected = ROOT / f"models/clawd-airpods4-anc-{revision}.blend"
    if Path(bpy.data.filepath).resolve() != expected:
        raise RuntimeError("Open the selected project revision before rendering")
    output = ROOT / f"exports/clawd-{revision}/renders"
    output.mkdir(parents=True, exist_ok=True)
    camera, floor, device_body, device_lid = configure_studio(revision=revision)
    scene = bpy.context.scene
    body = bpy.data.objects["CLAWD | body"]
    lid = bpy.data.objects["CLAWD | lid"]
    build = json.loads((ROOT / f"exports/clawd-{revision}/qa/design-build.json").read_text())
    hinge = Vector(build["visual_model_hinge_pivot_mm"])
    shots = {
        "front": {"position": (100, -190, 110), "target": (0, 0, 21), "scale": 105},
        "rear": {"position": (-100, 190, 110), "target": (0, 0, 23), "scale": 105},
        "open": {"position": (100, -180, 140), "target": (0, 5, 29), "scale": 115, "angle": 110},
        "exploded": {"position": (95, -180, 115), "target": (0, 0, 33), "scale": 128, "lift": 23},
        "underside": {"position": (65, -140, -120), "target": (0, 0, 7), "scale": 98, "no_floor": True},
        "fit-check": {"position": (95, -180, 115), "target": (0, 0, 32), "scale": 110, "lift": 21, "fit": True}
    }
    paths = []
    for name in names:
        specification = shots[name]
        camera.location = specification["position"]
        camera.rotation_euler = (Vector(specification["target"]) - camera.location).to_track_quat("-Z", "Y").to_euler()
        camera.data.ortho_scale = specification["scale"]
        floor.hide_render = specification.get("no_floor", False)
        floor.location.z = 8 if specification.get("fit") else 0
        transform = Matrix.Identity(4)
        if specification.get("angle"):
            transform = Matrix.Translation(hinge) @ Matrix.Rotation(math.radians(-specification["angle"]), 4, "X") @ Matrix.Translation(-hinge)
        if specification.get("lift"):
            transform = Matrix.Translation((0, 0, specification["lift"]))
        lid.matrix_world = transform
        for obj in device_lid:
            obj.matrix_world = transform if specification.get("angle") else Matrix.Identity(4)
        scene.collection.children[f"01 | CLAWD PRINT PARTS | {revision} UNVALIDATED"].hide_render = specification.get("fit", False)
        scene.collection.children["04 | FINISH PREVIEW | not extra print parts"].hide_render = specification.get("fit", False)
        scene.collection.children["05 | LOW COST FIT CHECK PAIR | unvalidated"].hide_render = not specification.get("fit", False)
        bpy.data.objects["FIT CHECK | lid"].matrix_world = transform if specification.get("fit") else Matrix.Identity(4)
        scene.render.filepath = str(output / f"clawd-{revision}-{name}.png")
        bpy.ops.render.render(write_still=True)
        paths.append(scene.render.filepath)
    lid.matrix_world = Matrix.Identity(4)
    for obj in device_lid:
        obj.matrix_world = Matrix.Identity(4)
    bpy.data.objects["FIT CHECK | lid"].matrix_world = Matrix.Identity(4)
    scene.collection.children[f"01 | CLAWD PRINT PARTS | {revision} UNVALIDATED"].hide_render = False
    scene.collection.children["04 | FINISH PREVIEW | not extra print parts"].hide_render = False
    scene.collection.children["05 | LOW COST FIT CHECK PAIR | unvalidated"].hide_render = True
    floor.hide_render = False
    floor.location.z = 0
    camera.location = shots["front"]["position"]
    camera.rotation_euler = (Vector(shots["front"]["target"]) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.ortho_scale = shots["front"]["scale"]
    if save_scene:
        for area in bpy.context.screen.areas if bpy.context.screen else []:
            if area.type == "VIEW_3D":
                area.spaces.active.shading.type = "SOLID"
                area.spaces.active.shading.color_type = "MATERIAL"
                area.spaces.active.region_3d.view_perspective = "CAMERA"
        bpy.ops.file.pack_all()
        bpy.ops.wm.save_as_mainfile(filepath=str(expected))
    return {"renders": paths, "render_note": "Color and optional black eye finish are illustrative; supplier finish is not specified"}
