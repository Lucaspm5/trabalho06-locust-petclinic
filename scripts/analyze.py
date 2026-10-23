#!/usr/bin/env python3
"""
Pos-processamento (Trabalho 06).
Le RAW_DIR/*_requests.csv e *_cpu.csv, descarta o aquecimento, calcula as metricas
por execucao, tira a media das repeticoes e gera CSVs, tabelas (Markdown) e graficos.
"""
import os
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / os.getenv("RAW_DIR", "results/raw")
OUT_DIR = RAW_DIR.parent
GRAPH_DIR = OUT_DIR / "graphs"
GRAPH_DIR.mkdir(parents=True, exist_ok=True)

WARMUP_S = int(os.getenv("WARMUP_S", "60"))
MEASURE_S = int(os.getenv("MEASURE_S", "360"))
END_S = WARMUP_S + MEASURE_S

SCEN = {"A": ("A - Leve", 30), "B": ("B - Moderado", 80), "C": ("C - Elevado", 150)}
PROFILE = {"read": "Perfil 1 - Leitura", "write": "Perfil 2 - Escrita"}
OPS = ["GET /owners", "GET /owners/{id}", "GET /vets", "POST /owners"]
CPU_SERVICES = ["api-gateway", "customers-service", "vets-service"]
METRICS = ["avg_ms", "p95_ms", "throughput_rps", "total_requests", "failure_pct"]
PATTERN = re.compile(r"^(read|write)_([ABC])_rep(\d+)_requests\.csv$")


def summarize(df):
    n = len(df)
    fails = int((df["success"] == 0).sum())
    return {
        "total_requests": n,
        "failures": fails,
        "failure_pct": 100.0 * fails / n if n else np.nan,
        "avg_ms": df["response_time_ms"].mean(),
        "p95_ms": df["response_time_ms"].quantile(0.95),
        "throughput_rps": n / MEASURE_S,
    }


def cpu_means(cpu_file, t0):
    if not cpu_file.exists():
        return {}
    c = pd.read_csv(cpu_file)
    c["cpu_percent"] = pd.to_numeric(c["cpu_percent"].astype(str).str.rstrip("%"), errors="coerce")
    c = c[(c["timestamp"] >= t0 + WARMUP_S) & (c["timestamp"] < t0 + END_S)]
    return c.groupby("container")["cpu_percent"].mean().to_dict()


def load():
    runs, ops, cpus, fails = [], [], [], []
    for f in sorted(RAW_DIR.glob("*_requests.csv")):
        m = PATTERN.match(f.name)
        if not m:
            continue
        profile, scen, rep = m.group(1), m.group(2), int(m.group(3))
        df = pd.read_csv(f)
        if df.empty:
            continue
        t0 = (df["timestamp"] - df["t_rel"]).median()
        w = df[(df["t_rel"] >= WARMUP_S) & (df["t_rel"] < END_S)]
        if w.empty:
            continue
        key = {"profile": profile, "scenario": scen, "users": SCEN[scen][1], "rep": rep}
        runs.append({**key, **summarize(w)})
        for op, g in w.groupby("name"):
            ops.append({**key, "operation": op, **summarize(g)})
        for (op, st), g in w[w["success"] == 0].groupby(["name", "status"]):
            fails.append({**key, "operation": op, "status": int(st), "count": len(g)})
        cpu_file = f.with_name(f.name.replace("_requests.csv", "_cpu.csv"))
        for svc, val in cpu_means(cpu_file, t0).items():
            cpus.append({**key, "service": svc, "cpu_percent": val})
    return tuple(pd.DataFrame(x) for x in (runs, ops, cpus, fails))


def mean_std(df, by, cols):
    g = df.groupby(by)[cols].agg(["mean", "std"])
    g.columns = [f"{c}_{s}" for c, s in g.columns]
    g["reps"] = df.groupby(by).size()
    return g.reset_index()


def pm(df, col, nd=1):
    return df.apply(lambda r: f"{r[col + '_mean']:.{nd}f} ± {0 if pd.isna(r[col + '_std']) else r[col + '_std']:.{nd}f}", axis=1)


