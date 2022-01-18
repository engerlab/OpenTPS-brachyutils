import os

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QAction

from GUI.Viewer.Viewers.sliceViewerWithContours import SliceViewerWithContours
from GUI.Viewer.gridElementToolbar import GridElementToolbar
from GUI.Viewer.Viewers.blackEmptyPlot import BlackEmptyPlot
from GUI.Viewer.Viewers.dvhPlot import DVHPlot
from GUI.Viewer.Viewers.profilePlot import ProfilePlot
from GUI.Viewer.imageFusionProperties import ImageFusionProperties


class GridElement(QWidget):
    DISPLAY_DVH = 'DVH'
    DISPLAY_NONE = 'None'
    DISPLAY_PROFILE = 'PROFILE'
    DISPLAY_SLICEVIEWER = 'SLICE'

    def __init__(self, viewController):
        QWidget.__init__(self)

        self._currentViewer = None
        self._displayType = None
        self._dropEnabled = False
        self._mainLayout = QVBoxLayout(self)
        self._profileViewer = None
        self._sliceViewer = None
        self._toolbar = GridElementToolbar()
        self._viewController = viewController

        self.setLayout(self._mainLayout)
        self._mainLayout.setContentsMargins(0, 0, 0, 0)

        self._toolbar.displayTypeSignal.connect(self._setDisplay)

        self._setToolbar(self._toolbar)
        self._setDisplay(self.DISPLAY_SLICEVIEWER)

        self._viewController.independentViewsEnabledSignal.connect(self._setDropEnabled)
        self._setDropEnabled(self._viewController.independentViewsEnabled)
        self._viewController.mainImageChangedSignal.connect(self._setMainImage)
        self._viewController.secondaryImageChangedSignal.connect(self._setSecondaryImage)

    def _dropEvent(self, e):
        if e.mimeData().hasText():
            if (e.mimeData().text() == 'image'):
                e.accept()
                if hasattr(self._currentViewer, 'mainImage'):
                    self._setMainImage(self._viewController.selectedImage)
                return
        e.ignore()

    @property
    def currentViewer(self):
        return self._currentViewer

    def _setDisplay(self, displayType):
        if displayType==self._displayType:
            return

        if not (self._currentViewer is None):
            self._currentViewer.hide()

        self._displayType = displayType

        if self._displayType==self.DISPLAY_DVH:
            self._currentViewer = DVHPlot()

        if self._displayType==self.DISPLAY_NONE:
            self._currentViewer = BlackEmptyPlot()

        if self._displayType==self.DISPLAY_PROFILE:
            if self._profileViewer is None:
                self._profileViewer = ProfilePlot(self._viewController)

            self._currentViewer = self._profileViewer

        if self._displayType==self.DISPLAY_SLICEVIEWER:
            if self._sliceViewer is None:
                self._sliceViewer = SliceViewerWithContours(self._viewController)

            self._currentViewer = self._sliceViewer

            self._setDropEnabled(self._dropEnabled)

        self._toolbar.handleDisplayChange(self._currentViewer)

        if not (self._currentViewer is None):
            self._mainLayout.removeWidget(self._currentViewer)

        self._mainLayout.addWidget(self._currentViewer)
        self._currentViewer.show()

    def _setDropEnabled(self, enabled):
        self._dropEnabled = enabled

        if enabled and self._displayType==self.DISPLAY_SLICEVIEWER:
            self._currentViewer.setAcceptDrops(True)
            self._currentViewer.dragEnterEvent = lambda event: event.accept()
            self._currentViewer.dropEvent = lambda event: self._dropEvent(event)
        else:
            self._currentViewer.setAcceptDrops(False)

    def _setMainImage(self, image):
        if hasattr(self._currentViewer, 'mainImage'):
            self._currentViewer.mainImage = image

            if not(image is None):
                image.patient.imageRemovedSignal.connect(self._handleImageRemoved)

    def _setSecondaryImage(self, image):
        if hasattr(self._currentViewer, 'secondaryImage'):
            self._currentViewer.secondaryImage = image

            if not(image is None):
                image.patient.imageRemovedSignal.connect(self._handleImageRemoved)

                iconPath = 'GUI' + os.path.sep + 'res' + os.path.sep + 'icons' + os.path.sep
                self._buttonProperties = QAction(QIcon(iconPath + "color-adjustment.png"), "Range", self)
                self._buttonProperties.setStatusTip("Range")
                self._buttonProperties.triggered.connect(lambda pressed: ImageFusionProperties(image, self).show())
                self._toolbar.addAction(self._buttonProperties)

    def _handleImageRemoved(self, image):
        if hasattr(self._currentViewer, 'mainImage') and self._currentViewer.mainImage == image:
            self._setMainImage(None)

        if hasattr(self._currentViewer, 'secondaryImage') and self._currentViewer.secondaryImage == image:
            self._setSecondaryImage(None)

    def _setToolbar(self, toolbar):
        self._toolbar = toolbar
        self._mainLayout.addWidget(self._toolbar)
