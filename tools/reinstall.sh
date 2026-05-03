#!/bin/bash
# tools/reinstall.sh — Full clean-slate reinstall of Montage on Toolforge.
#
# Run from the bastion as the tool account:
#   become montage-dev   (NOT montage — production is blocked)
#   bash ~/www/python/src/tools/reinstall.sh
#
# After this script completes, one manual step remains (must run inside the
# webservice shell pod):
#   toolforge webservice python3.13 shell
#   bash ~/www/python/src/tools/reinstall_venv.sh
#   exit
#   cd ~ && toolforge webservice python3.13 start

set -e

if ! command -v toolforge >/dev/null 2>&1; then
    echo ""
    echo "################################################################"
    echo "#                                                              #"
    echo "#   ERROR: This script must run on Toolforge, not locally.    #"
    echo "#   Running it on your local machine will wipe your home      #"
    echo "#   directory. SSH to the bastion first:                      #"
    echo "#     ssh <user>@login.toolforge.org && become montage-dev    #"
    echo "#                                                              #"
    echo "################################################################"
    echo ""
    exit 1
fi

SRC="$HOME/www/python/src"
BACKUP="$HOME/backup"
REPO="https://github.com/hatnote/montage.git"
BRANCH="${BRANCH:-montage-dev}"

# ── helpers ──────────────────────────────────────────────────────────────────

confirm() {
    local answer
    read -r -p "$1 [y/N] " answer
    case "$answer" in
        [yY][eE][sS]|[yY]) return 0 ;;
        *) return 1 ;;
    esac
}

abort() {
    echo ""
    echo "Aborted."
    exit 0
}

parse_db_name() {
    python3 -c "
import re, sys
try:
    content = open(sys.argv[1]).read()
    m = re.search(r'@[^/]+/([^?\"\\s]+)', content)
    print(m.group(1) if m else '')
except Exception:
    print('')
" "$1" 2>/dev/null
}

# ── production guard ─────────────────────────────────────────────────────────

TOOL=$(id -un | sed 's/^tools\.//')

if [ "$TOOL" = "montage" ]; then
    echo ""
    echo "################################################################"
    echo "#                                                              #"
    echo "#   ERROR: This script refuses to run on the production tool  #"
    echo "#   account (montage). It is only safe on montage-dev or      #"
    echo "#   montage-beta.                                              #"
    echo "#                                                              #"
    echo "################################################################"
    echo ""
    exit 1
fi

# ── warning ──────────────────────────────────────────────────────────────────

echo ""
echo "################################################################"
echo "#                                                              #"
echo "#   WARNING: FULL REINSTALL — DATA WILL BE PERMANENTLY LOST   #"
echo "#                                                              #"
echo "#   This script will:                                         #"
echo "#     - DESTROY THE DATABASE (all campaigns, rounds, votes)   #"
echo "#     - Wipe ~/www/python/ (repo + venv)                      #"
echo "#     - Clone a fresh copy of the repo ($BRANCH)              #"
echo "#     - Re-initialise an empty database schema                #"
echo "#                                                              #"
echo "#   Tool account : $TOOL                                       #"
echo "#   replica.my.cnf and config YAML will be preserved.         #"
echo "#                                                              #"
echo "################################################################"
echo ""

confirm "Are you sure you want to continue?" || abort

# ── 1. service check ─────────────────────────────────────────────────────────

echo ""
echo "── Checking running services..."

for pyver in python3.13 python3.12 python3.11; do
    if toolforge webservice "$pyver" stop 2>/dev/null; then
        if [ "$pyver" != "python3.13" ]; then
            echo ""
            echo "   WARNING: service was running as $pyver (expected python3.13)."
            echo "   This suggests a previous install used a different Python version."
            confirm "   Continue anyway?" || abort
        else
            echo "   Stopped python3.13 webservice."
        fi
    fi
done
echo "   Service check done."

# ── 2. backup ────────────────────────────────────────────────────────────────

echo ""
echo "── Backing up irreplaceable files to $BACKUP..."
mkdir -p "$BACKUP"

cp ~/replica.my.cnf "$BACKUP/"
echo "   Backed up replica.my.cnf"

CONFIG_COUNT=0
for f in "$SRC"/config.*.yaml; do
    [ -f "$f" ] || continue
    cp "$f" "$BACKUP/"
    echo "   Backed up $(basename "$f")"
    CONFIG_COUNT=$((CONFIG_COUNT + 1))
done

if [ "$CONFIG_COUNT" -eq 0 ]; then
    echo ""
    echo "   WARNING: no config.*.yaml found — you will need to create it"
    echo "   manually after reinstall (see step 6 of deployment.md)."
    confirm "   Continue without a config backup?" || abort
fi

# Dump organizer usernames from database before the wipe
CONFIG_FILE=$(ls "$SRC"/config.*.yaml 2>/dev/null | head -1)
if [ -n "$CONFIG_FILE" ]; then
    DB_NAME=$(parse_db_name "$CONFIG_FILE")
    if [ -n "$DB_NAME" ]; then
        if mariadb --defaults-file=~/replica.my.cnf \
               -h tools.db.svc.wikimedia.cloud \
               -N -e "SELECT username FROM users WHERE is_organizer=1;" \
               "$DB_NAME" > "$BACKUP/organizers.txt" 2>/dev/null; then
            ORGANIZER_COUNT=$(wc -l < "$BACKUP/organizers.txt" | tr -d ' ')
            echo "   Backed up $ORGANIZER_COUNT organizer(s) to organizers.txt"
        else
            echo "   WARNING: could not dump organizers (DB may not exist or schema not initialised)"
            rm -f "$BACKUP/organizers.txt"
        fi
    else
        echo "   WARNING: could not parse db_url from config — skipping organizer backup"
    fi
