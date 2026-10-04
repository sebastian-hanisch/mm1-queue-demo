"""Formeln gegen Handrechnung und gegen eine UNABHÄNGIGE Referenz: das lineare Gleichungssystem der abgeschnittenen
Geburts-Sterbe-Kette (kein Gebrauch der geschlossenen Formeln)."""

import math

import numpy as np
import pytest

import mm1_formulas as F


def _ctmc_stationary(lam, mu, k_max):
    """Stationäre Verteilung der auf 0..k_max abgeschnittenen Kette: π Q = 0, Σπ = 1 (lineares Gleichungssystem)."""
    n = k_max + 1
    q = np.zeros((n, n))
    for i in range(n - 1):
        q[i, i + 1] = lam
        q[i + 1, i] = mu
    np.fill_diagonal(q, -q.sum(axis=1))
    a = np.vstack([q.T[:-1], np.ones(n)])
    b = np.zeros(n)
    b[-1] = 1.0
    return np.linalg.solve(a, b)


@pytest.mark.parametrize("rho", [0.3, 0.5, 0.8, 0.9])
def test_geometric_formulas_match_the_ctmc_reference(rho):
    mu, lam = 1.0, rho
    pi = _ctmc_stationary(lam, mu, 400)
    states = np.arange(len(pi))
    m = F.stationary_metrics(lam, mu)
    assert (pi * states).sum() == pytest.approx(m["L"], rel=1e-6)
    assert (pi[1:] * (states[1:] - 1)).sum() == pytest.approx(m["Lq"], rel=1e-6)
    for n in (0, 1, 5):
        assert pi[n] == pytest.approx(F.p_n(lam, mu, n), rel=1e-6)
    # Little's Gesetz auf den Formelwerten (Gegenprobe, nicht Herleitung)
    assert m["L"] == pytest.approx(lam * m["W"], rel=1e-12)
    assert m["Lq"] == pytest.approx(lam * m["Wq"], rel=1e-12)


def test_hand_values_at_rho_one_half_and_nine_tenths():
    half = F.stationary_metrics(0.5, 1.0)
    assert (half["L"], half["Lq"], half["W"], half["Wq"]) == pytest.approx((1.0, 0.5, 2.0, 1.0))
    nine = F.stationary_metrics(0.9, 1.0)
    assert (nine["L"], nine["Wq"], nine["p_wait"]) == pytest.approx((9.0, 9.0, 0.9))


def test_overload_has_no_stationary_distribution():
    assert not F.is_stable(1.0, 1.0) and not F.is_stable(1.2, 1.0)
    with pytest.raises(ValueError):
        F.stationary_metrics(1.0, 1.0)
    with pytest.raises(ValueError):
        F.md1_mean_wait(1.1, 1.0)


def test_probabilities_sum_to_one_and_tail_is_a_survival_function():
    total = sum(F.p_n(0.7, 1.0, n) for n in range(2000))
    assert total == pytest.approx(1.0, rel=1e-9)
    assert F.prob_wait_exceeds(0.7, 1.0, 0.0) == pytest.approx(0.7)      # P(Wq > 0) = ρ
    assert F.prob_wait_exceeds(0.7, 1.0, 5.0) == pytest.approx(0.7 * math.exp(-0.3 * 5.0))
    assert F.prob_wait_exceeds(0.7, 1.0, 10.0) < F.prob_wait_exceeds(0.7, 1.0, 5.0)


def test_md1_wait_is_exactly_half_of_mm1_wait():
    for rho in (0.3, 0.6, 0.9):
        assert F.md1_mean_wait(rho, 1.0) == pytest.approx(F.stationary_metrics(rho, 1.0)["Wq"] / 2)
