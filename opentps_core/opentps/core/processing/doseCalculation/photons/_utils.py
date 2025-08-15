import numpy as np
import opentps.core.io.CCCdoseEngineIO as CCCdoseEngineIO
import scipy.sparse as sp
import logging
logger = logging.getLogger(__name__)
from scipy.ndimage import shift, gaussian_filter
import scipy.sparse as sp
from scipy.sparse import csc_matrix
from opentps.core.data.images import DoseImage
import ctypes
import os
import psutil
import os
from opentps.core.data.plan import PhotonPlan


def correctShift(setup, angle):
    """
    Correct the setup error for a given angle. This takes into account that a shift on the beam direction does not affect the dose distribution.
    Parameters
    ----------
    setup : np.array
        Setup error in LPS coordinates
    angle : float
        Angle of the beam in radians
    Returns
    -------
    np.array
        Corrected setup error in LPS coordinates
    """     
    return np.array([(setup[0] * np.cos(angle) - setup[1] * np.sin(angle)) * np.cos(angle), (setup[0] * np.cos(angle) - setup[1] * np.sin(angle)) * np.sin(angle), setup[2]])

def shiftBeamlets_cu(sparseBeamlets, gridSize,  scenarioShift_voxel, beamletAngles_rad):
    """
    Shift the beamlets in the dose influence matrix for a given setup error. This would be equivalent to recalculating the dose distribution for a given setup error. This function parallelizes the calculation of the shifts over each voxel of the beamlet using CUDA.
    ----------
    sparseBeamlets : sp.csc_matrix
        Sparse matrix of the beamlets
    gridSize : np.array
        Size of the grid
    scenarioShift_voxel : np.array
        Setup error in voxels
    beamletAngles_rad : np.array
        Angles of the beamlets in radians
    Returns
    -------
    sp.csc_matrix
        Sparse matrix of the shifted beamlets
    """   
    import pycuda.autoinit
    from pycuda.compiler import SourceModule
    import pycuda.driver as cuda

    scenarioShift_voxel[2]*=-1 ### To have the setup error in LPS. Check because some signs problem
    scenarioShift_voxel[1]*=-1 ### To have the setup error in LPS. Check because some signs problem
    nbOfBeamlets = sparseBeamlets.shape[1]
    nbOfVoxelInImage = sparseBeamlets.shape[0]
    gridSize = np.array(gridSize, dtype=np.int32)
    BeamletMatrix = []

    # Load the CUDA code from the external file
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "shiftBeamletsKernel.cu"), "r") as cuda_file:
        kernel_code = cuda_file.read()

    # Compile the CUDA code
    mod = SourceModule(kernel_code)

    for index in range(nbOfBeamlets):
        scenarioShiftCorrected_voxel = np.round(correctShift(scenarioShift_voxel, beamletAngles_rad[index]),3)
        # scenarioShiftCorrected_voxel = scenarioShift_voxel
        beamlet = sparseBeamlets[:, index]
        shiftTrunctated = CCCdoseEngineIO.convertTo1DcoordFortran(np.trunc(scenarioShiftCorrected_voxel), gridSize) 
        nonZeroIndexes = beamlet.nonzero()
        if len(nonZeroIndexes[0]) == 0:
            BeamletMatrix.append(beamlet)  
            continue
        nonZeroValues = np.array(beamlet[nonZeroIndexes], dtype= np.float32)
        nonZeroIndexes = np.array(nonZeroIndexes[0] + shiftTrunctated, dtype= np.int32)
        NumberOfElements = np.int32(len(nonZeroValues[0]))

        nonZeroValues_gpu = cuda.mem_alloc(nonZeroValues.nbytes)
        nonZeroIndexes_gpu = cuda.mem_alloc(nonZeroIndexes.nbytes)
        gridSize_gpu = cuda.mem_alloc(gridSize.nbytes)
        cuda.memcpy_htod(nonZeroValues_gpu, nonZeroValues)
        cuda.memcpy_htod(nonZeroIndexes_gpu, nonZeroIndexes)
        cuda.memcpy_htod(gridSize_gpu, gridSize)
        # gpuarray.zeros()
        nonZeroValuesShiftedExtendedArray = np.array([])
        nonZeroIndexesShiftedExtendedArray  = np.array([])
        scenarioShiftCorrected_voxel -= np.trunc(scenarioShiftCorrected_voxel)
        if np.sum(scenarioShiftCorrected_voxel)!=0:
            for i, shift in enumerate(scenarioShiftCorrected_voxel): #### Think on puting this into the cuda code
                if shift == 0:
                    continue
                weight = np.abs(shift) / np.sum(np.abs(scenarioShiftCorrected_voxel))
                directionalShiftCorrected_voxel = np.zeros(3)
                directionalShiftCorrected_voxel[i] = shift
                magnitude = CCCdoseEngineIO.convertTo1DcoordFortran(np.trunc(directionalShiftCorrected_voxel), gridSize) 
                direction = CCCdoseEngineIO.convertTo1DcoordFortran(np.sign(directionalShiftCorrected_voxel), gridSize) 
                directionNeg = CCCdoseEngineIO.convertTo1DcoordFortran(-1 * np.sign(directionalShiftCorrected_voxel), gridSize)
                shiftValue = np.float32((directionalShiftCorrected_voxel[np.nonzero(directionalShiftCorrected_voxel)[0][0]])%1)

                nonZeroValuesShifted = np.zeros(NumberOfElements * 2).astype(np.float32)
                nonZeroValuesShifted_gpu = cuda.mem_alloc(nonZeroValuesShifted.nbytes)
                cuda.memcpy_htod(nonZeroValuesShifted_gpu, nonZeroValuesShifted)

                nonZeroIndexesShifted = np.zeros(NumberOfElements * 2).astype(np.int32)
                nonZeroIndexesShifted_gpu = cuda.mem_alloc(nonZeroIndexesShifted.nbytes)
                cuda.memcpy_htod(nonZeroIndexesShifted_gpu, nonZeroIndexesShifted)

                Shift_voxel = np.array([magnitude, directionNeg, direction],dtype=np.int32)
                scenarioShiftVoxel_gpu = cuda.mem_alloc(Shift_voxel.nbytes)
                cuda.memcpy_htod(scenarioShiftVoxel_gpu, Shift_voxel)

                shiftSparse = mod.get_function("shiftSparse")
                shiftSparse(nonZeroValues_gpu,nonZeroValuesShifted_gpu,nonZeroIndexes_gpu,nonZeroIndexesShifted_gpu, scenarioShiftVoxel_gpu, gridSize_gpu, shiftValue, NumberOfElements, np.int32(nbOfVoxelInImage), grid=(int(NumberOfElements/1024)+1,1),block=(1024,1,1))

                cuda.memcpy_dtoh(nonZeroValuesShifted,nonZeroValuesShifted_gpu)
                cuda.memcpy_dtoh(nonZeroIndexesShifted,nonZeroIndexesShifted_gpu)

                nonZeroValuesShiftedExtendedArray = np.append(nonZeroValuesShiftedExtendedArray,nonZeroValuesShifted * weight)
                nonZeroIndexesShiftedExtendedArray = np.append(nonZeroIndexesShiftedExtendedArray,nonZeroIndexesShifted)
            beamlet = sp.csc_matrix((nonZeroValuesShiftedExtendedArray, (nonZeroIndexesShiftedExtendedArray, np.zeros(nonZeroIndexesShiftedExtendedArray.size))), shape=(nbOfVoxelInImage, 1),dtype=np.float32)    
        else:
            mask =nonZeroIndexes<nbOfVoxelInImage
            nonZeroValues = nonZeroValues[0][mask]
            nonZeroIndexes = nonZeroIndexes[mask]
            
            beamlet = sp.csc_matrix((nonZeroValues, (nonZeroIndexes, np.zeros(nonZeroIndexes.size))), shape=(nbOfVoxelInImage, 1),dtype=np.float32)      
        BeamletMatrix.append(beamlet)  
    return sp.hstack(BeamletMatrix, format='csc')

