import numpy as np
import math
from scipy.ndimage.interpolation import rotate
import copy


##------------------------------------------------------------------------------------------------
def oneDimensionNavThreshold(videoData, nav, gama, bins):

    """
    Select the pixel line under the navigator placed by mouse, then create an image with the pixel line of every frame.
    Use Otsu's thresholding method to select a threshold and mask the new ...

    Parameters
    ----------
    videoData : dict
        Dictionary containing all the data of the video.
    nav : list
        List containing the coordinates of the navigator.
    gama : float
        Gama value for the image.
    bins : int
        Number of bins for the image.

    Returns
    -------
    signal : array
        Array containing the signal of the navigator.
    rotAngleInRad : float
        Rotation angle in radians.
    navigatorOrientation : str
        Orientation of the navigator.
    nav : list
        List containing the coordinates of the navigator.
    """

    from skimage.filters import threshold_otsu
    from skimage.morphology import remove_small_objects
    from skimage.measure import label, regionprops
    
    #start = time.time()

    X1 = int(round(nav[2][0] * videoData["imageArrayList"][0].shape[1]))
    X2 = int(round(nav[3][0] * videoData["imageArrayList"][0].shape[1]))
    Y1 = int(round(nav[2][1] * videoData["imageArrayList"][0].shape[0]))
    Y2 = int(round(nav[3][1] * videoData["imageArrayList"][0].shape[0]))

    navCoords = [[X1, Y1], [X2, Y2]]

    ROIVidList, origin, rotAngleInRad, rotAngleInDeg, selectedLine, navigatorOrientation = extractROIAndRotationParams(videoData["imageArrayList"], navCoords)

    inversion = False

    rotatedVideoList = []
    for image in ROIVidList:

        img = np.rint(image * (bins / 255))
        img = (img * 255 / bins)  # .astype(np.uint8)

        img = img / 255
        img = np.power(img, gama)
        img *= 255
        img = img.astype(np.uint8)

        rotatedVideoList.append(rotate(img, rotAngleInDeg, reshape=False))

    underNavVectorList = []

    pixelSpacing = 0

    if navigatorOrientation == "vertical":

        if videoData["posOrientation"] == 'Cor': pixelSpacing = videoData["pixelSpacingXYZ"][2]
        elif videoData["posOrientation"] == 'Sag': pixelSpacing = videoData["pixelSpacingXYZ"][2]
        elif videoData["posOrientation"] == 'Tra': pixelSpacing = videoData["pixelSpacingXYZ"][1]

        if navCoords[0][1] > navCoords[1][1]:       ## check on points Y coords, or vertical
            inversion = True
            for image in rotatedVideoList:
                underNavVectorList.append(np.flip(image[:, selectedLine], axis=0))
        else:
            for image in rotatedVideoList:
                underNavVectorList.append(image[:, selectedLine])
    else:

        if videoData["posOrientation"] == 'Cor': pixelSpacing = videoData["pixelSpacingXYZ"][0]
        elif videoData["posOrientation"] == 'Sag': pixelSpacing = videoData["pixelSpacingXYZ"][1]
        elif videoData["posOrientation"] == 'Tra': pixelSpacing = videoData["pixelSpacingXYZ"][0]

        if navCoords[0][0] > navCoords[1][0]:
            inversion = True
            for image in rotatedVideoList:
                underNavVectorList.append(np.flip(image[selectedLine, :], axis=0))
        else:
            for image in rotatedVideoList:
                underNavVectorList.append(image[selectedLine, :])

    underNavVectorArray = np.zeros((len(underNavVectorList), underNavVectorList[0].shape[0]))

    for vectorIndex in range(0, len(underNavVectorList)):
        underNavVectorArray[vectorIndex] = underNavVectorList[vectorIndex]

    if np.std(underNavVectorArray) == 0:
        print("Not a valid navigator position")
        thresh = 0
    else:
        thresh = threshold_otsu(underNavVectorArray)
        #thresh *= 0.7

    thresholdedNavVideo = underNavVectorArray > thresh

    labeledImage = label(thresholdedNavVideo)
    regionProperties = regionprops(labeledImage)

    maxSize = 0
    for props in regionProperties:
        if props.area > maxSize:
            maxSize = props.area

    thresholdedNavVideo = remove_small_objects(thresholdedNavVideo, maxSize/2)

    print("Navigator added of size (in pixels) = ", thresholdedNavVideo.shape[1], " Otsu threshold used : ", thresh)

    signal = np.zeros(thresholdedNavVideo.shape[0])

    for i in range(0, thresholdedNavVideo.shape[0]):
        interfaceNotFound = True
        for j in range(0, thresholdedNavVideo.shape[1] - 1):
            if (thresholdedNavVideo[i, j] != thresholdedNavVideo[i, j+1] and interfaceNotFound):
                if inversion:
                    signal[i] = thresholdedNavVideo.shape[1] - (j+((thresh-underNavVectorArray[i, j])/(underNavVectorArray[i, j+1]-underNavVectorArray[i, j])))
                else:
                    signal[i] = j + ((thresh - underNavVectorArray[i, j]) / (underNavVectorArray[i, j + 1] - underNavVectorArray[i, j]))
                interfaceNotFound = False

    if math.cos(rotAngleInRad) != 0:
        signal *= (pixelSpacing/math.cos(rotAngleInRad))
    else:
        print('Invalid navigator position, rotation angle = 90°')

    if inversion:
        nav[2], nav[3] = nav[3], nav[2]

    #end = time.time()
    #print("ms to track motion : ", end - start)

    ##--------- compute other things to test the program and show results ----------
    # rr, cc = line(int(navCoords[0][1]), int(navCoords[0][0]), int(navCoords[1][1]), int(navCoords[1][0]))
    #
    # navigatorFrame = np.zeros((videoData["imageArrayList"][0].shape[0], videoData["imageArrayList"][0].shape[1]))
    # navigatorFrame[rr, cc] = 255
    # rotatedFrame = rotate(videoData["imageArrayList"][0], rotAngleInDeg, reshape=False) + rotate(navigatorFrame, rotAngleInDeg, reshape=False)
    #
    # navigatorROIFrame = np.zeros((ROIVidList[0].shape[0], ROIVidList[0].shape[1]))
    #
    # if navigatorOrientation == "vertical":
    #     navigatorROIFrame[:, round(navigatorROIFrame.shape[1] / 2)] = 255
    # else:
    #     navigatorROIFrame[round(navigatorROIFrame.shape[0] / 2), :] = 255
    #
    # plt.figure("Test ROI and rotation")
    # plt.subplot(2, 2, 1)
    # plt.imshow(videoData["imageArrayList"][0] + navigatorFrame, cmap="gray")
    # plt.subplot(2, 2, 2)
    # plt.imshow(rotatedFrame, cmap="gray")
    # plt.subplot(2, 2, 3)
    # plt.imshow(ROIVidList[0], cmap="gray")
    # plt.subplot(2, 2, 4)
    # plt.imshow(rotatedVideoList[0], cmap="gray")
    #
    # plt.figure("ROI and nav")
    # if navigatorOrientation == "vertical":
    #     plt.subplot(1, 2, 1)
    #     plt.imshow(np.transpose(underNavVectorArray), cmap="gray")
    #     plt.subplot(1, 2, 2)
    #     plt.imshow(np.transpose(thresholdedNavVideo), cmap="gray")
    # else:
    #     plt.subplot(1, 2, 1)
    #     plt.imshow(underNavVectorArray, cmap="gray")
    #     plt.subplot(1, 2, 2)
    #     plt.imshow(thresholdedNavVideo, cmap="gray")
    #
    # plt.figure("Show random under nav frames grey lvls")
    # plt.subplot(2, 3, 1)
    # plt.plot(underNavVectorArray[0, :])
    # plt.subplot(2, 3, 2)
    # plt.plot(underNavVectorArray[20, :])
    # plt.subplot(2, 3, 3)
    # plt.plot(underNavVectorArray[40, :])
    # plt.subplot(2, 3, 4)
    # plt.plot(underNavVectorArray[10, :])
    # plt.subplot(2, 3, 5)
    # plt.plot(underNavVectorArray[30, :])
    # plt.subplot(2, 3, 6)
    # plt.plot(underNavVectorArray[5, :])
    # plt.show()
    ##--------------------------------------------------------------------------------

    return signal, rotAngleInRad, navigatorOrientation, nav

