import os
import numpy as np
import scipy.signal
import logging
import multiprocessing as mp
from functools import partial

from Core.Data.Images.deformationField import DeformationField
from Core.Processing.Registration.registration import Registration


def morphonsConv(im, k):
    return scipy.signal.fftconvolve(im, k, mode='same')

def morphonsComplexConvS(im, k):
    return scipy.signal.fftconvolve(im, np.real(k), mode='same') + scipy.signal.fftconvolve(im, np.imag(k),
                                                                                            mode='same') * 1j
def morphonsComplexConvD(im, k):
    return scipy.signal.fftconvolve(im, np.real(k), mode='same') - scipy.signal.fftconvolve(im, np.imag(k),
                                                                                            mode='same') * 1j


class RegistrationMorphons(Registration):

    def __init__(self, fixed, moving, baseResolution=2.5, nbProcesses=-1):

        Registration.__init__(self, fixed, moving)
        self.baseResolution = baseResolution
        self.nbProcesses = nbProcesses

    def compute(self):

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

        morphonsPath = os.path.abspath("./Core/Processing/Registration/Morphons_kernels")
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

        field = DeformationField()

        for s in range(len(scales)):

            # Compute grid for new scale
            newGridSize = [round(self.fixed.PixelSpacing[1] / scales[s] * self.fixed.GridSize[0]),
                             round(self.fixed.PixelSpacing[0] / scales[s] * self.fixed.GridSize[1]),
                             round(self.fixed.PixelSpacing[2] / scales[s] * self.fixed.GridSize[2])]
            newVoxelSpacing = [self.fixed.PixelSpacing[0] * (self.fixed.GridSize[1] - 1) / (newGridSize[1] - 1),
                                 self.fixed.PixelSpacing[1] * (self.fixed.GridSize[0] - 1) / (newGridSize[0] - 1),
                                 self.fixed.PixelSpacing[2] * (self.fixed.GridSize[2] - 1) / (newGridSize[2] - 1)]

            print('Morphons scale:', s + 1, '/', len(scales), ' (',
                  round(newVoxelSpacing[0] * 1e2) / 1e2, 'x',
                  round(newVoxelSpacing[1] * 1e2) / 1e2, 'x',
                  round(newVoxelSpacing[2] * 1e2) / 1e2, 'mm3)')

            # Resample fixed and moving images and field according to the considered scale (voxel spacing)
            fixedResampled = self.fixed.copy()
            fixedResampled.resample_image(newGridSize, self.fixed.ImagePositionPatient, newVoxelSpacing)
            movingResampled = self.moving.copy()
            movingResampled.resample_image(fixedResampled.GridSize, fixedResampled.ImagePositionPatient,
                                            fixedResampled.PixelSpacing)

            if s != 0:
                field.resample_to_CT_grid(fixedResampled, 'Velocity')
                certainty.resample_image(fixedResampled.GridSize, fixedResampled.ImagePositionPatient,
                                         fixedResampled.PixelSpacing, fill_value=0)
            else:
                field.Init_Field_Zeros(fixedResampled.Image.shape, Offset=fixedResampled.ImagePositionPatient,
                                       PixelSpacing=fixedResampled.PixelSpacing)
                certainty = fixedResampled.copy()
                certainty.Image = np.zeros_like(certainty.Image)

            # Compute phase on fixed image
            if (self.nbProcesses > 1):
                pconv = partial(morphonsComplexConvS, fixedResampled.Image)
                qFixed = pool.map(pconv, k)
            else:
                qFixed = []
                for n in range(6):
                    qFixed.append(scipy.signal.fftconvolve(fixedResampled.Image, np.real(k[n]),
                                                            mode='same') + scipy.signal.fftconvolve(
                        fixedResampled.Image, np.imag(k[n]), mode='same') * 1j)

            for i in range(iterations[s]):

                # Deform moving image
                deformed = movingResampled.copy()
                if s != 0 or i != 0:
                    deformed.Image = field.deform_image(deformed, fill_value='closest')

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
                    pconv = partial(morphonsComplexConvD, deformed.Image)
                    qDeformed = pool.map(pconv, k)
                else:
                    qDeformed = []
                    for n in range(6):
                        qDeformed.append(
                            scipy.signal.fftconvolve(deformed.Image, np.real(k[n]),
                                                     mode='same') - scipy.signal.fftconvolve(deformed.Image,
                                                                                             np.imag(k[n]),
                                                                                             mode='same') * 1j)

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

                fieldUpdate = np.zeros_like(field.Velocity)
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
                fieldUpdate[:, :, :, 0] = -np.divide(fieldUpdate[:, :, :, 0], det)
                fieldUpdate[:, :, :, 1] = -np.divide(fieldUpdate[:, :, :, 1], det)
                fieldUpdate[:, :, :, 2] = -np.divide(fieldUpdate[:, :, :, 2], det)

                # Accumulate field and certainty
                field.Velocity[:, :, :, 0] += np.multiply(fieldUpdate[:, :, :, 0], np.divide(certaintyUpdate,
                                                                                              certainty.Image + certaintyUpdate + eps))
                field.Velocity[:, :, :, 1] += np.multiply(fieldUpdate[:, :, :, 1], np.divide(certaintyUpdate,
                                                                                              certainty.Image + certaintyUpdate + eps))
                field.Velocity[:, :, :, 2] += np.multiply(fieldUpdate[:, :, :, 2], np.divide(certaintyUpdate,
                                                                                              certainty.Image + certaintyUpdate + eps))
                certainty.Image = np.divide(np.power(certainty.Image, 2) + np.power(certaintyUpdate, 2),
                                            certainty.Image + certaintyUpdate + eps)

                # Regularize velocity field and certainty
                self.fieldRegularization(field, filterType="NormalizedGaussian", sigma=1.25, cert=certainty.Image)
                certainty.Image = normGaussConv(certainty.Image, certainty.Image, 1.25)

        self.deformed = self.moving.copy()
        self.deformed.Image = field.deform_image(self.deformed, fill_value='closest')

        return field
