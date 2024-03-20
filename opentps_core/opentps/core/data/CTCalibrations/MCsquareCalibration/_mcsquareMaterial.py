import os
from abc import abstractmethod
import re

import opentps.core.processing.doseCalculation.MCsquare as MCsquare

class MCsquareMaterial:
    """
    Base class for MCsquare materials.

    Attributes
    ----------
    density : float (default 0.0)
        Density of the material in g/cm3.
    electronDensity : float (default 0.0)
        Electron density of the material in cm-3.
    name : str
        Name of the material.
    number : int
        Number of the material.
    sp : SP
        Stopping power of the material.
    pstarSP : SP
        Stopping power of the material in PSTAR format.
    radiationLength : float (default 0.0)
        Radiation length of the material in g/cm2.
    """
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
        """
        Get material data in MCsquare format.
        """
        raise NotImplementedError()

    @staticmethod
    def getMaterialList(materialsPath='default'):
        """
        Get list of materials.

        Parameters
        ----------
        materialsPath : str (default 'default')
            Path to materials folder. If 'default', the default path is used.

        Returns
        -------
        matList : list of dict
            List of materials. Each material is a dict with keys 'ID' and 'name'.
        """
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
        """
        Get folder path from material number.

        Parameters
        ----------
        materialNumber : int
            Material number.
        materialsPath : str (default 'default')
            Path to materials folder. If 'default', the default path is used.

        Returns
        -------
        folderPath : str
            Folder path.
        """
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
        """
        Get list of material numbers.

        Parameters
        ----------
        materialsPath : str (default 'default')
            Path to materials folder. If 'default', the default path is used.

        Returns
        -------
        materialNumbers : list of int
            List of material numbers.
        """
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
    
    @staticmethod
    def getMaterialNumberFromName(name, materialsPath='default'):
        """
        Get Material number from material name if it exists

        Parameters
        ----------
        name : str
            Name of the material to search for
        materialsPath : str (default 'default')
            Path to materials folder. If 'default', the default path is used.

        Returns
        -------
        materialNumber : int
            Material number or None if it does not exists
        """
        if materialsPath=='default':
            materialsPath = os.path.join(str(MCsquare.__path__[0]), 'Materials')

        listPath = os.path.join(materialsPath, 'list.dat')

        with open(listPath, "r") as file:
            for line in file:
                # to_split = " ".join(line.split()) # remove double white spaces and tab
                lineSplit = line.split()

                if len(lineSplit)<2:
                    continue
                
                if lineSplit[1].casefold()==name.casefold():
                    return int(lineSplit[0])

    def write(self, folderPath, materialNamesOrderedForPrinting):
        """
        Write material data in specified folder.

        Parameters
        ----------
        folderPath : str
            Folder path.
        materialNamesOrderedForPrinting : list of str
            List of material names ordered for printing.
        """
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

    @classmethod
    def load(cls, materialNbOrName, materialsPath='default'):
        """
        Load element from file.

        Parameters
        ----------
        materialNbOrName : int or str
            Number of the material or name of the material.
        materialsPath : str (default 'default')
            Path to materials folder. If 'default', the default path is used.

        Returns
        -------
        self : MCsquareElement
            The loaded element.
        """
        from opentps.core.data.CTCalibrations.MCsquareCalibration._mcsquareElement import MCsquareElement
        from opentps.core.data.CTCalibrations.MCsquareCalibration._mcsquareMolecule import MCsquareMolecule

        if isinstance(materialNbOrName, int):
            materialNb = materialNbOrName
        elif isinstance(materialNbOrName, str):
            materialNb = cls.getMaterialNumberFromName(materialNbOrName, materialsPath)
        else:
            raise ValueError(f'{materialNbOrName} is not of type int or string')
        
        elementPath = cls.getFolderFromMaterialNumber(materialNb, materialsPath)

        with open(os.path.join(elementPath, 'Material_Properties.dat'), "r") as f:
            for line in f:
                if re.search(r'Mixture_Component', line): # molecule
                    return MCsquareMolecule.load(materialNb, materialsPath)

                if re.search(r'Atomic_Weight', line): # element
                    return MCsquareElement.load(materialNb, materialsPath)
            
        raise ValueError(moleculePath + ' is not an element nor a molecule.')

