#!/usr/bin/env bash
# Runtime credential gate for repo publishing.
# Purpose: block real operating credentials (proxy nodes, configs, certs, SSH hints)
# before commit/push. Keep this script generic: never add real IPs, passwords, UUIDs,
# fingerprints, hostnames, or user-specific values here.

set -euo pipefail

failures=0

section() {
  printf '\n=== %s ===\n' "$1"
}

fail_if_match() {
  local label="$1"
  local command="$2"
  section "$label"
  if bash -c "$command"; then
    echo "FAIL: $label matched sensitive-looking content"
    failures=$((failures + 1))
  else
    echo "OK: $label"
  fi
}

# Staged content scans. These are intentionally broad: a hit means human review,
# not automatic deletion. False positives are cheaper than leaked credentials.
fail_if_match \
  "proxy URI in staged diff" \
  "git diff --cached | grep -Ei 'ss://|trojan://|vless://|vmess://|hysteria2://|tuic://'"

fail_if_match \
  "proxy/runtime credentials in staged diff" \
  "git diff --cached | grep -Ei '(password|uuid|private-key|public-key|short-id|pinnedPeerCertSha256|external-controller|secret): *['\''\"'\'']?[A-Za-z0-9_~@%+=:;.,/-]{8,}'"

fail_if_match \
  "runtime config path or SSH command in staged diff" \
  "git diff --cached | grep -Ei '/etc/mihomo|/usr/local/etc/xray|config\\.yaml|config\\.json|root@|ssh -p [0-9]+'"

section "sensitive-looking tracked filenames"
if git ls-files | grep -Ei '(mihomo|clash|xray|sing-box).*config|config\.yaml|config\.json|server\.key|\.pem$|\.crt$'; then
  echo "REVIEW REQUIRED: sensitive-looking tracked filename(s) present"
  failures=$((failures + 1))
else
  echo "OK: no sensitive-looking tracked filenames"
fi

section "sensitive-looking untracked filenames"
if git ls-files --others --exclude-standard | grep -Ei '(mihomo|clash|xray|sing-box).*config|config\.yaml|config\.json|server\.key|\.pem$|\.crt$'; then
  echo "REVIEW REQUIRED: sensitive-looking untracked filename(s) present"
  failures=$((failures + 1))
else
  echo "OK: no sensitive-looking untracked filenames"
fi

if [[ "$failures" -ne 0 ]]; then
  cat <<'MSG'

BLOCKED: runtime credential gate failed.
Action:
  1. Stop commit/push.
  2. Replace real values with placeholders such as <IP>, <PORT>, <PASSWORD>, <UUID>, <SHA256>.
  3. Move real runtime configs out of the repo and add them to .gitignore.
  4. If a real credential already entered git history, rotate it first, then clean history.
MSG
  exit 1
fi

echo "PASS: runtime credential gate clean"
