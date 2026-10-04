"""Plotly-Abbildungen der M/M/1-Demo: Treppenkurve, laufender Mittelwert, Verteilung der Anzahl im System,
Wartezeit-Überschreitung, Auslastungs-Sweep, Streuung/Startverzerrung, benötigte Lauflänge.
Achsen sind gesperrt (fixedrange), damit Touch-Geräte beim Scrollen nicht zoomen."""

import math

import plotly.graph_objects as go

import mm1_constants as C
import mm1_formulas as F

SIM_COLOR = "#4c78a8"
FORMULA_COLOR = "#f58518"
GOOD_COLOR = "#54a24b"
BAD_COLOR = "#e45756"


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height, legend_y=-0.25):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=legend_y),
                      plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def build_trajectory(steps, start_min, end_min, formula_l=None):
    """Treppenkurve N(t) im Fenster (Minuten); gestrichelt der Formelwert L, falls es ihn gibt."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[t / 60 for t, _ in steps], y=[n for _, n in steps], mode="lines", line_shape="hv",
                             line=dict(color=SIM_COLOR, width=2), name="Lkw im System (simuliert)",
                             hovertemplate="%{x:.2f} h: %{y} Lkw<extra></extra>"))
    if formula_l is not None:
        fig.add_trace(go.Scatter(x=[start_min / 60, end_min / 60], y=[formula_l, formula_l], mode="lines",
                                 line=dict(color=FORMULA_COLOR, width=2, dash="dash"), name=f"Formel L = {formula_l:.1f}"))
    fig.update_xaxes(title_text="Zeit seit Start (Stunden)", range=[start_min / 60, end_min / 60])
    fig.update_yaxes(title_text="Lkw im System", rangemode="tozero")
    return _base(fig, 300)


def build_running_mean(series, formula_l=None):
    """Zeitlicher Mittelwert von N(t) von Beginn bis t: nähert sich (bei ρ < 1) langsam dem Formelwert."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[t / 60 for t, _ in series], y=[m for _, m in series], mode="lines",
                             line=dict(color=SIM_COLOR, width=2.5), name="Mittel bis t (simuliert)"))
    if formula_l is not None and series:
        fig.add_trace(go.Scatter(x=[series[0][0] / 60, series[-1][0] / 60], y=[formula_l, formula_l], mode="lines",
                                 line=dict(color=FORMULA_COLOR, width=2, dash="dash"), name=f"Formel L = {formula_l:.1f}"))
    fig.update_xaxes(title_text="Beobachtungszeit (Stunden)")
    fig.update_yaxes(title_text="Mittlere Zahl Lkw im System", rangemode="tozero")
    return _base(fig, 300)


def build_state_distribution(shares, rest, lam=None, mu=None):
    """Balken: Zeitanteil mit genau n Lkw im System; Punkte: geometrische Formel (1−ρ)ρⁿ."""
    ns = list(range(len(shares)))
    fig = go.Figure()
    fig.add_trace(go.Bar(x=ns, y=shares, marker_color=SIM_COLOR, name="simuliert (Zeitanteil)",
                         hovertemplate="n = %{x}: %{y:.1%}<extra></extra>"))
    if lam is not None:
        fig.add_trace(go.Scatter(x=ns, y=[F.p_n(lam, mu, n) for n in ns], mode="markers",
                                 marker=dict(color=FORMULA_COLOR, size=7, symbol="diamond"), name="Formel (1−ρ)ρⁿ"))
    fig.update_xaxes(title_text="Zahl der Lkw im System n")
    fig.update_yaxes(title_text="Anteil der Zeit", tickformat=".0%")
    return _base(fig, 300)


