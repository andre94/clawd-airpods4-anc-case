# Build and edit

## Requirements

- Blender 5.2.1 LTS, including its Python API and FBX importer.
- Python 3.10+ for the orchestration script; standard library only.
- Source files included under `assets/reference/`, with CC BY 4.0 attribution.

Codex, Claude Code, Blender MCP, cloud credentials and a network connection are
not needed after downloading the repository. No restricted donor case is used.

## Rebuild without overwriting the downloaded release

```sh
python3 tools/rebuild.py --blender /path/to/blender --output /path/to/new-empty-build
```

On macOS, the Blender executable may be
`/Applications/Blender.app/Contents/MacOS/Blender`. The output path must not exist.
The command copies only credited source assets, Python tools and JSON parameters
to a new build directory, then starts separate background Blender processes.
It does not reset an interactive Blender scene or overwrite the release blend.

The sequence is:

1. Import the Clawd STL and AirPods FBX only; save a millimetre reference scene.
2. Hash the included inputs for later integrity checks.
3. Build the v01 cover from its JSON parameters and the source envelopes.
4. Rebuild the lid with the v02 robust pixel lettering.
5. Add the v03 diagonal keyring bore and run its digital validation/export gates.

Final outputs are in the new build's `models/` and `exports/clawd-v03/` folders.
The reconstruction can differ at the byte/triangulation level between Blender
versions; geometry, dimensions and validation results matter, not a promise of
bit-identical `.blend` or mesh files. A build success is not physical validation.

### Verified clean rebuild

On 9 September 2026, a clean rebuild using Blender 5.2.1 LTS (build
`9e2066aef7ef`) completed all digital gates using only the included CC BY
reference assets. Both final prototype STLs were byte-identical to the v03
release meshes. See [rebuild-validation.json](../exports/clawd-v03/qa/rebuild-validation.json)
for the recorded SHA-256 values. This result applies to that tested environment;
it does not promise identical results across Blender versions or physical fit.

## Parameter dependencies

- `models/clawd-v01-parameters.json`: source envelope dimensions, cavity offset,
  main body, openings, seam, reliefs and initial construction.
- `models/clawd-v02-parameters.json`: robust rear lettering revision.
- `models/clawd-v03-parameters.json`: final keyring bore and reference hardware.

Shared fields repeated in later files document the inherited design; changing
only a repeated v03 cavity field does **not** rebuild the v01 cavity with that
new value. Update the construction-stage parameter file and keep later metadata
consistent, then rebuild all stages. The pipeline is a construction history,
not yet a unified live-parametric CAD application.

The pixel lettering tool currently supports the lowercase characters in
`andreabalbo.com` only. Other text needs suitable glyph definitions and a width,
wall and non-manifold-contact review. Engraving dimensions must remain compatible
with the lid and the printer's feature limits.

## Blender collections

`01` contains the two final print parts. `02` is the calibrated visual surrogate;
`03` holds editable masters and cutters; `04` is finish preview; `05` is the
simplified fit-check pair, not the full Clawd prototype. Studio objects and
keyring hardware are presentation-only. Upstream source collections retain
their own CC BY license metadata. Restricted donor meshes are absent.

## Renders

To regenerate the three v03 keyring views from a rebuilt model:

```sh
/path/to/blender --background /path/to/new-empty-build/models/clawd-airpods4-anc-v03.blend --python /path/to/new-empty-build/tools/render_clawd_keyring.py
```

Only body/lid print meshes should be exported for manufacture. Do not export all
scene objects. Mesh exports are millimetres; OBJ/STL tools may otherwise assume
metres. Do not change scene unit scale or apply another 1000× conversion blindly.
