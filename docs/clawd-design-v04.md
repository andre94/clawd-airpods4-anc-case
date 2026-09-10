# Clawd AirPods 4 ANC — v04 coverage and pad-retention prototype

10 September 2026. **Unvalidated physical prototype, not a production release.**

## Decision

The concern about the separate top cap is justified: v03 had a nominal
0.35 mm clearance cavity, a broad rear opening and no defined retention
hardware. Covering more of the device improves enclosure and provides more
supported contact area, but adding rigid material alone does not create grip.

The linked [Spigen Rugged Armor listing](https://www.amazon.it/dp/B0BC2B91VF),
checked on 10 September 2026, describes a two-piece **TPU** cover for **AirPods
Pro 2**, not a rigid PA12 cover for AirPods 4. Its fuller coverage is a useful
reference, but its dimensions and flexible fit cannot be copied directly.
The Clawd target remains **AirPods 4 with ANC**, using the existing calibrated
50.1 × 21.2 × 46.2 mm visual surrogate, not measured OEM CAD.

v04 keeps the two-shell architecture and the stock device hinge. It adds
fuller wrap-around coverage and deliberately specifies separate soft pads
instead of pretending that a loose hard-plastic cap will retain itself.

## Geometry changes

| Feature | v04 change |
| --- | --- |
| Lid | Extends the rear skirt outside the local hinge region; front, roof and side coverage remain |
| Rear body | Restores material outside the local hinge window, then clears the actual planned opening motion |
| Rear hinge window | 20 mm central construction width instead of a full-width cut; additional shaped motion clearance remains |
| Front | Bounded 10 × 7 mm rounded LED/pairing window, centred at Z 28.3 mm; a solid bridge now runs above it |
| Bottom | 14 × 8 mm USB-C window and two 6 × 4 mm speaker-access windows at X ±13 mm, replacing the 36 × 10 mm opening |
| Lid retention | Two side-pad seats plus one 16 × 7 mm roof-pad seat |
| Body retention | Two side-pad seats |
| Preserved | Clawd silhouette, eye recesses, 1 mm pixel branding, 4 mm diagonal keyring bore, nominal device calibration and 0.70 mm seam gap |

The rigid lid cannot extend uninterrupted across the entire rear seam: that
material would sweep into the charging-case body when opened. The rear cap
relief is derived from a 0.45 mm-expanded body envelope swept into lid
coordinates. Each section is clipped to the relevant rear region before
convex enclosure, avoiding an unnecessarily large cut across the cap. The
outer body is also relieved for the rear skirt. Construction samples are
0.5 degrees apart; verification separately checks 116 poses at 1-degree steps.

**This is fuller coverage, not a completely sealed case.** Functional hinge,
LED/tap, USB-C and speaker openings remain. No waterproof or impact rating is
claimed. The service windows are provisional and must be checked on the real
AirPods and charging cable; matching a visual asset does not validate access.

The closed printed envelope is unchanged. The body remains approximately
75.778 × 26.900 × 42.396 mm and the lid 62.000 × 26.900 × 16.504 mm.
Body and lid heights are separate part bounding boxes, not the assembled height.

## Retention pads — required, not printed

The cavities outside the seats retain the v03 nominal 0.35 mm clearance. The
seats use a nominal 0.65 mm normal offset, approximately 0.30 mm deeper than
the original cavity, to accommodate compliant pads. **Without pads, these
recesses do not improve grip and the bare shells remain unretained.**

| Seat | Quantity | Nominal footprint / position |
| --- | --- | --- |
| Body side | 2 | 8 mm in Y × 8 mm in Z; Z 18–26 mm |
| Lid side | 2 | 8 mm in Y × 5 mm in Z; Z 39.2–44.2 mm |
| Lid roof | 1 | 16 mm in X × 7 mm in Y; follows the inner roof contour |

Use supplier-approved, soft, non-marking silicone foam or equivalent compliant
material. **0.80 mm uncompressed thickness is an initial sample, not a finished
fit specification.** It suggests roughly 0.15 mm compression against a nominal
0.65 mm normal gap, but local curvature, adhesive backing, material behaviour,
device geometry and print tolerances all change the result. Footprints are
projected design dimensions, not flattened cutting patterns for curved pads.

Pads initially bond to the cover and grip the device by friction. If a physical
test shows insufficient lid retention, the roof seat can accommodate a
finish-compatible **removable double-sided pad**. Qualify its removability and
surface compatibility first; do not use permanent glue or force the device in.
There is no rigid snap feature against the unmeasured Apple seam, no latch,
no retention-force prediction and no secure-carrying claim.

The five charcoal objects in the Blender file are illustrative seated pad
envelopes with a small display clearance. They are **not uncompressed foam
CAD, print parts or a deformation simulation**. The two metal ring coils are
also display-only. Print exports contain only the two rigid shells.

## Digital checks

- Both final print meshes are closed, single-component and consistently
  oriented, with positive volumes, no loose geometry, no non-manifold edges
  and no non-adjacent triangle-overlap candidates in the mesh screen.
- Closed shell/device intersection volumes pass, as do 66 sampled axial
  insertion positions per rigid shell. Insertion with real compressed pads
  is not simulated.
- The dense motion screen checks 0–115 degrees inclusive at 1-degree steps,
  including the rigid lid and seated pad previews against the body, body-pad
  previews, charging-case body surrogate and positioned reference ring.
  It reports no surface collisions. Real hinge geometry, continuous motion,
  elastic behaviour and hardware articulation remain unqualified.
- Nine axis-aligned rays per pad seat give body-side gaps of approximately
  0.650–0.665 mm, lid-side gaps of 0.702–0.822 mm and roof gaps of 0.650–0.662 mm.
  Axis gaps are not normal pad thicknesses. The smallest sampled seat backing
  is approximately **2.100 mm at the roof**; this is not a global wall minimum.
  Measurement uses zero BVH inflation and avoids shared-facet sampling points.
- The v03 insertion cutters, calibration references, branding cutter and
  keyring cutter retain their geometry digests. The new shells reuse them.
- STL round-trip dimensions and topology pass at one coordinate unit per mm.
  The 3MF explicitly declares millimetres and contains exactly two objects.
- All previous `.blend` models and original reference-input hashes are unchanged.
  No external references are reported missing in the saved model.

A separate 0.5 mm orthographic grid screen measures **projected exposed
surrogate area**, excluding pads. It is not total surface coverage or a
protection rating:

| View | v03 exposed area | v04 exposed area | Reduction |
| --- | ---: | ---: | ---: |
| Front | 118.50 mm² | 69.25 mm² | 41.6% |
| Rear | 562.00 mm² | 343.00 mm² | 39.0% |
| Bottom | 359.25 mm² | 158.25 mm² | 55.9% |

## Files and reproduction

- Editable model: `models/clawd-airpods4-anc-v04.blend`.
- Parameters: `models/clawd-v04-parameters.json`.
- Revision builder: `tools/revise_clawd_coverage.py`.
- Render script: `tools/render_clawd_coverage.py`.
- Print prototypes and briefing: `exports/clawd-v04/clawd-prototype/`.
- Machine-readable mesh, export and coverage checks: `exports/clawd-v04/qa/`.
- Release renders: `docs/images/`; the rear comparison is **v03 left,
  v04 right**. `pad-seats` is an exploded, device-hidden view, not an operating
  hinge position. Colour and hardware are illustrative.

Use `tools/rebuild.py` as described in [BUILD.md](BUILD.md) to reconstruct the
entire history without MCP. The v04 builder opens the saved v03 file in a separate
background Blender process. It refuses live interactive scenes, checks millimetre units
and refuses to overwrite an existing v04 unless its exact expected SHA-256 is
supplied. It preserves archived v03 shells inside the new file. The old fit-check
pair remains historical context and is **not** a v04 pad-fit coupon or export.

The render script opens v04 in background, regenerates its own presentation
scene and does not save over the editable model. The live Blender bridge was
unavailable during this revision; no live scene or global preferences changed.

## Physical qualification before carrying or ordering

1. Obtain written supplier acceptance for the new files, unfilled MJF PA12,
   finished cavity accuracy, new rear contours, pad seats and service windows.
   Do not scale, automatically thicken or silently repair the model.
2. Print one unpainted pair. Inspect and depowder all openings. Check the actual
   device and cable before adding pads; never force a tight fit.
3. Measure the printed seat gaps and trial compliant pads of suitable thickness.
   Verify device finish compatibility and removal. Excessively thick pads can
   overload the lid hinge or make the case difficult to remove.
4. Test body and cap retention separately, including repeated opening, closing,
   removal and ordinary handling over a soft surface. Qualify any removable roof
   adhesive only if needed. Do not infer retention from the digital mesh check.
5. Check full opening, earbud removal, the LED and pairing/reset taps, USB-C
   connector moulding, ANC speaker audibility and Qi/Apple Watch charging,
   including attachment, alignment and temperature with pads installed.
6. Test the keyring anchor with an empty case or suitable dummy. **Do not carry
   the real AirPods by the ring until body retention, cap retention and anchor
   behaviour have all been physically qualified.** No load rating is provided.

v04 has not been uploaded to a printer, quoted, accepted or ordered.
Earlier v02/v03 quote or automatic acceptance results do not transfer to it.

The public Blender copy removes restricted donor and donor-derived archived
objects without changing the v04 print geometry. `publication-audit.json`
records the unchanged geometry digests; `manifest.json` records public file hashes.
`final-review.json` records the pre-publication working-scene hash, not the
sanitized public Blender file hash. Publication is not physical qualification.
