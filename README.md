# Trabalho 06 — Avaliação de Desempenho de Microsserviços com Locust

Avaliação do Spring PetClinic Microservices sob dois perfis de carga (leitura e escrita) e três cenários (30, 80 e 150 usuários).

**Vídeo demonstrativo:** <COLE_AQUI_O_LINK_DO_YOUTUBE>

## 1. Ambiente
(cole o conteúdo de `results/environment.txt` e descreva hardware do Windows: CPU, RAM, SSD)

## 2. Como reproduzir
```bash
git clone https://github.com/spring-petclinic/spring-petclinic-microservices.git ~/spring-petclinic-microservices
cd ~/spring-petclinic-microservices && git checkout <HASH_DO_COMMIT>
docker compose up -d config-server discovery-server customers-service visits-service vets-service api-gateway tracing-server admin-server prometheus-server grafana-server

git clone <URL_DESTE_REPO> && cd <PASTA>
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
chmod +x scripts/*.sh
./scripts/run_all.sh        # 60 execuções (~9 h)
python scripts/analyze.py   # gera tabelas e gráficos em results/
```

## 3. Metodologia
- Perfis: `ReadProfileUser` (45/35/15/5) e `WriteProfileUser` (20/20/20/40) em `locustfile.py`.
- Endpoints (via API Gateway, porta 8080): `/api/customer/owners`, `/api/customer/owners/{id}`, `/api/vet/vets`.
- Cenários: A=30, B=80, C=150 usuários; ramp-up de 5 usuários/s; think time 1–2 s.
- Cada execução: 1 min de aquecimento (descartado) + 6 min medidos. 10 repetições por configuração (60 execuções).
- Entre execuções, customers, vets, visits e gateway são reiniciados (banco HSQLDB em memória volta ao estado inicial).
- Métricas calculadas sobre o log por requisição (`results/raw`), apenas na janela medida. Resultado = média das 10 repetições (± desvio padrão).
- CPU: `docker stats` a cada ~2 s; média na janela medida (100% = 1 core).
- Falha = status HTTP diferente de 200/201 ou erro de conexão/timeout.

## 4. Resultados
(cole `results/tables.md` e inclua os gráficos)

![Tempo médio](results/graphs/01_tempo_medio.png)
![P95](results/graphs/02_p95.png)
![Vazão](results/graphs/03_vazao.png)
![Falhas](results/graphs/04_falhas.png)
![P95 por operação](results/graphs/05_p95_por_operacao.png)
![CPU](results/graphs/06_cpu_servicos.png)

## 5. Respostas
1. Efeito do aumento de usuários no tempo de resposta: ...
2. Perfil com maior vazão: ...
3. Operações com maior degradação: ...
4. Variação do consumo de CPU: ...
5. Cenário com maior taxa de falhas: ...

## 6. Conclusões e limitações
- Gerador de carga e aplicação compartilham a mesma máquina.
- Containers limitados a 512 MB (definido no docker-compose do PetClinic).
- `GET /owners` retorna todos os owners; no perfil de escrita a lista cresce durante a execução.
