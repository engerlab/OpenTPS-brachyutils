import pydicom
import scipy.ndimage
import math

from Core.Processing.C_libraries.libInterp3_wrapper import *
from Core.Data.Images.image3D import Image3D

class DeformationField(Image3D):

    def __init__(self):

        Image3D.__init__(self)

        self.velocity = []
        self.displacement = []

    def print_field_info(self, prefix=""):
        print(prefix + "Deformation field: " + self.SOPInstanceUID)
        print(prefix + "   " + self.DcmFile)

    def initFieldWithZeros(self, gridSize, origin=[0, 0, 0], spacing=[1, 1, 1]) -> object:
        if (len(gridSize) == 3):
            gridSize = tuple(gridSize) + (3,)
        elif (len(gridSize) == 4 and gridSize[3] != 3):
            print("Error: last dimension of deformation field should be of size 3")
            return

        self.velocity = np.zeros(gridSize)
        self.origin = origin
        self.spacing = spacing

    def copy(self):
        df = DeformationField()

        df.SeriesInstanceUID = self.SeriesInstanceUID + ".1"
        df.SOPInstanceUID = self.SOPInstanceUID
        df.PatientInfo = self.PatientInfo
        df.StudyInfo = self.StudyInfo
        df.CT_SeriesInstanceUID = self.CT_SeriesInstanceUID
        df.Plan_SOPInstanceUID = self.Plan_SOPInstanceUID
        df.FrameOfReferenceUID = self.FrameOfReferenceUID

        df.origin = list(self.origin)
        df.spacing = list(self.spacing)
        df.velocity = self.velocity
        df.displacement = self.velocity
        return df

    def import_Dicom_DF(self, CT_list, df_type='Velocity'):
        if (self.isLoaded == 1):
            print("Warning: Deformation Field " + self.SOPInstanceUID + " is already loaded")
            return

        dcm = pydicom.dcmread(self.DcmFile).DeformableRegistrationSequence[0]

        # find associated CT image
        ct = {}
        try:
            CT_ID = next(
                (x for x, val in enumerate(CT_list) if val.FrameOfReferenceUID == dcm.SourceFrameOfReferenceUID), -1)
            CT_ID = next((x for x, val in enumerate(CT_list) if val.FrameOfReferenceUID == dcm.FrameOfReferenceUID), -1)
            ct = CT_list[CT_ID]
        except:
            pass

        if (ct == {}):
            print("Warning: No ct image has been found with the same frame of reference as DeformationField ")
            print("DeformationField is imported on the first CT image.")
            ct = CT_list[0]

        # import deformation field
        self.CT_SeriesInstanceUID = ct.SeriesInstanceUID
        self.FrameOfReferenceUID = dcm.SourceFrameOfReferenceUID
        dcm_field = dcm.DeformableRegistrationGridSequence[0]

        self.origin = dcm_field.ImagePositionPatient
        self.spacing = dcm_field.GridResolution

        raw_field = np.frombuffer(dcm_field.VectorGridData, dtype=np.float32)
        raw_field = raw_field.reshape(
            (3, dcm_field.GridDimensions[0], dcm_field.GridDimensions[1], dcm_field.GridDimensions[2]),
            order='F').transpose(1, 2, 3, 0)
        field = raw_field.copy()
        for i in range(3):
            field[:, :, :, i] = field[:, :, :, i] / self.spacing[i]

        if df_type == 'Velocity':
            self.velocity = field
            self.displacement = self.exponentiateField()
            # Resample both the velocity and diplacement to the CT
            self.resampleToCTGrid(ct, whichField='both')
        elif df_type == 'Displacement':
            self.displacement = field
            self.resampleToCTGrid(ct, whichField='Displacement')
        else:
            print("Unknown deformation field type")
            return
        self.isLoaded = 1


    def resampleToCTGrid(self, ct, whichField):
        if (not ct.is_same_grid(self)):
            print('Resample deformation field to CT grid.')
            self.resampleDeformationField(ct.getGridSize(), ct.origin, ct.spacing, whichField)

    def resampleDeformationField(self, gridSize, origin, spacing, whichField='both'):
        if whichField == 'both':
            assert self.velocity != []
            assert self.displacement != []
            self.velocity = self.resampleVectorField(self.velocity, gridSize, origin, spacing)
            self.displacement = self.resampleVectorField(self.displacement, gridSize, origin, spacing)
        elif whichField == 'Velocity':
            assert self.velocity != []
            self.velocity = self.resampleVectorField(self.velocity, gridSize, origin, spacing)
        elif whichField == 'Displacement':
            assert self.displacement != []
            self.displacement = self.resampleVectorField(self.displacement, gridSize, origin, spacing)
        else:
            print("parameter whichField should either be 'both', 'Velocity' or 'Displacement'.")
            return

        self.origin = list(origin)
        self.spacing = list(spacing)

    def resampleVectorField(self, initField, gridSize, origin, spacing):
        fieldComponents = [0, 1, 2]
        # anti-aliasing filter
        if np.product(self.getGridSize()) > np.product(gridSize):  # downsampling
            sigma = [0, 0, 0]
            if (spacing[0] > self.spacing[0]): sigma[0] = 0.4 * (spacing[0] / self.spacing[0])
            if (spacing[1] > self.spacing[1]): sigma[1] = 0.4 * (spacing[1] / self.spacing[1])
            if (spacing[2] > self.spacing[2]): sigma[2] = 0.4 * (spacing[2] / self.spacing[2])
            if (sigma != [0, 0, 0]):
                print("Field is filtered before downsampling")

            for i in fieldComponents:
                initField[:, :, :, i] = scipy.ndimage.gaussian_filter(initField[:, :, :, i], sigma)

        # resampling
        initGridSize = list(self.getGridSize())

        interpX = (origin[0] - self.origin[0] + np.arange(gridSize[1]) * spacing[0]) / \
                   self.spacing[0]
        interpY = (origin[1] - self.origin[1] + np.arange(gridSize[0]) * spacing[1]) / \
                   self.spacing[1]
        interpZ = (origin[2] - self.origin[2] + np.arange(gridSize[2]) * spacing[2]) / \
                   self.spacing[2]

        # Correct for potential precision issues on the border of the grid
        interpX[interpX > initGridSize[1] - 1] = np.round(interpX[interpX > initGridSize[1] - 1] * 1e3) / 1e3
        interpY[interpY > initGridSize[0] - 1] = np.round(interpY[interpY > initGridSize[0] - 1] * 1e3) / 1e3
        interpZ[interpZ > initGridSize[2] - 1] = np.round(interpZ[interpZ > initGridSize[2] - 1] * 1e3) / 1e3

        xi = np.array(np.meshgrid(interpY, interpX, interpZ))
        xi = np.rollaxis(xi, 0, 4)
        xi = xi.reshape((xi.size // 3, 3))

        field = np.zeros((*gridSize, 3))
        for i in fieldComponents:
            fieldTemp = Trilinear_Interpolation(initField[:, :, :, i], initGridSize, xi)
            field[:, :, :, i] = fieldTemp.reshape((gridSize[1], gridSize[0], gridSize[2])).transpose(1, 0, 2) * \
                                self.spacing[i] / spacing[i]

        return field

    def exponentiateField(self, saveDisplacement=0):
        norm = np.square(self.velocity[:, :, :, 0]) + np.square(self.velocity[:, :, :, 1]) + np.square(
            self.velocity[:, :, :, 2])
        N = math.ceil(2 + math.log2(np.maximum(1.0, np.amax(np.sqrt(norm)))) / 2) + 1
        if N < 1: N = 1
        # print("Field exponentiation (N=" + str(N) + ')')

        self.displacement = self.velocity.copy() * 2 ** (-N)

        for r in range(N):
            new_0 = self.applyDisplacementField(self.displacement[:, :, :, 0], self.displacement, fill_value=0)
            new_1 = self.applyDisplacementField(self.displacement[:, :, :, 1], self.displacement, fill_value=0)
            new_2 = self.applyDisplacementField(self.displacement[:, :, :, 2], self.displacement, fill_value=0)
            self.displacement[:, :, :, 0] += new_0
            self.displacement[:, :, :, 1] += new_1
            self.displacement[:, :, :, 2] += new_2

        output = self.displacement
        if saveDisplacement == 0: self.displacement = []

        return output

    def deformImage(self, Im, fillValue=-1000):
        # Im is an image. The output is the matrix of voxels after deformation (i.e. deformed Im.Image)

        if (self.displacement == []):
            field = self.exponentiateField()
        else:
            field = self.displacement

        if tuple(self.getGridSize()) != tuple(Im.getGridSize()) or tuple(self.origin) != tuple(
                Im.ImagePositionPatient) or tuple(self.spacing) != tuple(Im.spacing):
            field = self.resampleVectorField(field, Im.getGridSize(), Im.ImagePositionPatient, Im.spacing)
            print("Warning: image and field dimensions do not match. Resample displacement field to image grid.")

        deformed = self.applyDisplacementField(Im.Image, field, fillValue=fillValue)

        return deformed

    def applyDisplacementField(self, img, field, fillValue=-1000):
        size = img.shape

        if (field.shape[0:3] != size):
            print("Error: image dimensions must match with the vector field to apply the displacement field.")
            return

        x = np.arange(size[0])
        y = np.arange(size[1])
        z = np.arange(size[2])
        xi = np.array(np.meshgrid(x, y, z))
        xi = np.rollaxis(xi, 0, 4)
        xi = xi.reshape((xi.size // 3, 3))
        xi = xi.astype('float32')
        xi[:, 0] += field[:, :, :, 0].transpose(1, 0, 2).reshape((xi.shape[0],))
        xi[:, 1] += field[:, :, :, 1].transpose(1, 0, 2).reshape((xi.shape[0],))
        xi[:, 2] += field[:, :, :, 2].transpose(1, 0, 2).reshape((xi.shape[0],))
        if fillValue == 'closest':
            xi[:, 0] = np.maximum(np.minimum(xi[:, 0], size[0] - 1), 0)
            xi[:, 1] = np.maximum(np.minimum(xi[:, 1], size[1] - 1), 0)
            xi[:, 2] = np.maximum(np.minimum(xi[:, 2], size[2] - 1), 0)
            fillValue = -1000
        # deformed = scipy.interpolate.interpn((x,y,z), img, xi, method='linear', fillValue=fillValue, bounds_error=False)
        deformed = Trilinear_Interpolation(img, size, xi, fillValue=fillValue)
        deformed = deformed.reshape((size[1], size[0], size[2])).transpose(1, 0, 2)

        return deformed

    def computeFieldNorm(self, whichField='Displacement'):
        if whichField == 'Velocity':
            assert self.velocity != []
            return np.sqrt(
                self.velocity[:, :, :, 0] ** 2 + self.velocity[:, :, :, 1] ** 2 + self.velocity[:, :, :, 2] ** 2)
        elif whichField == 'Displacement':
            assert self.displacement != []
            self.displacement
            return np.sqrt(
                self.displacement[:, :, :, 0] ** 2 + self.displacement[:, :, :, 1] ** 2 + self.displacement[:, :, :,
                                                                                          2] ** 2)
        else:
            print("parameter whichField should either be 'Velocity' or 'Displacement'.")
            return -1
