from PyQt5.QtCore import QObject


class GridController(QObject):
    def __init__(self, parent):
        QObject.__init__(self)

        self._independentViewsEnabled = None
        self._parent = parent
        self._gridElementControllers = []

        self.setIndependentViewsEnabled(False)

    def appendGridElementController(self, gridElementController):
        self._gridElementControllers.append(gridElementController)

    def getGridElementControllers(self):
        return self._gridElementControllers

    def getSelectedImageController(self):
        return self._parent.getSelectedImageController()

    def removeGridElementController(self, gridElementController):
        self._gridElementControllers.remove(gridElementController)

    def setIndependentViewsEnabled(self, enabled):
        if self._independentViewsEnabled==enabled:
            return

        if enabled:
            for controller in self._gridElementControllers:
                controller.setDropEnabled(True)
        else:
            for controller in self._gridElementControllers:
                controller.setDropEnabled(False)

        self._independentViewsEnabled = enabled

    def setMainImage(self, imageController):
        for controller in self._gridElementControllers:
            controller.setMainImage(imageController)

    def setSecondaryImage(self, imageController):
        for controller in self._gridElementControllers:
            controller.setSecondaryImage(imageController)
