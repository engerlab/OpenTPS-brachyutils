
__all__ = ['RangeShifter']

from opentps.core.data.CTCalibrations.MCsquareCalibration._mcsquareMolecule import MCsquareMolecule


class RangeShifter:
    def __init__(self):
        self.ID = ''
        self.type = ''
        self.material:MCsquareMolecule = None
        self.density = 0.0
        self.WET = 0.0

    def __str__(self):
        s = ''
        s = s + 'RS_ID = ' + self.ID + '\n'
        s = s + 'RS_type = ' + self.type + '\n'
        s = s + 'RS_density = ' + str(self.density) + '\n'
        s = s + 'RS_WET = ' + str(self.WET) + '\n'

        return s

    def mcsquareFormatted(self, materials) -> str:
        materialIndex = -1
        for i, material in enumerate(materials):
            if material["name"] == self.material.name:
                materialIndex = material["ID"]

        if materialIndex==-1:
            raise Exception('RS material ' + self.material.name + ' not found in material list')

        s = ''
        s = s + 'RS_ID = ' + self.ID + '\n'
        s = s + 'RS_type = ' + self.type + '\n'
        s = s + 'RS_material = ' + str(materialIndex) + '\n'
        s = s + 'RS_density = ' + str(self.density) + '\n'
        s = s + 'RS_WET = ' + str(self.WET) + '\n'

        return s
