
import logging

from Core.Data.CTCalibrations.abstractCTCalibration import AbstractCTCalibration
from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.roiMask import ROIMask
from Core.Data.patientData import PatientData

logger = logging.getLogger(__name__)


class PlanStructure(PatientData):
    def __init__(self):
        super().__init__()

        self.spotSpacing = 5.0
        self.layerSpacing = 5.0
        self.targetMargin = 5.0
        self.targetMask:ROIMask = None
        self.proximalLayers = 1
        self.distalLayers = 1
        self.alignLayersToSpacing = False
        self.calibration: AbstractCTCalibration = None
        self.ct: CTImage = None
        self.beamNames = []
        self.gantryAngles = []
        self.couchAngles = []
        self.accumulatedLayer = 0
        self.accumulatedSpot = 0
