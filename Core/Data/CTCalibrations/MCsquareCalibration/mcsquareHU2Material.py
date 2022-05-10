import logging
import os

import numpy as np

from Core.Data.CTCalibrations.MCsquareCalibration.mcsquareMolecule import MCsquareMolecule


class MCsquareHU2Material:
    def __init__(self, piecewiseTable=(None, None), fromFile=(None, 'default')):
        self.__hu = piecewiseTable[0]
        self.__materials = piecewiseTable[1]

        if not (fromFile[0] is None):
            self.__load(fromFile[0], materialsPath=fromFile[1])

    def __str__(self):
        return self.mcsquareFormatted()

    def mcsquareFormatted(self):
        materialsOrderedForPrinting = self.materialsOrderedForPrinting()
        matNames = [mat.name for mat in materialsOrderedForPrinting]

        s = ''
        for i, hu in enumerate(self.__hu):
            s += 'HU: ' + str(hu) + '\n'
            s += self.__materials[i].mcsquareFormatted(matNames) + '\n'

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

                    material = MCsquareMolecule()
                    material.load(int(lineSplit[1]), materialsPath)
                    self.__materials.append(material)

    def write(self, folderPath, huMaterialFile):
        self._writeHU2MaterialFile(huMaterialFile)
        self._writeMaterials(folderPath)
        self._writeMCsquareList(os.path.join(folderPath, 'list.dat'))

    def _writeHU2MaterialFile(self, huMaterialFile):
        printedMaterials = self.materialsOrderedForPrinting()

        with open(huMaterialFile, 'w') as f:
            for i, hu in enumerate(self.__hu):
                s = str(hu) + ' ' + str(printedMaterials.index(self.__materials[i])+1) + '\n'
                f.write(s)

    def _writeMaterials(self, folderPath):
        materialsOrderedForPrinting = self.materialsOrderedForPrinting()
        matNames = [mat.name for mat in materialsOrderedForPrinting]

        for material in self._allMaterialsandElements():
            material.write(folderPath, matNames)

    def _writeMCsquareList(self, listFile):
        printedMaterials = self.materialsOrderedForPrinting()

        with open(listFile, 'w') as f:
            for i in range(len(printedMaterials)):
                # If no material defined with number i we set the closest. MCsquare does not accept jumps in list.dat
                f.write(str(i+1) + ' ' + printedMaterials[i].name + '\n')

    def materialsOrderedForPrinting(self):
        materials = self._allMaterialsandElements()

        printedMaterials = []
        for material in materials:
            printedMaterials.append(material)

        return printedMaterials

    def _allMaterialsandElements(self):
        materialNbs = []
        materials = []
        for material in self.__materials:
            if material.number in materialNbs:
                pass

            materials.append(material)
            materialNbs.append(material.number)

            for element in material.MCsquareElements:
                if element.number in materialNbs:
                    pass
                materials.append(element)
                materialNbs.append(element.number)

        return self._sortMaterialsandElements(materialNbs, materials)

    def _sortMaterialsandElements(self, materialNbs, materials):
        uniqueMaterials = []

        materialNbs = np.array(materialNbs)
        _, ind = np.unique(materialNbs, return_index=True)

        for i in ind:
            uniqueMaterials.append(materials[i])

        return uniqueMaterials