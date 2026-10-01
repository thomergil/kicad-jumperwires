#!/usr/bin/env python3
"""Generate the JumperWires KiCad footprint library.

Wire jumpers made from bare wire, such as resistor-lead clippings. Writes one
footprint plus a STEP 3D model per length into JumperWires.pretty/. The footprints reference their models by bare filename,
which KiCad resolves relative to the library directory, so the library works
without configuring any path variables.

Usage:
    .venv/bin/python generate.py            # regenerate everything
    .venv/bin/python generate.py --no-3d    # footprints only (no cadquery needed)
"""

import argparse
import math
import re
import uuid
from pathlib import Path

LIBRARY_DIR = Path(__file__).parent / "JumperWires.pretty"

LENGTHS_MM = range(5, 101)  # hole pitch, center to center

WIRE_COLOR = (0.78, 0.78, 0.80)  # tinned copper

# Pads, same as KiCad's Resistor_THT footprints, which these leads come from.
# KiCad puts every through-hole pad on all copper layers when it loads a
# board, so B.Cu-only pads would always show as differing from the library.
PAD_DIAMETER = 1.6
PAD_DRILL = 0.8
PAD_LAYERS = '"*.Cu" "*.Mask"'

SILK_WIDTH = 0.15
SILK_PAD_CLEARANCE = 0.3
FAB_WIDTH = 0.1
COURTYARD_WIDTH = 0.05
COURTYARD_MARGIN = 0.25

# Wire geometry (a resistor lead).
WIRE_DIAMETER = 0.6
BEND_RADIUS = 0.6
BOARD_THICKNESS = 1.6
LEG_PROTRUSION = 1.0  # how far the leg sticks out below the board

# Stable UUIDs, so regenerating doesn't churn every file.
UUID_NAMESPACE = uuid.UUID("6f1d3c2e-8a4b-4e57-9c0d-2b7a51e9f4a3")


def footprint_name(length):
    return f"Jumper-Wire_{length}mm"


def fmt(value):
    return f"{value:.4f}".rstrip("0").rstrip(".")


def stable_uuid(name, item):
    return uuid.uuid5(UUID_NAMESPACE, f"{name}/{item}")


def footprint(length):
    name = footprint_name(length)
    pad_radius = PAD_DIAMETER / 2
    silk_x0 = pad_radius + SILK_PAD_CLEARANCE
    silk_x1 = length - silk_x0
    crt_x0 = -pad_radius - COURTYARD_MARGIN
    crt_x1 = length + pad_radius + COURTYARD_MARGIN
    crt_y = pad_radius + COURTYARD_MARGIN
    u = lambda item: stable_uuid(name, item)

    pads = "".join(
        f"""
	(pad "{number}" thru_hole circle
		(at {fmt(x)} 0)
		(size {fmt(PAD_DIAMETER)} {fmt(PAD_DIAMETER)})
		(drill {fmt(PAD_DRILL)})
		(layers {PAD_LAYERS})
		(uuid "{u(f"pad{number}")}")
	)"""
        for number, x in (("1", 0), ("2", length))
    )

    return f"""(footprint "{name}"
	(version 20241229)
	(generator "kicad-jumperwires")
	(generator_version "1.0")
	(layer "F.Cu")
	(descr "Wire jumper (wire bridge) for single-sided boards, {length}mm hole pitch, bare wire such as a resistor lead")
	(tags "jumper wire bridge link net tie single sided")
	(property "Reference" "REF**"
		(at {fmt(length / 2)} {fmt(-crt_y - 0.8)} 0)
		(layer "F.SilkS")
		(uuid "{u("reference")}")
		(effects
			(font
				(size 1 1)
				(thickness 0.15)
			)
		)
	)
	(property "Value" "{name}"
		(at {fmt(length / 2)} {fmt(crt_y + 0.8)} 0)
		(layer "F.Fab")
		(uuid "{u("value")}")
		(effects
			(font
				(size 1 1)
				(thickness 0.15)
			)
		)
	)
	(attr through_hole)
	(jumper_pad_groups ("1" "2"))
	(fp_line
		(start {fmt(silk_x0)} 0)
		(end {fmt(silk_x1)} 0)
		(stroke
			(width {fmt(SILK_WIDTH)})
			(type solid)
		)
		(layer "F.SilkS")
		(uuid "{u("silk")}")
	)
	(fp_line
		(start 0 0)
		(end {fmt(length)} 0)
		(stroke
			(width {fmt(FAB_WIDTH)})
			(type solid)
		)
		(layer "F.Fab")
		(uuid "{u("fab")}")
	)
	(fp_rect
		(start {fmt(crt_x0)} {fmt(-crt_y)})
		(end {fmt(crt_x1)} {fmt(crt_y)})
		(stroke
			(width {fmt(COURTYARD_WIDTH)})
			(type solid)
		)
		(fill no)
		(layer "F.CrtYd")
		(uuid "{u("courtyard")}")
	)
	(fp_text user "${{REFERENCE}}"
		(at {fmt(length / 2)} -0.8 0)
		(layer "F.Fab")
		(uuid "{u("fab-reference")}")
		(effects
			(font
				(size 0.8 0.8)
				(thickness 0.12)
			)
		)
	){pads}
	(model "{name}.step"
		(offset
			(xyz 0 0 0)
		)
		(scale
			(xyz 1 1 1)
		)
		(rotate
			(xyz 0 0 0)
		)
	)
)
"""


