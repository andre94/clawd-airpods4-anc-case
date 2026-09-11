# Bottom-access update — 11 September 2026

The `v04-bottom-access` files replace the previous website downloads. The
original `v0.4.0-alpha` tag remains unchanged; this update does not create a tag.

## Geometry

Removed the two narrow body bridges between the USB-C opening and the side
service windows using rounded Boolean cutters:

| Side | Minimum XYZ, mm | Maximum XYZ, mm | Radius, mm |
| --- | --- | --- | --- |
| Left | −11.5, −2, −15 | −5.5, 2, 8 | 0.8 |
| Right | 5.5, −2, −15 | 11.5, 2, 8 | 0.8 |

The cuts overlap the existing windows, joining them without widening the outer
ends. The body envelope, lid and all other mesh geometry remain unchanged.
About 59.597 mm³ of material is removed. The credited visual device model is
not measured OEM CAD; visible access is not proof of real-device alignment.

## Files and checks

- [Current printable pair and GLB](../exports/v04-bottom-access/).
- [Editable source](../models/clawd-airpods4-anc-v04-bottom-access.blend).
- [Patch/export script](../tools/export_clawd_bottom_access.py).
- [Digital validation report](../exports/v04-bottom-access/validation.json).
- [Build instructions](BUILD.md) and [printing guidance](PRINTING.md).

The public source was generated from the sanitized, unanimated v04 baseline.
The body exactly matches the approved local study geometry:
`bb031bed17fe1cbfba8442a1411f668d860277779b1489c44ae3fb4ee46e9959`.
It remains one closed oriented component with positive volume, no loose vertices,
degenerate faces or nonadjacent triangle-overlap candidates. All 18 sampled
vertical rays through the two removed bridges are unobstructed.

Both STLs pass millimetre-scale round-trip checks. The 3MF has two mesh objects
and explicit millimetre units. The viewer has four meshes: body, lid and two
paint indicators; no device, pads, ring or cutters. Its combined glTF-axis bounds
are 75.78 × 59.60 × 26.90 mm.

Existing uploaded gallery renders were kept. The sites may regenerate previews
associated with replaced model files. No actual print or physical test has been
performed: check alignment, cable clearance, acoustics, charging, retention,
finish compatibility and strength before use.
