## Data come from : https://www.creatis.insa-lyon.fr/rio/popi-model_original_page

from Core.IO.dataLoader import listAllFiles
import numpy as np
import pydicom
from scipy.ndimage import zoom
import os


## read a 4DCT
dataPath = "/home/damien/Desktop/4DCT-Dicom (copy)/90"
dataList = listAllFiles(dataPath)
print(type(dataList))
print(len(dataList["Dicom"]))
print(dataList["Dicom"][0])
print(dataList["Dicom"])
gridSizeAfterResample = [100, 100]

firstFile = pydicom.dcmread(dataList["Dicom"][0])

print(firstFile.PixelSpacing)
print(firstFile.Rows)
print(firstFile.Columns)
spacingAfterResample = [firstFile.PixelSpacing[0] * (firstFile.Rows/gridSizeAfterResample[0]),
                        firstFile.PixelSpacing[1] * (firstFile.Columns/gridSizeAfterResample[1])]

ratio = [gridSizeAfterResample[0]/firstFile.Rows, gridSizeAfterResample[1]/firstFile.Columns]

for fileIndex in range(len(dataList["Dicom"])):
    print(dataList["Dicom"][fileIndex])
    if (fileIndex % 3) == 0:
        dcm = pydicom.dcmread(dataList["Dicom"][fileIndex])
        imageArray = dcm.pixel_array

        print('Before resampling: ', imageArray.shape, np.min(imageArray), np.max(imageArray))

        resampled = zoom(imageArray, ratio).astype(np.int16)

        print('After resampling: ', resampled.shape, np.min(resampled), np.max(resampled))

        dcm.PixelData = resampled.tobytes()
        dcm.PixelSpacing = spacingAfterResample
        dcm.Rows, dcm.Columns = resampled.shape

        pydicom.dcmwrite(dataList["Dicom"][fileIndex], dcm)
    else:
        os.remove(dataList["Dicom"][fileIndex])



# import pydicom
# from pydicom.data import get_testdata_file
#
# print(__doc__)
#
# # FIXME: add a full-sized MR image in the testing data
# filename = get_testdata_file('MR_small.dcm')
# ds = pydicom.dcmread(filename)
#
# # get the pixel information into a numpy array
# data = ds.pixel_array
# print('The image has {} x {} voxels'.format(data.shape[0],
#                                             data.shape[1]))
# data_downsampling = data[::8, ::8]
# print('The downsampled image has {} x {} voxels'.format(
#     data_downsampling.shape[0], data_downsampling.shape[1]))
#
# # copy the data back to the original data set
# ds.PixelData = data_downsampling.tobytes()
# # update the information regarding the shape of the data array
# ds.Rows, ds.Columns = data_downsampling.shape
#
# # print the image information given in the dataset
# print('The information of the data set after downsampling: \n')
# print(ds)