def plot_lines(scen_agg, metric, ylabel, fname):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for prof, label in PROFILE.items():
        s = scen_agg[scen_agg["profile"] == prof].sort_values("users")
        ax.errorbar(s["users"], s[f"{metric}_mean"], yerr=s[f"{metric}_std"].fillna(0),
                    marker="o", capsize=4, label=label)
    ax.set_xlabel("Usuários simultâneos")
    ax.set_ylabel(ylabel)
    ax.set_xticks([v[1] for v in SCEN.values()])
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(GRAPH_DIR / fname, dpi=150)
    plt.close(fig)


def plot_ops(op_agg, metric, ylabel, fname):
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8), sharey=True)
    width = 0.25
    for ax, (prof, plabel) in zip(axes, PROFILE.items()):
        for i, scen in enumerate("ABC"):
            vals, errs = [], []
            for op in OPS:
                r = op_agg[(op_agg["profile"] == prof) & (op_agg["scenario"] == scen) & (op_agg["operation"] == op)]
                vals.append(r[f"{metric}_mean"].iloc[0] if len(r) else 0)
                errs.append(r[f"{metric}_std"].fillna(0).iloc[0] if len(r) else 0)
            ax.bar(np.arange(len(OPS)) + (i - 1) * width, vals, width, yerr=errs, capsize=3, label=SCEN[scen][0])
        ax.set_xticks(range(len(OPS)))
        ax.set_xticklabels(OPS, rotation=15)
        ax.set_title(plabel)
        ax.grid(axis="y", alpha=0.3)
    axes[0].set_ylabel(ylabel)
    axes[0].legend()
    fig.tight_layout()
    fig.savefig(GRAPH_DIR / fname, dpi=150)
    plt.close(fig)


def plot_cpu(cpu_agg, fname):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    width = 0.25
    for ax, (prof, plabel) in zip(axes, PROFILE.items()):
        for i, scen in enumerate("ABC"):
            vals, errs = [], []
            for svc in CPU_SERVICES:
                r = cpu_agg[(cpu_agg["profile"] == prof) & (cpu_agg["scenario"] == scen) & (cpu_agg["service"] == svc)]
                vals.append(r["cpu_percent_mean"].iloc[0] if len(r) else 0)
                errs.append(r["cpu_percent_std"].fillna(0).iloc[0] if len(r) else 0)
            ax.bar(np.arange(len(CPU_SERVICES)) + (i - 1) * width, vals, width, yerr=errs, capsize=3, label=SCEN[scen][0])
        ax.set_xticks(range(len(CPU_SERVICES)))
        ax.set_xticklabels(CPU_SERVICES)
        ax.set_title(plabel)
        ax.grid(axis="y", alpha=0.3)
    axes[0].set_ylabel("CPU média (% de 1 core)")
    axes[0].legend()
    fig.tight_layout()
    fig.savefig(GRAPH_DIR / fname, dpi=150)
    plt.close(fig)


