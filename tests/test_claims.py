"""JEDE Zahl aus README und App-Texten wird hier nachgerechnet. Formelwerte exakt, simulierte Werte über feste Seeds
(SplitMix64, plattformstabil), Messreihen-Zahlen aus der vorgerechneten Datei mit Marge, nie auf einen einzelnen
verrauschten Wert gepinnt."""

import statistics
from pathlib import Path

import pytest

import mm1_constants as C
import mm1_evaluation as E
import mm1_formulas as F
import mm1_simulation as S

PRE = E.load_precomputed()
GRID = {(g["rho_pct"], g["n"]): g for g in PRE["grid"]}
REQ = {r["rho_pct"]: r for r in PRE["required"]}


def _formula(rho_pct, service_min=3):
    lam, mu = E.rates(rho_pct, service_min)
    return F.stationary_metrics(lam, mu)


def test_formula_values_quoted_in_readme_and_preset_help():
    f50, f90, f97 = _formula(50), _formula(90), _formula(97)
    assert (f50["L"], f50["Wq"]) == pytest.approx((1.0, 3.0))
    assert (f90["L"], f90["Wq"]) == pytest.approx((9.0, 27.0))
    assert (f97["L"], f97["Wq"]) == pytest.approx((32.33, 97.0), abs=0.01)


def test_capacity_reserve_quoted_in_readme():
    before, after, rho_new = E.capacity_reserve(90, 10)
    assert (before, after) == pytest.approx((9.0, 4.5)) and 100 * rho_new == pytest.approx(81.8, abs=0.05)
    assert (after - before) / before == pytest.approx(-0.5)


def test_standard_run_quoted_in_readme():
    """Standardfall (ρ = 90 %, 3 min, 10 000 Lkw, Seed 35): ein EINZELLAUF liegt 14 % unter der Formel - typisch für die Streuung."""
    sim = E.run_live(90, 3, 10000, 35)
    assert sim.mean_in_system == pytest.approx(7.73, abs=0.005)
    assert sim.mean_wait == pytest.approx(23.0, abs=0.05)
    assert (sim.mean_in_system - 9.0) / 9.0 == pytest.approx(-0.141, abs=0.001)
    assert (sim.mean_wait - 27.0) / 27.0 == pytest.approx(-0.147, abs=0.001)


def test_littles_law_holds_exactly_on_every_path_incl_overload():
    for rho in (10, 50, 90, 97, 105, 110):
        sim = E.run_live(rho, 3, 3000, 5, record=False)
        assert E.little_check(sim)[2] < 1e-9


def test_event_simulation_equals_lindley_on_the_readme_seeds():
    for seed in (35, 100000, 100001):
        sim = S.simulate(0.3, 1 / 3, 5000, seed)
        assert max(abs(a - b) for a, b in zip(sim.waits, S.lindley_waits(0.3, 1 / 3, 5000, seed))) < 1e-6


def test_run_to_run_spread_quoted_in_readme():
    """Relative Standardabweichung der Wartezeit eines Laufs (10 000 Lkw): ρ 50 % etwa 5 %, ρ 90 % etwa 18 %, ρ 97 % etwa 50 %;
    mit 50 000 Lkw: ρ 90 % etwa 10 %, ρ 97 % etwa 30 %."""
    assert 100 * GRID[(50, 10000)]["rel_std"] == pytest.approx(5.4, abs=1.5)
    assert 100 * GRID[(90, 10000)]["rel_std"] == pytest.approx(18.2, abs=3.0)
    assert 100 * GRID[(97, 10000)]["rel_std"] == pytest.approx(51.2, abs=10.0)
    assert 100 * GRID[(90, 50000)]["rel_std"] == pytest.approx(10.0, abs=2.0)
    assert 100 * GRID[(97, 50000)]["rel_std"] == pytest.approx(30.1, abs=7.0)
    assert round(100 * GRID[(90, 10000)]["rel_std"]) == 18 and round(100 * GRID[(97, 50000)]["rel_std"]) == 30   # Preset-Hilfetexte


def test_start_bias_quoted_in_readme():
    """Leerer Start unterschätzt die Wartezeit bei ρ = 97 %: kurze Läufe stark, 50 000 Lkw nicht mehr messbar."""
    assert GRID[(97, 1000)]["bias_pct"] < -30
    assert GRID[(97, 10000)]["bias_pct"] < -5
    assert abs(GRID[(97, 50000)]["bias_pct"]) < 6
    assert all(abs(GRID[(50, n)]["bias_pct"]) < 5 for n in C.N_CUSTOMER_OPTIONS)


def _exact_runs_for_1pct(rho_pct, service_min=3):
    """Exakte Lauflänge für ±1 % (95 %) aus der asymptotischen Varianz des Mittels der Wartezeit in der M/M/1-Schlange:
    σ² = ρ (2 + 5ρ − 4ρ² + ρ³) / (μ² (1 − ρ)⁴) (Whitt); n = (1.96 / 0.01)² σ² / E[Wq]². Unabhängig von der Simulation."""
    rho = rho_pct / 100
    mu = 1 / service_min
    sigma2 = rho * (2 + 5 * rho - 4 * rho ** 2 + rho ** 3) / (mu ** 2 * (1 - rho) ** 4)
    return (1.96 / 0.01) ** 2 * sigma2 / _formula(rho_pct, service_min)["Wq"] ** 2


