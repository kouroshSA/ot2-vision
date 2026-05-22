# Lid detection

**Purpose:** verify that no transparent lid is sitting on top of any
labware in the slots a protocol will touch. A pipette collision with a
lid will damage the instrument.

**Inputs:** the list of deck slots the protocol uses (e.g. `[1, 2, 7]`).

**Output:** JSON of the form
```json
{"slots": {"1": {"lid": "none|present|suspect", ...}, ...},
 "safe_to_run": true|false,
 "blocking_issues": [...]}
```

**Steps:**

1. Capture top + side frames at 1920×1080 (see the `cv2.VideoCapture` snippet
   in `../CLAUDE.md`). Top = `/dev/video0`, side = `/dev/video2`.
2. Base64-encode both JPEGs.
3. Call the Anthropic API with model `ANTHROPIC_MODEL_VISION` (Haiku)
   and the prompt below, attaching both images:
   ```
   You are a pre-run safety check for an Opentrons OT-2. Inspect these two images.
   A LID is a flat transparent surface covering labware with well impressions
   visible THROUGH it. Tips protruding above a rack = NO lid.

   For each occupied slot, return JSON only:
   {"slots":{"<slot>":{"labware":"...","lid":"none|present|suspect","reason":"..."}},
    "safe_to_run": true|false,
    "blocking_issues": ["..."]}
   Mark safe_to_run=false if ANY of slots [<protocol_slots>] has lid != "none".
   ```
4. Parse the JSON response.

**Failure handling:**
- If `safe_to_run=false`, STOP and surface `blocking_issues` to the user.
  Do not proceed until the user confirms the lid has been removed.
- If Haiku returns `"lid": "suspect"` on a slot in the protocol's path,
  treat it as `present` (conservative).
- If parsing fails, retry once with a stricter "JSON only" suffix; if
  it still fails, fall back to manual user confirmation.
