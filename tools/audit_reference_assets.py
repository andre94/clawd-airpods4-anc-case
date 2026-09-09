import hashlib
import json
import struct
import xml.etree.ElementTree as ElementTree
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "assets" / "reference"
OUTPUT = ROOT / "exports" / "reference-audit"


def local_name(tag):
    return tag.rsplit("}", 1)[-1]


def stl_summary(data):
    triangle_count = struct.unpack_from("<I", data, 80)[0]
    if len(data) != 84 + triangle_count * 50:
        raise ValueError("Expected a binary STL with complete triangle records")
    minima = [float("inf")] * 3
    maxima = [float("-inf")] * 3
    for triangle_index in range(triangle_count):
        coordinates = struct.unpack_from("<9f", data, 96 + triangle_index * 50)
        for offset in range(0, 9, 3):
            for axis in range(3):
                minima[axis] = min(minima[axis], coordinates[offset + axis])
                maxima[axis] = max(maxima[axis], coordinates[offset + axis])
    return {
        "triangles": triangle_count,
        "bounds_raw": [minima, maxima],
        "dimensions_raw": [round(maximum - minimum, 6) for minimum, maximum in zip(minima, maxima)],
        "unit": "unspecified by STL; compare with source 3MF before treating as mm",
    }


def audit_package(package_path):
    destination = OUTPUT / package_path.parent.name
    destination.mkdir(parents=True, exist_ok=True)
    package = {"source": str(package_path.relative_to(ROOT)), "metadata": {}, "objects": [], "images": []}
    with zipfile.ZipFile(package_path) as archive:
        model = ElementTree.fromstring(archive.read("3D/3dmodel.model"))
        package["unit"] = model.get("unit", "millimeter")
        for child in model:
            if local_name(child.tag) == "metadata":
                package["metadata"][child.get("name")] = child.text
        settings = ElementTree.fromstring(archive.read("Metadata/model_settings.config"))
        for obj in settings.findall("object"):
            metadata = {entry.get("key"): entry.get("value") for entry in obj.findall("metadata")}
            parts = []
            for part in obj.findall("part"):
                part_metadata = {entry.get("key"): entry.get("value") for entry in part.findall("metadata")}
                parts.append({
                    "id": part.get("id"),
                    "type": part.get("subtype"),
                    "name": part_metadata.get("name"),
                    "mesh_stat": [entry.attrib for entry in part.findall("mesh_stat")],
                })
            package["objects"].append({"id": obj.get("id"), "metadata": metadata, "parts": parts})
        for filename in archive.namelist():
            if filename.startswith("Auxiliaries/Model Pictures/") or filename == "Auxiliaries/.thumbnails/thumbnail_middle.png":
                image_path = destination / Path(filename).name
                image_path.write_bytes(archive.read(filename))
                package["images"].append(str(image_path.relative_to(ROOT)))
    return package


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    report = {"input_hashes": {}, "packages": [], "stls": []}
    for path in sorted(REFERENCES.rglob("*")):
        if not path.is_file() or path.name == ".DS_Store":
            continue
        data = path.read_bytes()
        report["input_hashes"][str(path.relative_to(ROOT))] = hashlib.sha256(data).hexdigest()
        if path.suffix == ".3mf":
            report["packages"].append(audit_package(path))
        elif path.suffix == ".stl":
            report["stls"].append({"path": str(path.relative_to(ROOT)), **stl_summary(data)})
        elif path.suffix == ".zip":
            destination = OUTPUT / path.parent.name / "stls"
            destination.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(path) as archive:
                for filename in archive.namelist():
                    if filename.lower().endswith(".stl"):
                        member = archive.read(filename)
                        extracted_path = destination / Path(filename).name
                        extracted_path.write_bytes(member)
                        report["stls"].append({"path": str(extracted_path.relative_to(ROOT)), "source_zip": str(path.relative_to(ROOT)), **stl_summary(member)})
    (OUTPUT / "asset-audit.json").write_text(json.dumps(report, indent=2) + "\n")
    for package in report["packages"]:
        print(json.dumps({"package": package["source"], "units": package["unit"], "metadata": package["metadata"], "images": package["images"]}))
        for obj in package["objects"]:
            print(json.dumps({"id": obj["id"], "metadata": obj["metadata"], "part_names": sorted({part["name"] for part in obj["parts"] if part["name"]}), "part_types": {kind: sum(part["type"] == kind for part in obj["parts"]) for kind in sorted({part["type"] for part in obj["parts"]})}}))
    for stl in report["stls"]:
        print(json.dumps(stl))


if __name__ == "__main__":
    main()