##------------------------------------------------------------------------------------------------
def extractROIAndRotationParams(arrayList, squareCoords):
    """
    Extract the ROI from the image and compute the rotation angle based on the navigator position.

    Parameters
    ----------
    arrayList : list
        List containing the images of the video.
    squareCoords : list
        List containing the coordinates of the navigator.

    Returns
    -------
    ROIarrayList : list
        List containing the ROI of the images.
    origin : tuple
        Origin of the ROI.
    rotAngleInRad : float
        Rotation angle in radians.
    rotAngleInDeg : float
        Rotation angle in degrees.
    selectedLineIndex : int
        Index of the selected line.
    navigatorMainDirection : str
        Orientation of the navigator. "vertical" or "horizontal".
    """

    X1 = squareCoords[0][0]
    X2 = squareCoords[1][0]
    Y1 = squareCoords[0][1]
    Y2 = squareCoords[1][1]

    origin = (abs(X2-X1) / 2, abs(Y2-Y1) / 2)

    ROIarrayList = []

    if abs(Y2-Y1) > abs(X2-X1):
        navigatorMainDirection = "vertical"
        if X1 == X2:
            for image in arrayList:
                ROIarrayList.append(copy.deepcopy(image[min(Y1, Y2):max(Y1, Y2), X1-3:X2+4]))
            rotAngleInRad = 0
        else:
            for image in arrayList:
                ROIarrayList.append(copy.deepcopy(image[min(Y1, Y2):max(Y1, Y2), min(X1, X2)-3:max(X1, X2)+4]))
            rotAngleInRad = math.atan((X2 - X1) / (Y2 - Y1))
        selectedLineIndex = round(ROIarrayList[0].shape[1]/2)

    else:
        navigatorMainDirection = "horizontal"
        if Y1 == Y2:
            for image in arrayList:
                ROIarrayList.append(copy.deepcopy(image[Y1-3:Y2+4, min(X1, X2):max(X1, X2)]))
            rotAngleInRad = 0
        else:
            for image in arrayList:
                ROIarrayList.append(copy.deepcopy(image[min(Y1, Y2)-3:max(Y1, Y2)+4, min(X1, X2):max(X1, X2)]))
            rotAngleInRad = -math.atan((Y2 - Y1) / (X2 - X1))
        selectedLineIndex = round(ROIarrayList[0].shape[0] / 2)

    for image in ROIarrayList:
        image -= np.min(image)
        image = image/np.max(image)

    #= extractedROI[:]-np.mean(data[:, sliceNumber])

    rotAngleInDeg = -rotAngleInRad * (360 / (2 * math.pi))

    return ROIarrayList, origin, -rotAngleInRad, rotAngleInDeg, selectedLineIndex, navigatorMainDirection
