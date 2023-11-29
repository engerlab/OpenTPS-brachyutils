
__all__ = ['Projection']

from opentps.core.data.images._image2D import Image2D


class Projection(Image2D):
    """
    Base class for all projections of 2D images. i.e. DRR, XRayImage. Inherits from Image2D.

    Attributes
    ----------
    projectionAngle : float
        Angle of projection in degrees.
    rotationAxis : str
        Axis of rotation. 'X', 'Y', or 'Z'.
    sourceImage : Image2D
        Image from which the projection was created.
    """
    def __init__(self, imageArray=None, name="2D Image", origin=(0, 0, 0), spacing=(1, 1), seriesInstanceUID=None, projectionAngle=0, rotationAxis='Z', sourceImage=None, patient=None):
        super().__init__(imageArray=imageArray, name=name, origin=origin, spacing=spacing, seriesInstanceUID=seriesInstanceUID, patient=patient)
        self.projectionAngle = projectionAngle
        self.rotationAxis = rotationAxis
        self.sourceImage = sourceImage
        ## add other projection params such as noise or distance between source and panel ?


class DRR(Projection):
    """
    Class for digitally reconstructed radiographs (DRRs). Inherits from Projection. The default rotation axis is 'Z'.

    Attributes
    ----------
    frameOfReferenceUID : str
        UID of the frame of reference to which the DRR belongs.
    seriesInstanceUID : str
        UID of the series to which the DRR belongs.
    sliceLocation : list of float
        Slice location of the DRR.
    sopInstanceUIDs : list of str
        List of SOP Instance UIDs of the DRR.
    """
    def __init__(self, imageArray=None, name="2D Image", origin=(0, 0, 0), spacing=(1, 1), seriesInstanceUID="", projectionAngle=0, rotationAxis='Z', sourceImage=None, frameOfReferenceUID="", sliceLocation=[], sopInstanceUIDs=[]):
        super().__init__(imageArray=imageArray, name=name, origin=origin, spacing=spacing, seriesInstanceUID=seriesInstanceUID, projectionAngle=projectionAngle, rotationAxis=rotationAxis, sourceImage=sourceImage)

        self.frameOfReferenceUID = frameOfReferenceUID
        self.seriesInstanceUID = seriesInstanceUID
        self.sliceLocation = sliceLocation
        self.sopInstanceUIDs = sopInstanceUIDs

        ## other params specific to DRR ?


class XRayImage(Projection):
    """
    Class for X-ray images. Inherits from Projection. The default rotation axis is 'Z'.

    Attributes
    ----------
    frameOfReferenceUID : str
        UID of the frame of reference to which the X-ray image belongs.
    seriesInstanceUID : str
        UID of the series to which the X-ray image belongs.
    sliceLocation : list of float
        Slice location of the X-ray image.
    sopInstanceUIDs : list of str
        List of SOP Instance UIDs of the X-ray image.
    """
    def __init__(self, imageArray=None, name="2D Image", origin=(0, 0, 0), spacing=(1, 1), seriesInstanceUID="", projectionAngle=0, rotationAxis='Z', sourceImage=None, frameOfReferenceUID="", sliceLocation=[], sopInstanceUIDs=[]):
        super().__init__(seriesInstanceUID=seriesInstanceUID, imageArray=imageArray, name=name, origin=origin, spacing=spacing, projectionAngle=projectionAngle, rotationAxis=rotationAxis, sourceImage=sourceImage)

        self.frameOfReferenceUID = frameOfReferenceUID
        self.seriesInstanceUID = seriesInstanceUID
        self.sliceLocation = sliceLocation
        self.sopInstanceUIDs = sopInstanceUIDs

        ## other params specific to XRayImage ?


