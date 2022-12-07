import logging
import time
import numpy as np
import concurrent

# from timeit import repeat
logger = logging.getLogger(__name__)

def multiProcDeform(deformationList, dynMod, GTVMask, ncore=None, GPUNumber=0):
    imgList = [dynMod.midp for i in range(len(deformationList))]
    maskList = [GTVMask for i in range(len(deformationList))]
    tryGPUList = [True for i in range(len(deformationList))]
    GPUNumberList = [GPUNumber for i in range(len(deformationList))]
    
    import multiprocessing
    multiprocessing.set_start_method('spawn', force=True)
    
    nbrCore = multiprocessing.cpu_count() #number of logical cores of the machine
    resultDeformImageAndMask = []
    if ncore == None:
        logger.info("Number of logical cores used: %d", nbrCore)
        with concurrent.futures.ProcessPoolExecutor() as executor:
            results = executor.map(deformImageAndMask, imgList, maskList, deformationList, tryGPUList, GPUNumberList)
            resultDeformImageAndMask += results
        executor.shutdown(wait=False)
        
    elif ncore <= nbrCore:
        logger.info("Number of logical cores used: %d", ncore)
        with concurrent.futures.ProcessPoolExecutor(max_workers=ncore) as executor:
            results = executor.map(deformImageAndMask, imgList, maskList, deformationList, tryGPUList, GPUNumberList)
            resultDeformImageAndMask += results
        executor.shutdown(wait=False)
        
    else:
        logger.error("Too many cores asked. The machine has less logical cores.")
        
    return resultDeformImageAndMask

## ------------------------------------------------------------------------------------
def deformImageAndMask(img, ROIMask, deformation, tryGPU=True, GPUNumber=0):
    """
    This function is specific to this example and used to :
    - deform a CTImage and an ROIMask,
    - compute the deformed mask 3D center of mass
    - create DRR's for both,
    - binarize the DRR of the ROIMask
    - compute the 2D center of mass for the ROI DRR
    """
    try:
        import cupy
        cupy.cuda.Device(GPUNumber).use()
    except:
        print('cupy not found.')
    
    startTime = time.time()
    image = deformation.deformImage(img, fillValue='closest', outputType=np.int16, tryGPU=tryGPU)
    mask = deformation.deformImage(ROIMask, fillValue='closest', tryGPU=tryGPU)

    centerOfMass3D = mask.centerOfMass
    
    print('Image and mask deformed in', time.time() - startTime)
    return [image, mask, centerOfMass3D]

## ----------------------------------------------------------------------------------------
