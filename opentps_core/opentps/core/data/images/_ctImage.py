
__all__ = ['CTImage']

import pydicom
import copy
import numpy as np

from opentps.core.data.images._image3D import Image3D


class CTImage(Image3D):
    """
    Class for CT images. Inherits from Image3D and all its attributes.

    Attributes
    ----------
    name : str (default: "CT image")
        Name of the image.
    frameOfReferenceUID : str
        UID of the frame of reference.
    sliceLocation : float
        Location of the slice.
    sopInstanceUIDs : list of str
        List of SOP instance UIDs.
    """
    def __init__(self, imageArray=None, name="CT image", origin=(0, 0, 0), spacing=(1, 1, 1), angles=(0, 0, 0),
                 seriesInstanceUID="", frameOfReferenceUID="", sliceLocation=None, sopInstanceUIDs=None, patient=None):
        self.frameOfReferenceUID = frameOfReferenceUID
        self.sliceLocation = sliceLocation
        self.sopInstanceUIDs = sopInstanceUIDs

        super().__init__(imageArray=imageArray, name=name, origin=origin, spacing=spacing, angles=angles,
                         seriesInstanceUID=seriesInstanceUID, patient=patient)
    
    def __str__(self):
        return "CT image: " + self.seriesInstanceUID

    @classmethod
    def fromImage3D(cls, image, **kwargs):
        """
        Creates a CTImage from an Image3D object.

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
        -------
        CTImage
            The created CTImage object.
        """
        dic = {'imageArray': copy.deepcopy(image.imageArray), 'origin': image.origin, 'spacing': image.spacing,
               'angles': image.angles, 'seriesInstanceUID': image.seriesInstanceUID, 'patient': image.patient}
        dic.update(kwargs)
        return cls(**dic)

    def copy(self):
        """
        Returns a copy of the CTImage object.

        Returns
        -------
        CTImage
        """
        return CTImage(imageArray=copy.deepcopy(self.imageArray), name=self.name+'_copy', origin=self.origin, spacing=self.spacing, angles=self.angles, seriesInstanceUID=pydicom.uid.generate_uid())

    def compressData(self):
        self.imageArray = self.imageArray.astype(np.int16)


