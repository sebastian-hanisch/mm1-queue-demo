"""Ereignisdiskrete Simulation einer Ein-Server-Schlange (FIFO) und, als unabhängige zweite Rechnung,
die Lindley-Rekursion für dieselben Wartezeiten.

Aufbau nach Einheiten (je Ereignistyp ein Handler, kein versteckter Zustand):
  - `draw_service`: eine Bedienzeit ziehen (exponentiell oder fest)
  - `handle_arrival`, `handle_departure`: Zustandsübergänge
  - `simulate`: Ereignisschleife (Komposition, keine eigene Regel)
  - `lindley_waits`: Wartezeiten ohne Ereignisliste, aus denselben Zufallszahlen

Zufall nur über einen übergebenen `SplitMix64` (reine Ganzzahl-Arithmetik, Portfolio-Konvention): numpy
garantiert keine über Versionen stabilen Zufallsströme, die CI installiert aber wöchentlich die neueste Version.
Je Kunde werden in fester Reihenfolge (Zwischenankunftszeit, Bedienzeit) gezogen - dadurch liefern
Ereignissimulation und Lindley-Rekursion Zahl für Zahl dieselben Wartezeiten.
"""

import heapq
import math
from collections import deque
from dataclasses import dataclass, field

_MASK = (1 << 64) - 1
ARRIVAL, DEPARTURE = 0, 1
SERVICE_EXP, SERVICE_FIXED = "exp", "fest"


class SplitMix64:
    """Kleiner, gut gemischter 64-Bit-Zufallsgenerator (Vigna); reine Ganzzahl-Arithmetik."""

    def __init__(self, seed):
        self.state = seed & _MASK

    def next(self):
        self.state = (self.state + 0x9E3779B97F4A7C15) & _MASK
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _MASK
        return z ^ (z >> 31)

    def uniform(self):
        """Gleichverteilt auf [0, 1) mit 53 Bit."""
        return (self.next() >> 11) * (1.0 / (1 << 53))

    def expovariate(self, rate):
        """Exponentiell mit Mittel 1/rate (Inversionsverfahren; 1 − u liegt in (0, 1], der Logarithmus ist endlich)."""
        return -math.log(1.0 - self.uniform()) / rate


@dataclass
class SimResult:
    n_customers: int
    end_time: float                  # Zeitpunkt des letzten Abgangs (System dann leer)
    waits: list                      # Wartezeit in der Schlange je Kunde (Reihenfolge der Ankunft)
    sojourns: list                   # Verweilzeit je Kunde (Warten + Bedienung)
    area_in_system: float            # ∫ N(t) dt über [0, end_time]
    area_in_queue: float             # ∫ Nq(t) dt
    busy_time: float                 # Zeit mit belegtem Server
    time_in_state: dict              # n -> Zeit, in der genau n im System waren
    trajectory: list = field(default_factory=list)   # [(t, N nach dem Ereignis)], nur mit `record=True`

    @property
    def mean_in_system(self):
        return self.area_in_system / self.end_time

    @property
    def mean_in_queue(self):
        return self.area_in_queue / self.end_time

    @property
    def mean_wait(self):
        return sum(self.waits) / self.n_customers

    @property
    def mean_sojourn(self):
        return sum(self.sojourns) / self.n_customers

    @property
    def utilisation(self):
        return self.busy_time / self.end_time

    @property
    def arrival_rate(self):
        return self.n_customers / self.end_time


def draw_service(rng, mu, service):
    """Eine Bedienzeit: exponentiell mit Mittel 1/μ oder fest 1/μ (bei fester Dauer wird KEINE Zufallszahl gezogen -
    die Zwischenankunftszeiten bleiben dadurch in beiden Fällen dieselben Zahlen)."""
    return rng.expovariate(mu) if service == SERVICE_EXP else 1.0 / mu


class _State:
    __slots__ = ("t", "n", "queue", "busy", "events", "seq", "n_customers", "lam", "mu", "service",
                 "area_n", "area_q", "busy_time", "time_in_state", "waits", "sojourns", "arrival_time", "service_time",
                 "trajectory", "record")


