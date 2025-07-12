from __future__ import annotations

__all__ = ['PlanPhotonSegment']

import copy
from typing import Sequence, Union
import unittest
import numpy as np
import math


class Beamlet:
    def __init__(self, x=None, y=None, mu=0) -> None:
        self._x = x
        self._y = y
        self._mu = mu

    @property
    def XY_mm(self):
        return np.array([[self._x, self._y]])


class PlanPhotonSegment:
    """
    Class for storing the segment data of a photonBeam.

    Attributes
    ----------
    x_jaw_mm: list of float
        List of the x jaw positions in mm
    y_jaw_mm: list of float
        List of the y jaw positions in mm
    Xmlc_mm: list of float
        List of the x MLC positions in mm
    Ymlc_mm: list of float
        List of the y MLC positions in mm
    mu: float
        Monitor units
    seriesInstanceUID: str
        Series instance UID
    isocenterPosition_mm: list of float
        Isocenter position in mm
    gantryAngle_degree: float
        Gantry angle in degree
    couchAngle_degree: float
        Couch angle in degree
    beamLimitingDeviceAngle_degree: float
        Beam limiting device angle in degree
    xBeamletSpacing_mm: float
        Spacing between the x beamlets in mm
    yBeamletSpacing_mm: float
        Spacing between the y beamlets in mm
    _beamlets: list of Beamlet
        List of beamlets
    scalingFactor: float
        Scaling factor
    controlPointIndex: int
        Control point index
    """
    def __init__(self) -> None:
        self.x_jaw_mm = []
        self.y_jaw_mm = []
        self.Xmlc_mm = []
        self.XmlcBoundaries_mm = []
        self.Ymlc_mm = []
        self.mu = None
        self.seriesInstanceUID = ""
        self.isocenterPosition_mm = [0, 0, 0]
        self.gantryAngle_degree = 0.0
        self.couchAngle_degree = 0.0
        self.beamLimitingDeviceAngle_degree = 0.0  ### The beam limiting device rotates CC
        self.xBeamletSpacing_mm = 1
        self.yBeamletSpacing_mm = 1
        self._beamlets: Sequence[
            Beamlet] = []  ### This can be saved as a sparse representation of the beamlet matrix representation
        self.scalingFactor = 1
        self.controlPointIndex = 0

    def __getitem__(self, beamletNb):
        return self._beamlets[beamletNb]

    def __len__(self):
        """
        Returns the number of beamlets.

        Returns
        --------
        int
            number of beamlets
        """
        return len(self._beamlets)

    def __str__(self):
        """
        Returns a string representation of the segment.

        Returns
        --------
        str
            string representation of the segment
        """
        s = ''
        for beamlet in self._beamlets:
            s += 'Beamlet\n'
            s += str(beamlet)
        return s

    @property
    def beamlets(self) -> Sequence[Beamlet]:
        # For backwards compatibility but we can now access each layer with indexing brackets
        return [beamlet for beamlet in self._beamlets]

    @property
    def Ymin(self) -> Sequence[Beamlet]:
        """Retun MLC min position in Y direction."""
        if len(self.Xmlc_mm) > 0:
            return self.Xmlc_mm[0, 0]
        else:
            return -200

    @property
    def Ymax(self) -> Sequence[Beamlet]:
        """Retun MLC max position in Y direction."""
        if len(self.Xmlc_mm) > 0:
            return self.Xmlc_mm[-1, 1]
        else:
            return 200

    @property
    def area_mm(self):
        area_mm = 0
        if len(self._beamlets) > 0:
            area_mm = len(self._beamlets) * self.xBeamletSpacing_mm * self.yBeamletSpacing_mm
        if len(self._beamlets) == 0 and len(self.Xmlc_mm) != 0:
            for leaf in self.Xmlc_mm:
                area_mm += (leaf[1] - leaf[0]) * (leaf[3] - leaf[2])
        return area_mm

    def appendBeamlet(self, x, y, mu):
        self._beamlets.append(Beamlet(x, y, mu))
        self.isPure()

    def appendBeamlets(self, matrixRepresentation):
        FOV = np.abs(self.Xmlc_mm[0, 0]) + np.abs(self.Xmlc_mm[-1, 1])  # Suppose square MLC
        numSpotX = math.ceil(FOV / self.xBeamletSpacing_mm)
        numSpotY = math.ceil(FOV / self.yBeamletSpacing_mm)
        indexes = np.argwhere(matrixRepresentation > 0)
        for index in indexes:
            x = (index[1] - round(numSpotX / 2)) * self.xBeamletSpacing_mm - self.xBeamletSpacing_mm / 2
            y = (index[0] - round(numSpotY / 2)) * self.yBeamletSpacing_mm - self.yBeamletSpacing_mm / 2
            self.appendBeamlet(x, y, matrixRepresentation[index[0], index[1]])
        self.isPure()

    def isPure(self):
        if len(self) > 0:
            if np.all(self.beamletMUs == self.beamletMUs[0]):
                self.mu = self.beamletMUs[0]
                return True
            else:
                self.mu = None
            return False
        else:
            True

    def removeBeamlet(self, beamlet: Union[Beamlet, Sequence[Beamlet]]):
        if isinstance(beamlet, Sequence):
            beamlets = beamlet
            for beamlet in beamlets:
                self.removeBeamlet(beamlet)
            return
        self._beamlets.remove(beamlet)
        self.isPure()

    @property
    def beamletsXY_mm(self) -> np.ndarray:
        xy = np.array([])
        for beamlet in self._beamlets:
            beamletXY = list(beamlet.XY_mm)
            if len(xy) <= 0:
                xy = beamletXY
            else:
                xy = np.concatenate((xy, beamletXY))

        return xy

    @property
    def beamletMUs(self):
        mu = []
        for beamlet in self._beamlets:
            mu.append(beamlet._mu)
        return np.array(mu)

    @beamletMUs.setter
    def beamletMUs(self, mu: Union[Sequence[float], float]):
        # if isinstance(mu, float):
        #     self.mu = mu
        #     return np.array([self.mu] * len(self))
        # print('Beamlets in a beam segment have only one mu')
        mu = np.array(mu)
        if len(mu) == 1:
            mu = np.array([mu[0]] * len(self))
            self.mu = mu[0]
        if len(mu) != len(self):
            raise ValueError(
                f'The size of the mu array {len(mu)} does not fit the size of the beamlets {len(self)} for the beam {self.id}')
        for i, beamlet in enumerate(self._beamlets):
            beamlet._mu = mu[i]
        self.isPure()

    @property
    def meterset(self) -> float:
        return np.sum(self.beamletMUs)

    @property
    def beamletWeights(self) -> np.ndarray:
        return np.array(self.beamletMUs / self.scalingFactor)

    @beamletWeights.setter
    def beamletWeights(self, w: Sequence[float]):
        self.beamletMUs = np.array(w * self.scalingFactor)
        self.isPure()

    def simplify(self, threshold: float = 0.0):
        # self._fusionDuplicates()
        if threshold is not None:
            self.removeZeroMUSpots(threshold)

    def removeZeroMUSpots(self, threshold):
        index_to_keep = np.flatnonzero(self.beamletMUs > threshold)
        self._beamlets = [self._beamlets[i] for i in index_to_keep]

    def copy(self):
        return copy.deepcopy(self)

    def createEmptyBeamSegmentWithSameMetaData(self):
        beamSegment = self.copy()
        beamSegment._beamlets = []
        return beamSegment

    def createBeamletsFromSegments(self):
        if len(self) > 0:
            return
        if len(self.Xmlc_mm) == 0:
            print('to convert a segment into beamlets the segment must have the MLC coordinates')

        FOV = np.abs(self.Xmlc_mm[0, 0]) + np.abs(self.Xmlc_mm[-1, 1])  # Suppose square MLC
        numSpotX = math.ceil(FOV / self.xBeamletSpacing_mm)
        numSpotY = math.ceil(FOV / self.yBeamletSpacing_mm)
        Xaperture = np.abs(self.Xmlc_mm[:, 2] - self.Xmlc_mm[:, 3])
        openMLC = self.Xmlc_mm[Xaperture > self.xBeamletSpacing_mm]
        angle = math.radians(self.beamLimitingDeviceAngle_degree)
        for leaf in openMLC:
            jmin = math.floor((leaf[0] + self.yBeamletSpacing_mm / 2) / self.yBeamletSpacing_mm + round(numSpotY / 2))
            jmax = math.ceil((leaf[1] + self.yBeamletSpacing_mm / 2) / self.yBeamletSpacing_mm + round(numSpotY / 2))
            for j in range(jmin, jmax + 1):
                y = (j - round(numSpotY / 2)) * self.yBeamletSpacing_mm - self.yBeamletSpacing_mm / 2
                if y < leaf[0] or y > leaf[1] or y < self.y_jaw_mm[0] or y > self.y_jaw_mm[1]:
                    continue
                imin = math.floor(
                    (leaf[2] + self.xBeamletSpacing_mm / 2) / self.xBeamletSpacing_mm + round(numSpotX / 2))
                imax = math.ceil(
                    (leaf[3] + self.xBeamletSpacing_mm / 2) / self.xBeamletSpacing_mm + round(numSpotX / 2))
                for i in range(imin, imax + 1):
                    x = (i - round(numSpotX / 2)) * self.xBeamletSpacing_mm - self.xBeamletSpacing_mm / 2
                    if x > self.x_jaw_mm[0] and x < self.x_jaw_mm[1] and x > leaf[2] and x < leaf[3]:
                        self.appendBeamlet(x, y, self.mu)
                        # self.appendBeamlet(x * np.cos(angle) - y * np.sin(angle) , x * np.sin(angle) + y * np.cos(angle), self.mu) ### The beam limiting device rotates CC

    def beamletMatrixRepresentation(self):
        FOV = np.abs(self.Ymin) + np.abs(self.Ymax)  # Suppose square MLC
        numSpotX = math.ceil(FOV / self.xBeamletSpacing_mm)
        numSpotY = math.ceil(FOV / self.yBeamletSpacing_mm)
        beamletsMatrix = np.zeros((numSpotY, numSpotX))
        for beamlet in self._beamlets:
            j = math.floor((beamlet._x + self.xBeamletSpacing_mm / 2) / self.xBeamletSpacing_mm + round(numSpotX / 2))
            i = math.floor((beamlet._y + self.yBeamletSpacing_mm / 2) / self.yBeamletSpacing_mm + round(numSpotY / 2))
            beamletsMatrix[i, j] = beamlet._mu
        return beamletsMatrix


if __name__ == '__main__':
    unittest.main()
