from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import pyqtSignal

from Core.Data.dynamic3DSequence import Dynamic3DSequence
from Core.event import Event
from GUI.Viewer.Viewers.imageViewer import ImageViewer
from GUI.Viewer.Viewers.dynamicImageViewer import DynamicImageViewer


class MultiTypeImageViewer(QWidget):

    MODE_DYNAMIC = 'DYNAMIC'
    MODE_STATIC = 'STATIC'

    def __init__(self, viewController):
        QWidget.__init__(self)

        self._mainLayout = QVBoxLayout(self)
        self._mainLayout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._mainLayout)

        self._viewController = viewController

        self._mode = self.MODE_STATIC
        self.dynamicModeChangedSignal = Event(object)

        self._dynamicViewer = DynamicImageViewer(self._viewController)
        self._mainLayout.addWidget(self._dynamicViewer)
        self._dynamicViewer.hide()

        self._staticViewer = ImageViewer(self._viewController)
        self._mainLayout.addWidget(self._staticViewer)
        self._staticViewer.show()

        self._viewer = self._staticViewer


    def __getattribute__(self, item):
        try:
            return super().__getattribute__(item)
        except:
            return self._viewer.__getattribute__(item)

    @property
    def primaryImage(self):
        if self._viewer is None:
            return None
        return self._viewer.primaryImage

    @primaryImage.setter
    def primaryImage(self, image):

        if isinstance(image, Dynamic3DSequence):
            self.viewerMode = self.MODE_DYNAMIC
        else:
            self.viewerMode = self.MODE_STATIC
        self._viewer.primaryImage = image

    @property
    def viewerMode(self):
        return self._mode

    @viewerMode.setter
    def viewerMode(self, mode):

        if mode == self._mode:
            return

        self._mode = mode
        self.dynamicModeChangedSignal.emit(self._dynamicViewer)
        self._viewer.hide()

        if self._mode == self.MODE_DYNAMIC:
            self._viewer = self._dynamicViewer
        else:
            self._viewer = self._staticViewer

        self._viewer.show()