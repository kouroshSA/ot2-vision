# OT-2 Vision — Help

You're in the lab automation repo. This shell + Claude Code combination
drives the Opentrons OT-2 robot via natural-language instructions, with
mandatory vision-based safety checks before every run.

## Quick start

```bash
# 1. Verify everything is wired up
claude --version                              # Claude Code installed?
echo ${ANTHROPIC_API_KEY:0:12}                # should be sk-ant-api03
curl -sS http://169.254.142.150:31950/health  # OT-2 reachable?

# 2. Make a work directory where generated files will land
mkdir -p ~/runs/$(date +%Y%m%d) && cd ~/runs/$(date +%Y%m%d)

# 3. Launch Claude Code and give an instruction
claude
> Pick a tip from slot 7 well A8, aspirate 10 uL from slot 1 A1, dispense into slot 3 A4.
```

## Where things live

| What | Where |
|------|-------|
| **Curated protocol templates** (use these as starting points) | `primitives/` |
| **Vision / safety / robot procedures** | `procedures/` |
| **Mandatory safety doctrine** | `CLAUDE.md` |
| **Lab user setup + operation guide** | `instruction.md` |
| **Generated / one-off protocols** (gitignored, local) | `protocols/` |
| **Shared lab API key + OT-2 config** | `/opt/ot2-vision/.env` (group `ot2lab`) |

## Adding a primitive (reusable protocol)

1. Drop a `.py` in `primitives/` with a clear filename
   (`<verb>_<noun>.py`, e.g. `serial_dilute.py`).
2. Top of the file: docstring, an editable `# ---- edit for your run ----`
   block, then standard `metadata` / `requirements` / `def run(protocol)`.
3. Add a row to `primitives/README.md`.
4. Commit and push.

## Adding a procedure (vision / safety / robot workflow)

1. Create `procedures/<name>.md` with this structure: Purpose, Inputs,
   Output, Steps, Failure handling.
2. Add a row to `procedures/README.md`.
3. If it's part of mandatory pre-run safety, link it from `CLAUDE.md`.
4. Commit and push.

## Asking Claude to do things

Claude reads `CLAUDE.md` automatically when you launch from this repo,
so the safety doctrine is always in effect. You can:

- **Ask for a protocol** in natural language — Claude generates the
  Python, runs the safety preflight (see `procedures/preflight.md`),
  asks for go/no-go, then uploads and executes.
- **Ask for a single safety check** — "what's on the deck?", "map slot
  7's tips", "are there any lids on the plates?"
- **Reuse a primitive** — "run the wave goodbye transfer with tip A8,
  source A1, dest B3".
- **Override safety** — "I've checked the lids manually, skip that
  step". Claude will echo the override back before proceeding.

## Troubleshooting

See the troubleshooting table in `instruction.md`.

## More help

- This repo on GitHub: https://github.com/kouroshSA/ot2-vision
- OT-2 REST API docs: https://docs.opentrons.com/v2/
- Claude Code docs: https://docs.claude.com/en/docs/claude-code
