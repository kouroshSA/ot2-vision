# Procedures

Step-by-step playbooks for the vision and REST-API workflows Claude runs
around an OT-2 protocol — safety checks, deck inspection, robot
introspection. **These are not protocols** (don't get uploaded to the
OT-2); they're workflows Claude executes locally with bash, the
Anthropic API, and the OT-2 REST API.

Each procedure is a self-contained markdown file with explicit
executable steps. Claude reads the file, runs the steps, and reports
results back to the user.

## Catalog

| Procedure | When to run | What it produces |
|-----------|-------------|------------------|
| [`lid_detection.md`](lid_detection.md) | Before every protocol | JSON: per-slot lid status, blocking issues |
| [`tip_map.md`](tip_map.md) | Before any protocol using tips | 8×12 ASCII grid of a tip rack |
| [`deck_state.md`](deck_state.md) | Before every protocol | JSON: what labware is in each slot |
| [`pipette_mount.md`](pipette_mount.md) | Before every protocol | Pass/fail: pipette matches what the protocol expects |
| [`preflight.md`](preflight.md) | Before every protocol (composite) | Consolidated go/no-go report |

The mandatory safety doctrine — i.e. *what* checks must pass before a
real protocol runs — lives in [`../CLAUDE.md`](../CLAUDE.md). The
procedures here describe *how* to perform each check.

## How to add a new procedure

1. Create `<name>.md` in this directory.
2. Use this structure:
   ```markdown
   # <Name>

   **Purpose:** one sentence on what this procedure verifies or produces.

   **Inputs:** what the caller provides (deck state, slot number, etc.)

   **Output:** the exact format Claude returns to the user.

   **Steps:**
   1. ...
   2. ...

   **Failure handling:** how to react if a step fails or returns ambiguous data.
   ```
3. Add a row to the catalog above.
4. If the procedure is part of the mandatory pre-run safety doctrine,
   reference it from `../CLAUDE.md`.
