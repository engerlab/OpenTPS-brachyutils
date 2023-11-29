import numpy as np

from opentps.core.data._patientData import PatientData

class Dynamic2DSequence(PatientData):
    """
    Dynamic 2D Sequence class. Inherits from PatientData.

    Attributes
    ----------
    name : str (default = "2D Dyn Seq")
        Name of the dynamic 2D sequence.
    dyn2DImageList : list
        List of 2D images.
    timingsList : list
        List of timings.
    breathingPeriod : float (default = 4000)
        Breathing period.
    inhaleDuration : float (default = 1800)
        Inhale duration.
    repetitionMode : str (default = 'LOOP')
        Repetition mode.
    """

    LOOPED_MODE = 'LOOP'
    ONESHOT_MODE = 'OS'

    def __init__(self, dyn2DImageList = [], timingsList = [], name="2D Dyn Seq", repetitionMode='LOOP'):
        super().__init__(name=name)

        self.dyn2DImageList = dyn2DImageList
        self.timingsList = timingsList
        self.breathingPeriod = 4000
        self.inhaleDuration = 1800

        # self.isDynamic = True
        self.repetitionMode = repetitionMode

        print('Dynamic 2D Sequence', self.name, 'Created with ', len(self.dyn2DImageList), 'images')
        for img in self.dyn2DImageList:
            print('   ', img.name)

    def print_dynSeries_info(self, prefix=""):
        """
        Print the dynamic 2D sequence information.
        """
        print(prefix + "Dyn series: " + self.SequenceName)
        print(prefix, len(self.dyn2DImageList), ' 3D images in the serie')


    def prepareTimingsForViewer(self):
        """
        Prepare the timings for the viewer.

        Returns
        -------
        timingList : array_like
            List of timings.
        """

        numberOfImages = len(self.dyn2DImageList)
        timingList = np.linspace(0, 4000, numberOfImages+1)

        return timingList