import ctypes
import os

import numpy as np

import opentps.core.processing.doseCalculation.MCsquare as MCsquareModule
from opentps.core.io.mcsquareIO import _print_memory_usage

from scipy.sparse import csc_matrix, hstack


class Ptr:
    def __init__(self, ctype):
        self._ctype = ctype

        val = ctype(0)
        self._ptr = ctypes.pointer(val)

    @property
    def ptr(self):
        return self._ptr

    @property
    def value(self):
        return self._ptr[0]

class PtrToPtr:
    # A pointer to a pointer (typically to create a pointer to an array)

    #ctypes.c_int32, ctypes.c_float
    def __init__(self, ctype):
        self._ctype = ctype

        array = ctypes.pointer(ctype())
        self._ptr = ctypes.pointer(ctypes.cast(array, ctypes.POINTER(ctype)))

    @property
    def ptr(self):
        return self._ptr

    def getArray(self, shape):
        # The second pointer might have changed so we cannot just return the initial array
        arr = ctypes.cast(self._ptr.contents, ctypes.POINTER(self._ctype))
        return np.ctypeslib.as_array(arr, shape=shape).tolist()

class PtrToPtrToPtr:
    # A pointer to a pointer to a pointer (typically to create a pointer to an array)

    #ctypes.c_int32, ctypes.c_float
    def __init__(self, ctype):
        self._ctype = ctype

        array = ctypes.pointer(ctype())
        innerPtr = ctypes.pointer(ctypes.cast(array, ctypes.POINTER(ctype)))
        self._ptr = ctypes.pointer(innerPtr)

    @property
    def ptr(self):
        return self._ptr

    def getArrays(self, shapes):
        # The second pointer might have changed so we cannot just return the initial array
        arrays = []
        numArray = len(shapes)

        for i in range(numArray):
            pInner =  ctypes.cast(self._ptr[0], ctypes.POINTER(ctypes.c_void_p))
            arr = ctypes.cast(pInner[i], ctypes.POINTER(self._ctype))
            arr = np.ctypeslib.as_array(arr, shape=(shapes[i], )).tolist()
            arrays.append(arr)
        return arrays

class MCsquareSharedLib():
    _libsparseMat = ctypes.CDLL(os.path.join(MCsquareModule.__path__[0], "libMCsquare.so"))

    def __init__(self, mcsquarePath=None):
        pass

    def computeBeamletsSharedLib(self, configFile:str, nVoxels:int, nSpots:int) -> csc_matrix:
        Ai = PtrToPtr(ctypes.c_int32)
        Ap = PtrToPtr(ctypes.c_int32)
        Ax = PtrToPtr(ctypes.c_float)
        nnz = Ptr(ctypes.c_int32)
        columns = Ptr(ctypes.c_int32)

        self._libsparseMat.computeBeamletsSparseMat(ctypes.create_string_buffer(configFile.encode('ASCII')), Ap.ptr, Ai.ptr, Ax.ptr, nnz.ptr, columns.ptr)

        nnzVal = nnz.value
        columnsVal = columns.value

        beamletMat = csc_matrix((Ax.getArray((nnzVal, )), Ai.getArray((nnzVal, )), Ap.getArray((columnsVal+1, ))), shape=(nVoxels, nSpots))

        _print_memory_usage(beamletMat)

        return beamletMat


    def computeBeamletsSharedLib2(self, configFile:str, nVoxels:int, nSpots:int) -> csc_matrix:
        #TODO Empty beamlet
        rowVal = PtrToPtrToPtr(ctypes.c_float)
        rowIndex = PtrToPtrToPtr(ctypes.c_int32)
        rowIndexContNb = PtrToPtrToPtr(ctypes.c_int32)
        rowIndexLen = PtrToPtr(ctypes.c_int32)
        colIndex = PtrToPtr(ctypes.c_int32)
        columns = Ptr(ctypes.c_int32)

        self._libsparseMat.computeBeamlets(ctypes.create_string_buffer(configFile.encode('ASCII')), rowVal.ptr, rowIndex.ptr,
                                     rowIndexContNb.ptr, rowIndexLen.ptr, colIndex.ptr, columns.ptr)
        rowValPtr = rowVal.ptr
        rowIndexPtr = rowIndex.ptr
        rowIndexContNbPtr = rowIndexContNb.ptr
        rowIndexLenPtr = rowIndexLen.ptr
        colIndexPtr = colIndex.ptr
        columnsPtr = columns.ptr

        import time
        start_time = time.time()

        columns = columns.value
        colIndex = colIndex.getArray((columns, ))
        rowIndexLen = rowIndexLen.getArray((columns, ))
        rowIndexContNb = rowIndexContNb.getArrays(rowIndexLen)
        rowIndex =  rowIndex.getArrays(rowIndexLen)

        rowValNums = []
        for spotInd in range(nSpots):
            if rowIndexLen[spotInd]>0:
                rowValNums.append(np.sum(rowIndexContNb[spotInd], axis=0))
            else:
                rowValNums.append(0)

        rowVal = rowVal.getArrays(rowValNums)

        beamletMat = None
        for spotInd in range(nSpots):
            cumContValNb = 0
            nbVal = rowValNums[spotInd]

            if nbVal==0:
                print("Sckipping beamlet " + str(spotInd))
                continue

            spotRowInd = []

            for rowInd in range(len(rowIndex[spotInd])):
                rowStart = rowIndex[spotInd][rowInd]
                contValNb = rowIndexContNb[spotInd][rowInd]

                for i in range(contValNb):
                    spotRowInd.append(rowStart +i)

                cumContValNb += contValNb

            A = csc_matrix((rowVal[spotInd], (spotRowInd, np.zeros((nbVal, )))), shape=(nVoxels, 1),
                           dtype=np.float32)

            if beamletMat is None:
                beamletMat = A
            else:
                beamletMat = hstack([beamletMat, A])

        print(str(nSpots) + " beamlets read in %s seconds" % (time.time() - start_time))
        _print_memory_usage(beamletMat)

        #libsparseMat.freeSparseMat(rowValPtr, rowIndexPtr, rowIndexContNbPtr, rowIndexLenPtr, colIndexPtr, columnsPtr)

        return beamletMat
