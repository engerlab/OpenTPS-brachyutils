from PyQt5.QtCore import pyqtSignal, QObject

from GUI.ViewControllers.gridElementController import GridElementController


class GridFourElementController(QObject):
    def __init__(self, viewController):
        QObject.__init__(self)

        self._parent = viewController

        self.botLeftController = GridElementController(parent=self)
        self.botRightController = GridElementController(parent=self)
        self.topLeftController = GridElementController(parent=self)
        self.topRightController = GridElementController(parent=self)

        self.singleImageMode = True

    def getSelectedImageController(self):
        return self._parent.getSelectedImageController()

    def setMainImage(self, imageController):
        self.botLeftController.setMainImage(imageController)
        self.botRightController.setMainImage(imageController)
        self.topLeftController.setMainImage(imageController)
        self.topRightController.setMainImage(imageController)

    def setSecondaryImage(self, imageController):
        self.botLeftController.setSecondaryImage(imageController)
        self.botRightController.setSecondaryImage(imageController)
        self.topLeftController.setSecondaryImage(imageController)
        self.topRightController.setSecondaryImage(imageController)



