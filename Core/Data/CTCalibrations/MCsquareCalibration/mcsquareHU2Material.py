import logging
import os
import shutil
from distutils.dir_util import copy_tree
from glob import glob
from typing import Sequence

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
        materialsOrderedForPrinting = self.materialsOrderedForPrinting()

        with open(huMaterialFile, 'w') as f:
            for i, hu in enumerate(self.__hu):
                s = str(hu) + ' ' + str(materialsOrderedForPrinting.index(self.__materials[i])+1) + '\n'
                f.write(s)

    def _writeMaterials(self, folderPath):
        materialsOrderedForPrinting = self.materialsOrderedForPrinting()
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
        materialsOrderedForPrinting = self.materialsOrderedForPrinting()

        with open(listFile, 'w') as f:
            for i, mat in enumerate(materialsOrderedForPrinting):
                f.write(str(i+1) + ' ' + mat.name + '\n')

    def materialsOrderedForPrinting(self):
        materials = self._allMaterialsandElements()
        defaultMats = MCsquareMaterial.getMaterialList('default')

        orderMaterials = []
        for mat in defaultMats:
            newMat = MCsquareMaterial()
            newMat.name = mat["name"]
            orderMaterials.append(newMat)

        for material in materials:
            orderMaterials.append(material)

        return orderMaterials

    def _allMaterialsandElements(self):
        materials = []
        for material in self.__materials:
            materials.append(material)

            for element in material.MCsquareElements:
                materials.append(element)

        return self._sortMaterialsandElements(materials)

    def _sortMaterialsandElements(self, materials:Sequence[MCsquareMaterial]) -> Sequence[MCsquareMaterial]:
        uniqueMaterials = []

        materialNames = [material.name for material in materials]
        _, ind = np.unique(materialNames, return_index=True)

        for i in ind:
            uniqueMaterials.append(materials[i])

        uniqueMaterials.sort(key=lambda e:e.number)

        return uniqueMaterials