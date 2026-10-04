"""Auswertung der Simulation gegen die Formeln: Kennzahlen, Verteilungen, Little-Gegenprobe, Kapazitätsreserve,
Gegenbeispiel feste Bedienzeit. Die teuren Messreihen (viele lange Läufe) stehen vorgerechnet in
`precomputed_sweep.json` (Generator: generate_precomputed.py, Laden: `load_precomputed`)."""

import json
import math
import statistics
from pathlib import Path

import mm1_constants as C
import mm1_formulas as F
from mm1_simulation import SERVICE_EXP, SERVICE_FIXED, lindley_waits, simulate

PRECOMPUTED_PATH = Path(__file__).resolve().parent / "precomputed_sweep.json"


def rates(rho_pct, service_min):
    """(λ, μ) je Minute aus Auslastung in Prozent und mittlerer Abfertigungsdauer in Minuten."""
    mu = 1.0 / service_min
    return rho_pct / 100.0 * mu, mu


def run_live(rho_pct, service_min, n_customers, seed, service=SERVICE_EXP, record=True):
    lam, mu = rates(rho_pct, service_min)
    return simulate(lam, mu, n_customers, seed, service, record=record)


def little_check(sim):
    """Little's Gesetz auf dem simulierten Pfad: (L aus ∫N dt / T, λ̂ · Ŵ, relative Abweichung). Gilt hier exakt
    (bis auf Rundung), weil jeder Lauf mit leerem System endet - jeder Kunde trägt genau seine Verweilzeit zur Fläche
    unter N(t) bei."""
    l_hat = sim.mean_in_system
    lw = sim.arrival_rate * sim.mean_sojourn
    return l_hat, lw, abs(l_hat - lw) / l_hat if l_hat else 0.0


