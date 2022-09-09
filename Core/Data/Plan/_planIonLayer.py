
__all__ = ['PlanIonLayer']


import copy
import unittest
from typing import Iterable, Union, Sequence, Optional, Tuple

import numpy as np


class PlanIonLayer:
    def __init__(self, nominalEnergy: float = 0.0):
        self._x = np.array([])
        self._y = np.array([])
        self._mu = np.array([])
        self._timings = np.array([])
        self.scalingFactor = 1.

        self.nominalEnergy: float = nominalEnergy
        self.numberOfPaintings: int = 1
        self.rangeShifterSettings: RangeShifterSettings = RangeShifterSettings()
        self.seriesInstanceUID = ""

    def __len__(self):
        return len(self._mu)

    def __str__(self):
        s = 'NominalEnergy: ' + str(self.nominalEnergy) + '\n'
        s += 'Spots ((x, y), MU): \n'

        xyAndMUs = zip(list(self.spotXY), self._mu)
        for xyAndMU in xyAndMUs:
            s += str(xyAndMU)
        return s

    def __deepcopy__(self, memodict={}):
        newLayer = PlanIonLayer()

        memodict[id(self)] = newLayer

        newLayer._deepCopyProperties(self, memodict)

        return newLayer

    def _deepCopyProperties(self, otherLayer, memodict):
        self._x = np.array(otherLayer._x)
        self._y = np.array(otherLayer._y)
        self._mu = np.array(otherLayer._mu)
        self._timings = np.array(otherLayer._timings)

        self.nominalEnergy = otherLayer.nominalEnergy
        self.numberOfPaintings = otherLayer.numberOfPaintings
        self.rangeShifterSettings = otherLayer.rangeShifterSettings.__deepcopy__(memodict)
        self.seriesInstanceUID = otherLayer.seriesInstanceUID

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
    def spotMUs(self) -> np.ndarray:
        return np.array(self._mu)

    @spotMUs.setter
    def spotMUs(self, mu: Sequence[float]):
        mu = np.array(mu)

        if len(self._mu) != len(mu):
            raise ValueError(
                "Length of provided MUs is not correct. Provided: " + str(len(mu)) + " - Expected: " + str(
                    len(self._mu)))

        self._mu = mu

    @property
    def spotWeights(self) -> np.ndarray:
        return np.array(self._mu/self.scalingFactor)

    @spotWeights.setter
    def spotWeights(self, w: Sequence[float]):
        self._mu = np.array(w * self.scalingFactor)

    @property
    def spotTimings(self) -> np.ndarray:
        return np.array(self._timings)

    @spotTimings.setter
    def spotTimings(self, w: Sequence[float]):
        w = np.array(w)

        if len(self._timings) != len(w):
            raise ValueError(
                "Length of provided spot timings is not correct. Provided: " + str(len(w)) + " - Expected: " + str(
                    len(self._timings)))

        self._timings = w

    @property
    def meterset(self) -> float:
        return np.sum(self.spotMUs)

    @property
    def numberOfSpots(self) -> int:
        return len(self.spotMUs)

    def addToSpot(self, x: Union[float, Sequence[float]], y: Union[float, Sequence[float]],
                  mu: Union[float, Sequence[float]], timing: Optional[Union[float, Sequence[float]]] = None):
        if isinstance(x, Iterable):
            for i, xElem in enumerate(x):
                t = timing if timing is None else timing[i]
                self._addToSinglepot(xElem, y[i], mu[i], t)
        else:
            self._addToSinglepot(x, y, mu, timing)

    def _addToSinglepot(self, x: float, y: float, mu: float, timing: Optional[float] = None):
        alreadyExists, where = self.spotDefinedInXY(x, y)
        if alreadyExists:
            self._mu[where] = self._mu[where] + mu
        else:
            self._appendSingleSpot(x, y, mu, timing)

    def appendSpot(self, x: Union[float, Sequence[float]], y: Union[float, Sequence[float]],
                   mu: Union[float, Sequence[float]], timing: Optional[Union[float, Sequence[float]]] = None):
        if not isinstance(x, Iterable): x = [x]
        if not isinstance(y, Iterable): y = [y]
        if not isinstance(mu, Iterable): mu = [mu]
        if timing is not None and not isinstance(timing, Iterable): timing = [timing]

        for i, xElem in enumerate(x):
            t = timing if timing is None else timing[i]
            self._appendSingleSpot(xElem, y[i], mu[i], t)

    def _appendSingleSpot(self, x: float, y: float, mu: float, timing: Optional[float] = None):
        alreadyExists, where = self.spotDefinedInXY(x, y)
        if alreadyExists:
            if timing is None:  # possible to have two spots at the same location with different timings (e.g. bursts in synchrocyclotron)
                raise ValueError('Spot already exists in (x,y)')
            else:
                if timing == self._timings[where]:
                    raise ValueError('Spot already exists in (x,y,timing)')

        self._x = np.append(self._x, x)
        self._y = np.append(self._y, y)
        self._mu = np.append(self._mu, mu)
        if timing is not None:
            self._timings = np.append(self._timings, timing)
            assert len(self._mu) == len(self._timings)

    def setSpot(self, x: Union[float, Sequence[float]], y: Union[float, Sequence[float]],
                mu: Union[float, Sequence[float]], timing: Optional[Union[float, Sequence[float]]] = None):
        if isinstance(x, Iterable):
            for i, xElem in enumerate(x):
                t = timing if timing is None else timing[i]
                self._setSingleSpot(xElem, y[i], mu[i], t)
        else:
            self._setSingleSpot(x, y, mu, timing)

    def _setSingleSpot(self, x: float, y: float, mu: float, timing: Optional[float] = None):
        alreadyExists, spotPos = self.spotDefinedInXY(x, y)
        if alreadyExists:
            self._x[spotPos] = x
            self._y[spotPos] = y
            self._mu[spotPos] = mu
            if timing is not None: self._timings[spotPos] = timing
        else:
            self.appendSpot(x, y, mu, timing)

    def removeSpot(self, x: Union[float, Sequence[float]], y: Union[float, Sequence[float]]):
        _, spotPos = self.spotDefinedInXY(x, y)

        self._x = np.delete(self._x, spotPos)
        self._y = np.delete(self._y, spotPos)
        self._mu = np.delete(self._mu, spotPos)
        if len(self._timings) > 0:
            self._timings = np.delete(self._timings, spotPos)

    def spotDefinedInXY(self, x: Union[float, Sequence[float]], y: Union[float, Sequence[float]]) -> Tuple[bool, int]:
        if isinstance(x, Iterable):
            exist = []
            where = []
            for i, xElem in enumerate(x):
                logicalVal, pos = self._singleSpotCheck(xElem, y[i])

                exist.append(logicalVal)
                where.append(pos)
        else:
            exist, where = self._singleSpotCheck(x, y)

        return (exist, where)

    def _singleSpotCheck(self, x: float, y: float) -> Tuple[bool, Optional[int]]:
        for i, (x_xy, y_xy) in enumerate(self.spotXY):
            if (x == x_xy and y == y_xy):
                return (True, i)
        return (False, None)

    def reorderSpots(self, order: Union[str, Sequence[int]] = 'scanAlgo'):
        if type(order) is str:
            if order == 'scanAlgo':  # the way scanAlgo sort spots in a serpentine fashion
                coord = np.column_stack((self._x, self._y)).astype(float)
                order = np.argsort(coord.view('f8,f8'), order=['f1', 'f0'],
                                   axis=0).ravel()  # sort according to y then x
                coord = coord[order]
                _, ind_unique = np.unique(coord[:, 1], return_index=True)  # unique y's
                n_unique = len(ind_unique)
                if n_unique > 1:
                    for i in range(1, n_unique):
                        if i == n_unique - 1:
                            ind_last_x_at_current_y = coord.shape[0]
                        else:
                            ind_last_x_at_current_y = ind_unique[i + 1] - 1
                        if ind_unique[i] == ind_last_x_at_current_y:  # only 1 spot for current y coord
                            continue

                        coord_last_x_at_current_y = coord[ind_last_x_at_current_y - 1, 0]
                        ind_previous = ind_unique[i] - 1
                        coord_previous = coord[ind_previous, 0]
                        ind_first_x_at_current_y = ind_unique[i]
                        coord_first_x_at_current_y = coord[ind_first_x_at_current_y, 0]

                        # Check closest point to coord_previous
                        if np.abs(coord_previous - coord_first_x_at_current_y) > np.abs(
                                coord_previous - coord_last_x_at_current_y):
                            # Need to inverse the order of the spot irradiated for those coordinates:
                            order[ind_first_x_at_current_y:ind_last_x_at_current_y] = order[
                                                                                      ind_first_x_at_current_y:ind_last_x_at_current_y][
                                                                                      ::-1]
                            coord[ind_first_x_at_current_y:ind_last_x_at_current_y] = coord[
                                                                                      ind_first_x_at_current_y:ind_last_x_at_current_y][
                                                                                      ::-1]

            elif order == 'timing':  # sort spots by increasing order of timings
                assert len(self._timings) == len(self._mu)
                order = np.argsort(self._timings)
            else:
                raise ValueError(f"order method type {order} does not exist.")

        # order is a list of the order of the spot irradiated
        # sort all lists according to order
        n = len(order)
        self._x = np.array([self._x[i] for i in order])
        self._y = np.array([self._y[i] for i in order])
        self._mu = np.array([self._mu[i] for i in order])
        if len(self._timings) == n:
            self._timings = np.array([self._timings[i] for i in order])

    def simplify(self, threshold: float = 0.0):
        self._fusionDuplicates()
        self.removeZeroMUSpots(threshold)
    
    def removeZeroMUSpots(self, threshold):
        index_to_keep = np.flatnonzero(self._mu > threshold)
        self._mu = np.array([self._mu[i] for i in range(len(self._mu)) if i in index_to_keep])
        self._x = np.array([self._x[i] for i in range(len(self._x)) if i in index_to_keep])
        self._y = np.array([self._y[i] for i in range(len(self._y)) if i in index_to_keep])


    def _fusionDuplicates(self):
        if len(self) > 1:
            # If timing is not taken into account (self._timings is empty), two spots with the same location are considered duplicates
            # If timing is taken into account (self._timings is not empty), two spots with the same location are considered duplicates only if their timing are equal
            if len(self._timings)==0:
                unique_positions = [(self._x[0], self._y[0])]
                ind = 1
                while ind < len(self._x):
                    current_position = (self._x[ind], self._y[ind])
                    if current_position in unique_positions:
                        #fusion
                        match_ind = unique_positions.index(current_position) # find index in unique positions
                        self._mu[match_ind] += self._mu[ind]
                        self._x = np.delete(self._x, ind)
                        self._y = np.delete(self._y, ind)
                        self._mu = np.delete(self._mu, ind)
                    else:
                        unique_positions.append(current_position)
                        ind += 1
            else:
                unique_positions = [(self._x[0], self._y[0], self._timings[0])]
                ind = 1
                while ind < len(self._x):
                    current_position = (self._x[ind], self._y[ind], self._timings[ind])
                    if current_position in unique_positions:
                        #fusion
                        match_ind = unique_positions.index(current_position) # find index in unique positions
                        self._mu[match_ind] += self._mu[ind]
                        self._x = np.delete(self._x, ind)
                        self._y = np.delete(self._y, ind)
                        self._mu = np.delete(self._mu, ind)
                        self._timings = np.delete(self._timings, ind)
                    else:
                        unique_positions.append(current_position)
                        ind += 1

    def copy(self):
        return copy.deepcopy(self)

    def createEmptyLayerWithSameMetaData(self):
        layer = self.copy()
        layer._x = np.array([])
        layer._y = np.array([])
        layer._mu = np.array([])
        layer._timings = np.array([])
        return layer


