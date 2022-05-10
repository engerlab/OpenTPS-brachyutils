import numpy as np
import math
import scipy


def dilate(ct, mask, dilatation):
    """ Dilate ROI mask by [x] mm
    inputs:
    - CT: Patient CT images
    - mask: ROI mask attribute
    - dilatation: margin use to dilate ROI [mm]
    """
    rtvMargin = dilatation  # mm
    rtvMarginX = rtvMargin / ct.PixelSpacing[0]  # voxels
    rtvMarginY = rtvMargin / ct.PixelSpacing[1]  # voxels
    rtvMarginZ = rtvMargin / ct.PixelSpacing[2]  # voxels
    rtvSize = 2 * np.ceil(np.array([rtvMarginY, rtvMarginX, rtvMarginZ])).astype(
        int) + 1  # size of the structuring element
    struct = np.zeros(tuple(rtvSize)).astype(bool)
    for i in range(rtvSize[0]):
        for j in range(rtvSize[1]):
            for k in range(rtvSize[2]):
                y = i - math.floor(rtvSize[0] / 2)
                x = j - math.floor(rtvSize[1] / 2)
                z = k - math.floor(rtvSize[2] / 2)
                if (
                        y ** 2 / rtvMarginY ** 2 + x ** 2 / rtvMarginX ** 2 + z ** 2 / rtvMarginZ ** 2 <= 1):
                    # generate ellipsoid structuring element
                    struct[i, j, k] = True
    rtvMask = scipy.ndimage.binary_dilation(mask, structure=struct).astype(mask.dtype)
    return rtvMask


def createROIRings(ct, patient, targetMask, nRings, deltaMM):
    """
    Create a ring ROI to obtain nice gradient dose around the organ
        inputs:
    patient: ROI added to which patient contours
    target_mask: Organ around which the ring is created
    nRings: Number of rings to be created
    delta_mm: thickness of each ring
    """
    rings = []
    targetSizes = [targetMask]

    for i in range(nRings):
        tgDil = dilate(ct, targetMask, deltaMM * (i + 1))
        targetSizes.append(tgDil)

    for i in range(nRings):
        ringMask = np.logical_xor(targetSizes[i + 1], targetSizes[i])
        ring = ROIcontour()
        ring.ROIName = 'ring_' + str(i + 1)
        ring.SeriesInstanceUID = patient.RTstructs[0].Contours[0].SeriesInstanceUID
        ring.ROIDisplayColor = patient.RTstructs[0].Contours[0].ROIDisplayColor
        ring.Mask = ringMask
        ring.Mask_GridSize = patient.RTstructs[0].Contours[0].Mask, patient.RTstructs[0].Contours[5].Mask_GridSize
        ring.Mask_PixelSpacing = patient.RTstructs[0].Contours[0].Mask, patient.RTstructs[0].Contours[
            5].Mask_PixelSpacing
        ring.Mask_Offset = patient.RTstructs[0].Contours[0].Mask, patient.RTstructs[0].Contours[5].Mask_Offset
        ring.Mask_NumVoxels = patient.RTstructs[0].Contours[0].Mask, patient.RTstructs[0].Contours[5].Mask_NumVoxels
        patient.RTstructs[0].Contours.append(ring)
        patient.RTstructs[0].NumContours += 1
        rings.append(ring)
    return rings


def permuteSparseMatrix(M, newRowOrder=None, newColOrder=None):
    """
    Reorders the rows and/or columns in a scipy sparse matrix
    using the specified array(s) of indexes
    e.g., [1,0,2,3,...] would swap the first and second row/col.
    """
    if newRowOrder is None and newColOrder is None:
        return M

    newM = M
    if newRowOrder is not None:
        identity = scipy.sparse.eye(M.shape[0]).tocoo()
        identity.row = identity.row[newRowOrder]
        newM = identity.dot(newM)
    if newColOrder is not None:
        identity = scipy.sparse.eye(M.shape[1]).tocoo()
        identity.col = identity.col[newColOrder]
        newM = newM.dot(identity)
    return newM.astype(np.float32)


class WeightStructure:
    """
    This class defines the weight structure object interface.
    This class is required to generate arc plans
    It is intended to define several structures and utilities
    such as list of weights/energies grouped by layer or by beam
    but also functions computing ELST, sparsity of the plan, etc.
    """

    def __init__(self, plan):
        self.plan = plan
        # weights
        self.flatWeights = self.plan.get_spot_weights()
        # total number of beam
        self.nBeams = len(self.plan.Beams)
        # total number of layers
        self.nLayers = self.computeNOfLayers()
        # Number of spots in each layer, number of spots in each beam, number of layers in each beam, energy of each
        # layer
        self.nSpotsInLayer, self.nSpotsInBeam, self.nLayersInBeam, self.energyLayers = self.getWeightsStruct()

    def computeNOfLayers(self):
        """
        return total number of energy layers in the plan
        """
        res = 0
        for i in range(len(self.plan.Beams)):
            for j in range(len(self.plan.Beams[i].Layers)):
                res += 1
        return res

    def getSpotIndex(self):
        """
        return 3 lists of size=nSpots:
        *spotsBeams: beam index of each spot
        *spotsLayers: layer index of each spot
        *spotsEnergies: energy of each spot
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
        """
        accumulateLayers = 0
        nOfSpotsInLayer = np.zeros(self.nLayers)
        nOfLayersInBeam = np.zeros(self.nBeams)
        nOfSpotsInBeam = np.zeros(self.nBeams)
        energies = []

        for i in range(len(self.plan.Beams)):
            nOfLayersInBeam[i] = len(self.plan.Beams[i].Layers)
            energiesInbeam = []
            for j in range(len(self.plan.Beams[i].Layers)):
                nOfSpotsInLayer[accumulateLayers] = len(self.plan.Beams[i].Layers[j].SpotMU)
                energiesInbeam.append(self.plan.Beams[i].Layers[j].NominalBeamEnergy)
                nOfSpotsInBeam[i] += len(self.plan.Beams[i].Layers[j].SpotMU)
                accumulateLayers += 1
            energies.append(energiesInbeam)

        return nOfSpotsInLayer.astype(int), nOfSpotsInBeam.astype(int), nOfLayersInBeam.astype(int), energies

    def getEnergyStructure(self, x):
        """transform 1d weight vector into  list of weights vectors ordered by energy layer and beam
        [b1e1,b1e2,...,b2e1,b2e2,...,bBeE]"""
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
        """transform 1d weight vector into  list of layers vectors ordered by beam
        [[[b1e1],[b1e2],...],[[b2e1],[b2e2],...],...,[[bBe1],...,[bBeE]]]"""
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
        return tuble including:
        - Energy layer switching time (ELST) in seconds,
        - Number of upwards energy switching
        - Number of downwards energy switching
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

    def getListOfActiveLayersInBeams(self, x):
        """
        return list of number of active energy layers in each beam (len = nBeams)
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


def getEnergyWeights(energyList):
    """
    return list of energy layer weights (len = nLayers);
    if upward energy switching or same energy: cost = 5.5
    if downward energy switching: cost = 0.6
    [FIX ME]: first layer ?
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
