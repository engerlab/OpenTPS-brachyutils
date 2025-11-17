from enum import Enum


class Robustness:
    """
    This class is used to compute the robustness of a plan (optimization).

    Attributes
    ----------
    selectionStrategy : str
        The selection strategy used to select the scenarios.
        It can be "REDUCED_SET" or "ALL" or "RANDOM" or "DISABLED".
    setupSystematicError : list (default = [1.6, 1.6, 1.6]) (mm)
        The setup systematic error in mm.
    setupRandomError : list (default = [1.4, 1.4, 1.4]) (mm, sigma)
        The setup random error in mm.
    rangeSystematicError : float (default = 1.6) (%)
        The range systematic error in %.
    scenarios : list
        The list of scenarios.
    numScenarios: int
        The number of scenarios generated
    """
    class Strategies(Enum):
        DEFAULT = "DISABLED"
        DISABLED = "DISABLED"
        ALL = "ALL"
        REDUCED_SET = "REDUCED_SET"
        RANDOM = "RANDOM"
    
    class Mode4D(Enum):   ## Only for protons
        DISABLED = "DISABLED"
        MCsquareAccumulation = 'MCsquareAccumulation'
        MCsquareSystematic = 'MCsquareSystematic'

    def __init__(self):
        self.selectionStrategy = self.Strategies.DEFAULT
        self.setupSystematicError = [1.6, 1.6, 1.6]  # mm
        self.setupRandomError = [1.4, 1.4, 1.4]  # mm
        self.scenarios = []
        self.numScenarios = 0

        #4D Mode
        self.Mode4D = self.Mode4D.DISABLED  ## Only for protons
        self.CreateReffrom4DCT = False
        self.Create4DCTfromRef = False
        self.SystematicAmplitudeError = 0.0
        self.RandomAmplitudeError = 0.0
        self.Dynamic_delivery = False
        self.SystematicPeriodError = 0.0
        self.RandomPeriodError = 0.0
        self.Breathing_period = 7