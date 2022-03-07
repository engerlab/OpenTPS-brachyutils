import unittest
from typing import Iterable, Union, Sequence, Optional, Tuple

import numpy as np


class PlanIonLayer:
    def __init__(self, nominalEnergy:float=0.0):
        self._x = np.array([])
        self._y = np.array([])
        self._weights = np.array([])

        self.nominalEnergy:float = nominalEnergy
        self.numberOfPaintings:int = 1
        self.rangeShifterSettings:RangeShifterSettings = RangeShifterSettings()

    def __deepcopy__(self, memodict={}):
        newLayer = PlanIonLayer()

        newLayer._x = np.array(self._x)
        newLayer._y = np.array(self._y)
        newLayer._weights = np.array(self._weights)

        newLayer.nominalEnergy = self.nominalEnergy
        newLayer.numberOfPaintings = self.numberOfPaintings
        newLayer.rangeShifterSettings = self.rangeShifterSettings

        return newLayer

    def __len__(self):
        return len(self._weights)

    def __str__(self):
        s = 'NominalEnergy: ' + str(self.nominalEnergy) + '\n'
        s += 'Spots ((x, y), MU): \n'

        xyAndWeights = zip(list(self.spotXY), self._weights)
        for xyAndWeight in xyAndWeights:
            s += str(xyAndWeight)
        return s

    @property
    def spotX(self) -> Sequence[float]:
        return [x for x in self._x]

    @property
    def spotY(self) -> Sequence[float]:
        return [y for y in self._y]

    @property
    def spotXY(self) -> Iterable[Tuple[float, float]]:
        return zip(self._x, self._y)

    @property
    def spotWeights(self) -> np.ndarray:
        return np.array(self._weights)

    @spotWeights.setter
    def spotWeights(self, w:Sequence[float]):
        w = np.array(w)

        if len(self._weights) != len(w):
            raise ValueError("Length of provided weights is not correct. Provided: " + str(len(w)) + " - Expected: " + str(len(self._weights)))

        self._weights = w

    @property
    def meterset(self) -> float:
        return np.sum(self._weights)

    def addToSpot(self, x:Union[float, Sequence[float]], y:Union[float, Sequence[float]], weight:Union[float, Sequence[float]]):
        if isinstance(x, Sequence):
            for i, xElem in enumerate(x):
                self._addToSinglepot(xElem, y[i], weight[i])
        else:
            self._addToSinglepot(x, y, weight)

    def _addToSinglepot(self, x:float, y:float, weight:float):
        alreadyExists, where = self.spotDefinedInXY(x, y)
        if alreadyExists:
            self._weights[where] = self._weights[where] + weight
        else:
            self._appendSingleSpot(x, y, weight)

    def appendSpot(self, x:Union[float, Sequence[float]], y:Union[float, Sequence[float]], weight:Union[float, Sequence[float]]):
        if isinstance(x, Sequence):
            for i, xElem in enumerate(x):
                self._appendSingleSpot(xElem, y[i], weight[i])
        else:
            self._appendSingleSpot(x, y, weight)

    def _appendSingleSpot(self, x:float, y:float, weight:float):
        alreadyExists, _ = self.spotDefinedInXY(x, y)
        if alreadyExists:
            raise ValueError('Spot already exists in (x,y)')

        self._x = np.append(self._x, x)
        self._y = np.append(self._y, y)
        self._weights = np.append(self._weights, weight)

    def setSpot(self, x:Union[float, Sequence[float]], y:Union[float, Sequence[float]], weight:Union[float, Sequence[float]]):
        if isinstance(x, Sequence):
            for i, xElem in enumerate(x):
                self._setSingleSpot(xElem, y[i], weight[i])
        else:
            self._setSingleSpot(x, y, weight)

    def _setSingleSpot(self, x:float, y:float, weight:float):
        alreadyExists, spotPos = self.spotDefinedInXY(x, y)
        if alreadyExists:
            self._x[spotPos] = x
            self._y[spotPos] = y
            self._weights[spotPos] = weight
        else:
            self.appendSpot(x, y, weight)

    def removeSpot(self, x:Union[float, Sequence[float]], y:Union[float, Sequence[float]]):
        _, spotPos = self.spotDefinedInXY(x, y)

        self._x = np.delete(self._x, spotPos)
        self._y = np.delete(self._y, spotPos)
        self._weights = np.delete(self._weights, spotPos)

    def spotDefinedInXY(self, x:Union[float, Sequence[float]], y:Union[float, Sequence[float]]) -> tuple[bool, int]:
        if isinstance(x, Sequence):
            exist = []
            where = []
            for i, xElem in enumerate(x):
                logicalVal, pos = self._singleSpotCheck(xElem, y[i])

                exist.append(logicalVal)
                where.append(pos)
        else:
            exist, where = self._singleSpotCheck(x, y)

        return (exist, where)

    def _singleSpotCheck(self, x:float, y:float) -> Tuple[bool, Optional[int]]:
        for i, (x_xy, y_xy) in enumerate(self.spotXY):
            if (x == x_xy and y == y_xy):
                return (True, i)
        return (False, None)

    def reorderSpots(self, order):
        # TODO
        raise NotImplementedError()

    def simplify(self, threshold:float=0.0):
        # TODO
        raise(NotImplementedError('TODO'))

class RangeShifterSettings:
    def __init__(self):
        self.isocenterToRangeShifterDistance = 0.0
        self.rangeShifterWaterEquivalentThickness = None # Means get thickness from BDL! This is extremely error prone!
        self.rangeShifterSetting = 'OUT'

class PlanIonLayerTestCase(unittest.TestCase):
    def testAppendSpot(self):
        layer = PlanIonLayer()

        x = 0
        y = 0
        weight = 0
        layer.appendSpot(x, y, weight)

        self.assertEqual(list(layer.spotXY), [(x, y)])
        self.assertEqual(layer.spotWeights, 0)

        self.assertRaises(Exception, lambda :layer.appendSpot(x, y, weight))

    def testSetSpot(self):
        layer = PlanIonLayer()

        x = 0
        y = 0
        weight = 0

        layer.setSpot(x, y, weight)
        self.assertEqual(list(layer.spotXY), [(x, y)])
        self.assertEqual(layer.spotWeights, 0)

        layer.setSpot(x, y, weight)
        self.assertEqual(list(layer.spotXY), [(x, y)])
        self.assertEqual(layer.spotWeights, 0)

    def testRemoveSpot(self):
        layer = PlanIonLayer()

        x = 0
        y = 0
        weight = 0

        layer.setSpot(x, y, weight)
        self.assertEqual(list(layer.spotXY), [(x, y)])
        self.assertEqual(layer.spotWeights, 0)

        layer.removeSpot(x, y)

        self.assertEqual(list(layer.spotXY), [])
        np.testing.assert_array_equal(layer.spotWeights, np.array([]))

        layer.setSpot(x, y, weight)
        self.assertEqual(list(layer.spotXY), [(x, y)])
        self.assertEqual(layer.spotWeights, 0)

    def testSpotDefinedInXY(self):
        layer = PlanIonLayer()

        x = 0
        y = 0
        weight = 0

        layer.setSpot(x, y, weight)

        exists, where = layer.spotDefinedInXY(x, y)
        self.assertTrue(exists)
        self.assertEqual(where, 0)

        layer.removeSpot(x, y)

        exists, where = layer.spotDefinedInXY(x, y)
        self.assertFalse(exists)
        self.assertIsNone(where)
