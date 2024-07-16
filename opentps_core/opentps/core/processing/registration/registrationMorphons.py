import os
import numpy as np
import scipy.signal
import logging
import multiprocessing as mp
from functools import partial

logger = logging.getLogger(__name__)

try:
    import cupy
    import cupyx.scipy.signal
except:
    logger.warning('cupy not found.')

from opentps.core.data.images._deformation3D import Deformation3D
from opentps.core.data.images._vectorField3D import VectorField3D
from opentps.core.processing.registration.registration import Registration
import opentps.core.processing.imageProcessing.filter3D as imageFilter3D
import opentps.core.processing.registration.morphonsCupy as morphonsCupy



def morphonsConv(im, k):
    return scipy.signal.fftconvolve(im, k, mode='same')


def morphonsComplexConvS(im, k):
    return scipy.signal.fftconvolve(im, np.real(k), mode='same') + scipy.signal.fftconvolve(im, np.imag(k), mode='same') * 1j


def morphonsComplexConvD(im, k):
    return scipy.signal.fftconvolve(im, np.real(k), mode='same') - scipy.signal.fftconvolve(im, np.imag(k), mode='same') * 1j


def applyMorphonsKernels(image, k, is_fixed=1, tryGPU=True):
    output = []
    if image._imageArray.size > 1e5 and tryGPU:
        try:
            # print('in registration morphons applyMorphonsKernels cupy used')
            data = cupy.asarray(image._imageArray)
            for n in range(6):
                if(is_fixed):
                    output.append(cupy.asnumpy(cupyx.scipy.signal.fftconvolve(data, cupy.asarray(np.real(k[n])), mode='same')) + cupy.asnumpy(cupyx.scipy.signal.fftconvolve(data, cupy.asarray(np.imag(k[n])), mode='same')) * 1j)
                else:
                    output.append(cupy.asnumpy(cupyx.scipy.signal.fftconvolve(data, cupy.asarray(np.real(k[n])), mode='same')) - cupy.asnumpy(cupyx.scipy.signal.fftconvolve(data, cupy.asarray(np.imag(k[n])), mode='same')) * 1j)
        except:
            logger.warning('cupy not used for morphons kernel convolution.')

    if(len(output)==0):
        for n in range(6):
            if (is_fixed):
                output.append(scipy.signal.fftconvolve(image._imageArray, np.real(k[n]), mode='same') + scipy.signal.fftconvolve(image._imageArray, np.imag(k[n]), mode='same') * 1j)
            else:
                output.append(scipy.signal.fftconvolve(image._imageArray, np.real(k[n]), mode='same') - scipy.signal.fftconvolve(image._imageArray, np.imag(k[n]), mode='same') * 1j)

    return output


