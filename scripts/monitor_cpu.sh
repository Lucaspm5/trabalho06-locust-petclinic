#!/usr/bin/env bash
# Uso: monitor_cpu.sh <saida.csv>
# Amostra CPU (%) e memoria de todos os containers. 100% = 1 core (pode passar de 100%).
OUT="$1"
trap 'exit 0' TERM INT
echo "timestamp,container,cpu_percent,mem_usage" > "$OUT"
while true; do
  TS=$(date +%s.%N)
  docker stats --no-stream --format '{{.Name}},{{.CPUPerc}},{{.MemUsage}}' | sed "s/^/${TS},/" >> "$OUT"
done
