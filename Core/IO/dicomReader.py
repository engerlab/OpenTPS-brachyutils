import os, sys
import pydicom
import numpy as np
import logging

from Core.Data.Images.ctImage import CTImage

logger = logging.getLogger(__name__)
class DICOMReader:
    @staticmethod
    def read(dcmFiles):
        if type(dcmFiles) is list:
            if len(dcmFiles)==1:
                return DICOMReader.read(dcmFiles[0])
            else:
                return DICOMReader.readCT(dcmFiles)
        else:
            dcm = pydicom.dcmread(dcmFiles)
            if 'StructureSetROISequence' in dcm:
                return DICOMReader.loadRTStruct(dcmFiles)
            else:
                #TODO
                pass


    @staticmethod
    def readCT(dcmFiles):
        """​
        Reads from a list of DICOM files and builds a CTimage object

        Parameters
        ----------​

        dcmFiles : list

            list of dcm files composing the CT image.​
​

        Returns​
        -------​
        CTimage
        """
        images = []
        sopInstanceUIDs = []
        sliceLocation = np.zeros(len(dcmFiles), dtype='float')
        
        for i in range(len(dcmFiles)):
            file_path = dcmFiles[i]
            dcm = pydicom.dcmread(file_path)

            if (hasattr(dcm, 'SliceLocation') and abs(dcm.SliceLocation - dcm.ImagePositionPatient[2]) > 0.001):
                logging.warning("WARNING: SliceLocation (" + str(
                    dcm.SliceLocation) + ") is different than ImagePositionPatient[2] (" + str(
                    dcm.ImagePositionPatient[2]) + ") for " + file_path)

            sliceLocation[i] = float(dcm.ImagePositionPatient[2])
            images.append(dcm.pixel_array * dcm.RescaleSlope + dcm.RescaleIntercept)
            sopInstanceUIDs.append(dcm.SOPInstanceUID)

        # sort slices according to their location in order to reconstruct the 3d image
        sort_index = np.argsort(sliceLocation)
        sliceLocation = sliceLocation[sort_index]
        sopInstanceUIDs = [sopInstanceUIDs[n] for n in sort_index]
        images = [images[n] for n in sort_index]
        image = np.dstack(images).astype("float32").transpose(1, 0, 2)

        if image.shape[0:2] != (dcm.Columns, dcm.Rows):
            logging.warning("WARNING: GridSize " + str(image.shape[0:2]) + " different from Dicom Columns (" + str(
                dcm.Columns) + ") and Rows (" + str(dcm.Rows) + ")")

        meanSliceDistance = (sliceLocation[-1] - sliceLocation[0]) / (len(images) - 1)
        if (hasattr(dcm, 'SliceThickness') and (
                type(dcm.SliceThickness) == int or type(dcm.SliceThickness) == float) and abs(
                meanSliceDistance - dcm.SliceThickness) > 0.001):
            logging.warning(
                "WARNING: meanSliceDistance (" + str(meanSliceDistance) + ") is different from SliceThickness (" + str(
                    dcm.SliceThickness) + ")")

        imagePositionPatient = [float(dcm.ImagePositionPatient[0]), float(dcm.ImagePositionPatient[1]),
                                sliceLocation[0]]
        pixelSpacing = [float(dcm.PixelSpacing[1]), float(dcm.PixelSpacing[0]), meanSliceDistance]
        frameOfReferenceUID = dcm.FrameOfReferenceUID = dcm.FrameOfReferenceUID
        seriesInstanceUID = dcm.SeriesInstanceUID
        
        #TODO: ImgName
        return CTImage(data=image, name="CT", origin=imagePositionPatient, spacing=pixelSpacing, seriesInstanceUID=seriesInstanceUID, frameOfReferenceUID=frameOfReferenceUID, sliceLocation=sliceLocation)
    
    @staticmethod
    def loadRTPlan(DcmFile):
        raise(NotImplementedError("TODO"))

    @staticmethod
    def loadRTStruct(DcmFile):
        raise(NotImplementedError("TODO"))


if __name__ == '__main__':
    folderPath = r'D:/Users/Public/Documents/Data/CT_test'

    fileList = [os.path.join(folderPath, file) for file in os.listdir(folderPath)]
    image = DICOMReader.read(fileList)
    
    logging.info(image)