fi

# ── 3. confirm wipe ──────────────────────────────────────────────────────────

echo ""
echo "── The following will be deleted from ~:"
ls -A ~ | grep -v '^replica\.my\.cnf$' | grep -v '^backup$' | sed 's/^/     /'
echo ""
confirm "Wipe everything listed above? This cannot be undone." || abort

# ── 4. wipe ──────────────────────────────────────────────────────────────────
# NOTE: this script file lives inside ~/www/python/src/ and is deleted here.
# That is safe — bash has already loaded the entire script into memory.
# From this point on we handle errors explicitly (set -e is still active but
# we check the clone step manually since failure here leaves a wiped home dir).

echo ""
echo "── Wiping..."
cd ~
for item in $(ls -A | grep -v '^replica\.my\.cnf$' | grep -v '^backup$'); do
    rm -rf "$item"
done
echo "   Done."

# ── 5. clone ─────────────────────────────────────────────────────────────────

echo ""
echo "── Cloning $REPO (branch: $BRANCH)..."
mkdir -p ~/www/python

if ! git clone --branch "$BRANCH" "$REPO" "$SRC"; then
    echo ""
    echo "ERROR: git clone failed. Your home directory has been wiped."
    echo "To recover manually:"
    echo "  git clone --branch $BRANCH $REPO $SRC"
    echo "  cp $BACKUP/config.*.yaml $SRC/"
    exit 1
fi
echo "   Cloned to $SRC"

# ── 6. restore config ────────────────────────────────────────────────────────

echo ""
echo "── Restoring config..."
RESTORED=0
for f in "$BACKUP"/config.*.yaml; do
    [ -f "$f" ] || continue
    cp "$f" "$SRC/"
    chmod 600 "$SRC/$(basename "$f")"
    echo "   Restored $(basename "$f")"
    RESTORED=$((RESTORED + 1))
done

if [ "$RESTORED" -eq 0 ]; then
    echo ""
    echo "   WARNING: no config found in $BACKUP."
    echo "   Creating a blank config from the default template..."
    TOOL_FULL="tools.$TOOL"
    ENV_NAME=$(python3 -c "
import re
content = open('$SRC/montage/utils.py').read()
m = re.search(r\"'$TOOL_FULL'\\\\s*:\\\\s*'([^']+)'\", content)
print(m.group(1) if m else 'default')
" 2>/dev/null)
    CONFIG_NEW="$SRC/config.${ENV_NAME}.yaml"
    cp "$SRC/config.default.yaml" "$CONFIG_NEW"
    chmod 600 "$CONFIG_NEW"
    echo "   Created $(basename "$CONFIG_NEW") — you will be prompted to fill in required values."
fi

# ── validate / fill in config ─────────────────────────────────────────────────

echo ""
echo "── Checking config..."
bash "$SRC/tools/steps/configure.sh"

# ── 7. frontend ──────────────────────────────────────────────────────────────

echo ""
echo "── Building frontend..."
bash "$SRC/tools/build_frontend.sh"

# ── 8. schema ────────────────────────────────────────────────────────────────

echo ""
echo "── Initialising database schema..."
source "$HOME/www/python/venv/bin/activate" 2>/dev/null || {
    echo "   WARNING: venv not found — skipping schema init."
    echo "   Run tools/reinstall_venv.sh first, then: python3 $SRC/tools/create_schema.py"
    SKIP_SCHEMA=1
}

if [ -z "$SKIP_SCHEMA" ]; then
    python3 "$SRC/tools/create_schema.py"
    echo "   Schema initialised."

    # Re-insert organizers
    if [ -f "$BACKUP/organizers.txt" ] && [ -s "$BACKUP/organizers.txt" ]; then
        CONFIG_FILE=$(ls "$SRC"/config.*.yaml 2>/dev/null | head -1)
        DB_NAME=$([ -n "$CONFIG_FILE" ] && parse_db_name "$CONFIG_FILE" || echo "")
        if [ -n "$DB_NAME" ]; then
            echo ""
            echo "── Restoring organizers..."
            while IFS= read -r username; do
                [ -z "$username" ] && continue
                mariadb --defaults-file=~/replica.my.cnf \
                    -h tools.db.svc.wikimedia.cloud \
                    -e "INSERT INTO users (username, is_organizer) VALUES ('$username', 1) ON DUPLICATE KEY UPDATE is_organizer=1;" \
                    "$DB_NAME" 2>/dev/null && echo "   Restored organizer: $username" \
                    || echo "   WARNING: could not restore organizer: $username"
            done < "$BACKUP/organizers.txt"
        else
            echo "   WARNING: could not parse db_url — organizers not restored"
            echo "   They are saved in $BACKUP/organizers.txt for manual restore."
        fi
    fi
fi

# ── 9. venv health check ─────────────────────────────────────────────────────

VENV="$HOME/www/python/venv"
if [ ! -f "$VENV/bin/python3" ] || ! "$VENV/bin/python3" -c "import urllib3" 2>/dev/null; then
    echo ""
    echo "   NOTE: venv not yet set up — this is expected."
    echo "   Complete the install by running the step below."
fi

# ── done ─────────────────────────────────────────────────────────────────────

echo ""
echo "################################################################"
echo "#   Almost done — one step requires the webservice shell:      #"
echo "#                                                              #"
echo "#   toolforge webservice python3.13 shell                     #"
echo "#   bash ~/www/python/src/tools/reinstall_venv.sh             #"
echo "#   exit                                                       #"
echo "#   cd ~ && toolforge webservice python3.13 start             #"
echo "#                                                              #"
echo "################################################################"
echo ""
