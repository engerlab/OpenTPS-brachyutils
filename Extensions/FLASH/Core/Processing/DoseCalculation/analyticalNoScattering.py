from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.doseImage import DoseImage
from Core.Data.Plan.rtPlan import RTPlan
from Core.Processing.DoseCalculation.abstractDoseCalculator import AbstractDoseCalculator


class AnalyticalNoScattering(AbstractDoseCalculator):
    def computeDose(self, ct:CTImage, plan: RTPlan) -> DoseImage:
        resDose = 0
        derivDose = 0
