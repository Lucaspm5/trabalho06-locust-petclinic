#!/usr/bin/env bash
cd "$(dirname "$0")/.."
source scripts/env.sh
OUT=results/environment.txt
{
  echo "# Ambiente - coletado em $(date -Is)"
  echo "## SO";                lsb_release -a 2>/dev/null; uname -a
  echo "## CPU";               lscpu | grep -E 'Model name|^CPU\(s\)|Thread|Core'
  echo "## Memoria (WSL)";     free -h
  echo "## Docker";            docker version --format 'Client {{.Client.Version}} / Server {{.Server.Version}}'; docker compose version
  echo "## Python / Locust";   python3 --version; .venv/bin/locust --version
  echo "## PetClinic (commit)"; git -C "$PETCLINIC_DIR" log -1 --format='%H %cd'
  echo "## Containers";        docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
  echo "## Limite de memoria (bytes) por container"
  docker inspect --format '{{.Name}} mem_limit={{.HostConfig.Memory}}' $(docker ps -q)
} > "$OUT"
cat "$OUT"