def running_mean_in_system(trajectory, n_points=400):
    """Zeitlicher Mittelwert von N(t) über [0, t] an etwa `n_points` Stützstellen: [(t, Mittelwert bis t)]."""
    if len(trajectory) < 2:
        return []
    stride = max(1, len(trajectory) // n_points)
    area, out = 0.0, []
    for k in range(1, len(trajectory)):
        t0, n0 = trajectory[k - 1]
        t1, _ = trajectory[k]
        area += n0 * (t1 - t0)
        if k % stride == 0 and t1 > 0:
            out.append((t1, area / t1))
    return out


def state_distribution(sim, max_state=C.MAX_STATE_SHOWN):
    """Anteil der Zeit mit genau n im System (n = 0 … max_state); der Rest ab max_state + 1 wird zusammengefasst.
    Rückgabe: (Liste der Anteile, Anteil darüber)."""
    total = sum(sim.time_in_state.values())
    shares = [sim.time_in_state.get(n, 0.0) / total for n in range(max_state + 1)]
    return shares, max(0.0, 1.0 - sum(shares))


def wait_tail_fractions(sim, thresholds=C.TAIL_MINUTES):
    """Anteil der Lkw mit Wartezeit über t Minuten, für jedes t in `thresholds`."""
    n = sim.n_customers
    return {t: sum(1 for w in sim.waits if w > t) / n for t in thresholds}


def wait_survival_curve(sim, t_max, n_points=60):
    """P(Wq > t) aus den simulierten Wartezeiten an gleichmäßigen Stützstellen 0 … t_max: ([t], [Anteil])."""
    waits = sorted(sim.waits)
    n = len(waits)
    ts = [t_max * k / (n_points - 1) for k in range(n_points)]
    out, idx = [], 0
    for t in ts:
        while idx < n and waits[idx] <= t:
            idx += 1
        out.append((n - idx) / n)
    return ts, out


def window_steps(trajectory, start_min, end_min):
    """Treppenkurve N(t) im Fenster [start_min, end_min]: Stützpunkte (t, N), links mit dem Wert zum Fensterbeginn,
    rechts mit dem letzten Wert im Fenster abgeschlossen. Für `line_shape='hv'`."""
    n_start = 0
    pts = []
    for t, n in trajectory:
        if t <= start_min:
            n_start = n
        elif t <= end_min:
            pts.append((t, n))
        else:
            break
    out = [(start_min, n_start)] + pts
    out.append((end_min, out[-1][1]))
    return out


def capacity_reserve(rho_pct, speedup_pct):
    """Wirkung von `speedup_pct` % schnellerer Abfertigung bei gleicher Ankunftsrate: (L vorher, L nachher, ρ nachher).
    L ist None, wo ρ ≥ 1 gilt (vorher: Schlange wächst ohne Grenze; nachher: auch nach der Beschleunigung noch)."""
    rho = rho_pct / 100.0
    rho_new = rho / (1 + speedup_pct / 100.0)
    l_before = rho / (1 - rho) if rho < 1 else None
    l_after = rho_new / (1 - rho_new) if rho_new < 1 else None
    return l_before, l_after, rho_new


def compare_services(rho_pct, service_min, n_customers, seed):
    """Dasselbe Gate zweimal mit denselben Ankünften: exponentielle gegen feste Bedienzeit (gleiches Mittel).
    Gegenbeispiel zur M/M/1-Annahme: Little's Gesetz gilt in beiden Läufen, die M/M/1-Formel für die Wartezeit nur
    im ersten. Rückgabe None bei ρ ≥ 1."""
    lam, mu = rates(rho_pct, service_min)
    if not F.is_stable(lam, mu):
        return None
    out = {"mm1_formula_wq": F.stationary_metrics(lam, mu)["Wq"], "md1_formula_wq": F.md1_mean_wait(lam, mu)}
    for key, service in (("exp", SERVICE_EXP), ("fest", SERVICE_FIXED)):
        sim = simulate(lam, mu, n_customers, seed, service)
        _, _, little_gap = little_check(sim)
        out[key] = {"wq": sim.mean_wait, "l": sim.mean_in_system, "little_gap": little_gap}
    return out


def estimator_study(rho_pct, n_customers, reps, seed_base, service_min=3):
    """Wartezeit-Schätzer über `reps` unabhängige Läufe (leeres System am Start, alle Kunden zählen): Mittel der
    Schätzwerte, Abweichung vom exakten Wq in Prozent (Startverzerrung) und relative Standardabweichung eines Laufs.
    Rechnet mit der Lindley-Rekursion (liefert Kunde für Kunde dieselben Wartezeiten wie die Ereignissimulation,
    ist aber schneller; belegt in tests/test_simulation.py). Nur für ρ < 1."""
    lam, mu = rates(rho_pct, service_min)
    exact = F.stationary_metrics(lam, mu)["Wq"]
    ests = [sum(lindley_waits(lam, mu, n_customers, seed_base + r)) / n_customers for r in range(reps)]
    mean, sd = statistics.fmean(ests), statistics.stdev(ests)
    return {"rho_pct": rho_pct, "n": n_customers, "reps": reps, "exact_wq": exact, "mean_wq": mean,
            "bias_pct": 100.0 * (mean - exact) / exact, "rel_std": sd / mean,
            "n_for_1pct": n_customers * (1.96 * sd / exact / 0.01) ** 2}


def _interp(xs, ys, x):
    """Lineare Interpolation (außerhalb der Stützstellen: Randwert)."""
    if x <= xs[0]:
        return ys[0]
    for k in range(1, len(xs)):
        if x <= xs[k]:
            w = (x - xs[k - 1]) / (xs[k] - xs[k - 1])
            return ys[k - 1] + w * (ys[k] - ys[k - 1])
    return ys[-1]


def typical_run_error(precomputed, rho_pct, n_customers):
    """Gemessene typische Abweichung EINES Laufs von der Formel-Wartezeit (relative Standardabweichung) und
    mittlere Startverzerrung in Prozent für die gewählte Auslastung und Lauflänge, aus der vorgerechneten Tabelle
    (linear zwischen den gemessenen Auslastungen). None für ρ ≥ 1 oder jenseits der gemessenen Auslastungen."""
    grid = precomputed["grid"]
    rhos = sorted({row["rho_pct"] for row in grid})
    if rho_pct >= 100 or rho_pct > rhos[-1]:
        return None
    rows = {r["rho_pct"]: r for r in grid if r["n"] == n_customers}
    return (_interp(rhos, [rows[r]["rel_std"] for r in rhos], rho_pct),
            _interp(rhos, [rows[r]["bias_pct"] for r in rhos], rho_pct))


def load_precomputed():
    with open(PRECOMPUTED_PATH, encoding="utf-8") as f:
        return json.load(f)
