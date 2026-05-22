# OT-2 Vision Automation — Project Instructions

## Help command

When the user types `help` (case-insensitive, possibly with punctuation
like `help?` or `help me`), reply with the contents of
[`HELP.md`](HELP.md) verbatim before doing anything else. This is the
canonical onboarding entry point for new lab users.

## Pre-Run Safety Checks (MANDATORY)

Before executing ANY protocol on the OT-2, run the full **preflight**
procedure: [`procedures/preflight.md`](procedures/preflight.md). It
composes four sub-checks:

1. **Lid detection** — [`procedures/lid_detection.md`](procedures/lid_detection.md).
   A pipette collision with a transparent lid will damage the instrument.
   If any occupied slot in the protocol's path has `lid != "none"`,
   STOP and warn the user.
2. **Tip map** — [`procedures/tip_map.md`](procedures/tip_map.md).
   Verify the specific well(s) the protocol will pick from actually
   have tips. Output as an 8×12 ASCII grid for the user to confirm.
3. **Deck state** — [`procedures/deck_state.md`](procedures/deck_state.md).
   Verify physical labware in each slot matches what the protocol
   `load_labware()` calls expect.
4. **Pipette mount** — [`procedures/pipette_mount.md`](procedures/pipette_mount.md).
   Verify the attached pipette matches the protocol's
   `load_instrument()` request.

The user may explicitly override an individual check ("I've checked
the lids manually, skip that"). Always echo the override back before
proceeding. Never silently skip a safety check.

## Camera Setup

| Camera | Device | Position | Purpose |
|--------|--------|----------|---------|
| Insta360 Link 2C | `/dev/video0` | Top (overhead) | Deck overview, tip mapping, lid detection |
| Insta360 Link 2C Pro | `/dev/video2` | Side (elevated) | Cross-validation, tip protrusion check, label reading |

`.env` has `CAMERA_DEVICE=0` and `SIDE_CAMERA_DEVICE=2`. USB
re-enumeration after reboot can shift these — check `v4l2-ctl
--list-devices` if capture fails.

**Capture procedure:**
```python
import cv2
cap = cv2.VideoCapture(DEVICE_INDEX)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
for _ in range(10):  # let auto-exposure settle
    cap.read()
ret, frame = cap.read()
cap.release()
```

## Models

- `ANTHROPIC_MODEL_VISION` (Haiku 4.5) — fast vision/safety checks.
  Known limitation: mis-identifies slot contents on overhead views.
  Always have the user visually confirm before acting on the output.
- `ANTHROPIC_MODEL_CODEGEN` (Sonnet 4.6) — protocol code generation.

Both load from `/opt/ot2-vision/.env` (or `./.env`) via
`ot2_vision.config`.

## Environment

- Conda env: `lumi-opentron`
- Run Python via: `conda run -n lumi-opentron --no-capture-output python3 ...`
  (the `--no-capture-output` flag is required — without it, conda
  buffers stdout and the output looks lost).

## OT-2 Deck Layout Reference

```
  10   11   Trash
   7    8    9
   4    5    6
   1    2    3
```

Slot numbering is embossed on the deck surface. From the top camera,
slot 1 is bottom-left and slot 11 is top-center.

## Where things live

- `primitives/` — curated reusable protocol templates (tracked)
- `procedures/` — vision / safety / robot workflow playbooks (tracked)
- `protocols/` — generated and one-off protocols (gitignored)
- `instruction.md` — lab-user-facing setup + operation guide
- `HELP.md` — quick-start shown when the user types `help`
