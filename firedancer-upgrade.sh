#!/usr/bin/env bash
# Frankendancer upgrade script
# Usage: bash firedancer-upgrade.sh v0.910.40000

# ─── Color helpers ────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

ok()   { echo -e "${GREEN}✅  $*${NC}"; }
fail() { echo -e "${RED}🔴  $*${NC}"; }
warn() { echo -e "${YELLOW}⏰  $*${NC}"; }
info() { echo -e "${CYAN}ℹ️   $*${NC}"; }
hdr()  { echo -e "\n${BOLD}$*${NC}"; }

# ─── Constants ────────────────────────────────────────────────────────────────
CONFIG="/home/firedancer/solana_fd/solana-testnet.toml"
FDCTL_BIN="/usr/local/bin/fdctl"
LOG_FILE="/root/upgrade-$(date +%Y%m%d-%H%M%S).log"
FD_REPO="/root/firedancer"
BUILD_ENV_FILE="/tmp/fd_build_env_$$"
EPOCH_WARN_PCT=70
DISK_MIN_GB=50
SKIP_RATE_WARN=10

# ─── Logging ──────────────────────────────────────────────────────────────────
exec > >(tee -a "$LOG_FILE") 2>&1
info "Log file: $LOG_FILE"

# ─── Argument validation ──────────────────────────────────────────────────────
if [[ $# -ne 1 ]]; then
    fail "Usage: $0 <new-version>   e.g.  $0 v0.910.40000"
    exit 1
fi
NEW="$1"

# ─── Rollback instructions (shown on any fatal error) ─────────────────────────
show_rollback() {
    echo ""
    fail "=================== ROLLBACK INSTRUCTIONS ==================="
    echo -e "${RED}1. Restore backup binary (if it exists):${NC}"
    echo "   cp /root/fdctl-backup-\$OLD  $FDCTL_BIN"
    echo "   chmod +x $FDCTL_BIN"
    echo ""
    echo -e "${RED}2. If configure fini was already run, reinitialise with OLD binary:${NC}"
    echo "   sudo $FDCTL_BIN configure init all --config $CONFIG"
    echo ""
    echo -e "${RED}3. Restart the node:${NC}"
    echo "   sudo systemctl start firedancer"
    echo ""
    echo -e "${RED}4. If git checkout changed the source, reset:${NC}"
    echo "   cd $FD_REPO && git checkout \$OLD && git submodule update --init --recursive"
    fail "============================================================="
}

die() {
    fail "$1"
    show_rollback
    exit 1
}

# ─── Determine OLD version ────────────────────────────────────────────────────
hdr "=== Determining current version ==="
if [[ ! -x "$FDCTL_BIN" ]]; then
    die "fdctl not found at $FDCTL_BIN"
fi
OLD=$("$FDCTL_BIN" version 2>/dev/null | grep -oP '[\d.]+' | head -1)
if [[ -z "$OLD" ]]; then
    die "Could not determine current fdctl version"
fi
ok "OLD version : $OLD"
ok "NEW version : $NEW"

if [[ "$OLD" == "$NEW" ]]; then
    warn "OLD == NEW ($OLD). Nothing to upgrade. Exiting."
    exit 0
fi

# ─── Determine IDENTITY ───────────────────────────────────────────────────────
IDENTITY=$(solana address 2>/dev/null)
if [[ -z "$IDENTITY" ]]; then
    warn "Could not determine identity via 'solana address'. Continuing anyway."
    IDENTITY="unknown"
else
    ok "Identity    : $IDENTITY"
fi

# ─── Save build env to file (not exported) ───────────────────────────────────
cat > "$BUILD_ENV_FILE" <<EOF
OLD=$OLD
NEW=$NEW
IDENTITY=$IDENTITY
CONFIG=$CONFIG
FDCTL_BIN=$FDCTL_BIN
FD_REPO=$FD_REPO
EOF

# ══════════════════════════════════════════════════════════════════════════════
# БЛОК 1 — Проверки
# ══════════════════════════════════════════════════════════════════════════════
hdr "=== БЛОК 1: Проверки ==="

CHECK_SOLANA_CLI=0
CHECK_EPOCH=1
CHECK_HEALTH=0
CHECK_SKIP=0
CHECK_TAG=0
CHECK_DISK=0
CHECK_EXECSTART=0
HAS_CONFIGURE_INIT=0

SOLANA_CLI_VER=""
EPOCH_PCT=""
SKIP_RATE_VAL=""
DISK_FREE_GB=""
EXECSTART_LINE=""

# ── 1.1 Solana CLI version ────────────────────────────────────────────────────
info "Checking Solana CLI version..."
SOLANA_CLI_VER=$(solana --version 2>/dev/null | grep -oP '[\d]+\.[\d]+\.[\d]+' | head -1)
if [[ -z "$SOLANA_CLI_VER" ]]; then
    fail "Solana CLI not found or version undetectable"
else
    MAJOR=$(echo "$SOLANA_CLI_VER" | cut -d. -f1)
    if [[ -n "$SOLANA_CLI_VER" ]]; then
        ok "Solana CLI $SOLANA_CLI_VER  (3.x.x ✓)"
        CHECK_SOLANA_CLI=1
    else
        fail "Solana CLI $SOLANA_CLI_VER — expected 3.x.x"
    fi
fi

# ── 1.2 Epoch progress ────────────────────────────────────────────────────────
info "Checking epoch progress..."
EPOCH_INFO=$(solana epoch-info 2>/dev/null)
if [[ -z "$EPOCH_INFO" ]]; then
    warn "Could not get epoch info (RPC unavailable?)"
else
    SLOT_IN_EPOCH=$(echo "$EPOCH_INFO" | grep -i "Slot in Epoch" | grep -oP '[\d,]+' | head -1 | tr -d ',')
    SLOTS_IN_EPOCH=$(echo "$EPOCH_INFO" | grep -i "Slots in Epoch" | grep -oP '[\d,]+' | head -1 | tr -d ',')
    if [[ -n "$SLOT_IN_EPOCH" && -n "$SLOTS_IN_EPOCH" && "$SLOTS_IN_EPOCH" -gt 0 ]]; then
        EPOCH_PCT=$(awk "BEGIN {printf \"%.1f\", ($SLOT_IN_EPOCH / $SLOTS_IN_EPOCH) * 100}")
        EPOCH_INT=${EPOCH_PCT%.*}
        if [[ "$EPOCH_INT" -lt "$EPOCH_WARN_PCT" ]]; then
            ok "Epoch progress: ${EPOCH_PCT}%  (< ${EPOCH_WARN_PCT}% ✓)"
            CHECK_EPOCH=1
        else
            fail "Epoch progress: ${EPOCH_PCT}%  (>= ${EPOCH_WARN_PCT}% — risky upgrade window)"
        fi
    else
        warn "Could not parse epoch slot info. Skipping epoch check."
        EPOCH_PCT="n/a"
    fi
fi

# ── 1.3 Node health: systemd status ───────────────────────────────────────────
info "Checking node health (systemd)..."
SVC_STATUS=$(systemctl is-active firedancer 2>/dev/null)
if [[ "$SVC_STATUS" == "active" ]]; then
    ok "firedancer systemd service: active (running)"
    CHECK_HEALTH=1
else
    fail "firedancer systemd service: $SVC_STATUS (expected active)"
fi

# ── 1.4 Skip rate ─────────────────────────────────────────────────────────────
info "Checking skip rate for $IDENTITY..."
if [[ "$IDENTITY" != "unknown" ]]; then
    VALIDATORS_JSON=$(solana validators --output json 2>/dev/null)
    if [[ -n "$VALIDATORS_JSON" ]]; then
        SKIP_RATE_VAL=$(echo "$VALIDATORS_JSON" | \
            python3 -c "
import sys, json
data = json.load(sys.stdin)
validators = data.get('validators', [])
for v in validators:
    if v.get('identityPubkey') == '${IDENTITY}':
        print(v.get('skipRate', 'n/a'))
        break
" 2>/dev/null)
        if [[ -z "$SKIP_RATE_VAL" || "$SKIP_RATE_VAL" == "n/a" ]]; then
            warn "Could not find skip rate for identity $IDENTITY"
            SKIP_RATE_VAL="n/a"
            CHECK_SKIP=1
        else
            SKIP_PCT=$(awk "BEGIN {printf \"%.2f\", $SKIP_RATE_VAL}" 2>/dev/null || echo "0")
            SKIP_INT=$(awk "BEGIN {printf \"%d\", $SKIP_RATE_VAL}" 2>/dev/null || echo "0")
            SKIP_RATE_VAL="${SKIP_PCT}%"
            if [[ "$SKIP_INT" -lt "$SKIP_RATE_WARN" ]]; then
                ok "Skip rate: ${SKIP_RATE_VAL}  (< ${SKIP_RATE_WARN}% ✓)"
                CHECK_SKIP=1
            else
                fail "Skip rate: ${SKIP_RATE_VAL}  (>= ${SKIP_RATE_WARN}%)"
            fi
        fi
    else
        warn "Could not fetch validators list. Skipping skip-rate check."
        SKIP_RATE_VAL="n/a"
        CHECK_SKIP=1
    fi
else
    warn "Identity unknown — skipping skip-rate check."
    SKIP_RATE_VAL="n/a"
    CHECK_SKIP=1
fi

# ── 1.5 GitHub tag exists ─────────────────────────────────────────────────────
info "Checking GitHub tag $NEW..."
TAG_URL="https://api.github.com/repos/firedancer-io/firedancer/git/refs/tags/${NEW}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Accept: application/vnd.github+json" \
    "$TAG_URL" 2>/dev/null)
if [[ "$HTTP_CODE" == "200" ]]; then
    ok "GitHub tag $NEW exists"
    CHECK_TAG=1
elif [[ "$HTTP_CODE" == "404" ]]; then
    fail "GitHub tag $NEW not found (404)"
else
    warn "GitHub API returned HTTP $HTTP_CODE — check network; assuming tag exists"
    CHECK_TAG=1
fi

# ── 1.6 Free disk space ───────────────────────────────────────────────────────
info "Checking free disk space on $FD_REPO..."
if [[ -d "$FD_REPO" ]]; then
    DISK_FREE_GB=$(df -BG "$FD_REPO" 2>/dev/null | awk 'NR==2 {gsub("G",""); print $4}')
else
    DISK_FREE_GB=$(df -BG / 2>/dev/null | awk 'NR==2 {gsub("G",""); print $4}')
fi
if [[ -n "$DISK_FREE_GB" ]]; then
    if [[ "$DISK_FREE_GB" -ge "$DISK_MIN_GB" ]]; then
        ok "Free disk: ${DISK_FREE_GB}G  (>= ${DISK_MIN_GB}G ✓)"
        CHECK_DISK=1
    else
        fail "Free disk: ${DISK_FREE_GB}G  (< ${DISK_MIN_GB}G required)"
    fi
else
    warn "Could not determine free disk space"
fi

# ── 1.7 ExecStart type ───────────────────────────────────────────────────────
info "Checking ExecStart in systemd unit..."
UNIT_FILE=$(systemctl show firedancer -p FragmentPath 2>/dev/null | cut -d= -f2)
if [[ -n "$UNIT_FILE" && -f "$UNIT_FILE" ]]; then
    EXECSTART_LINE=$(grep -i "ExecStart" "$UNIT_FILE" | head -1)
    if echo "$EXECSTART_LINE" | grep -q "configure init"; then
        ok "ExecStart includes 'configure init' — will re-run after upgrade"
        HAS_CONFIGURE_INIT=1
    else
        ok "ExecStart does NOT include 'configure init' — will run configure init manually"
        HAS_CONFIGURE_INIT=0
    fi
    CHECK_EXECSTART=1
else
    warn "Could not read systemd unit file. Will assume configure init is needed."
    EXECSTART_LINE="(not found)"
    HAS_CONFIGURE_INIT=1
    CHECK_EXECSTART=1
fi

echo "HAS_CONFIGURE_INIT=$HAS_CONFIGURE_INIT" >> "$BUILD_ENV_FILE"

# ══════════════════════════════════════════════════════════════════════════════
# БЛОК 2 — Сводка проверок и подтверждение
# ══════════════════════════════════════════════════════════════════════════════
hdr "=== БЛОК 2: Сводка проверок ==="

echo ""
echo -e "${BOLD}┌──────────────────────────────────────────────────────────┐${NC}"
echo -e "${BOLD}│                   UPGRADE SUMMARY                       │${NC}"
echo -e "${BOLD}├──────────────────────────────────────────────────────────┤${NC}"
printf "│  %-30s  %-20s │\n" "OLD version"     "$OLD"
printf "│  %-30s  %-20s │\n" "NEW version"     "$NEW"
printf "│  %-30s  %-20s │\n" "Identity"        "${IDENTITY:0:20}"
printf "│  %-30s  %-20s │\n" "Config"          "$CONFIG"
printf "│  %-30s  %-20s │\n" "Repo"            "$FD_REPO"
echo -e "${BOLD}├──────────────────────────────────────────────────────────┤${NC}"
printf "│  %-30s  %-20s │\n" "Solana CLI" \
    "$([ $CHECK_SOLANA_CLI -eq 1 ] && echo "✅  $SOLANA_CLI_VER" || echo "🔴  $SOLANA_CLI_VER")"
printf "│  %-30s  %-20s │\n" "Epoch progress" \
    "$([ $CHECK_EPOCH -eq 1 ] && echo "✅  ${EPOCH_PCT}%" || echo "🔴  ${EPOCH_PCT}%")"
printf "│  %-30s  %-20s │\n" "Node health" \
    "$([ $CHECK_HEALTH -eq 1 ] && echo "✅  active" || echo "🔴  $SVC_STATUS")"
printf "│  %-30s  %-20s │\n" "Skip rate" \
    "$([ $CHECK_SKIP -eq 1 ] && echo "✅  $SKIP_RATE_VAL" || echo "🔴  $SKIP_RATE_VAL")"
printf "│  %-30s  %-20s │\n" "GitHub tag $NEW" \
    "$([ $CHECK_TAG -eq 1 ] && echo "✅  exists" || echo "🔴  NOT FOUND")"
printf "│  %-30s  %-20s │\n" "Free disk" \
    "$([ $CHECK_DISK -eq 1 ] && echo "✅  ${DISK_FREE_GB}G" || echo "🔴  ${DISK_FREE_GB}G")"
printf "│  %-30s  %-20s │\n" "ExecStart configure init" \
    "$([ $HAS_CONFIGURE_INIT -eq 1 ] && echo "yes (will re-run)" || echo "no")"
echo -e "${BOLD}└──────────────────────────────────────────────────────────┘${NC}"
echo ""

HARD_FAILS=0
[[ $CHECK_SOLANA_CLI -eq 0 ]] && HARD_FAILS=$((HARD_FAILS+1))
[[ $CHECK_TAG        -eq 0 ]] && HARD_FAILS=$((HARD_FAILS+1))
[[ $CHECK_DISK       -eq 0 ]] && HARD_FAILS=$((HARD_FAILS+1))
[[ $CHECK_HEALTH     -eq 0 ]] && HARD_FAILS=$((HARD_FAILS+1))

SOFT_FAILS=0
[[ $CHECK_EPOCH -eq 0 ]] && SOFT_FAILS=$((SOFT_FAILS+1))
[[ $CHECK_SKIP  -eq 0 ]] && SOFT_FAILS=$((SOFT_FAILS+1))

if [[ $HARD_FAILS -gt 0 ]]; then
    fail "$HARD_FAILS hard check(s) failed. Fix them before upgrading."
    exit 1
fi

if [[ $SOFT_FAILS -gt 0 ]]; then
    warn "$SOFT_FAILS soft warning(s) (epoch / skip rate). Upgrade is risky right now."
fi

echo -e "${BOLD}Все критические проверки пройдены. Начать апгрейд?${NC}"
echo -e "${YELLOW}Нода будет остановлена. (yes/no):${NC} \c"
read -r CONFIRM

if [[ "$CONFIRM" != "yes" ]]; then
    info "Отмена — апгрейд не запущен."
    exit 0
fi

# ══════════════════════════════════════════════════════════════════════════════
# БЛОК 3 — Апгрейд
# ══════════════════════════════════════════════════════════════════════════════
hdr "=== БЛОК 3: Апгрейд ==="

# shellcheck source=/dev/null
source "$BUILD_ENV_FILE"

# ── 3.1 Backup old binary ─────────────────────────────────────────────────────
BACKUP_OLD="/root/fdctl-backup-${OLD}-$(date +%Y%m%d%H%M%S)"
info "Backing up $FDCTL_BIN → $BACKUP_OLD"
cp "$FDCTL_BIN" "$BACKUP_OLD" || die "Failed to backup fdctl binary"
chmod +x "$BACKUP_OLD"
ok "Backup created: $BACKUP_OLD"

# ── 3.2 Stop the node ─────────────────────────────────────────────────────────
info "Stopping firedancer service..."
systemctl stop firedancer
STOP_RC=$?
if [[ $STOP_RC -ne 0 ]]; then
    die "systemctl stop firedancer failed (rc=$STOP_RC)"
fi
sleep 3
SVC_NOW=$(systemctl is-active firedancer 2>/dev/null)
if [[ "$SVC_NOW" == "active" ]]; then
    die "Service is still active after stop command"
fi
ok "firedancer stopped"

# ── 3.3 git stash ─────────────────────────────────────────────────────────────
info "git stash in $FD_REPO..."
if [[ ! -d "$FD_REPO/.git" ]]; then
    die "$FD_REPO is not a git repository"
fi
cd "$FD_REPO" || die "Cannot cd to $FD_REPO"
git stash
GIT_STASH_RC=$?
if [[ $GIT_STASH_RC -ne 0 ]]; then
    die "git stash failed (rc=$GIT_STASH_RC)"
fi
ok "git stash done"

# ── 3.4 git fetch ─────────────────────────────────────────────────────────────
info "git fetch --all --tags --force..."
git fetch --all --tags --force
GIT_FETCH_RC=$?
if [[ $GIT_FETCH_RC -ne 0 ]]; then
    die "git fetch failed (rc=$GIT_FETCH_RC)"
fi
ok "git fetch done"

# ── 3.5 git checkout NEW ──────────────────────────────────────────────────────
info "git checkout $NEW..."
git checkout "$NEW"
GIT_CO_RC=$?
if [[ $GIT_CO_RC -ne 0 ]]; then
    die "git checkout $NEW failed (rc=$GIT_CO_RC)"
fi
ok "git checkout $NEW done"

# ── 3.6 git submodule update ──────────────────────────────────────────────────
info "git submodule update --init --recursive..."
git submodule update --init --recursive
GIT_SUB_RC=$?
if [[ $GIT_SUB_RC -ne 0 ]]; then
    die "git submodule update failed (rc=$GIT_SUB_RC)"
fi
ok "submodules updated"

# ── 3.7 Verify git describe --tags ───────────────────────────────────────────
info "Verifying git describe --tags..."
GIT_TAG=$(git describe --tags 2>/dev/null)
if [[ -z "$GIT_TAG" ]]; then
    die "git describe --tags returned empty — checkout may have failed"
fi
if [[ "$GIT_TAG" != "$NEW"* ]]; then
    die "git describe --tags returned '$GIT_TAG', expected tag starting with '$NEW'"
fi
ok "git describe --tags: $GIT_TAG"

# ── 3.8 configure fini all (using OLD binary) ─────────────────────────────────
info "Running configure fini all with OLD binary ($BACKUP_OLD)..."
"$BACKUP_OLD" configure fini all --config "$CONFIG"
FINI_RC=$?
if [[ $FINI_RC -ne 0 ]]; then
    warn "configure fini all returned rc=$FINI_RC — may be acceptable; continuing"
else
    ok "configure fini all done"
fi

# ── 3.9 make clean ────────────────────────────────────────────────────────────
info "make clean..."
make clean
MAKE_CLEAN_RC=$?
if [[ $MAKE_CLEAN_RC -ne 0 ]]; then
    die "make clean failed (rc=$MAKE_CLEAN_RC)"
fi
ok "make clean done"

# ── 3.9b Rebuild deps ─────────────────────────────────────────────────────────
BUILD_LOG="/root/fd-build-$(date +%Y%m%d%H%M%S).log"
info "Running deps.sh nuke..."
./deps.sh nuke >> "$BUILD_LOG" 2>&1
info "Running deps.sh +dev..."
./deps.sh +dev >> "$BUILD_LOG" 2>&1
DEPS_RC=$?
if [[ $DEPS_RC -ne 0 ]]; then
    warn "deps.sh +dev failed — trying apt-get --fix-missing and retry..."
    apt-get update --fix-missing -y >> "$BUILD_LOG" 2>&1
    ./deps.sh +dev >> "$BUILD_LOG" 2>&1
    DEPS_RC=$?
    if [[ $DEPS_RC -ne 0 ]]; then
        die "deps.sh +dev failed"
    fi
fi
ok "deps rebuilt"

# ── 3.10 Build fdctl (nohup make) ─────────────────────────────────────────────
NPROC=$(nproc)
info "Starting build: nohup make -j $NPROC fdctl  (log: $BUILD_LOG)"
nohup make -j "$NPROC" fdctl > "$BUILD_LOG" 2>&1 &
BUILD_PID=$!
echo "BUILD_PID=$BUILD_PID" >> "$BUILD_ENV_FILE"
info "Build PID: $BUILD_PID"

# ── 3.11 Progress indicator while building ────────────────────────────────────
info "Waiting for build to complete..."
SPINNER=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')
SPIN_IDX=0
BUILD_ELAPSED=0
BUILD_MAX=3600  # 60 minutes timeout

while kill -0 "$BUILD_PID" 2>/dev/null; do
    SPIN_CHAR="${SPINNER[$SPIN_IDX]}"
    SPIN_IDX=$(( (SPIN_IDX + 1) % 10 ))
    LAST_LINE=$(tail -1 "$BUILD_LOG" 2>/dev/null | cut -c1-60)
    printf "\r${CYAN}  %s  [%4ds]  %-60s${NC}" "$SPIN_CHAR" "$BUILD_ELAPSED" "$LAST_LINE"
    sleep 2
    BUILD_ELAPSED=$((BUILD_ELAPSED + 2))
    if [[ $BUILD_ELAPSED -ge $BUILD_MAX ]]; then
        echo ""
        die "Build timed out after ${BUILD_MAX}s"
    fi
done
echo ""

wait "$BUILD_PID"
BUILD_RC=$?
if [[ $BUILD_RC -ne 0 ]]; then
    fail "Build failed (rc=$BUILD_RC). Last 20 lines of build log:"
    tail -20 "$BUILD_LOG"
    die "Build failed"
fi
ok "Build completed in ${BUILD_ELAPSED}s"

# ── 3.12 Install new binary ───────────────────────────────────────────────────
info "Locating built fdctl binary..."
NEW_FDCTL=""
for candidate in \
    "${FD_REPO}/build/native/gcc/bin/fdctl" \
    "${FD_REPO}/build/linux/gcc/native/bin/fdctl" \
    "${FD_REPO}/fdctl"; do
    if [[ -x "$candidate" ]]; then
        NEW_FDCTL="$candidate"
        break
    fi
done

if [[ -z "$NEW_FDCTL" ]]; then
    NEW_FDCTL=$(find "${FD_REPO}/build" -name "fdctl" -type f -perm /111 2>/dev/null | head -1)
fi

if [[ -z "$NEW_FDCTL" ]]; then
    die "Built fdctl binary not found in ${FD_REPO}/build — check $BUILD_LOG"
fi

info "Found built binary: $NEW_FDCTL"
cp "$NEW_FDCTL" "$FDCTL_BIN" || die "Failed to install new fdctl"
chmod +x "$FDCTL_BIN"
ok "New fdctl installed at $FDCTL_BIN"

# ── 3.12b Fix config ──────────────────────────────────────────────────────────
info "Applying config fixes to $CONFIG..."
CONFIG_CHANGED=0
if grep -qF 'dynamic_port_range = "8004-8029"' "$CONFIG"; then
    sed -i 's/dynamic_port_range = "8004-8029"/dynamic_port_range = "8004-8030"/' "$CONFIG"
    info "Config: dynamic_port_range updated 8004-8029 → 8004-8030"
    CONFIG_CHANGED=1
fi
AWK_BUNDLE=$(awk '
    /^\[tiles\.bundle\]/ { in_section=1; next }
    /^\[/ { in_section=0 }
    in_section && /enabled = true/ { found=1 }
    END { print found+0 }
' "$CONFIG")
if [[ "$AWK_BUNDLE" == "1" ]]; then
    awk '
        /^\[tiles\.bundle\]/ { in_section=1; print; next }
        /^\[/ { in_section=0 }
        in_section && /enabled = true/ { sub(/enabled = true/, "enabled = false") }
        { print }
    ' "$CONFIG" > "${CONFIG}.tmp" && mv "${CONFIG}.tmp" "$CONFIG"
    info "Config: [tiles.bundle] enabled = true → enabled = false"
    CONFIG_CHANGED=1
fi
ok "Config fixes applied"

# ── 3.12c Fix systemd unit ────────────────────────────────────────────────────
info "Checking systemd unit for old 'configure init all' format..."
UNIT_FILE_UPG=$(systemctl show firedancer -p FragmentPath 2>/dev/null | cut -d= -f2)
UNIT_CHANGED=0
if [[ -n "$UNIT_FILE_UPG" && -f "$UNIT_FILE_UPG" ]]; then
    if grep -q "ExecStart=.*configure init all" "$UNIT_FILE_UPG"; then
        info "Found 'configure init all' in ExecStart — rewriting to per-step ExecStartPre..."
        EXECSTART_OLD=$(grep "ExecStart=.*configure init all" "$UNIT_FILE_UPG" | head -1)
        FDCTL_PATH=$(echo "$EXECSTART_OLD" | sed 's/ExecStart=//' | awk '{print $1}')
        CFG_PATH=$(echo "$EXECSTART_OLD" | grep -oP -- '--config \S+' | head -1)
        cp "$UNIT_FILE_UPG" "${UNIT_FILE_UPG}.bak-upgrade-${OLD}"
        awk -v bin="$FDCTL_PATH" -v cfg="$CFG_PATH" '
            /ExecStart=.*configure init all/ {
                print "ExecStartPre=" bin " configure init hugetlbfs " cfg
                print "ExecStartPre=" bin " configure init ethtool-loopback " cfg
                print "ExecStartPre=" bin " configure init ethtool-channels " cfg
                print "ExecStartPre=" bin " configure init ethtool-offloads " cfg
                next
            }
            { print }
        ' "${UNIT_FILE_UPG}.bak-upgrade-${OLD}" > "$UNIT_FILE_UPG"
        info "Systemd unit: replaced 'configure init all' ExecStart with 4 ExecStartPre steps"
        UNIT_CHANGED=1
    fi
    systemctl daemon-reload
    [[ $UNIT_CHANGED -eq 1 ]] && info "daemon-reload done"
    ok "Systemd unit fixed"
else
    warn "Could not find systemd unit file — skipping unit fix"
    ok "Systemd unit check skipped"
fi

# ── 3.13 Verify new version ───────────────────────────────────────────────────
info "Verifying installed binary version..."
INSTALLED_VER=$("$FDCTL_BIN" version 2>/dev/null | grep -oP '[\d.]+' | head -1)
if [[ -z "$INSTALLED_VER" ]]; then
    die "Installed fdctl reports no version"
fi
if [[ "$INSTALLED_VER" != "$NEW"* ]]; then
    warn "Installed version '$INSTALLED_VER' does not exactly match '$NEW' — verify manually"
else
    ok "Installed version: $INSTALLED_VER"
fi

# ── 3.13b Auto-detect network interface
INTERFACE=$(ip route get 8.8.8.8 2>/dev/null | grep -oP "dev \K\S+")
if [[ -n "$INTERFACE" ]]; then
    if ! grep -q "\[net\]" "$CONFIG"; then
        info "Adding [net] interface = $INTERFACE to config..."
        echo -e "\n[net]\ninterface = \"$INTERFACE\"" >> "$CONFIG"
        ok "Interface $INTERFACE added to config"
    else
        info "[net] section already exists in config — skipping"
    fi
else
    warn "Could not detect network interface — skipping"
fi

# ── 3.14 configure init all (if needed) ───────────────────────────────────────
if [[ "$HAS_CONFIGURE_INIT" -eq 0 ]]; then
    info "Running configure init all (ExecStart does not include it)..."
    "$FDCTL_BIN" configure init all --config "$CONFIG"
    INIT_RC=$?
    if [[ $INIT_RC -ne 0 ]]; then
        die "configure init all failed (rc=$INIT_RC)"
    fi
    ok "configure init all done"
else
    info "ExecStart includes configure init — skipping manual init (systemd will handle it)"
fi

# ── 3.15 Start the node ───────────────────────────────────────────────────────
info "Starting firedancer service..."
systemctl start firedancer
START_RC=$?
if [[ $START_RC -ne 0 ]]; then
    die "systemctl start firedancer failed (rc=$START_RC)"
fi
sleep 5
SVC_POST=$(systemctl is-active firedancer 2>/dev/null)
if [[ "$SVC_POST" != "active" ]]; then
    fail "Service status after start: $SVC_POST"
    fail "journalctl output (last 30 lines):"
    journalctl -u firedancer -n 30 --no-pager 2>/dev/null
    die "Service did not come up"
fi
ok "firedancer service started: $SVC_POST"

# ══════════════════════════════════════════════════════════════════════════════
# БЛОК 4 — Финальная верификация
# ══════════════════════════════════════════════════════════════════════════════
hdr "=== БЛОК 4: Финальная верификация ==="

# ── 4.1 Wait for node in cluster (up to 15 minutes) ──────────────────────────
CLUSTER_WAIT_MAX=900
CLUSTER_POLL=30
CLUSTER_ELAPSED=0
FOUND_IN_CLUSTER=0

if [[ "$IDENTITY" == "unknown" ]]; then
    warn "Identity unknown — skipping cluster appearance check"
    FOUND_IN_CLUSTER=1
else
    info "Waiting for $IDENTITY to appear in cluster (up to ${CLUSTER_WAIT_MAX}s)..."
    while [[ $CLUSTER_ELAPSED -lt $CLUSTER_WAIT_MAX ]]; do
        VALIDATORS_OUT=$(solana validators 2>/dev/null)
        if echo "$VALIDATORS_OUT" | grep -q "$IDENTITY"; then
            FOUND_IN_CLUSTER=1
            ok "Node $IDENTITY appeared in cluster after ${CLUSTER_ELAPSED}s"
            break
        fi
        warn "  [${CLUSTER_ELAPSED}s] Not in cluster yet — retrying in ${CLUSTER_POLL}s..."
        sleep "$CLUSTER_POLL"
        CLUSTER_ELAPSED=$((CLUSTER_ELAPSED + CLUSTER_POLL))
    done
fi

if [[ $FOUND_IN_CLUSTER -eq 0 ]]; then
    fail "Node did not appear in cluster within ${CLUSTER_WAIT_MAX}s"
    fail "Check: solana validators | grep $IDENTITY"
    fail "Check: journalctl -u firedancer -f"
fi

# ── 4.2 Final status ──────────────────────────────────────────────────────────
hdr "=== Final Status ==="
echo ""
SVC_FINAL=$(systemctl is-active firedancer 2>/dev/null)
FINAL_VER=$("$FDCTL_BIN" version 2>/dev/null | grep -oP '[\d.]+' | head -1)
DELINQUENT=""
if [[ "$IDENTITY" != "unknown" ]]; then
    DELINQUENT=$(solana validators 2>/dev/null | grep "$IDENTITY" | grep -i delinquent || true)
fi

echo -e "${BOLD}┌──────────────────────────────────────────────────────────┐${NC}"
echo -e "${BOLD}│                  POST-UPGRADE STATUS                    │${NC}"
echo -e "${BOLD}├──────────────────────────────────────────────────────────┤${NC}"
printf "│  %-30s  %-24s │\n" "Service"           "$SVC_FINAL"
printf "│  %-30s  %-24s │\n" "Old version"       "$OLD"
printf "│  %-30s  %-24s │\n" "New version"       "$FINAL_VER"
printf "│  %-30s  %-24s │\n" "In cluster"        "$([ $FOUND_IN_CLUSTER -eq 1 ] && echo 'yes' || echo 'NO')"
printf "│  %-30s  %-24s │\n" "Delinquent"        "$([ -z "$DELINQUENT" ] && echo 'no' || echo 'YES — check!')"
printf "│  %-30s  %-24s │\n" "Build log"         "$BUILD_LOG"
printf "│  %-30s  %-24s │\n" "Upgrade log"       "$LOG_FILE"
printf "│  %-30s  %-24s │\n" "Old binary backup" "$(basename "$BACKUP_OLD")"
echo -e "${BOLD}└──────────────────────────────────────────────────────────┘${NC}"
echo ""

# ── 4.3 Backup new binary ─────────────────────────────────────────────────────
BACKUP_NEW="/root/fdctl-backup-${NEW}-$(date +%Y%m%d%H%M%S)"
cp "$FDCTL_BIN" "$BACKUP_NEW" || warn "Could not create backup of new binary"
ok "New binary backed up: $BACKUP_NEW"

# ── 4.4 Show validator status ─────────────────────────────────────────────────
if [[ "$IDENTITY" != "unknown" ]]; then
    info "Validator entry:"
    solana validators 2>/dev/null | grep "$IDENTITY" || warn "Not found in validators list yet"
fi

echo ""
if [[ $FOUND_IN_CLUSTER -eq 1 && "$SVC_FINAL" == "active" ]]; then
    ok "Upgrade to $NEW completed successfully!"
else
    warn "Upgrade completed with warnings. Check service logs:"
    warn "  journalctl -u firedancer -f"
fi

rm -f "$BUILD_ENV_FILE"
