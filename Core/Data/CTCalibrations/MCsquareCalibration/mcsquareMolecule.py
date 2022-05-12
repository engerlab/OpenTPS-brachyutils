import os
import re

from Core.Data.CTCalibrations.MCsquareCalibration.G4StopPow import G4StopPow
from Core.Data.CTCalibrations.MCsquareCalibration.mcsquareElement import MCsquareElement
from Core.Data.CTCalibrations.MCsquareCalibration.mcsquareMaterial import MCsquareMaterial


class MCsquareMolecule(MCsquareMaterial):
    def __init__(self, density=0.0, electronDensity=0.0, name=None, number=0, sp=None, radiationLength=0.0, MCsquareElements=None, weights=None):
        super().__init__(density=density, electronDensity=electronDensity, name=name, number=number, sp=sp, radiationLength=radiationLength)
        self.MCsquareElements = MCsquareElements
        self.weights = weights

    def __str__(self):
        return self.mcsquareFormatted()

    def mcsquareFormatted(self, materialNamesOrderedForPrinting):
        s = 'Name ' + self.name + '\n'
        s += 'Molecular_Weight 	0.0 		 # N.C.\n'
        s += 'Density ' + str(self.density) + " # in g/cm3 \n"
        electronDensity = self.electronDensity if self.electronDensity > 0. else 1e-4
        s += 'Electron_Density ' + str(electronDensity) + " # in cm-3 \n"
        s += 'Radiation_Length ' + str(self.radiationLength) + " # in g/cm2 \n"
        s += 'Nuclear_Data 		Mixture ' + str(len(self.weights)) + ' # mixture with ' + str(len(self.weights)) + ' components \n'
        s += '# 	Label 	Name 		fraction by mass (in %)\n'

        for i, element in enumerate(self.MCsquareElements):
            nb = materialNamesOrderedForPrinting.index(element.name) + 1
            s += 'Mixture_Component ' + str(nb) + ' ' + element.name + ' ' + str(self.weights[i]) + '\n'

        return s

    def load(self, materialNb, materialsPath='default'):
        moleculePath = MCsquareMaterial.getFolderFromMaterialNumber(materialNb, materialsPath)

        self.number = materialNb
        self.MCsquareElements = []
        self.weights = []

        with open(os.path.join(moleculePath, 'Material_Properties.dat'), "r") as f:
            for line in f:
                if re.search(r'Name', line):
                    line = line.split()
                    if line[0]=='#':
                        continue

                    self.name = line[1]
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

                if re.search(r'Mixture_Component', line):
                    line = line.split()

                    element = MCsquareElement()
                    element.load(int(line[1]), materialsPath)

                    self.MCsquareElements.append(element)
                    self.weights.append(float(line[3]))

                    continue

                if re.search(r'Atomic_Weight', line):
                    raise ValueError(moleculePath + ' is an element not a molecule.')

        self.sp = G4StopPow(fromFile=os.path.join(moleculePath, 'G4_Stop_Pow.dat'))
        self.pstarSP = G4StopPow(fromFile=os.path.join(moleculePath, 'PSTAR_Stop_Pow.dat'))
