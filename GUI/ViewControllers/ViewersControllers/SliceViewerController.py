from PyQt5.QtCore import pyqtSignal, QObject


class SliceViewerController(QObject):
    contourAddedSignal = pyqtSignal(object)
    contourRemovedSignal = pyqtSignal(object)
    mainImageChangeSignal = pyqtSignal(object)
    secondaryImageChangeSignal = pyqtSignal(object)
    selectedPositionSignal = pyqtSignal(object)
    wwlValueSignal = pyqtSignal(object)

    def __init__(self):
        QObject.__init__(self)

        self._mainImageController = None
        self._contourControllers = []
        self._secondaryImageController = None

    def appendContour(self, contourController):
        if contourController in self._contourControllers:
            return

        self._contourControllers.append(contourController)
        self.contourAddedSignal.emit(self._contourControllers[-1])

    def removeContour(self, contourController):
        if not (contourController in self._contourControllers):
            return

        self._contourControllers.remove(contourController)
        self.contourRemovedSignal.emit(contourController)

    def setMainImage(self, imageController):
        self._mainImageController = imageController
        self.mainImageChangeSignal.emit(self._mainImageController)

    def setSecondaryImage(self, imageController):
        self._secondaryImageController = imageController
        self.secondaryImageChangeSignal.emit(self._secondaryImageController)


