# OT-2 Vision Pipeline Architecture

## Overview

End-to-end system that detects labware on an OT-2 deck via camera, maps detections
to deck coordinates, generates Python protocols via AI, and executes them on the robot.

```
 User Instruction (natural language)
              │
              ▼
┌──────────────────────────────────────────────────────────────┐
│                    PIPELINE FLOW                             │
│                                                              │
│   ┌─────────┐   ┌───────────┐   ┌──────────┐   ┌────────┐  │
│   │ CAPTURE │──▶│  DETECT   │──▶│  GROUND  │──▶│GENERATE│  │
│   │ Camera  │   │   YOLO    │   │ Mapping  │   │ Claude │  │
│   └─────────┘   └───────────┘   └──────────┘   └───┬────┘  │
│                                                     │       │
│                                    ┌──────────┐     │       │
│                                    │ EXECUTE  │◀────┘       │
│                                    │  OT-2    │             │
│                                    └──────────┘             │
└──────────────────────────────────────────────────────────────┘
```

---

## Stage 1: Camera Capture

**Module**: `ot2_vision/camera/realsense.py`
**Hardware**: Intel RealSense D435i

```
┌──────────────────────────────────────┐
│         RealSenseCamera              │
│                                      │
│  start() ──▶ capture() ──▶ stop()   │
│                  │                   │
│                  ▼                   │
│            FrameData                 │
│         ┌──────────────┐             │
│         │ rgb    (H,W,3) uint8 BGR   │
│         │ depth  (H,W)   uint16 mm   │
│         │ intrinsics (fx,fy,ppx,ppy) │
│         │ depth_scale  (0.001)       │
│         │ timestamp                  │
│         └──────────────┘             │
└──────────────────────────────────────┘
```

- Resolution: 1280 x 720 (configurable)
- Depth aligned to color stream
- `pixel_to_3d(u, v)` deprojects pixel to 3D camera-frame coordinates

---

## Stage 2: Labware Detection

**Module**: `ot2_vision/detection/detector.py`
**Model**: YOLOv8m (COCO pretrained, needs labware fine-tuning)

```
┌──────────────────────────────────────────────────────┐
│                LabwareDetector                        │
│                                                      │
│  RGB Frame ──▶ YOLO Inference ──▶ list[Detection]   │
│                                                      │
│  Detection:                                          │
│  ┌─────────────────────────────────────┐             │
│  │ class_id       (0-8)               │             │
│  │ class_name     "96-well plate"     │             │
│  │ confidence     0.0 - 1.0           │             │
│  │ bbox           (x1, y1, x2, y2) px │             │
│  │ center_px      (cx, cy) px         │             │
│  │ opentrons_name (property)          │             │
│  └─────────────────────────────────────┘             │
└──────────────────────────────────────────────────────┘
```

**Supported labware classes (9)**:

```
ID  Class                 Opentrons Load Name
──  ────────────────────  ──────────────────────────────────────────
 0  96-well plate         corning_96_wellplate_360ul_flat
 1  96-well PCR plate     opentrons_96_wellplate_200ul_pcr_full_skirt
 2  384-well plate        corning_384_wellplate_112ul_flat
 3  300uL tip rack        opentrons_96_tiprack_300ul
 4  1000uL tip rack       opentrons_96_tiprack_1000ul
 5  12-row reservoir      nest_12_reservoir_15ml
 6  1-well reservoir      nest_1_reservoir_195ml
 7  24-tube rack          opentrons_24_tuberack_nest_1.5ml_snapcap
 8  Deep well plate       nest_96_wellplate_2ml_deep
```

---

## Stage 3: Spatial Grounding

**Module**: `ot2_vision/grounding/`

Transforms pixel-space detections into physical deck positions.

