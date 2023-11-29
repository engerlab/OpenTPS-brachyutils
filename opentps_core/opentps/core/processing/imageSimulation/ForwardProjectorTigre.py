import logging
import numpy as np
import math

logger = logging.getLogger(__name__)

def forwardProjectionTigre(ct, angles, axis='Z', ctIsocenter=None, SAD=1000, SID=1550, flatpanelGridSize=[1440,1440], flatpanelPixelSpacing=[0.296,0.296], poissonNoise=1e5, gaussianNoise=10):
    """
    Forward projection of CT image using Tigre toolbox ( https://github.com/CERN/TIGRE/blob/master/Frontispiece/python_installation.md ).

    Parameters
    ----------
    ct : CT
        CT object
    angles : float or list or numpy.ndarray
        Projection angles in radians
    axis : str, optional
        Axis of CT image to be used for forward projection. The default is 'Z'.
    ctIsocenter : numpy.ndarray, optional
        Isocenter of CT image. The default is None.
    SAD : float, optional
        Source to axis distance in mm. The default is 1000.
    SID : float, optional
        Source to detector distance in mm. The default is 1550.
    flatpanelGridSize : list, optional
        Flatpanel grid size in pixels. The default is [1440,1440].
    flatpanelPixelSpacing : list, optional
        Flatpanel pixel spacing in mm. The default is [0.296,0.296].
    poissonNoise : float, optional
        Poisson noise level. The default is 1e5.
    gaussianNoise : float, optional
        Gaussian noise level. The default is 10.

    Returns
    -------
    projections : numpy.ndarray
        Forward projections.
    """
    try:
        import tigre  # https://github.com/CERN/TIGRE/blob/master/Frontispiece/python_installation.md
    except:
        logger.error('No module tigre available. Abort forwardProjectionTigre.')
    
    try:
        from tigre.utilities import CTnoise
    except:
        logger.error('Noise model from Tigre library not available. No noise is added.')
        poissonNoise = None
        gaussianNoise = None

    if not(isinstance(angles,(np.ndarray, np.generic))):
        if isinstance(angles, list):
            angles = np.array(angles)
        else:
            angles = np.array([angles])

    angles = angles-math.pi/2 # Correction so that 0 degree corresponds to top-down direction in case of 'Z' orientation -> TO BE CHECKED

    ctCenter = ct.origin + ct.gridSize * ct.spacing / 2
    if ctIsocenter is None:
        ctIsocenter = ctCenter.copy()

    # For binary data
    if ct.imageArray.dtype == 'bool':
        ct._imageArray = ct.imageArray.astype(np.float32)
        ct._imageArray[ct.imageArray < 0.5] = -1000
        ct._imageArray[ct.imageArray >= 0.5] = 1000

    # Convert CT to attenuation in specified axis
    mu_water = 0.0215
    if axis == 'Z':
        im = np.transpose(np.float32(ct.imageArray) * mu_water / 1000 + mu_water, [2, 1, 0])
        ctSpacing = np.array([ct.spacing[2], ct.spacing[1], ct.spacing[0]])
        ctGridSize = np.array([ct.gridSize[2], ct.gridSize[1], ct.gridSize[0]])
        ctCenter = np.array([ctCenter[2], ctCenter[1], ctCenter[0]])
        ctIsocenter = np.array([ctIsocenter[2], ctIsocenter[1], ctIsocenter[0]])
    elif axis == 'Y':
        im = np.transpose(np.float32(ct.imageArray) * mu_water / 1000 + mu_water, [1, 0, 2])
        ctSpacing = np.array([ct.spacing[1],ct.spacing[0],ct.spacing[2]])
        ctGridSize = np.array([ct.gridSize[1],ct.gridSize[0],ct.gridSize[2]])
        ctCenter = np.array([ctCenter[1],ctCenter[0],ctCenter[2]])
        ctIsocenter = np.array([ctIsocenter[1],ctIsocenter[0],ctIsocenter[2]])
    else:
        im = np.float32(ct.imageArray) * mu_water / 1000 + mu_water
        ctSpacing = ct.spacing
        ctGridSize = ct.gridSize

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
    geo.DSD = SID  # Distance Source Detector      (mm)
    geo.DSO = SAD  # Distance Source Origin        (mm)
    # Detector parameters
    geo.nDetector = np.array(flatpanelGridSize)  # number of pixels              (px)
    geo.dDetector = np.array(flatpanelPixelSpacing)  # size of each pixel            (mm)
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

    if poissonNoise is None or gaussianNoise is None:
        return projections
    else:
        return CTnoise.add(projections, Poisson=poissonNoise, Gaussian=np.array([0, gaussianNoise]))