def build_wait_survival(ts, sim_surv, lam=None, mu=None):
    """Anteil der Lkw mit Wartezeit über t (logarithmische Achse; Nullwerte werden ausgelassen)."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ts, y=[v if v > 0 else None for v in sim_surv], mode="lines",
                             line=dict(color=SIM_COLOR, width=2.5), name="simuliert"))
    if lam is not None:
        fig.add_trace(go.Scatter(x=ts, y=[F.prob_wait_exceeds(lam, mu, t) for t in ts], mode="lines",
                                 line=dict(color=FORMULA_COLOR, width=2, dash="dash"), name="Formel ρ·e^(−(μ−λ)t)"))
    fig.update_xaxes(title_text="Wartezeit t (Minuten)")
    fig.update_yaxes(title_text="Anteil der Lkw mit Wartezeit > t", type="log", tickformat=".1%")
    return _base(fig, 300)


def build_rho_sweep(precomputed, current_rho_pct, service_min=3):
    """Mittlere Wartezeit Wq über der Auslastung: Formel (Linie) gegen simulierte Mittel (Punkte, Fehlerbalken:
    95 %-Intervall des Mittels über die Wiederholungen); die senkrechte Linie markiert die gewählte Auslastung."""
    mu = 1.0 / service_min
    xs = list(range(5, 99))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xs, y=[F.stationary_metrics(x / 100 * mu, mu)["Wq"] for x in xs], mode="lines",
                             line=dict(color=FORMULA_COLOR, width=2.5), name="Formel Wq = ρ/(μ−λ)"))
    n_max = max(r["n"] for r in precomputed["grid"])
    pts = [r for r in precomputed["grid"] if r["n"] == n_max]
    reps = precomputed["grid_reps"]
    fig.add_trace(go.Scatter(
        x=[r["rho_pct"] for r in pts], y=[r["mean_wq"] for r in pts], mode="markers",
        marker=dict(color=SIM_COLOR, size=8),
        error_y=dict(type="data", array=[1.96 * r["rel_std"] * r["mean_wq"] / math.sqrt(reps) for r in pts], visible=True),
        name=f"simuliert (Mittel aus {reps} Läufen à {C.fmt_int(n_max)} Lkw)",
        hovertemplate="ρ = %{x} %: %{y:.1f} min<extra></extra>"))
    if current_rho_pct < 99:
        fig.add_vline(x=current_rho_pct, line=dict(color="#888", width=1, dash="dot"))
    fig.update_xaxes(title_text="Auslastung ρ (%)", range=[0, 100])
    ticks = [1, 2, 5, 10, 20, 50, 100, 200]
    fig.update_yaxes(title_text="Mittlere Wartezeit (Minuten, log)", type="log", tickmode="array", tickvals=ticks,
                     ticktext=[str(t) for t in ticks])
    return _base(fig, 360)


def build_run_error(precomputed):
    """Zwei Bilder nebeneinander in einer Figur: Streuung eines Laufs (relative Standardabweichung) und
    Startverzerrung (mittlere Abweichung vom Formelwert) über der Lauflänge, je Auslastung eine Linie."""
    from plotly.subplots import make_subplots

    grid = precomputed["grid"]
    chosen = (50, 80, 90, 95, 97)
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Streuung eines Laufs", "Startverzerrung (Mittel vieler Läufe)"),
                        horizontal_spacing=0.12)
    palette = ["#54a24b", "#4c78a8", "#f58518", "#e45756", "#7f3c8d"]
    for color, rho in zip(palette, chosen):
        rows = sorted((r for r in grid if r["rho_pct"] == rho), key=lambda r: r["n"])
        ns = [r["n"] for r in rows]
        fig.add_trace(go.Scatter(x=ns, y=[100 * r["rel_std"] for r in rows], mode="lines+markers",
                                 line=dict(color=color, width=2), name=f"ρ = {rho} %", legendgroup=str(rho)), row=1, col=1)
        fig.add_trace(go.Scatter(x=ns, y=[r["bias_pct"] for r in rows], mode="lines+markers",
                                 line=dict(color=color, width=2), name=f"ρ = {rho} %", legendgroup=str(rho),
                                 showlegend=False), row=1, col=2)
    n_ticks = [1000, 2000, 5000, 10000, 20000, 50000]
    for col in (1, 2):
        fig.update_xaxes(title_text="Lkw je Lauf (log)", type="log", tickmode="array", tickvals=n_ticks,
                         ticktext=["1k", "2k", "5k", "10k", "20k", "50k"], row=1, col=col)
    s_ticks = [2, 5, 10, 20, 50, 100]
    fig.update_yaxes(title_text="Abweichung 1σ (%)", type="log", tickmode="array", tickvals=s_ticks,
                     ticktext=[str(t) for t in s_ticks], row=1, col=1)
    fig.update_yaxes(title_text="Abweichung von der Formel (%)", row=1, col=2)
    _base(fig, 400, legend_y=-0.28)
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
    return fig


def build_required_runs(precomputed):
    """Lkw je Lauf für ±1 % Genauigkeit (95 %) bei den gemessenen Auslastungen."""
    rows = precomputed["required"]
    fig = go.Figure(go.Bar(x=[f"ρ = {r['rho_pct']} %" for r in rows], y=[r["n_for_1pct"] for r in rows],
                           marker_color=[GOOD_COLOR, SIM_COLOR, FORMULA_COLOR, BAD_COLOR, "#7f3c8d"][:len(rows)],
                           text=[_short(r["n_for_1pct"]) for r in rows], textposition="outside",
                           hovertemplate="%{x}: %{y:,.0f} Lkw<extra></extra>"))
    ticks = [1e5, 1e6, 1e7, 1e8, 1e9, 1e10]
    fig.update_yaxes(title_text="Lkw je Lauf für ±1 % (log)", type="log", range=[5, 10.5], tickmode="array",
                     tickvals=ticks, ticktext=["100 Tsd.", "1 Mio.", "10 Mio.", "100 Mio.", "1 Mrd.", "10 Mrd."])
    return _base(fig, 320)


def _short(n):
    if n >= 1e9:
        return f"{n / 1e9:.1f} Mrd."
    if n >= 1e6:
        return f"{n / 1e6:.1f} Mio."
    return f"{n / 1e3:.0f} Tsd."
