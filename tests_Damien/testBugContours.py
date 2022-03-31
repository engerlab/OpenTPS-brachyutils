from Core.IO.dataLoader import loadAllData, listAllFiles
import pydicom


dataPath = '/home/damien/Desktop/Patient_0 (copy)/'


## ---------------------------------------------------------------------------------------
def readDicomStructCor(dcmFile):

    # Read DICOM file
    dcm = pydicom.dcmread(dcmFile)

    if(hasattr(dcm, 'SeriesDescription') and dcm.SeriesDescription != ""): structName = dcm.SeriesDescription
    else: structName = dcm.SeriesInstanceUID

    print('in read dicom struct', structName)

    for dcmStruct in dcm.StructureSetROISequence:

        print(dcmStruct.ROIName)

        refROINumberList = []
        for x, val, in enumerate(dcm.ROIContourSequence):
            # print(x, val.ReferencedROINumber)
            refROINumberList.append(val.ReferencedROINumber)

        doublonIndex = -1
        for elementIndex in range(len(refROINumberList)-1):
            if refROINumberList[elementIndex] == refROINumberList[elementIndex+1]:
                doublonIndex = elementIndex+1
                print('Doublon found ReferencedROINumbers', doublonIndex)

        if doublonIndex != -1:
            print('-1 correction applied')
            for elementIndex in range(doublonIndex):
                # print(dcm.ROIContourSequence[elementIndex].ReferencedROINumber)
                dcm.ROIContourSequence[elementIndex].ReferencedROINumber = dcm.ROIContourSequence[elementIndex].ReferencedROINumber - 1

    pydicom.dcmwrite(dcmFile, dcm)


## ---------------------------------------------------------------------------------------

filesList = listAllFiles(dataPath)
# print(filesList)

for file in filesList['Dicom']:
    dcm = pydicom.dcmread(file)
    if dcm.SOPClassUID == "1.2.840.10008.5.1.4.1.1.481.3":
        print('Struct file found')
        struct = readDicomStructCor(file)

