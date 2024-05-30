
__all__ = ['RSPImage']

import copy
from typing import Optional

import numpy as np

from opentps.core.data.CTCalibrations._abstractCTCalibration import AbstractCTCalibration
from opentps.core.data.images._ctImage import CTImage
from opentps.core.data.images._image3D import Image3D
from opentps.core.data.plan._planIonBeam import PlanIonBeam
import opentps.core.processing.imageProcessing.imageTransform3D as imageTransform3D
from opentps.core.processing.imageProcessing import resampler3D


class RSPImage(Image3D):
    """
    Class for Relative Stopping Power images. Inherits from Image3D.

    Attributes
    ----------
    name : str (default: "RSP image")
        Name of the image.
    frameOfReferenceUID : str
        Frame of reference UID.
    sliceLocation : list of float
        Slice location.
    sopInstanceUIDs : list of str
        SOP instance UID.
    """
    def __init__(self, imageArray=None, name="RSP image", origin=(0, 0, 0), spacing=(1, 1, 1),
                 angles=(0, 0, 0), seriesInstanceUID=None, frameOfReferenceUID=None, sliceLocation=[], sopInstanceUIDs=[], patient=None):

        self.frameOfReferenceUID = frameOfReferenceUID
        self.sliceLocation = sliceLocation
        self.sopInstanceUIDs = sopInstanceUIDs

        super().__init__(imageArray=imageArray, name=name, origin=origin, spacing=spacing,
                         angles=angles, seriesInstanceUID=seriesInstanceUID, patient=None)

    def __str__(self):
        return "RSP image: " + self.seriesInstanceUID

    @classmethod
    def fromImage3D(cls, image, **kwargs):
        """
        Create a new RSPImage from an Image3D object.

        Parameters
        ----------
        image : Image3D
            Image3D object.
        kwargs : dict (optional)
            Additional keyword arguments.
                - imageArray : numpy.ndarray
                    Image array of the image.
                - origin : tuple of float
                    Origin of the image.
                - spacing : tuple of float
                    Spacing of the image.
                - angles : tuple of float
                    Angles of the image.
                - seriesInstanceUID : str
                    Series instance UID of the image.
                - patient : Patient
                    Patient object of the image.
        """
        dic = {'imageArray': copy.deepcopy(image.imageArray), 'origin': image.origin, 'spacing': image.spacing,
               'angles': image.angles, 'seriesInstanceUID': image.seriesInstanceUID, 'patient': image.patient}
        dic.update(kwargs)
        return cls(**dic)

    @classmethod
    def fromCT(cls, ct:CTImage, calibration:AbstractCTCalibration, energy:float=100.):
        """
        Create a new RSPImage from a CTImage object by converting the Housefield units to relative stopping power according to the calibration.

        Parameters
        ----------
        ct : CTImage
            CTImage object.
        calibration : AbstractCTCalibration
            CT calibration object.
        energy : float (default: 100.)
            Energy of the beam in MeV.

        Returns
        -------
        RSPImage
            RSPImage object.
        """
        newRSPImage = cls.fromImage3D(ct)
        newRSPImage.imageArray = calibration.convertHU2RSP(ct.imageArray, energy)

        return newRSPImage

    def computeCumulativeWEPL(self, beam:Optional[PlanIonBeam]=None, sad=np.Inf, roi=None) -> Image3D:
        """
        Compute the cumulative water equivalent path length (WEPL) of the image.

        Parameters
        ----------
        beam : PlanIonBeam (optional)
            Ion beam object.
        roi : ROICountour or ROIMask (optional)

        Returns
        -------
        Image3D
            Image3D object.
        """
        if not (beam is None):
            rspIEC = imageTransform3D.dicomToIECGantry(self, beam, fillValue=0., cropROI=roi, cropDim0=True, cropDim1=True, cropDim2=False)
        else:
            rspIEC = self.__class__.fromImage3D(self)

        rspIEC.imageArray = np.cumsum(rspIEC.imageArray, axis=2)*rspIEC.spacing[2]

        if not (beam is None):
            outImage = imageTransform3D.iecGantryToDicom(rspIEC, beam, 0.)
            outImage = resampler3D.resampleImage3DOnImage3D(outImage, self, inPlace=True, fillValue=0.)
        else:
            outImage = rspIEC

        return outImage

    def get_SPR_at_position(self, position):
        """
        Get the stopping power ratio at a given position. If the position is outside the image, the SPR is set to 0.001.

        Parameters
        ----------
        position : tuple of float
            Position in mm.

        Returns
        -------
        float
            Stopping power ratio.
        """
        voxel_id = self.getVoxelIndexFromPosition(position)

        if voxel_id[0] < 0 or voxel_id[1] < 0 or voxel_id[2] < 0:
            return 0.001

        elif voxel_id[0] >= self.gridSize[0] or voxel_id[1] >= self.gridSize[1] or voxel_id[2] >= self.gridSize[2]:
            return 0.001

        else:
            return self.imageArray[voxel_id[0], voxel_id[1], voxel_id[2]]
