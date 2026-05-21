#!/usr/bin/env bash
# add-lab-user.sh — provision a new lab user on the OT-2 control machine.
#
# Creates a Linux user, adds them to the camera/USB/lab groups, installs
# Claude Code in their home, and points them at the shared ot2-vision repo
# at /opt/ot2-vision (group-readable by ot2lab members, including the .env
# with the lab Anthropic API key).
#
# Usage:  sudo ./scripts/add-lab-user.sh <username>
# Example: sudo ./scripts/add-lab-user.sh alice

set -euo pipefail

# ---- config ----
SHARED_REPO="/opt/ot2-vision"
REPO_URL="https://github.com/kouroshSA/ot2-vision.git"
LAB_GROUP="ot2lab"
HW_GROUPS=("video" "dialout" "plugdev")
# On first run only, seed /opt/ot2-vision/.env from this file (with API key etc).
# Override with: SOURCE_ENV=/path/to/.env sudo ./add-lab-user.sh <user>
# Default tries the invoking admin's working copy under their home.
SOURCE_ENV="${SOURCE_ENV:-${SUDO_USER:+/home/$SUDO_USER/Models/ot2-vision/.env}}"
MIN_NODE_MAJOR=18

# ---- args ----
if [[ $# -ne 1 ]]; then
    echo "usage: sudo $0 <username>" >&2
    exit 1
fi
USERNAME="$1"
if ! [[ "$USERNAME" =~ ^[a-z][a-z0-9_-]{2,31}$ ]]; then
    echo "Invalid username '$USERNAME' (must match [a-z][a-z0-9_-]{2,31})" >&2
    exit 1
fi
if [[ $EUID -ne 0 ]]; then
    echo "Run as root (use sudo)." >&2
    exit 1
fi

# ---- prereqs ----
command -v git >/dev/null || apt-get install -y -qq git
command -v node >/dev/null || {
    echo "Node.js is required (>= $MIN_NODE_MAJOR). Install it (e.g. via NodeSource) and re-run." >&2
    exit 1
}
NODE_MAJOR=$(node -p 'process.versions.node.split(".")[0]')
if (( NODE_MAJOR < MIN_NODE_MAJOR )); then
    echo "Node.js $NODE_MAJOR is too old; need >= $MIN_NODE_MAJOR." >&2
    exit 1
fi

# ---- 1. lab group ----
if ! getent group "$LAB_GROUP" >/dev/null; then
    groupadd "$LAB_GROUP"
    echo "Created group $LAB_GROUP"
fi

# ---- 2. shared repo at /opt/ot2-vision ----
if [[ ! -d "$SHARED_REPO/.git" ]]; then
    git clone "$REPO_URL" "$SHARED_REPO"
    echo "Cloned $REPO_URL -> $SHARED_REPO"
else
    git -C "$SHARED_REPO" pull --ff-only
    echo "Updated $SHARED_REPO"
fi
chown -R root:"$LAB_GROUP" "$SHARED_REPO"
find "$SHARED_REPO" -type d -exec chmod 2750 {} \;   # setgid so new files inherit group
find "$SHARED_REPO" -type f -exec chmod g+r {} \;

# ---- 3. shared .env (API key + camera + OT-2 IP) ----
if [[ ! -f "$SHARED_REPO/.env" ]]; then
    if [[ -f "$SOURCE_ENV" ]]; then
        cp "$SOURCE_ENV" "$SHARED_REPO/.env"
        echo "Seeded $SHARED_REPO/.env from $SOURCE_ENV"
    else
        echo "WARNING: $SOURCE_ENV not found; $SHARED_REPO/.env not created" >&2
    fi
fi
if [[ -f "$SHARED_REPO/.env" ]]; then
    chown root:"$LAB_GROUP" "$SHARED_REPO/.env"
    chmod 640 "$SHARED_REPO/.env"
fi

# ---- 4. user account ----
if id "$USERNAME" >/dev/null 2>&1; then
    echo "User $USERNAME already exists; will only update groups + tooling."
else
    TMP_PASS=$(openssl rand -base64 12)
    useradd -m -s /bin/bash "$USERNAME"
    echo "$USERNAME:$TMP_PASS" | chpasswd
    passwd -e "$USERNAME" >/dev/null   # force change on first login
    echo "Created user $USERNAME (temporary password: $TMP_PASS)"
    echo "  -> share this with them via a secure channel; they'll be forced to change it on first login."
fi

# ---- 5. group memberships ----
for g in "${HW_GROUPS[@]}" "$LAB_GROUP"; do
    usermod -aG "$g" "$USERNAME"
done
echo "$USERNAME is now in: ${HW_GROUPS[*]} $LAB_GROUP"

# ---- 6. per-user Claude Code install ----
HOME_DIR=$(getent passwd "$USERNAME" | cut -d: -f6)
sudo -u "$USERNAME" -H bash <<'EOSU'
set -euo pipefail
mkdir -p ~/.npm-global
npm config set prefix "$HOME/.npm-global" >/dev/null
export PATH="$HOME/.npm-global/bin:$PATH"
if ! command -v claude >/dev/null; then
    npm install -g @anthropic-ai/claude-code >/dev/null
fi
grep -q '.npm-global/bin' ~/.bashrc || \
    echo 'export PATH="$HOME/.npm-global/bin:$PATH"' >> ~/.bashrc
EOSU
echo "Installed Claude Code in $HOME_DIR/.npm-global"

# ---- 7. symlink shared repo into their home ----
sudo -u "$USERNAME" ln -snf "$SHARED_REPO" "$HOME_DIR/ot2-vision"

# ---- 8. summary ----
cat <<MSG

==============================================================
DONE — $USERNAME provisioned.

Tell them:
  1. Log in as $USERNAME (SSH or local console). They'll be prompted to set
     a new password on first login.
  2. Open a fresh shell so the PATH update + group changes apply
     (or run:  newgrp $LAB_GROUP  then re-source ~/.bashrc).
  3. Verify Claude Code:    claude --version
  4. cd ~/ot2-vision        # symlink to the shared repo
  5. Read ~/ot2-vision/CLAUDE.md for the mandatory pre-run safety checks.
  6. Authenticate Claude Code with the lab API key (one-time):
        export ANTHROPIC_API_KEY=\$(grep ^ANTHROPIC_API_KEY \\
            ~/ot2-vision/.env | cut -d= -f2-)
     Or use:  claude config set api-key <key>

Lab API key + camera + OT-2 IP all live in $SHARED_REPO/.env
(mode 640, group $LAB_GROUP — readable only by lab members).
==============================================================
MSG
