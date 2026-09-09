# Third-party notices and provenance

Source pages and license links checked on 9 September 2026. Attribution is not
an assertion that the original uploaders control every depicted brand right.

## Clawd silhouette — akmiller01

- Work: [Simple Claude Code Mascot - Clawd](https://www.printables.com/model/1655582-simple-claude-code-mascot-clawd).
- Author: [akmiller01](https://www.printables.com/@akmiller01_232084).
- License: [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/).
- Original included at `assets/reference/clawd.stl` and in the `CLAWD_ORIGINAL`
  collection of the editable assembly.
- Provenance check: the original local file's download-origin URL exactly
  matches the target of the `clawd` STL download button on that model's Files
  page. It is the 6,284-byte file, not the separate `clawd_singlecolor` variant.
- Modifications: extracted and proportionally adapted silhouette, new depth,
  rounded edges, split body/lid, cavity and service cuts, rebuilt eye recesses,
  custom rear lettering and diagonal keyring bore.

## AirPods 4 visual reference — Falah3D

- Work: [AirPods 4](https://sketchfab.com/3d-models/airpods-4-e44730974131402eb496352cab19c82e).
- Author: [Falah3D / 3dFalah](https://sketchfab.com/3dFalah).
- License: [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/).
- Original FBX and textures are included under `assets/reference/airpods-4/`;
  imported objects are in `AIRPODS_VISUAL_REFERENCE_NOT_METROLOGY`.
- Identification evidence: matching title, original FBX format, 16 February
  2026 file date, approximately 7 MB source bundle and the published 54.3k
  vertices / 99.2k triangles (local import: 54,281 / 99,248). A fresh archive
  byte-for-byte comparison was not available because the browser blocked its
  download. This identification is documented rather than presented as a
  verified upstream checksum.
- Modifications: close the visual lid pose; calibrate overall dimensions to
  published nominal dimensions; derive convex body/lid envelopes and offset
  cavities; position and re-material selected geometry for illustrative renders.
- This is not Apple engineering CAD, metrology, a fit guarantee or certification.

## Studied but excluded — Generic Makerspace

The private reference study also inspected *Milk Crate Airpods 4 Case* and
*Retro Gameboy Airpods 4 Case* by Generic Makerspace. Both supplied 3MF files
declare **Standard Digital File License**, not an open license.

Those 3MF files, STL archives, extracted donor meshes, reference-study blend,
creator images and slicer profiles are **not included** here. Donor body/lid
objects are removed from the public Blender copy. The public reconstruction
imports only the two CC BY assets above; no donor package is required. The
cover's cavity is derived from the credited AirPods visual reference, not from
the restricted case meshes.

## Tools and brand names

Blender is separately licensed software. Its source, binaries and the Blender
Lab MCP server are not vendored here. The project uses Blender's Python API;
the optional MCP connection is a development convenience, not a build dependency.

Clawd is a Claude Code mascot reference. This is unofficial fan work, not
affiliated with or endorsed by Anthropic or Apple. Project licenses do not
grant rights in their names, trademarks or other rights outside our control.

Suggested credit when sharing an image or adaptation:

> Clawd AirPods 4 ANC Case by Andrea Balbo, CC BY-SA 4.0. Adapted from
> “Simple Claude Code Mascot - Clawd” by akmiller01 (CC BY 4.0); AirPods visual
> reference by Falah3D (CC BY 4.0). Unofficial, physically unvalidated prototype.

Include the source and license links above with that credit, and identify your
own changes. Reference-only hardware and device geometry are not print parts.
