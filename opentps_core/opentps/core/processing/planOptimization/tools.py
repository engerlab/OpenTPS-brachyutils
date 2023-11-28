import numpy as np
import scipy.sparse as sp
import pandas as pd

from opentps.core.data import DVH
from opentps.core.data.plan._planIonBeam import PlanIonBeam
from opentps.core.data.plan._planIonLayer import PlanIonLayer
from opentps.core.data.plan._planIonSpot import PlanIonSpot
from opentps.core.data.plan._rtPlan import RTPlan

import logging

logger = logging.getLogger(__name__)


class WeightStructure:
    """
    This class defines the weight structure object interface.
    This class is required to generate arc plans
    It is intended to define several structures and utilities
    such as list of weights/energies grouped by layer or by beam
    but also functions computing ELST, sparsity of the plan, etc.

    Attributes
    ----------
    plan : RTPlan
        The plan to be optimized
    beamletMatrix : scipy.sparse.csc_matrix
        The beamlet matrix of the plan
    x : numpy.ndarray
        The weights of the beamlets
    nSpots : int
        The total number of spots in the plan
    nBeams : int
        The total number of beams in the plan
    nLayers : int
        The total number of layers in the plan
    nSpotsInLayer : numpy.ndarray
        The number of spots in each layer
    nSpotsInBeam : numpy.ndarray
        The number of spots in each beam
    nLayersInBeam : numpy.ndarray
        The number of layers in each beam
    energyLayers : list
        The energies of each layer
    nSpotsGrouped : int
        The total number of spots in the plan after grouping
    sparseMatrixGrouped : scipy.sparse.csc_matrix
        The beamlet matrix of the plan after grouping
    xGrouped : numpy.ndarray
        The weights of the beamlets after grouping
    spotsGrouped : list
        The list of spots after grouping
    beamsGrouped : list
        The list of beams after grouping
    layersGrouped : list
        The list of layers after grouping
    spotNewID : list
        The list of new spot IDs after grouping
    """

    def __init__(self, plan:RTPlan):

        self.plan = plan
        # beamlets
        self.beamletMatrix = self.plan.planDesign.beamlets.toSparseMatrix()
        # weights
        self.x = self.plan.spotMUs
        # total number of spots
        self.nSpots = self.plan.numberOfSpots
        # total number of beam
        self.nBeams = len(self.plan.beams)
        # total number of layers
        self.nLayers = self.computeNOfLayers()
        # Number of spots in each layer, number of spots in each beam, number of layers in each beam, energy of each
        # layer
        self.nSpotsInLayer, self.nSpotsInBeam, self.nLayersInBeam, self.energyLayers = self.getWeightsStruct()
        # Spot grouping
        self.nSpotsGrouped = 0
        self.sparseMatrixGrouped = None
        self.xGrouped = None
        self.spotsGrouped = None
        self.beamsGrouped = None
        self.layersGrouped = None
        self.spotNewID = None

    def loadSolution(self, x):
        """
        load solution x (weights) into the object
        """
        logger.info("LoadingSolution x ...")
        self.x = x

    def computeNOfLayers(self):
        """
        return total number of energy layers in the plan

        Returns
        -------
        int
            The total number of energy layers in the plan
        """
        res = 0
        for i in range(len(self.plan.beams)):
            for j in range(len(self.plan.beams[i].layers)):
                res += 1
        return res

    def getSpotIndex(self):
        """
        return 3 lists of size=nSpots:
        *spotsBeams: beam index of each spot
        *spotsLayers: layer index of each spot
        *spotsEnergies: energy of each spot

        Returns
        -------
        list
            The list of beam indices of each spot
        list
            The list of layer indices of each spot
        list
            The list of energies of each spot
        """
        spotsBeams = []
        spotsLayers = []
        spotsEnergies = []
        accumulateLayers = 0
        for beam in range(self.nBeams):
            for layer in range(self.nLayersInBeam[beam]):
                for spot in range(self.nSpotsInLayer[accumulateLayers]):
                    spotsBeams.append(beam)
                    spotsLayers.append(accumulateLayers)
                    # spotsLayers.append(layer)
                    spotsEnergies.append(self.energyLayers[beam][layer])
                accumulateLayers += 1
        return spotsBeams, spotsLayers, spotsEnergies

    def getWeightsStruct(self):
        """
        return 3 arrays and 1 list of arrays
        * nOfSpotsInLayer: array with number of spots in each layer (size=nLayers)
        * nOfSpotsInBeam: array with number of spots in each beam (size=nBeams)
        * nOfLayersInBeam: array with number of layers in each beam (size=nBeams)
        * energies: list of arrays with energies of each beam (len=nBeams)

        Returns
        -------
        numpy.ndarray
            The number of spots in each layer
        numpy.ndarray
            The number of spots in each beam
        numpy.ndarray
            The number of layers in each beam
        """
        accumulateLayers = 0
        nOfSpotsInLayer = np.zeros(self.nLayers)
        nOfLayersInBeam = np.zeros(self.nBeams)
        nOfSpotsInBeam = np.zeros(self.nBeams)
        energies = []

        for i in range(len(self.plan.beams)):
            nOfLayersInBeam[i] = len(self.plan.beams[i].layers)
            energiesInbeam = []
            for j in range(len(self.plan.beams[i].layers)):
                nOfSpotsInLayer[accumulateLayers] = len(self.plan.beams[i].layers[j].spotMUs)
                energiesInbeam.append(self.plan.beams[i].layers[j].nominalEnergy)
                nOfSpotsInBeam[i] += len(self.plan.beams[i].layers[j].spotMUs)
                accumulateLayers += 1
            energies.append(energiesInbeam)

        return nOfSpotsInLayer.astype(int), nOfSpotsInBeam.astype(int), nOfLayersInBeam.astype(int), energies

    def getEnergyStructure(self, x):
        """
        transform 1d weight vector into  list of weights vectors ordered by energy layer and beam
        [b1e1,b1e2,...,b2e1,b2e2,...,bBeE]

        Parameters
        ----------
        x : numpy.ndarray
            The weights of the beamlets

        Returns
        -------
        list
            The list of weights vectors ordered by energy layer and beam
        """
        energyStruct = []
        accumulateWeights = 0
        for el in range(self.nLayers):
            if el == 0:
                energyStruct.append(x[:self.nSpotsInLayer[el]])
            else:
                accumulateWeights += self.nSpotsInLayer[el - 1]
                energyStruct.append(x[accumulateWeights:self.nSpotsInLayer[el] + accumulateWeights])
        return energyStruct

    def getBeamStructure(self, x):
        """
        transform 1d weight vector into  list of layers vectors ordered by beam
        [[[b1e1],[b1e2],...],[[b2e1],[b2e2],...],...,[[bBe1],...,[bBeE]]]

        Parameters
        ----------
        x : numpy.ndarray
            The weights of the beamlets

        Returns
        -------
        list
            The list of layers vectors ordered by beam
        """
        energyStruct = self.getEnergyStructure(x)
        beamLayerStruct = []
        accumulateLayers = 0
        for nOfLayers in self.nLayersInBeam:
            LayersInbeam = []
            for el in range(len(energyStruct)):
                LayersInbeam.append(energyStruct[accumulateLayers])
                accumulateLayers += 1
                if len(LayersInbeam) == nOfLayers:
                    # reached number of Layers defined in beam, now next beam
                    break
            beamLayerStruct.append(LayersInbeam)
        return beamLayerStruct

    def getMUPerBeam(self, x):
        """
        return list of MUs in each beam (len=nBeams)

        Parameters
        ----------
        x : numpy.ndarray
            The weights of the beamlets

        Returns
        -------
        list
            The list of MUs in each beam
        """
        nOfMUinbeams = []
        energyStruct = self.getEnergyStructure(x)
        beamStruct = self.nLayersInBeam
        accumulateLayers = 0
        for nOfLayers in beamStruct:
            nOfMUInbeam = 0
            LayersInbeam = []
            for el in range(len(energyStruct)):
                nOfMUInbeam += np.sum(energyStruct[accumulateLayers])
                LayersInbeam.append(energyStruct[accumulateLayers])
                accumulateLayers += 1
                if len(LayersInbeam) == nOfLayers:
                    break
            nOfMUinbeams.append(nOfMUInbeam)
        return nOfMUinbeams

    def getMUPerLayer(self, x):
        """
        return list of MUs in each layer (len=nLayers)

        Parameters
        ----------
        x : numpy.ndarray
            The weights of the beamlets

        Returns
        -------
        list
            The list of MUs in each layer
        """
        nOfMUinLayers = []
        energyStruct = self.getEnergyStructure(x)
        beamStruct = self.nLayersInBeam
        accumulateLayers = 0
        for nOfLayers in beamStruct:
            LayersInbeam = []
            for el in range(len(energyStruct)):
                nOfMUinLayers.append(np.sum(energyStruct[accumulateLayers]))
                LayersInbeam.append(energyStruct[accumulateLayers])
                accumulateLayers += 1
                if len(LayersInbeam) == nOfLayers:
                    break
        return nOfMUinLayers

    def computeELSparsity(self, x, nLayers):
        """
        return the percentage of active energy layers in the plan (non-null weight)
        input:
        - x: spot weights
        - nLayers: threshold on number of active layers in each beam

        Parameters
        ----------
        x : numpy.ndarray
            The weights of the beamlets
        nLayers : int
            The threshold on number of active layers in each beam

        Returns
        -------
        float
            The percentage of active energy layers in the plan (non-null weight) = Sparsity
        """
        energyStruct = self.getEnergyStructure(x)
        layersActiveInBeams = np.zeros(len(self.nLayersInBeam))
        accumulateLayers = 0
        i = 0
        for nOfLayers in self.nLayersInBeam:
            layersActiveInBeam = 0
            LayersInbeam = []
            for el in range(len(energyStruct)):
                nOfMUInLayer = np.sum(energyStruct[accumulateLayers])
                if nOfMUInLayer > 0.0:
                    layersActiveInBeam += 1
                LayersInbeam.append(energyStruct[accumulateLayers])
                accumulateLayers += 1
                if len(LayersInbeam) == nOfLayers:
                    # reached number of Layers defined in beam, now next beam
                    break
            layersActiveInBeams[i] = layersActiveInBeam
            i += 1
        idealCase = np.count_nonzero(layersActiveInBeams < nLayers + 1)
        percentageOfActiveLayers = idealCase / self.nBeams
        return percentageOfActiveLayers * 100

    def getListOfActiveEnergies(self, x, regCalc=True):
        """
        return list of energies of the active layers (non-null weight)
        ! zero if layer is not active (len = nLayers)

        Parameters
        ----------
        x : numpy.ndarray
            The weights of the beamlets
        regCalc : bool (default=True)
            If True, the list of energies of the active layers is returned for regularized calculation

        Returns
        -------
        list
            The list of energies of the active layers
        """
        energyStruct = self.getEnergyStructure(x)
        activeEnergyList = []
        accumulateLayers = 0
        i = 0

        for nOfLayers in self.nLayersInBeam:
            layersActiveInBeam = 0
            LayersInbeam = []
            for el in range(len(energyStruct)):
                nOfMUInLayer = np.sum(energyStruct[accumulateLayers])

                if regCalc:
                    if nOfMUInLayer > 0.0:
                        layersActiveInBeam += 1
                        activeEnergyList.append(self.energyLayers[i][el])
                    else:
                        activeEnergyList.append(0.)
                else:
                    if nOfMUInLayer > 0.0:
                        layersActiveInBeam += 1
                        activeEnergyList.append(self.energyLayers[i][el])

                LayersInbeam.append(energyStruct[accumulateLayers])
                accumulateLayers += 1
                if len(LayersInbeam) == nOfLayers:
                    # reached number of Layers defined in beam, now next beam
                    break

            i += 1
        return activeEnergyList

    def computeIrradiationTime(self, x):
        """
        return the irradiation time of the plan (in seconds)

        Parameters
        ----------
        x : numpy.ndarray
            The weights of the beamlets

        Returns
        -------
        float
            The Energy layer switching time (ELST) in seconds
        int
            The number of upwards energy switching
        int
            The number of downwards energy switching
        """
        time = 0
        switchUp = 0
        switchDown = 0
        activeEnergyList = self.getListOfActiveEnergies(x, regCalc=False)

        for j, energy in enumerate(activeEnergyList[1:], start=1):
            if activeEnergyList[j - 1] == activeEnergyList[j]:
                pass
            else:
                if activeEnergyList[j - 1] > activeEnergyList[j]:
                    # switch down
                    time += 0.6
                    switchDown += 1
                elif activeEnergyList[j - 1] < activeEnergyList[j]:
                    # switch up
                    time += 5.5
                    switchUp += 1

        return time, switchUp, switchDown

    def isActivated(self, el: PlanIonLayer) -> bool:
        """
        return True if layer is activated (non-null weight)

        Parameters
        ----------
        el : PlanIonLayer
            The layer to be checked

        Returns
        -------
        bool
            True if layer is activated (non-null weight)
        """
        activated = False
        for spotID in el.spotIndices:
            if self.x[spotID] > 0.0:
                activated = True
                break
        return activated

    def getListOfActiveLayersInBeams(self, x):
        """
        return list of number of active energy layers in each beam (len = nBeams)

        Parameters
        ----------
        x : numpy.ndarray
            The weights of the beamlets

        Returns
        -------
        list
            The list of number of active energy layers in each beam
        """
        beamStruct = self.nLayersInBeam
        energyStruct = self.getEnergyStructure(x)

        layersActiveInBeams = []
        totalActiveLayers = 0
        accumulateLayers = 0
        j = 0
        meanMUinbeams = []
        for nOfLayers in beamStruct:
            nOfMUinbeam = 0
            layersActiveInBeam = 0
            LayersInBeam = []
            for el in range(nOfLayers):
                nOfMUInLayer = np.sum(energyStruct[accumulateLayers])
                nOfMUinbeam += nOfMUInLayer
                if nOfMUInLayer > 0.0:
                    layersActiveInBeam += 1
                    totalActiveLayers += 1
                LayersInBeam.append(energyStruct[accumulateLayers])
                accumulateLayers += 1
                if len(LayersInBeam) == nOfLayers:
                    break
            layersActiveInBeams.append(layersActiveInBeam)
            meanOfMUinbeam = nOfMUinbeam / nOfLayers
            meanMUinbeams.append(meanOfMUinbeam)
            j += 1
        return layersActiveInBeams

    def groupSpots(self, groupSpotsby=10):
        """
        Group spot by a given parameter. Allows to get a faster optimal solution to be used as a warm start for
        higher scale problem

        Parameters
        ----------
        groupSpotsby : int (default=10)
            The number of spots to be grouped
        """
        accumulatedSpots = 0
        accumulatedLayers = 0
        nNewSpotsInLayer = []
        self.spotsGrouped = []
        self.spotNewID = []

        for i, beam in enumerate(self.plan.beams):
            for j, layer in enumerate(beam.layers):
                nSpotsInLayer = len(layer.spots)
                nNewSpots = divmod(nSpotsInLayer, groupSpotsby)
                for k in range(nNewSpots[0] + 1):
                    spot = PlanIonSpot()
                    spot.id = accumulatedSpots
                    spot.beamID = i
                    spot.layerID = accumulatedLayers
                    spot.energy = self.energyLayers[i][j]
                    if k == nNewSpots[0]:
                        self.spotNewID += nNewSpots[1] * [accumulatedSpots]
                        if nNewSpots[1] > 0:
                            accumulatedSpots += 1
                            self.spotsGrouped.append(spot)
                    else:
                        self.spotNewID += groupSpotsby * [accumulatedSpots]
                        self.spotsGrouped.append(spot)
                        accumulatedSpots += 1
                if nNewSpots[1] > 0:
                    nNewSpotsInLayer.append(nNewSpots[0] + 1)
                else:
                    nNewSpotsInLayer.append(nNewSpots[0])
                accumulatedLayers += 1
        self.nSpotsGrouped = accumulatedSpots
        self.xGrouped = np.zeros(self.nSpotsGrouped)
        logger.info("New number of spots = ", self.nSpotsGrouped)
        # New structure:
        accumulatedLayers = 0
        accumulatedSpots = 0
        self.layersGrouped = []
        self.beamsGrouped = []
        # BEAMS
        for i in range(self.nBeams):
            b = PlanIonBeam()
            b.id = i
            # LAYERS
            for j in range(self.nLayersInBeam[i]):
                el = PlanIonLayer()
                el.id = accumulatedLayers
                el.beamID = i
                el.nominalEnergy = self.energyLayers[i][j]
                # SPOTS
                for k in range(nNewSpotsInLayer[accumulatedLayers]):
                    el._spotIndices.append(accumulatedSpots)
                    el._spots.append(self.spotsGrouped[accumulatedSpots])
                    accumulatedSpots += 1
                self.layersGrouped.append(el)
                b._layerIndices.append(el.id)
                b._layers.append(el)
                accumulatedLayers += 1
            self.beamsGrouped.append(b)
        logger.info("accumulated spots = ", accumulatedSpots)
        # BEAMLET
        # Load beamlet matrix
        matrix_coo = sp.coo_matrix(self.beamletMatrix)
        beamletsGrouped = [matrix_coo.row, [], matrix_coo.data]
        for i in range(len(beamletsGrouped[0])):
            spot_id = self.spotNewID[matrix_coo.col[i]]
            # minidose is tricky
            beamletsGrouped[1].append(spot_id)
        logger.info('new index in sparse matrix')
        # get index of elements with same voxel_id and spot_id
        zipList = list(zip(matrix_coo.row, beamletsGrouped[1]))
        idx_duplicates = list(pd.DataFrame(zipList).groupby([0, 1], axis=0).indices.values())
        logger.info('find index of duplicates')
        # merge dose corresponding to same new spot id
        for elem in idx_duplicates:
            minidose = 0
            for idx in elem:
                minidose += beamletsGrouped[2][idx]
            for idx in elem:
                beamletsGrouped[2][idx] = minidose
        logger.info('add dose corresponding to same new spot id')
        # to remove duplicated from list and reduce beamlet size
        res = list(set(list(zip(beamletsGrouped[0], beamletsGrouped[1], beamletsGrouped[2]))))
        logger.info('remove duplicated')
        # unzip result (use zip(*iterable) ?)
        beamletsGrouped = [[i for i, j, k in res], [j for i, j, k in res], [k for i, j, k in res]]
        logger.info('unzip beamlets')
        # create final sparse matrix
        self.sparseMatrixGrouped = sp.csc_matrix((beamletsGrouped[2], (beamletsGrouped[0], beamletsGrouped[1])),
                                                 shape=(self.beamletMatrix.get_shape()[0], self.nSpotsGrouped))
        logger.info('convert to sparse matrix')

    def ungroupSol(self):
        """
        ungroup solution x (weights) into the object
        """
        for i in range(self.nSpots):
            idx = self.spotNewID[i]
            self.x[i] = self.xGrouped[idx]

    def groupSol(self):
        """
        group solution x (weights) into the object
        """
        # u, idx_repeated = np.unique(self.spot_new_id, return_index=True)
        idx_repeated = pd.DataFrame(self.spotNewID).groupby([0]).indices
        for i, itm in enumerate(idx_repeated.values()):
            self.xGrouped[i] = self.x[itm[0]]


