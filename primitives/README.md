# OT-2 Protocol Primitives

Curated, reusable OT-2 protocol templates. Each `.py` file is a working
protocol you can upload to the OT-2 directly, or edit the constants at
the top to adapt to your run.

These are **tracked in git** — generated/one-off protocols belong in
`../protocols/` instead (gitignored).

## Catalog

| File | Description | Key constants |
|------|-------------|---------------|
| `wave_goodbye_transfer.py` | Single-tip transfer between two plates with a light-flash + arm-sweep flourish at the end | `TIP_WELL`, `SOURCE_WELL`, `DEST_WELL`, `VOLUME_UL` |
| `aspirate_to_trash.py` | Aspirate a small volume and throw the tip away (with liquid in it) — for removing a known volume from a well without depositing it | `TIP_WELL`, `SOURCE_WELL`, `VOLUME_UL` |

## How to use a primitive

1. Copy it into your work directory (or edit in place if you don't want
   to keep your changes long-term):
   ```bash
   cp ~/ot2-vision/primitives/aspirate_to_trash.py ./my_run.py
   ```
2. Edit the constants at the top of the file.
3. Upload via Claude Code (just ask Claude to run it) or directly with
   the OT-2 REST API (see `~/Models/instructions.md` for the curl flow).

## How to add a new primitive

1. Drop your `.py` in this directory with a descriptive filename
   (`<verb>_<noun>.py`, e.g. `serial_dilute.py`, `tip_calibration.py`).
2. Top of the file: docstring explaining what it does, an editable
   `# ---- edit for your run ----` block of constants, and standard
   Opentrons `metadata` + `requirements` + `def run(protocol)`.
3. Add a row to the catalog table above with a one-line description
   and the names of the editable constants.
4. Commit with a clear message: `Add <name> primitive`.

## Conventions

- API level: **2.15** (matches the lab OT-2 firmware v1.1.0)
- Pipette: **`p20_single_gen2` on right mount** (the only mount installed)
- Tip rack: **`opentrons_96_tiprack_20ul`** by default
- Plates: **`corning_96_wellplate_360ul_flat`** by default
- Always end with `protocol.home()` so the next run starts from a known position
- Set `set_rail_lights(False)` at the very end so the deck isn't left lit
