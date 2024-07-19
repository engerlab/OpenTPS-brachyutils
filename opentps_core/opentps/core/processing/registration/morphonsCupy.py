import os
import numpy as np
import math
import logging

logger = logging.getLogger(__name__)

try:
    import cupy
    import cupyx.scipy.signal
except:
    logger.warning('cupy not found.')
    pass


def applyMorphonsKernels(data, k, is_fixed=1):
    output = []
    for n in range(6):
         if(is_fixed):
              output.append(cupyx.scipy.signal.fftconvolve(data, cupy.real(k[n]), mode='same') + cupyx.scipy.signal.fftconvolve(data, cupy.imag(k[n]), mode='same') * 1j)
         else:
              output.append(cupyx.scipy.signal.fftconvolve(data, cupy.real(k[n]), mode='same') - cupyx.scipy.signal.fftconvolve(data, cupy.imag(k[n]), mode='same') * 1j)
    return output


def normGaussConvCupy(data, cert, sigma):
    temp_cert = cupyx.scipy.ndimage.gaussian_filter(cert, sigma=sigma, mode="constant")
    z = (temp_cert == 0)
    temp_cert[z] = 1.0
    vectorDimension = 1
    if data.ndim > 3:
        vectorDimension = data.shape[3]
    if vectorDimension > 1:
        for i in range(vectorDimension):
            temp_data = cupyx.scipy.ndimage.gaussian_filter(cupy.multiply(data[:,:,:,i], cert), sigma=sigma, mode="constant")
            temp_data[z] = 0.0
            data[:,:,:,i] = np.divide(temp_data, temp_cert)
    else:
        data = cupyx.scipy.ndimage.gaussian_filter(cupy.multiply(data, cert), sigma=sigma, mode="constant")
        data[z] = 0.0
        data = np.divide(data, temp_cert)

    cert = cupyx.scipy.ndimage.gaussian_filter(cupy.multiply(cert, cert), sigma=sigma, mode="constant")
    cert[z] = 0.0
    cert = np.divide(cert, temp_cert)

    return data, cert


def exponentiateFieldCupy(field, spacing):
    norm = cupy.square(field[:, :, :, 0]/spacing[0]) + cupy.square(field[:, :, :, 1]/spacing[1]) + cupy.square(field[:, :, :, 2]/spacing[2])
    N = math.ceil(2 + math.log2(cupy.maximum(1.0, cupy.amax(cupy.sqrt(norm)))) / 2) + 1
    if N < 1: N = 1
    field = field * 2 ** (-N)
    for r in range(N):
        new_0 = warpCupy(field[:, :, :, 0], field, spacing)
        new_1 = warpCupy(field[:, :, :, 1], field, spacing)
        new_2 = warpCupy(field[:, :, :, 2], field, spacing)
        field[:, :, :, 0] += new_0
        field[:, :, :, 1] += new_1
        field[:, :, :, 2] += new_2
    return field


