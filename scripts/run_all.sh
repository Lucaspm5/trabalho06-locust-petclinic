#!/usr/bin/env bash
# Executa 2 perfis x 3 cenarios x REPS repeticoes (padrao: 60 execucoes).
# E retomavel: execucoes concluidas (arquivo .done) sao puladas.
cd "$(dirname "$0")/.."
source scripts/env.sh
source .venv/bin/activate
set -uo pipefail

declare -A USERS=( [A]=30 [B]=80 [C]=150 )
declare -A CLASS=( [read]=ReadProfileUser [write]=WriteProfileUser )
RUN_TIME=$((WARMUP_S + MEASURE_S))
mkdir -p "$RAW_DIR"

reset_env() {
  echo "[reset] reiniciando customers, vets, visits e api-gateway (HSQLDB volta ao estado inicial)"
  (cd "$PETCLINIC_DIR" && docker compose restart customers-service vets-service visits-service api-gateway) > /dev/null 2>&1
  sleep 20
  ./scripts/wait_ready.sh || return 1
  sleep 10
}

TOTAL=$((REPS * 6))
n=0
for rep in $(seq 1 "$REPS"); do
  rep_id=$(printf "%02d" "$rep")
  for scen in A B C; do
    for prof in read write; do
      n=$((n+1))
      base="${prof}_${scen}_rep${rep_id}"
      raw="$RAW_DIR/${base}_requests.csv"
      cpu="$RAW_DIR/${base}_cpu.csv"
      if [[ -f "$RAW_DIR/${base}.done" ]]; then echo "[skip] $base (ja concluida)"; continue; fi
      echo "=== [$n/$TOTAL] $(date '+%F %T') | $base | ${USERS[$scen]} usuarios | ${RUN_TIME}s ==="
      if ! reset_env; then echo "[ERRO] ambiente nao ficou pronto; abortando"; exit 1; fi

      ./scripts/monitor_cpu.sh "$cpu" &
      mon_pid=$!

      RAW_CSV="$raw" locust -f locustfile.py "${CLASS[$prof]}" \
        --host "$GATEWAY" --headless \
        -u "${USERS[$scen]}" -r "$SPAWN_RATE" -t "${RUN_TIME}s" \
        --csv "$RAW_DIR/${base}_locust" --only-summary --exit-code-on-error 0
      rc=$?

      kill "$mon_pid" 2>/dev/null
      wait "$mon_pid" 2>/dev/null

      if [[ $rc -eq 0 ]]; then
        touch "$RAW_DIR/${base}.done"
      else
        echo "[ERRO] locust retornou $rc em $base; descartando arquivos desta execucao"
        rm -f "$raw" "$cpu"
      fi
    done
  done
done
echo "=== Concluido em $(date '+%F %T') ==="
