
from Core.Data.CTCalibrations.MCsquareCalibration.mcsquareHU2Material import MCsquareHU2Material
from Core.Data.CTCalibrations.abstractCTCalibration import AbstractCTCalibration
from Core.Data.CTCalibrations.piecewiseHU2Density import PiecewiseHU2Density


class MCsquareCTCalibration(AbstractCTCalibration, PiecewiseHU2Density, MCsquareHU2Material):
    def __init__(self, hu2densityTable=(None, None), hu2materialTable=(None, None), fromFiles=(None, None, 'default')):
        PiecewiseHU2Density.__init__(self, piecewiseTable=hu2densityTable, fromFile=fromFiles[0])
        MCsquareHU2Material.__init__(self, piecewiseTable=hu2materialTable, fromFile=(fromFiles[1], fromFiles[2]))

    def __str__(self):
        s = 'HU - Density\n'
        s += PiecewiseHU2Density.__str__(self)
        s += 'HU - Material\n'
        s += MCsquareHU2Material.__str__(self)

        return s

    def convertHU2MassDensity(self, hu):
        return PiecewiseHU2Density.convertHU2MassDensity(self, hu)

    def convertHU2RSP(self, hu, energy=100):
        raise('TODO')

    def convertMassDensity2HU(self, density):
        return PiecewiseHU2Density.convertMassDensity2HU(self, density)

    def convertMassDensity2RSP(self, density, energy=100):
        raise('TODO')

    def convertRSP2HU(self, rsp, energy=100):
        return self.convertMassDensity2HU(self.convertRSP2MassDensity(rsp, energy))

    def convertRSP2MassDensity(self, rsp, energy=100):
        raise('TODO')

    def write(self, folderPath, scannerName):
        scannerPath = os.path.join(folderPath, 'Scanners', scannerName)
        materialPath = os.path.join(folderPath, 'Materials')

        os.makedirs(scannerPath, exist_ok=True)
        os.makedirs(materialPath, exist_ok=True)

        PiecewiseHU2Density.write(self, os.path.join(scannerPath, 'HU_Density_Conversion.txt'))
        MCsquareHU2Material.write(self, materialPath, os.path.join(scannerPath, 'HU_Material_Conversion.txt'))

# test
if __name__ == '__main__':
    import os
    import MCsquare

    MCSquarePath = str(MCsquare.__path__[0])
    scannerPath = os.path.join(MCSquarePath, 'Scanners', 'UCL_Toshiba')

    calibration = MCsquareCTCalibration(fromFiles=(os.path.join(scannerPath, 'HU_Density_Conversion.txt'),
                                                   os.path.join(scannerPath, 'HU_Material_Conversion.txt'),
                                                   os.path.join(MCSquarePath, 'Materials')))

    print(calibration)

    calibration.write('/home/sylvain/Documents/sandbox', 'scanner')