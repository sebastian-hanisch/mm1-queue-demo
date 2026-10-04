"""Geschlossene Formeln der M/M/1-Schlange (Poisson-Ankünfte, exponentielle Bedienzeit, ein Server, FIFO,
unbegrenzte Schlange). Einheiten: Raten je Minute, Zeiten in Minuten. Nur gültig für ρ = λ/μ < 1 (stationär)."""

import math


def utilisation(lam, mu):
    """ρ = λ/μ: Anteil der Zeit, in der der Server (statistisch) beschäftigt ist."""
    return lam / mu


def is_stable(lam, mu):
    """Eine stationäre Verteilung gibt es nur bei ρ < 1; bei ρ ≥ 1 wächst die Schlange ohne Grenze."""
    return lam < mu


def stationary_metrics(lam, mu):
    """Mittelwerte im stationären Zustand: Anzahl im System L, in der Schlange Lq, Verweilzeit W, Wartezeit Wq,
    Wahrscheinlichkeit zu warten (= ρ, PASTA). Verwendet Little's Gesetz L = λW nur zur Gegenprobe, nicht zur
    Herleitung: L und Wq folgen aus der geometrischen Verteilung (Gleichgewichtsgleichungen)."""
    if not is_stable(lam, mu):
        raise ValueError("ρ ≥ 1: keine stationäre Verteilung")
    rho = lam / mu
    L = rho / (1 - rho)
    Lq = rho * rho / (1 - rho)
    W = 1 / (mu - lam)
    Wq = rho / (mu - lam)
    return {"rho": rho, "L": L, "Lq": Lq, "W": W, "Wq": Wq, "p_wait": rho}


def p_n(lam, mu, n):
    """P(N = n) = (1 - ρ) ρ^n: geometrische Verteilung der Anzahl im System."""
    rho = lam / mu
    return (1 - rho) * rho ** n


def prob_wait_exceeds(lam, mu, t):
    """P(Wq > t) = ρ e^{-(μ-λ)t}: Anteil der Lkw, die länger als t Minuten in der Schlange stehen (t > 0)."""
    return (lam / mu) * math.exp(-(mu - lam) * t)


def md1_mean_wait(lam, mu):
    """Mittlere Wartezeit bei FESTER Bedienzeit 1/μ (M/D/1, Pollaczek-Khinchine mit Varianz 0): genau halb so
    groß wie bei exponentieller Bedienzeit. Nur als Gegenbeispiel zur M/M/1-Annahme gebraucht."""
    if not is_stable(lam, mu):
        raise ValueError("ρ ≥ 1: keine stationäre Verteilung")
    rho = lam / mu
    return rho / (2 * mu * (1 - rho))
