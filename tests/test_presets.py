"""Presets: Vollständigkeit, gültige Werte, Permalink-Konstanten."""

import pytest

import mm1_constants as C
import mm1_presets as P


def test_every_preset_has_help_and_all_keys():
    assert set(C.PRESETS) == set(C.PRESET_HELP) == set(C.PRESET_ORDER) and len(C.PRESETS) == 4
    for name, preset in C.PRESETS.items():
        assert set(preset) == set(P.PRESET_KEYS) and C.PRESET_HELP[name]


def test_preset_values_are_valid_and_match_the_setting_specs():
    for preset in C.PRESETS.values():
        assert C.RHO_PCT_MIN <= preset["rho_pct"] <= C.RHO_PCT_MAX
        assert C.SERVICE_MIN_MIN <= preset["service_min"] <= C.SERVICE_MIN_MAX
        assert preset["n_customers"] in C.N_CUSTOMER_OPTIONS
        for key, state_key in P.PRESET_KEYS.items():
            P.SETTING_SPECS[state_key].caster(preset[key])


def test_preset_names_state_the_utilisation_they_set():
    for name, preset in C.PRESETS.items():
        assert f"{preset['rho_pct']} %" in name


def test_default_preset_equals_the_default_settings():
    p = C.PRESETS["Normalfall (ρ = 90 %)"]
    assert (p["rho_pct"], p["service_min"], p["n_customers"], p["seed"]) == (
        C.DEFAULT_RHO_PCT, C.DEFAULT_SERVICE_MIN, C.DEFAULT_N_CUSTOMERS, C.DEFAULT_SEED)


def test_one_preset_is_the_overload_case_and_one_is_beyond_the_measured_range():
    assert any(p["rho_pct"] >= 100 for p in C.PRESETS.values())
    assert max(r for r in C.SWEEP_RHO_PCT) < 100


def test_bounds_and_url_params():
    assert P.bounds("rho_slider") == (C.RHO_PCT_MIN, C.RHO_PCT_MAX) and P.bounds("seed_input") == (0, C.SEED_MAX)
    assert len({spec.url_param for spec in P.SETTING_SPECS.values()}) == len(P.SETTING_SPECS)


@pytest.mark.parametrize("value,expected", [(1000, 1000), (1400, 1000), (3000, 2000), (3600, 5000), (3500, 2000), (999999, 50000), (1, 1000)])
def test_n_customers_snaps_to_the_nearest_option(value, expected):
    assert P.snap_n_customers(value) == expected


def test_fmt_int_uses_dots_as_thousands_separator():
    assert C.fmt_int(10000) == "10.000" and C.fmt_int(950) == "950" and C.fmt_int(1000000) == "1.000.000"
