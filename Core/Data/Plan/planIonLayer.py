import unittest
from typing import Iterable, Union, Sequence

import numpy as np


class PlanIonLayer:
    def __init__(self, nominalEnergy:float=0.0):
        self.nominalEnergy = nominalEnergy
        self.numberOfPaintings = 1
        self._spots = PlanIonSpots()
        self.rsSettings = RangeShifterSettings

    def __len__(self):
        return len(self._spots)

    def __str__(self):
        s = 'NominalEnergy: ' + str(self.nominalEnergy) + '\n'
        s += 'Spots (x, y, MU): \n'

        xyAndWeights = zip(list(self._spots.xy), self._spots.weights)
        for xyAndWeight in xyAndWeights:
            s += str(xyAndWeight)
        return s

    @property
    def spots(self):
        return self._spots

    @property
    def meterset(self) -> int:
        return np.sum(self._spots.weights)

    def simplify(self, threshold=0.0):
        # TODO
        raise(NotImplementedError('TODO'))

class RangeShifterSettings:
    def __init__(self):
        self.isocenterToRangeShifterDistance = 0.0
        self.rangeShifterWaterEquivalentThickness = 0.0
        self.rangeShifterSetting = 'OUT'

class PlanIonSpots:
    def __init__(self):
        self._x = np.array([])
        self._y = np.array([])
        self._weights = np.array([])

    def __len__(self):
        return len(self._weights)

    @property
    def xy(self) -> Iterable:
        return zip(self._x, self._y)

    @property
    def weights(self) -> np.ndarray:
        return np.array(self._weights)

    def appendSpot(self, x:Union[float, Sequence], y:Union[float, Sequence], weight:Union[float, Sequence]):
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

    def setSpot(self, x:Union[float, Sequence], y:Union[float, Sequence], weight:Union[float, Sequence]):
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

    def removeSpot(self, x:Union[float, Sequence], y:Union[float, Sequence]):
        _, spotPos = self.spotDefinedInXY(x, y)

        self._x = np.delete(self._x, spotPos)
        self._y = np.delete(self._y, spotPos)
        self._weights = np.delete(self._weights, spotPos)

    def spotDefinedInXY(self, x:Union[float, Sequence], y:Union[float, Sequence]) -> tuple:
        if x is list:
            exist = []
            where = []
            for i, xElem in enumerate(x):
                logicalVal, pos = self._singleSpotCheck(xElem, y[i])

                exist.append(logicalVal)
                where.append(pos)
        else:
            exist, where = self._singleSpotCheck(x, y)

        return (exist, where)


    def _singleSpotCheck(self, x: float, y: float) -> tuple:
        for i, (x_xy, y_xy) in enumerate(self.xy):
            if (x == x_xy and y == y_xy):
                return (True, i)
        return (False, None)

    def reorderSpots(self, order):
        # TODO
        raise NotImplementedError()


class PlanIonSpotsTestCase(unittest.TestCase):
    def testAppendSpot(self):
        spots = PlanIonSpots()

        x = 0
        y = 0
        weight = 0
        spots.appendSpot(x, y, weight)

        self.assertEqual(list(spots.xy), [(x, y)])
        self.assertEqual(spots.weights, 0)

        self.assertRaises(Exception, lambda :spots.appendSpot(x, y, weight))

    def testSetSpot(self):
        spots = PlanIonSpots()

        x = 0
        y = 0
        weight = 0

        spots.setSpot(x, y, weight)
        self.assertEqual(list(spots.xy), [(x, y)])
        self.assertEqual(spots.weights, 0)

        spots.setSpot(x, y, weight)
        self.assertEqual(list(spots.xy), [(x, y)])
        self.assertEqual(spots.weights, 0)

    def testRemoveSpot(self):
        spots = PlanIonSpots()

        x = 0
        y = 0
        weight = 0

        spots.setSpot(x, y, weight)
        self.assertEqual(list(spots.xy), [(x, y)])
        self.assertEqual(spots.weights, 0)

        spots.removeSpot(x, y)

        self.assertEqual(list(spots.xy), [])
        np.testing.assert_array_equal(spots.weights, np.array([]))

        spots.setSpot(x, y, weight)
        self.assertEqual(list(spots.xy), [(x, y)])
        self.assertEqual(spots.weights, 0)

    def testSpotDefinedInXY(self):
        spots = PlanIonSpots()

        x = 0
        y = 0
        weight = 0

        spots.setSpot(x, y, weight)

        exists, where = spots.spotDefinedInXY(x, y)
        self.assertTrue(exists)
        self.assertEqual(where, 0)

        spots.removeSpot(x, y)

        exists, where = spots.spotDefinedInXY(x, y)
        self.assertFalse(exists)
        self.assertIsNone(where)
