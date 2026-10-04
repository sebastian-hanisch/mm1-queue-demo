"""M/M/1 - ein Gate, ein Schalter - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Wurzel der Konzepte-Linie "Warteschlangentheorie und Simulation": Lkw kommen zufällig an einem Terminal-Gate mit
EINER Abfertigungsspur an (Poisson-Ankünfte, exponentielle Abfertigungsdauer, FIFO). Die Formeln der M/M/1-Schlange
stehen neben einer ereignisdiskreten Simulation - und die Demo zeigt, wo die Formel exakt ist, wo ein einzelner
Simulationslauf von ihr abweicht und warum. Siehe README für die Einordnung in die Linie.

Lauffähig mit: streamlit run app.py
"""

import streamlit as st

import mm1_constants as C
import mm1_formulas as F
from mm1_evaluation import (capacity_reserve, compare_services, little_check, load_precomputed, rates,
                            run_live, running_mean_in_system, state_distribution, typical_run_error,
                            wait_survival_curve, wait_tail_fractions, window_steps)
from mm1_presets import (apply_preset, bounds, init_session_state_defaults, load_permalink_settings,
                         randomize_seed, sync_query_params)
from mm1_visualization import (build_required_runs, build_rho_sweep, build_run_error, build_running_mean,
                               build_state_distribution, build_trajectory, build_wait_survival)

st.set_page_config(page_title="M/M/1-Warteschlange – Sebastian Hanisch", layout="wide")


@st.cache_data(show_spinner=False)
def _precomputed():
    return load_precomputed()


@st.cache_data(show_spinner=False)
def _run(rho_pct, service_min, n_customers, seed):
    return run_live(rho_pct, service_min, n_customers, seed)


@st.cache_data(show_spinner=False)
def _services(rho_pct, service_min, n_customers, seed):
    return compare_services(rho_pct, service_min, n_customers, seed)


def _min(x):
    return f"{x:.1f} min"


st.title("🚛 M/M/1: ein Gate, ein Schalter")
st.markdown(
    """
Ein **Terminal-Gate mit einer Abfertigungsspur**: Lkw treffen zufällig ein (**Poisson-Ankünfte**), jede Abfertigung
dauert zufällig lange (**exponentiell verteilt**), wer warten muss, stellt sich hinten an (FIFO). Das ist die
**M/M/1-Schlange**, das einfachste Modell der Warteschlangentheorie. Die Kernaussage passt in einen Satz: Die
Wartezeit wächst nicht linear mit der **Auslastung ρ**, sondern **explodiert, sobald ρ gegen 100 % geht**. Die
Formeln stehen hier neben einer **Simulation**, die Lkw für Lkw dasselbe Gate nachspielt. Weiter unten: wie stark
ein einzelner Simulationslauf von der Formel abweicht, wie lange man simulieren muss, und was passiert, wenn die
Abfertigungsdauer nicht exponentiell ist.
"""
)
st.caption(
    "Erstes Stück der Linie „Warteschlangentheorie und Simulation“: jedes Folgestück hebt genau EINE der Annahmen "
    "unter „Wo die Annahmen enden“ auf."
)

with st.expander("So funktioniert die M/M/1-Schlange", expanded=True):
    st.markdown(
        """
- **Zwei Zufallsgrößen:** die Zeit zwischen zwei Ankünften (Mittel 1/λ) und die Abfertigungsdauer (Mittel 1/μ), beide
  „gedächtnislos“: wie lange schon gewartet wurde, sagt nichts darüber, wann es weitergeht.
- **Auslastung** ρ = λ/μ: Anteil der Zeit, in der die Spur im Mittel belegt ist. Nur bei **ρ < 100 %** stellt sich ein
  Gleichgewicht ein; darüber wächst die Schlange ohne Grenze.
- **Gleichgewicht:** Auf lange Sicht stehen n Lkw im System mit Wahrscheinlichkeit (1−ρ)·ρⁿ. Daraus folgt im Mittel
  **L = ρ/(1−ρ)** Lkw im System und eine mittlere Wartezeit **Wq = ρ/(μ−λ)**.
- **Little's Gesetz** L = λ·W (Zahl im System = Ankunftsrate mal Verweilzeit) gilt nicht nur hier, sondern für jedes
  stabile System, auch ohne exponentielle Zeiten.
- **Simulation:** Ereignis für Ereignis (Ankunft, Abgang) vom leeren Gate aus. Sie braucht keine Formel, liefert aber nur
  einzelne, streuende Läufe.
        """
    )