def main():
    runs, ops, cpus, fails = load()
    if runs.empty:
        raise SystemExit(f"Nenhum *_requests.csv valido em {RAW_DIR}")

    runs.to_csv(OUT_DIR / "summary_runs.csv", index=False)
    ops.to_csv(OUT_DIR / "summary_operations_runs.csv", index=False)
    if not fails.empty:
        fails.to_csv(OUT_DIR / "failures_by_status.csv", index=False)

    scen_agg = mean_std(runs, ["profile", "scenario", "users"], METRICS).sort_values(["profile", "users"])
    op_agg = mean_std(ops, ["profile", "scenario", "users", "operation"], ["avg_ms", "p95_ms", "failure_pct", "throughput_rps"])
    scen_agg.to_csv(OUT_DIR / "summary_scenarios.csv", index=False)
    op_agg.to_csv(OUT_DIR / "summary_operations.csv", index=False)

    md = ["# Resultados (média ± desvio padrão das repetições; janela medida sem aquecimento)\n"]

    t = scen_agg
    tab = pd.DataFrame({
        "Perfil": t["profile"].map(PROFILE),
        "Cenário": t["scenario"].map(lambda s: SCEN[s][0]),
        "Usuários": t["users"],
        "Reps": t["reps"],
        "Tempo médio (ms)": pm(t, "avg_ms"),
        "P95 (ms)": pm(t, "p95_ms"),
        "Vazão (req/s)": pm(t, "throughput_rps", 2),
        "Total de req.": pm(t, "total_requests", 0),
        "Falhas (%)": pm(t, "failure_pct", 2),
    })
    md += ["## 1. Visão geral por perfil e cenário\n", tab.to_markdown(index=False), "\n"]

    o = op_agg.sort_values(["profile", "users", "operation"])
    tab = pd.DataFrame({
        "Perfil": o["profile"].map(PROFILE),
        "Cenário": o["scenario"].map(lambda s: SCEN[s][0]),
        "Operação": o["operation"],
        "Tempo médio (ms)": pm(o, "avg_ms"),
        "P95 (ms)": pm(o, "p95_ms"),
        "Falhas (%)": pm(o, "failure_pct", 2),
    })
    md += ["## 2. Por operação\n", tab.to_markdown(index=False), "\n"]

    piv = op_agg.pivot_table(index=["profile", "operation"], columns="scenario", values="avg_ms_mean")
    if {"A", "C"} <= set(piv.columns):
        deg = (piv["C"] / piv["A"]).rename("Razão C/A").reset_index()
        deg["profile"] = deg["profile"].map(PROFILE)
        deg.columns = ["Perfil", "Operação", "Razão C/A (tempo médio)"]
        deg["Razão C/A (tempo médio)"] = deg["Razão C/A (tempo médio)"].round(2)
        md += ["## 3. Degradação por operação (tempo médio no cenário C ÷ cenário A)\n", deg.to_markdown(index=False), "\n"]

    if not cpus.empty:
        cpu_all = mean_std(cpus, ["profile", "scenario", "users", "service"], ["cpu_percent"])
        cpu_all.to_csv(OUT_DIR / "summary_cpu_all_containers.csv", index=False)
        c = cpu_all[cpu_all["service"].isin(CPU_SERVICES)].sort_values(["profile", "users", "service"])
        tab = pd.DataFrame({
            "Perfil": c["profile"].map(PROFILE),
            "Cenário": c["scenario"].map(lambda s: SCEN[s][0]),
            "Serviço": c["service"],
            "CPU média (% de 1 core)": pm(c, "cpu_percent"),
        })
        md += ["## 4. CPU média por serviço\n", tab.to_markdown(index=False), "\n"]
        plot_cpu(cpu_all, "06_cpu_servicos.png")

    if not fails.empty:
        f = fails.groupby(["profile", "scenario", "operation", "status"])["count"].sum().reset_index()
        f["profile"] = f["profile"].map(PROFILE)
        f.columns = ["Perfil", "Cenário", "Operação", "HTTP status", "Falhas (soma das reps)"]
        md += ["## 5. Falhas por status HTTP (0 = erro de conexão/timeout)\n", f.to_markdown(index=False), "\n"]

    (OUT_DIR / "tables.md").write_text("\n".join(md), encoding="utf-8")

    plot_lines(scen_agg, "avg_ms", "Tempo médio de resposta (ms)", "01_tempo_medio.png")
    plot_lines(scen_agg, "p95_ms", "Tempo de resposta P95 (ms)", "02_p95.png")
    plot_lines(scen_agg, "throughput_rps", "Vazão (req/s)", "03_vazao.png")
    plot_lines(scen_agg, "failure_pct", "Taxa de falhas (%)", "04_falhas.png")
    plot_lines(scen_agg, "total_requests", "Total de requisições (janela medida)", "07_total_requisicoes.png")
    plot_ops(op_agg, "p95_ms", "P95 (ms)", "05_p95_por_operacao.png")
    plot_ops(op_agg, "avg_ms", "Tempo médio (ms)", "08_medio_por_operacao.png")

    print(f"{len(runs)} execuções processadas. Saídas em: {OUT_DIR}")


if __name__ == "__main__":
    main()
