import numpy as np


class G4StopPow:
    """
    Class for storing stopping power data from Geant4.
    Inizaialize with fromFile argument to load from file.

    Attributes
    ----------
    SPs : list of SP
        List of stopping power data points
    """
    def __init__(self, SPs=None, fromFile=None):
        if SPs is None:
            SPs = []

        self.SPs = SPs

        if not(fromFile is None):
            self.load(fromFile)

    def __str__(self):
        s = ''
        for sp in self.SPs:
            s += str(sp) + '\n'

        return s

    def write(self, fileName):
        """
        Write stopping power data to file.

        Parameters
        ----------
        fileName : str
            File name
        """
        with open(fileName, 'w') as f:
            f.write(str(self))

    def load(self, filePath):
        """
        Load stopping power data from file.

        Parameters
        ----------
        filePath : str
            File path
        """
        data = np.loadtxt(filePath, 'float')

        self.SPs = []
        for i in range(data.shape[0]):
            self.SPs.append(SP(energy=data[i, 0], sp=data[i, 1]))

    def toList(self):
        """
        Convert stopping power data to list.

        Returns
        -------
        energy : list of float
            List of energies
        sp : list of float
            List of stopping powers
        """
        energy = [sp.energy for sp in self.SPs]
        sp = [sp.sp for sp in self.SPs]

        return (energy, sp)

class SP:
    """
    Class for storing stopping power data point.

    Attributes
    ----------
    energy : float
        Energy
    sp : float
        Stopping power
    """
    def __init__(self, energy=0.0, sp=0.0):
        self.energy = energy
        self.sp = sp

    def __str__(self):
        return str(self.energy) + ' ' + str(self.sp)