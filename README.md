# M/M/1 – ein Gate, ein Schalter (Streamlit-Demo)

**[→ Demo live ausprobieren](https://sebastianhanisch-mm1-queue-demo.streamlit.app/)**

Interaktive Demo zur **M/M/1-Schlange**, dem einfachsten Modell der Warteschlangentheorie, am Beispiel eines
Terminal-Gates mit einer Abfertigungsspur. **Wurzel der Konzepte-Linie „Warteschlangentheorie und Simulation“** im
Portfolio von [Sebastian Hanisch](https://sebastianhanisch.net) (Operations Research und Machine Learning): ein Verfahren,
ein wachsendes Beispiel, jedes Folgestück hebt genau eine Annahme dieser Wurzel auf.

Lkw kommen zufällig an (Poisson-Ankünfte), jede Abfertigung dauert zufällig lange (exponentiell), wer warten muss, stellt
sich hinten an (FIFO). Die Formeln des Gleichgewichts stehen neben einer ereignisdiskreten Simulation, die Lkw für Lkw
dasselbe Gate nachspielt.

## Kernfrage

Wie hängt die Wartezeit von der Auslastung ρ = λ/μ ab, und wie verlässlich ist eine Simulation gegenüber der Formel?
Die Formel ist exakt, ein einzelner Simulationslauf dagegen nur eine streuende Stichprobe, und wie stark er streut,
hängt selbst an ρ.

## Modell

- Ankünfte: Poisson-Prozess mit Rate λ. Abfertigungsdauer: exponentiell mit Mittel 1/μ. Ein Server, FIFO, unbegrenzte
  Schlange (Kendall-Notation M/M/1).
- Gleichgewicht nur bei ρ < 100 %: P(n im System) = (1−ρ)ρⁿ, L = ρ/(1−ρ), Wq = ρ/(μ−λ), P(Wq > t) = ρ·e^(−(μ−λ)t).
- Little's Gesetz L = λ·W gilt allgemein; auf einem simulierten Pfad, der leer endet, sogar als exakte Identität.
- Regler: Auslastung (10–110 %), mittlere Abfertigungsdauer (1–6 min, verschiebt nur die Zeitachse), Lauflänge
  (1 000–50 000 Lkw), Zufalls-Seed. Voreinstellung: 90 %, 3 min (18 Lkw/h kommen an, 20 Lkw/h werden abgefertigt), 10 000 Lkw.
- Ab ρ ≥ 100 % gibt es kein Gleichgewicht; die App zeigt das offen (keine Formelwerte, Warnung) und lässt die
  Simulation weiterlaufen, damit man die wachsende Schlange sieht.

Details und Herleitung im 📐-Expander der App.

## Methodik

- **Ereignissimulation** (`mm1_simulation.py`): Ereignisliste mit Ankünften und Abgängen, je Ereignistyp ein Handler,
  Start mit leerem Gate. Zufall aus einem Ganzzahl-Generator (SplitMix64) statt numpy: numpy garantiert keine über
  Versionen stabilen Zufallsströme, die CI installiert aber wöchentlich die neueste Version.
- **Lindley-Rekursion** als zweite, unabhängige Rechnung derselben Wartezeiten (ohne Ereignisliste, aus denselben
  Zufallszahlen in derselben Reihenfolge). Beide stimmen Kunde für Kunde überein; die vorgerechneten Messreihen nutzen
  die schnellere Lindley-Rekursion.
- **Unabhängige Referenz für die Formeln:** das lineare Gleichungssystem der abgeschnittenen Geburts-Sterbe-Kette
  (`tests/test_formulas.py`), ohne die geschlossenen Formeln zu benutzen.
- **Vorgerechnete Messreihen** (`generate_precomputed.py` → `precomputed_sweep.json`, rund drei Minuten): Auslastung ×
  Lauflänge je 200 unabhängige Läufe (Streuung und Startverzerrung), dazu die Lauflänge für ±1 % Genauigkeit. Nur der
  gewählte Einzellauf wird live gerechnet.

## Befunde (gemessen, keine Behauptungen)

Alle Zahlen stehen in `tests/test_claims.py`; Zeiten bei 3 min mittlerer Abfertigung.

| Frage | Befund |
|---|---|
| Was sagt die Formel? | ρ = 50 %: im Mittel 1 Lkw im System, 3 min Wartezeit. ρ = 90 %: **9 Lkw, 27 min**. ρ = 97 %: **32.3 Lkw, 97 min**. |
| Was bringt mehr Kapazität? | Bei ρ = 90 % senkt eine um 10 % schnellere Abfertigung (ρ → 81.8 %) die Schlange von 9.0 auf **4.5** Lkw (−50 %). |
| Gilt Little's Gesetz im Lauf? | **Exakt** auf jedem simulierten Pfad, auch bei Überlast (Fläche unter N(t) = Summe der Verweilzeiten). |
| Stimmen Ereignissimulation und Lindley-Rekursion überein? | Ja, Kunde für Kunde (Abweichung < 10⁻⁶ min). |
| Wie weit liegt ein Einzellauf von der Formel? | Standardfall (Seed 35, 10 000 Lkw): **7.73 statt 9.00** Lkw (−14 %), Wartezeit 23.0 statt 27.0 min (−15 %). Das ist typisch, kein Ausreißer (nächste Zeile). |
| Wie stark streut ein Lauf? | Relative Standardabweichung der Wartezeit bei 10 000 Lkw: ρ = 50 % **±5 %**, ρ = 90 % **±18 %**, ρ = 97 % **±51 %**. Mit 50 000 Lkw: ρ = 90 % ±10 %, ρ = 97 % ±30 %. |
| Unterschätzt der leere Start die Schlange? | Bei ρ = 97 % ja: im Mittel **−47 %** bei 1 000 Lkw, −11 % bei 10 000, bei 50 000 nicht mehr vom Rauschen zu trennen. Bei ρ = 50 % liegt sie in jeder Lauflänge unter 5 %. |
| Wie lang muss ein Lauf sein (±1 %, 95 %)? | Rund **0.6 Mio.** Lkw bei ρ = 50 %, 6 Mio. bei 80 %, **20 Mio.** bei 90 %, 70 Mio. bei 95 %, **1.1 Mrd.** bei 99 % (Messunsicherheit rund ±20 %). Zwischen 50 % und 99 % liegt etwa das 1 700-Fache. |
| Folgen die simulierten Mittel der Formelkurve? | Ja: 200 Läufe à 50 000 Lkw je Auslastung liegen innerhalb von vier Standardfehlern (plus 2 % Startverzerrung) an der Formel; die Fehlerbalken wachsen nahe 100 % stark. |
| Feste statt exponentielle Abfertigung? | Wartezeit **genau halb so groß** (Formel); simuliert bei ρ = 50 %: 1.50 gegen 3.01 min (fünf Seeds à 100 000 Lkw). Little's Gesetz gilt in beiden Fällen. |

## Befunde und Korrekturen gegenüber dem Plan

- **Eine Aussage aus dem ersten App-Entwurf war falsch** und ist korrigiert: „Nahe 100 % liegen die simulierten Punkte
  unter der Kurve.“ Bei 50 000 Lkw je Lauf und 200 Läufen sind sie von der Formel nicht zu trennen (−1.6 % bei ρ = 97 %,
  Standardfehler etwa 2 %); die Startverzerrung zeigt sich erst bei kürzeren Läufen.
- **Referenz statt `simpy`:** Der Plan sah `simpy` als Kreuzprüfung vor. Stattdessen dient die exakte
  Geburts-Sterbe-Kette als unabhängige Referenz (nur numpy, kein zusätzliches Paket).
- **Zufallsgenerator:** SplitMix64 (Portfolio-Konvention) statt `random.Random`.
- **„Einschwingzeit“ als eigene Messung entfällt** in diesem Stück: Die Startverzerrung nach Lauflänge liefert dieselbe
  Aussage und führt direkt zum Folgestück über Simulation.

## Ehrliche Grenzen

- Die Lauflängen für ±1 % beruhen auf der Annahme, dass die Varianz des Schätzers mit 1/N fällt, gemessen bei
  1 Mio. Lkw und 60 Läufen (Unsicherheit der Zahl rund ±20 %, 1σ). Bei ρ = 99 % ist selbst diese Lauflänge noch mit −3.7 %
  Startverzerrung behaftet; die 1.1 Mrd. sind dort eine grobe Abschätzung.
- Die Startverzerrungen in der Tabelle sind Mittel über 200 Läufe und selbst verrauscht (bei ±50 % Streuung eines
  Laufs auf wenige Prozentpunkte genau).
- Die Messreihen gelten für beliebige mittlere Abfertigungsdauern, weil eine Skalierung der Zeitachse alle Verhältnisse
  unverändert lässt; gemessen wurde bei 3 min.
- Die Live-Ansicht rechnet **einen** Lauf; Konfidenzintervalle aus Wiederholungen und das Abschneiden der Einschwingphase
  gibt es nur in den vorgerechneten Messreihen.
- Die Auslastungen der Messreihe enden bei 97 %; für 98–99 % zeigt die App die typische Streuung nicht an.

## Bewusst nicht umgesetzt

Jede dieser Annahmen hebt ein Folgestück der Linie auf:

| Annahme | Folgestück |
|---|---|
| Abfertigungsdauer exponentiell | M/G/1 (Pollaczek-Khinchine), Kingman-Näherung G/G/1 |
| Ein Server | M/M/c (Erlang C), Power-of-d-Choices; mehrere Server mit Markov-Kette bereits in `ems_demo` |
| Unbegrenzte Schlange | M/M/c/c (Erlang B), seltene Ereignisse (Splitting) |
| Unendliche Geduld | Erlang A |
| Konstante Ankunftsrate | Wurzel-Personalregel (Halfin-Whitt), zeitvariable Ankünfte |
| Alle Lkw gleich wichtig | Prioritätsklassen |
| Ein einziger Halt | Jackson-Netze |
| Ein fester Simulationslauf ohne Intervalle | [Simulationsanalyse (Warm-up, Konfidenzintervalle)](https://github.com/sebastian-hanisch/output-analysis-demo) |

Der Baum zeigt dieselben Folgestücke in ihrer Abhängigkeit:

```
M/M/1 (diese Demo)                                           [gebaut: mm1-queue-demo]
 ├─ Ereignisdiskrete Simulation (Warm-up, Konfidenz)
 ├─ M/M/c Erlang C (mehrere Server, Pooling)
 │    ├─ Erlang A (Abwanderung)
 │    │    └─ Halfin-Whitt / Wurzel-Personalregel
 │    │         └─ Zeitvariable Ankünfte (MOL, ISA)
 │    └─ Power-of-d-Choices (viele Spuren)
 ├─ M/M/c/c Erlang B (Verlustsystem)
 │    └─ Seltene Ereignisse (Splitting)
 ├─ M/G/1 Pollaczek-Khinchine → Kingman G/G/1 (beliebige Bedienzeit)
 │    └─ Prioritätsklassen
 └─ Jackson-Netze (mehrere Stationen)
      └─ Surrogat-Modelle (NN/GP) gegen Formel und Simulation
```

Hier nicht enthalten: mehrere Server, begrenzte Schlange, Geduld, nicht-exponentielle Bedienzeiten (nur als
Gegenbeispiel mit fester Dauer), zeitabhängige Ankunftsraten, Prioritäten, Netze.

## Verwandte Demos im Portfolio

- [`ems_demo`](https://github.com/sebastian-hanisch/ems-demo): Fall-Demo zur Standortplanung von Rettungsfahrzeugen
  mit dem **Hypercube Queueing Model** (Larson 1974), einer Markov-Kette über alle 2ᴺ Verfügbarkeitszustände mehrerer
  Server. Ihr Korrektheitstest ist die klassische **Erlang-B-Formel**, dieselbe, die diese Linie in einem Folgestück
  (Verlustsystem) selbst herleitet. Dort ist die Warteschlangenrechnung Werkzeug für die Standortwahl, hier ist sie das Thema.
- [`berth-allocation-demo`](https://github.com/sebastian-hanisch/berth-allocation-demo) und
  [`truck-appointment-demo`](https://github.com/sebastian-hanisch/truck-appointment-demo): Fall-Demos der Terminal-Planung,
  deterministisch (kein Zufall im Modell). Hier ist der Zufall das Modell.
- [`value-iteration-demo`](https://github.com/sebastian-hanisch/value-iteration-demo): Markov-Entscheidungsprozesse
  (Zustände mit Übergangswahrscheinlichkeiten und Entscheidungen) aus der Reinforcement-Learning-Linie.

## Tests

87 Tests, rund 20 s: Formeln gegen Handrechnung und die abgeschnittene Geburts-Sterbe-Kette, Simulation gegen eine von
Hand gerechnete Drei-Lkw-Instanz (Wartezeiten, ∫N dt, Zeit je Zustand, Treppenkurve), Generator gegen die Referenzfolge,
Ereignissimulation gegen Lindley-Rekursion, Little's Gesetz als Pfadidentität, Auswertungsfunktionen von Hand, Vollständigkeit
der vorgerechneten Datei, Presets/Permalink, AppTest-Rauchtests (Standard, jedes Preset, Überlast, Randwerte, Permalink-
Grenzen, Würfel-Knopf) und `test_claims.py` für jede Zahl dieser README.

## Dateistruktur

| Datei | Inhalt |
|---|---|
| `app.py` | Streamlit-Oberfläche |
| `mm1_formulas.py` | geschlossene Formeln (M/M/1, Gegenbeispiel M/D/1) |
| `mm1_simulation.py` | Generator, Ereignissimulation mit Handlern, Lindley-Rekursion |
| `mm1_evaluation.py` | Kennzahlen, Verteilungen, Little-Gegenprobe, Messreihen-Funktionen |
| `generate_precomputed.py` | rechnet die Messreihen vor → `precomputed_sweep.json` |
| `mm1_visualization.py` | Plotly-Abbildungen (Achsen gesperrt) |
| `mm1_presets.py`, `mm1_constants.py` | Presets, Permalink, Grenzen |
| `tests/` | siehe oben |

## Literatur

- Little, J. D. C. (1961): A Proof for the Queuing Formula: L = λW. *Operations Research* 9(3), 383–387.
- Lindley, D. V. (1952): The theory of queues with a single server. *Mathematical Proceedings of the Cambridge Philosophical
  Society* 48(2), 277–289.
- Kendall, D. G. (1953): Stochastic Processes Occurring in the Theory of Queues and their Analysis by the Method of the
  Imbedded Markov Chain. *Annals of Mathematical Statistics* 24(3), 338–354 (Kendall-Notation).
- Wolff, R. W. (1982): Poisson Arrivals See Time Averages. *Operations Research* 30(2), 223–231.

## Lokal ausführen

```
pip install -r requirements.txt
streamlit run app.py
```

Tests: `pip install -r requirements-dev.txt` und `python -m pytest tests/ -v`. Messreihen neu rechnen:
`python generate_precomputed.py`.

Gebaut mit Streamlit und Plotly.