```
                    Detection (pixels)
                         │
          ┌──────────────┴──────────────┐
          │                             │
          ▼                             ▼
   ┌──────────────┐           ┌──────────────────┐
   │ Depth Lookup │           │   Calibration    │
   │ at center_px │           │ (ArUco markers)  │
   │              │           │                  │
   │ pixel + depth│           │ 4x4 transform:   │
   │ + intrinsics │           │ camera → deck    │
   │ = 3D camera  │           │ (SVD Procrustes) │
   │   coords     │           │                  │
   └──────┬───────┘           └────────┬─────────┘
          │                            │
          └──────────┬─────────────────┘
                     │
                     ▼
            ┌────────────────┐
            │  DECK MAPPER   │
            │                │
            │ 3D camera pt   │
            │    × transform │
            │ = deck (x,y,z) │
            │   in mm        │
            └───────┬────────┘
                    │
                    ▼
            ┌────────────────┐
            │ SLOT FINDER    │
            │                │
            │ (x,y) → which  │
            │ slot contains  │
            │ this point?    │
            └───────┬────────┘
                    │
                    ▼
            GroundedObject
          ┌───────────────────┐
          │ detection  (orig) │
          │ slot       (1-11) │
          │ deck_pos   (x,y,z)│
          │ labware_name      │
          └───────────────────┘
```

### OT-2 Deck Layout

```
         LEFT                    CENTER                   RIGHT
         X=0                     X=132.5                  X=265
    ┌──────────────┬──────────────┬──────────────┐
    │              │              │              │
    │   Slot 10    │   Slot 11    │    TRASH     │  Y=271.5  BACK
    │              │              │   (fixed)    │
    ├──────────────┼──────────────┼──────────────┤
    │              │              │              │
    │   Slot 7     │   Slot 8     │   Slot 9     │  Y=181.0
    │              │              │              │
    ├──────────────┼──────────────┼──────────────┤
    │              │              │              │
    │   Slot 4     │   Slot 5     │   Slot 6     │  Y=90.5
    │              │              │              │
    ├──────────────┼──────────────┼──────────────┤
    │              │              │              │
    │   Slot 1     │   Slot 2     │   Slot 3     │  Y=0     FRONT
    │              │              │              │
    └──────────────┴──────────────┴──────────────┘
                                         Operator stands here ▼

    Each slot: 128mm wide × 86mm tall
    Full deck: 393mm × 357.5mm
```

### Calibration

- 4 ArUco markers (DICT_4X4_50, 30mm) placed at corners of the deck
- Marker 0: Slot 1 bottom-left (12.13, 9.0 mm)
- Marker 1: Slot 3 bottom-right (380.87, 9.0 mm)
- Marker 2: Slot 7 top-left (12.13, 258.0 mm)
- Marker 3: Slot 9 top-right (380.87, 258.0 mm)
- SVD-based Procrustes algorithm computes rigid transform (rotation + translation)

---

## Stage 4: Protocol Generation

**Module**: `ot2_vision/protocol/`

```
┌───────────────────────────────────────────────────────────────┐
│                    ProtocolGenerator                          │
│                                                              │
│  ┌──────────────┐    ┌─────────────────┐    ┌────────────┐  │
│  │ Scene Desc   │    │  System Prompt  │    │  Claude    │  │
│  │              │───▶│                 │───▶│  API Call  │  │
│  │ <deck_state> │    │ + constraints   │    │            │  │
│  │  Slot 1: ... │    │ + deck layout   │    │ sonnet     │  │
│  │  Slot 3: ... │    │ + transfer tips │    │ temp=0.0   │  │
│  └──────────────┘    │ + reference docs│    │ 4096 tok   │  │
│                      └─────────────────┘    └─────┬──────┘  │
│                                                   │         │
│  User Instruction ────────────────────────────────┘         │
│  "transfer 10uL from plate 1 to plate 2"                   │
│                                                              │
│                         ┌───────────────┐                   │
│                         │ Extract code  │                   │
│                         │ from response │                   │
│                         │ (```python)   │                   │
│                         └───────┬───────┘                   │
│                                 │                           │
│                                 ▼                           │
│                        Python protocol                      │
│                           string                            │
└───────────────────────────────────────────────────────────────┘
```

### Validation (`validator.py`)

```
Protocol Code
     │
     ├──▶ 1. Syntax Check      (ast.parse)
     ├──▶ 2. Structure Check    (imports, def run(), apiLevel, robotType)
     └──▶ 3. Simulation         (opentrons_simulate, optional)
            │
            ▼
     (is_valid, message)
