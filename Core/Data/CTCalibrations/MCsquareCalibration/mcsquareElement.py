import os
import re

from Core.Data.CTCalibrations.MCsquareCalibration.G4StopPow import G4StopPow
from Core.Data.CTCalibrations.MCsquareCalibration.mcsquareMaterial import MCsquareMaterial


class MCsquareElement(MCsquareMaterial):
    def __init__(self, density=0.0, electronDensity=0.0, name=None, number=0, sp=None, radiationLength=0.0, atomicWeight=0.0):
        super().__init__(density=density, electronDensity=electronDensity, name=name, number=number, sp=sp, radiationLength=radiationLength)

        self.atomicWeight = atomicWeight
        self._nuclear_data = ""
        self._nuclearElasticData = None
        self._nuclearInelasticData = None

    def __str__(self):
        return self.mcsquareFormatted()

    def mcsquareFormatted(self, materialNamesOrderedForPrinting=None):
        if self.density<=0:
            self.density = 1e-18

        if self.electronDensity<=0:
            self.electronDensity = 1e-18

        s = 'Name ' + self.name + '\n'
        s += 'Atomic_Weight ' + str(self.atomicWeight) + '\n'
        s += 'Density ' + str(self.density) + " # in g/cm3 \n"
        s += 'Electron_Density ' + str(self.electronDensity) + " # in cm-3 \n"
        s += 'Radiation_Length ' + str(self.radiationLength) + " # in g/cm2 \n"
        s += 'Nuclear_Data ' + self._nuclear_data + '\n'

        return s

    def load(self, materialNb, materialsPath='default'):
        elementPath = MCsquareMaterial.getFolderFromMaterialNumber(materialNb, materialsPath)

        self.number = materialNb
        self.MCsquareElements = []
        self.weights = []

        with open(os.path.join(elementPath, 'Material_Properties.dat'), "r") as f:
            for line in f:
                if re.search(r'Name', line):
                    line = line.split()
                    self.name = line[1]
                    continue

                if re.search(r'Atomic_Weight', line):
                    line = line.split()
                    self.atomicWeight = float(line[1])
                    continue

                if re.search(r'Electron_Density', line):
                    line = line.split()
                    self.electronDensity = float(line[1])
                    continue
                elif re.search(r'Density', line):
                    line = line.split()
                    self.density = float(line[1])
                    continue

                if re.search(r'Radiation_Length', line):
                    line = line.split()
                    self.radiationLength = float(line[1])
                    continue

                if re.search(r'Nuclear_Data', line):
                    if 'ICRU' in line:
                        self._nuclear_data = 'ICRU'

                        file = open(os.path.join(elementPath, 'ICRU_Nuclear_elastic.dat'), mode='r')
                        self._nuclearElasticData = file.read()
                        file.close()

                        file = open(os.path.join(elementPath, 'ICRU_Nuclear_inelastic.dat'), mode='r')
                        self._nuclearInelasticData = file.read()
                        file.close()
                    else:
                        self._nuclear_data = 'proton-proton'

                if re.search(r'Mixture_Component', line):
                    raise ValueError(elementPath + ' is a molecule not an element.')



        self.sp = G4StopPow(fromFile=os.path.join(elementPath, 'G4_Stop_Pow.dat'))
        self.pstarSP = G4StopPow(fromFile=os.path.join(elementPath, 'PSTAR_Stop_Pow.dat'))

    def write(self, folderPath, materialNamesOrderedForPrinting):
        super().write(folderPath, materialNamesOrderedForPrinting)

        if 'ICRU' in self._nuclear_data:
            with open(os.path.join(folderPath, 'ICRU_Nuclear_elastic.dat')) as f:
                f.write(self._nuclearElasticData)

            with open(os.path.join(folderPath, 'ICRU_Nuclear_inelastic.dat')) as f:
                f.write(self._nuclearInelasticData)
