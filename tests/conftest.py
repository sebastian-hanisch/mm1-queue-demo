import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class ScriptedRng:
    """Liefert vorgegebene Werte statt Zufall (Mini-Instanz von Hand gerechnet); `expovariate(rate)` ignoriert die
    Rate und gibt der Reihe nach die Werte zurück - Reihenfolge wie in der Simulation: Zwischenankunftszeit 1,
    Bedienzeit 1, Zwischenankunftszeit 2, ..."""

    def __init__(self, values):
        self.values = list(values)
        self.i = 0

    def expovariate(self, rate):
        v = self.values[self.i]
        self.i += 1
        return v


@pytest.fixture
def mini_rng():
    """Drei Lkw: Ankünfte bei 1, 2.5, 3.5 Minuten; Bedienzeiten 2, 2, 1 (Zwischenankunft 1, Bedienung 2, 1.5, 2, 1, 1)."""
    return ScriptedRng([1, 2, 1.5, 2, 1, 1])
