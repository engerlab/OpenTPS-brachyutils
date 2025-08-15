__all__ = ['RobustnessPhoton','RobustScenario']

import itertools
import logging
import numpy as np
from opentps.core.data._sparseBeamlets import SparseBeamlets
from opentps.core.data.plan._robustness import Robustness

logger = logging.getLogger(__name__)


class RobustScenario(SparseBeamlets):
    def __init__(self, sse = None, sre = None):
        self.sse = sse      # Setup Systematic Error
        self.sre = sre      # Setup Random Error
        
    def printInfo(self):
        logger.info('Setup Systematic Error:{} mm'.format(self.sse))
        logger.info('Setup Random Error:{} mm'.format(self.sre))

    def __str__(self):
        str = 'Setup Systematic Error:{} mm\n'.format(self.sse) + 'Setup Random Error:{} mm\n'.format(self.sre)

        return str
    
    def toTxt(self, path):
        f = open(path, "w")
        f.write(str(self))
        f.close()

class RobustnessPhoton(Robustness):
    """
    This class creates an object that stores the robustness parameters of a photon plan and generates robust scenarios through sampling(optimization).

    Attributes
    ----------
    scenariosConfig : list
        The list of scenarios configurations.
    """

    def __init__(self):
        self.numberOfSigmas = 2.5
        self.scenariosConfig:list[RobustScenario] = []
        
        super().__init__()
    
    def generateRobustScenarios(self):
        if self.setupSystematicError not in [None, 0, [0,0,0]]:
            if self.selectionStrategy == self.selectionStrategy.RANDOM :
                self.generateRandomScenarios()
            elif self.selectionStrategy == self.selectionStrategy.REDUCED_SET :
                self.generateReducedErrorSpacecenarios()
            elif self.selectionStrategy == self.selectionStrategy.ALL :
                self.generateAllErrorSpaceScenarios()
            else :
                raise Exception("No evaluation strategy selected")
        else :
            raise Exception("No evaluation strategy selected")

        # Remove duplicates and nominal scenario
        sse_list = []
        for s in reversed(range(len(self.scenariosConfig))):
            scenario = self.scenariosConfig[s]
            sse  = scenario.sse.tolist()
            if sse in sse_list or sse == [0,0,0]:
                self.scenariosConfig.pop(s)
            else:
                sse_list.append(sse)

    def generateReducedErrorSpacecenarios(self):  # From [a, b, c] to 6 scenarios [+-a, +-b, +-c]
        for index, sse in enumerate(self.setupSystematicError):
            for sign in [-1,1]:
                array = np.zeros(3)
                array[index] = sse * sign
                scenario = RobustScenario(sse = array, sre = self.setupRandomError)
                self.scenariosConfig.append(scenario)

    def generateAllErrorSpaceScenarios(self):
        # Point coordinates on hypersphere with two zero axes
        R = self.setupSystematicError[0]
        for sign in [-1, 1]:
            self.scenariosConfig.append(RobustScenario(sse = np.round(np.array([sign * R, 0, 0]), 2), sre = self.setupRandomError))
            self.scenariosConfig.append(RobustScenario(sse = np.round(np.array([0, sign * R, 0]), 2), sre = self.setupRandomError))
            self.scenariosConfig.append(RobustScenario(sse = np.round(np.array([0, 0, sign * R]), 2), sre = self.setupRandomError))

        # Coordinates of point on hypersphere with zero axis
        sqrt2 = R / np.sqrt(2)
        for sign1, sign2 in itertools.product([-1, 1], repeat=2):
            self.scenariosConfig.append(RobustScenario(sse = np.round(np.array([sign1 * sqrt2, sign2 * sqrt2, 0]), 2), sre = self.setupRandomError))
            self.scenariosConfig.append(RobustScenario(sse = np.round(np.array([sign1 * sqrt2, 0, sign2 * sqrt2]), 2), sre = self.setupRandomError))
            self.scenariosConfig.append(RobustScenario(sse = np.round(np.array([0, sign1 * sqrt2, sign2 * sqrt2]), 2), sre = self.setupRandomError))

        # Coordinates of point on hypersphere without any zero axis (diagonals)
        sqrt3 = R / np.sqrt(3)
        for signs in itertools.product([-1, 1], repeat=3):
            self.scenariosConfig.append(RobustScenario(sse = np.round(np.array([signs[0] * sqrt3, signs[1] * sqrt3, signs[2] * sqrt3]), 2), sre = self.setupRandomError))


    def generateRandomScenarios(self):
        # Sample in gaussian, the gaussian is scaled by the number of sigmas cause the input is already sigma x nbr of sigma
        setupErrorSpace = self.setupSystematicError
        for _ in range(self.numScenarios):
            SampleSetupError = [np.random.normal(0, sigma/self.numberOfSigmas) for sigma in setupErrorSpace]
            SampleSetupError = np.round(SampleSetupError, 2)
            scenario = RobustScenario(sse = SampleSetupError, sre = self.setupRandomError)
            self.scenariosConfig.append(scenario)

    def sampleScenario(self):
        sse_sampled = list(np.random.normal([0]*len(self.setupSystematicError),self.setupSystematicError)) if self.setupSystematicError != None else None
        sre_sampled = np.random.uniform([self.setupRandomError,0]) if self.setupRandomError != None else None
        return RobustScenario(sb = None, sse = sse_sampled, sre = sre_sampled)
