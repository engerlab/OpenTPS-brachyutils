import glob
import os

from Core.Data.CTCalibrations.MCsquareCalibration.mcsquareCTCalibration import MCsquareCTCalibration
from Core.Data.CTCalibrations.RayStationCalibration.rayStationCTCalibration import RayStationCTCalibration
from Core.Data.CTCalibrations.abstractCTCalibration import AbstractCTCalibration


def readScanner(scannerFolder) -> AbstractCTCalibration:
    try:
        return MCsquareCTCalibration(fromFiles=(scannerFolder + os.sep + 'HU_Density_Conversion.txt',
                                                   scannerFolder + os.sep + 'HU_Material_Conversion.txt',
                                                   'default'))
    except:
        pass

    try:
        materialsFile = glob.glob('material*.*')[0]
        conversionFile = glob.glob('calibration*.*')
        conversionFile += (glob.glob('Density*.*'))
        conversionFile  = conversionFile[0]
        return RayStationCTCalibration(fromFiles=(scannerFolder + os.sep + materialsFile,
                                                   scannerFolder + os.sep + conversionFile))
    except:
        pass

    raise ValueError(str(scannerFolder) + ' does not contain a supported CT calibration curve')
