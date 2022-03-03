from Core.Processing.DoseCalculation.abstractMCDoseCalculator import AbstractMCDoseCalculator


class Geant4DoseCalculator(AbstractMCDoseCalculator):
    def __init__(self):
        super().__init__()