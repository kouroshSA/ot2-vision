# OT-2 Vision Automation — Project Instructions

## Pre-Run Safety Checks (MANDATORY)

Before executing ANY protocol on the OT-2, perform these checks using both cameras:

### 1. Lid Detection

Tip racks may have transparent lids that must be removed before pipetting. A collision between the pipette and a lid can damage the instrument.

- **Capture images from both cameras** (top: `/dev/video3`, side: `/dev/video5`)
- **Check every occupied slot** for the presence of a lid
- A lid appears as a flat transparent surface covering the rack, with well impressions visible through it
- If a lid is detected, **STOP and warn the user** before executing any protocol
- Do NOT proceed with pipetting until the user confirms the lid has been removed

### 2. Tip Map Generation

Before any protocol that uses tips, generate a tip map to know which wells have tips and which are empty. This prevents the pipette from attempting to pick up from an empty position.

**Procedure:**
1. Capture from top camera (`/dev/video3`, 1920x1080) and side camera (`/dev/video5`, 1920x1080)
2. Crop the tip rack region from the top view
3. Calibrate a 12x8 grid using physical SBS rack dimensions:
   - Well spacing: ~9mm (translates to ~25px at typical camera distance)
   - Determine rack left edge from pixel intensity transition (deck gray ~55-70 to rack black ~4-6)
   - Column 1 starts ~14.38mm (margin) from the rack left edge
4. Use CLAHE equalization to handle uneven lighting across the rack
5. Detect tips by reflection contrast: a tip has a bright rim (max pixel > 100) against the dark rack background, with high contrast (max - mean > 50)
6. Cross-validate with side camera:
   - Tips protrude as transparent funnel shapes above the rack surface
   - Confirm the overall shape/extent of the tip block
   - Rule out false positives at rack edges (edge reflections can mimic tips)
7. Output the tip map as an 8x12 grid (rows A-H, columns 1-12) with X (tip present) and . (empty)

**Output:** Always present the tip map as an ASCII grid so the user can quickly verify correct tip locations for the session:
```
     1   2   3   4   5   6   7   8   9  10  11  12
  A  .   .   .   X   X   X   X   .   .   .   .   .
  B  .   .   X   X   X   .   X   .   .   .   .   .
  C  .   .   X   X   X   X   X   .   .   .   .   .
  D  .   X   X   X   X   X   X   .   .   .   .   .
  E  .   X   X   X   X   X   X   .   .   .   .   .
  F  .   X   X   X   X   X   .   .   .   .   .   .
  G  .   X   .   X   X   X   .   .   .   .   .   .
  H  .   .   .   X   X   X   X   .   .   .   .   .
  38 tips remaining / 58 empty
```
- `X` = tip present, `.` = empty
- Include total tips remaining and empty count below the grid
- Include per-column and per-row totals when useful
- The user should visually confirm the map matches what they see on the deck before proceeding

### 3. Deck State Verification

Before running a protocol, verify the current deck state matches what the protocol expects:
- Identify which slots have labware
- Confirm labware types (tip rack, well plate, reservoir, etc.)
- Check that required slots are not empty
- Note any unexpected items on the deck

## Camera Setup

| Camera | Device | Position | Purpose |
|--------|--------|----------|---------|
| Insta360 Link 2C | `/dev/video3` | Top (overhead) | Deck overview, tip mapping, lid detection |
| Insta360 Link 2C Pro | `/dev/video5` | Side (elevated) | Cross-validation, tip protrusion check, label reading |

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

## Environment

- Conda env: `lumi-opentron`
- All Python scripts should be run via: `conda run -n lumi-opentron python3 -c "..."`

## OT-2 Deck Layout Reference

```
  10   11   Trash
   7    8    9
   4    5    6
   1    2    3
```

Slot numbering is embossed on the deck surface. When viewing from the top camera, slot 1 is bottom-left and slot 11 is top-center.
