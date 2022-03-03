import logging
import numpy as np
import tigre
from tigre.utilities import CTnoise

logger = logging.getLogger(__name__)

def forwardProjectionTigre(ct, angles, orientation='Z', options=None):

    if isinstance(angles, list):
        angles = np.array(angles)
    else:
        angles = np.array([angles])

    # Convert CT to attenuation in correct orientation
    mu_water = 0.0215
    if orientation == 'Z':
        im = np.transpose(np.float32(ct.imageArray) * mu_water / 1000 + mu_water, [2, 1, 0])
        ctOrigin = ct.origin[::-1]
        ctSpacing = ct.spacing[::-1]
        ctGridSize = ct.gridSize[::-1]
    if orientation == 'X':
        im = np.float32(ct.imageArray) * mu_water / 1000 + mu_water
        ctOrigin = ct.origin
        ctSpacing = ct.spacing
        ctGridSize = ct.gridSize
    if orientation == 'Y':
        im = np.transpose(np.float32(ct.imageArray) * mu_water / 1000 + mu_water, [1, 0, 2])
        ctOrigin = np.array([ct.origin[1],ct.origin[0],ct.origin[2]])
        ctSpacing = np.array([ct.spacing[1],ct.spacing[0],ct.spacing[2]])
        ctGridSize = np.array([ct.gridSize[1],ct.gridSize[0],ct.gridSize[2]])


    ctCenter = ctOrigin + ctGridSize * ctSpacing / 2
    ctIsocenter = ctCenter.copy()
    # ctIsocenter = plan.isocenterPosition[::-1]

    #  Geometry definition
    #           -nVoxel:        3x1 array of number of voxels in the image
    #           -sVoxel:        3x1 array with the total size in mm of the image
    #           -dVoxel:        3x1 array with the size of each of the voxels in mm
    #           -nDetector:     2x1 array of number of voxels in the detector plane
    #           -sDetector:     2x1 array with the total size in mm of the detector
    #           -dDetector:     2x1 array with the size of each of the pixels in the detector in mm
    #           -DSD:           1x1 or 1xN array. Distance Source Detector, in mm
    #           -DSO:           1x1 or 1xN array. Distance Source Origin.
    #           -offOrigin:     3x1 or 3xN array with the offset in mm of the centre of the image from the origin.
    #           -offDetector:   2x1 or 2xN array with the offset in mm of the centre of the detector from the x axis
    #           -rotDetector:   3x1 or 3xN array with the rotation in roll-pitch-yaw of the detector

    geo = tigre.geometry()
    # Distances
    geo.DSD = 1550  # Distance Source Detector      (mm)
    geo.DSO = 1000  # Distance Source Origin        (mm)
    # Detector parameters
    geo.nDetector = np.array([1440, 1441])  # number of pixels              (px)
    geo.dDetector = np.array([0.296, 0.296])  # size of each pixel            (mm)
    geo.sDetector = geo.nDetector * geo.dDetector  # total size of the detector    (mm)
    # Image parameters
    geo.nVoxel = ctGridSize  # number of voxels              (vx)
    geo.sVoxel = np.multiply(ctGridSize, ctSpacing)  # total size of the image       (mm)
    geo.dVoxel = geo.sVoxel / geo.nVoxel  # size of each voxel            (mm)
    # Offsets
    geo.offOrigin = ctCenter - ctIsocenter  # Offset of image from origin   (mm)
    geo.offDetector = np.array([0, 0])  # Offset of Detector            (mm)
    # Auxiliary
    geo.accuracy = 0.25  # Variable to define accuracy
    geo.COR = 0  # y direction displacement for centre of rotation correction (mm)
    geo.rotDetector = np.array([0, 0, 0])  # Rotation of the detector, by X,Y and Z axis respectively. (rad)
    geo.mode = "cone"  # Or 'parallel'. Geometry type.

    projections = tigre.Ax(im.copy(), geo, angles, "interpolated")

    return CTnoise.add(projections, Poisson=1e5, Gaussian=np.array([0, 10]))
