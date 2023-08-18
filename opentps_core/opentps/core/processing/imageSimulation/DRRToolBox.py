import math
import time
import logging

logger = logging.getLogger(__name__)

from opentps.core.data.dynamicData._dynamic2DSequence import Dynamic2DSequence
from opentps.core.data.images._projections import DRR
from opentps.core.data.dynamicData._dynamic3DSequence import Dynamic3DSequence
from opentps.core.processing.imageSimulation.ForwardProjectorTigre import forwardProjectionTigre
from opentps.core.processing.imageSimulation.ForwardProjectorTomopy import forwardProjectionTomopy

def getImageInCorrectOrientation(imageArray, orientation):
    """
    This function takes an image array and an orientation and returns the image array in the correct orientation.
    The orientation is given as a string, either 'X', 'Y' or 'Z'.

    Parameters
    ----------
    imageArray : numpy array
        The image array to be rotated.
    orientation : string
        The orientation of the image array. Either 'X', 'Y' or 'Z'.

    Returns
    -------
    imageToUse : numpy array
        The image array in the correct orientation.
    """

    if orientation == 'Z':
        imageToUse = imageArray.transpose(2, 1, 0)
    if orientation == 'X':
        imageToUse = imageArray
    if orientation == 'Y':
        imageToUse = imageArray.transpose(1, 0, 2)

    return imageToUse


def forwardProjection(image, angleInDeg=0, axis='Z', library='tomopy', nCores=1):
    """
    This function takes an image and an angle and returns the forward projection of the image at the given angle.

    Parameters
    ----------
    image : CTImage or numpy array
        The image to be projected.
    angleInDeg : float
        The angle at which the image should be projected.
    axis : string
        The axis around which the image should be rotated. Either 'X', 'Y' or 'Z'.
    library : string
        The library to be used for the forward projection. Either 'tomopy' or 'tigre'.
    nCores : int
        The number of cores to be used for the forward projection.

    Returns
    -------
    drrImage : numpy array
        The forward projection of the image at the given angle.
    """

    angleInRad = angleInDeg * 2 * math.pi / 360

    if library == 'tomopy':
        img3DArrayOriented = getImageInCorrectOrientation(image.imageArray, axis)
        drrImage = forwardProjectionTomopy(img3DArrayOriented, angleInRad, nCores=nCores)

        return drrImage

    elif library == 'tigre':
        try:
            drrImage = forwardProjectionTigre(image, angleInRad, axis)[0]
            return drrImage
        except:
            logger.error("Could not simulate projection using tigre.")


def computeDRRSet(image, angleAndAxisList, sourceImageName='', library='tomopy', nCores=1):

    """
    if image is a CTImage, this should copy the patient info and image ID to be given to the XRayImage
    else (if it is a numpy array), it should be set to None or created.

    Parameters
    ----------
    image : CTImage or numpy array
        The image to be projected.
    angleAndAxisList : list
        A list of tuples containing the angles and axes at which the image should be projected.
    sourceImageName : string
        The name of the image to be projected.
    library : string
        The library to be used for the forward projection. Either 'tomopy' or 'tigre'.
    nCores : int
        The number of cores to be used for the forward projection.

    Returns
    -------
    DRRSet : list
        A list of DRRs.
    """

    if not type(angleAndAxisList) == list:
        print('Angle list is not in the correct format')
        return
    for angleAndOrientation in angleAndAxisList:
        if len(angleAndOrientation) != 2:
            print('Angle list is not in the correct format')
            return

    if sourceImageName:
        nameToUse = sourceImageName
    else:
        nameToUse = image.name

    DRRSet = []
    for angleAndAxe in angleAndAxisList:

        drr = DRR(name='DRR_' + nameToUse + '_' + str(angleAndAxe[1]) + '_' + str(angleAndAxe[0]), sourceImage=image.seriesInstanceUID)
        drr.imageArray = forwardProjection(image, angleInDeg=angleAndAxe[0], axis=angleAndAxe[1], library=library, nCores=nCores)
        drr.projectionAngle = angleAndAxe[0]
        drr.rotationAxis = angleAndAxe[1]

        DRRSet.append(drr)

    return DRRSet


def computeDRRSequence(dynamic3DSequence, angleAndOriList, library='tomopy', nCores=1):
    """
    compute a DRR Set for each image in a list

    Parameters
    ----------
    dynamic3DSequence : Dynamic3DSequence or list
        The dynamic 3D sequence to be projected.
    angleAndOriList : list
        A list of tuples containing the angles and axes at which the image should be projected.
    library : string
        The library to be used for the forward projection. Either 'tomopy' or 'tigre'.
    nCores : int
        The number of cores to be used for the forward projection.

    Returns
    -------
    DRRSetSequence : list
        A list of DRR sets.
    """

    if isinstance(dynamic3DSequence, Dynamic3DSequence):
        imageList = dynamic3DSequence.dyn3DImageList
    elif type(dynamic3DSequence) == list:  # does not work for now, because the dynamic3DSequence.name is used to be given to the images
        imageList = dynamic3DSequence

    DRRSetSequence = []
    for imageIndex, image in enumerate(imageList):
        DRRSetSequence.append(computeDRRSet(image, angleAndOriList, sourceImageName=str(imageIndex), library=library, nCores=nCores))

    return DRRSetSequence


def createDRRDynamic2DSequences(dynamic3DSequence, angleAndAxeList, library='tomopy', nCores=1):
    """
    create a DRR Dynamic2DSequence for each image in a list

    Parameters
    ----------
    dynamic3DSequence : Dynamic3DSequence or list
        The dynamic 3D sequence to be projected.
    angleAndAxeList : list
        A list of tuples containing the angles and axes at which the image should be projected.
    library : string
        The library to be used for the forward projection. Either 'tomopy' or 'tigre'.
    nCores : int
        The number of cores to be used for the forward projection.

    Returns
    -------
    dyn2DSeqList : list
        A list of DRR Dynamic2DSequences.
    """

    drrSetSequence = computeDRRSequence(dynamic3DSequence, angleAndAxeList, library=library, nCores=nCores)
    numberOfImageInSet = len(drrSetSequence[0])

    dyn2DSeqList = []
    for imageInSetIndex in range(numberOfImageInSet):
        dyn2DSeqList.append(Dynamic2DSequence(name='DRR_' + dynamic3DSequence.name + '_' + str(angleAndAxeList[imageInSetIndex][1]) + '_' + str(angleAndAxeList[imageInSetIndex][0])))

    for imageInSetIndex in range(numberOfImageInSet):

        DRRList = []
        dyn2DSeqList[imageInSetIndex]
        for imageSet in drrSetSequence:
            DRRList.append(imageSet[imageInSetIndex])

        dyn2DSeqList[imageInSetIndex].breathingPeriod = dynamic3DSequence.breathingPeriod
        dyn2DSeqList[imageInSetIndex].inhaleDuration = dynamic3DSequence.inhaleDuration
        dyn2DSeqList[imageInSetIndex].patient = dynamic3DSequence.patient
        dyn2DSeqList[imageInSetIndex].timingsList = dynamic3DSequence.timingsList
        dyn2DSeqList[imageInSetIndex].dyn2DImageList = DRRList

    return dyn2DSeqList