def find_change_indices(arr):
    """
    Find the indices where the values of an array change
    ----------
    arr : np.array
        Array of values
    -------
    list
        List of indices where the values change
    """   
    arr = np.array(arr)
    # Create a boolean array where changes occur
    changes = arr[1:] != arr[:-1]
    # Use np.where to find the indices where changes occur, add 1 because we compare with the previous element
    change_indices = np.where(changes)[0] + 1
    return change_indices.tolist()

def shiftBeamlets(sparseBeamlets, gridSize,  scenarioShift_voxel, beamletAngles_rad):
    """
    Shift the beamlets in the dose influence matrix for a given setup error. This would be equivalent to recalculating the dose distribution for a given setup error. 
    ----------
    sparseBeamlets : sp.csc_matrix
        Sparse matrix of the beamlets
    gridSize : np.array
        Size of the grid
    scenarioShift_voxel : np.array
        Setup error in voxels
    beamletAngles_rad : np.array
        Angles of the beamlets in radians
    Returns
    -------
    sp.csc_matrix
        Sparse matrix of the shifted beamlets
    """   
    paralelize = False
    try:
        import pycuda.driver as cuda
        import pycuda.autoinit
        cuda.init()
        device_count = cuda.Device.count()
        if device_count>0:
            paralelize = True
    except Exception as e:
        print(f"CUDA is not available: {e}")
    
    if paralelize:
        return shiftBeamlets_cu(sparseBeamlets, gridSize,  scenarioShift_voxel, beamletAngles_rad)
    return shiftBeamlets_cpp(sparseBeamlets, gridSize,  scenarioShift_voxel, beamletAngles_rad)


