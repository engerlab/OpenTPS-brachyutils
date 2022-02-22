import os.path

import numpy as np
from scipy import interpolate

from Core.Data.Plan.rangeShifter import RangeShifter


class BDL:
    def __init__(self, bdlPath=None):
        self._path = bdlPath

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

        if not(self._path is None):
            self._load(self._path)

    def __str__(self):
        return self.mcsquareFormatted()

    def mcsquareFormatted(self):
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

    def computeMU2Protons(self, energy):
        f = interpolate.interp1d(self.NominalEnergy, self.ProtonsMU, kind='linear', fill_value='extrapolate')
        return f(energy)

    def computeSpotSizes(self, energy):
        sigmaX = interpolate.interp1d(self.NominalEnergy, self.SpotSize1x, kind='linear', fill_value='extrapolate')
        sigmaX = sigmaX(energy)
        sigmaY = interpolate.interp1d(self.NominalEnergy, self.SpotSize1y, kind='linear', fill_value='extrapolate')
        sigmaY = sigmaY(energy)

        return (sigmaX, sigmaY)

    def _load(self, path):
        with open(path, 'r') as fid:
            # verify BDL format
            line = fid.readline()
            fid.seek(0)
            if not "--UPenn beam model (double gaussian)--" in line and not "--Lookup table BDL format--" in line:
                fid.close()
                raise("BDL format not supported")

            line_num = -1
            readNIDist = False
            smx = False
            smy = False
            for line in fid:
                line_num += 1

                # remove comments
                if line[0] == '#': continue
                line = line.split('#')[0]

                if "Nozzle exit to Isocenter distance" in line:
                    readNIDist = True
                    continue
                if readNIDist:
                    line = line.split()
                    self.nozzle_isocenter = float(line[0])
                    readNIDist = False
                    continue

                if "SMX" in line:
                    smx = True
                    continue
                if smx:
                    line = line.split()
                    self.smx = float(line[0])
                    smx = False
                    continue

                if "SMY" in line:
                    smy = True
                    continue
                if smy:
                    line = line.split()
                    self.smy = float(line[0])
                    smy = False
                    continue


                # find begining of the BDL table in the file
                if ("NominalEnergy" in line): table_line = line_num + 1

                # parse range shifter data
                if ("Range Shifter parameters" in line):
                    RS = RangeShifter()
                    self.RangeShifters.append(RS)

                if ("RS_ID" in line):
                    line = line.split('=')
                    value = line[1].replace('\r', '').replace('\n', '').replace('\t', '').replace(' ', '')
                    self.RangeShifters[-1].ID = value

                if ("RS_type" in line):
                    line = line.split('=')
                    value = line[1].replace('\r', '').replace('\n', '').replace('\t', '').replace(' ', '')
                    self.RangeShifters[-1].type = value.lower()

                if ("RS_material" in line):
                    line = line.split('=')
                    value = line[1].replace('\r', '').replace('\n', '').replace('\t', '').replace(' ', '')
                    self.RangeShifters[-1].material = int(value)

                if ("RS_density" in line):
                    line = line.split('=')
                    value = line[1].replace('\r', '').replace('\n', '').replace('\t', '').replace(' ', '')
                    self.RangeShifters[-1].density = float(value)

                if ("RS_WET" in line):
                    line = line.split('=')
                    value = line[1].replace('\r', '').replace('\n', '').replace('\t', '').replace(' ', '')
                    self.RangeShifters[-1].WET = float(value)

        # parse BDL table
        BDL_table = np.loadtxt(path, skiprows=table_line)

        self.NominalEnergy = BDL_table[:, 0]
        self.MeanEnergy = BDL_table[:, 1]
        self.EnergySpread = BDL_table[:, 2]
        self.ProtonsMU = BDL_table[:, 3]
        self.Weight1 = BDL_table[:, 4]
        self.SpotSize1x = BDL_table[:, 5]
        self.Divergence1x = BDL_table[:, 6]
        self.Correlation1x = BDL_table[:, 7]
        self.SpotSize1y = BDL_table[:, 8]
        self.Divergence1y = BDL_table[:, 9]
        self.Correlation1y = BDL_table[:, 10]
        self.Weight2 = BDL_table[:, 11]
        self.SpotSize2x = BDL_table[:, 12]
        self.Divergence2x = BDL_table[:, 13]
        self.Correlation2x = BDL_table[:, 14]
        self.SpotSize2y = BDL_table[:, 15]
        self.Divergence2y = BDL_table[:, 16]
        self.Correlation2y = BDL_table[:, 17]

    def write(self, fileName):
        with open(fileName, 'w') as f:
            f.write(str(self))

if __name__ == '__main__':
    import MCsquare.BDL as BDLModule
    bdl = BDL(bdlPath = os.path.join(str(BDLModule.__path__[0]), 'BDL_default_DN_RangeShifter.txt'))

    print(bdl)
