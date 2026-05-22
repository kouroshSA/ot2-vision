# Pipette mount verification

**Purpose:** confirm the OT-2 has the pipette the protocol expects,
on the mount the protocol expects. Mismatched pipettes cause runs to
fail or, worse, succeed at the wrong volume.

**Inputs:** the expected pipette name + mount, parsed from the
protocol's `load_instrument()` call (e.g. `("p20_single_gen2", "right")`).

**Output:** pass/fail with the actual attached pipette info.

**Steps:**

1. GET the pipettes endpoint:
   ```bash
   curl -sS -H "Opentrons-Version: 3" http://169.254.142.150:31950/pipettes
   ```
2. Parse the response. Each mount returns either `null` (empty) or an
   object with `name`, `model`, `id`.
3. Verify the expected mount's `name` matches the protocol's request.
4. If the other mount is also occupied, note it but don't block.

**Failure handling:**
- If the expected mount is `null` (no pipette attached), STOP. Tell the
  user to attach the pipette before retrying.
- If the wrong pipette is attached (e.g. `p300_single_gen2` when
  protocol expects `p20_single_gen2`), STOP. Volume scaling and tip
  compatibility are pipette-specific — there is no safe fallback.
- If the OT-2 is unreachable (curl fails), surface the network error
  and do not proceed.
