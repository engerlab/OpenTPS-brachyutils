from Extensions.FLASH.Core.Data.cem import CEM
from Extensions.FLASH.Core.IO.numpyToSTL import numpyToSTL


def writeCEM(cem:CEM, filePath:str):
    numpyToSTL(cem.imageArray*cem.rsp, cem.spacing, filePath)
