"""AppTest-Rauchtests: Voreinstellung, jedes Preset, Überlast, Randwerte, Würfel-Knopf, Permalink-Grenzen, Abschnitte, Footer."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import mm1_constants as C

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def _run(**state):
    at = AppTest.from_file(APP, default_timeout=300)
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    return at


def _ok(at):
    assert not at.exception, [e.value for e in at.exception]


def _metric(at, label):
    return next(m.value for m in at.metric if m.label == label)


def test_default_run_has_no_exception_and_shows_formula_and_simulation():
    at = _run()
    _ok(at)
    assert _metric(at, "Auslastung ρ") == "90 %"
    assert _metric(at, "Lkw im System, Mittel (Formel)") == "9.00"
    assert _metric(at, "Wartezeit in der Schlange (Formel)") == "27.0 min"
    assert _metric(at, "Lkw im System, Mittel (simuliert)") == "7.73"
    assert _metric(at, "Little's Gesetz im Lauf: L gegen λ·W") == "stimmt"
    assert any("Ein einzelner Lauf ist keine Messung der Formel" in i.value for i in at.info)


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_button_runs(name):
    at = _run()
    next(b for b in at.button if b.key == f"preset_{name}").click().run()
    _ok(at)
    p = C.PRESETS[name]
    assert at.session_state["rho_slider"] == p["rho_pct"] and at.session_state["n_customers_select"] == p["n_customers"]
    assert at.metric


def test_overload_shows_a_warning_and_no_formula_values():
    at = _run(rho_slider=105)
    _ok(at)
    assert _metric(at, "Lkw im System, Mittel (Formel)").startswith("gilt nicht")
    assert any("kein Gleichgewicht" in w.value for w in at.warning)
    assert any("braucht ein Gleichgewicht" in i.value for i in at.info)


def test_exactly_at_the_stability_limit_is_overload():
    at = _run(rho_slider=100)
    _ok(at)
    assert _metric(at, "Lkw im System, Mittel (Formel)").startswith("gilt nicht")


@pytest.mark.parametrize("kw", [dict(rho_slider=C.RHO_PCT_MIN), dict(rho_slider=C.RHO_PCT_MAX),
                                 dict(service_slider=C.SERVICE_MIN_MIN), dict(service_slider=C.SERVICE_MIN_MAX),
                                 dict(n_customers_select=C.N_CUSTOMER_OPTIONS[0]),
                                 dict(n_customers_select=C.N_CUSTOMER_OPTIONS[-1], rho_slider=97),
                                 dict(rho_slider=99)])
def test_extreme_settings_run(kw):
    _ok(_run(**kw))


def test_utilisation_is_independent_of_the_service_time_slider():
    a = _run(service_slider=1)
    b = _run(service_slider=6)
    _ok(a)
    _ok(b)
    assert _metric(a, "Lkw im System, Mittel (Formel)") == _metric(b, "Lkw im System, Mittel (Formel)")
    assert _metric(a, "Wartezeit in der Schlange (Formel)") != _metric(b, "Wartezeit in der Schlange (Formel)")


def test_dice_button_changes_the_seed_and_the_result():
    at = _run()
    old_seed, old_l = at.session_state["seed_input"], _metric(at, "Lkw im System, Mittel (simuliert)")
    next(b for b in at.button if b.label == "🎲 Neuen Lauf würfeln").click().run()
    _ok(at)
    assert at.session_state["seed_input"] != old_seed
    assert _metric(at, "Lkw im System, Mittel (simuliert)") != old_l


def test_window_slider_exists_for_long_runs_and_changes_nothing_else():
    at = _run()
    sl = next(s for s in at.slider if s.key == "window_start_h")
    assert sl.min == 0 and sl.max > 100
    at.slider(key="window_start_h").set_value(sl.max).run()
    _ok(at)
    assert _metric(at, "Lkw im System, Mittel (simuliert)") == "7.73"


def test_speedup_slider_changes_the_capacity_verdict():
    at = _run()
    at.select_slider(key="speedup_pct").set_value(50).run()
    _ok(at)
    assert any("von **9.0 auf 1.5**" in s.value for s in at.success)


def test_permalink_values_are_clamped_and_snapped():
    at = AppTest.from_file(APP, default_timeout=300)
    at.query_params["rho"] = "9999"
    at.query_params["svc"] = "-5"
    at.query_params["n"] = "3000"
    at.run()
    _ok(at)
    assert at.session_state["rho_slider"] == C.RHO_PCT_MAX and at.session_state["service_slider"] == C.SERVICE_MIN_MIN
    assert at.session_state["n_customers_select"] == 2000


def test_permalink_ignores_garbage():
    at = AppTest.from_file(APP, default_timeout=300)
    at.query_params["rho"] = "viel"
    at.query_params["seed"] = "x"
    at.run()
    _ok(at)
    assert at.session_state["rho_slider"] == C.DEFAULT_RHO_PCT and at.session_state["seed_input"] == C.DEFAULT_SEED


def test_charts_and_experiments_are_present():
    at = _run()
    _ok(at)
    assert len(at.get("plotly_chart")) == 7
    headers = [s.value for s in at.subheader]
    assert any("Wie lange muss man simulieren" in h for h in headers)
    assert any("Feste statt exponentieller Abfertigungsdauer" in h for h in headers)
    assert any("Wo die Annahmen enden" in h for h in headers)


def test_fixed_service_experiment_shows_half_the_formula_wait():
    at = _run(rho_slider=50, n_customers_select=20000)
    _ok(at)
    assert _metric(at, "Wartezeit, Formel M/M/1") == "3.0 min"
    assert _metric(at, "Wartezeit, Formel feste Dauer") == "1.5 min"


def test_footer_is_present():
    at = _run()
    assert any("Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net)" in c.value
               for c in at.caption)


def test_related_demos_are_linked():
    at = _run()
    text = " ".join(c.value for c in at.caption)
    for name in ("ems-demo", "berth-allocation-demo", "truck-appointment-demo", "value-iteration-demo"):
        assert name in text


def test_every_limit_names_a_follow_up_piece():
    """Die Grenzen-Tabelle nennt zu jeder aufgehobenen Annahme das geplante Folgestück."""
    at = _run()
    table = next(m.value for m in at.markdown if "Wer setzt an" in m.value)
    for name in ("Pollaczek-Khinchine", "Erlang C", "Power-of-d", "Erlang B", "Splitting", "Erlang A", "Halfin-Whitt",
                 "zeitvariable Ankünfte", "Prioritätsklassen", "Jackson-Netze", "Simulationsanalyse"):
        assert name in table, name
    assert table.count("geplant") >= 8


def test_seed_control_uses_the_portfolio_wording():
    at = _run()
    assert [n.label for n in at.number_input] == ["Zufalls-Seed"]