def wire_solid(length):
    """Return the wire solid; origin at pad 1, z=0 on the board top."""
    import cadquery as cq

    r = BEND_RADIUS
    z_center = r  # the bends start at the board surface
    z_bottom = -BOARD_THICKNESS - LEG_PROTRUSION
    diag = r / math.sqrt(2)

    # The XZ workplane's local y axis is global Z.
    path = (
        cq.Workplane("XZ")
        .moveTo(0, z_bottom)
        .lineTo(0, z_center - r)
        .threePointArc((r - diag, z_center - r + diag), (r, z_center))
        .lineTo(length - r, z_center)
        .threePointArc((length - r + diag, z_center - r + diag), (length, z_center - r))
        .lineTo(length, z_bottom)
    )
    return (
        cq.Workplane("XY", origin=(0, 0, z_bottom))
        .circle(WIRE_DIAMETER / 2)
        .sweep(path, transition="round")
        .val()
    )


def write_step(path, name, wire):
    import cadquery as cq

    assembly = cq.Assembly(name=name)
    assembly.add(wire, name="wire", color=cq.Color(*WIRE_COLOR))
    tmp = path.with_suffix(".tmp.step")
    assembly.export(str(tmp), "STEP")
    # Pin the header timestamp so regenerating only changes files that differ.
    step = tmp.read_text()
    tmp.unlink()
    step = re.sub(r"(FILE_NAME\('[^']*',)'[^']*'", r"\1'2000-01-01T00:00:00'", step, count=1)
    # OpenCASCADE emits color styling in memory order, so identical models can
    # come out with entities renumbered; keep the existing file in that case.
    if path.exists() and step_signature(path.read_text()) == step_signature(step):
        return
    path.write_text(step)


def step_signature(step):
    return sorted(re.sub(r"#\d+", "#", line) for line in step.splitlines())


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--no-3d", action="store_true", help="skip STEP generation")
    args = parser.parse_args()

    LIBRARY_DIR.mkdir(exist_ok=True)
    for length in LENGTHS_MM:
        name = footprint_name(length)
        (LIBRARY_DIR / f"{name}.kicad_mod").write_text(footprint(length))
        if not args.no_3d:
            write_step(LIBRARY_DIR / f"{name}.step", name, wire_solid(length))
        print(f"{length}mm", end=" ", flush=True)
    print()


if __name__ == "__main__":
    main()
