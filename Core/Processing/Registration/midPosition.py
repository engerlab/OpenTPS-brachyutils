import numpy as np
from pydicom.uid import generate_uid
import logging

from Core.Data.Images.deformation3D import Deformation3D
from Core.Processing.Registration.registrationMorphons import RegistrationMorphons

logger = logging.getLogger(__name__)


def compute(CT4D, refIndex=0, baseResolution=2.5, nbProcesses=-1):

    """Compute mid-position image and corresponding deformations from a 4D image.

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
            logger.info('\nRegistering phase', refIndex, 'to phase', i, '...')
            reg = RegistrationMorphons(CT4D.dyn3DImageList[i], CT4D.dyn3DImageList[refIndex], baseResolution=baseResolution, nbProcesses=nbProcesses)
            motionFieldList.append(reg.compute())
            if (max(averageField.getGridSize()) == 0):
                averageField.initFromImage(motionFieldList[i])
            averageField.velocity.data += motionFieldList[i].velocity.data

    motionFieldList[refIndex].initFromImage(averageField)
    averageField.velocity.data /= len(motionFieldList)

    # compute fields to midp
    for i in range(len(CT4D.dyn3DImageList)):
        motionFieldList[i].name = 'def ' + CT4D.dyn3DImageList[i].name
        motionFieldList[i].velocity.data = averageField.velocity.data - motionFieldList[i].velocity.data

    # deform images
    def3DImageList = []
    for i in range(len(CT4D.dyn3DImageList)):
        def3DImageList.append(motionFieldList[i].deformImage(CT4D.dyn3DImageList[i], fillValue='closest').data)

    # invert fields (to have them from midp to phases)
    for i in range(len(CT4D.dyn3DImageList)):
        motionFieldList[i].displacement = None
        motionFieldList[i].velocity.data = -motionFieldList[i].velocity.data

    # compute MidP
    midp = CT4D.dyn3DImageList[0].copy()
    midp.UID = generate_uid()
    midp.data = np.median(def3DImageList, axis=0)
    
    return midp, motionFieldList
