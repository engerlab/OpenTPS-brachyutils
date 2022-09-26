import os
from abc import abstractmethod

import opentps.core.processing.doseCalculation.MCsquare as MCsquare

class MCsquareMaterial:
    def __init__(self, density=0.0, electronDensity=0.0, name=None, number=0, sp=None, radiationLength=0.0):
        self.density = density
        self.electronDensity = electronDensity
        self.name = name
        self.number = number
        self.sp = sp
        self.pstarSP = None
        self.radiationLength = radiationLength

    @abstractmethod
    def mcsquareFormatted(self, materialsOrderedForPrinting):
        raise NotImplementedError()

    @staticmethod
    def getMaterialList(materialsPath='default'):
        matList = []

        if materialsPath=='default':
            materialsPath = os.path.join(str(MCsquare.__path__[0]), 'Materials')

        listPath = os.path.join(materialsPath, 'list.dat')

        with open(listPath, "r") as file:
            for line in file:
                lineSplit = line.split()

                if len(lineSplit)<2:
                    continue

                matList.append({"ID": int(lineSplit[0]), "name": lineSplit[1]})

        return matList

    @staticmethod
    def getFolderFromMaterialNumber(materialNumber, materialsPath='default'):
        if materialsPath=='default':
            materialsPath = os.path.join(str(MCsquare.__path__[0]), 'Materials')

        listPath = os.path.join(materialsPath, 'list.dat')

        with open(listPath, "r") as file:
            for line in file:
                lineSplit = line.split()

                if len(lineSplit)<2:
                    continue

                if materialNumber==int(lineSplit[0]):
                    return os.path.join(materialsPath, lineSplit[1])

        return None

    @staticmethod
    def getMaterialNumbers(materialsPath='default'):
        if materialsPath=='default':
            materialsPath = os.path.join(str(MCsquare.__path__[0]), 'Materials')

        listPath = os.path.join(materialsPath, 'list.dat')

        materialNumbers = []
        with open(listPath, "r") as file:
            for line in file:
                lineSplit = line.split()

                if len(lineSplit)<2:
                    continue

                materialNumbers.append(int(lineSplit[0]))

        return materialNumbers

    def write(self, folderPath, materialNamesOrderedForPrinting):
        folderPath = os.path.join(folderPath, self.name)
        propertiesFile = os.path.join(folderPath, 'Material_Properties.dat')
        spFile = os.path.join(folderPath, 'G4_Stop_Pow.dat')
        spFilePSTAR = os.path.join(folderPath, 'PSTAR_Stop_Pow.dat')

        os.makedirs(folderPath, exist_ok=True)

        with open(propertiesFile, 'w') as f:
            f.write(self.mcsquareFormatted(materialNamesOrderedForPrinting))

        self.sp.write(spFile)
        if not (self.pstarSP is None):
            self.pstarSP.write(spFilePSTAR)
