import os

import numpy as np

from Data.CTCalibration.MCsquareCalibration.MCSquareMolecule import MCSquareMolecule


class MCSquareHU2Material:
    def __init__(self, piecewiseTable=(None, None), fromFile=(None, 'default')):
        self.__hu = piecewiseTable[0]
        self.__materials = piecewiseTable[1]

        if not (fromFile[0] is None):
            self.__load(fromFile[0], materialsPath=fromFile[1])

    def __str__(self):
        s = ''
        for i, hu in enumerate(self.__hu):
            s += 'HU: ' + str(hu) + '\n'
            s += str(self.__materials[i]) + '\n'

        return s

    def getTableString(self):
        s = ''
        for i, hu in enumerate(self.__hu):
            s += str(hu) + ' ' + str(self.__materials[i].number) + '\n'

        return s

    def __load(self, materialFile, materialsPath='default'):
        self.__hu = []
        self.__materials = []

        with open(materialFile, "r") as file:
            for line in file:
                lineSplit = line.split()
                if len(lineSplit)<=0:
                    continue

                if lineSplit[0] == '#':
                    continue

                # else
                if len(lineSplit) > 1:
                    self.__hu.append(float(lineSplit[0]))

                    material = MCSquareMolecule()
                    material.load(int(lineSplit[1]), materialsPath)
                    self.__materials.append(material)

    def write(self, folderPath, huMaterialFile):
        listPath = os.path.join(folderPath, 'list.dat')

        with open(huMaterialFile, 'w') as f:
            f.write(self.getTableString())

        for material in self.__materials:
            material.write(folderPath)

        # lsit.dat file
        elementNbs = []
        elementObjs = []
        for material in self.__materials:
            elementObjs.append(material)
            elementNbs.append(material.number)

            elements = material.MCsquareElements
            for element in elements:
                if element.number in elementNbs:
                    pass
                elementObjs.append(element)
                elementNbs.append(element.number)

        elementNbs = np.array(elementNbs)
        _, ind = np.unique(elementNbs, return_index=True)

        with open(listPath, 'w') as f:
            for i in ind:
                f.write(str(elementNbs[i]) + ' ' + elementObjs[i].name + '\n')
