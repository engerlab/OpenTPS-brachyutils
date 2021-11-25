import pydicom
import scipy.ndimage
import math

from Core.Processing.C_libraries.libInterp3_wrapper import *
from Core.Data.image3D import Image3D

class DeformationField(Image3D):

    def __init__(self):

        Image3D.__init__(self)

        self.SOPInstanceUID = ""
        self.FieldName = ""
        self.DcmFile = ""
        self.SeriesInstanceUID = ""
        self.PatientInfo = {}
        self.StudyInfo = {}
        self.CT_SeriesInstanceUID = ""
        self.Plan_SOPInstanceUID = ""
        self.FrameOfReferenceUID = ""
        self.ImagePositionPatient = [0, 0, 0]
        self.PixelSpacing = [1, 1, 1]
        self.GridSize = [0, 0, 0]
        self.NumVoxels = 0
        self.Velocity = []
        self.Displacement = []
        self.isLoaded = 0

    def print_field_info(self, prefix=""):
        print(prefix + "Deformation field: " + self.SOPInstanceUID)
        print(prefix + "   " + self.DcmFile)

    def Init_Field_Zeros(self, GridSize, Offset=[0, 0, 0], PixelSpacing=[1, 1, 1]) -> object:
        if (len(GridSize) == 3):
            GridSize = tuple(GridSize) + (3,)
        elif (len(GridSize) == 4 and GridSize[3] != 3):
            print("Error: last dimension of deformation field should be of size 3")
            return

        self.Velocity = np.zeros(GridSize)
        self.ImagePositionPatient = Offset
        self.PixelSpacing = PixelSpacing
        self.GridSize = GridSize[0:3]

    def copy(self):
        df = DeformationField()
        df.FieldName = df.FieldName
        df.SeriesInstanceUID = self.SeriesInstanceUID + ".1"
        df.SOPInstanceUID = self.SOPInstanceUID
        df.PatientInfo = self.PatientInfo
        df.StudyInfo = self.StudyInfo
        df.CT_SeriesInstanceUID = self.CT_SeriesInstanceUID
        df.Plan_SOPInstanceUID = self.Plan_SOPInstanceUID
        df.FrameOfReferenceUID = self.FrameOfReferenceUID
        df.ImagePositionPatient = list(self.ImagePositionPatient)
        df.PixelSpacing = list(self.PixelSpacing)
        df.GridSize = list(self.GridSize)
        df.NumVoxels = 0
        df.Velocity = self.Velocity
        df.Displacement = self.Velocity
        return df

    def import_Dicom_DF(self, CT_list, df_type='Velocity'):
        if (self.isLoaded == 1):
            print("Warning: Deformation Field " + self.SOPInstanceUID + " is already loaded")
            return

        dcm = pydicom.dcmread(self.DcmFile).DeformableRegistrationSequence[0]

        # find associated CT image
        CT = {}
        try:
            CT_ID = next(
                (x for x, val in enumerate(CT_list) if val.FrameOfReferenceUID == dcm.SourceFrameOfReferenceUID), -1)
            CT_ID = next((x for x, val in enumerate(CT_list) if val.FrameOfReferenceUID == dcm.FrameOfReferenceUID), -1)
            CT = CT_list[CT_ID]
        except:
            pass

        if (CT == {}):
            print("Warning: No CT image has been found with the same frame of reference as DeformationField ")
            print("DeformationField is imported on the first CT image.")
            CT = CT_list[0]

        # import deformation field
        self.CT_SeriesInstanceUID = CT.SeriesInstanceUID
        self.FrameOfReferenceUID = dcm.SourceFrameOfReferenceUID
        dcm_field = dcm.DeformableRegistrationGridSequence[0]

        self.ImagePositionPatient = dcm_field.ImagePositionPatient
        self.ImageOrientationPatient = dcm_field.ImageOrientationPatient
        self.GridSize = dcm_field.GridDimensions
        self.PixelSpacing = dcm_field.GridResolution
        self.NumVoxels = self.GridSize[0] * self.GridSize[1] * self.GridSize[2]

        raw_field = np.frombuffer(dcm_field.VectorGridData, dtype=np.float32)
        raw_field = raw_field.reshape(
            (3, dcm_field.GridDimensions[0], dcm_field.GridDimensions[1], dcm_field.GridDimensions[2]),
            order='F').transpose(1, 2, 3, 0)
        field = raw_field.copy()
        for i in range(3):
            field[:, :, :, i] = field[:, :, :, i] / self.PixelSpacing[i]

        if df_type == 'Velocity':
            self.Velocity = field
            self.Displacement = self.Exponentiation()
            # Resample both the velocity and diplacement to the CT
            self.resample_to_CT_grid(CT, which_df='both')
        elif df_type == 'Displacement':
            self.Displacement = field
            self.resample_to_CT_grid(CT, which_df='Displacement')
        else:
            print("Unknown deformation field type")
            return
        self.isLoaded = 1

    def resample_to_CT_grid(self, CT, which_df):
        if (not CT.is_same_grid(self)):
            print('Resample deformation field to CT grid.')
            self.resample_DF(CT.GridSize, CT.ImagePositionPatient, CT.PixelSpacing, which_df)

    def resample_DF(self, GridSize, Offset, PixelSpacing, which_df='both'):
        if which_df == 'both':
            assert self.Velocity != []
            assert self.Displacement != []
            self.Velocity = self.resample_field(self.Velocity, GridSize, Offset, PixelSpacing)
            self.Displacement = self.resample_field(self.Displacement, GridSize, Offset, PixelSpacing)
        elif which_df == 'Velocity':
            assert self.Velocity != []
            self.Velocity = self.resample_field(self.Velocity, GridSize, Offset, PixelSpacing)
        elif which_df == 'Displacement':
            assert self.Displacement != []
            self.Displacement = self.resample_field(self.Displacement, GridSize, Offset, PixelSpacing)
        else:
            print("parameter which_df should either be 'both', 'Velocity' or 'Displacement'.")
            return

        self.ImagePositionPatient = list(Offset)
        self.PixelSpacing = list(PixelSpacing)
        self.GridSize = list(GridSize)
        self.NumVoxels = GridSize[0] * GridSize[1] * GridSize[2]

    def resample_field(self, init_field, GridSize, Offset, PixelSpacing):
        field_components = [0, 1, 2]
        # anti-aliasing filter
        if self.NumVoxels > np.product(GridSize):  # downsampling
            sigma = [0, 0, 0]
            if (PixelSpacing[0] > self.PixelSpacing[0]): sigma[0] = 0.4 * (PixelSpacing[0] / self.PixelSpacing[0])
            if (PixelSpacing[1] > self.PixelSpacing[1]): sigma[1] = 0.4 * (PixelSpacing[1] / self.PixelSpacing[1])
            if (PixelSpacing[2] > self.PixelSpacing[2]): sigma[2] = 0.4 * (PixelSpacing[2] / self.PixelSpacing[2])
            if (sigma != [0, 0, 0]):
                print("Field is filtered before downsampling")

            for i in field_components:
                init_field[:, :, :, i] = scipy.ndimage.gaussian_filter(init_field[:, :, :, i], sigma)

        # resampling
        Init_GridSize = list(self.GridSize)

        interp_x = (Offset[0] - self.ImagePositionPatient[0] + np.arange(GridSize[1]) * PixelSpacing[0]) / \
                   self.PixelSpacing[0]
        interp_y = (Offset[1] - self.ImagePositionPatient[1] + np.arange(GridSize[0]) * PixelSpacing[1]) / \
                   self.PixelSpacing[1]
        interp_z = (Offset[2] - self.ImagePositionPatient[2] + np.arange(GridSize[2]) * PixelSpacing[2]) / \
                   self.PixelSpacing[2]

        # Correct for potential precision issues on the border of the grid
        interp_x[interp_x > Init_GridSize[1] - 1] = np.round(interp_x[interp_x > Init_GridSize[1] - 1] * 1e3) / 1e3
        interp_y[interp_y > Init_GridSize[0] - 1] = np.round(interp_y[interp_y > Init_GridSize[0] - 1] * 1e3) / 1e3
        interp_z[interp_z > Init_GridSize[2] - 1] = np.round(interp_z[interp_z > Init_GridSize[2] - 1] * 1e3) / 1e3

        xi = np.array(np.meshgrid(interp_y, interp_x, interp_z))
        xi = np.rollaxis(xi, 0, 4)
        xi = xi.reshape((xi.size // 3, 3))

        field = np.zeros((*GridSize, 3))
        for i in field_components:
            field_temp = Trilinear_Interpolation(init_field[:, :, :, i], Init_GridSize, xi)
            field[:, :, :, i] = field_temp.reshape((GridSize[1], GridSize[0], GridSize[2])).transpose(1, 0, 2) * \
                                self.PixelSpacing[i] / PixelSpacing[i]

        return field

    def Exponentiation(self, save_displacement=0):
        norm = np.square(self.Velocity[:, :, :, 0]) + np.square(self.Velocity[:, :, :, 1]) + np.square(
            self.Velocity[:, :, :, 2])
        N = math.ceil(2 + math.log2(np.maximum(1.0, np.amax(np.sqrt(norm)))) / 2) + 1
        if N < 1: N = 1
        # print("Field exponentiation (N=" + str(N) + ')')

        self.Displacement = self.Velocity.copy() * 2 ** (-N)

        for r in range(N):
            new_0 = self.apply_displacement_field(self.Displacement[:, :, :, 0], self.Displacement, fill_value=0)
            new_1 = self.apply_displacement_field(self.Displacement[:, :, :, 1], self.Displacement, fill_value=0)
            new_2 = self.apply_displacement_field(self.Displacement[:, :, :, 2], self.Displacement, fill_value=0)
            self.Displacement[:, :, :, 0] += new_0
            self.Displacement[:, :, :, 1] += new_1
            self.Displacement[:, :, :, 2] += new_2

        output = self.Displacement
        if (save_displacement == 0): self.Displacement = []

        return output

    def deform_image(self, Im, fill_value=-1000):
        # Im is an image. The output is the matrix of voxels after deformation (i.e. deformed Im.Image)

        if (self.Displacement == []):
            field = self.Exponentiation()
        else:
            field = self.Displacement

        if tuple(self.GridSize) != tuple(Im.GridSize) or tuple(self.ImagePositionPatient) != tuple(
                Im.ImagePositionPatient) or tuple(self.PixelSpacing) != tuple(Im.PixelSpacing):
            field = self.resample_field(field, Im.GridSize, Im.ImagePositionPatient, Im.PixelSpacing)
            print("Warning: image and field dimensions do not match. Resample displacement field to image grid.")

        deformed = self.apply_displacement_field(Im.Image, field, fill_value=fill_value)

        return deformed

    def apply_displacement_field(self, img, field, fill_value=-1000):
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
        if fill_value == 'closest':
            xi[:, 0] = np.maximum(np.minimum(xi[:, 0], size[0] - 1), 0)
            xi[:, 1] = np.maximum(np.minimum(xi[:, 1], size[1] - 1), 0)
            xi[:, 2] = np.maximum(np.minimum(xi[:, 2], size[2] - 1), 0)
            fill_value = -1000
        # deformed = scipy.interpolate.interpn((x,y,z), img, xi, method='linear', fill_value=fill_value, bounds_error=False)
        deformed = Trilinear_Interpolation(img, size, xi, fill_value=fill_value)
        deformed = deformed.reshape((size[1], size[0], size[2])).transpose(1, 0, 2)

        return deformed

    def field_norm(self, which_df='Displacement'):
        if which_df == 'Velocity':
            assert self.Velocity != []
            return np.sqrt(
                self.Velocity[:, :, :, 0] ** 2 + self.Velocity[:, :, :, 1] ** 2 + self.Velocity[:, :, :, 2] ** 2)
        elif which_df == 'Displacement':
            assert self.Displacement != []
            self.Displacement
            return np.sqrt(
                self.Displacement[:, :, :, 0] ** 2 + self.Displacement[:, :, :, 1] ** 2 + self.Displacement[:, :, :,
                                                                                          2] ** 2)
        else:
            print("parameter which_df should either be 'Velocity' or 'Displacement'.")
            return -1