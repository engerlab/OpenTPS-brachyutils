
__all__ = ['BDL']


from typing import Tuple, Optional, Sequence

import numpy as np
from scipy import interpolate

from opentps.core.data.CTCalibrations.MCsquareCalibration._mcsquareMaterial import MCsquareMaterial


class BDL:
    def __init__(self):
        self.nozzle_isocenter = 0.0
        self.smx = 0.0
        self.smy = 0.0
        self.isLoaded = 0
        self.nominalEnergy = []
        self.meanEnergy = []
        self.energySpread = []
        self.protonsMU = []
        self.weight1 = []
        self.spotSize1x = []
        self.divergence1x = []
        self.correlation1x = []
        self.spotSize1y = []
        self.divergence1y = []
        self.correlation1y = []
        self.weight2 = []
        self.spotSize2x = []
        self.divergence2x = []
        self.correlation2x = []
        self.spotSize2y = []
        self.divergence2y = []
        self.correlation2y = []
        self.rangeShifters = []

    def __str__(self):
        return self.mcsquareFormatted()

    def mcsquareFormatted(self, materials:Optional[Sequence[MCsquareMaterial]]=None) -> str:
        s = '--UPenn beam model (double gaussian)--\n\n'
        s += 'Nozzle exit to Isocenter distance\n'
        s += str(self.nozzle_isocenter) + '\n\n'
        s += 'SMX to Isocenter distance\n'
        s += str(self.smx) + '\n\n'
        s += 'SMY to Isocenter distance\n'
        s += str(self.smy) + '\n\n'

        if len(self.rangeShifters) >0:
            s += 'Range Shifter parameters\n'
            for RS in self.rangeShifters:
                s += RS.mcsquareFormatted(materials)
            s += '\n'

        s += 'Beam parameters\n'
        s += str(len(self.nominalEnergy)) + ' energies\n\n'
        s += 'NominalEnergy 	 MeanEnergy 	 EnergySpread 	 ProtonsMU 	 Weight1 	 SpotSize1x 	 Divergence1x 	 Correlation1x 	 SpotSize1y 	 Divergence1y 	 Correlation1y 	 Weight2 	 SpotSize2x 	 Divergence2x 	 Correlation2x 	 SpotSize2y 	 Divergence2y 	 Correlation2y\n'
        for i, energy in enumerate(self.nominalEnergy):
            s += str(self.nominalEnergy[i]) + ' '
            s += str(self.meanEnergy[i]) + ' '
            s += str(self.energySpread[i]) + ' '
            s += str(self.protonsMU[i]) + ' '
            s += str(self.weight1[i]) + ' '
            s += str(self.spotSize1x[i]) + ' '
            s += str(self.divergence1x[i]) + ' '
            s += str(self.correlation1x[i]) + ' '
            s += str(self.spotSize1y[i]) + ' '
            s += str(self.divergence1y[i]) + ' '
            s += str(self.correlation1y[i]) + ' '
            s += str(self.weight2[i]) + ' '
            s += str(self.spotSize2x[i]) + ' '
            s += str(self.divergence2x[i]) + ' '
            s += str(self.correlation2x[i]) + ' '
            s += str(self.spotSize2y[i]) + ' '
            s += str(self.divergence2y[i]) + ' '
            s += str(self.correlation2y[i]) + ' '
            s += '\n'

        return s

    def computeMU2Protons(self, energy:float) -> float:
        return np.interp(energy, self.nominalEnergy, self.protonsMU)
        #if = interpolate.interp1d(self.NominalEnergy, self.ProtonsMU, kind='linear', fill_value='extrapolate')
        #return f(energy)

    def correlations(self, energy:float) -> Tuple[float, float]:
        correlationX = interpolate.interp1d(self.nominalEnergy, self.correlation1x, kind='linear', fill_value='extrapolate')
        correlationX = correlationX(energy)
        correlationY = interpolate.interp1d(self.nominalEnergy, self.correlation1y, kind='linear', fill_value='extrapolate')
        correlationY = correlationY(energy)

        return (correlationX, correlationY)

    def divergences(self, energy:float) -> Tuple[float, float]:
        divergenceX = interpolate.interp1d(self.nominalEnergy, self.divergence1x, kind='linear', fill_value='extrapolate')
        divergenceX = divergenceX(energy)
        divergenceY = interpolate.interp1d(self.nominalEnergy, self.divergence1y, kind='linear', fill_value='extrapolate')
        divergenceY = divergenceY(energy)

        return (divergenceX, divergenceY)

    def spotSizes(self, energy:float) -> Tuple[float, float]:
        sigmaX = interpolate.interp1d(self.nominalEnergy, self.spotSize1x, kind='linear', fill_value='extrapolate')
        sigmaX = sigmaX(energy)
        sigmaY = interpolate.interp1d(self.nominalEnergy, self.spotSize1y, kind='linear', fill_value='extrapolate')
        sigmaY = sigmaY(energy)

        return (sigmaX, sigmaY)
