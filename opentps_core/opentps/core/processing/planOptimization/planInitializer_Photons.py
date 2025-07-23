import logging
import math
import numpy as np
from opentps.core.data.CTCalibrations._abstractCTCalibration import AbstractCTCalibration
from opentps.core.data.images._ctImage import CTImage
from opentps.core.data.images._roiMask import ROIMask
from opentps.core.data.plan._planPhotonBeam import PlanPhotonBeam
from opentps.core.data.plan._photonPlan import PhotonPlan
from opentps.core.data.plan._planPhotonBeam import PlanPhotonBeam

logger = logging.getLogger(__name__)

class BeamInitializer:
    """
    This class is used to initialize a photon beam.

    Attributes
    ----------
    calibration : AbstractCTCalibration
        The CT calibration used to convert the CT image to RSP image.
    targetMargin : float
        The margin around the target in mm.
    beam : PlanPhotonBeam
        The beam to initialize.
    """
    def __init__(self):
        self.targetMargin = 0.
        self.beam: PlanPhotonBeam = None

        self.calibration: AbstractCTCalibration = None

    def initializeBeam(self):
        """
        Placement of the spots according to the Beam's Eye View (BEV) by applying gantry and 
        couch rotations to the target and projecting onto the x-z axis (BEV axis). 
        The BEV is discretized into beamlets based on defined x-y spacings.
        """

        ## Step 1: Place the target in the reference frame centered on the isocenter, so the axes are in mm.
        x, y, z = np.where(self.targetMask.imageArray)
        x = self.targetMask.origin[0] + x*self.targetMask.spacing[0] - self.beam.isocenterPosition_mm[0]
        y = self.targetMask.origin[1] + y*self.targetMask.spacing[1] - self.beam.isocenterPosition_mm[1]
        z = self.targetMask.origin[2] + z*self.targetMask.spacing[2] - self.beam.isocenterPosition_mm[2]
        centered_coords = np.vstack((x, y, z))

        ## Step 2: Define rotation matrices for gantry and couch
        # the - from the fact we rotate the target and not the Gantry/Couch
        gantry_angle_rad = np.radians(-self.beam.gantryAngle_degree)
        couch_angle_rad = np.radians(-self.beam.couchAngle_degree)
        # Rotation matrix around the Z-axis for the Gantry's angle
        rotationGantry_matrix = np.array([[np.cos(gantry_angle_rad), np.sin(gantry_angle_rad), 0],
                                        [-np.sin(gantry_angle_rad), np.cos(gantry_angle_rad), 0],
                                        [0, 0, 1]])
        # Rotation matrix around the Y-axis for the Couch's angle
        rotationCouch_matrix = np.array([[np.cos(couch_angle_rad), 0, np.sin(couch_angle_rad)],
                                        [0, 1, 0],
                                        [-np.sin(couch_angle_rad), 0, np.cos(couch_angle_rad)]])

        ## Step 3: Rotate coordinates using the combined rotation matrices
        rotated_coords = (rotationGantry_matrix @ (rotationCouch_matrix @ centered_coords))
        x_rotated, y_rotated, z_rotated = rotated_coords

        # Step 4 : Divergen projection due to the divergence of the photon beam
        x_rotated_projected = np.array([(x_rotated[i]) * self.SAD_mm / (self.SAD_mm + y_rotated[i]) for i in range(len(x_rotated))])
        z_rotated_projected = np.array([(z_rotated[i]) * self.SAD_mm / (self.SAD_mm + y_rotated[i]) for i in range(len(z_rotated))])

        # Step 5: Round x and z coordinates to the nearest beamlet spacings
        beamlet_spacing_x = self.beam.xBeamletSpacing_mm
        beamlet_spacing_z = self.beam.yBeamletSpacing_mm
        x_rotated_mult = np.round(x_rotated_projected / beamlet_spacing_x) * beamlet_spacing_x
        z_rotated_mult = np.round(z_rotated_projected / beamlet_spacing_z) * beamlet_spacing_z
        
        # Step 6: Combine rounded coordinates into beamlet positions and remove duplicates (same x-z position but in a other slide)
        beamlet_positions = [(xi, zi) for xi, zi in zip(x_rotated_mult, z_rotated_mult)]
        unique_beamlet_positions = np.unique(beamlet_positions, axis=0)

        # Be sure to not take (a,b) that are extrems in both direction
        unique_beamlet_positions = np.array([(a, b) for (a, b) in unique_beamlet_positions if np.min(x_rotated_projected) <= a <= np.max(x_rotated_projected) 
                                             and np.min(z_rotated_projected) <= b <= np.max(z_rotated_projected)])

        # Step 7: Separate positions into x and y arrays for the Beam Eyes View
        BEVx = np.flip(unique_beamlet_positions[:, 0])
        BEVy = np.flip(unique_beamlet_positions[:, 1])

        # Step 7: Append each beamlet position to the beam
        for n in range(len(BEVx)):
            self.beam.appendBeamlet(BEVx[n], BEVy[n], 1)

class PhotonPlanInitializer:
    def __init__(self):
        self.ctCalibration: AbstractCTCalibration = None
        self.ct: CTImage = None
        self.plan: PhotonPlan = None
        self.targetMask: ROIMask = None
        self.SAD_mm = None

        self._beamInitializer = BeamInitializer()

    def placeBeamlets(self, targetMargin: float = 0.):
        self._beamInitializer.calibration = self.ctCalibration
        self._beamInitializer.targetMargin = targetMargin

        logger.info('Target is dilated using a margin of {} mm. This process might take some time.'.format(targetMargin))
        roiDilated = ROIMask.fromImage3D(self.targetMask, patient=None)
        roiDilated.dilateMask(radius=targetMargin)
        logger.info('Dilation done.')
        self._beamInitializer.targetMask = roiDilated

        self.SAD_mm = self.plan.SAD_mm

        for beam in self.plan:
            beam.removeBeamSegment(beam.beamSegments)
            if beam.beamType == 'Static':
                beam.createBeamSegment()                
                self._beamInitializer.beam = beam[0]
                self._beamInitializer.SAD_mm = self.SAD_mm
                self._beamInitializer.initializeBeam()
