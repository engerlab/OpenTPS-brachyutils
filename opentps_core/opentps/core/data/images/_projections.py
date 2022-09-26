
__all__ = ['Projection']

from opentps.core.data.images._image2D import Image2D


class Projection(Image2D):
    def __init__(self, imageArray=None, name="2D Image", origin=(0, 0, 0), spacing=(1, 1), seriesInstanceUID=None, projectionAngle=0, rotationAxis='Z', sourceImage=None, patient=None):
        super().__init__(imageArray=imageArray, name=name, origin=origin, spacing=spacing, seriesInstanceUID=seriesInstanceUID, patient=patient)
        self.projectionAngle = projectionAngle
        self.rotationAxis = rotationAxis
        self.sourceImage = sourceImage
        ## add other projection params such as noise or distance between source and panel ?


class DRR(Projection):
    def __init__(self, imageArray=None, name="2D Image", origin=(0, 0, 0), spacing=(1, 1), seriesInstanceUID="", projectionAngle=0, rotationAxis='Z', sourceImage=None, frameOfReferenceUID="", sliceLocation=[], sopInstanceUIDs=[]):
        super().__init__(imageArray=imageArray, name=name, origin=origin, spacing=spacing, seriesInstanceUID=seriesInstanceUID, projectionAngle=projectionAngle, rotationAxis=rotationAxis, sourceImage=sourceImage)

        self.frameOfReferenceUID = frameOfReferenceUID
        self.seriesInstanceUID = seriesInstanceUID
        self.sliceLocation = sliceLocation
        self.sopInstanceUIDs = sopInstanceUIDs

        ## other params specific to DRR ?


class XRayImage(Projection):
    def __init__(self, imageArray=None, name="2D Image", origin=(0, 0, 0), spacing=(1, 1), seriesInstanceUID="", projectionAngle=0, rotationAxis='Z', sourceImage=None, frameOfReferenceUID="", sliceLocation=[], sopInstanceUIDs=[]):
        super().__init__(seriesInstanceUID=seriesInstanceUID, imageArray=imageArray, name=name, origin=origin, spacing=spacing, projectionAngle=projectionAngle, rotationAxis=rotationAxis, sourceImage=sourceImage)

        self.frameOfReferenceUID = frameOfReferenceUID
        self.seriesInstanceUID = seriesInstanceUID
        self.sliceLocation = sliceLocation
        self.sopInstanceUIDs = sopInstanceUIDs

        ## other params specific to XRayImage ?


