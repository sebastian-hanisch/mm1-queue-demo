"""JEDE Zahl aus README und App-Texten wird hier nachgerechnet. Formelwerte exakt, simulierte Werte über feste Seeds
(SplitMix64, plattformstabil), Messreihen-Zahlen aus der vorgerechneten Datei mit Marge, nie auf einen einzelnen
verrauschten Wert gepinnt."""

import statistics

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


def test_required_run_length_quoted_in_readme():
    """Lkw je Lauf für ±1 % (95 %): rund 0.6 Mio. / 6 Mio. / 20 Mio. / 70 Mio. / 1.1 Mrd. (Messunsicherheit rund ±20 %)."""
    assert REQ[50]["n_for_1pct"] == pytest.approx(0.65e6, rel=0.35)
    assert REQ[80]["n_for_1pct"] == pytest.approx(5.6e6, rel=0.35)
    assert REQ[90]["n_for_1pct"] == pytest.approx(20e6, rel=0.35)
    assert REQ[95]["n_for_1pct"] == pytest.approx(68e6, rel=0.35)
    assert REQ[99]["n_for_1pct"] == pytest.approx(1.1e9, rel=0.4)
    assert 1000 < REQ[99]["n_for_1pct"] / REQ[50]["n_for_1pct"] < 3500


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