def resampleCupy(input, inputOrigin, inputSpacing, outputOrigin, outputSpacing, outputGridSize, fillValue=0):
    vectorDimension = 1
    if input.ndim > 3:
        vectorDimension = input.shape[3]

    # anti-aliasing filter
    sigma = [0, 0, 0]
    if (outputSpacing[0] > inputSpacing[0]): sigma[0] = 0.4 * (outputSpacing[0] / inputSpacing[0])
    if (outputSpacing[1] > inputSpacing[1]): sigma[1] = 0.4 * (outputSpacing[1] / inputSpacing[1])
    if (outputSpacing[2] > inputSpacing[2]): sigma[2] = 0.4 * (outputSpacing[2] / inputSpacing[2])
    if (sigma != [0, 0, 0]):
        data = cupy.copy(input)
        if vectorDimension > 1:
            for i in range(vectorDimension):
                data[:, :, :, i] = cupyx.scipy.ndimage.gaussian_filter(data[:, :, :, i], sigma=sigma, truncate=2.5, mode="reflect")
        else:
            data[:, :, :] = cupyx.scipy.ndimage.gaussian_filter(data[:, :, :], sigma=sigma, truncate=2.5, mode="reflect")
    else:
        data = input

    interpX = (outputOrigin[0] - inputOrigin[0] + cupy.arange(outputGridSize[0]) * outputSpacing[0]) / inputSpacing[0]
    interpY = (outputOrigin[1] - inputOrigin[1] + cupy.arange(outputGridSize[1]) * outputSpacing[1]) / inputSpacing[1]
    interpZ = (outputOrigin[2] - inputOrigin[2] + cupy.arange(outputGridSize[2]) * outputSpacing[2]) / inputSpacing[2]

    xi = cupy.array(cupy.meshgrid(interpX, interpY, interpZ))
    xi = cupy.rollaxis(xi, 0, 4)
    xi = xi.reshape((xi.size // 3, 3))

    if vectorDimension > 1:
        field = cupy.zeros((*outputGridSize, vectorDimension))
        for i in range(vectorDimension):
            fieldTemp = cupyx.scipy.ndimage.map_coordinates(data[:, :, :, i], xi.T, order=1, mode='nearest', cval=fillValue)
            field[:, :, :, i] = fieldTemp.reshape((outputGridSize[1], outputGridSize[0], outputGridSize[2])).transpose(1, 0, 2)
        return field
    else:
        data = cupyx.scipy.ndimage.map_coordinates(data, xi.T, order=1, mode='nearest', cval=fillValue)
        return data.reshape((outputGridSize[1], outputGridSize[0], outputGridSize[2])).transpose(1, 0, 2)


def warpCupy(data, displacement, displacementSpacing, dataSpacing=None, displacementOrigin=None, dataOrigin=None):
    if dataSpacing is None:
        dataSpacing = displacementSpacing
    if displacementOrigin is None:
        displacementOrigin = [0,0,0]
    if dataOrigin is None:
        dataOrigin = displacementOrigin

    size = displacement.shape
    vectorDimension = 1
    if data.ndim > 3:
        vectorDimension = size[3]

    interpX = (displacementOrigin[0] - dataOrigin[0] + cupy.arange(size[0]) * displacementSpacing[0]) / dataSpacing[0]
    interpY = (displacementOrigin[1] - dataOrigin[1] + cupy.arange(size[1]) * displacementSpacing[1]) / dataSpacing[1]
    interpZ = (displacementOrigin[2] - dataOrigin[2] + cupy.arange(size[2]) * displacementSpacing[2]) / dataSpacing[2]
    xi = cupy.array(cupy.meshgrid(interpX, interpY, interpZ))
    xi = cupy.rollaxis(xi, 0, 4)
    xi = xi.reshape((xi.size // 3, 3))
    xi[:, 0] += displacement[:, :, :, 0].transpose(1, 0, 2).reshape((xi.shape[0],)) / displacementSpacing[0]
    xi[:, 1] += displacement[:, :, :, 1].transpose(1, 0, 2).reshape((xi.shape[0],)) / displacementSpacing[1]
    xi[:, 2] += displacement[:, :, :, 2].transpose(1, 0, 2).reshape((xi.shape[0],)) / displacementSpacing[2]

    if vectorDimension > 1:
        field = cupy.zeros_like(data)
        for i in range(vectorDimension):
            fieldTemp = cupyx.scipy.ndimage.map_coordinates(data[:, :, :, i], xi.T, order=1, mode='nearest')
            field[:, :, :, i] = fieldTemp.reshape((size[1], size[0], size[2])).transpose(
                1, 0, 2)
        data = field
    else:
        data = cupyx.scipy.ndimage.map_coordinates(data, xi.T, order=1, mode='nearest')
        data = data.reshape((size[1], size[0], size[2])).transpose(1, 0, 2)

    return data


def computeMorphonsCupy(fixed,fixedOrigin,fixedSpacing,moving,movingOrigin,movingSpacing,baseResolution,priorVelocity=None,threshold=0):

    eps32 = cupy.finfo("float32").eps
    sigmaRegularization = 1.25
    scales = baseResolution * np.asarray([11.3137, 8.0, 5.6569, 4.0, 2.8284, 2.0, 1.4142, 1.0])
    iterations = [10, 10, 10, 10, 10, 10, 5, 2]
    qDirections = [[0, 0.5257, 0.8507], [0, -0.5257, 0.8507], [0.5257, 0.8507, 0], [-0.5257, 0.8507, 0],
                   [0.8507, 0, 0.5257], [0.8507, 0, -0.5257]]
    morphonsPath = os.path.join(os.path.dirname(__file__), 'Morphons_kernels')
    k = []
    k.append(cupy.asarray(np.reshape(
        np.float32(np.fromfile(os.path.join(morphonsPath, "kernel1_real.bin"), dtype="float64")) + np.float32(
            np.fromfile(os.path.join(morphonsPath, "kernel1_imag.bin"), dtype="float64")) * 1j, (9, 9, 9))))
    k.append(cupy.asarray(np.reshape(
        np.float32(np.fromfile(os.path.join(morphonsPath, "kernel2_real.bin"), dtype="float64")) + np.float32(
            np.fromfile(os.path.join(morphonsPath, "kernel2_imag.bin"), dtype="float64")) * 1j, (9, 9, 9))))
    k.append(cupy.asarray(np.reshape(
        np.float32(np.fromfile(os.path.join(morphonsPath, "kernel3_real.bin"), dtype="float64")) + np.float32(
            np.fromfile(os.path.join(morphonsPath, "kernel3_imag.bin"), dtype="float64")) * 1j, (9, 9, 9))))
    k.append(cupy.asarray(np.reshape(
        np.float32(np.fromfile(os.path.join(morphonsPath, "kernel4_real.bin"), dtype="float64")) + np.float32(
            np.fromfile(os.path.join(morphonsPath, "kernel4_imag.bin"), dtype="float64")) * 1j, (9, 9, 9))))
    k.append(cupy.asarray(np.reshape(
        np.float32(np.fromfile(os.path.join(morphonsPath, "kernel5_real.bin"), dtype="float64")) + np.float32(
            np.fromfile(os.path.join(morphonsPath, "kernel5_imag.bin"), dtype="float64")) * 1j, (9, 9, 9))))
    k.append(cupy.asarray(np.reshape(
        np.float32(np.fromfile(os.path.join(morphonsPath, "kernel6_real.bin"), dtype="float64")) + np.float32(
            np.fromfile(os.path.join(morphonsPath, "kernel6_imag.bin"), dtype="float64")) * 1j, (9, 9, 9))))

    fixedGridSize = np.array(fixed.shape)
    fixed = cupy.asarray(fixed, dtype='float32')
    moving = cupy.asarray(moving, dtype='float32')

    for s in range(len(scales)):

        usePriorVelocity = not (priorVelocity is None) and s<3

        # Compute grid for new scale
        gridSize = np.array([round(fixedSpacing[1] / scales[s] * fixedGridSize[0]),
                             round(fixedSpacing[0] / scales[s] * fixedGridSize[1]),
                             round(fixedSpacing[2] / scales[s] * fixedGridSize[2])])
        spacing = np.array([fixedSpacing[0] * (fixedGridSize[1] - 1) / (gridSize[1] - 1),
                            fixedSpacing[1] * (fixedGridSize[0] - 1) / (gridSize[0] - 1),
                            fixedSpacing[2] * (fixedGridSize[2] - 1) / (gridSize[2] - 1)])

        if(spacing[0]<fixedSpacing[0] and spacing[1]<fixedSpacing[1] and spacing[2]<fixedSpacing[2]):
            break

        print('Morphons scale:' + str(s + 1) + '/' + str(len(scales)) + ' (' + str
            (round(spacing[0] * 1e2) / 1e2 ) + 'x' + str(round(spacing[1] * 1e2) / 1e2) + 'x' + str
            (round(spacing[2] * 1e2) / 1e2) + 'mm3)')

        # Resample fixed and moving images and deformation according to the considered scale (voxel spacing)
        fixedResampled = resampleCupy(fixed, fixedOrigin, fixedSpacing, fixedOrigin, spacing, gridSize, fillValue=-1000)
        movingResampled = resampleCupy(moving, movingOrigin, movingSpacing, fixedOrigin, spacing, gridSize, fillValue=-1000)
        if usePriorVelocity:
            priorVelocityResampled = cupy.asarray(priorVelocity)
            priorVelocityResampled = resampleCupy(priorVelocityResampled, fixedOrigin, fixedSpacing, fixedOrigin, spacing, gridSize, fillValue=0)

        if s != 0:
            velocity = resampleCupy(velocity, fixedOrigin, previousSpacing, fixedOrigin, spacing, gridSize, fillValue=0)
            certainty = resampleCupy(certainty, fixedOrigin, previousSpacing, fixedOrigin, spacing, gridSize, fillValue=0)
        else:
            velocity = cupy.zeros((gridSize[0], gridSize[1], gridSize[2], 3), dtype="float32")
            certainty = cupy.zeros_like(fixedResampled, dtype="float32")

        previousSpacing = spacing

        # Compute phase on fixed image
        qFixed = applyMorphonsKernels(fixedResampled, k, is_fixed=1)

        for i in range(iterations[s]):

            # Deform moving image then reset displacement field
            displacement = exponentiateFieldCupy(velocity, spacing)
            deformed = warpCupy(movingResampled, displacement, spacing)

            # Compute phase difference
            a11 = cupy.zeros_like(qFixed[0], dtype="float32")
            a12 = cupy.zeros_like(qFixed[0], dtype="float32")
            a13 = cupy.zeros_like(qFixed[0], dtype="float32")
            a22 = cupy.zeros_like(qFixed[0], dtype="float32")
            a23 = cupy.zeros_like(qFixed[0], dtype="float32")
            a33 = cupy.zeros_like(qFixed[0], dtype="float32")
            b1 = cupy.zeros_like(qFixed[0], dtype="float32")
            b2 = cupy.zeros_like(qFixed[0], dtype="float32")
            b3 = cupy.zeros_like(qFixed[0], dtype="float32")

            qDeformed = applyMorphonsKernels(deformed, k, is_fixed=0)

            for n in range(6):
                qq = cupy.multiply(qFixed[n], qDeformed[n])

                vk = cupy.divide(cupy.imag(qq), cupy.absolute(qq) + eps32)
                ck2 = cupy.multiply(cupy.sqrt(cupy.absolute(qq)), cupy.power(cupy.cos(cupy.divide(vk, 2)), 4))
                vk = cupy.multiply(vk, ck2)

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

            fieldUpdate = cupy.zeros_like(velocity)
            fieldUpdate[:, :, :, 0] = (a22 * a33 - cupy.power(a23, 2)) * b1 + (a13 * a23 - a12 * a33) * b2 + (
                    a12 * a23 - a13 * a22) * b3
            fieldUpdate[:, :, :, 1] = (a13 * a23 - a12 * a33) * b1 + (a11 * a33 - cupy.power(a13, 2)) * b2 + (
                    a12 * a13 - a11 * a23) * b3
            fieldUpdate[:, :, :, 2] = (a12 * a23 - a13 * a22) * b1 + (a12 * a13 - a11 * a23) * b2 + (
                    a11 * a22 - cupy.power(a12, 2)) * b3
            certaintyUpdate = a11 + a22 + a33

            # Corrections
            det = a11 * a22 * a33 + 2 * a12 * a13 * a23 - cupy.power(a13, 2) * a22 - a11 * cupy.power(a23, 2) - cupy.power(a12, 2) * a33

            z = (det == 0)
            det[z] = 1
            fieldUpdate[z, 0] = 0
            fieldUpdate[z, 1] = 0
            fieldUpdate[z, 2] = 0
            certaintyUpdate[z] = 0
            fieldUpdate[:, :, :, 0] = -cupy.divide(fieldUpdate[:, :, :, 0], det ) *spacing[0]
            fieldUpdate[:, :, :, 1] = -cupy.divide(fieldUpdate[:, :, :, 1], det ) *spacing[1]
            fieldUpdate[:, :, :, 2] = -cupy.divide(fieldUpdate[:, :, :, 2], det ) *spacing[2]

            # Accumulate deformation and certainty
            fieldUpdate[:, :, :, 0] = velocity[:, :, :, 0] + cupy.multiply(fieldUpdate[:, :, :, 0], cupy.divide(certaintyUpdate, certainty + certaintyUpdate + eps32))
            fieldUpdate[:, :, :, 1] = velocity[:, :, :, 1] + cupy.multiply(fieldUpdate[:, :, :, 1], cupy.divide(certaintyUpdate, certainty + certaintyUpdate + eps32))
            fieldUpdate[:, :, :, 2] = velocity[:, :, :, 2] + cupy.multiply(fieldUpdate[:, :, :, 2], cupy.divide(certaintyUpdate, certainty + certaintyUpdate + eps32))
            velocity = fieldUpdate
            certainty = cupy.divide(cupy.power(certainty, 2) + cupy.power(certaintyUpdate, 2), certainty + certaintyUpdate + eps32)

            # Correct velocity with prior if required
            if usePriorVelocity:
                # velocity = priorVelocityResampled
                velocity[fixedResampled > threshold, :] = priorVelocityResampled[fixedResampled > threshold, :]
                certainty[fixedResampled > threshold] = cupy.amax(certainty)

            # Regularize velocity deformation and certainty
            velocity, certainty = normGaussConvCupy(velocity, certainty, sigmaRegularization)

    velocityResampled = resampleCupy(velocity, fixedOrigin, previousSpacing, fixedOrigin, fixedSpacing, fixedGridSize, fillValue=0)
    displacement = exponentiateFieldCupy(velocityResampled, fixedSpacing)
    deformed = warpCupy(cupy.asarray(moving), displacement, fixedSpacing, movingSpacing, fixedOrigin, movingOrigin)

    return cupy.asnumpy(velocityResampled), cupy.asnumpy(deformed)
