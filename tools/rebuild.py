import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(command):
    print("Running:", " ".join(str(part) for part in command), flush=True)
    subprocess.run([str(part) for part in command], check=True)


def main():
    parser = argparse.ArgumentParser(description="Rebuild the v03 prototype in a new directory")
    parser.add_argument("--blender", required=True, help="Blender executable path or command")
    parser.add_argument("--output", required=True, type=Path, help="New, nonexistent build directory")
    args = parser.parse_args()
    blender = shutil.which(args.blender)
    if blender is None:
        raise FileNotFoundError("Blender executable was not found")
    output = args.output.expanduser().resolve()
    if output.exists():
        raise FileExistsError("Choose a new output directory; existing work is never overwritten")
    if output == ROOT or ROOT in output.parents:
        raise ValueError("Use a build directory outside the source repository")
    output.mkdir(parents=True)
    shutil.copytree(ROOT / "assets", output / "assets", copy_function=shutil.copyfile)
    (output / "tools").mkdir()
    (output / "models").mkdir()
    for source in (ROOT / "tools").glob("*.py"):
        shutil.copyfile(source, output / "tools" / source.name)
    for source in (ROOT / "models").glob("*-parameters.json"):
        shutil.copyfile(source, output / "models" / source.name)
    for name in ("LICENSE.md", "THIRD_PARTY_NOTICES.md"):
        shutil.copyfile(ROOT / name, output / name)
    shutil.copytree(ROOT / "LICENSES", output / "LICENSES", copy_function=shutil.copyfile)
    run([blender, "--background", "--factory-startup", "--python-exit-code", "1", "--python", output / "tools/prepare_references.py"])
    run([sys.executable, output / "tools/audit_reference_assets.py"])
    stages = (
        ("clawd-airpods4-anc-reference-study-v01.blend", "build_clawd_case.py"),
        ("clawd-airpods4-anc-v01.blend", "revise_clawd_lid.py"),
        ("clawd-airpods4-anc-v02.blend", "add_clawd_keyring.py"),
    )
    for baseline, script in stages:
        run([blender, "--background", output / "models" / baseline, "--python-exit-code", "1", "--python", output / "tools" / script])
    report = json.loads((output / "exports/clawd-v03/qa/geometry-validation.json").read_text())
    if not all(report.get(key) for key in ("mesh_gate_passed", "surrogate_fit_gate_passed", "original_input_hashes_unchanged")):
        raise RuntimeError("The final digital validation gates did not pass")
    print(json.dumps({"output": str(output), "digital_gates_passed": True, "physical_validation": "NOT PERFORMED"}))


if __name__ == "__main__":
    main()
