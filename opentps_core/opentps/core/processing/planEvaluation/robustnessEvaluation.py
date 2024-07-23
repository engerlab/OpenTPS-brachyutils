from __future__ import annotations

import logging
from enum import Enum
from typing import Union

import numpy as np
import pickle
import os


from opentps.core.data._dvhBand import DVHBand
from opentps.core.processing.imageProcessing import resampler3D

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from opentps.core.data import ROIContour
    from opentps.core.data.images import ROIMask, DoseImage

logger = logging.getLogger(__name__)

class RobustnessEval:
    """
    This class is used to compute the robustness of a plan.

    Attributes
    ----------
    selectionStrategy : str
        The selection strategy used to select the scenarios.
        It can be "DISABLED", "ERRORSPACE_REGULAR", "ERRORSPACE_STAT" or "DOSIMETRIC".
    setupSystematicError : list (default = [1.6, 1.6, 1.6])
        The setup systematic error in mm.
    setupRandomError : list (default = [1.4, 1.4, 1.4])
        The setup random error in mm.
    rangeSystematicError : float (default = 1.6)
        The range systematic error in %.
    target : ROIContour
        The target contour.
    targetPrescription : float (default = 60)
        The target prescription in Gy.
    nominal : RobustnessScenario
        The nominal scenario.
    numScenarios : int
        The number of scenarios.
    scenarios : list
        The list of scenarios.
    dvhBands : list
        The list of DVH bands.
    doseDistributionType : str
        The dose distribution type.
        It can be "Nominal", "Voxel wise minimum" or "Voxel wise maximum".
    doseDistribution : list[DoseImage]
        The dose distributions.
    """

    # TODO: Add analysisStrategy class : DOSIMETRIC or ERROR SPACE
    class Strategies(Enum):
        DEFAULT = "DISABLED"
        DISABLED = "DISABLED"
        ALL = "ALL"
        REDUCED_SET = "REDUCED_SET"
        RANDOM = "RANDOM"

    def __init__(self):
        self.selectionStrategy = self.Strategies.DEFAULT
        self.setupSystematicError = [1.6, 1.6, 1.6]  # mm
        self.setupRandomError = [1.4, 1.4, 1.4]  # mm
        self.rangeSystematicError = 1.6  # %
        self.target = []
        self.targetPrescription = 60  # Gy
        self.nominal = RobustnessScenario()
        self.numScenarios = 0
        self.scenarios = []
        self.dvhBands = []
        self.doseDistributionType = ""
        self.doseDistribution = []

    def setNominal(self, dose: DoseImage, contours: Union[ROIContour, ROIMask]):
        """
        Set the nominal scenario.

        Parameters
        ----------
        dose : DoseImage
            The dose image.
        contours : list[ROIContour]
            The list of contours.
        """
        from opentps.core.data._dvh import DVH
        self.nominal.dose = dose
        self.nominal.dvh.clear()
        for contour in contours:
            myDVH = DVH(contour, self.nominal.dose)
            self.nominal.dvh.append(myDVH)
        self.nominal.dose.imageArray = self.nominal.dose.imageArray.astype(np.float32)

    def addScenario(self, dose: DoseImage, contours: Union[ROIContour, ROIMask]):
        """
        Add a scenario.

        Parameters
        ----------
        dose : DoseImage
            The dose image.
        contours : list[ROIContour]
            The list of contours.
        """
        from opentps.core.data._dvh import DVH
        scenario = RobustnessScenario()
        scenario.dose = dose
        # Need to set patient to None for memory, est-ce que ca va poser probleme ?
        scenario.dose.patient = None
        scenario.dvh.clear()
        for contour in contours:
            contour.patient = None
            myDVH = DVH(contour, scenario.dose)
            scenario.dvh.append(myDVH)
        scenario.dose.imageArray = scenario.dose.imageArray.astype(
            np.float16)  # can be reduced to float16 because all metrics are already computed and it's only used for display

        self.scenarios.append(scenario)

    def setTarget(self, ct, target, targetPrescription):
        """
        Set the target contour.

        Parameters
        ----------
        ct : CTImage
            The CT image.
        target : ROIContour
            The target contour.
        targetPrescription : float
            The target prescription in Gy.
        """
        from opentps.core.data import ROIContour
        if isinstance(target, ROIContour):
            targetContour = target.getBinaryMask(origin=ct.origin, gridSize=ct.gridSize,
                                                              spacing=ct.spacing)
        else: targetContour = target

        if not(self.nominal.dose.hasSameGrid(targetContour)):
            resampler3D.resampleImage3DOnImage3D(targetContour,self.nominal.dose, inPlace=True, fillValue=0.)
        self.target = targetContour
        self.targetPrescription = targetPrescription
        for dvh in self.nominal.dvh:
            if dvh._roiName == self.target.name:
                self.nominal.targetD95 = dvh.D95
                self.nominal.targetD5 = dvh.D5
                self.nominal.targetMSE = self.computeTargetMSE(self.nominal.dose.imageArray)
                break

        for scenario in self.scenarios:
            for dvh in scenario.dvh:
                if dvh._roiName == self.target.name:
                    scenario.targetD95 = dvh.D95
                    scenario.targetD5 = dvh.D5
                    scenario.targetMSE = self.computeTargetMSE(scenario.dose.imageArray)
                    break

    def recomputeDVH(self, contours):
        """
        Recompute the DVH.

        Parameters
        ----------
        contours : list[ROIContour]
            The list of contours.
        """
        from opentps.core.data._dvh import DVH
        self.nominal.dvh.clear()
        for contour in contours:
            myDVH = DVH(contour, self.nominal.dose)
            self.nominal.dvh.append(myDVH)

        for scenario in self.scenarios:
            scenario.dvh.clear()
            for contour in contours:
                myDVH = DVH(contour, scenario.dose)
                scenario.dvh.append(myDVH)

    def computeTargetMSE(self, dose):
        """
        Compute the target mean square error.

        Parameters
        ----------
        dose : DoseImage
            The dose image.

        Returns
        -------
        float
            The target mean square error.
        """
        dose_vector = dose[self.target.imageArray]
        error = dose_vector - self.targetPrescription
        mse = np.mean(np.square(error))
        return mse

    def analyzeErrorSpace(self, ct, metric, targetContour, targetPrescription):
        """
        Analyze the error space by sorting the scenarios from worst to best according to selected metric and compute the DVH-band.

        Parameters
        ----------
        ct : CTImage
            The CT image.
        metric : str
            The metric used to sort the scenarios.
            It can be "D95" or "MSE".
        targetContour : ROIContour
            The target contour.
        targetPrescription : float
            The target prescription in Gy.
        """
        if (
                self.target == [] or self.target.name != targetContour.name or self.targetPrescription != targetPrescription):
            self.setTarget(ct, targetContour, targetPrescription)

        # sort scenarios from worst to best according to selected metric
        if metric == "D95":
            self.scenarios.sort(key=(lambda scenario: scenario.targetD95))
        elif metric == "MSE":
            self.scenarios.sort(key=(lambda scenario: scenario.targetMSE))

        # initialize dose distribution
        if self.doseDistributionType == "Nominal":
            self.doseDistribution = self.nominal.dose.copy()
        else:
            self.doseDistribution = self.scenarios[0].dose.copy()  # Worst scenario

        # initialize dvh-band structure
        allDVH = []
        allDmean = []
        for dvh in self.scenarios[0].dvh:
            allDVH.append(np.array([]).reshape((len(dvh._volume), 0)))
            allDmean.append([])

        # generate DVH-band
        for s in range(self.numScenarios):
            self.scenarios[s].selected = 1
            if self.doseDistributionType == "Voxel wise minimum":
                self.doseDistribution.imageArray = np.minimum(self.doseDistribution.imageArray, self.scenarios[s].dose.imageArray)
            elif self.doseDistributionType == "Voxel wise maximum":
                self.doseDistribution.imageArray = np.maximum(self.doseDistribution.imageArray, self.scenarios[s].dose.imageArray)
            for c in range(len(self.scenarios[s].dvh)):
                allDVH[c] = np.hstack((allDVH[c], np.expand_dims(self.scenarios[s].dvh[c]._volume, axis=1)))
                allDmean[c].append(self.scenarios[s].dvh[c].Dmean)

        self.dvhBands.clear()
        for c in range(len(self.scenarios[0].dvh)):
            dvh = self.scenarios[0].dvh[c]
            dvhBand = DVHBand()
            dvhBand._roiName = dvh._roiName
            dvhBand._dose = dvh._dose
            dvhBand._volumeLow = np.amin(allDVH[c], axis=1)
            dvhBand._volumeHigh = np.amax(allDVH[c], axis=1)
            dvhBand._nominalDVH = self.nominal.dvh[c]
            dvhBand.computeMetrics()
            dvhBand._Dmean = [min(allDmean[c]), max(allDmean[c])]
            self.dvhBands.append(dvhBand)

    def analyzeDosimetricSpace(self, metric, CI, targetContour, targetPrescription):
        """
        Analyze the dosimetric space by sorting the scenarios from worst to best according to selected metric and compute the DVH-band.

        Parameters
        ----------
        metric : str
            The metric used to sort the scenarios.
            It can be "D95" or "MSE".
        CI : float
            The confidence interval in %.
        targetContour : ROIContour
            The target contour.
        targetPrescription : float
            The target prescription in Gy.
        """
        if (
                self.target == [] or self.target.name != targetContour.name or self.targetPrescription != targetPrescription):
            self.setTarget(targetContour, targetPrescription)

        if metric == "D95":
            self.scenarios.sort(key=(lambda scenario: scenario.targetD95))
        elif metric == "MSE":
            self.scenarios.sort(key=(lambda scenario: scenario.targetMSE))

        start = round(self.numScenarios * (100 - CI) / 100)
        if start == self.numScenarios: start -= 1

        # initialize dose distribution
        if self.doseDistributionType == "Nominal":
            self.doseDistribution = self.nominal.dose.copy()
        else:
            self.doseDistribution = self.scenarios[start].dose.copy()  # Worst scenario

        # initialize dvh-band structure
        selectedDVH = []
        selectedDmean = []
        for dvh in self.scenarios[0].dvh:
            selectedDVH.append(np.array([]).reshape((len(dvh.volume), 0)))
            selectedDmean.append([])

        # select scenarios
        for s in range(self.numScenarios):
            if s < start:
                self.scenarios[s].selected = 0
            else:
                self.scenarios[s].selected = 1
                if self.doseDistributionType == "Voxel wise minimum":
                    self.doseDistribution.imageArray = np.minimum(self.doseDistribution.imageArray, self.scenarios[s].dose.imageArray)
                elif self.doseDistributionType == "Voxel wise maximum":
                    self.doseDistribution.imageArray = np.maximum(self.doseDistribution.imageArray, self.scenarios[s].dose.imageArray)
                for c in range(len(self.scenarios[s].dvh)):
                    selectedDVH[c] = np.hstack(
                        (selectedDVH[c], np.expand_dims(self.scenarios[s].dvh[c].volume, axis=1)))
                    selectedDmean[c].append(self.scenarios[s].dvh[c].Dmean)

        # compute DVH-band envelopes
        self.dvhBands.clear()
        for c in range(len(self.scenarios[s].dvh)):
            dvh = self.scenarios[0].dvh[c]
            dvhBand = DVHBand()
            dvhBand._roiName = dvh._roiName
            dvhBand._dose = dvh._dose
            dvhBand._volumeLow = np.amin(selectedDVH[c], axis=1)
            dvhBand._volumeHigh = np.amax(selectedDVH[c], axis=1)
            dvhBand._nominalDVH = self.nominal.dvh[c]
            dvhBand.computeMetrics()
            dvhBand._Dmean = [min(selectedDmean[c]), max(selectedDmean[c])]
            self.dvhBands.append(dvhBand)

    def printInfo(self):
        """
        Print the information of the robustness evaluation.
        """
        logger.info("Nominal scenario:")
        self.nominal.printInfo()

        for i in range(len(self.scenarios)):
            logger.info("Scenario " + str(i + 1))
            self.scenarios[i].printInfo()

    def save(self, folder_path):
        """
        Save the different scenarios and the robustness test.

        Parameters
        ----------
        folder_path : str
            The folder path.
        """
        if not os.path.isdir(folder_path):
            os.mkdir(folder_path)

        for s in range(self.numScenarios):
            file_path = os.path.join(folder_path, "Scenario_" + str(s) + ".tps")
            self.scenarios[s].save(file_path)


        tmp = self.scenarios
        self.scenarios = []

        file_path = os.path.join(folder_path, "RobustnessTest" + ".tps")
        with open(file_path, 'wb') as fid:
            pickle.dump(self.__dict__, fid)

        self.scenarios = tmp

    def load(self, folder_path):
        """
        Load the different scenarios and the robustness test.

        Parameters
        ----------
        folder_path : str
            The folder path.
        """
        file_path = os.path.join(folder_path, "RobustnessTest" + ".tps")
        with open(file_path, 'rb') as fid:
            tmp = pickle.load(fid)
        self.__dict__.update(tmp)

        for s in range(self.numScenarios):
            file_path = os.path.join(folder_path, "Scenario_" + str(s) + ".tps")
            scenario = RobustnessScenario()
            scenario.load(file_path)
            self.scenarios.append(scenario)

