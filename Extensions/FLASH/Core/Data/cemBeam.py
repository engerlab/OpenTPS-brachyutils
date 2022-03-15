from Core.Data.Plan.planIonBeam import PlanIonBeam

class CEMBeam(PlanIonBeam):
    def __init__(self):
        super().__init__()

        from Extensions.FLASH.Core.Data.cem import CEM # Here to aoid circular import

        self.cem:CEM = None
        self.cemToIsocenter:float = 0.
