from opentps.core.processing.doseCalculation import AbstractMCDoseCalculator

__all__ = ['Geant4DoseCalculator']

class Geant4DoseCalculator(AbstractMCDoseCalculator):
    def __init__(self):
        super().__init__()