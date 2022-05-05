from typing import Sequence

import numpy as np

from Core.Data.CTCalibrations.MCsquareCalibration.mcsquareMaterial import MCsquareMaterial


class RangeShifter:
    def __init__(self):
        self.ID = ''
        self.type = ''
        self.material = None
        self.density = 0.0
        self.WET = 0.0

    def __str__(self):
        s = ''
        s = s + 'RS_ID = ' + self.ID + '\n'
        s = s + 'RS_type = ' + self.type + '\n'
        s = s + 'RS_density = ' + str(self.density) + '\n'
        s = s + 'RS_WET = ' + str(self.WET) + '\n'

        return s

    def mcsquareFormatted(self, materials:Sequence[MCsquareMaterial]) -> str:
        refDensities = np.array([m.density for m in materials])
        materialIndex = np.argmin(np.abs(refDensities - self.density)) + 1

        s = ''
        s = s + 'RS_ID = ' + self.ID + '\n'
        s = s + 'RS_type = ' + self.type + '\n'
        s = s + 'RS_material = ' + str(materialIndex) + '\n'
        s = s + 'RS_density = ' + str(self.density) + '\n'
        s = s + 'RS_WET = ' + str(self.WET) + '\n'

        return s
