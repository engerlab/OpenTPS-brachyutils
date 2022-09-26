
__all__ = ['PlanIonSpot']


class PlanIonSpot:
    def __init__(self):
        super(PlanIonSpot, self).__init__()
        self.id = 0
        self.beamID, layerID = 0, 0
        self.voxels = []
        self.energy = 0.0


class Contrib:
    """Dose contribution of spot to voxel"""
    def __init__(self, **kwargs):
        super(Contrib, self).__init__(**kwargs)
        self.spotID = 0
        self.minidose = 0.0


class Voxel:
    """Dose contribution of voxel to spot"""
    def __init__(self, **kwargs):
        super(Voxel, self).__init__(**kwargs)
        self.id = 0
        self.minidose = 0.0