st.caption("🎯 Schnellstart – ein Beispielszenario laden:")
preset_cols = st.columns(len(C.PRESET_ORDER))
for i, name in enumerate(C.PRESET_ORDER):
    with preset_cols[i]:
        st.button(name, key=f"preset_{name}", width="stretch", on_click=apply_preset, args=(name,),
                  help=C.PRESET_HELP[name])

st.caption(
    "🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, "
    "um ein Szenario zu teilen."
)

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    rho_pct = st.slider("Auslastung ρ des Gates", *bounds("rho_slider"), key="rho_slider", format="%d %%",
                        help="Anteil der Zeit, in dem die Spur im Mittel belegt ist (Ankunftsrate geteilt durch "
                             "Abfertigungsrate). Ab 100 % wächst die Schlange ohne Grenze.")
    service_min = st.slider("Mittlere Abfertigungsdauer (Minuten)", *bounds("service_slider"), key="service_slider",
                            help="Mittlere Dauer einer Abfertigung. Verschiebt nur die Zeitachse: Auslastung und "
                                 "alle Verhältnisse bleiben gleich.")
    n_customers = st.select_slider("Simulierte Lkw je Lauf", options=C.N_CUSTOMER_OPTIONS, key="n_customers_select",
                                   help="Länge des Simulationslaufs. Längere Läufe streuen weniger, brauchen "
                                        "aber mehr Rechenzeit.")
    seed = st.number_input("Zufalls-Seed", min_value=bounds("seed_input")[0], max_value=bounds("seed_input")[1],
                           step=1, key="seed_input", help="Bestimmt alle Zufallszahlen des Laufs.")
    st.button("🎲 Neuen Lauf würfeln", on_click=randomize_seed)

rho_pct, service_min, n_customers, seed = int(rho_pct), int(service_min), int(n_customers), int(seed)
sync_query_params({"rho_slider": rho_pct, "service_slider": service_min, "n_customers_select": n_customers,
                   "seed_input": seed})

lam, mu = rates(rho_pct, service_min)
stable = F.is_stable(lam, mu)
formula = F.stationary_metrics(lam, mu) if stable else None
pre = _precomputed()

with st.spinner("Simuliere das Gate …"):
    sim = _run(rho_pct, service_min, n_customers, seed)

st.markdown("---")
st.markdown("## 🚛 Das Gate in Zahlen")
st.caption(
    f"Ankunftsrate λ = {lam * 60:.1f} Lkw/h, Abfertigungsrate μ = {mu * 60:.1f} Lkw/h "
    f"(mittlere Abfertigung {service_min} min), {C.fmt_int(n_customers)} simulierte Lkw."
)

l_hat, lw_hat, little_gap = little_check(sim)
c1, c2, c3 = st.columns(3)
c1.metric("Auslastung ρ", f"{rho_pct} %")
c2.metric("Lkw im System, Mittel (Formel)", f"{formula['L']:.2f}" if stable else "gilt nicht (ρ ≥ 100 %)")
c3.metric("Lkw im System, Mittel (simuliert)", f"{l_hat:.2f}",
          delta=f"{(l_hat - formula['L']) / formula['L']:+.1%} gegen Formel" if stable else None, delta_color="off")
