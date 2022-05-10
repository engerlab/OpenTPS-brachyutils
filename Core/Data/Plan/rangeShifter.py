from typing import Sequence

import numpy as np

from Core.Data.CTCalibrations.MCsquareCalibration.mcsquareMaterial import MCsquareMaterial


class RangeShifter:
    def __init__(self):
        self.ID = ''
        self.type = ''
        self.material = None # Depreacted! materialName will be used instead
        self.materialName = None
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
        #refDensities = np.array([m.density for m in materials])
        #materialIndex = np.argmin(np.abs(refDensities - self.density)) + 1

        materialIndex = -1
        for i, material in enumerate(materials):
            print(material.name)
            if material.name == self.materialName:
                materialIndex = i

#        if materialIndex==-1:
#            raise Exception('RS material ' + self.materialName + ' not found in material list')

        s = ''
        s = s + 'RS_ID = ' + self.ID + '\n'
        s = s + 'RS_type = ' + self.type + '\n'
        s = s + 'RS_material = ' + str(materialIndex) + '\n'
        s = s + 'RS_density = ' + str(self.density) + '\n'
        s = s + 'RS_WET = ' + str(self.WET) + '\n'

        return s
