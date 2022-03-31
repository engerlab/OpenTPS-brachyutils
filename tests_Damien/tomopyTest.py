import numpy as np
import tomopy
import matplotlib.pyplot as plt


def createSphere(radius):

    size = radius * 2 + 1
    ''' amplitude : numpy.ndarray of shape size*size*size. '''
    A = np.zeros((size, size, size))
    AA = np.zeros((size, size, size+(2*radius)))
    print('in createSphere', AA.shape)
    ''' (x0, y0, z0) : coordinates of center of circle inside amplitude. '''
    x0, y0, z0 = int(np.floor(A.shape[0]/2)), int(np.floor(A.shape[1]/2)), int(np.floor(A.shape[1]/2))

    for x in range(x0-radius, x0+radius+1):
        for y in range(y0-radius, y0+radius+1):
            for z in range(z0-radius, z0+radius+1):
                ''' deb: measures how far a coordinate in amplitude is far from the center. 
                        deb>=0: inside the sphere.
                        deb<0: outside the sphere.'''
                deb = radius - ((x0-x)**2 + (y0-y)**2 + (z0-z)**2)**0.5
                if (deb)>=0: AA[x,y,z] = 1

    AA[1:-1, 1:-1, 2*radius:] = 1

    # plt.figure()
    # plt.subplot(1,3,1)
    # plt.imshow(AA[:, 10, :])
    # plt.subplot(1, 3, 2)
    # plt.imshow(AA[:, :, 10])
    # plt.subplot(1, 3, 3)
    # plt.imshow(AA[:, :, 30])
    # plt.show()

    return AA
## -------------------------------------------------------------------------------------------------

testImage = np.zeros((180, 200, 170))
cubeSize = (20, 40, 30)
cubePosition = (30, 60, 60)
sphereRadius = 11
sphere = createSphere(sphereRadius)
spherePosition = [150, 150, 80]

testImage[cubePosition[0]-int(cubeSize[0]/2):cubePosition[0]+int(cubeSize[0]/2),
          cubePosition[1]-int(cubeSize[1]/2):cubePosition[1]+int(cubeSize[1]/2),
          cubePosition[2]-int(cubeSize[2]/2):cubePosition[2]+int(cubeSize[2]/2)] = 1

testImage[spherePosition[0]-sphereRadius:spherePosition[0]+sphereRadius+1,
          spherePosition[1]-sphereRadius:spherePosition[1]+sphereRadius+1,
          spherePosition[2]-2*sphereRadius:spherePosition[2]+2*sphereRadius+1] += sphere

testImage2 = np.zeros((180, 200, 170))
cubeSize = (20, 40, 30)
cubePosition = (30, 60, 60)
sphereRadius = 11
sphere = createSphere(sphereRadius)
spherePosition = [150, 150, 60]

testImage2[cubePosition[0]-int(cubeSize[0]/2):cubePosition[0]+int(cubeSize[0]/2),
          cubePosition[1]-int(cubeSize[1]/2):cubePosition[1]+int(cubeSize[1]/2),
          cubePosition[2]-int(cubeSize[2]/2):cubePosition[2]+int(cubeSize[2]/2)] = 1

print(sphere.shape)
testImage2[spherePosition[0]-sphereRadius:spherePosition[0]+sphereRadius+1,
          spherePosition[1]-sphereRadius:spherePosition[1]+sphereRadius+1,
          spherePosition[2]-2*sphereRadius:spherePosition[2]+2*sphereRadius+1] += sphere


testImage3 = np.zeros((180, 200, 170))
cubeSize = (20, 60, 30)
cubePosition = (30, 60, 120)
sphereRadius = 11
sphere = createSphere(sphereRadius)
spherePosition = [150, 150, 60]

testImage3[cubePosition[0]-int(cubeSize[0]/2):cubePosition[0]+int(cubeSize[0]/2),
          cubePosition[1]-int(cubeSize[1]/2):cubePosition[1]+int(cubeSize[1]/2),
          cubePosition[2]-int(cubeSize[2]/2):cubePosition[2]+int(cubeSize[2]/2)] = 1

print(sphere.shape)
testImage3[spherePosition[0]-sphereRadius:spherePosition[0]+sphereRadius+1,
          spherePosition[1]-sphereRadius:spherePosition[1]+sphereRadius+1,
          spherePosition[2]-2*sphereRadius:spherePosition[2]+2*sphereRadius+1] += sphere

angle = 0
fluoSimImage = tomopy.project(testImage, angle)[0]
print(fluoSimImage.shape)
fluoSimImage2 = tomopy.project(testImage2, angle)[0]
fluoSimImage3 = tomopy.project(testImage3, angle)[0]

angle = -1.57
fluoSimImage4 = tomopy.project(testImage, angle)[0]
print(fluoSimImage4.shape)
fluoSimImage5 = tomopy.project(testImage2, angle)[0]
fluoSimImage6 = tomopy.project(testImage3, angle)[0]

plt.figure()
plt.subplot(3,3,1)
plt.imshow(testImage[:,:,60])
plt.subplot(3,3,2)
plt.imshow(fluoSimImage)
plt.subplot(3,3,3)
plt.imshow(fluoSimImage4)
plt.subplot(3,3,4)
plt.imshow(testImage2[:,:,60])
plt.subplot(3,3,5)
plt.imshow(fluoSimImage2)
plt.subplot(3,3,6)
plt.imshow(fluoSimImage5)
plt.subplot(3,3,7)
plt.imshow(testImage3[:,:,60])
plt.subplot(3,3,8)
plt.imshow(fluoSimImage3)
plt.subplot(3,3,9)
plt.imshow(fluoSimImage6)
plt.show()


