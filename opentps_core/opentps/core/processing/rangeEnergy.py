from math import exp, log
from typing import Union

import numpy as np


def rangeToEnergy(r80: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """
    This function converts the water equivalent range (defined as r80,
    i.e., the position of the 80% dose in the distal falloff, in cm) to incident
    energy of the proton beam (in MeV).

    The formula comes from Loic Grevillot
    et al. [1, 2], from a fitting to the NIST/ICRU database.

    [1] L. Grevillot, et al. "A Monte Carlo pencil beam scanning model for
    proton treatment plan simulation using GATE/GEANT4."
    Phys Med Biol, 56(16):5203–5219, Aug 2011.
    [2] L. Grevillot, et al. "Optimization of geant4 settings for proton
    pencil beam scanning simulations using gate". Nuclear Instruments and
    Methods in Physics Research Section B: Beam Interactions
    with Materials and Atoms, 268(20):3295 – 3305, 2010.

    Parameters
    ----------
    r80 : float
        r80 in cm.

    Returns
    -------
    energy : float
        Energy in MeV.
    """

    #r80 /= 10  # mm -> cm

    if isinstance(r80, np.ndarray):
        r80[r80 < 1.] = 1.
        return np.exp(
            3.464048 + 0.561372013 * np.log(r80) - 0.004900892 * np.log(r80) * np.log(r80) + 0.001684756748 * np.log(
                r80) * np.log(r80) * np.log(r80))

    if r80 <= 0.0:
        return 0
    else:
        return exp(
            3.464048 + 0.561372013 * log(r80) - 0.004900892 * log(r80) * log(r80) + 0.001684756748 * log(r80) * log(
                r80) * log(r80))

def rangeMMToEnergy(r80: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """
    This function converts the water equivalent range (defined as r80,
    i.e., the position of the 80% dose in the distal falloff, in mm) to incident
    energy of the proton beam (in MeV).

    It uses the function rangeToEnergy, but converts the input and output to mm.

    Parameters
    ----------
    r80 : float
        r80 in mm.

    Returns
    -------
    energy : float
        Energy in MeV.
    """
    return rangeToEnergy(r80/10.)

def energyToRange(energy: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """
    This function converts a proton beam energy (in MeV) to a water equivalent range (defined as r80,
    i.e., the position of the 80% dose in the distal falloff, in cm).

    The formula comes from Loic Grevillot
    et al. [1, 2], from a fitting to the NIST/ICRU database.

    [1] L. Grevillot, et al. "A Monte Carlo pencil beam scanning model for
    proton treatment plan simulation using GATE/GEANT4."
    Phys Med Biol, 56(16):5203–5219, Aug 2011.
    [2] L. Grevillot, et al. "Optimization of geant4 settings for proton
    pencil beam scanning simulations using gate". Nuclear Instruments and
    Methods in Physics Research Section B: Beam Interactions
    with Materials and Atoms, 268(20):3295 – 3305, 2010.

    Parameters
    ----------
    energy : float
        Energy in MeV.

    Returns
    -------
    r80 : float
        r80 in cm.
    """

    if isinstance(energy, np.ndarray):
        energy[energy < 1.] = 1.
        r80 = np.exp(-5.5064 + 1.2193 * np.log(energy) + 0.15248 * np.log(energy) * np.log(energy) - 0.013296 * np.log(
            energy) * np.log(energy) * np.log(energy))
    elif energy <= 0.0:
        r80 = 0
    else:
        r80 = exp(-5.5064 + 1.2193 * log(energy) + 0.15248 * log(energy) * log(energy) - 0.013296 * log(energy) * log(
            energy) * log(energy))

    return r80

def energyToRangeMM(energy: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """
    This function converts a proton beam energy (in MeV) to a water equivalent range (defined as r80,
    i.e., the position of the 80% dose in the distal falloff, in mm).

    It uses the function energyToRange, but converts the input and output to mm.

    Parameters
    ----------
    energy : float
        Energy in MeV.

    Returns
    -------
    r80 : float
        r80 in mm.
    """
    return energyToRange(energy)*10.
