# OT-2 Lab — Setup and Operation Guide

For lab users running the Opentrons OT-2 through Claude Code on the lab control machine.

---

## Part 1 — First-time setup

### 1.1 Lab admin (one-time per machine, then once per new lab user)

**Machine prerequisites** (only on a fresh control machine):

```bash
# Install Node.js >= 18 system-wide
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
```

You also need a working copy of the repo with a valid `.env` (containing
`ANTHROPIC_API_KEY` + camera + OT-2 config) somewhere in your home dir —
the provisioning script copies it into the shared location on first run.

**Provision a new lab user:**

```bash
cd ~/Models/ot2-vision
sudo ./scripts/add-lab-user.sh <username>
```

This creates the user with all hardware/lab groups, clones the repo to
`/opt/ot2-vision`, seeds the shared `.env` (mode 640, group `ot2lab`),
installs Claude Code into the user's home, and configures their
`~/.bashrc` to auto-export `ANTHROPIC_API_KEY` so Claude Code uses
API-key billing (no `claude login` flow). A temp password is printed —
share it securely; the user is forced to change it on first login.

### 1.2 Lab user (after the admin has provisioned your account)

1. Log in as your username (SSH or local console). Set a new password
   when prompted on first login.
2. Open a fresh shell so PATH + group changes apply.
3. Verify everything is wired up:
   ```bash
   claude --version                       # Claude Code installed
   echo ${ANTHROPIC_API_KEY:0:12}         # should print: sk-ant-api03
   cd ~/ot2-vision && ls                  # symlink to /opt/ot2-vision
   ```
4. **Read `~/ot2-vision/CLAUDE.md`** — it defines the mandatory pre-run
   safety procedure (lid detection, tip map, deck verification). The
   assistant follows this on every protocol run.

---

## Part 2 — Running the OT-2 through Claude Code

### 2.1 Pre-flight checks

Before any run, verify:

```bash
# OT-2 is reachable
curl -sS -H "Opentrons-Version: 3" http://169.254.142.150:31950/health

# Both cameras enumerated
ls /dev/video*

# Conda environment for the Python pipeline
conda activate lumi-opentron
```

### 2.2 Launch Claude Code in your work directory

**Important:** Claude Code uses your current shell directory as its
working directory. Anything it generates — protocol files, capture
images, run logs — gets written there. Always `cd` to where you want
the artifacts saved before launching `claude`.

```bash
mkdir -p ~/runs/$(date +%Y%m%d)
cd ~/runs/$(date +%Y%m%d)
claude
```

### 2.3 Give the assistant a natural-language instruction

Once in Claude Code, type your protocol request. Claude will:

1. Capture from the top and side cameras
2. Run the safety checks from `CLAUDE.md` (lid, tip map, deck state)
3. Generate a Python protocol matching your request
4. Show you the deck summary and ask for go/no-go
5. Upload + execute on the OT-2 via the REST API at `169.254.142.150`
6. **Save the generated protocol file in the current directory** as
   `<short-description>.py`

**Example prompts:**

- *"Pick a tip from E7 of slot 7, aspirate 5 µL from slot 1 A1,
  dispense into slot 3 A4, drop tip, wave goodbye."*
- *"Tell me what's currently on the deck and which tip positions are
  available."*
- *"Transfer 10 µL from each well of row A on plate 1 into the
  corresponding well on plate 2."*

### 2.4 What gets saved

After a run, your work directory will contain:

| File | Purpose |
|------|---------|
| `<name>.py` | Generated OT-2 protocol (re-runnable) |
| `safety_top.jpg`, `safety_side.jpg` | Camera frames used for safety checks |
| Any output Claude was asked to save | Run logs, notes, plots |

These are yours — under your home dir, not shared with other lab members.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `claude: command not found` | Open a fresh shell (PATH update is in `~/.bashrc`) |
| `ANTHROPIC_API_KEY` is empty | You're not in `ot2lab` group — ask admin |
| `curl ... 169.254.142.150` fails | OT-2 is off, on a different network, or rebooting (allow 1–2 min after power on) |
| `/dev/video0` or `/dev/video2` missing | Camera unplugged, or USB enumeration shifted on reboot — check `v4l2-ctl --list-devices` |
| Tip pickup crashes the pipette | The rack position you targeted was empty — always visually verify the tip map before executing |
| Claude wants to `claude login` | Env var isn't set — check `echo $ANTHROPIC_API_KEY` is non-empty before launching |

---

## Quick reference

- Shared repo: `/opt/ot2-vision` (read-only for `ot2lab` members)
- Shared `.env` with lab API key: `/opt/ot2-vision/.env` (mode 640, group `ot2lab`)
- OT-2 API: `http://169.254.142.150:31950` (no auth — anyone on the lab network can reach it)
- Safety procedure: `~/ot2-vision/CLAUDE.md`
- Provisioning script: `~/ot2-vision/scripts/add-lab-user.sh`
