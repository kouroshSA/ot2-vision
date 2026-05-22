# Preflight

**Purpose:** composite procedure that runs every mandatory check
before a real protocol executes. This is the procedure Claude invokes
by default whenever a user asks to run a protocol on the OT-2.

**Inputs:** the parsed protocol — specifically:
- slots used (`source`, `dest`, `tip_rack`, etc.)
- pipette + mount expected
- tip rack slot(s) the protocol will pick from

**Output:** consolidated go/no-go report:
```
PREFLIGHT — <protocol_name>
  [✓/✗] OT-2 reachable: <api_version> / <fw_version>
  [✓/✗] Pipette: <name> on <mount>   (expected: <name> on <mount>)
  [✓/✗] Lid detection: <safe_to_run>
  [✓/✗] Deck state: <slots OK | mismatches>
  [✓/✗] Tip map (slot N): <n>/96 tips, well <pick_well> present?
  --------
  STATUS: GO | NO-GO
  Blocking issues: [...]
```

**Steps:**

1. **Reachability** — `curl /health`. Note API + firmware version.
   If unreachable, STOP immediately.
2. **Pipette mount** — run [`pipette_mount.md`](pipette_mount.md).
3. **Lid detection** — run [`lid_detection.md`](lid_detection.md)
   restricted to the slots the protocol uses.
4. **Deck state** — run [`deck_state.md`](deck_state.md), passing the
   protocol's expected `(slot, labware)` list.
5. **Tip map** — run [`tip_map.md`](tip_map.md) for each tip rack the
   protocol picks from. Specifically verify the well(s) the protocol
   will `pick_up_tip(rack[well])` are present.
6. Print the consolidated report.
7. If `STATUS == NO-GO`, halt and surface the blocking issues to the
   user. Do NOT proceed to upload.

**Failure handling:**
- A `NO-GO` from any sub-step blocks the protocol upload.
- The user can override an individual sub-step by explicitly saying so
  (e.g. "I've checked the lids and tips manually, skip those") — but
  Claude must echo the override decision back before proceeding.

**Composability:** sub-procedures can be invoked individually when a
user asks for just one check (e.g. "what's on the deck?" → just run
`deck_state.md`).