class RegistrationMorphons(Registration):
    """
    Class for performing registration using morphons kernels. inherited from Registration class.

    Attributes
    ----------
    fixed : Image3D
        Fixed image.
    moving : Image3D
        Moving image.
    baseResolution : float
        Base resolution for registration.
    nbProcesses : int
        Number of processes to use for registration.
    tryGPU : bool
        Try to use GPU for registration.

    """
    def __init__(self, fixed, moving, baseResolution=2.5, nbProcesses=-1, tryGPU=True):

        Registration.__init__(self, fixed, moving)
        self.baseResolution = baseResolution
        self.nbProcesses = nbProcesses
        self.tryGPU = tryGPU

    def compute(self):

        """Perform registration between fixed and moving images.

            Returns
            -------
            numpy array
                Deformation from moving to fixed images.
            """

        if self.tryGPU:
            try:
                velocity, deformed = morphonsCupy.computeMorphonsCupy(self.fixed.imageArray, self.fixed.origin, self.fixed.spacing, self.moving.imageArray, self.moving.origin, self.moving.spacing, self.baseResolution)
                spacing = np.array([self.baseResolution,self.baseResolution,self.baseResolution])
                deformation = Deformation3D(origin=self.fixed.origin, spacing=spacing, velocity=VectorField3D(imageArray=cupy.asnumpy(velocity), name="velocity", origin=self.fixed.origin, spacing=spacing))
                self.deformed = self.fixed.copy()
                self.deformed._imageArray = deformed
                self.deformed.setName(self.moving.name + '_registered_to_' + self.fixed.name)
                return deformation
            except:
                logger.info('Failed to use full CuPy implementation. Try CPU instead.')

        if self.nbProcesses < 0:
            self.nbProcesses = min(mp.cpu_count(), 6)

        if self.nbProcesses > 1:
            pool = mp.Pool(self.nbProcesses)

        eps = np.finfo("float64").eps
        eps32 = np.finfo("float32").eps
        scales = self.baseResolution * np.asarray([11.3137, 8.0, 5.6569, 4.0, 2.8284, 2.0, 1.4142, 1.0])
        iterations = [10, 10, 10, 10, 10, 10, 5, 2]
        qDirections = [[0, 0.5257, 0.8507], [0, -0.5257, 0.8507], [0.5257, 0.8507, 0], [-0.5257, 0.8507, 0],
                       [0.8507, 0, 0.5257], [0.8507, 0, -0.5257]]

        morphonsPath = os.path.join(os.path.dirname(__file__), 'Morphons_kernels')
        k = []
        k.append(np.reshape(
            np.float32(np.fromfile(os.path.join(morphonsPath, "kernel1_real.bin"), dtype="float64")) + np.float32(
                np.fromfile(os.path.join(morphonsPath, "kernel1_imag.bin"), dtype="float64")) * 1j, (9, 9, 9)))
        k.append(np.reshape(
            np.float32(np.fromfile(os.path.join(morphonsPath, "kernel2_real.bin"), dtype="float64")) + np.float32(
                np.fromfile(os.path.join(morphonsPath, "kernel2_imag.bin"), dtype="float64")) * 1j, (9, 9, 9)))
        k.append(np.reshape(
            np.float32(np.fromfile(os.path.join(morphonsPath, "kernel3_real.bin"), dtype="float64")) + np.float32(
                np.fromfile(os.path.join(morphonsPath, "kernel3_imag.bin"), dtype="float64")) * 1j, (9, 9, 9)))
        k.append(np.reshape(
            np.float32(np.fromfile(os.path.join(morphonsPath, "kernel4_real.bin"), dtype="float64")) + np.float32(
                np.fromfile(os.path.join(morphonsPath, "kernel4_imag.bin"), dtype="float64")) * 1j, (9, 9, 9)))
        k.append(np.reshape(
            np.float32(np.fromfile(os.path.join(morphonsPath, "kernel5_real.bin"), dtype="float64")) + np.float32(
                np.fromfile(os.path.join(morphonsPath, "kernel5_imag.bin"), dtype="float64")) * 1j, (9, 9, 9)))
        k.append(np.reshape(
            np.float32(np.fromfile(os.path.join(morphonsPath, "kernel6_real.bin"), dtype="float64")) + np.float32(
                np.fromfile(os.path.join(morphonsPath, "kernel6_imag.bin"), dtype="float64")) * 1j, (9, 9, 9)))

        deformation = Deformation3D()

        for s in range(len(scales)):

            # Compute grid for new scale
            newGridSize = np.array([round(self.fixed.spacing[1] / scales[s] * self.fixed.gridSize[0]),
                           round(self.fixed.spacing[0] / scales[s] * self.fixed.gridSize[1]),
                           round(self.fixed.spacing[2] / scales[s] * self.fixed.gridSize[2])])
            newVoxelSpacing = np.array([self.fixed.spacing[0] * (self.fixed.gridSize[1] - 1) / (newGridSize[1] - 1),
                               self.fixed.spacing[1] * (self.fixed.gridSize[0] - 1) / (newGridSize[0] - 1),
                               self.fixed.spacing[2] * (self.fixed.gridSize[2] - 1) / (newGridSize[2] - 1)])

            if(newVoxelSpacing[0]<self.fixed.spacing[0] and newVoxelSpacing[1]<self.fixed.spacing[1] and newVoxelSpacing[2]<self.fixed.spacing[2]):
                break

            logger.info('Morphons scale:' + str(s + 1) + '/' + str(len(scales)) + ' (' + str(round(newVoxelSpacing[0] * 1e2) / 1e2 ) + 'x' + str(round(newVoxelSpacing[1] * 1e2) / 1e2) + 'x' + str(round(newVoxelSpacing[2] * 1e2) / 1e2) + 'mm3)')

            # Resample fixed and moving images and deformation according to the considered scale (voxel spacing)
            fixedResampled = self.fixed.copy()
            fixedResampled.resample(newVoxelSpacing, newGridSize, self.fixed.origin, tryGPU=self.tryGPU)
            movingResampled = self.moving.copy()
            movingResampled.resample(fixedResampled.spacing, fixedResampled.gridSize, fixedResampled.origin, tryGPU=self.tryGPU)

            if s != 0:
                deformation.resample(fixedResampled.spacing, fixedResampled.gridSize, fixedResampled.origin, tryGPU=self.tryGPU)
                certainty.resample(fixedResampled.spacing, fixedResampled.gridSize, fixedResampled.origin, fillValue=0, tryGPU=self.tryGPU)
            else:
                deformation.initFromImage(fixedResampled)
                certainty = fixedResampled.copy()
                certainty._imageArray = np.zeros_like(certainty._imageArray)

            # Compute phase on fixed image
            if (self.nbProcesses > 1):
                pconv = partial(morphonsComplexConvS, fixedResampled._imageArray)
                qFixed = pool.map(pconv, k)
            else:
                qFixed = applyMorphonsKernels(fixedResampled, k, is_fixed=1, tryGPU=self.tryGPU)

            for i in range(iterations[s]):

                # Deform moving image then reset displacement field
                deformed = deformation.deformImage(movingResampled, fillValue='closest', tryGPU=self.tryGPU)
                deformation.displacement = None

                # Compute phase difference
                a11 = np.zeros_like(qFixed[0], dtype="float64")
                a12 = np.zeros_like(qFixed[0], dtype="float64")
                a13 = np.zeros_like(qFixed[0], dtype="float64")
                a22 = np.zeros_like(qFixed[0], dtype="float64")
                a23 = np.zeros_like(qFixed[0], dtype="float64")
                a33 = np.zeros_like(qFixed[0], dtype="float64")
                b1 = np.zeros_like(qFixed[0], dtype="float64")
                b2 = np.zeros_like(qFixed[0], dtype="float64")
                b3 = np.zeros_like(qFixed[0], dtype="float64")

                if (self.nbProcesses > 1):
                    pconv = partial(morphonsComplexConvD, deformed.imageArray)
                    qDeformed = pool.map(pconv, k)
                else:
                    qDeformed = applyMorphonsKernels(deformed, k, is_fixed=0, tryGPU=self.tryGPU)

                for n in range(6):
                    qq = np.multiply(qFixed[n], qDeformed[n])

                    vk = np.divide(np.imag(qq), np.absolute(qq) + eps32)
                    ck2 = np.multiply(np.sqrt(np.absolute(qq)), np.power(np.cos(np.divide(vk, 2)), 4))
                    vk = np.multiply(vk, ck2)

                    # Add contributions to the equation system
                    b1 += qDirections[n][0] * vk
                    a11 += qDirections[n][0] * qDirections[n][0] * ck2
                    a12 += qDirections[n][0] * qDirections[n][1] * ck2
                    a13 += qDirections[n][0] * qDirections[n][2] * ck2
                    b2 += qDirections[n][1] * vk
                    a22 += qDirections[n][1] * qDirections[n][1] * ck2
                    a23 += qDirections[n][2] * qDirections[n][1] * ck2
                    b3 += qDirections[n][2] * vk
                    a33 += qDirections[n][2] * qDirections[n][2] * ck2

                fieldUpdate = np.zeros_like(deformation.velocity.imageArray)
                fieldUpdate[:, :, :, 0] = (a22 * a33 - np.power(a23, 2)) * b1 + (a13 * a23 - a12 * a33) * b2 + (
                        a12 * a23 - a13 * a22) * b3
                fieldUpdate[:, :, :, 1] = (a13 * a23 - a12 * a33) * b1 + (a11 * a33 - np.power(a13, 2)) * b2 + (
                        a12 * a13 - a11 * a23) * b3
                fieldUpdate[:, :, :, 2] = (a12 * a23 - a13 * a22) * b1 + (a12 * a13 - a11 * a23) * b2 + (
                        a11 * a22 - np.power(a12, 2)) * b3
                certaintyUpdate = a11 + a22 + a33

                # Corrections
                det = a11 * a22 * a33 + 2 * a12 * a13 * a23 - np.power(a13, 2) * a22 - a11 * np.power(a23,
                                                                                                      2) - np.power(a12,
                                                                                                                    2) * a33

                z = (det == 0)
                det[z] = 1
                fieldUpdate[z, 0] = 0
                fieldUpdate[z, 1] = 0
                fieldUpdate[z, 2] = 0
                certaintyUpdate[z] = 0
                fieldUpdate[:, :, :, 0] = -np.divide(fieldUpdate[:, :, :, 0], det)*deformation.velocity.spacing[0]
                fieldUpdate[:, :, :, 1] = -np.divide(fieldUpdate[:, :, :, 1], det)*deformation.velocity.spacing[1]
                fieldUpdate[:, :, :, 2] = -np.divide(fieldUpdate[:, :, :, 2], det)*deformation.velocity.spacing[2]

                # Accumulate deformation and certainty
                fieldUpdate[:, :, :, 0] = deformation.velocity.imageArray[:, :, :, 0] + np.multiply(fieldUpdate[:, :, :, 0], np.divide(certaintyUpdate, certainty.imageArray + certaintyUpdate + eps))
                fieldUpdate[:, :, :, 1] = deformation.velocity.imageArray[:, :, :, 1] + np.multiply(fieldUpdate[:, :, :, 1], np.divide(certaintyUpdate, certainty.imageArray + certaintyUpdate + eps))
                fieldUpdate[:, :, :, 2] = deformation.velocity.imageArray[:, :, :, 2] + np.multiply(fieldUpdate[:, :, :, 2], np.divide(certaintyUpdate, certainty.imageArray + certaintyUpdate + eps))
                deformation.setVelocityArray(fieldUpdate)
                certainty._imageArray = np.divide(np.power(certainty.imageArray, 2) + np.power(certaintyUpdate, 2), certainty.imageArray + certaintyUpdate + eps)

                # Regularize velocity deformation and certainty
                self.regularizeField(deformation, filterType="NormalizedGaussian", sigma=1.25, cert=certainty.imageArray, tryGPU=self.tryGPU)
                certainty._imageArray = imageFilter3D.normGaussConv(certainty.imageArray, certainty.imageArray, 1.25, tryGPU=self.tryGPU)

        self.deformed = deformation.deformImage(self.moving, fillValue='closest', tryGPU=self.tryGPU)
        self.deformed.setName(self.moving.name + '_registered_to_' + self.fixed.name)

        return deformation
