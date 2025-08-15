
__all__ = ['PlanProtonLayer']


import copy
import unittest
from typing import Iterable, Union, Sequence, Optional, Tuple
import numpy as np

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from opentps.core.data.plan._planProtonSpot import PlanProtonSpot


class PlanProtonLayer:
    """
    This class is used to store the layer of a ionBeam.

    Attributes
    ----------
    nominalEnergy: float (default: 0.0)
        nominal energy of the layer
    spots: list of PlanIonSpot
        list of spots
    spotX: np.ndarray
        x coordinates of the spots
    spotY: np.ndarray
        y coordinates of the spots
    spotXY: np.ndarray
        x and y coordinates of the spots
    spotMUs: np.ndarray
        MUs of the spots
    spotWeights: np.ndarray
        weights of the spots
    spotTimings: np.ndarray
        timings of the spots
    spotIrradiationDurations: np.ndarray
        irradiation durations of the spots
    meterset:
        meterset of the layer
    numberOfSpots: int
        number of spots
    numberOfPaintings: int (default: 1)
        number of paintings
    rangeShifterSettings: RangeShifterSettings
        range shifter settings
    seriesInstanceUID: str
        series instance UID
    spotsPeakPosInDcmCoords: list of np.ndarray
        peak positions of the spots in DICOM coordinates
    spotsPeakPosInTargetSystem: list of np.ndarray
        peak positions of the spots in target system coordinates
    """
    def __init__(self, nominalEnergy: float = 0.0):

        self._spots: Sequence[PlanProtonSpot] = []
        self._x = np.array([])
        self._y = np.array([])
        self._mu = np.array([])
        self._startTime = np.array([])
        self._irradiationDuration = np.array([])
        self.scalingFactor = 1.

        self.nominalEnergy: float = nominalEnergy
        self.numberOfPaintings: int = 1
        self.rangeShifterSettings: RangeShifterSettings = RangeShifterSettings()
        self.seriesInstanceUID = ""
        self.spotsPeakPosInDcmCoords = []
        self.spotsPeakPosInTargetSystem = []

    def __len__(self):
        """
        Returns the number of spots.

        Returns
        --------
        int
            number of spots
        """
        return len(self._mu)

    def __str__(self):
        """
        Returns a string representation of the layer.

        Returns
        --------
        str
            string representation of the layer
        """
        s = 'NominalEnergy: ' + str(self.nominalEnergy) + '\n'
        s += 'Spots ((x, y), MU): \n'

        xyAndMUs = zip(list(self.spotXY), self._mu)
        for xyAndMU in xyAndMUs:
            s += str(xyAndMU)
        return s

    @property
    def spots(self):
        # For backwards compatibility but we can now access each layer with indexing brackets
        return [spot for spot in self._spots]

    @property
    def spotX(self) -> Sequence[float]:
        return self._x

    @property
    def spotY(self) -> Sequence[float]:
        return self._y

    @property
    def spotXY(self) -> Iterable[Tuple[float, float]]:
        return np.column_stack((self._x, self._y))

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
        return np.array(self._startTime)

    @spotTimings.setter
    def spotTimings(self, w: Sequence[float]):
        w = np.array(w)

        if len(self._startTime) != len(w):
            raise ValueError(
                "Length of provided spot timings is not correct. Provided: " + str(len(w)) + " - Expected: " + str(
                    len(self._startTime)))

        self._startTime = w

    @property
    def spotIrradiationDurations(self) -> np.ndarray:
        return np.array(self._irradiationDuration)

    @spotIrradiationDurations.setter
    def spotIrradiationDurations(self, w: Sequence[float]):
        w = np.array(w)

        if self.numberOfSpots != len(w):
            raise ValueError(
                "Length of provided spot timings is not correct. Provided: " + str(len(w)) + " - Expected: " + str(
                    self.numberOfSpots))

        self._irradiationDuration = w

    @property
    def meterset(self) -> float:
        return np.sum(self.spotMUs)

    @property
    def numberOfSpots(self) -> int:
        return len(self.spotXY)

    def addToSpot(self, x: Union[float, Sequence[float]], y: Union[float, Sequence[float]],
                  mu: Union[float, Sequence[float]], startTime: Optional[Union[float, Sequence[float]]] = None,
                  irradiationDuration: Optional[Union[float, Sequence[float]]] = None):
        """
        Adds MU to a spot or multiple spots.

        Parameters
        ----------
        x: float or Sequence[float]
            x coordinate of the spot(s)
        y: float or Sequence[float]
            y coordinate of the spot(s)
        mu: float or Sequence[float]
            MU of the spot(s)
        startTime: float or Sequence[float] (optional)
            start time of the spot(s)
        irradiationDuration: float or Sequence[float] (optional)
            irradiation duration of the spot(s)
        """
        if isinstance(x, Iterable):
            for i, xElem in enumerate(x):
                t = startTime if startTime is None else startTime[i]
                d = irradiationDuration if irradiationDuration is None else irradiationDuration[i]
                self._addToSinglepot(xElem, y[i], mu[i], t, d)
        else:
            self._addToSinglepot(x, y, mu, startTime, irradiationDuration)

    def _addToSinglepot(self, x: float, y: float, mu: float, startTime: Optional[float] = None, irradiationDuration: Optional[float] = None):
        alreadyExists, where = self.spotDefinedInXY(x, y)
        if alreadyExists:
            self._mu[where] = self._mu[where] + mu
        else:
            self._appendSingleSpot(x, y, mu, startTime, irradiationDuration)

    def appendSpot(self, x: Union[float, Sequence[float]], y: Union[float, Sequence[float]],
                   mu: Union[float, Sequence[float]], startTime: Optional[Union[float, Sequence[float]]] = None,
                   irradiationDuration: Optional[Union[float, Sequence[float]]] = None):
        """
        Appends a spot or multiple spots to the layer.

        Parameters
        ----------
        x: float or Sequence[float]
            x coordinate of the spot(s)
        y: float or Sequence[float]
            y coordinate of the spot(s)
        mu: float or Sequence[float]
            MU of the spot(s)
        startTime: float or Sequence[float] (optional)
            start time of the spot(s)
        irradiationDuration: float or Sequence[float] (optional)
            irradiation duration of the spot(s)
        """
        if not isinstance(x, Iterable): x = [x]
        if not isinstance(y, Iterable): y = [y]
        if not isinstance(mu, Iterable): mu = [mu]
        if startTime is not None and not isinstance(startTime, Iterable): startTime = [startTime]
        if irradiationDuration is not None and not isinstance(irradiationDuration, Iterable): irradiationDuration = [irradiationDuration]
        for i, xElem in enumerate(x):
            t = startTime if startTime is None else startTime[i]
            d = irradiationDuration if irradiationDuration is None else irradiationDuration[i]
            self._appendSingleSpot(xElem, y[i], mu[i], t, d)

    def _appendSingleSpot(self, x: float, y: float, mu: float, startTime: Optional[float] = None, irradiationDuration: Optional[float] = None):
        alreadyExists, where = self.spotDefinedInXY(x, y)
        if alreadyExists:
            if startTime is None:  # possible to have two spots at the same location with different timings (e.g. bursts in synchrocyclotron)
                raise ValueError('Spot already exists in (x,y)')
            else:
                if startTime == self._startTime[where]:
                    raise ValueError('Spot already exists in (x,y,timing)')

        self._x = np.append(self._x, x)
        self._y = np.append(self._y, y)
        self._mu = np.append(self._mu, mu)
        if startTime is not None:
            self._startTime = np.append(self._startTime, startTime)
            assert len(self._mu) == len(self._startTime)
        if irradiationDuration is not None:
            self._irradiationDuration = np.append(self._irradiationDuration, irradiationDuration)
            assert len(self._mu) == len(self._irradiationDuration)           

    def setSpot(self, x: Union[float, Sequence[float]], y: Union[float, Sequence[float]],
                mu: Union[float, Sequence[float]], startTime: Optional[Union[float, Sequence[float]]] = None,
                irradiationDuration: Optional[Union[float, Sequence[float]]] = None):
        """
        Sets a spot or multiple spots to the layer.

        Parameters
        ----------
        x: float or Sequence[float]
            x coordinate of the spot(s)
        y: float or Sequence[float]
            y coordinate of the spot(s)
        mu: float or Sequence[float]
            MU of the spot(s)
        startTime: float or Sequence[float] (optional)
            start time of the spot(s)
        irradiationDuration: float or Sequence[float] (optional)
            irradiation duration of the spot(s)
        """
        if isinstance(x, Iterable):
            for i, xElem in enumerate(x):
                t = startTime if startTime is None else startTime[i]
                d = irradiationDuration if irradiationDuration is None else irradiationDuration[i]
                self._setSingleSpot(xElem, y[i], mu[i], t, d)
        else:
            self._setSingleSpot(x, y, mu, startTime, irradiationDuration)

    def _setSingleSpot(self, x: float, y: float, mu: float, startTime: Optional[float] = None, irradiationDuration: Optional[float] = None):
        alreadyExists, spotPos = self.spotDefinedInXY(x, y)
        if alreadyExists:
            self._x[spotPos] = x
            self._y[spotPos] = y
            self._mu[spotPos] = mu
            if startTime is not None: self._startTime[spotPos] = startTime
            if irradiationDuration is not None: self._irradiationDuration[spotPos] = irradiationDuration
        else:
            self.appendSpot(x, y, mu, startTime, irradiationDuration)

    def removeSpot(self, x: Union[float, Sequence[float]], y: Union[float, Sequence[float]]):
        """
        Removes a spot or multiple spots from the layer.

        Parameters
        ----------
        x: float or Sequence[float]
            x coordinate of the spot(s)
        y: float or Sequence[float]
            y coordinate of the spot(s)
        """
        _, spotPos = self.spotDefinedInXY(x, y)

        self._x = np.delete(self._x, spotPos)
        self._y = np.delete(self._y, spotPos)
        self._mu = np.delete(self._mu, spotPos)
        if len(self._startTime) > 0:
            self._startTime = np.delete(self._startTime, spotPos)
        if len(self._irradiationDuration) > 0:
            self._irradiationDuration = np.delete(self._irradiationDuration, spotPos)

    def spotDefinedInXY(self, x: Union[float, Sequence[float]], y: Union[float, Sequence[float]]) -> Tuple[bool, int]:
        """
        Checks if a spot or multiple spots are defined in the layer.

        Parameters
        ----------
        x: float or Sequence[float]
            x coordinate of the spot(s)
        y: float or Sequence[float]
            y coordinate of the spot(s)

        Returns
        ----------
        exist: bool or Sequence[bool]
            True if the spot(s) exist in the layer, False otherwise
        """
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
            if (np.isclose(x , x_xy, atol=0.1) and np.isclose(y , y_xy, atol=0.1)):
                return (True, i)
        return (False, None)

    def reorderSpots(self, order: Union[str, Sequence[int]] = 'scanAlgo'):
        """
        Reorders the spots in the layer.

        Parameters
        ----------
        order: str or Sequence[int]
            the way the spots are sorted.
            If str, the following options are available:
                - 'scanAlgo': the way scanAlgo sort spots in a serpentine fashion
                - 'timing': sort according to the start time of the spots
            If Sequence[int], the spots a reordered according to the order of the indices

        Raises
        ----------
        ValueError: if the order is not recognized
        """
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
                            order[ind_first_x_at_current_y:ind_last_x_at_current_y+1] = order[
                                                                                      ind_first_x_at_current_y:ind_last_x_at_current_y+1][
                                                                                      ::-1]
                            coord[ind_first_x_at_current_y:ind_last_x_at_current_y+1] = coord[
                                                                                      ind_first_x_at_current_y:ind_last_x_at_current_y+1][
                                                                                      ::-1]

            elif order == 'timing':  # sort spots by increasing order of timings
                assert len(self._startTime) == len(self._mu)
                order = np.argsort(self._startTime)
            else:
                raise ValueError(f"order method type {order} does not exist.")

        # order is a list of the order of the spot irradiated
        # sort all lists according to order
        n = len(order)
        self._x = np.array([self._x[i] for i in order])
        self._y = np.array([self._y[i] for i in order])
        self._mu = np.array([self._mu[i] for i in order])
        if len(self._startTime) == n:
            self._startTime = np.array([self._startTime[i] for i in order])
        if len(self._irradiationDuration) == n:
            self._irradiationDuration = np.array([self._irradiationDuration[i] for i in order])


    def simplify(self, threshold: float = 0.0):
        """
        Simplifies the layer by merging duplicate spots and removing spots with a mu below a threshold.

        Parameters
        ----------
        threshold: float (default: 0.0)
            the threshold below which spots are removed
        """
        self._fusionDuplicates()
        if threshold is not None:
            self.removeZeroMUSpots(threshold)
    
    def removeZeroMUSpots(self, threshold):
        """
        Removes spots with a mu below a threshold.

        Parameters
        ----------
        threshold: float
            the threshold below which spots are removed
        """
        index_to_keep = np.flatnonzero(self._mu > threshold)
        self._mu = np.array([self._mu[i] for i in range(len(self._mu)) if i in index_to_keep])
        self._x = np.array([self._x[i] for i in range(len(self._x)) if i in index_to_keep])
        self._y = np.array([self._y[i] for i in range(len(self._y)) if i in index_to_keep])
        if len(self._startTime) > 0:
            self._startTime = np.array([self._startTime[i] for i in range(len(self._startTime)) if i in index_to_keep])
        if len(self._irradiationDuration) > 0:
            self._irradiationDuration = np.array([self._irradiationDuration[i] for i in range(len(self._irradiationDuration)) if i in index_to_keep])


    def _fusionDuplicates(self):
        """
        Merge spots with the same location.
        """
        if len(self) > 1:
            # If timing is not taken into account (self._startTime is empty), two spots with the same location are considered duplicates
            # If timing is taken into account (self._startTime is not empty), two spots with the same location are considered duplicates only if their timing are equal
            if len(self._startTime)==0:
                unique_positions = np.atleast_2d([self._x[0], self._y[0]])
                ind = 1
                while ind < len(self._x):
                    current_position = np.array([self._x[ind], self._y[ind]])
                    if np.any(np.sum(np.isclose(current_position, unique_positions, atol=0.1), axis=1)==2): # at least one pair is close
                        #fusion
                        match_ind = np.flatnonzero(np.sum(np.isclose(current_position, unique_positions, atol=0.1), axis=1)==2)[0]
                        self._mu[match_ind] += self._mu[ind]
                        self._x = np.delete(self._x, ind)
                        self._y = np.delete(self._y, ind)
                        self._mu = np.delete(self._mu, ind)
                    else:
                        unique_positions = np.vstack((unique_positions, current_position))
                        ind += 1
            else:
                unique_positions = np.atleast_2d([self._x[0], self._y[0], self._startTime[0] / 1000])
                ind = 1
                while ind < len(self._x):
                    current_position = np.array([self._x[ind], self._y[ind], self._startTime[ind] / 1000])
                    if np.any(np.sum(np.isclose(current_position, unique_positions, atol=0.1), axis=1)==3): # at least one pair is close
                        #fusion
                        match_ind = np.flatnonzero(np.sum(np.isclose(current_position, unique_positions, atol=0.1), axis=1)==3)[0]
                        self._mu[match_ind] += self._mu[ind]
                        self._x = np.delete(self._x, ind)
                        self._y = np.delete(self._y, ind)
                        self._mu = np.delete(self._mu, ind)
                        self._startTime = np.delete(self._startTime, ind)
                        if len(self._irradiationDuration) > 0:
                            self._irradiationDuration = np.delete(self._irradiationDuration, ind)
                    else:
                        unique_positions = np.vstack((unique_positions, current_position))
                        ind += 1

    def copy(self):
        return copy.deepcopy(self)

    def createEmptyLayerWithSameMetaData(self):
        """
        Creates an empty layer with the same metadata (e.g. range shifter settings) as the current layer.
        """
        layer = self.copy()
        layer._x = np.array([])
        layer._y = np.array([])
        layer._mu = np.array([])
        layer._startTime = np.array([])
        layer._irradiationDuration = np.array([])
        return layer


