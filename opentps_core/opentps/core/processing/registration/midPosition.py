import numpy as np
from pydicom.uid import generate_uid
import logging

from opentps.core.processing.registration.registrationMorphons import RegistrationMorphons
from opentps.core.data.images._deformation3D import Deformation3D


logger = logging.getLogger(__name__)


def compute(CT4D, refIndex=0, baseResolution=2.5, nbProcesses=-1, tryGPU=True):

    """
    Compute mid-position image and corresponding deformations from a 4D image.

    Parameters
    ----------
    CT4D : Dynamic3DSequence
        4D image.
    refIndex : int
        index of the reference phase in the 4D image.
    baseResolution : double
        spacing of the highest registration resolution (i.e. spacing of the output deformation fields)
    nbProcesses : int
        number of processes to be used in Morphons registration (-1 = maximum number of processes)

    Returns
    -------
    numpy array
        MidP image.
    list
        List of deformations between MidP image and each phase of the 4D image
    """

    averageField = Deformation3D()

    # perform registrations
    motionFieldList = []

    for i in range(len(CT4D.dyn3DImageList)):

        if i == refIndex:
            emptyField = Deformation3D()
            motionFieldList.append(emptyField)
        else:
            logger.info('\nRegistering phase' + str(refIndex) + ' to phase' + str(i) + '...')
            reg = RegistrationMorphons(CT4D.dyn3DImageList[i], CT4D.dyn3DImageList[refIndex], baseResolution=baseResolution, nbProcesses=nbProcesses, tryGPU=tryGPU)
            motionFieldList.append(reg.compute())
            if (max(averageField.gridSize) == 0):
                averageField.initFromImage(motionFieldList[i])
            averageField.setVelocityArray(averageField.velocity.imageArray + motionFieldList[i].velocity.imageArray)

    motionFieldList[refIndex].initFromImage(averageField)
    averageField.setVelocityArray(averageField.velocity.imageArray / len(motionFieldList))

    # compute fields to midp
    for i in range(len(CT4D.dyn3DImageList)):
        motionFieldList[i].name = 'def ' + CT4D.dyn3DImageList[i].name
        motionFieldList[i].setVelocityArray(averageField.velocity.imageArray - motionFieldList[i].velocity.imageArray)

    # deform images
    def3DImageList = []
    for i in range(len(CT4D.dyn3DImageList)):
        def3DImageList.append(motionFieldList[i].deformImage(CT4D.dyn3DImageList[i], fillValue='closest', tryGPU=tryGPU)._imageArray)

    # invert fields (to have them from midp to phases)
    for i in range(len(CT4D.dyn3DImageList)):
        motionFieldList[i].displacement = None
        motionFieldList[i].setVelocityArray(-motionFieldList[i].velocity.imageArray)

    # compute MidP
    midp = CT4D.dyn3DImageList[0].copy()
    midp.UID = generate_uid()
    midp._imageArray = np.median(def3DImageList, axis=0)
    
    return midp, motionFieldList
