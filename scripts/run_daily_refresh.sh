#!/usr/bin/env bash
set -euo pipefail

# TailCast daily refresh: fetch data → features → walk-forward training → wf_predictions.csv
#
# Usage:
#   ./scripts/run_daily_refresh.sh
#   SKIP_FETCH=1 ./scripts/run_daily_refresh.sh   # reuse cached raw data
#   NO_DB=1 ./scripts/run_daily_refresh.sh        # CSV-only (default)

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

LOG_DIR="${LOG_DIR:-$ROOT_DIR/logs}"
mkdir -p "$LOG_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$LOG_DIR/daily_refresh_${STAMP}.log"

# Optional: load FRED key from MacroShift .env if TailCast has no .env
MACROSHIFT_ENV="${MACROSHIFT_ENV:-/Users/kyeongminkim/Desktop/Projects/MacroShift/.env}"
if [[ -f "$ROOT_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
  set +a
elif [[ -f "$MACROSHIFT_ENV" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$MACROSHIFT_ENV"
  set +a
fi

PYTHON="${PYTHON:-$ROOT_DIR/venv/bin/python}"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="$(command -v python3)"
fi

PIPELINE_ARGS=()
TRAINING_ARGS=()
if [[ "${NO_DB:-1}" == "1" ]]; then
  PIPELINE_ARGS+=(--no-db)
fi
if [[ "${SKIP_FETCH:-0}" == "1" ]]; then
  PIPELINE_ARGS+=(--use-cache)
fi

exec > >(tee -a "$LOG_FILE") 2>&1

echo "=== TailCast daily refresh started $(date -Iseconds) ==="
echo "ROOT_DIR=$ROOT_DIR"
echo "PYTHON=$PYTHON"
echo "LOG_FILE=$LOG_FILE"
echo "PIPELINE_ARGS=${PIPELINE_ARGS[*]:-none}"
echo "FRED_API_KEY=${FRED_API_KEY:+set}"

echo "[1/2] Phase 1 — data fetch + features + labels"
"$PYTHON" run_pipeline.py "${PIPELINE_ARGS[@]}"

echo "[2/2] Phase 2 — walk-forward training → data/model_outputs/wf_predictions.csv"
if ((${#TRAINING_ARGS[@]})); then
  "$PYTHON" run_training.py "${TRAINING_ARGS[@]}"
else
  "$PYTHON" run_training.py
fi

PRED_PATH="$ROOT_DIR/data/model_outputs/wf_predictions.csv"
if [[ ! -f "$PRED_PATH" ]]; then
  echo "ERROR: expected output missing: $PRED_PATH"
  exit 1
fi

read -r END_DATE ROWS < <("$PYTHON" - <<'PY'
import pandas as pd
from pathlib import Path
p = Path("data/model_outputs/wf_predictions.csv")
df = pd.read_csv(p, index_col=0, parse_dates=True)
print(df.index.max().date(), len(df))
PY
)

SUMMARY="$LOG_DIR/daily_refresh_latest.json"
cat > "$SUMMARY" <<EOF
{
  "status": "ok",
  "finished_at": "$(date -Iseconds)",
  "predictions_path": "$PRED_PATH",
  "prediction_end_date": "$END_DATE",
  "prediction_rows": $ROWS,
  "log_file": "$LOG_FILE"
}
EOF

echo "=== TailCast daily refresh complete ==="
echo "predictions_end=$END_DATE rows=$ROWS"
echo "summary=$SUMMARY"
ln -sf "$LOG_FILE" "$LOG_DIR/daily_refresh_latest.log"
