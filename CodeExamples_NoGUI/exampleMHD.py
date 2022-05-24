import os
import sys
currentWorkingDir = os.getcwd()
while not os.path.isfile(currentWorkingDir + '/main.py'): currentWorkingDir = os.path.dirname(currentWorkingDir)
sys.path.append(currentWorkingDir)

from Core.IO.mhdReadWrite import *
from Core.IO.dataLoader import listAllFiles, loadAllData
from Core.IO.dicomIO import readDicomCT

if __name__ == '__main__':

    # Load DICOM CT and struct
    inputPaths = "/mnt/c/Users/vhamaide/OneDrive - UCL/Bureau/UCL/ARIES/data/liver/patient_0/4DCT/p0"
    dataList = loadAllData(inputPaths, maxDepth=0)
    CT = dataList[1]
    rt_struct = dataList[0]
    print(type(CT))
    print(type(rt_struct))
    rt_struct.print_ROINames()

    # Save as MHD
    outputPath_CT = "/mnt/c/Users/vhamaide/OneDrive - UCL/Bureau/UCL/ARIES/data/liver/patient_0/MHD_test/p0"
    exportImageMHD(outputPath_CT, CT)

    # Save contour as MHD
    outputPath_contour = "/mnt/c/Users/vhamaide/OneDrive - UCL/Bureau/UCL/ARIES/data/liver/patient_0/MHD_test/p0_GTV"
    contour_GTV = rt_struct.getContourByName('MidP CT GTV')
    contour_GTV_mask = contour_GTV.getBinaryMask(origin=CT.origin, gridSize=CT.gridSize, spacing=CT.spacing)
    exportImageMHD(outputPath_contour, contour_GTV_mask)

    # Read MHD CT and compare with DICOM CT
    CT_MHD = importImageMHD(outputPath_CT+'.mhd')
    # compare the two
    print(np.all(np.isclose(CT_MHD.imageArray, CT.imageArray)))
    print(np.all(CT_MHD.origin == CT.origin))
    print(np.all(CT_MHD.spacing == CT.spacing))
    print(np.all(CT_MHD.gridSize == CT.gridSize))


    # Read MHD contour and compare with DICOM contour
    contour_MHD = importImageMHD(outputPath_contour+'.mhd')
    # compare the two
    print(np.all(contour_MHD.imageArray == contour_GTV_mask.imageArray))
    print(np.all(contour_MHD.origin == contour_GTV_mask.origin))
    print(np.all(contour_MHD.spacing == contour_GTV_mask.spacing))
    print(np.all(contour_MHD.gridSize == contour_GTV_mask.gridSize))


    ### Velocity field
    def_input_path = "/mnt/c/Users/vhamaide/OneDrive - UCL/Bureau/UCL/ARIES/data/liver/patient_0/deformation_fields/p0"
    dataList = loadAllData(def_input_path, maxDepth=0)
    df = dataList[0]
    print(type(df))

    # Save as MHD
    outputPath_df = "/mnt/c/Users/vhamaide/OneDrive - UCL/Bureau/UCL/ARIES/data/liver/patient_0/MHD_test/df0"
    exportImageMHD(outputPath_df, df)

    # Read MHD df and compare with DICOM df
    df_MHD = importImageMHD(outputPath_df+'.mhd')
    # compare the two
    print(np.all(np.isclose(df_MHD.imageArray, df.imageArray)))
    print(np.all(df_MHD.origin == df.origin))
    print(np.all(df_MHD.spacing == df.spacing))
    print(np.all(df_MHD.gridSize == df.gridSize))