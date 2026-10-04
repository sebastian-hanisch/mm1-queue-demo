"""Konstanten der M/M/1-Demo: Regler, Voreinstellungen, Messreihen-Parameter. Zeiten in Minuten."""

def fmt_int(n):
    """Ganzzahl mit Punkt als Tausendertrenner (10000 -> 10.000)."""
    return f"{n:,}".replace(",", ".")


RHO_PCT_MIN, RHO_PCT_MAX, DEFAULT_RHO_PCT = 10, 110, 90          # Auslastung ρ = λ/μ in Prozent
SERVICE_MIN_MIN, SERVICE_MIN_MAX, DEFAULT_SERVICE_MIN = 1, 6, 3  # mittlere Abfertigungsdauer je Lkw in Minuten
N_CUSTOMER_OPTIONS = (1000, 2000, 5000, 10000, 20000, 50000)
DEFAULT_N_CUSTOMERS = 10000
SEED_MAX = 999999
DEFAULT_SEED = 35

WINDOW_HOURS = 4                  # Fensterbreite der Treppenkurve N(t)
WINDOW_STEP_HOURS = 1
TAIL_MINUTES = (5, 15, 30, 60)    # Schwellen für "Anteil der Lkw mit Wartezeit über ..."
MAX_STATE_SHOWN = 40              # Balken der Verteilung der Anzahl im System (darüber zusammengefasst)

# Messreihen (vorgerechnet in `precomputed_sweep.json`, siehe generate_precomputed.py)
SWEEP_RHO_PCT = (10, 20, 30, 40, 50, 60, 70, 80, 85, 90, 93, 95, 97)
MU_PER_MIN_SWEEP = 1 / 3          # 3 Minuten Bedienzeit, wie die Voreinstellung

PRESET_ORDER = ("Normalfall (ρ = 90 %)", "Entspannt (ρ = 50 %)", "Fast voll (ρ = 97 %)", "Überlast (ρ = 105 %)")


def _preset(rho_pct=DEFAULT_RHO_PCT, service_min=DEFAULT_SERVICE_MIN, n_customers=DEFAULT_N_CUSTOMERS):
    return {"rho_pct": rho_pct, "service_min": service_min, "n_customers": n_customers, "seed": DEFAULT_SEED}


PRESETS = {
    "Normalfall (ρ = 90 %)": _preset(),
    "Entspannt (ρ = 50 %)": _preset(rho_pct=50),
    "Fast voll (ρ = 97 %)": _preset(rho_pct=97, n_customers=50000),
    "Überlast (ρ = 105 %)": _preset(rho_pct=105),
}
# Formelwerte bei 3 min Abfertigung (exakt, tests/test_claims.py rechnet sie nach); Streuung eines Laufs aus der
# vorgerechneten Messreihe (relative Standardabweichung der Wartezeit bei 10 000 Lkw, 200 Läufe)
PRESET_HELP = {
    "Normalfall (ρ = 90 %)": "ρ = 90 %: Die Formel sagt 9 Lkw im System und 27 min mittlere Wartezeit bei 3 min Abfertigung. Ein einzelner Lauf mit 10 000 Lkw streut dabei um etwa ±18 %.",
    "Entspannt (ρ = 50 %)": "ρ = 50 %: im Mittel 1 Lkw im System und 3 min Wartezeit - das Gate hat Luft, ein Lauf mit 10 000 Lkw trifft die Formel auf wenige Prozent genau.",
    "Fast voll (ρ = 97 %)": "ρ = 97 %: die Formel sagt etwa 32 Lkw im System und 97 min Wartezeit - schon 3 Prozentpunkte unter der Grenze. Der Lauf ist auf 50 000 Lkw verlängert und streut trotzdem noch um etwa ±30 %.",
    "Überlast (ρ = 105 %)": "ρ = 105 %: mehr Lkw als abgefertigt werden können - kein Gleichgewicht, die Schlange wächst, die Formeln gelten nicht mehr.",
}