class RobustnessScenario:
    """
    This class is used to store the information of a scenario.

    Attributes
    ----------
    dose : DoseImage
        The dose image.
    dvh : list[DVH]
        The list of DVH.
    targetD95 : float
        The target D95.
    targetD5 : float
        The target D5.
    targetMSE : float
        The target mean square error.
    selected : int
        1 if the scenario is selected, 0 otherwise.
    """

    def __init__(self):
        self.dose = []
        self.dvh = []
        self.targetD95 = 0
        self.targetD5 = 0
        self.targetMSE = 0
        self.selected = 0

    def printInfo(self):
        """
        Print the information of the scenario.
        """
        logger.info("Target_D95 = " + str(self.targetD95))
        logger.info("Target_D5 = " + str(self.targetD5))
        logger.info("Target_MSE = " + str(self.targetMSE))
        logger.info(" ")

    def save(self, file_path):
        """
        Save the scenario.

        Parameters
        ----------
        file_path : str
            The file path.
        """
        with open(file_path, 'wb') as fid:
            pickle.dump(self.__dict__, fid)

    def load(self, file_path):
        """
        Load the scenario.

        Parameters
        ----------
        file_path : str
            The file path.
        """
        with open(file_path, 'rb') as fid:
            tmp = pickle.load(fid)

        self.__dict__.update(tmp)
