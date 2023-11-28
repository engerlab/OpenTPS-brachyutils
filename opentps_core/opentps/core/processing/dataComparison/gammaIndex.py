import pymedphys
import numpy as np
from typing import Sequence, Tuple
from opentps.core.data.images._image3D import Image3D

def _orientation_is_head_first(orientation_vector, is_decubitus):
    """
    From pymedphys (https://github.com/pymedphys/pymedphys)
    """
    if is_decubitus:
        return np.abs(np.sum(orientation_vector)) != 2

    return np.abs(np.sum(orientation_vector)) == 2

def xyz_axes_from_dataset(
    ds: Image3D, coord_system: str = "DICOM"
) -> Tuple["np.ndarray", "np.ndarray", "np.ndarray"]:
    r"""Returns the x, y and z axes of a DICOM dataset's
    pixel array in the specified coordinate system.

    Adapted from pymedphys (https://github.com/pymedphys/pymedphys)

    For DICOM RT Dose datasets, these are the x, y, z axes of the
    dose grid.

    Parameters
    ----------
    ds : pydicom.dataset.Dataset
        A DICOM dataset that contains pixel data. Supported modalities
        include 'CT' and 'RTDOSE'.

    coord_system : str, optional
        The coordinate system in which to return the `x`, `y` and `z`
        axes of the DICOM dataset. The accepted, case-insensitive
        values of `coord_system` are:

        'DICOM' or 'd':
            Return axes in the DICOM coordinate system.

        'patient', 'IEC patient' or 'p':
            Return axes in the IEC patient coordinate system.

        'fixed', 'IEC fixed' or 'f':
            Return axes in the IEC fixed coordinate system.

    Returns
    -------
    (x, y, z)
        A tuple containing three `numpy.ndarray`s corresponding to the `x`,
        `y` and `z` axes of the DICOM dataset's pixel array in the
        specified coordinate system.

    Notes
    -----
    Supported scan orientations [1]_:

    =========================== ==========================
    Orientation                 ds.ImageOrientationPatient
    =========================== ==========================
    Feet First Decubitus Left   [0, 1, 0, 1, 0, 0]
    Feet First Decubitus Right  [0, -1, 0, -1, 0, 0]
    Feet First Prone            [1, 0, 0, 0, -1, 0]
    Feet First Supine           [-1, 0, 0, 0, 1, 0]
    Head First Decubitus Left   [0, -1, 0, 1, 0, 0]
    Head First Decubitus Right  [0, 1, 0, -1, 0, 0]
    Head First Prone            [-1, 0, 0, 0, -1, 0]
    Head First Supine           [1, 0, 0, 0, 1, 0]
    =========================== ==========================

    References
    ----------
    .. [1] O. McNoleg, "Generalized coordinate transformations for Monte
       Carlo (DOSXYZnrc and VMC++) verifications of DICOM compatible
       radiotherapy treatment plans", arXiv:1406.0014, Table 1,
       https://arxiv.org/ftp/arxiv/papers/1406/1406.0014.pdf

    Extra notes
    -----------
    The ordering to unpack the pixel spacing values from PixelSpacing have
    importance when dealing with non square pixels. For more information
    on how to unpack the PixelSpacing values in the right order, see :
    http://dicom.nema.org/medical/dicom/current/output/chtml/part03/
    sect_10.7.html#sect_10.7.1.3
    """

    position = np.array(ds.origin)
    orientation = np.array([1, 0, 0, 0, 1,0])

    if not (
        np.array_equal(np.abs(orientation), np.array([1, 0, 0, 0, 1, 0]))
        or np.array_equal(np.abs(orientation), np.array([0, 1, 0, 1, 0, 0]))
    ):
        raise ValueError(
            "Dose grid orientation is not supported. Dose "
            "grid slices must be aligned along the "
            "superoinferior axis of patient."
        )

    is_decubitus = orientation[0] == 0
    is_head_first = _orientation_is_head_first(orientation, is_decubitus)

    row_spacing = float(ds.spacing[1])
    column_spacing = float(ds.spacing[0])

    row_range = np.array([row_spacing * i for i in range(ds.gridSize[1])])
    col_range = np.array([column_spacing * i for i in range(ds.gridSize[0])])

    if is_decubitus:
        x_dicom_fixed = orientation[1] * position[1] + col_range
        y_dicom_fixed = orientation[3] * position[0] + row_range
    else:
        x_dicom_fixed = orientation[0] * position[0] + col_range
        y_dicom_fixed = orientation[4] * position[1] + row_range

    if is_head_first:
        # z_dicom_fixed = position[2] + np.array(ds.GridFrameOffsetVector)
        z_dicom_fixed = position[2] + ds.spacing[2] * np.arange(ds.gridSize[2])
    else:
        # z_dicom_fixed = -position[2] + np.array(ds.GridFrameOffsetVector)
        z_dicom_fixed = -position[2] + ds.spacing[2] * np.arange(ds.gridSize[2])

    if coord_system.upper() in ("FIXED", "IEC FIXED", "F"):
        x = x_dicom_fixed
        y = z_dicom_fixed
        z = -np.flip(y_dicom_fixed)

    elif coord_system.upper() in ("DICOM", "D", "PATIENT", "IEC PATIENT", "P"):

        if orientation[0] == 1:
            x = x_dicom_fixed
        elif orientation[0] == -1:
            x = np.flip(x_dicom_fixed)
        elif orientation[1] == 1:
            y_d = x_dicom_fixed
        elif orientation[1] == -1:
            y_d = np.flip(x_dicom_fixed)

        if orientation[4] == 1:
            y_d = y_dicom_fixed
        elif orientation[4] == -1:
            y_d = np.flip(y_dicom_fixed)
        elif orientation[3] == 1:
            x = y_dicom_fixed
        elif orientation[3] == -1:
            x = np.flip(y_dicom_fixed)

        if not is_head_first:
            z_d = np.flip(z_dicom_fixed)
        else:
            z_d = z_dicom_fixed

        if coord_system.upper() in ("DICOM", "D"):
            y = y_d
            z = z_d
        elif coord_system.upper() in ("PATIENT", "IEC PATIENT", "P"):
            y = z_d
            z = -np.flip(y_d)

    return (x, y, z)


