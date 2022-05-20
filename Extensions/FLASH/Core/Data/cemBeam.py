from typing import Optional

from Core.Data.Plan.planIonBeam import PlanIonBeam
from Extensions.FLASH.Core.Data.aperture import Aperture


class CEMBeam(PlanIonBeam):
    def __init__(self):
        super().__init__()

        from Extensions.FLASH.Core.Data.cem import BiComponentCEM # Here to aoid circular import

        self.cem:Optional[BiComponentCEM] = None
        self.aperture:Optional[Aperture] = None
        self.cemToIsocenter:float = 0.
        self.apertureToIsocenter: float = 0.
