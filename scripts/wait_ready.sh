#!/usr/bin/env bash
# Espera o gateway responder 200 nos 3 endpoints, 3 vezes seguidas.
source "$(dirname "$0")/env.sh"
ok=0
for i in $(seq 1 120); do
  c1=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY/api/customer/owners/1" || true)
  c2=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY/api/vet/vets" || true)
  c3=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY/api/customer/owners" || true)
  if [[ "$c1" == "200" && "$c2" == "200" && "$c3" == "200" ]]; then ok=$((ok+1)); else ok=0; fi
  if [[ $ok -ge 3 ]]; then echo "[wait_ready] OK"; exit 0; fi
  sleep 5
done
echo "[wait_ready] TIMEOUT" >&2
exit 1