def _advance_clock(s, t_new):
    """Zeit auf t_new vorstellen und die Flächen unter N(t), Nq(t) sowie die Zeit je Zustand fortschreiben."""
    dt = t_new - s.t
    s.area_n += s.n * dt
    s.area_q += max(s.n - 1, 0) * dt
    if s.busy:
        s.busy_time += dt
    s.time_in_state[s.n] = s.time_in_state.get(s.n, 0.0) + dt
    s.t = t_new


def _start_service(s, cid):
    """Kunde cid beginnt die Bedienung jetzt: Wartezeit festhalten, Abgang einplanen."""
    s.waits[cid] = s.t - s.arrival_time[cid]
    s.busy = True
    s.seq += 1
    heapq.heappush(s.events, (s.t + s.service_time[cid], s.seq, DEPARTURE, cid))


def handle_arrival(s, cid, rng):
    """Ein Lkw kommt an. Bedienzeit wird beim Eintreffen gezogen (Reihenfolge der Zufallszahlen: Zwischen-
    ankunftszeit, Bedienzeit), danach die nächste Ankunft eingeplant - solange noch Kunden kommen sollen."""
    s.arrival_time[cid] = s.t
    s.service_time[cid] = draw_service(rng, s.mu, s.service)
    s.n += 1
    if not s.busy:
        _start_service(s, cid)
    else:
        s.queue.append(cid)
    if cid + 1 < s.n_customers:
        s.seq += 1
        heapq.heappush(s.events, (s.t + rng.expovariate(s.lam), s.seq, ARRIVAL, cid + 1))


def handle_departure(s, cid):
    """Ein Lkw ist abgefertigt. Der nächste in der Schlange (FIFO) beginnt, sonst wird der Server frei."""
    s.sojourns[cid] = s.t - s.arrival_time[cid]
    s.n -= 1
    if s.queue:
        _start_service(s, s.queue.popleft())
    else:
        s.busy = False


def simulate(lam, mu, n_customers, seed, service=SERVICE_EXP, record=False, rng=None):
    """Simuliert `n_customers` Ankünfte (Rate lam) bei Bedienrate mu und läuft, bis alle abgefertigt sind. Start mit
    leerem System. `record=True` schreibt die Treppenkurve N(t) (ein Eintrag je Ereignis) mit. `rng` ersetzt den
    Generator aus `seed` (für Tests mit vorgegebenen Zahlen)."""
    rng = rng if rng is not None else SplitMix64(seed)
    s = _State()
    s.t, s.n, s.queue, s.busy = 0.0, 0, deque(), False
    s.events, s.seq, s.n_customers = [], 0, n_customers
    s.lam, s.mu, s.service = lam, mu, service
    s.area_n = s.area_q = s.busy_time = 0.0
    s.time_in_state = {}
    s.waits, s.sojourns = [0.0] * n_customers, [0.0] * n_customers
    s.arrival_time, s.service_time = [0.0] * n_customers, [0.0] * n_customers
    s.trajectory, s.record = [(0.0, 0)] if record else [], record
    heapq.heappush(s.events, (rng.expovariate(lam), 0, ARRIVAL, 0))
    while s.events:
        t, _, kind, cid = heapq.heappop(s.events)
        _advance_clock(s, t)
        if kind == ARRIVAL:
            handle_arrival(s, cid, rng)
        else:
            handle_departure(s, cid)
        if s.record:
            s.trajectory.append((t, s.n))
    return SimResult(n_customers, s.t, s.waits, s.sojourns, s.area_n, s.area_q, s.busy_time, s.time_in_state,
                     s.trajectory)


def lindley_waits(lam, mu, n_customers, seed, service=SERVICE_EXP, rng=None):
    """Wartezeiten per Lindley-Rekursion W_{k+1} = max(0, W_k + S_k − A_{k+1}): ohne Ereignisliste, aus denselben
    Zufallszahlen in derselben Reihenfolge wie `simulate` (Zwischenankunft k, Bedienzeit k, ...)."""
    rng = rng if rng is not None else SplitMix64(seed)
    waits = [0.0] * n_customers
    expo, w, prev_service = rng.expovariate, 0.0, 0.0
    for k in range(n_customers):
        gap = expo(lam)
        if k > 0:
            w = max(0.0, w + prev_service - gap)
        waits[k] = w
        prev_service = draw_service(rng, mu, service)
    return waits
