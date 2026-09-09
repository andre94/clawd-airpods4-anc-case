# Printing the v03 prototype

**Not physically validated. Request a supplier-specific technical review before
ordering. An automatic quote or a watertight mesh is not manufacturing approval.**

## Quantity, units and orientation

Print one `clawd-prototype-body-v03-mm.stl` and one
`clawd-prototype-lid-v03-mm.stl`, or use the alternative two-part 3MF. Do not
combine both options into an order. All dimensions are in mm at 100% scale.
The exported lid is reoriented for separate manufacture; the native blend
shows its assembled position. The printer should choose build orientation,
supports and finishing appropriate to its equipment.

No validated layer height, wall count, infill, support recipe or G-code is
provided. Machine-specific profiles would imply evidence we do not yet have.
Do not print the reference STL/FBX in `assets/` or all objects from the blend.

## Material and finishing

Unfilled PA12 nylon by MJF or SLS is a candidate for a durable prototype. Ask
the supplier to assess its actual dimensional capability, small-hole cleanup,
wall guidelines and finishing allowances. A PLA/PETG FDM or resin sample may
be useful for some checks, but cannot automatically qualify final PA12 fit,
surface friction, flexibility, toughness or anchor strength. Avoid assuming a
brittle presentation resin is suitable for an everyday keyring accessory.

Start **unpainted**. Terracotta/orange (`#C87558` shader base color, not a physical
color standard) and black eyes are visual intent only. Render lighting changes
the apparent shade. Agree a material sample or finish color with the printer.
Keep cavity/mating surfaces free of paint; coating buildup can consume the
nominal clearance. Readable rear lettering is already part of the lid mesh.

## Ask the printer to check

- Finished cavity tolerance against the nominal 0.35 mm normal offset, including
  shrinkage, surface roughness and any smoothing or coating.
- Minimum local walls, thin edges, eye floors, rear engraving and lid reliefs.
  Engraving is nominally 1 mm deep, with approximately 1 mm grid features.
- Ø4 mm diagonal keyring bore, rounded entries, usable ring articulation,
  print orientation and strength of the surrounding plastic.
- Whether any repair, resizing, thickening or support cleanup changes the fit.
  Obtain agreement before modifying the CAD or rescaling a part.

Neither the outer body nor the separate lid has a qualified positive lock.
Removable liner/pad tuning may be needed, but no pad thickness is specified or
validated yet. Do not force a tight print onto the device, lever against its
hinge, or push through the USB-C port to remove it. Stop if it binds or scratches.

## Access and charging

The model includes geometric openings for front access, hinge movement and a
bottom USB-C / ANC-speaker service area. Opening geometry is not evidence that
every plug, tap gesture or charging pad works. Qi / Apple Watch charging,
alignment and temperature need real-device checks. No magnets or conductive
inserts are specified. Hardware placement must not impede charging or scratch
the device.

Use [QUALIFICATION.md](QUALIFICATION.md) to record results before a finished
print. Vendor prices, lead times and acceptance are intentionally not asserted
in this public package.
