# Deck state

**Purpose:** identify what labware is sitting at each slot of the OT-2
deck and verify that what's present matches what the protocol expects
to load.

**Inputs:** optionally, a list of `(slot, expected_labware)` pairs from
the protocol.

**Output:** JSON of per-slot contents, plus a verification result if
expectations were provided:
```json
{"1": {"contents": "96-well plate", "notes": ""},
 "7": {"contents": "20uL tip rack (partially used)", "notes": "tips visible columns 1-4"},
 ...
 "verification": {"mismatches": [...], "pass": true|false}}
```

**Steps:**

1. Capture top frame at 1920×1080 (`/dev/video0`).
2. Call `ANTHROPIC_MODEL_VISION` with the image and this prompt
   (deck orientation matters — embedded labels anchor the reader):
   ```
   OT-2 deck top-camera image. The slot numbers are EMBOSSED on the deck.

   Deck layout:
     Row top:    [10] [11] [trash]
     Row 3:      [ 7] [ 8] [ 9]
     Row 2:      [ 4] [ 5] [ 6]
     Row bottom: [ 1] [ 2] [ 3]

   For each slot 1-11, read the embossed number to anchor yourself, then
   describe what's physically IN that slot, if anything.

   Return ONLY JSON: {"<slot>": {"contents": "empty|<short>", "notes": "..."}}
   ```
3. If protocol expectations were provided, compare each `(slot, expected)`
   pair against the Haiku result. Mark mismatches.
4. Print the per-slot summary to the user.

**Failure handling:**
- **Known limitation:** Haiku has been observed mis-assigning slot
  contents on overhead views (e.g. saying slot 1 has a tip rack when
  it's a plate). Always ask the user to visually confirm the result
  before proceeding.
- If a protocol-required slot reports `"empty"`, STOP and warn the user.
- If Haiku flags a slot as ambiguous (`"unknown"` / unclear notes) and
  that slot is in the protocol path, ask the user to confirm what's there.
