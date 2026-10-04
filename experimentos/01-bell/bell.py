"""Estado de Bell em hardware quântico real da IBM.

Prepara (|00> + |11>) / sqrt(2): um qubit em superposição (Hadamard) e um CNOT que
o emaranha com o segundo. Em um computador perfeito só apareceriam "00" e "11",
metade das vezes cada. Tudo que aparece além disso ("01" e "10") é ruído do hardware.

Uso:
    export IBM_QUANTUM_TOKEN=...   # chave da IBM Cloud (nunca no repositório)
    python bell.py [--shots 1024] [--saida resultados]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from qiskit import QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2


def circuito_bell() -> QuantumCircuit:
    qc = QuantumCircuit(2, 2, name="bell")
    qc.h(0)
    qc.cx(0, 1)
    qc.measure([0, 1], [0, 1])
    return qc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shots", type=int, default=1024)
    ap.add_argument("--saida", default="resultados")
    args = ap.parse_args()

    token = os.environ.get("IBM_QUANTUM_TOKEN")
    if not token:
        print("defina IBM_QUANTUM_TOKEN", file=sys.stderr)
        return 2

    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=token)
    backend = service.least_busy(operational=True, simulator=False, min_num_qubits=2)
    print(f"backend: {backend.name} ({backend.num_qubits} qubits)")

    qc = circuito_bell()
    isa = generate_preset_pass_manager(optimization_level=1, backend=backend).run(qc)

    job = SamplerV2(mode=backend).run([isa], shots=args.shots)
    print(f"job: {job.job_id()}  (aguardando na fila...)")
    contagens = job.result()[0].data.c.get_counts()
    metricas = job.metrics()

    total = sum(contagens.values())
    fidelidade_ideal = (contagens.get("00", 0) + contagens.get("11", 0)) / total
    resultado = {
        "quando": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "backend": backend.name,
        "qubits_do_chip": backend.num_qubits,
        "shots": total,
        "contagens": dict(sorted(contagens.items())),
        "fracao_00_ou_11": round(fidelidade_ideal, 4),
        "fracao_ruido": round(1 - fidelidade_ideal, 4),
        "segundos_quanticos_usados": metricas.get("usage", {}).get("quantum_seconds"),
        "job_id": job.job_id(),
    }

    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)
    (saida / "bell.json").write_text(json.dumps(resultado, indent=2, ensure_ascii=False) + "\n")
    (saida / "circuito.txt").write_text(str(qc.draw("text")) + "\n")

    import matplotlib

    matplotlib.use("Agg")
    from qiskit.visualization import plot_histogram

    fig = plot_histogram(contagens, title=f"Estado de Bell em {backend.name} ({total} shots)")
    fig.savefig(saida / "bell.png", dpi=160, bbox_inches="tight")

    print(json.dumps(resultado, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
