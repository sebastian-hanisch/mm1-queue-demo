"""Rechnet die teuren Messreihen vor (Build-Zeit, nicht in der App): `python generate_precomputed.py` schreibt
`precomputed_sweep.json`. Dauer: einige Minuten, parallel auf mehreren Prozessen.

  grid      Auslastung × Lauflänge: Startverzerrung und Streuung eines Laufs (je 200 Läufe)
  required  Lkw je Lauf für ±1 % Genauigkeit (95 %) bei ausgewählten Auslastungen (Lauflänge 1 Mio., 60 Läufe)
"""

import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import mm1_constants as C
from mm1_evaluation import PRECOMPUTED_PATH, estimator_study

GRID_REPS = 200
REQUIRED_RHO_PCT = (50, 80, 90, 95, 99)
REQUIRED_N, REQUIRED_REPS = 1_000_000, 60


def _grid_task(args):
    rho_pct, n_idx, n = args
    return estimator_study(rho_pct, n, GRID_REPS, seed_base=rho_pct * 10_000_000 + n_idx * 1_000_000)


def _required_task(rho_pct):
    return estimator_study(rho_pct, REQUIRED_N, REQUIRED_REPS, seed_base=rho_pct * 10_000_000 + 9_000_000)


def main(workers):
    t0 = time.time()
    grid_jobs = [(r, i, n) for r in C.SWEEP_RHO_PCT for i, n in enumerate(C.N_CUSTOMER_OPTIONS)]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        required = list(ex.map(_required_task, REQUIRED_RHO_PCT))
        grid = list(ex.map(_grid_task, grid_jobs))
    out = {"service_min": 3, "grid_reps": GRID_REPS, "required_n": REQUIRED_N, "required_reps": REQUIRED_REPS,
           "grid": grid, "required": required}
    Path(PRECOMPUTED_PATH).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"fertig in {time.time() - t0:.0f} s -> {PRECOMPUTED_PATH}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else min(6, os.cpu_count() or 1))
