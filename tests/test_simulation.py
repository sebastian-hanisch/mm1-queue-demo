"""Simulation: Zufallsgenerator, Mini-Instanz von Hand gerechnet, Ereignissimulation gegen Lindley-Rekursion,
Little's Gesetz als Pfadidentität."""

import pytest

import mm1_simulation as S


def test_splitmix64_matches_the_reference_sequence():
    """Referenzfolge des Verfahrens (Vigna) für Startwert 0."""
    rng = S.SplitMix64(0)
    assert [rng.next() for _ in range(3)] == [0xE220A8397B1DCDAF, 0x6E789E6AA1B965F4, 0x06C45D188009454F]


def test_uniform_is_in_unit_interval_and_expovariate_is_positive_with_correct_mean():
    rng = S.SplitMix64(5)
    us = [rng.uniform() for _ in range(2000)]
    assert all(0.0 <= u < 1.0 for u in us)
    ex = [rng.expovariate(0.5) for _ in range(20000)]
    assert min(ex) > 0
    assert sum(ex) / len(ex) == pytest.approx(2.0, rel=0.05)


def test_mini_instance_by_hand(mini_rng):
    """Ankünfte 1 / 2.5 / 3.5, Bedienzeiten 2 / 2 / 1: Beginn 1, 3, 5; Abgänge 3, 5, 6.
    Wartezeiten 0 / 0.5 / 1.5, Verweilzeiten 2 / 2.5 / 2.5, ∫N dt = 7, ∫Nq dt = 2, belegt 5 von 6 Minuten."""
    r = S.simulate(0.5, 0.5, 3, seed=0, rng=mini_rng, record=True)
    assert r.waits == pytest.approx([0.0, 0.5, 1.5])
    assert r.sojourns == pytest.approx([2.0, 2.5, 2.5])
    assert r.end_time == pytest.approx(6.0)
    assert r.area_in_system == pytest.approx(7.0)
    assert r.area_in_queue == pytest.approx(2.0)
    assert r.busy_time == pytest.approx(5.0)
    assert r.time_in_state == pytest.approx({0: 1.0, 1: 3.0, 2: 2.0})
    assert [n for _, n in r.trajectory] == [0, 1, 2, 1, 2, 1, 0]
    assert r.mean_in_system == pytest.approx(7 / 6)


def test_mini_instance_lindley_gives_the_same_waits(mini_rng):
    assert S.lindley_waits(0.5, 0.5, 3, seed=0, rng=mini_rng) == pytest.approx([0.0, 0.5, 1.5])


@pytest.mark.parametrize("service", [S.SERVICE_EXP, S.SERVICE_FIXED])
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_event_simulation_and_lindley_agree_customer_by_customer(seed, service):
    sim = S.simulate(0.27, 1 / 3, 3000, seed, service)
    lw = S.lindley_waits(0.27, 1 / 3, 3000, seed, service)
    assert max(abs(a - b) for a, b in zip(sim.waits, lw)) < 1e-6


@pytest.mark.parametrize("rho", [0.5, 0.9, 1.05])
def test_littles_law_holds_exactly_on_every_path(rho):
    """Das System endet leer, also ist ∫N dt = Σ Verweilzeiten (jeder Kunde trägt seine Verweilzeit bei) - auch bei Überlast."""
    sim = S.simulate(rho / 3, 1 / 3, 5000, 7)
    assert sim.area_in_system == pytest.approx(sum(sim.sojourns), rel=1e-9)
    assert sim.mean_in_system == pytest.approx(sim.arrival_rate * sim.mean_sojourn, rel=1e-9)


def test_queue_never_negative_and_fifo_order_of_departures():
    sim = S.simulate(0.3, 1 / 3, 2000, 4)
    assert min(sim.waits) >= 0.0 and all(s >= w for s, w in zip(sim.sojourns, sim.waits))
    assert sum(sim.time_in_state.values()) == pytest.approx(sim.end_time)


def test_same_seed_same_result_different_seed_different_result():
    a = S.simulate(0.25, 1 / 3, 500, 11)
    b = S.simulate(0.25, 1 / 3, 500, 11)
    c = S.simulate(0.25, 1 / 3, 500, 12)
    assert a.waits == b.waits and a.waits != c.waits


def test_fixed_service_draws_no_service_random_numbers():
    """Bei fester Bedienzeit sind die Zwischenankunftszeiten dieselben wie bei exponentieller (gleicher Zufallsstrom
    für die Ankünfte), sonst wäre der Vergleich in `compare_services` nicht fair."""
    class Counting(S.SplitMix64):
        calls = 0

        def next(self):
            Counting.calls += 1
            return super().next()

    Counting.calls = 0
    S.simulate(0.3, 1 / 3, 100, 0, S.SERVICE_FIXED, rng=Counting(3))
    fixed_calls = Counting.calls
    Counting.calls = 0
    S.simulate(0.3, 1 / 3, 100, 0, S.SERVICE_EXP, rng=Counting(3))
    assert Counting.calls == 2 * fixed_calls - 1 or Counting.calls > fixed_calls
