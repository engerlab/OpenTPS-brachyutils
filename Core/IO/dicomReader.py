import os

import pydicom
import numpy as np

from Core.Data.ctImage import CTImage


class DICOMReader:
    @staticmethod
    def read(DcmFiles):
        if type(DcmFiles) is list:
            if len(DcmFiles)==1:
                return DICOMReader.read(DcmFiles[0])
            else:
                return DICOMReader.readSeries(DcmFiles)
        else:
            dcm = pydicom.dcmread(DcmFiles)
            if 'StructureSetROISequence' in dcm:
                return DICOMReader.loadRTStruct(DcmFiles)
            else:
                #TODO
                pass


    @staticmethod
    def readSeries(DcmFiles):
        images = []
        SOPInstanceUIDs = []
        SliceLocation = np.zeros(len(DcmFiles), dtype='float')

        for i in range(len(DcmFiles)):
            file_path = DcmFiles[i]
            dcm = pydicom.dcmread(file_path)
            # dcm = pydicom.dcmread(file_path, force=True)

            if (hasattr(dcm, 'SliceLocation') and abs(dcm.SliceLocation - dcm.ImagePositionPatient[2]) > 0.001):
                print("WARNING: SliceLocation (" + str(
                    dcm.SliceLocation) + ") is different than ImagePositionPatient[2] (" + str(
                    dcm.ImagePositionPatient[2]) + ") for " + file_path)

            SliceLocation[i] = float(dcm.ImagePositionPatient[2])
            images.append(dcm.pixel_array * dcm.RescaleSlope + dcm.RescaleIntercept)
            SOPInstanceUIDs.append(dcm.SOPInstanceUID)

        # sort slices according to their location in order to reconstruct the 3d image
        sort_index = np.argsort(SliceLocation)
        SliceLocation = SliceLocation[sort_index]
        SOPInstanceUIDs = [SOPInstanceUIDs[n] for n in sort_index]
        images = [images[n] for n in sort_index]
        Image = np.dstack(images).astype("float32").transpose(1, 0, 2)

        if Image.shape[0:2] != (dcm.Columns, dcm.Rows):
            print("WARNING: GridSize " + str(Image.shape[0:2]) + " different from Dicom Columns (" + str(
                dcm.Columns) + ") and Rows (" + str(dcm.Rows) + ")")

        MeanSliceDistance = (SliceLocation[-1] - SliceLocation[0]) / (len(images) - 1)
        if (hasattr(dcm, 'SliceThickness') and (
                type(dcm.SliceThickness) == int or type(dcm.SliceThickness) == float) and abs(
                MeanSliceDistance - dcm.SliceThickness) > 0.001):
            print(
                "WARNING: MeanSliceDistance (" + str(MeanSliceDistance) + ") is different from SliceThickness (" + str(
                    dcm.SliceThickness) + ")")

        ImagePositionPatient = [float(dcm.ImagePositionPatient[0]), float(dcm.ImagePositionPatient[1]),
                                SliceLocation[0]]
        PixelSpacing = [float(dcm.PixelSpacing[1]), float(dcm.PixelSpacing[0]), MeanSliceDistance]
        FrameOfReferenceUID = dcm.FrameOfReferenceUID = dcm.FrameOfReferenceUID
        SeriesInstanceUID = dcm.SeriesInstanceUID

        #TODO: ImgName
        return CTImage(data=Image, spacing=PixelSpacing, origin=ImagePositionPatient)

    @staticmethod
    def loadRTPlan(DcmFile):
        raise(NotImplementedError("TODO"))

    @staticmethod
    def loadRTStruct(DcmFile):
        raise(NotImplementedError("TODO"))


if __name__ == '__main__':
    folderPath = '/home/sylvain/Downloads/MIROPT_data'

    fileList = [os.path.join(folderPath, file) for file in os.listdir(folderPath)]
    image = DICOMReader.read(fileList)

    print(image)