```

---

## Stage 5: Execution

**Module**: `ot2_vision/executor/`

```
┌──────────────────────────────────────────────────────────────┐
│                      OT2Client                               │
│              http://169.254.142.150:31950                     │
│              Header: Opentrons-Version: 3                    │
│                                                              │
│  Protocol Code                                               │
│       │                                                      │
│       ▼                                                      │
│  ┌──────────────┐   POST /protocols                          │
│  │ 1. UPLOAD    │──────────────────────▶ protocol_id         │
│  └──────┬───────┘                                            │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────┐   POST /runs                               │
│  │ 2. CREATE    │──────────────────────▶ run_id              │
│  │    RUN       │                                            │
│  └──────┬───────┘                                            │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────┐   GET /protocols/{id}/analyses             │
│  │ 3. WAIT FOR  │──────────────────────▶ "completed"         │
│  │   ANALYSIS   │   (poll every 3s, timeout 120s)            │
│  └──────┬───────┘                                            │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────┐   POST /runs/{id}/actions {play}           │
│  │ 4. START     │──────────────────────▶ running             │
│  └──────┬───────┘                                            │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────┐   GET /runs/{id}                           │
│  │ 5. MONITOR   │──────────────────────▶ succeeded/failed    │
│  │              │   (poll every 5s, timeout 600s)            │
│  └──────────────┘                                            │
│                                                              │
│  Emergency: stop_run() ──▶ POST /runs/{id}/actions {stop}    │
│  Direct:    home()     ──▶ POST /robot/home                  │
│             set_lights()──▶ POST /robot/lights               │
└──────────────────────────────────────────────────────────────┘
```

---

## Natural Language Interface (Current)

Currently operates through Claude Code as the natural language layer:

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  User: "pick up a tip, aspirate 5uL from A1,                │
│         put it in B1, then wave goodbye"                     │
│                │                                             │
│                ▼                                             │
│  ┌──────────────────────┐                                    │
│  │   Claude Code        │  ◀── Knows deck state:            │
│  │   (this session)     │      Slot 2: Falcon plate          │
│  │                      │      Slot 7: tips (D3-H3)          │
│  │   Translates to      │      Right: P20 single             │
│  │   OT-2 protocol code │                                    │
│  └──────────┬───────────┘                                    │
│             │                                                │
│             ▼                                                │
│  ┌──────────────────────┐                                    │
│  │   run_protocol.run() │  Upload → Create → Start → Wait   │
│  │   (with Ctrl+C stop) │                                    │
│  └──────────────────────┘                                    │
│                                                              │
│  Future: local LLM replaces Claude Code in this role         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Primitives Library

Saved reusable protocols in `ot2_vision/executor/primitives.py`:

| Primitive | Description |
|-----------|-------------|
| `WAVE_GOODBYE` | Flash lights, sweep arm high across deck, home, final flash |

---

## CLI Commands

```
$ ot2-vision --help

  test-camera     Live RGB + Depth display (press q to quit)
  calibrate       ArUco camera-to-deck calibration
  run             Full pipeline: capture → detect → ground → generate → [execute]
  demo            Generate protocol from mock scene (no hardware)
  validate        Check protocol syntax and structure
  execute         Upload and run a protocol file on OT-2
  wave-goodbye    Robot waves its arm and flashes lights
```

---

## Configuration

All settings via `.env` file:

```
ANTHROPIC_API_KEY=...              # Claude API key
OT2_IP=169.254.142.150             # Robot IP (link-local Ethernet)
OT2_PORT=31950                     # Robot API port
YOLO_MODEL_PATH=models/yolov8m.pt  # YOLO weights
DETECTION_CONFIDENCE=0.5           # Detection threshold
CALIBRATION_PATH=calibration/camera_to_deck.json
```

---

## Current Hardware

| Component | Details |
|-----------|---------|
| Robot | OT-2 Standard (OT2CEP20200619B06), API v8.6.0 |
| Pipette | P20 single-channel gen2 (right mount) |
| Camera | Intel RealSense D435i (1280x720) |
| GPU | NVIDIA RTX 5060 |
| Connection | Ethernet via USB adapter, link-local 169.254.x.x |
