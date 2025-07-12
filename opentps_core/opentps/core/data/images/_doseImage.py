
__all__ = ['DoseImage']


import numpy as np
import copy
import pydicom

from opentps.core.data.images._image3D import Image3D
from opentps.core.data.plan._rtPlan import RTPlan
from opentps.core.data.images._ctImage import CTImage

class DoseImage(Image3D):
    """
    Class for dose images. Inherits from Image3D and its attributes.

    Attributes
    ----------
    referenceCT : CTImage
        Reference CT image for the dose image.
    referencePlan : RTPlan
        Reference RTPlan for the dose image.
    sopInstanceUID : str
        SOP instance UID of the dose image.
    """

    def __init__(self, imageArray=None, name="Dose image", origin=(0, 0, 0), spacing=(1, 1, 1), angles=(0, 0, 0),
                 seriesInstanceUID=None, sopInstanceUID=None, referencePlan:RTPlan = None, referenceCT:CTImage = None, patient=None):
        self.referenceCT = referenceCT
        self.sopInstanceUID = sopInstanceUID
        self.referencePlan = referencePlan

        super().__init__(imageArray=imageArray, name=name, origin=origin, spacing=spacing, angles=angles,
                         seriesInstanceUID=seriesInstanceUID, patient=patient)

    @classmethod
    def fromImage3D(cls, image: Image3D, **kwargs):
        """
        Creates a DoseImage from an Image3D object.

        Parameters
        ----------
        image : Image3D
            Image3D object to be converted.
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

        Returns
        --------
        DoseImage
            DoseImage object.
        """
        dic = {'imageArray': copy.deepcopy(image.imageArray), 'origin': image.origin, 'spacing': image.spacing,
               'angles': image.angles, 'seriesInstanceUID': image.seriesInstanceUID, 'patient': image.patient}
        dic.update(kwargs)

        cl = cls(**dic)
        if isinstance(image, DoseImage):
            cl.referenceCT = image.referenceCT
            cl.referencePlan = image.referencePlan
        return cl

    def copy(self):
        """
        Returns a copy of the DoseImage object.

        Returns
        --------
        DoseImage
            Copy of the DoseImage object.
        """
        dose = DoseImage(imageArray=copy.deepcopy(self.imageArray), name=self.name+'_copy', origin=self.origin, spacing=self.spacing, angles=self.angles, seriesInstanceUID=pydicom.uid.generate_uid(), referencePlan=self.referencePlan, referenceCT=self.referenceCT)
        return dose

    @classmethod
    def createEmptyDoseWithSameMetaData(cls, image:Image3D, **kwargs):
        """
        Creates an empty DoseImage with the same meta data as the given Image3D object.

        Parameters
        ----------
        image : Image3D
            Image3D object to be converted.
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
        dic = {'imageArray': np.zeros_like(image.imageArray), 'origin': image.origin, 'spacing': image.spacing,
               'angles': image.angles, 'seriesInstanceUID': image.seriesInstanceUID, 'patient': image.patient}
        dic.update(kwargs)

        cl = cls(**dic)
        if isinstance(image, DoseImage):
            cl.referenceCT = image.referenceCT
            cl.referencePlan = image.referencePlan
        return cl
