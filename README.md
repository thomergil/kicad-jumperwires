# kicad-jumperwires

KiCad footprints for thin-wire jumpers on single-sided boards: a short wire
soldered through two holes where a trace can't cross another trace.

The library has one footprint for every whole millimeter from 5 to 100mm, measured
between the hole centers: `JumperWires:Jumper-Wire_5mm` … `Jumper-Wire_100mm`.
Each has two 1.6mm pads with a 0.8mm drill, and a 3D model. KiCad 9 and later treat
the two pads as connected, so DRC doesn't report the copper on either end as
unconnected.

## Install

1. Clone this repo.
2. In KiCad, open Preferences → Manage Footprint Libraries.
3. Add `JumperWires.pretty` with the nickname `JumperWires`.

## Use

In the schematic, add a `NetTie_2` symbol. Connect both pins to the net the
jumper carries. Give the symbol the footprint of the right length.

## Change the lengths

Edit `generate.py`, then run these commands. They install CadQuery, which builds
the 3D models, and run the script:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python generate.py
```

## Other jumper-wire libraries

- BlackCoffee's `JumperWires.zip` on the
  [KiCad forum](https://forum.kicad.info/t/jumper-wires-for-single-double-sided-pcbs/26446)
  (2020), for insulated hookup wire. It uses the same library name, but its
  footprints aren't compatible with these.
- [farTooOld/Kicad_BreadBoard](https://github.com/farTooOld/Kicad_BreadBoard):
  breadboards and breadboard jumpers.
- [speedypleath/jumper-wires-kicad](https://github.com/speedypleath/jumper-wires-kicad):
  colored hookup wires for the 3D view, as footprints with no pads.

## Credits

Written with [Claude Code](https://claude.com/claude-code).

## License

MIT
