#!/usr/bin/env bash
# Shared helpers: run one check and print one row of the report table.
# Source this file; do not run it directly.

report_header() {
  echo
  echo "| Check | Command | Result |"
  echo "|---|---|---|"
}

# run_check "<name>" "<command>"  -> prints PASS or FAIL, keeps the log in $LOG_DIR
run_check() {
  local name="$1" cmd="$2"
  local log="$LOG_DIR/${name// /-}.log"
  if bash -c "$cmd" >"$log" 2>&1; then
    echo "| $name | \`$cmd\` | PASS |"
  else
    echo "| $name | \`$cmd\` | FAIL (log: $log) |"
    FAILED=1
  fi
}

# not_run "<name>" "<command>" "<reason>"
not_run() {
  echo "| $1 | \`$2\` | NOT RUN: $3 |"
}

LOG_DIR="$(mktemp -d -t edugest-review-XXXX)"
FAILED=0
