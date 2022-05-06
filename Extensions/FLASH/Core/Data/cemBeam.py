from typing import Optional

from Core.Data.Plan.planIonBeam import PlanIonBeam

class CEMBeam(PlanIonBeam):
    def __init__(self):
        super().__init__()

        from Extensions.FLASH.Core.Data.cem import BiComponentCEM # Here to aoid circular import

        self.cem:Optional[BiComponentCEM] = None
        self.cemToIsocenter:float = 0.
