# Tip map

**Purpose:** produce an 8×12 grid showing which wells of a given tip
rack are occupied. Prevents the pipette from attempting to pick up at
an empty position.

**Inputs:** the deck slot number of the tip rack (e.g. `7`).

**Output:** ASCII grid + totals, e.g.
```
     1   2   3   4   5   6   7   8   9  10  11  12
  A  X   X   X   X   .   .   .   X   X   X   X   X
  B  X   X   X   X   X   X   .   X   X   X   X   X
  ...
TOTAL_PRESENT: 84
TOTAL_EMPTY: 12
```

**Steps:**

1. Capture top + side frames (1920×1080).
2. **CV path (preferred):**
   - Crop the slot region from the top frame using the deck geometry
     (slot 7 ≈ row 3 left in standard OT-2 layout).
   - Apply CLAHE equalization to handle uneven lighting.
   - For each of the 96 well positions in the cropped rack:
     - Compute max pixel and mean pixel in a small window around the
       expected well center.
     - Tip is PRESENT if `max > 100` AND `(max - mean) > 50` (bright
       reflection rim against dark rack background).
   - Cross-validate with the side frame: count visible tip protrusions
     per column; if column-count disagrees with the CV map by >2,
     mark the column as `?` and report low confidence.
3. **Haiku fallback (when CV uncertain):**
   - Send top + side crops to `ANTHROPIC_MODEL_VISION` asking for the
     ASCII grid directly. **Haiku has been unreliable here in past
     sessions** — use only as a sanity check, not the ground truth.
4. Apply known-empty facts from this session's runs (any well the
   pipette already picked from is now empty regardless of what the
   image shows).
5. Print the grid + totals.

**Failure handling:**
- If CV confidence is low for a row or column, print `?` for those
  cells and tell the user to manually verify before running.
- The user should always visually confirm the map against the deck
  before pressing play.

**Known limitation (2026-05-22):** the top camera's oblique angle and
moderate resolution make per-well CV detection unreliable across the
full 96-position rack. Without a top-down camera position, the most
robust tip map is still a manual visual count by the user.
