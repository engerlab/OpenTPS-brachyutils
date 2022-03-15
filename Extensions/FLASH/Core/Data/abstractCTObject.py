from abc import abstractmethod

from Core.Data.Images.roiMask import ROIMask


class AbstractCTObject:
    @abstractmethod
    def computeROI(self, *args) -> ROIMask:
        raise NotImplementedError
