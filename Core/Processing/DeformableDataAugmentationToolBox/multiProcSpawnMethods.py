import time
import numpy as np
import concurrent

# from timeit import repeat

def multiProcDeform(deformationList, dynMod, GTVMask):

    imgList = [dynMod.midp for i in range(len(deformationList))]
    maskList = [GTVMask for i in range(len(deformationList))]
    
    import multiprocessing
    multiprocessing.set_start_method('spawn', force=True)

    test = []
    with concurrent.futures.ProcessPoolExecutor() as executor:
        results = executor.map(deformImageAndMask, imgList, maskList, deformationList)
        test += results
        executor.shutdown()

    return test

## ------------------------------------------------------------------------------------
def deformImageAndMask(img, ROIMask, deformation, tryGPU=True):
    """
    This function is specific to this example and used to :
    - deform a CTImage and an ROIMask,
    - compute the deformed mask 3D center of mass
    - create DRR's for both,
    - binarize the DRR of the ROIMask
    - compute the 2D center of mass for the ROI DRR
    """
    
    startTime = time.time()
    image = deformation.deformImage(img, fillValue='closest', outputType=np.int16, tryGPU=tryGPU)
    # print(image.imageArray.shape, np.min(image.imageArray), np.max(image.imageArray), np.mean(image.imageArray))
    mask = deformation.deformImage(ROIMask, fillValue='closest', tryGPU=tryGPU)
    # print('mask', type(mask), type(mask.imageArray[0,0,0]))
    print('image and mask deformed in', time.time() - startTime)

    startTime = time.time()
    centerOfMass3D = mask.centerOfMass
    # print('centerOfMass3D computed in', time.time() - startTime)

    return [image, mask, centerOfMass3D]

## ----------------------------------------------------------------------------------------
