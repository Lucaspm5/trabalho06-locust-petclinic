#!/usr/bin/env python3
"""Preenche os placeholders do README com dados reais (hash, ambiente, tabelas, URL)."""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
readme = (ROOT / "README.md").read_text(encoding="utf-8")


def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, encoding="utf-8", errors="replace")
    return r.stdout.strip()


def replace_once(text, old, new):
    if old not in text:
        print(f"[AVISO] trecho não encontrado: {old[:60]!r}")
        return text
    return text.replace(old, new)


commit = sh("git -C ~/spring-petclinic-microservices log -1 --format=%H")
user = sh("gh api user -q .login")
cpu = sh('powershell.exe -NoProfile -Command "(Get-CimInstance Win32_Processor).Name"')
ram = sh('powershell.exe -NoProfile -Command "[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB)"')
env = (ROOT / "results/environment.txt").read_text(encoding="utf-8").strip()
tables = (ROOT / "results/tables.md").read_text(encoding="utf-8")
tables = re.sub(r"^# .*\n", "", tables, count=1, flags=re.M)      # remove o H1
tables = re.sub(r"^## ", "### ", tables, flags=re.M)               # rebaixa os títulos

readme = replace_once(readme, "<HASH_DO_COMMIT>", commit)
if user:
    readme = replace_once(readme, "<URL_DESTE_REPO>", f"https://github.com/{user}/trabalho06-locust-petclinic.git")
else:
    print("[AVISO] não consegui obter o usuário do GitHub (gh auth login?). Mantive <URL_DESTE_REPO>.")
readme = replace_once(readme, "<PASTA>", "trabalho06-locust-petclinic")

env_block = (
    f"**Host (Windows):** {cpu}; {ram} GB de RAM. Experimentos executados em Ubuntu sobre WSL2 com Docker, "
    "gerador de carga (Locust) e aplicação na mesma máquina.\n\n"
    "Detalhes coletados por `scripts/collect_env.sh` (`results/environment.txt`):\n\n"
    f"```text\n{env}\n```"
)
readme = replace_once(
    readme,
    "(cole o conteúdo de `results/environment.txt` e descreva hardware do Windows: CPU, RAM, SSD)",
    env_block,
)

estrutura = '''### Estrutura do repositório

```text
.
├── locustfile.py            # perfis ReadProfileUser e WriteProfileUser
├── requirements.txt
├── scripts/                 # env.sh, wait_ready.sh, monitor_cpu.sh, run_all.sh, collect_env.sh, analyze.py
└── results/
    ├── raw/                 # *_cpu.csv (docker stats) e *_locust_*.csv (estatísticas nativas do Locust, incluem aquecimento)
    ├── raw_requests.tar.gz  # log por requisição das 60 execuções
    ├── summary_*.csv        # métricas por execução, por cenário, por operação e CPU
    ├── tables.md            # tabelas consolidadas
    ├── failures_by_status.csv
    ├── environment.txt, run_all.log
    └── graphs/              # gráficos (PNG)
```

Para reprocessar sem reexecutar os experimentos:

```bash
mkdir -p results/raw && tar xzf results/raw_requests.tar.gz -C results/raw
python scripts/analyze.py
```

'''
readme = replace_once(readme, "## 3. Metodologia", estrutura + "## 3. Metodologia")

readme = replace_once(
    readme,
    "- Falha = status HTTP diferente de 200/201 ou erro de conexão/timeout.",
    "- Falha = status HTTP diferente de 200/201 ou erro de conexão/timeout.\n"
    "- Interpretação do enunciado: cada execução dura 7 min (1 min de aquecimento descartado + 6 min medidos).\n"
    "- Tempo médio e P95 consideram todas as requisições da janela medida, inclusive as com falha.\n"
    "- A média das repetições é a média aritmética das métricas de cada execução (inclusive do P95).\n"
    "- As configurações são intercaladas (repetição 1 de todas, depois repetição 2, etc.) para diluir efeitos de deriva do ambiente.",
)

readme = replace_once(
    readme,
    "(cole `results/tables.md` e inclua os gráficos)",
    "Valores: média ± desvio padrão das 10 repetições, na janela medida (sem aquecimento).\n\n"
    + tables.strip()
    + "\n\n### Gráficos",
)

readme = replace_once(
    readme,
    "![CPU](results/graphs/06_cpu_servicos.png)",
    "![CPU](results/graphs/06_cpu_servicos.png)\n"
    "![Total de requisições](results/graphs/07_total_requisicoes.png)\n"
    "![Tempo médio por operação](results/graphs/08_medio_por_operacao.png)",
)

(ROOT / "README.md").write_text(readme.rstrip() + "\n", encoding="utf-8")
print("README atualizado.")
