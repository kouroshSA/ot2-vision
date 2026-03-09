# OT-2 Vision-Language-to-Protocol System

## What This Is

A system that lets you control an Opentrons OT-2 liquid handling robot using natural language grounded in what a camera sees on the deck. Instead of writing Python protocols by hand, you say something like:

> "Look at the deck, find the two 96-well plates, pipette 5 ul from well A5 of the far plate and put it in B4 of the near plate"

The system captures an image from an Intel RealSense D435i depth camera, detects labware, maps it to deck slots, sends the scene + instruction to Claude, and gets back a runnable OT-2 protocol.

## Architecture

```
User speaks/types instruction
        |
        v
 Camera Module          RealSense D435i  →  aligned RGB + depth frame
        |
        v
 Detection Module       YOLOv8m (50MB)   →  bounding boxes + class labels
        |
        v
 Spatial Grounding      ArUco calibration →  objects mapped to OT-2 deck slots
        |                                    "far plate" / "near plate" resolved
        v
 Protocol Generator     Claude API        →  complete OT-2 Python protocol
        |
        v
 OT-2 Executor          REST API          →  upload, run, monitor on robot
```

## What Was Done

### Project structure (`~/Models/ot2-vision/`)

```
ot2_vision/
├── camera/             RealSense D435i capture (RGB + aligned depth)
├── detection/          YOLOv8m inference, labware class defs, visualization
├── grounding/          OT-2 deck geometry, ArUco calibration, spatial resolver
├── protocol/           Claude API integration, prompt templates, validator
├── executor/           OT-2 REST API client (upload → run → monitor)
├── pipeline.py         End-to-end orchestration
└── cli.py              CLI with 6 commands
```

28 Python source files, 4 utility scripts, 4 test files.

### Modules built

| Module | Key Files | Status |
|--------|-----------|--------|
| Camera | `camera/realsense.py`, `camera/frame_data.py` | Working — D435i captures 1280x720 RGB+depth |
| Detection | `detection/detector.py`, `detection/annotator.py` | Working — YOLOv8m runs inference on GPU |
| Grounding | `grounding/ot2_deck.py`, `grounding/calibration.py`, `grounding/spatial_resolver.py`, `grounding/deck_mapper.py` | Working — 12 slots mapped, ArUco calibration ready |
| Protocol Gen | `protocol/generator.py`, `protocol/prompt_templates.py`, `protocol/scene_description.py` | Working — calls Claude API with scene context |
| Validator | `protocol/validator.py` | Working — syntax + structure + opentrons_simulate |
| Executor | `executor/ot2_client.py`, `executor/protocol_runner.py` | Written — needs OT-2 connected to test |
| Pipeline | `pipeline.py` | Written — orchestrates full flow |
| CLI | `cli.py` | Working — 6 commands registered |

### Hardware verified

| Component | Status |
|-----------|--------|
| Intel RealSense D435i | Connected, detected, captures frames (fx=914, 1280x720) |
| YOLOv8m (COCO pretrained) | Loaded, runs inference on RTX 5060, ~200MB VRAM |
| pyrealsense2 2.56.5 | pip wheel works on kernel 6.17 (no source build needed) |
| NVIDIA RTX 5060 | PyTorch 2.10 cu128, CUDA working |

### Tests

31 unit tests, all passing:
- `test_ot2_deck.py` — 11 tests for deck geometry and slot lookups
- `test_spatial_resolver.py` — 11 tests for far/near/left/right resolution
- `test_scene_description.py` — 4 tests for scene text generation
- `test_protocol_validator.py` — 5 tests for protocol validation

Run with: `conda activate lumi-opentron && pytest tests/ -v`

### Dependencies installed (in `lumi-opentron` conda env)

- `pyrealsense2==2.56.5` — RealSense camera driver
- `ultralytics==8.4.21` — YOLOv8
- `opencv-contrib-python-headless==4.13.0` — OpenCV with ArUco support
- `anthropic==0.84.0` — Claude API client
- `click==8.1.7` — CLI framework
- `rich==13.7.1` — terminal formatting
- `pytest==9.0.2` — testing

### CLI commands

```bash
conda activate lumi-opentron
cd ~/Models/ot2-vision

# Test camera (live RGB+depth display, press q to quit)
python -m ot2_vision.cli test-camera

# Generate protocol from mock scene (no hardware needed, needs ANTHROPIC_API_KEY in .env)
python -m ot2_vision.cli demo "transfer 10ul from plate in slot 1 A1 to plate in slot 3 B2"

# Generate protocol from mock scene JSON file
python -m ot2_vision.cli demo "pipette from the far plate to the near plate" --scene-file data/mock_scene.json

# Validate a protocol file
python -m ot2_vision.cli validate protocols/some_protocol.py

# Full pipeline (camera + detection + generation)
python -m ot2_vision.cli run "look at the deck, find the plates, transfer 5ul from A1 of the far plate to B4 of the near plate"

# Full pipeline with OT-2 execution
python -m ot2_vision.cli run "..." --execute

# Run calibration (ArUco markers on deck)
python -m ot2_vision.cli calibrate

# Upload and execute existing protocol on OT-2
python -m ot2_vision.cli execute protocols/my_protocol.py --host 192.168.1.10
```

