#!/usr/bin/env bash
# Configuracoes compartilhadas (podem ser sobrescritas por variaveis de ambiente)
export PETCLINIC_DIR="${PETCLINIC_DIR:-$HOME/spring-petclinic-microservices}"
export GATEWAY="${GATEWAY:-http://localhost:8080}"
export REPS="${REPS:-10}"
export WARMUP_S="${WARMUP_S:-60}"
export MEASURE_S="${MEASURE_S:-360}"
export SPAWN_RATE="${SPAWN_RATE:-5}"
export RAW_DIR="${RAW_DIR:-results/raw}"
