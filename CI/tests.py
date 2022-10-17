
import os
import numpy as np

from opentps.core.data import PatientList
from opentps.core.data.images import CTImage
from opentps.core.data.images import ROIMask
from opentps.core.data import Patient
from opentps.core.io import mcsquareIO, scannerReader
from opentps.core.processing.doseCalculation.doseCalculationConfig import DoseCalculationConfig
from opentps.core.examples.registration import exampleMorphons
from opentps.core.examples.segmentation import exampleSegmentation


def checkNoInit():
    import opentps.core as opentpsCore
    path_to_file = os.path.join(opentpsCore.__path__[0], '..', '__init__.py')
    if os.path.exists(path_to_file):
        raise Exception("There cannot be any __init__.py in """ + path_to_file + " to comply with namespace package definition. Please remove this file!")

    path_to_file = os.path.join(opentpsCore.__path__[0], '..', 'opentps', '__init__.py')
    if os.path.exists(path_to_file):
        raise Exception(
            "There cannot be any __init__.py in """ + path_to_file + " to comply with namespace package definition. Please remove this file!")

    path_to_file = os.path.join(opentpsCore.__path__[0], '..', '..', '..', 'opentps_gui', '__init__.py')
    if os.path.exists(path_to_file):
        raise Exception(
            "There cannot be any __init__.py in """ + path_to_file + " to comply with namespace package definition. Please remove this file!")

    path_to_file = os.path.join(opentpsCore.__path__[0], '..', '..', '..', 'opentps_gui', 'opentps', '__init__.py')
    if os.path.exists(path_to_file):
        raise Exception(
            "There cannot be any __init__.py in """ + path_to_file + " to comply with namespace package definition. Please remove this file!")

print('TEST')

checkNoInit()
exampleMorphons.run()
exampleSegmentation.run()


