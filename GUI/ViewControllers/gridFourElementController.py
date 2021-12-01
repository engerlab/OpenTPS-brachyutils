from PyQt5.QtCore import pyqtSignal, QObject

from GUI.ViewControllers.gridElementController import GridElementController


class GridFourElementController(QObject):
    def __init__(self, viewController):
        QObject.__init__(self)

        self._parent = viewController

        self.controller0 = GridElementController(parent=self)
        self.controller1 = GridElementController(parent=self)
        self.controller2 = GridElementController(parent=self)
        self.controller3 = GridElementController(parent=self)

        self.singleImageMode = True

    def getSelectedImageController(self):
        return self._parent.getSelectedImageController()

    def setMainImage(self, imageController):
        self.controller0.setMainImage(imageController)
        self.controller1.setMainImage(imageController)
        self.controller2.setMainImage(imageController)
        self.controller3.setMainImage(imageController)

    def setSecondaryImage(self, imageController):
        self.controller0.setSecondaryImage(imageController)
        self.controller1.setSecondaryImage(imageController)
        self.controller2.setSecondaryImage(imageController)
        self.controller3.setSecondaryImage(imageController)



