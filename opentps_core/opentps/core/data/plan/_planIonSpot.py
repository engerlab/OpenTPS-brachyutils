
__all__ = ['PlanIonSpot']


class PlanIonSpot:
    """
    A single ion spot in a layer of a beam.

    Attributes
    ----------
    spotXY : list
        List of x,y coordinates of the spot in the beam's coordinate system.
    id : int
        Spot ID.
    beamID : int (default 0)
        Beam ID.
    layerID : int (default 0)
        Layer ID.
    voxels : list
        List of voxels that are hit by the spot.
    energy : float (default 0.0)
        Energy of the spot.
    peakPosInDicomCoords : list
        Peak position of the spot in the DICOM coordinate system.
    peakPosInTargetSystem : list
        Peak position of the spot in the target coordinate system.
    spotWeight : int (default 0)
        Spot weight.
    spotTiming : int (default 0)
        Spot timing.
    """
    def __init__(self):
        super(PlanIonSpot, self).__init__()
        self.spotXY = []
        self.id = 0
        self.beamID, layerID = 0, 0
        self.voxels = []
        self.energy = 0.0
        self.peakPosInDicomCoords = None
        self.peakPosInTargetSystem = None
        self.spotWeight = 0
        self.spotTiming = 0
class Contrib:
    """
    Dose contribution of spot to voxel

    Attributes
    ----------
    spotID : int (default 0)
        Spot ID.
    minidose : float (default 0.0)
        Dose contribution of spot to voxel.
    """
    def __init__(self, **kwargs):
        super(Contrib, self).__init__(**kwargs)
        self.spotID = 0
        self.minidose = 0.0


class Voxel:
    """
    Dose contribution of voxel to spot

    Attributes
    ----------
    id : int (default 0)
        Voxel ID.
    minidose : float (default 0.0)
        Dose contribution of voxel to spot.
    """
    def __init__(self, **kwargs):
        super(Voxel, self).__init__(**kwargs)
        self.id = 0
        self.minidose = 0.0
