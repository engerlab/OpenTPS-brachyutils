import math
import logging

from opentps.core.data.dynamicData.dynamic2DSequence import Dynamic2DSequence
from opentps.core.data.images._projections import DRR
from opentps.core.data.dynamicData.dynamic3DSequence import Dynamic3DSequence
from opentps.core.processing.imageSimulation.ForwardProjectorTigre import forwardProjectionTigre

logger = logging.getLogger(__name__)

def getImageInCorrectOrientation(imageArray, orientation):

    if orientation == 'Z':
        imageToUse = imageArray.transpose(2, 1, 0)
    if orientation == 'X':
        imageToUse = imageArray
    if orientation == 'Y':
        imageToUse = imageArray.transpose(1, 0, 2)

    return imageToUse


def forwardProjection(image, angle, axis='Z'):

    angleInRad = angle * 2 * math.pi / 360
    library = 'tomopy'

    if library == 'tomopy':
        img3DArrayOriented = getImageInCorrectOrientation(image.imageArray, axis)
        try:
            import tomopy       ## this way the import is done multiple times in the case of a DRRSet or DRRSequence creation, not sure it's the best idea
            drrImage = tomopy.project(img3DArrayOriented, angleInRad)[0]

            # plt.figure()
            # plt.imshow(drrImage)
            # plt.show()

            # drrImage = tomopy.sim.project.add_gaussian(drrImage, mean=0, std=1)
            return drrImage
        except:
            library = 'tigre'
            logger.warning("No module tomopy available. Try tigre instead.")

    if library == 'tigre':
        try:
            drrImage = forwardProjectionTigre(image, angleInRad, axis)[0]
            return drrImage
        except:
            logger.error("Could not simulate projection using tigre.")


def computeDRRSet(image, angleAndAxisList, sourceImageName=''):

    """
    if image is a CTImage, this should copy the patient info and image ID to be given to the XRayImage
    else (if it is a numpy array), it should be set to None or created
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
        drr.imageArray = forwardProjection(image, angleAndAxe[0], angleAndAxe[1])
        drr.projectionAngle = angleAndAxe[0]
        drr.rotationAxis = angleAndAxe[1]

        DRRSet.append(drr)

    return DRRSet


def computeDRRSequence(dynamic3DSequence, angleAndOriList):
    """
    compute a DRR Set for each image in a list
    """

    if isinstance(dynamic3DSequence, Dynamic3DSequence):
        imageList = dynamic3DSequence.dyn3DImageList
    elif type(dynamic3DSequence) == list:  # does not work for now, because the dynamic3DSequence.name is used to be given to the images
        imageList = dynamic3DSequence

    DRRSetSequence = []
    for imageIndex, image in enumerate(imageList):
        DRRSetSequence.append(computeDRRSet(image, angleAndOriList, sourceImageName=str(imageIndex)))

    return DRRSetSequence


def createDRRDynamic2DSequences(dynamic3DSequence, angleAndAxeList):

    drrSetSequence = computeDRRSequence(dynamic3DSequence, angleAndAxeList)
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

# *(360/(2*math.pi))