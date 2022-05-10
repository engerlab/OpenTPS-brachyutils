import functools
import os

import numpy as np

from Core.Data.CTCalibrations.RayStationCalibration.rayStationCTCalibration import RayStationCTCalibration
from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.roiMask import ROIMask
from Core.Data.patient import Patient
from Core.IO import mcsquareIO
from Core.api import API
from Extensions.FLASH.Core.Processing.CEMOptimization import cemObjectives, workflows
from Extensions.FLASH.Core.Processing.CEMOptimization.workflows import SingleBeamCEMOptimizationWorkflow
import Extensions.FLASH.DefaultData as defaultDataModule


def setPatient(patient, data):
    data.patient = patient

defaultDataPath = defaultDataModule.__path__[0]

# openTPS patient list
patientList = API.patientList

# We create a dummy patient for this study
patient = Patient()
patient.name = 'Patient0'

patientList.append(patient)

# Create a CT larger in dim 1 so that it can fully contain the CEF
ct = CTImage()
ctSize = (120, 200, 120)
imageArray = -1024.*np.ones(ctSize)
imageArray[:, 160:, :] = 0
ct.imageArray = imageArray
ct.name = 'CT'
ct.patient = patient
ct.orgin = (0, 0, 0)
ct.spacing = (1, 1, 1)

# Target ROI
roi = ROIMask.fromImage3D(ct)
roiArray = np.zeros(roi.imageArray.shape)
roiArray[58:63, 170:185, 58:63] = 1
roi.imageArray = roiArray.astype(bool)
roi.name = 'TV'
roi.patient = patient

terms = []
obj = cemObjectives.DoseMinObjective(roi, 20-0.5)
objective = workflows.Objective(objectiveTerm=obj, weight=1.)
terms.append(objective)
obj = cemObjectives.DoseMaxObjective(roi, 20+0.5)
objective = workflows.Objective(objectiveTerm=obj, weight=1.)
terms.append(objective)


cemOptimizer = SingleBeamCEMOptimizationWorkflow()
cemOptimizer.ctCalibration = RayStationCTCalibration(fromFiles=(defaultDataPath + os.path.sep + 'calibration_cef.txt', defaultDataPath + os.path.sep + 'materials_cef.txt'))
cemOptimizer.beamModel = mcsquareIO.readBDL(defaultDataPath + os.path.sep + 'BDL_memoire.txt')
cemOptimizer.gantryAngle = 0.
cemOptimizer.cemToIsocenter = 50.
cemOptimizer.beamEnergy = 100.
cemOptimizer.ct = ct
cemOptimizer.spotSpacing = 20.
cemOptimizer.cemRSP = 1.
cemOptimizer.rangeShifterRSP = 1.
cemOptimizer.objectives = terms

cemOptimizer.doseUpdateEvent.connect(functools.partial(setPatient, patient))

cemOptimizer.run()

finalDose = cemOptimizer.finalDose
finalDose.name = 'Final dose'
finalDose.patient = patient

beam = cemOptimizer.finalPlan.beams[0]
cem = beam.cem
np.savetxt('cemData', cem.imageArray)
