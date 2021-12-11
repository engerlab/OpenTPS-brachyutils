import os
import pydicom


class DataLoader:
    """
    The DataLoader class is responsible for finding and loading data from the file system.

    """

    @staticmethod
    def loadAllData(self, inputPath, maxDepth=-1):
        """
        Load all data found at the given path.

        Parameters
        ----------
        inputPath: str
            Path to the file or folder containing the data to be loaded.

        maxDepth: int, optional
            Maximum subfolder depth where the function will check for data to be loaded.
            Default is -1, which implies recursive search over infinite subfolder depth.

        Returns
        -------
        dataList: list of data objects
            The function returns a list of data objects containing the imported data.

        """


        dataList = []

        fileList = os.listdir(inputPath)

        return dataList