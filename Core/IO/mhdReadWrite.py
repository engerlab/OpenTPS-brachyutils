import os, sys
import numpy as np
import logging

from Core.Data.Images.image3D import Image3D


def importImageMHD(headerFile):
    """
    Import image from a pair of MHD header and binary files.

    Parameters
    ----------
    headerFile: str
        Path of the MHD header file to be imported.

    Returns
    -------
    image: image3D object
        The function returns the imported image if successfully imported, or None in case of error.
    """
    # Parse file path
    inputFolder, inputFile = os.path.split(headerFile)
    fileName, fileExtension = os.path.splitext(inputFile)

    metaData = readHeaderMHD(headerFile)
    binaryFile = os.path.join(inputFolder, metaData["ElementDataFile"])
    image = readBinaryMHD(binaryFile, metaData)
    return image



def exportImageMHD(outputPath, image):
    """
    Export image in MHD format (header + binary files).

    Parameters
    ----------
    outputPath: str
        Path of the MHD header file that will be generated.

    image: image3D (or sub-class) object
        Image to be exported.
    """

    # Parse file path
    destFolder, destFile = os.path.split(outputPath)
    fileName, fileExtension = os.path.splitext(destFile)
    if fileExtension == ".mhd" or fileExtension == ".MHD":
      mhdFile = destFile
      rawFile = fileName + ".raw"
    else:
      mhdFile = destFile + ".mhd"
      rawFile = destFile + ".raw"
    mhdPath = os.path.join(destFolder, mhdFile)
    rawPath = os.path.join(destFolder, rawFile)

    metaData = generateDefaultMetaData()
    metaData["NDims"] = len(image._spacing)
    metaData["DimSize"] = image._imageArray.shape
    metaData["ElementSpacing"] = tuple(image._spacing)
    metaData["Offset"] = tuple(image._origin)
    metaData["ElementDataFile"] = rawFile

    writeHeaderMHD(mhdPath, metaData=metaData)
    writeBinaryMHD(rawPath, image._imageArray, metaData=metaData)




def generateDefaultMetaData():
    """
    Generate a Python dictionary with default values for MHD header parameters.

    Returns
    -------
    metaData: dictionary
        The function returns a Python dictionary with default MHD header information
    """

    return {
        "ObjectType": "Image",
        "NDims": 3,
        "ElementNumberOfChannels": 1,
        "DimSize": (0,0,0),
        "ElementSpacing": (1.0, 1.0, 1.0),
        "Offset": (0.0, 0.0, 0.0),
        "TransformMatrix": (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0),
        "CenterOfRotation": (0.0, 0.0, 0.0),
        "BinaryData": True,
        "CompressedData": False,
        "ElementByteOrderMSB": False,
        "ElementType": "MET_FLOAT",
        "ElementDataFile": ""
    }



def readHeaderMHD(headerFile):
    """
    Read and parse the MHD header file.

    Parameters
    ----------
    headerFile: str
        Path of the MHD header file to be loaded.

    Returns
    -------
    metaData: dictionary
        The function returns a Python dictionary with the header information
    """

    # Parse file path
    folderPath, inputFile = os.path.split(headerFile)
    fileName, fileExtension = os.path.splitext(inputFile)

    metaData = None
    
    with open(headerFile, 'r') as fid:

        # default meta data
        metaData = generateDefaultMetaData()

        # parse header data
        for line in fid:
        
            # remove comments
            if line[0] == '#': continue
            line = line.split('#')[0]
          
            # clean the string and extract key & value
            line = line.replace('\r', '').replace('\n', '').replace('\t', ' ')
            line = line.split('=')
            key = line[0].replace(' ', '')
            value = line[1].split(' ')
            value = list(filter(len, value))

          
            if "ObjectType" in key:
                metaData["ObjectType"] = value[0]

            elif "NDims" in key:
                metaData["NDims"] = int(value[0])
            
            elif "ElementNumberOfChannels" in key:
                metaData["ElementNumberOfChannels"] = int(value[0])
            
            elif "DimSize" in key:
                metaData["DimSize"] = (int(value[0]), int(value[1]), int(value[2]))
            
            elif "ElementSpacing" in key:
                metaData["ElementSpacing"] = (float(value[0]), float(value[1]), float(value[2]))
            
            elif "Offset" in key:
                metaData["Offset"] = (float(value[0]), float(value[1]), float(value[2]))
            
            elif "TransformMatrix" in key:
                metaData["TransformMatrix"] = (float(value[0]), float(value[1]), float(value[2]), \
                                                 float(value[3]), float(value[4]), float(value[5]), \
                                                 float(value[6]), float(value[7]), float(value[8]))
            
            elif "CenterOfRotation" in key:
                metaData["CenterOfRotation"] = (float(value[0]), float(value[1]), float(value[2]))
          
            elif "BinaryData" in key:
                metaData["BinaryData"] = bool(value[0])
          
            elif "CompressedData" in key:
                metaData["CompressedData"] = bool(value[0])
          
            elif "ElementByteOrderMSB" in key:
                metaData["ElementByteOrderMSB"] = bool(value[0])
            
            elif "ElementType" in key:
                metaData["ElementType"] = value[0]
            
            elif "ElementDataFile" in key:
                if os.path.isabs(value[0]):
                    metaData["ElementDataFile"] = value[0]
                else:
                    metaData["ElementDataFile"] = os.path.join(folderPath, value[0])

    return metaData



