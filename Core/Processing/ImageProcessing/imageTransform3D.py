from math import pi, cos, sin
from typing import Sequence

import numpy as np
from numpy import linalg
from scipy.ndimage import zoom, affine_transform

from Core.Data.Images.image3D import Image3D
from Core.Data.Plan.planIonBeam import PlanIonBeam


class ImageTransform3D:
    @staticmethod
    def dicomToIECGantry(image:Image3D, beam:PlanIonBeam, fillValue:float=0) -> Image3D:
        spacing = np.array(image.spacing)

        tform = ImageTransform3D._forwardDicomToIECGantry(image, beam)
        tform = linalg.inv(tform)

        imageArray = zoom(image.imageArray, spacing, cval=fillValue)
        imageArray = affine_transform(imageArray, tform, cval=fillValue)
        imageArray = zoom(imageArray, np.array([1., 1., 1.])/spacing, cval=fillValue)

        outImage = image.copy()
        outImage.imageArray = imageArray

        return outImage

    @staticmethod
    def dicomCoordinate2iecGantry(image:Image3D, beam:PlanIonBeam, point:Sequence[float]) -> Sequence[float]:
        u = point[0]
        v = point[1]
        w = point[2]

        tform = ImageTransform3D._forwardDicomToIECGantry(image, beam)

        u = u - image.origin[0]
        v = v - image.origin[1]
        w = w - image.origin[2]

        [x, y, z] = ImageTransform3D._transformPointsForward(tform, u, v, w);

        x = x + image.origin[0]
        y = y + image.origin[1]
        z = z + image.origin[2]

        return (x, y, z)

    @staticmethod
    def iecGantryToDicom(image:Image3D, beam:PlanIonBeam, fillValue:float=0) -> Image3D:
        spacing = np.array(image.spacing)

        tform = ImageTransform3D._forwardDicomToIECGantry(image, beam)

        imageArray = zoom(image.imageArray, spacing, cval=fillValue)
        imageArray = affine_transform(imageArray, tform, cval=fillValue)
        imageArray = zoom(imageArray, np.array([1., 1., 1.]) / spacing, cval=fillValue)

        outImage = image.copy()
        outImage.imageArray = imageArray

        return outImage

    @staticmethod
    def iecGantryCoordinatetoDicom(image: Image3D, beam: PlanIonBeam, point: Sequence[float]) -> Sequence[float]:
        u = point[0]
        v = point[1]
        w = point[2]

        tform = ImageTransform3D._forwardDicomToIECGantry(image, beam)
        tform = linalg.inv(tform)

        u = u - image.origin[0]
        v = v - image.origin[1]
        w = w - image.origin[2]

        [x, y, z] = ImageTransform3D._transformPointsForward(tform, u, v, w);

        x = x + image.origin[0]
        y = y + image.origin[1]
        z = z + image.origin[2]

        return (x, y, z)

    @staticmethod
    def _transformPointsForward(tform: np.ndarray, u:float, v:float, w:float):
        res = tform @ np.array([u, v, w, 1])

        return res[:-1]

    @staticmethod
    def _forwardDicomToIECGantry(image:Image3D, beam:PlanIonBeam) -> np.ndarray:
        isocenter = beam.isocenterPosition
        gantryAngle = beam.gantryAngle
        patientSupportAngle = beam.patientSupportAngle

        orig = np.array(isocenter) - np.array(image.origin)

        M = ImageTransform3D._roll(-gantryAngle, [0, 0, 0]) @ \
            ImageTransform3D._rot(patientSupportAngle, [0, 0, 0]) @ \
            ImageTransform3D._pitch(-90, [0, 0, 0])

        Trs = [[1., 0., 0., -orig[0]],
               [0., 1., 0., -orig[1]],
               [0., 0., 1., -orig[2]],
               [0., 0., 0., 1.]]

        Flip = [[1., 0., 0., 0.],
                [0., 1., 0., 0.],
                [0., 0., -1., 0.],
                [0., 0., 0., 1.]]

        Trs = np.array(Trs)
        Flip = np.array(Flip)

        T = linalg.inv(Flip @ Trs) @ M @ Flip @ Trs

        return T


    @staticmethod
    def _roll(angle:float, offset:Sequence[float]) -> np.ndarray:
        a = pi * angle / 180.
        ca = cos(a)
        sa = sin(a)

        R = [[ca, 0., sa, offset[0]],
             [0., 1., 0., offset[1]],
             [-sa, 0., ca, offset[2]],
             [0., 0., 0., 1.]]

        return np.array(R)

    @staticmethod
    def _rot(angle:float, offset:Sequence[float]) -> np.ndarray:
        a = pi * angle / 180.
        ca = cos(a)
        sa = sin(a)

        R = [[ca, -sa, 0., offset[0]],
             [sa, ca, 0., offset[1]],
             [0., 0., 1., offset[2]],
             [0., 0., 0., 1.]]

        return np.array(R)

    @staticmethod
    def _pitch(angle:float, offset:Sequence[float]) -> np.ndarray:
        a = pi * angle / 180.
        ca = cos(a)
        sa = sin(a)

        R = [[1., 0., 0., offset[0]],
             [0., ca, -sa, offset[1]],
             [0., sa, ca, offset[2]],
             [0., 0., 0., 1.]]

        return np.array(R)