def getEnergyWeights(energyList):
    """
    return list of energy layer weights (len = nLayers);
    if upward energy switching or same energy: cost = 5.5
    if downward energy switching: cost = 0.6
    [FIX ME]: first layer ?

    Parameters
    ----------
    energyList : list
        The list of energies of each layer

    Returns
    -------
    list
        The list of energy layer weights
    """
    energyWeights = energyList.copy()
    for i, nonZeroIndex in enumerate(np.nonzero(energyList)[0]):
        if i == 0:
            energyWeights[nonZeroIndex] = 0.1
        elif energyList[nonZeroIndex] == energyList[np.nonzero(energyList)[0][i - 1]]:
            energyWeights[nonZeroIndex] = 0.1
        else:
            if energyList[nonZeroIndex] < energyList[np.nonzero(energyList)[0][i - 1]]:
                energyWeights[nonZeroIndex] = 0.6
            else:
                energyWeights[nonZeroIndex] = 5.5
    finalEnergyWeights = np.where(energyWeights == 0, 1., energyWeights)
    return finalEnergyWeights


def evaluateClinical(dose, contours, clinDict):
    """
    Evaluate clinical constraints

    Parameters
    ----------
    dose : numpy.ndarray
        The dose matrix
    contours : list
        The list of contours
    clinDict : dict
        The dictionary of clinical constraints
    """
    roi = clinDict['ROI']
    metric = clinDict['Metric']
    limit = clinDict['Limit']

    condition = []
    roiIndex = []
    toRemove = []
    L = []
    for i in range(len(contours)):
        L.append(contours[i].name)
    for i in range(len(roi)):
        if metric[i] == 'Dmin':
            condition.append(">")
        else:
            condition.append("<")
        try:
            index_value = L.index(roi[i])
        except ValueError:
            index_value = -1
        if index_value == -1:
            toRemove.append(i)
        else:
            roiIndex.append(index_value)

    for i in sorted(toRemove, reverse=True):
        del (roi[i])
        del (metric[i])
        del (condition[i])
        del (limit[i])

    dash = '-' * 100
    print(dash)
    print('{:<15s}{:<10s}{:<8s}{:<8s}{:^8s}{:<8s}{:^8s}'.format("ROI", "Metric", "Limit", "D98/D2", "Passed", "D95/D5",
                                                                "Passed"))
    print(dash)

    for i in range(len(roi)):
        print('{:<15s}{:<10s}{:<8.2f}'.format(roi[i], metric[i], limit[i]), end="")
        ROI_DVH = DVH(contours[roiIndex[i]], dose)
        if metric[i] == "Dmin":
            print('{:<8.2f}'.format(ROI_DVH.D98), end="")
            if ROI_DVH.D98 > limit[i]:
                print('{:^8s}'.format("1"), end="")
            else:
                print('{:^8s}'.format("0"), end="")
            print('{:<8.2f}'.format(ROI_DVH.D95), end="")
            if ROI_DVH.D95 > limit[i]:
                print('{:^8s}'.format("1"))
            else:
                print('{:^8s}'.format("0"))
        elif metric[i] == "Dmax":
            print('{:<8.2f}'.format(ROI_DVH.D2), end="")
            if ROI_DVH.D2 < limit[i]:
                print('{:^8s}'.format("1"), end="")
            else:
                print('{:^8s}'.format("0"), end="")
            print('{:<8.2f}'.format(ROI_DVH.D5), end="")
            if ROI_DVH.D5 < limit[i]:
                print('{:^8s}'.format("1"))
            else:
                print('{:^8s}'.format("0"))
        elif metric[i] == "Dmean":
            print('{:<8.2f}'.format(ROI_DVH.Dmean), end="")
            if ROI_DVH.Dmean < limit[i]:
                print('{:^8s}'.format("1"))
            else:
                print('{:^8s}'.format("0"))
        else:
            print('{:<8.2f}'.format(ROI_DVH.D003), end="")
            if ROI_DVH.D003 < limit[i]:
                print('{:^8s}'.format("1"))
            else:
                print('{:^8s}'.format("0"))