c4, c5, c6 = st.columns(3)
c4.metric("Wartezeit in der Schlange (Formel)", _min(formula["Wq"]) if stable else "gilt nicht (ρ ≥ 100 %)")
c5.metric("Wartezeit in der Schlange (simuliert)", _min(sim.mean_wait),
          delta=f"{(sim.mean_wait - formula['Wq']) / formula['Wq']:+.1%} gegen Formel" if stable else None,
          delta_color="off")
c6.metric("Little's Gesetz im Lauf: L gegen λ·W", "stimmt" if little_gap < 1e-6 else f"Abweichung {little_gap:.2%}",
          help=f"L = {l_hat:.4f} (Fläche unter der Kurve geteilt durch die Laufzeit), λ·W = {lw_hat:.4f} "
               "(Ankunftsrate mal mittlere Verweilzeit). Auf jedem Lauf gleich, weil das Gate am Ende leer ist.")

if stable:
    err = typical_run_error(pre, rho_pct, n_customers)
    if err is not None:
        rel_std, bias = err
        bias_text = (f"und unterschätzt sie im Mittel um {-bias:.0f} %, weil das Gate leer startet"
                     if bias < -3 else "ohne messbare Verzerrung durch den leeren Start")
        st.info(
            f"**Ein einzelner Lauf ist keine Messung der Formel.** Bei ρ = {rho_pct} % und {C.fmt_int(n_customers)} Lkw weicht die "
            f"simulierte Wartezeit typischerweise um etwa **±{100 * rel_std:.0f} %** von der Formel ab "
            f"(gemessen über {pre['grid_reps']} Läufe), {bias_text}. "
            "Mehr dazu unter „Wie lange muss man simulieren?“."
        )
else:
    peak = max(n for _, n in sim.trajectory)
    st.warning(
        f"**ρ ≥ 100 %: kein Gleichgewicht.** Es kommen im Mittel mehr Lkw an, als abgefertigt werden können; die "
        f"Schlange wächst, bis keine neuen Lkw mehr kommen (hier bis auf {peak} Lkw gleichzeitig im System). Die "
        "Formeln gelten nicht, und der simulierte Mittelwert hängt nur noch von der Lauflänge ab."
    )