def shiftBeamlets_cpp(sparseBeamlets, gridSize,  scenarioShift_voxel, beamletAngles_rad):
    """
    Shift the beamlets in the dose influence matrix for a given setup error.
    This would be equivalent to recalculating the dose distribution for a given setup error.
    This function is executed in c++ to gain speed and parallelize the process over different threads.
    ----------
    sparseBeamlets : sp.csc_matrix
        Sparse matrix of the beamlets
    gridSize : np.array
        Size of the grid
    scenarioShift_voxel : np.array
        Setup error in voxels
    beamletAngles_rad : np.array
        Angles of the beamlets in radians
    Returns
    -------
    sp.csc_matrix
        Sparse matrix of the shifted beamlets
    """   
    lib = ctypes.cdll.LoadLibrary(os.path.join(os.path.dirname(os.path.abspath(__file__)), "shiftBeamlets.so"))
    
    # Define the argument types and return types for the C++ function
    lib.shiftBeamlets.argtypes = [
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        np.ctypeslib.ndpointer(dtype=np.int32, ndim=1, flags='C_CONTIGUOUS'),
        np.ctypeslib.ndpointer(dtype=np.int32, ndim=1, flags='C_CONTIGUOUS'),
        np.ctypeslib.ndpointer(dtype=np.int32, ndim=1, flags='C_CONTIGUOUS'),
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        np.ctypeslib.ndpointer(dtype=np.int32, ndim=1, flags='C_CONTIGUOUS'),
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        ctypes.c_int,
        ctypes.c_int
    ]
    numThreads = psutil.cpu_count()
    scenarioShift_voxel[2]*=-1 ### To have the setup error in LPS. Check because some signs problem
    scenarioShift_voxel[1]*=-1 ### To have the setup error in LPS. Check because some signs problem
    gridSize = np.array(gridSize, dtype=np.int32)
    BeamletMatrix = []
    
    length = sparseBeamlets.shape[0]
    nonZeroIndexes = sparseBeamlets.nonzero()
    nonZeroValues = np.array(sparseBeamlets[nonZeroIndexes], dtype= np.float32)[0]
    nonZeroIndexes_beamlet = np.array(nonZeroIndexes[0], dtype= np.int32)
    indexes_beamlet = np.array(nonZeroIndexes[1], dtype= np.int32)
    arg = np.argsort(indexes_beamlet)
    
    indexes_beamlet = indexes_beamlet[arg]
    nonZeroIndexes_beamlet = nonZeroIndexes_beamlet[arg]
    nonZeroValues = nonZeroValues[arg]
    indexesChangeBeamlet = [0] + find_change_indices(indexes_beamlet) + [len(indexes_beamlet)]
    NumberOfElements = len(nonZeroValues)
    nonZeroValues = np.array(nonZeroValues, dtype=np.float32)
    nonZeroIndexes_beamlet = np.array(nonZeroIndexes_beamlet, dtype=np.int32)
    indexesChangeBeamlet = np.array(indexesChangeBeamlet, dtype=np.int32)
    scenarioShift_voxel = np.array(scenarioShift_voxel, dtype=np.float32)
    
    nonZeroValuesShifted = np.zeros(NumberOfElements * 2 * 3).astype(np.float32)
    nonZeroIndexesShifted = np.zeros(NumberOfElements * 2 * 3).astype(np.int32)
    beamletAngles_rad = np.array(beamletAngles_rad, dtype=np.float32)
    nOfBeamlets = len(beamletAngles_rad)
    lib.shiftBeamlets(nonZeroValues, nonZeroValuesShifted, nonZeroIndexes_beamlet, nonZeroIndexesShifted, indexesChangeBeamlet, scenarioShift_voxel, gridSize, beamletAngles_rad, nOfBeamlets, numThreads)
    
    for i in range(nOfBeamlets):
        start = indexesChangeBeamlet[i]
        end = indexesChangeBeamlet[i+1]
        indexes = nonZeroIndexesShifted[start*2*3:end*2*3]
        values = nonZeroValuesShifted[start*2*3:end*2*3]
        indexes = indexes[indexes.nonzero()]
        values = values[values.nonzero()]
        BeamletMatrix.append(sp.csc_matrix((values, (indexes, np.zeros(len(indexes)))), shape=(length,1), dtype=np.float32))
        
    return sp.hstack(BeamletMatrix, format='csc')