def readBinaryMHD(inputPath, metaData=None):
    """
    Read and the MHD binary file.

    Parameters
    ----------
    inputPath: str
        Path of the input binary file

    metaData: dictionary
        Python dictionary with the MHD header information

    Returns
    -------
    image: image3D object
        The function returns the imported image if successfully imported, or None in case of error.
    """

    # Parse file path
    folderPath, outputFile = os.path.split(inputPath)
    fileName, fileExtension = os.path.splitext(outputFile)

    if not os.path.isfile(inputPath):
        logging.error("ERROR: file " + inputPath + " not found!")
        return None

    if metaData == None:
        metaData = generateDefaultMetaData()

    # import data
    if metaData["ElementType"] == "MET_DOUBLE":
        data = np.fromfile(metaData["ElementDataFile"], dtype=np.float)
    else:
        data = np.fromfile(metaData["ElementDataFile"], dtype=np.float32)
    data = data.reshape(metaData["DimSize"], order='F')

    # return Image3D object
    image = Image3D(imageArray=data, name=fileName, origin=metaData["Offset"], spacing=metaData["ElementSpacing"])
    return image



def writeHeaderMHD(outputPath, metaData=None):
    """
    Write MHD header file.

    Parameters
    ----------
    outputPath: str
        Path of the MHD header file to be exported.

    metaData: dictionary
        Python dictionary with the header information
    """

    # Parse file path
    destFolder, destFile = os.path.split(outputPath)
    fileName, fileExtension = os.path.splitext(destFile)
    if fileExtension == ".mhd" or fileExtension == ".MHD":
      mhdFile = destFile
      rawFile = fileName + ".raw"
    else:
      mhdFile = destFile + ".mhd"
      rawFile = destFile + ".raw"
    mhdPath = os.path.join(destFolder, mhdFile)

    if metaData == None:
        metaData = generateDefaultMetaData()

    if metaData["ElementDataFile"] == "":
        metaData["ElementDataFile"] = rawFile

    # Write header file
    logging.info("Write MHD file: " + mhdPath)
    with open(mhdPath, "w") as fid:
        for key in metaData:
            fid.write(key + " = ")
            if isinstance(metaData[key], list) or isinstance(metaData[key], tuple):
                for element in metaData[key]: fid.write(str(element) + " ")
            else:
                fid.write(str(metaData[key]))
            fid.write("\n") 



def writeBinaryMHD(outputPath, data, metaData=None):
    """
    Write MHD binary file.

    Parameters
    ----------
    outputPath: str
        Path of the output binary file.

    data: Numpy array
        Numpy array with the image to be exported.

    metaData: dictionary
        Python dictionary with the MHD header information.
    """

    # Parse file path
    destFolder, destFile = os.path.split(outputPath)
    fileName, fileExtension = os.path.splitext(destFile)
    if fileExtension == ".raw" or fileExtension == ".RAW":
      rawFile = destFile
    else:
      rawFile = destFile + ".raw"
    rawPath = os.path.join(destFolder, rawFile)

    if metaData == None:
        metaData = generateDefaultMetaData()
        metaData["ElementDataFile"] = rawFile
      
    # convert data type
    if metaData["ElementType"] == "MET_DOUBLE" and data.dtype != "float64":
      data = np.copy(data).astype("float64")
    elif metaData["ElementType"] == "MET_FLOAT" and data.dtype != "float32":
      data = np.copy(data).astype("float32")
    
    if data.dtype.byteorder == '>':
      data.byteswap() 
    elif data.dtype.byteorder == '=' and sys.byteorder != "little":
      data.byteswap()
  
    # Write binary file
    with open(rawPath,"w") as fid:
        data.reshape(data.size, order='F').tofile(fid)