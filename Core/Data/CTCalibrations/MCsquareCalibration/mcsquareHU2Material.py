import logging
import os
import shutil
from distutils.dir_util import copy_tree
from glob import glob

import numpy as np

from Core.Data.CTCalibrations.MCsquareCalibration.mcsquareMaterial import MCsquareMaterial
from Core.Data.CTCalibrations.MCsquareCalibration.mcsquareMolecule import MCsquareMolecule

import Core.Processing.DoseCalculation.MCsquare as MCsquareModule


class MCsquareHU2Material:
    def __init__(self, piecewiseTable=(None, None), fromFile=(None, 'default')):
        self.__hu = piecewiseTable[0]
        self.__materials = piecewiseTable[1]

        if not (fromFile[0] is None):
            self.__load(fromFile[0], materialsPath=fromFile[1])

    def __str__(self):
        return self.mcsquareFormatted()

    def mcsquareFormatted(self):
        mats = self._allMaterialsandElements()
        matNames = [mat.name for mat in mats]

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
        self._copyDefaultMaterials(folderPath)
        self._writeMaterials(folderPath)
        self._writeMCsquareList(os.path.join(folderPath, 'list.dat'))

    def _writeHU2MaterialFile(self, huMaterialFile):
        printedMaterials = self.materialsOrderedForPrinting()

        with open(huMaterialFile, 'w') as f:
            for i, hu in enumerate(self.__hu):
                s = str(hu) + ' ' + str(printedMaterials.index(self.__materials[i])+1) + '\n'
                f.write(s)

    def _writeMaterials(self, folderPath):
        materialsOrderedForPrinting = self._allMaterialsandElements()
        matNames = [mat.name for mat in materialsOrderedForPrinting]

        for material in self._allMaterialsandElements():
            material.write(folderPath, matNames)

    def _copyDefaultMaterials(self, folderPath):
        materialsPath = os.path.join(str(MCsquareModule.__path__[0]), 'Materials')

        for folder in glob(materialsPath + os.path.sep + '*' + os.path.sep):
            y = folder.split('/')
            last_folder = y[-1]
            if last_folder=='':
                last_folder = y[-2]

            targetFolder = os.path.join(folderPath, os.path.basename(last_folder))
            os.makedirs(targetFolder, exist_ok=False)
            copy_tree(folder, targetFolder)

    def _writeMCsquareList(self, listFile):
        matList = MCsquareMaterial.getMaterialList('default')

        with open(listFile, 'w') as f:
            #We keep the default MCsquare list because some IDs (eg. that of Water) are hard coded in MCsquare.
            for mat in matList:
                id = mat["ID"]
                f.write(str(id) + ' ' + mat["name"] + '\n')

            for i, mat in enumerate(self._allMaterialsandElements()):
                # If no material defined with number i we set the closest. MCsquare does not accept jumps in list.dat
                f.write(str(i+id+1) + ' ' + mat.name + '\n')

    def materialsOrderedForPrinting(self):
        materials = self._allMaterialsandElements()
        defaultMats = MCsquareMaterial.getMaterialList('default')

        printedMaterials = []
        for i in enumerate(defaultMats):
            printedMaterials.append('Default MCsquare material')

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