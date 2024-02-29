import os
from distutils.dir_util import copy_tree
from glob import glob
from typing import Sequence, Union
import re

import numpy as np
from numpy.matlib import repmat

from opentps.core.data.CTCalibrations.MCsquareCalibration._mcsquareMaterial import MCsquareMaterial
from opentps.core.data.CTCalibrations.MCsquareCalibration._mcsquareMolecule import MCsquareMolecule
from opentps.core.data.CTCalibrations.MCsquareCalibration._mcsquareElement import MCsquareElement

import opentps.core.processing.doseCalculation.MCsquare as MCsquareModule


class MCsquareHU2Material:
    """
    Class for converting HU to MCsquare material

    Attributes
    ----------
    !! USED ONLY AT INITIALIZATION !!
    fromFile : tuple
        Path to the file containing the HU to mass density conversion table and path to the materials folder.
    piecewiseTable : tuple
        Tuple containing the HU to mass density conversion table.
    """
    def __init__(self, piecewiseTable=([], []), fromFile=(None, 'default')):
        self.__hu = piecewiseTable[0]
        self.__materials = piecewiseTable[1]

        if not (fromFile[0] is None):
            self._initializeFromFiles(fromFile[0], materialsPath=fromFile[1])
        self.materialsPath = fromFile[1]

    def __str__(self):
        return self.mcsquareFormatted()

    @classmethod
    def fromFiles(cls, huMaterialFile, materialsPath='default'):
        """
        Create a MCsquareHU2Material object from a file.

        Parameters
        ----------
        huMaterialFile : str
            Path to the file containing the HU to mass density conversion table.
        materialsPath : str
            Path to the materials folder.

        Returns
        -------
        MCsquareHU2Material
            The MCsquareHU2Material object.
        """
        newObj = cls()
        newObj._initializeFromFiles(huMaterialFile, materialsPath)

        return newObj

    def _initializeFromFiles(self, huMaterialFile, materialsPath='default'):
        self.__load(huMaterialFile, materialsPath=materialsPath)

    def addEntry(self, hu:float, material:MCsquareMolecule):
        """
        Add an entry to the HU to material conversion table.

        Parameters
        ----------
        hu : float
            HU value.
        material : MCsquareMolecule
            Material.
        """
        self.__hu = np.append(self.__hu, hu)
        self.__materials = np.append(self.__materials, material)

        self.__hu = np.array(self.__hu)
        self.__materials = np.array(self.__materials)

        ind = np.argsort(self.__hu)

        self.__hu = self.__hu[ind]
        self.__materials = self.__materials[ind]

    def mcsquareFormatted(self):
        """
        Returns the HU to material conversion table in MCsquare format.

        Returns
        -------
        str
            The HU to material conversion table in MCsquare format.
        """
        mats = self.allMaterialsAndElements()
        matNames = [mat.name for mat in mats]

        s = ''
        for i, hu in enumerate(self.__hu):
            s += 'HU: ' + str(hu) + '\n'
            s += self.__materials[i].mcsquareFormatted(matNames) + '\n'

        return s

    def convertHU2SP(self, hu:Union[float, np.ndarray], energy:float = 100.) ->  Union[float, np.ndarray]:
        """
        Convert HU to stopping power.

        Parameters
        ----------
        hu : float or np.ndarray
            HU value(s).
        energy : float (default = 100.)
            Energy in MeV.

        Returns
        -------
        float or np.ndarray
            The stopping power value(s).
        """
        huIsScalar = not isinstance(hu, np.ndarray)

        if huIsScalar:
            return self._convert2DHU2SP(np.array([hu]), energy=energy)[0]
        else:
            if len(hu.shape) == 2:
                return self._convert2DHU2SP(hu, energy=energy)
            elif len(hu.shape) == 3:
                rsps = np.zeros(hu.shape)
                for i in range(hu.shape[2]):
                    rsps[:, :, i] = self._convert2DHU2SP(hu[:, :, i], energy=energy)
                return rsps
            else:
                return np.vectorize(lambda h: self.convertHU2SP(h, energy=energy))(hu)

    def _convert2DHU2SP(self, hu:np.ndarray, energy:float=100.) -> np.ndarray:
        huShape = hu.shape

        hu = hu.flatten()
        huLen = max(hu.shape)

        spRef = np.array([material.stoppingPower(energy) for material in self.__materials])
        huRef = np.array(self.__hu)
        huRefLen = max(spRef.shape)

        referenceHUs = repmat(huRef.reshape(huRefLen, 1), 1, huLen)
        queryHUs = repmat(hu.reshape(1, huLen), huRefLen, 1)

        diff = referenceHUs - queryHUs
        diff[diff>0] = -9999
        indexOfClosestSP = (np.abs(diff)).argmin(axis=0)

        sp = spRef[indexOfClosestSP]

        return np.reshape(sp, huShape)

    def convertSP2HU(self, sp:Union[float, np.ndarray], energy:float = 100.) ->  Union[float, np.ndarray]:
        """
        Convert stopping power to HU.

        Parameters
        ----------
        sp : float or np.ndarray
            Stopping power value(s).
        energy : float (default = 100.)
            Energy in MeV.

        Returns
        -------
        float or np.ndarray
            The HU value(s).
        """
        spIsScalar = not isinstance(sp, np.ndarray)

        if spIsScalar:
            return self._convert2DSP2HU(np.array([sp]), energy=energy)[0]
        else:
            if len(sp.shape) == 2:
                return self._convert2DSP2HU(sp, energy=energy)
            elif len(sp.shape) == 3:
                rsps = np.zeros(sp.shape)
                for i in range(sp.shape[2]):
                    rsps[:, :, i] = self._convert2DSP2HU(sp[:, :, i], energy=energy)
                return rsps
            else:
                return np.vectorize(lambda s: self.convertHU2SP(s, energy=energy))(sp)

    def _convert2DSP2HU(self, sp:np.ndarray, energy:float=100.) -> np.ndarray:
        spShape = sp.shape

        sp = sp.flatten()
        spLen = max(sp.shape)

        spRef = np.array([material.stoppingPower(energy) for material in self.__materials])
        spRefLen = max(spRef.shape)

        referenceSPs = repmat(spRef.reshape(spRefLen, 1), 1, spLen)
        querySPs = repmat(sp.reshape(1, spLen), spRefLen, 1)

        indexOfClosestSP = (np.abs(referenceSPs - querySPs)).argmin(axis=0)

        refHUs = np.array(self.__hu)
        hu = refHUs[indexOfClosestSP]

        return np.reshape(hu, spShape)
    
    def convertMaterial2HU(self, materialName:str):
        for i, mat in enumerate(self.__materials):
            if mat.name.casefold() == materialName.casefold():
                return self.__hu[i]
        raise ValueError(f'Material {materialName} undefined')
    
    def getHU2MaterialConversion(self):
        return (self.__hu, self.__materials)
    
    def getMaterialFromName(self, name:str):
        for mat in self.__materials:
            if mat.name.casefold() == name.casefold():
                return mat
        raise ValueError(f'Material {name} is not part of the calibration file')
    
    def loadMaterial(self, materialNb, materialsPath='default'):
        """
        Load material from file.

        Parameters
        ----------
        materialNb : int
            Number of the material.
        materialsPath : str (default 'default')
            Path to materials folder. If 'default', the default path is used.

        Returns
        -------
        self : MCsquareMaterial
            The loaded material.
        """
        materialPath = MCsquareMaterial.getFolderFromMaterialNumber(materialNb, materialsPath)
        with open(os.path.join(materialPath, 'Material_Properties.dat'), "r") as f:
            for line in f:
                if re.search(r'Atomic_Weight', line):
                    return MCsquareElement.load(materialNb, materialsPath)

        return MCsquareMolecule.load(materialNb, materialsPath)

    def __load(self, materialFile, materialsPath='default'):
        self.__hu = []
        self.__materials = []
        self.materialsPath = materialsPath

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

                    material = self.loadMaterial(int(lineSplit[1]), materialsPath)
                    self.__materials.append(material)
    
    def writeHeader(self):
        """
        Return header of HU to density conversion table
        """
        s =  "# ===================\n"
        s += "# HU	Material label\n"
        s += "# ===================\n\n"
        return s

    def write(self, folderPath, huMaterialFile):
        """
        Write the HU to material conversion table to a file.

        Parameters
        ----------
        folderPath : str
            Path to the folder where the materials will be written.
        huMaterialFile : str
            Path to the file where the HU to material conversion table will be written.
        """
        self._writeHU2MaterialFile(huMaterialFile)
        if folderPath:
            self._copyDefaultMaterials(folderPath)
            self._writeMaterials(folderPath)
            self._writeMCsquareList(os.path.join(folderPath, 'list.dat'))

    def _writeHU2MaterialFile(self, huMaterialFile):
        materialsOrderedForPrinting = self.materialsOrderedForPrinting()
        materialsOrderedForPrinting_names = [mat.name.casefold() for mat in materialsOrderedForPrinting]

        with open(huMaterialFile, 'w') as f:
            f.write(self.writeHeader())
            for i, hu in enumerate(self.__hu):
                index = materialsOrderedForPrinting_names.index(self.__materials[i].name.casefold())
                s = str(hu) + ' ' + str(materialsOrderedForPrinting[index].number) + '\n'
                f.write(s)

    def _writeMaterials(self, folderPath):
        materialsOrderedForPrinting = self.materialsOrderedForPrinting()
        matNames = [mat.name for mat in materialsOrderedForPrinting]

        for material in self.allMaterialsAndElements():
            material.write(folderPath, matNames)

    def _copyDefaultMaterials(self, folderPath):
        if self.materialsPath == 'default':
            materialsPath = os.path.join(str(MCsquareModule.__path__[0]), 'Materials')
        else:
            materialsPath = self.materialsPath

        for folder in glob(materialsPath + os.path.sep + '*' + os.path.sep):
            y = folder.split(os.path.sep)
            last_folder = y[-1]
            if last_folder=='':
                last_folder = y[-2]

            targetFolder = os.path.join(folderPath, os.path.basename(last_folder))
            os.makedirs(targetFolder, exist_ok=True)
            copy_tree(folder, targetFolder)

    def _writeMCsquareList(self, listFile):
        materialsOrderedForPrinting = self.materialsOrderedForPrinting()

        with open(listFile, 'w') as f:
            for i, mat in enumerate(materialsOrderedForPrinting):
                f.write(str(mat.number) + ' ' + mat.name + '\n')


    def materialsOrderedForPrinting(self):
        """
        Returns the materials in the order they should be printed in the MCsquare list.dat file.

        Returns
        -------
        list
            The materials in the order they should be printed in the MCsquare list.dat file.
        """
        materials = self.allMaterialsAndElements()
        # defaultMats = MCsquareMaterial.getMaterialList('default')
        defaultMats = MCsquareMaterial.getMaterialList(self.materialsPath)

        orderMaterials = []
        for mat in defaultMats:
            newMat = MCsquareMaterial()
            newMat.name = mat["name"]
            newMat.number = mat["ID"]
            orderMaterials.append(newMat)

        for material in materials:
            if material.name.casefold() not in [mat.name.casefold() for mat in orderMaterials]:
                orderMaterials.append(material)

        return orderMaterials

    def allMaterialsAndElements(self):
        """
        Returns all materials and elements in the HU to material conversion table.

        Returns
        -------
        list
            All materials and elements in the HU to material conversion table sorted by number.
        """
        materials = []
        for material in self.__materials:
            materials.append(material)

            for element in material.MCsquareElements:
                materials.append(element)

        return self._sortMaterialsandElements(materials)

    def _sortMaterialsandElements(self, materials:Sequence[MCsquareMaterial]) -> Sequence[MCsquareMaterial]:
        uniqueMaterials = []

        materialNames = [material.name.casefold() for material in materials]
        _, ind = np.unique(materialNames, return_index=True)

        for i in ind:
            uniqueMaterials.append(materials[i])

        uniqueMaterials.sort(key=lambda e:e.number)

        return uniqueMaterials