def test_exact_asymptotic_variance_gives_the_known_run_lengths():
    """Handwerte der Formel (ρ = 50 %: σ² = 261 min², E[Wq] = 3 min)."""
    assert _exact_runs_for_1pct(50) == pytest.approx(1.114e6, rel=0.002)
    assert _exact_runs_for_1pct(90) == pytest.approx(17.03e6, rel=0.002)


def test_required_run_length_quoted_in_readme():
    """Lkw je Lauf für ±1 % (95 %): rund 1.0 Mio. / 6 Mio. / 19 Mio. / 67 Mio. / 1.5 Mrd. (300 Läufe à 1 Mio. Lkw, Messunsicherheit ±8 %, 1σ)."""
    assert PRE["required_reps"] == 300 and PRE["required_n"] == 1_000_000
    assert REQ[50]["n_for_1pct"] == pytest.approx(1.04e6, rel=0.01)
    assert REQ[80]["n_for_1pct"] == pytest.approx(6.0e6, rel=0.01)
    assert REQ[90]["n_for_1pct"] == pytest.approx(19e6, rel=0.01)
    assert REQ[95]["n_for_1pct"] == pytest.approx(67e6, rel=0.01)
    assert REQ[99]["n_for_1pct"] == pytest.approx(1.46e9, rel=0.01)
    assert 1300 < REQ[99]["n_for_1pct"] / REQ[50]["n_for_1pct"] < 1500   # "etwa das 1 400-Fache"


def test_required_run_length_matches_the_exact_asymptotic_variance():
    """Bindung an die exakte Rechnung: das Band (±30 %, ρ = 99 %: ±35 %) deckt gut dreieinhalb Standardfehler der 300-Läufe-Messung plus die
    Startverzerrung ab. Die frühere 60-Läufe-Zahl (0.65 Mio. bei ρ = 50 %, 42 % unter 1.11 Mio.) läge außerhalb."""
    for rho_pct, band in ((50, 0.30), (80, 0.30), (90, 0.30), (95, 0.30), (99, 0.35)):
        assert REQ[rho_pct]["n_for_1pct"] == pytest.approx(_exact_runs_for_1pct(rho_pct), rel=band), rho_pct
    assert REQ[50]["n_for_1pct"] > 0.65e6 * 1.3


def test_readme_quotes_the_stored_run_lengths():
    """Die Zahlen der README-Zeile „Wie lang muss ein Lauf sein“ sind die gerundeten Werte der vorgerechneten Datei."""
    row = next(line for line in (Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8").splitlines()
               if line.startswith("| Wie lang muss ein Lauf sein"))
    def mio(rho):
        return REQ[rho]["n_for_1pct"] / 1e6
    factor = f"{round(REQ[99]['n_for_1pct'] / REQ[50]['n_for_1pct'], -2):,.0f}".replace(",", " ")
    expected = [f"Rund **{mio(50):.1f} Mio.** Lkw bei ρ = 50 %", f"{mio(80):.0f} Mio. bei 80 %", f"**{mio(90):.0f} Mio.** bei 90 %",
                f"{mio(95):.0f} Mio. bei 95 %", f"**{mio(99) / 1e3:.1f} Mrd.** bei 99 %", f"das {factor}-Fache"]
    for text in expected:
        assert text in row, text


def test_sweep_points_follow_the_formula_curve():
    """Simulierte Mittel (200 Läufe à 50 000 Lkw) liegen innerhalb von vier Standardfehlern plus 2 % Startverzerrung an der Formel."""
    n = max(C.N_CUSTOMER_OPTIONS)
    for rho in C.SWEEP_RHO_PCT:
        g = GRID[(rho, n)]
        se = g["rel_std"] * g["mean_wq"] / PRE["grid_reps"] ** 0.5
        assert abs(g["mean_wq"] - g["exact_wq"]) <= 4 * se + 0.02 * g["exact_wq"], rho


def test_fixed_service_halves_the_wait():
    """Feste Abfertigungsdauer: Wartezeit = Hälfte von M/M/1 (Formel exakt); simuliert bei ρ = 50 % über fünf Seeds à 100 000 Lkw."""
    runs = [E.compare_services(50, 3, 100000, 100 + k) for k in range(5)]
    fest = statistics.fmean(r["fest"]["wq"] for r in runs)
    exp = statistics.fmean(r["exp"]["wq"] for r in runs)
    assert runs[0]["md1_formula_wq"] == pytest.approx(1.5) and runs[0]["mm1_formula_wq"] == pytest.approx(3.0)
    assert fest == pytest.approx(1.5, rel=0.04) and exp == pytest.approx(3.0, rel=0.04)
    assert fest / exp == pytest.approx(0.5, abs=0.04)
