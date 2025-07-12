import numpy as np

from opentps.core.data.MCsquare._bdl import BDL


class BDLWithSpotTilt(BDL):
    def __init__(self):
        BDL.__init__(self)

        self.SpotTilt = 0

    def _load(self, path):
        BDL._load(self, path)

        with open(path, 'r') as fid:
            with open(path, 'r') as fid:
                # verify BDL format
                line = fid.readline()
                fid.seek(0)
                if not "--UPenn beam model (double gaussian)--" in line and not "--Lookup table BDL format--" in line:
                    fid.close()
                    raise ("BDL format not supported")

                line_num = -1
                for line in fid:
                    line_num += 1

                    # remove comments
                    if line[0] == '#': continue
                    line = line.split('#')[0]

                    # find begining of the BDL table in the file
                    if ("NominalEnergy" in line): table_line = line_num + 1

                    # parse BDL table
                BDL_table = np.loadtxt(path, skiprows=table_line)

                self.SpotTilt = BDL_table[:, 18]