st.markdown("### Die Schlange über der Zeit")
total_min = sim.end_time
window_min = C.WINDOW_HOURS * 60
max_start_h = int((total_min - window_min) // 60)
if max_start_h >= 1:
    start_h = st.slider("Fenster ab Stunde", 0, max_start_h, key="window_start_h", step=C.WINDOW_STEP_HOURS,
                        help=f"Zeigt {C.WINDOW_HOURS} Stunden des Laufs; 0 = vom leeren Gate aus.")
else:
    start_h = 0
start_min = start_h * 60
end_min = min(total_min, start_min + window_min)
col_a, col_b = st.columns(2)
with col_a:
    st.markdown("**Lkw im System, Stunde für Stunde**")
    st.plotly_chart(build_trajectory(window_steps(sim.trajectory, start_min, end_min), start_min, end_min,
                                     formula["L"] if stable else None),
                    width="stretch", key=f"traj_{rho_pct}_{service_min}_{n_customers}_{seed}_{start_h}")
with col_b:
    st.markdown("**Laufender Mittelwert über den ganzen Lauf**")
    st.plotly_chart(build_running_mean(running_mean_in_system(sim.trajectory), formula["L"] if stable else None),
                    width="stretch", key=f"run_{rho_pct}_{service_min}_{n_customers}_{seed}")
if stable:
    st.caption(
        "Links ein Ausschnitt: die Schlange schwankt stark, Rückstaus bauen sich langsam auf und lösen sich langsam wieder "
        "auf. Rechts der Mittelwert über den gesamten Lauf: er startet bei 0 (leeres Gate) und nähert sich dem Formelwert "
        "von unten, bei hoher Auslastung sehr langsam."
    )
else:
    st.caption(
        "Links ein Ausschnitt, rechts der Mittelwert über den gesamten Lauf: Bei Überlast nähert er sich keinem Wert, "
        "er steigt mit der Beobachtungszeit weiter, solange Lkw nachkommen."
    )

st.markdown("### Mittelwerte täuschen: die Verteilung")
col_c, col_d = st.columns(2)
shares, rest = state_distribution(sim)
with col_c:
    st.markdown("**Wie viele Lkw stehen gleichzeitig im System?**")
    st.plotly_chart(build_state_distribution(shares, rest, lam if stable else None, mu if stable else None),
                    width="stretch", key=f"dist_{rho_pct}_{service_min}_{n_customers}_{seed}")
    if rest > 0.0005:
        st.caption(f"Weitere {rest:.1%} der Zeit stehen mehr als {C.MAX_STATE_SHOWN} Lkw im System (nicht gezeigt).")
with col_d:
    st.markdown("**Wie viele Lkw warten länger als t Minuten?**")
    t_max = max(5.0, 8.0 * (formula["Wq"] if stable else service_min * 10))
    t_max = min(t_max, max(sim.waits)) if max(sim.waits) > 0 else t_max
    ts, surv = wait_survival_curve(sim, t_max)
    st.plotly_chart(build_wait_survival(ts, surv, lam if stable else None, mu if stable else None),
                    width="stretch", key=f"surv_{rho_pct}_{service_min}_{n_customers}_{seed}")
tails = wait_tail_fractions(sim)
tail_cols = st.columns(len(C.TAIL_MINUTES))
for col, minutes in zip(tail_cols, C.TAIL_MINUTES):
    col.metric(f"Anteil mit Wartezeit über {minutes} min", f"{tails[minutes]:.1%}",
               delta=f"Formel {F.prob_wait_exceeds(lam, mu, minutes):.1%}" if stable else None, delta_color="off",
               delta_arrow="off")
if stable:
    st.caption(
        f"Im Mittel wartet ein Lkw {formula['Wq']:.1f} min, aber **{formula['p_wait']:.0%} aller Lkw müssen überhaupt "
        "warten** (wer eine freie Spur vorfindet, wartet 0), und die Wartezeiten fallen nur exponentiell langsam ab: "
        "Einzelne Lkw warten ein Mehrfaches des Mittelwerts."
    )

st.markdown("---")
st.subheader("📐 Wie schnell explodiert die Schlange? Sweep über die Auslastung")
st.plotly_chart(build_rho_sweep(pre, rho_pct, 3), width="stretch", key="rho_sweep")
st.caption(
    f"Mittlere Wartezeit bei 3 min Abfertigungsdauer: Formel gegen simulierte Mittel aus {pre['grid_reps']} Läufen "
    f"je Auslastung (Lauflänge {C.fmt_int(max(C.N_CUSTOMER_OPTIONS))} Lkw, Fehlerbalken: 95 %-Intervall des Mittels, "
    "logarithmische Achse). Die Punkte folgen der Kurve; die Fehlerbalken werden nahe 100 % deutlich länger, weil die "
    "Läufe dort viel stärker streuen (siehe nächster Abschnitt)."
)

st.markdown("**Was bringt mehr Kapazität?**")
speedup = st.select_slider("Abfertigung schneller um", options=[5, 10, 20, 50], value=10, format_func=lambda v: f"{v} %",
                           key="speedup_pct")
l_before, l_after, rho_new = capacity_reserve(rho_pct, speedup)
if l_before is not None and l_after is not None:
    st.success(
        f"Bei ρ = {rho_pct} % senkt eine um {speedup} % schnellere Abfertigung die Auslastung auf {100 * rho_new:.1f} % "
        f"und die mittlere Zahl der Lkw im System von **{l_before:.1f} auf {l_after:.1f}** "
        f"({(l_after - l_before) / l_before:+.0%}). Nahe 100 % wirkt jedes bisschen Kapazität überproportional, bei "
        "niedriger Auslastung kaum."
    )
elif l_after is not None:
    st.success(
        f"Bei ρ = {rho_pct} % wächst die Schlange ohne Grenze. Eine um {speedup} % schnellere Abfertigung senkt die "
        f"Auslastung auf {100 * rho_new:.1f} %: dann stehen im Mittel {l_after:.1f} Lkw im System."
    )
else:
    st.warning(
        f"Auch mit {speedup} % schnellerer Abfertigung bleibt die Auslastung bei {100 * rho_new:.1f} % (≥ 100 %): die "
        "Schlange wächst weiter ohne Grenze."
    )

st.markdown("---")
st.subheader("🔬 Wie lange muss man simulieren?")
st.markdown(
    f"Jeder Lauf startet mit leerem Gate und streut um den Formelwert. Gemessen über {pre['grid_reps']} unabhängige "
    "Läufe je Zelle: links die Streuung eines einzelnen Laufs, rechts die mittlere Abweichung vom Formelwert "
    "(Startverzerrung)."
)
st.plotly_chart(build_run_error(pre), width="stretch", key="run_error")
st.markdown(f"**Wie viele Lkw braucht ein Lauf für ±1 % Genauigkeit (95 %)?** (Läufe à {C.fmt_int(pre['required_n'])} Lkw, "
            f"{pre['required_reps']} Wiederholungen)")
st.plotly_chart(build_required_runs(pre), width="stretch", key="required_runs")
req = {r["rho_pct"]: r for r in pre["required"]}
st.info(
    f"Bei ρ = 50 % genügen rund {req[50]['n_for_1pct'] / 1e6:.1f} Mio. Lkw, bei ρ = 90 % rund "
    f"{req[90]['n_for_1pct'] / 1e6:.0f} Mio., bei ρ = 99 % rund {req[99]['n_for_1pct'] / 1e9:.1f} Mrd. Für gleiche "
    f"Genauigkeit braucht ρ = 99 % also etwa das {round(req[99]['n_for_1pct'] / req[50]['n_for_1pct'], -2):.0f}-Fache an "
    "Lkw wie ρ = 50 %, und kurze Läufe unterschätzen die Schlange zusätzlich (Startverzerrung). Das Gate-Modell ist dabei das "
    "einfachste überhaupt - bei komplexeren Systemen gilt dasselbe, nur ohne Formel zum Gegenprüfen."
)

st.markdown("---")
st.subheader("🔬 Feste statt exponentieller Abfertigungsdauer")
st.markdown(
    "Dasselbe Gate, dieselben Ankünfte, dieselbe mittlere Abfertigungsdauer, aber jede Abfertigung dauert **genau** "
    "gleich lang statt zufällig. Little's Gesetz bleibt gültig - die M/M/1-Formel für die Wartezeit nicht mehr."
)
svc = _services(rho_pct, service_min, n_customers, seed)
if svc is None:
    st.info("Der Vergleich braucht ein Gleichgewicht (ρ < 100 %).")
else:
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Wartezeit, Formel M/M/1", _min(svc["mm1_formula_wq"]))
    s2.metric("Wartezeit, Formel feste Dauer", _min(svc["md1_formula_wq"]))
    s3.metric("Simulation, exponentiell", _min(svc["exp"]["wq"]))
    s4.metric("Simulation, fest", _min(svc["fest"]["wq"]))
    st.success(
        f"Little's Gesetz stimmt in beiden Läufen (Abweichung {svc['exp']['little_gap']:.1e} bzw. "
        f"{svc['fest']['little_gap']:.1e}). Die Wartezeit bei fester Dauer ist die **Hälfte** der M/M/1-Wartezeit "
        f"(Formel: {_min(svc['md1_formula_wq'])} statt {_min(svc['mm1_formula_wq'])}); der Einzellauf zeigt "
        f"{_min(svc['fest']['wq'])} gegen {_min(svc['exp']['wq'])}. Nicht der Mittelwert der Abfertigungsdauer entscheidet "
        "über die Schlange, sondern auch ihre **Streuung**."
    )

st.markdown("---")
st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was passiert, wenn sie verletzt ist | Wer setzt an |
|---|---|---|
| **Abfertigungsdauer exponentiell** | Die Wartezeit hängt von der Streuung der Dauer ab: bei fester Dauer nur halb so groß (Experiment oben). | **[M/G/1 (Pollaczek-Khinchine), Kingman-Näherung G/G/1](https://sebastianhanisch-mg1-kingman-demo.streamlit.app/)** |
| **Ein Server** | Reale Gates haben mehrere Spuren; „eine gemeinsame Schlange oder je Spur eine“ ist eine eigene Frage, und wo Kunden die Spur selbst wählen, entscheidet die Wahlregel. | **[M/M/c (Erlang C)](https://sebastianhanisch-mmc-queue-demo.streamlit.app/)** und **[Power-of-d-Choices](https://sebastianhanisch-power-of-d-demo.streamlit.app/)**; mehrere Server mit Markov-Kette: `ems_demo` |
| **Unbegrenzte Schlange** | Stellplätze sind knapp: wer bei voller Zufahrt ankommt, geht verloren. Die Verlustwahrscheinlichkeit ist oft winzig und damit nur mit Tricks simulierbar. | **[M/M/c/c (Erlang B)](https://sebastianhanisch-erlang-b-demo.streamlit.app/)** und **[seltene Ereignisse (Splitting)](https://sebastianhanisch-splitting-demo.streamlit.app/)** |
| **Unendliche Geduld** | Niemand dreht um. Mit Abwanderung bleibt auch bei Überlast ein Gleichgewicht. | **[Erlang A](https://sebastianhanisch-erlang-a-demo.streamlit.app/)** |
| **Konstante Ankunftsrate** | Echte Gates haben Morgenspitzen; die Gleichgewichtsformeln mit dem Tagesmittel unterschätzen die Spitze. | **[Wurzel-Personalregel (Halfin-Whitt)](https://sebastianhanisch-square-root-staffing-demo.streamlit.app/)**, **[zeitvariable Ankünfte](https://sebastianhanisch-time-varying-arrivals-demo.streamlit.app/)** |
| **Alle Lkw gleich wichtig** | Eilige Lkw brauchen Vorfahrt; das verschiebt die Wartezeit zwischen den Klassen. | **[Prioritätsklassen](https://sebastianhanisch-priority-queue-demo.streamlit.app/)** |
| **Ein einziger Halt** | Kein Weg durch mehrere Stationen (Gate, Kran, Stapel), bei denen Engpässe wandern. | **[Jackson-Netze](https://sebastianhanisch-jackson-network-demo.streamlit.app/)** |
| **Ein fester Simulationslauf ohne Intervalle** | Ein Lauf ist eine Stichprobe: die Live-Ansicht zeigt keine Konfidenzintervalle, kein Abschneiden des Einschwingens. | **[Simulationsanalyse (Warm-up, Konfidenzintervalle)](https://sebastianhanisch-output-analysis-demo.streamlit.app/)** |
"""
)
st.caption(
    "Verwandt im Portfolio: [markov-queue-demo](https://sebastianhanisch-markov-queue-demo.streamlit.app/) (Zusatzstück: Zustandsdiagramm, Generator und die drei Wege zum Gleichgewicht hinter den Formeln), die Rettungsdienst-Demo "
    "[ems-demo](https://sebastianhanisch-ems-demo.streamlit.app/) rechnet mit einer Markov-Kette über mehrere "
    "Server (Hypercube Queueing Model) und prüft sich an der Erlang-B-Formel; die Hafen-Fall-Demos "
    "[berth-allocation-demo](https://sebastianhanisch-berth-allocation-demo.streamlit.app/) und "
    "[truck-appointment-demo](https://sebastianhanisch-truck-appointment-demo.streamlit.app/) planen "
    "Terminals dagegen deterministisch, ohne Zufall im Modell; Markov-Ketten mit Entscheidungen behandelt "
    "[value-iteration-demo](https://sebastianhanisch-value-iteration-demo.streamlit.app/)."
)
st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Modell** (Kendall-Notation M/M/1): Ankünfte bilden einen Poisson-Prozess mit Rate $\lambda$, Abfertigungsdauern sind
unabhängig exponentiell mit Rate $\mu$, ein Server, FIFO, unbegrenzte Schlange. $N(t)$, die Zahl der Lkw im System, ist
eine Geburts-Sterbe-Kette mit Geburtsrate $\lambda$ und Sterberate $\mu$ (für $N \ge 1$).

**Gleichgewicht.** Mit $\rho = \lambda/\mu < 1$ gilt für die stationäre Verteilung $\pi_n$ das Schnittgleichgewicht
$\lambda\,\pi_n = \mu\,\pi_{n+1}$, also $\pi_n = (1-\rho)\rho^n$. Daraus
$$L = \sum_n n\,\pi_n = \frac{\rho}{1-\rho},\qquad L_q = \sum_{n \ge 1}(n-1)\,\pi_n = \frac{\rho^2}{1-\rho}.$$
Wartezeit und Verweilzeit folgen aus **Little's Gesetz** $L = \lambda W$ und $L_q = \lambda W_q$:
$$W = \frac{1}{\mu-\lambda},\qquad W_q = \frac{\rho}{\mu-\lambda}.$$
Ein ankommender Lkw findet das System (nach PASTA, Poisson-Ankünfte sehen Zeitmittelwerte) mit Wahrscheinlichkeit $\rho$
belegt, daher $P(W_q > 0) = \rho$; die Wartezeit hat den Rest exponentiell: $P(W_q > t) = \rho\,e^{-(\mu-\lambda)t}$.

**Little's Gesetz auf einem Pfad.** Endet das System leer, trägt jeder Kunde genau seine Verweilzeit zur Fläche unter
$N(t)$ bei: $\int_0^T N(t)\,dt = \sum_k S_k$. Dividiert man durch $T$, steht links $\bar L$ und rechts $\hat\lambda\,\hat W$.

**Feste Abfertigungsdauer** ($1/\mu$ ohne Streuung, M/D/1): die Pollaczek-Khinchine-Formel
$W_q = \dfrac{\lambda\,E[S^2]}{2(1-\rho)}$ gibt mit $E[S^2] = 1/\mu^2$ den Wert $\dfrac{\rho}{2\mu(1-\rho)}$, genau die Hälfte von
M/M/1 (dort $E[S^2] = 2/\mu^2$).

**Simulation.** Ereignisliste mit Ankünften und Abgängen; Ankunftsabstände und Abfertigungsdauern aus einem
Ganzzahl-Zufallsgenerator (SplitMix64) per Inversion $-\ln(1-u)/\text{Rate}$. Zur Gegenprobe berechnet die
**Lindley-Rekursion** $W_{k+1} = \max(0,\,W_k + S_k - A_{k+1})$ aus denselben Zufallszahlen Kunde für Kunde dieselben
Wartezeiten ohne Ereignisliste.

Implementiert in `mm1_formulas.py` (Formeln), `mm1_simulation.py` (Ereignissimulation, Lindley-Rekursion, Generator),
`mm1_evaluation.py` (Kennzahlen, Verteilungen, Messreihen-Funktionen), `generate_precomputed.py` (vorgerechnete
Messreihen).
        """
    )

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zur Reihe: [Warteschlangentheorie: M/M/1 bis Surrogat](https://sebastianhanisch.net/konzepte-warteschlangentheorie.html)."
)