## Next Steps

### 1. Set your Anthropic API key

Edit `~/Models/ot2-vision/.env` and replace the placeholder:
```
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```
Then test demo mode: `python -m ot2_vision.cli demo "transfer 10ul from slot 1 A1 to slot 3 B2"`

### 2. Fine-tune YOLOv8 on labware

The current model is COCO-pretrained (detects people, cars, etc). It needs fine-tuning to detect OT-2 labware (96-well plates, tip racks, reservoirs).

**Options:**
- **Roboflow public datasets** — search for "microplate", "well plate", or "labware" datasets and combine with your own images
- **Collect your own data** — mount the camera over the OT-2, capture 100-200 images per labware type in various configurations, annotate with [Label Studio](https://labelstud.io/) or [Roboflow](https://roboflow.com/)
- **Training** takes ~30 min on the RTX 5060:
  ```bash
  conda activate lumi-opentron
  yolo detect train data=data/dataset.yaml model=models/yolov8m.pt epochs=100 imgsz=1280
  ```

Target classes defined in `ot2_vision/detection/labware_classes.py`:
- 96-well plate, 96-well PCR plate, 384-well plate
- 300ul tip rack, 1000ul tip rack
- 12-row reservoir, 1-well reservoir
- 24-tube rack, deep well plate

### 3. Camera-to-deck calibration

When the camera is mounted above the OT-2 deck:

1. Print 4 ArUco markers (dictionary DICT_4X4_50, IDs 0-3, 30mm each)
2. Tape them on the deck at the calibration points:
   - Marker 0: Slot 1 bottom-left (12.13, 9.0 mm)
   - Marker 1: Slot 3 bottom-right (380.87, 9.0 mm)
   - Marker 2: Slot 7 top-left (12.13, 258.0 mm)
   - Marker 3: Slot 9 top-right (380.87, 258.0 mm)
3. Run: `python -m ot2_vision.cli calibrate`
4. Press SPACE when markers are visible — saves transform to `calibration/camera_to_deck.json`

### 4. Connect and test with OT-2

1. Connect OT-2 via USB or WiFi
2. Find its IP (via Opentrons app or `nmap -p 31950 192.168.1.0/24`)
3. Update `.env`: `OT2_IP=<your-ot2-ip>`
4. Test: `curl http://<OT2_IP>:31950/health`
5. Execute a protocol: `python -m ot2_vision.cli execute protocols/generated.py --host <OT2_IP>`

### 5. Full end-to-end test

With camera mounted, calibrated, labware model trained, and OT-2 connected:

```bash
python -m ot2_vision.cli run \
  "look at the deck, find the two 96-well plates, \
   pipette 5 ul from well A5 of the far plate \
   and put it in B4 of the near plate" \
  --execute
```

### 6. Future improvements

- **Voice input** — add microphone + Whisper for hands-free operation
- **Continuous monitoring** — watch the deck during protocol execution, detect errors (spills, misplaced labware)
- **Multi-step conversations** — iterative refinement of protocols through dialogue
- **Protocol library** — save and recall previously generated protocols
- **Labware verification** — before execution, verify the detected labware matches what the protocol expects

## File Map

```
~/Models/ot2-vision/
├── pyproject.toml                    Project metadata + dependencies
├── Makefile                          Build/test/run targets
├── .env                              API keys and OT-2 connection settings
├── summary.md                        This file
│
├── ot2_vision/                       Main package (28 files)
│   ├── config.py                     Central config from .env
│   ├── pipeline.py                   End-to-end orchestration
│   ├── cli.py                        CLI entry point (6 commands)
│   ├── camera/                       RealSense D435i capture
│   ├── detection/                    YOLOv8 inference + labware classes
│   ├── grounding/                    Deck geometry + calibration + spatial resolver
│   ├── protocol/                     Claude API + prompts + validator
│   └── executor/                     OT-2 REST API client
│
├── scripts/                          Standalone utilities
│   ├── test_camera.py                Camera verification (live display)
│   ├── calibrate.py                  Interactive ArUco calibration
│   ├── test_detection.py             Detection on single image
│   └── test_pipeline.py              Full pipeline dry run
│
├── tests/                            Unit tests (31 tests, all passing)
├── models/yolov8m.pt                 YOLOv8m weights (50MB, COCO pretrained)
├── calibration/                      Stored calibration matrix (after calibrating)
├── protocols/                        Generated protocol output
└── data/
    ├── mock_scene.json               Sample mock scene for demo mode
    ├── sample_rgb.png                Test capture from D435i
    └── sample_annotated.png          Test capture with YOLO detections
```