class RangeShifterSettings:
    def __init__(self):
        self.isocenterToRangeShifterDistance = 0.0
        self.rangeShifterWaterEquivalentThickness = None  # Means get thickness from BDL! This is extremely error prone!
        self.rangeShifterSetting = 'OUT'
        self.referencedRangeShifterNumber = 0

    def __deepcopy__(self, memodict={}):
        newSettings = RangeShifterSettings()

        newSettings.isocenterToRangeShifterDistance = self.isocenterToRangeShifterDistance
        newSettings.rangeShifterWaterEquivalentThickness = self.rangeShifterWaterEquivalentThickness
        newSettings.rangeShifterSetting = self.rangeShifterSetting
        newSettings.referencedRangeShifterNumber = self.referencedRangeShifterNumber

        return newSettings


class PlanIonLayerTestCase(unittest.TestCase):
    def testAppendSpot(self):
        layer = PlanIonLayer()

        x = 0
        y = 0
        mu = 0
        layer.appendSpot(x, y, mu)

        self.assertEqual(list(layer.spotXY), [(x, y)])
        self.assertEqual(layer.spotMUs, 0)

        self.assertRaises(Exception, lambda: layer.appendSpot(x, y, mu))

    def testAppendSpotWithTiming(self):
        layer = PlanIonLayer()

        x = 0
        y = 0
        mu = 0
        timing = 0
        layer.appendSpot(x, y, mu, timing)

        self.assertEqual(list(layer.spotXY), [(x, y)])
        self.assertEqual(layer.spotMUs, 0)
        self.assertEqual(layer.spotTimings, 0)

        self.assertRaises(Exception, lambda: layer.appendSpot(x, y, mu, timing))

    def testSetSpot(self):
        layer = PlanIonLayer()

        x = 0
        y = 0
        mu = 0

        layer.setSpot(x, y, mu)
        self.assertEqual(list(layer.spotXY), [(x, y)])
        self.assertEqual(layer.spotMUs, 0)

        layer.setSpot(x, y, mu)
        self.assertEqual(list(layer.spotXY), [(x, y)])
        self.assertEqual(layer.spotMUs, 0)

    def testSetSpotWithTiming(self):
        layer = PlanIonLayer()

        x = 0
        y = 0
        mu = 0
        timing = 0

        layer.setSpot(x, y, mu, timing)
        self.assertEqual(list(layer.spotXY), [(x, y)])
        self.assertEqual(layer.spotMUs, 0)
        self.assertEqual(layer.spotTimings, 0)

        layer.setSpot(x, y, mu)
        self.assertEqual(list(layer.spotXY), [(x, y)])
        self.assertEqual(layer.spotMUs, 0)
        self.assertEqual(layer.spotTimings, 0)

    def testRemoveSpot(self):
        layer = PlanIonLayer()

        x = 0
        y = 0
        mu = 0
        timing = 0

        layer.setSpot(x, y, mu, timing)
        self.assertEqual(list(layer.spotXY), [(x, y)])
        self.assertEqual(layer.spotMUs, 0)
        self.assertEqual(layer.spotTimings, 0)

        layer.removeSpot(x, y)

        self.assertEqual(list(layer.spotXY), [])
        np.testing.assert_array_equal(layer.spotMUs, np.array([]))
        np.testing.assert_array_equal(layer.spotTimings, np.array([]))

        layer.setSpot(x, y, mu, timing)
        self.assertEqual(list(layer.spotXY), [(x, y)])
        self.assertEqual(layer.spotMUs, 0)
        self.assertEqual(layer.spotTimings, 0)

    def testSpotDefinedInXY(self):
        layer = PlanIonLayer()

        x = 0
        y = 0
        mu = 0

        layer.setSpot(x, y, mu)

        exists, where = layer.spotDefinedInXY(x, y)
        self.assertTrue(exists)
        self.assertEqual(where, 0)

        layer.removeSpot(x, y)

        exists, where = layer.spotDefinedInXY(x, y)
        self.assertFalse(exists)
        self.assertIsNone(where)

    def testReorderSpots(self):
        layer = PlanIonLayer()
        x = [0, 2, 1, 3]
        y = [1, 2, 2, 0]
        mu = [0.2, 0.5, 0.3, 0.1]

        layer.appendSpot(x, y, mu)
        layer.reorderSpots(order='scanAlgo')
        np.testing.assert_array_equal(layer.spotX, [3, 0, 1, 2])
        np.testing.assert_array_equal(layer.spotY, [0, 1, 2, 2])
        np.testing.assert_array_almost_equal(layer.spotMUs, np.array([0.1, 0.2, 0.3, 0.5]))

        layer = PlanIonLayer()
        x = [0, 1, 2, 3]
        y = [1, 2, 2, 0]
        mu = [0.2, 0.5, 0.3, 0.1]
        timing = [3, 2, 5, 6]
        layer.appendSpot(x, y, mu, timing)
        layer.reorderSpots(order='timing')
        np.testing.assert_array_equal(layer.spotX, [1, 0, 2, 3])
        np.testing.assert_array_equal(layer.spotY, [2, 1, 2, 0])
        np.testing.assert_array_almost_equal(layer.spotMUs, np.array([0.5, 0.2, 0.3, 0.1]))
        np.testing.assert_array_almost_equal(layer.spotTimings, np.array([2, 3, 5, 6]))

    def testFusionDuplicates(self):
        layer = PlanIonLayer(nominalEnergy=100.)
        x = [0, 2, 1, 3, 10, 4]
        y = [1, 2, 2, 0, 2, 5]
        mu = [0.2, 0.5, 0.3, 0.1, 0.2, 0.4]
        layer.appendSpot(x, y, mu)
        layer._x[4] = 2

        layer._fusionDuplicates()
        self.assertEqual(len(layer._x),5)
        np.testing.assert_array_equal(layer.spotX, np.array([0, 2, 1, 3, 4]))
        np.testing.assert_array_equal(layer.spotY, np.array([1, 2, 2, 0, 5]))
        np.testing.assert_array_almost_equal(layer.spotMUs, np.array([0.2, 0.7, 0.3, 0.1, 0.4]))

        layer = PlanIonLayer(nominalEnergy=100.)
        x = [0, 2, 1, 3, 10, 4]
        y = [1, 2, 2, 0, 2, 5]
        mu = [0.2, 0.5, 0.3, 0.1, 0.2, 0.4]
        timings = [1, 2, 3, 4, 2, 6]
        layer.appendSpot(x, y, mu, timings)
        layer._x[4] = 2

        layer._fusionDuplicates()
        self.assertEqual(len(layer._x),5)
        np.testing.assert_array_equal(layer.spotX, np.array([0, 2, 1, 3, 4]))
        np.testing.assert_array_equal(layer.spotY, np.array([1, 2, 2, 0, 5]))
        np.testing.assert_array_equal(layer.spotMUs, np.array([0.2, 0.7, 0.3, 0.1, 0.4]))
        np.testing.assert_array_almost_equal(layer.spotTimings, np.array([1, 2, 3, 4, 6]))

        layer = PlanIonLayer(nominalEnergy=100.)
        x = [0, 2, 1, 3, 10, 3, 2, 30]
        y = [1, 2, 2, 0, 2, 3, 3, 0]
        mu = [0.2, 0.5, 0.3, 0.1, 0.3, 0.6, 0.4, 0.2]
        layer.appendSpot(x, y, mu)
        layer._x[4] = 1
        layer._x[-1] = 3
        layer._fusionDuplicates()
        np.testing.assert_array_equal(layer.spotX, np.array([0, 2, 1, 3, 3, 2]))
        np.testing.assert_array_equal(layer.spotY, np.array([1, 2, 2, 0, 3, 3]))
        np.testing.assert_array_almost_equal(layer.spotMUs, np.array([0.2, 0.5, 0.6, 0.3, 0.6, 0.4]))


if __name__ == '__main__':
    unittest.main()
