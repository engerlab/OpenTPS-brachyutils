from PyQt5.QtCore import QObject


class GridController(QObject):
    def __init__(self, viewerPanelController):
        QObject.__init__(self)

        self._gridElementControllers = []
        self._viewerPanelController = viewerPanelController

    def appendGridElementController(self, gridElementController):
        self._gridElementControllers.append(gridElementController)

    def getGridElementControllers(self):
        return self._gridElementControllers

    def getSelectedImageController(self):
        return self._viewerPanelController.getSelectedImageController()

    def removeGridElementController(self, gridElementController):
        self._gridElementControllers.remove(gridElementController)

    def setMainImage(self, imageController):
        for controller in self._gridElementControllers:
            if hasattr(controller, 'setMainImage'):
                controller.setMainImage(imageController)

    def setSecondaryImage(self, imageController):
        for controller in self._gridElementControllers:
            controller.setSecondaryImage(imageController)
