import argparse
import hashlib
import json
import math
import struct
import zipfile
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifest.json"
EXPECTED_DIMENSIONS = {
    "body": (75.77778, 26.9, 42.39634),
    "lid": (62.0, 26.9, 16.50365),
}


def release_files():
    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT)
        if not path.is_file() or any(part in (".git", "__pycache__") for part in relative.parts):
            continue
        if path == MANIFEST or path.name == ".DS_Store" or path.suffix in (".pyc", ".log"):
            continue
        if path.name.endswith((".blend1", ".blend2")):
            raise ValueError("Blender backups must not be included in a release")
        yield relative, path


def check_stl(path, expected):
    data = path.read_bytes()
    triangle_count = struct.unpack_from("<I", data, 80)[0]
    if not triangle_count or len(data) != 84 + 50 * triangle_count:
        raise ValueError(f"Invalid binary STL structure: {path.name}")
    minima = [float("inf")] * 3
    maxima = [float("-inf")] * 3
    for triangle in range(triangle_count):
        coordinates = struct.unpack_from("<9f", data, 96 + 50 * triangle)
        if not all(math.isfinite(value) for value in coordinates):
            raise ValueError(f"Non-finite STL coordinates: {path.name}")
        for vertex in range(3):
            for axis in range(3):
                value = coordinates[vertex * 3 + axis]
                minima[axis] = min(minima[axis], value)
                maxima[axis] = max(maxima[axis], value)
    actual = tuple(upper - lower for lower, upper in zip(minima, maxima))
    if any(abs(measured - nominal) > 0.01 for measured, nominal in zip(actual, expected)):
        raise ValueError(f"Unexpected dimensions: {path.name}: {actual}")
    return {"triangles": triangle_count, "dimensions_mm": actual}


def main():
    parser = argparse.ArgumentParser(description="Check release structure, units and recorded file hashes; not physical qualification")
    parser.add_argument("--write-manifest", action="store_true", help="Record reviewed current files after validating structure")
    args = parser.parse_args()
    required = (
        "README.md", "LICENSE.md", "THIRD_PARTY_NOTICES.md", "LICENSES/MIT.txt",
        "LICENSES/CC-BY-4.0.txt", "LICENSES/CC-BY-SA-4.0.txt",
        "models/clawd-airpods4-anc-v03.blend", "docs/QUALIFICATION.md",
        "exports/clawd-v03/qa/publication-audit.json",
        "models/clawd-airpods4-anc-v04.blend", "docs/clawd-design-v04.md",
        "exports/clawd-v04/qa/publication-audit.json",
        "exports/clawd-v04/qa/coverage-revision-validation.json",
    )
    for relative in required:
        if not (ROOT / relative).is_file():
            raise FileNotFoundError(relative)
    private_markers = ("/Users/", "/Volumes/", "@gmail.com", "@outlook.com", "AWSAccessKeyId=", "x-amz-security-token=")
    files = {}
    for relative, path in release_files():
        if any(part in (".codex", ".venv-blender-mcp", "milk-crate-2258620", "retro-gameboy-2171267") for part in relative.parts):
            raise ValueError(f"Non-public path: {relative}")
        data = path.read_bytes()
        if path != Path(__file__).resolve() and path.suffix in (".md", ".txt", ".json", ".py", ".yml"):
            text = data.decode("utf-8").lower()
            if any(marker.lower() in text for marker in private_markers):
                raise ValueError(f"Private path or credential marker in {relative}")
        if len(data) >= 50 * 1024 * 1024:
            raise ValueError(f"Oversized repository file: {relative}")
        files[str(relative)] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    meshes = {}
    for revision in ("v03", "v04"):
        directory = ROOT / f"exports/clawd-{revision}/clawd-prototype"
        for part, dimensions in EXPECTED_DIMENSIONS.items():
            filename = f"clawd-prototype-{part}-{revision}-mm.stl"
            meshes[filename] = check_stl(directory / filename, dimensions)
        with zipfile.ZipFile(directory / f"clawd-prototype-pair-{revision}-mm.3mf") as archive:
            if archive.testzip() is not None:
                raise ValueError("Invalid 3MF archive")
            model = ElementTree.fromstring(archive.read("3D/3dmodel.model"))
            namespace = {"model": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
            objects = model.findall("model:resources/model:object", namespace)
            if model.get("unit") != "millimeter" or len(objects) != 2:
                raise ValueError("3MF must contain exactly two objects in millimetres")
    if args.write_manifest:
        MANIFEST.write_text(json.dumps({"release": "v0.4.0-alpha", "design_revision": "v04", "files": files}, indent=2) + "\n")
    elif json.loads(MANIFEST.read_text())["files"] != files:
        raise ValueError("Release files differ from manifest; review changes before regenerating it")
    print(json.dumps({"file_count": len(files), "meshes": meshes, "three_mf_objects": 2, "physical_validation": "NOT PERFORMED"}, indent=2))


if __name__ == "__main__":
    main()
