from opentps.core.processing.doseCalculation.abstractMCDoseCalculator import AbstractMCDoseCalculator


class Geant4DoseCalculator(AbstractMCDoseCalculator):
    def __init__(self):
        super().__init__()