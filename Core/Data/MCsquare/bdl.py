import os.path

from scipy import interpolate


class BDL:
    def __init__(self):
        self.nozzle_isocenter = 0.0
        self.smx = 0.0
        self.smy = 0.0
        self.NominalEnergy = []
        self.MeanEnergy = []
        self.EnergySpread = []
        self.ProtonsMU = []
        self.Weight1 = []
        self.SpotSize1x = []
        self.Divergence1x = []
        self.Correlation1x = []
        self.SpotSize1y = []
        self.Divergence1y = []
        self.Correlation1y = []
        self.Weight2 = []
        self.SpotSize2x = []
        self.Divergence2x = []
        self.Correlation2x = []
        self.SpotSize2y = []
        self.Divergence2y = []
        self.Correlation2y = []
        self.RangeShifters = []

    def __str__(self):
        return self.mcsquareFormatted()

    def mcsquareFormatted(self) -> str:
        s = '--UPenn beam model (double gaussian)--\n\n'
        s += 'Nozzle exit to Isocenter distance\n'
        s += str(self.nozzle_isocenter) + '\n\n'
        s += 'SMX to Isocenter distance\n'
        s += str(self.smx) + '\n\n'
        s += 'SMY to Isocenter distance\n'
        s += str(self.smy) + '\n\n'

        #if len(self.RangeShifters)>0:
        #    raise ValueError('RS not supported yet')

        s += 'Beam parameters\n'
        s += str(len(self.NominalEnergy)) + ' energies\n\n'
        s += 'NominalEnergy 	 MeanEnergy 	 EnergySpread 	 ProtonsMU 	 Weight1 	 SpotSize1x 	 Divergence1x 	 Correlation1x 	 SpotSize1y 	 Divergence1y 	 Correlation1y 	 Weight2 	 SpotSize2x 	 Divergence2x 	 Correlation2x 	 SpotSize2y 	 Divergence2y 	 Correlation2y\n'
        for i, energy in enumerate(self.NominalEnergy):
            s += str(self.NominalEnergy[i]) + ' '
            s += str(self.MeanEnergy[i]) + ' '
            s += str(self.EnergySpread[i]) + ' '
            s += str(self.ProtonsMU[i]) + ' '
            s += str(self.Weight1[i]) + ' '
            s += str(self.SpotSize1x[i]) + ' '
            s += str(self.Divergence1x[i]) + ' '
            s += str(self.Correlation1x[i]) + ' '
            s += str(self.SpotSize1y[i]) + ' '
            s += str(self.Divergence1y[i]) + ' '
            s += str(self.Correlation1y[i]) + ' '
            s += str(self.Weight2[i]) + ' '
            s += str(self.SpotSize2x[i]) + ' '
            s += str(self.Divergence2x[i]) + ' '
            s += str(self.Correlation2x[i]) + ' '
            s += str(self.SpotSize2y[i]) + ' '
            s += str(self.Divergence2y[i]) + ' '
            s += str(self.Correlation2y[i]) + ' '
            s += '\n'

        return s

    def computeMU2Protons(self, energy: float) -> float:
        f = interpolate.interp1d(self.NominalEnergy, self.ProtonsMU, kind='linear', fill_value='extrapolate')
        return f(energy)

    def computeSpotSizes(self, energy: float) -> tuple[float, float]:
        sigmaX = interpolate.interp1d(self.NominalEnergy, self.SpotSize1x, kind='linear', fill_value='extrapolate')
        sigmaX = sigmaX(energy)
        sigmaY = interpolate.interp1d(self.NominalEnergy, self.SpotSize1y, kind='linear', fill_value='extrapolate')
        sigmaY = sigmaY(energy)

        return (sigmaX, sigmaY)
