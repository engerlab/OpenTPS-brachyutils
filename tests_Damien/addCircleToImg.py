import numpy as np
import matplotlib.pyplot as plt
from skimage import draw
import time

def addCircleToImg(img, backgroundMean=70, tumorMean=100, tumorRadius=5):

    rr, cc = draw.disk((100, 100), radius=tumorRadius, shape=img.shape)
    img[rr, cc] = img[rr, cc] + tumorMean - backgroundMean

    # plt.figure()
    # plt.imshow(img)
    # plt.show()

    return img

numberOfImages = 400
imgSize = [400, 400]
backgroundMean = 70
noiseMultiplier = 5

startTime = time.time()
noisyBackground = noiseMultiplier * np.random.randn(numberOfImages, imgSize[0], imgSize[1]) + backgroundMean
print(noisyBackground.shape)


for imageIndex in range(noisyBackground.shape[0]):

    noisyBackground[imageIndex] = addCircleToImg(noisyBackground[imageIndex])

stopTime = time.time()

print(stopTime-startTime)

