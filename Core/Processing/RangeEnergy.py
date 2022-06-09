from math import exp, log
from typing import Union

import numpy as np


def rangeToEnergy(r80: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    r80 /= 10  # mm -> cm

    if isinstance(r80, np.ndarray):
        r80[r80 < 1.] = 1.
        return np.exp(
            3.464048 + 0.561372013 * np.log(r80) - 0.004900892 * np.log(r80) * np.log(r80) + 0.001684756748 * np.log(
                r80) * np.log(r80) * np.log(r80))

    if r80 <= 1.:
        return 0
    else:
        return exp(
            3.464048 + 0.561372013 * log(r80) - 0.004900892 * log(r80) * log(r80) + 0.001684756748 * log(r80) * log(
                r80) * log(r80))


def energyToRange(energy: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    if isinstance(energy, np.ndarray):
        energy[energy < 1.] = 1.
        r80 = np.exp(-5.5064 + 1.2193 * np.log(energy) + 0.15248 * np.log(energy) * np.log(energy) - 0.013296 * np.log(
            energy) * np.log(energy) * np.log(energy))
    elif energy <= 1:
        r80 = 0
    else:
        r80 = exp(-5.5064 + 1.2193 * log(energy) + 0.15248 * log(energy) * log(energy) - 0.013296 * log(energy) * log(
            energy) * log(energy))

    return r80 * 10
