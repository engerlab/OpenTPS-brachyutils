from Core.Data.Plan.planIonBeam import PlanIonBeam
from Extensions.FLASH.Core.Data.cem import CEM


class CEMBeam(PlanIonBeam):
    def __init__(self):
        super().__init__()

        self.cem:CEM = None
        self.cemToIsocenter:float = 0.