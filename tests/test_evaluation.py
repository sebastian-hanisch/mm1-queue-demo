"""Auswertung: Mini-Instanz von Hand, Interpolation der vorgerechneten Tabelle, Kapazitätsreserve, Vollständigkeit der
Messreihen-Datei."""

import pytest

import mm1_constants as C
import mm1_evaluation as E
import mm1_simulation as S


@pytest.fixture
def mini(mini_rng):
    return S.simulate(0.5, 0.5, 3, seed=0, rng=mini_rng, record=True)


def test_rates_from_utilisation_and_service_time():
    lam, mu = E.rates(90, 3)
    assert mu == pytest.approx(1 / 3) and lam == pytest.approx(0.3)
    assert E.rates(50, 6)[0] == pytest.approx(1 / 12)


def test_little_check_on_the_mini_instance(mini):
    l_hat, lw, gap = E.little_check(mini)
    assert l_hat == pytest.approx(7 / 6) and lw == pytest.approx(7 / 6) and gap < 1e-12


def test_running_mean_ends_at_the_overall_mean(mini):
    series = E.running_mean_in_system(mini.trajectory)
    assert series[0] == pytest.approx((1.0, 0.0))             # bis t = 1 war das Gate leer
    assert series[-1] == pytest.approx((6.0, 7 / 6))
    assert E.running_mean_in_system([(0.0, 0)]) == []


def test_running_mean_is_decimated_for_long_runs():
    sim = S.simulate(0.2, 1 / 3, 5000, 3, record=True)
    series = E.running_mean_in_system(sim.trajectory, n_points=400)
    assert 300 <= len(series) <= 450
    assert series[-1][1] == pytest.approx(sim.mean_in_system, rel=0.01)


def test_state_distribution_on_the_mini_instance(mini):
    shares, rest = E.state_distribution(mini, max_state=2)
    assert shares == pytest.approx([1 / 6, 3 / 6, 2 / 6]) and rest == pytest.approx(0.0, abs=1e-12)
    shares1, rest1 = E.state_distribution(mini, max_state=1)
    assert rest1 == pytest.approx(2 / 6) and sum(shares1) + rest1 == pytest.approx(1.0)


def test_wait_tail_and_survival_curve_by_hand(mini):
    """Wartezeiten 0 / 0.5 / 1.5."""
    assert E.wait_tail_fractions(mini, thresholds=(0.4, 1.0, 2.0)) == pytest.approx({0.4: 2 / 3, 1.0: 1 / 3, 2.0: 0.0})
    ts, surv = E.wait_survival_curve(mini, t_max=2.0, n_points=5)
    assert ts == pytest.approx([0, 0.5, 1.0, 1.5, 2.0])
    assert surv == pytest.approx([2 / 3, 1 / 3, 1 / 3, 0.0, 0.0])


def test_window_steps_on_the_mini_trajectory(mini):
    assert E.window_steps(mini.trajectory, 2.0, 4.0) == [(2.0, 1), (2.5, 2), (3.0, 1), (3.5, 2), (4.0, 2)]
    assert E.window_steps(mini.trajectory, 0.0, 1.5)[0] == (0.0, 0)


def test_capacity_reserve_by_hand():
    before, after, rho_new = E.capacity_reserve(90, 10)
    assert before == pytest.approx(9.0) and after == pytest.approx(4.5) and rho_new == pytest.approx(0.9 / 1.1)
    assert E.capacity_reserve(105, 10)[0] is None and E.capacity_reserve(105, 10)[1] == pytest.approx(0.95454545 / 0.04545454, rel=1e-4)
    assert E.capacity_reserve(105, 5) [1] is None and E.capacity_reserve(110, 5)[1] is None


def test_compare_services_returns_none_under_overload_and_both_runs_otherwise():
    assert E.compare_services(105, 3, 1000, 1) is None
    out = E.compare_services(50, 3, 2000, 1)
    assert set(out) == {"mm1_formula_wq", "md1_formula_wq", "exp", "fest"}
    assert out["md1_formula_wq"] == pytest.approx(out["mm1_formula_wq"] / 2)
    assert out["exp"]["little_gap"] < 1e-9 and out["fest"]["little_gap"] < 1e-9


def test_estimator_study_small_cell_is_plausible():
    cell = E.estimator_study(50, 10000, 60, seed_base=424242)
    assert cell["exact_wq"] == pytest.approx(3.0)
    assert 0.03 < cell["rel_std"] < 0.09 and abs(cell["bias_pct"]) < 3.0


def test_precomputed_file_is_complete_and_consistent():
    pre = E.load_precomputed()
    assert {(g["rho_pct"], g["n"]) for g in pre["grid"]} == {(r, n) for r in C.SWEEP_RHO_PCT for n in C.N_CUSTOMER_OPTIONS}
    assert all(g["reps"] == pre["grid_reps"] for g in pre["grid"])
    assert [r["rho_pct"] for r in pre["required"]] == [50, 80, 90, 95, 99]
    req = {r["rho_pct"]: r["n_for_1pct"] for r in pre["required"]}
    assert req[50] < req[80] < req[90] < req[95] < req[99]


def test_streuung_grows_with_utilisation_and_shrinks_with_run_length():
    """Qualitative Ordnung der Messreihe (keine exakten Zahlen): längere Läufe streuen weniger, höhere Auslastung mehr."""
    grid = {(g["rho_pct"], g["n"]): g for g in E.load_precomputed()["grid"]}
    for rho in (50, 90, 97):
        assert grid[(rho, 50000)]["rel_std"] < grid[(rho, 1000)]["rel_std"]
    for n in C.N_CUSTOMER_OPTIONS:
        assert grid[(50, n)]["rel_std"] < grid[(90, n)]["rel_std"] < grid[(97, n)]["rel_std"] * 1.2


def test_typical_run_error_lookup_and_interpolation():
    pre = E.load_precomputed()
    rel90, bias90 = E.typical_run_error(pre, 90, 10000)
    row = next(g for g in pre["grid"] if g["rho_pct"] == 90 and g["n"] == 10000)
    assert (rel90, bias90) == pytest.approx((row["rel_std"], row["bias_pct"]))
    rel85, _ = E.typical_run_error(pre, 85, 10000)
    rel93, _ = E.typical_run_error(pre, 93, 10000)
    assert min(rel85, rel93) <= E.typical_run_error(pre, 88, 10000)[0] <= max(rel85, rel93) + 1e-9
    assert E.typical_run_error(pre, 100, 10000) is None and E.typical_run_error(pre, 105, 10000) is None
    assert E.typical_run_error(pre, 99, 10000) is None          # jenseits der gemessenen Auslastungen (≤ 97 %)
