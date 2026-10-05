"""Orakel mit anderem Rechenweg: (1) P(Wq > t) als Mischung von Erlang-Verteilungen über die Gleichgewichtsverteilung der abgeschnittenen Kette (statt der Formel ρ·e^{−(μ−λ)t}) und
Pollaczek-Khinchine über E[S²]; (2) die Ereignissimulation gegen eine Kunde-für-Kunde-Rechnung in absoluten Zeiten (Start = max(Ankunft, Abgang des Vorgängers)) samt Flächen unter N(t),
Zeit je Zustand, Wartezeit-Anteilen und Treppenkurve, mit den Zufallszahlen der Demo, aber ohne Ereignisliste."""

import math
import random

import numpy as np
import pytest

import mm1_evaluation as E
import mm1_formulas as F
import mm1_simulation as S


def _ctmc(lam, mu, k_max):
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


def test_wait_tail_equals_the_erlang_mixture_over_the_chain():
    """Wer n Lkw vor sich findet (n ≥ 1), wartet Erlang(n, μ)-verteilt: P(Wq > t) = Σ_{n≥1} π_n · P(Poisson(μt) ≤ n − 1)."""
    rng = random.Random(1)
    for _ in range(12):
        mu, rho = rng.uniform(0.2, 2.0), rng.uniform(0.1, 0.85)
        lam = rho * mu
        pi = _ctmc(lam, mu, max(200, int(40 / (1 - rho))))
        assert pi[-5:].sum() < 1e-12
        for t in (0.0, 1.0 / mu, 4.0 / mu):
            x = mu * t
            cum = np.cumsum([math.exp(-x) * x ** k / math.factorial(k) for k in range(150)])
            surv = sum(pi[n] * cum[n - 1] for n in range(1, 150))
            surv += pi[150:].sum()
            assert F.prob_wait_exceeds(lam, mu, t) == pytest.approx(surv, abs=1e-9)


def test_deterministic_service_wait_by_pollaczek_khinchine_second_moment():
    for rho in (0.2, 0.5, 0.9):
        lam, mu = rho, 1.0
        assert F.md1_mean_wait(lam, mu) == pytest.approx(lam * (1 / mu) ** 2 / (2 * (1 - rho)))


def _naive(lam, mu, n, seed, service):
    rng = S.SplitMix64(seed)
    arr, svc, t = [], [], 0.0
    for _ in range(n):
        t += rng.expovariate(lam)
        arr.append(t)
        svc.append(rng.expovariate(mu) if service == S.SERVICE_EXP else 1 / mu)
    start, dep, free = [], [], 0.0
    for k in range(n):
        s = max(arr[k], free)
        free = s + svc[k]
        start.append(s)
        dep.append(free)
    return arr, start, dep


@pytest.mark.parametrize("service", [S.SERVICE_EXP, S.SERVICE_FIXED])
def test_event_simulation_equals_a_customer_by_customer_recursion(service):
    rng = random.Random(5)
    for it in range(40):
        n, mu = rng.randint(1, 40), rng.uniform(0.2, 2.0)
        lam, seed = rng.uniform(0.1, 1.4) * mu, rng.randint(0, 10 ** 6)
        sim = S.simulate(lam, mu, n, seed, service, record=True)
        arr, start, dep = _naive(lam, mu, n, seed, service)
        assert sim.waits == pytest.approx([s - a for s, a in zip(start, arr)], abs=1e-9)
        assert sim.sojourns == pytest.approx([d - a for d, a in zip(dep, arr)], abs=1e-9)
        assert sim.end_time == pytest.approx(dep[-1])
        events = sorted([(a, 1) for a in arr] + [(d, -1) for d in dep])
        cur, t0, area, area_q, busy, spent = 0, 0.0, 0.0, 0.0, 0.0, {}
        for t, delta in events:
            dt = t - t0
            area += cur * dt
            area_q += max(cur - 1, 0) * dt
            busy += dt if cur > 0 else 0.0
            spent[cur] = spent.get(cur, 0.0) + dt
            cur, t0 = cur + delta, t
        assert (sim.area_in_system, sim.area_in_queue, sim.busy_time) == pytest.approx((area, area_q, busy), rel=1e-9, abs=1e-9)
        for state, value in spent.items():
            assert sim.time_in_state.get(state, 0.0) == pytest.approx(value, abs=1e-9)
        shares, rest = E.state_distribution(sim, max_state=2)
        total = sum(spent.values())
        assert shares == pytest.approx([spent.get(k, 0.0) / total for k in range(3)], abs=1e-9)
        assert rest == pytest.approx(1 - sum(shares), abs=1e-9)
        for threshold in (0.1, 1.0, 5.0):
            assert E.wait_tail_fractions(sim, (threshold,))[threshold] == pytest.approx(sum(1 for s, a in zip(start, arr) if s - a > threshold) / n)
        lo, hi = sorted([rng.uniform(0, sim.end_time), rng.uniform(0, sim.end_time)])

        def n_at(t):
            return sum(d for tt, d in events if tt <= t)
        steps = E.window_steps(sim.trajectory, lo, hi)
        assert steps[0] == (lo, n_at(lo)) and steps[-1] == (hi, n_at(hi))
        assert all(value == n_at(t) for t, value in steps[1:-1])