def dnorm(x, mu, sd):
    return 1 / (np.sqrt(2 * np.pi) * sd) * np.e ** (-np.power((x - mu) / sd, 2) / 2)


def adjustDoseToScenario(scenario, nominal, plan: PhotonPlan): ### Shift beamlets according sse + apply gaussian filter one the dose array to simulate sre
    if scenario.sse is not None:
        shiftVoxels = np.array(scenario.sse) / np.array(nominal.doseSpacing)
        cumulativeNumberBeamlets = 0
        weights = nominal._weights
        doseGridSize = nominal.doseGridSize
        dose = np.zeros(doseGridSize)
        sizeImage = nominal._sparseBeamlets.shape[0]
        nofBeamlets = nominal._sparseBeamlets.shape[1]
        assert nofBeamlets==len(plan.beamlets), f"The number of beamlets in the dose influece matrix is {nofBeamlets} but the number of beamlets in the treatment plan is {len(plan.beamlets)}"
        for segment in plan.beamSegments:
            beamletsSegment = nominal._sparseBeamlets[:, cumulativeNumberBeamlets: cumulativeNumberBeamlets + len(segment)]
            weightsSegment = weights[cumulativeNumberBeamlets: cumulativeNumberBeamlets + len(segment)]
            result = csc_matrix.dot(beamletsSegment, weightsSegment).reshape(sizeImage,1)
            result = np.reshape(result, doseGridSize, order='F')
            result = np.flip(result, 0)
            result = np.flip(result, 1)
            shiftVoxelsCorrected = np.round(correctShift(shiftVoxels, segment.gantryAngle_degree / 180 * np.pi), 3) #only for axe of the beam
            dose +=  shift(result, shiftVoxelsCorrected, mode='constant', cval=0, order=1)
            cumulativeNumberBeamlets+=len(segment)

        dose = DoseImage(imageArray=dose, origin=nominal.doseOrigin, spacing=nominal.doseSpacing,
                              angles=(1, 0, 0, 0, 1, 0, 0, 0, 1))
    else:
        dose = nominal.toDoseImage()

    doseArray = dose.imageArray
    if np.all(scenario.sre) != None:
        doseArray = gaussian_filter(doseArray.astype(float), sigma = scenario.sre, order=0, truncate=2)
    else:
        return dose
    dose.imageArray = doseArray

    return dose