class RangeShifterSettings:
    """
    Class to store range shifter settings.

    Parameters
    -----------
    isocenterToRangeShifterDistance: float (default: 0.0)
        distance from isocenter to range shifter
    rangeShifterWaterEquivalentThickness: float
        water equivalent thickness of the range shifter
    rangeShifterSetting: str (default: 'OUT')
    referencedRangeShifterNumber: int (default: 0)
        referenced range shifter number
    """
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
        layer = PlanProtonLayer()

        x = 0
        y = 0
        mu = 0
        layer.appendSpot(x, y, mu)

        np.testing.assert_array_equal(list(layer.spotXY), [(x, y)])
        np.testing.assert_array_equal(layer.spotMUs, [0])

        self.assertRaises(Exception, lambda: layer.appendSpot(x, y, mu))

    def testAppendSpotWithTiming(self):
        layer = PlanProtonLayer()

        x = 0
        y = 0
        mu = 0
        startTime = 0
        layer.appendSpot(x, y, mu, startTime)

        np.testing.assert_array_equal(list(layer.spotXY), [(x, y)])
        np.testing.assert_array_equal(layer.spotMUs, [0])
        np.testing.assert_array_equal(layer.spotTimings, [0])

        self.assertRaises(Exception, lambda: layer.appendSpot(x, y, mu, startTime))

    def testSetSpot(self):
        layer = PlanProtonLayer()

        x = 0
        y = 0
        mu = 0

        layer.setSpot(x, y, mu)
        np.testing.assert_array_equal(list(layer.spotXY), [(x, y)])
        np.testing.assert_array_equal(layer.spotMUs, [0])

        layer.setSpot(x, y, mu)
        np.testing.assert_array_equal(list(layer.spotXY), [(x, y)])
        np.testing.assert_array_equal(layer.spotMUs, [0])

    def testSetSpotWithTiming(self):
        layer = PlanProtonLayer()

        x = 0
        y = 0
        mu = 0
        startTime = 0

        layer.setSpot(x, y, mu, startTime)
        np.testing.assert_array_equal(list(layer.spotXY), [(x, y)])
        np.testing.assert_array_equal(layer.spotMUs, [0])
        np.testing.assert_array_equal(layer.spotTimings, [0])

        layer.setSpot(x, y, mu)
        np.testing.assert_array_equal(list(layer.spotXY), [(x, y)])
        np.testing.assert_array_equal(layer.spotMUs, [0])
        np.testing.assert_array_equal(layer.spotTimings, [0])

    def testRemoveSpot(self):
        layer = PlanProtonLayer()

        x = 0
        y = 0
        mu = 0
        startTime = 0

        layer.setSpot(x, y, mu, startTime)
        np.testing.assert_array_equal(list(layer.spotXY), [(x, y)])
        np.testing.assert_array_equal(layer.spotMUs, [0])
        np.testing.assert_array_equal(layer.spotTimings, [0])

        layer.removeSpot(x, y)

        self.assertEqual(list(layer.spotXY), [])
        np.testing.assert_array_equal(layer.spotMUs, np.array([]))
        np.testing.assert_array_equal(layer.spotTimings, np.array([]))

        layer.setSpot(x, y, mu, startTime)
        np.testing.assert_array_equal(list(layer.spotXY), [(x, y)])
        np.testing.assert_array_equal(layer.spotMUs, [0])
        np.testing.assert_array_equal(layer.spotTimings, [0])

    def testSpotDefinedInXY(self):
        layer = PlanProtonLayer()

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
        layer = PlanProtonLayer()
        x = [0, 2, 1, 3]
        y = [1, 2, 2, 0]
        mu = [0.2, 0.5, 0.3, 0.1]

        layer.appendSpot(x, y, mu)
        layer.reorderSpots(order='scanAlgo')
        np.testing.assert_array_equal(layer.spotX, [3, 0, 1, 2])
        np.testing.assert_array_equal(layer.spotY, [0, 1, 2, 2])
        np.testing.assert_array_almost_equal(layer.spotMUs, np.array([0.1, 0.2, 0.3, 0.5]))

        layer = PlanProtonLayer()
        x = [0, 1, 2, 3]
        y = [1, 2, 2, 0]
        mu = [0.2, 0.5, 0.3, 0.1]
        startTime = [3, 2, 5, 6]
        layer.appendSpot(x, y, mu, startTime)
        layer.reorderSpots(order='timing')
        np.testing.assert_array_equal(layer.spotX, [1, 0, 2, 3])
        np.testing.assert_array_equal(layer.spotY, [2, 1, 2, 0])
        np.testing.assert_array_almost_equal(layer.spotMUs, np.array([0.5, 0.2, 0.3, 0.1]))
        np.testing.assert_array_almost_equal(layer.spotTimings, np.array([2, 3, 5, 6]))

    def testFusionDuplicates(self):
        layer = PlanProtonLayer(nominalEnergy=100.)
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

        layer = PlanProtonLayer(nominalEnergy=100.)
        x = [0, 2, 1, 3, 10, 4]
        y = [1, 2, 2, 0, 2, 5]
        mu = [0.2, 0.5, 0.3, 0.1, 0.2, 0.4]
        startTimes = [1, 2, 3, 4, 2, 6]
        layer.appendSpot(x, y, mu, startTimes)
        layer._x[4] = 2

        layer._fusionDuplicates()
        self.assertEqual(len(layer._x),5)
        np.testing.assert_array_equal(layer.spotX, np.array([0, 2, 1, 3, 4]))
        np.testing.assert_array_equal(layer.spotY, np.array([1, 2, 2, 0, 5]))
        np.testing.assert_array_equal(layer.spotMUs, np.array([0.2, 0.7, 0.3, 0.1, 0.4]))
        np.testing.assert_array_almost_equal(layer.spotTimings, np.array([1, 2, 3, 4, 6]))

        layer = PlanProtonLayer(nominalEnergy=100.)
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