def gammaIndex(referenceImage:Image3D, evaluationImage:Image3D,     
               dose_percent_threshold, distance_mm_threshold, lower_percent_dose_cutoff=20,
               interp_fraction=10, max_gamma=None, local_gamma=False, global_normalisation=None,
               skip_once_passed=False, random_subset=None, ram_available=int(2**30 * 4)):
    """
    Compute the gamma index between two images using pymedphys library (https://github.com/pymedphys/pymedphys).
    This function is essentially a wrapper on function `pymedphys.gamma` using when using OpenTPS data.
    As such, most of the parameters are the same.

    pymedphys DOCSTRING:
    Compare two dose grids with the gamma index.

    It computes 1, 2, or 3 dimensional gamma with arbitrary gird sizes while
    interpolating on the fly. This function makes use of some of the ideas
    presented within <http://dx.doi.org/10.1118/1.2721657>.

    Parameters
    ----------
    axes_reference : tuple
        The reference coordinates.
    dose_reference : np.array
        The reference dose grid. Each point in the reference grid becomes the
        centre of a Gamma ellipsoid. For each point of the reference, nearby
        evaluation points are searched at increasing distances.
    axes_evaluation : tuple
        The evaluation coordinates.
    dose_evaluation : np.array
        The evaluation dose grid. Evaluation here is defined as the grid which
        is interpolated and searched over at increasing distances away from
        each reference point.
    dose_percent_threshold : float
        The percent dose threshold
    distance_mm_threshold : float
        The gamma distance threshold. Units must
        match of the coordinates given.
    lower_percent_dose_cutoff : float, optional
        The percent lower dose cutoff below which gamma will not be calculated.
        This is only applied to the reference grid.
    interp_fraction : float, optional
        The fraction which gamma distance threshold is divided into for
        interpolation. Defaults to 10 as recommended within
        <http://dx.doi.org/10.1118/1.2721657>. If a 3 mm distance threshold is chosen
        this default value would mean that the evaluation grid is interpolated at
        a step size of 0.3 mm.
    max_gamma : float, optional
        The maximum gamma searched for. This can be used to speed up
        calculation, once a search distance is reached that would give gamma
        values larger than this parameter, the search stops. Defaults to :obj:`np.inf`
    local_gamma
        Designates local gamma should be used instead of global. Defaults to
        False.
    global_normalisation : float, optional
        The dose normalisation value that the percent inputs calculate from.
        Defaults to the maximum value of :obj:`dose_reference`.
    random_subset : int, optional
        Used to only calculate a random subset of the reference grid. The
        number chosen is how many random points to calculate.
    ram_available : int, optional
        The number of bytes of RAM available for use by this function. Defaults
        to 4GB.

    Returns
    -------
    gamma: Image3D or DoseImage
        Contains the array of gamma values the same shape as that
        given by the reference image.
    """
    x,y,z = xyz_axes_from_dataset(referenceImage)
    axes_reference = (z, y, x)
    x,y,z = xyz_axes_from_dataset(evaluationImage)
    axes_evaluation = (z, y, x)

    gamma = pymedphys.gamma(
        axes_reference=axes_reference, dose_reference=referenceImage.imageArray.transpose(2,1,0), 
        axes_evaluation=axes_evaluation, dose_evaluation=evaluationImage.imageArray.transpose(2,1,0), 
        dose_percent_threshold=dose_percent_threshold, distance_mm_threshold=distance_mm_threshold, 
        lower_percent_dose_cutoff=lower_percent_dose_cutoff, interp_fraction=interp_fraction,
        max_gamma=max_gamma, local_gamma=local_gamma, global_normalisation=global_normalisation,
        skip_once_passed=skip_once_passed, random_subset=random_subset, 
        ram_available=ram_available).transpose(2,1,0)

    gammaImage = referenceImage.__class__.fromImage3D(referenceImage, imageArray=gamma, name="gamma")
    return gammaImage

def computePassRate(gammaImage:Image3D):
    """
    Compute gamma pass rate

    Parameters
    ----------
    gammaImage: Image3D
        gamma image

    Returns
    -------
    passRate: float
        Pass rate in percent
    """
    gamma = gammaImage.imageArray
    valid_gamma = gamma[~np.isnan(gamma)]
    return np.sum(valid_gamma <= 1) / np.product(valid_gamma.shape) * 100
