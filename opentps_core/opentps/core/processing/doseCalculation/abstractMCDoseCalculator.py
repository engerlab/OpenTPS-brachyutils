
from opentps.core.processing.doseCalculation.abstractDoseCalculator import AbstractDoseCalculator

__all__ = ['AbstractMCDoseCalculator']

class AbstractMCDoseCalculator(AbstractDoseCalculator):
    def __init__(self):
        super().__init__()

    @property
    def nbPrimaries(self) -> int:
        raise NotImplementedError()

    @nbPrimaries.setter
    def nbPrimaries(self, primaries: int):
        raise NotImplementedError()
