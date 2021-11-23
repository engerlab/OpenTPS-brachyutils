from PyQt5.QtCore import QObject, pyqtSignal


class ModelController(QObject):
    _mainImageChangeSignal = pyqtSignal(object)
    _overlayImageChangeSignal = pyqtSignal(object)

    def __init__(self):
        QObject.__init__(self)

        self._mainImage = None
        self._overlayImage = None
        self._patient = None

    def getMainImageChangeSignal(self):
        return self._mainImageChangeSignal

    def getOverlayImageChangeSignal(self):
        return self._overlayImageChangeSignal

    def setMainImage(self, mainImage):
        self._mainImage = mainImage
        self._mainImageChangeSignal.emit(self._mainImage)

    def setOverlayImage(self, image):
        self._overlayImage = image
        self._overlayImageChangeSignal.emit(self._overlayImage)

    def setPatient(self, patient):
        self._patient = patient

        # If patient is None, we don't have data to display anymore
        if self._patient is None:
            self.setMainImage(None)
            self.setOverlayImage(None)
        else:
            images = self._patient.images
            if len(images)>0:
                self.setMainImage(images[0])


