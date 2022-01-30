
from PyQt5.QtWidgets import QWidget, QVBoxLayout

from Core.Data.Images.image3D import Image3D
from Core.Data.dynamic3DSequence import Dynamic3DSequence
from GUI.Viewer.Viewers.imageViewer import ImageViewer
from GUI.Viewer.Viewers.dynamicImageViewer import DynamicImageViewer
from GUI.Viewer.dataViewerToolbar import DataViewerToolbar
from GUI.Viewer.Viewers.blackEmptyPlot import BlackEmptyPlot
from GUI.Viewer.Viewers.dvhPlot import DVHPlot
from GUI.Viewer.Viewers.profilePlot import ProfilePlot

class SliceViewerDescriptor():
    def __get__(self, instance, objType=None):
        if not hasattr(instance, '_dynViewer'):
            instance._dynViewer = DynamicImageViewer(instance._viewController)
            instance._staticViewer = ImageViewer(instance._viewController)

        if instance._viewerDisplayMode == instance.VIEWER_STATIC:
            return instance._staticViewer
        elif instance._viewerDisplayMode == instance.VIEWER_DYN:
            return instance._dynViewer
        else:
            raise ValueError("_viewerDisplayMode has invalid value.")


class DataViewer(QWidget):

    DISPLAY_DVH = 'DVH'
    DISPLAY_NONE = 'None'
    DISPLAY_PROFILE = 'PROFILE'
    DISPLAY_SLICEVIEWER = 'SLICE'

    VIEWER_STATIC = 'STATIC'
    VIEWER_DYN = 'DYN'

    sliceViewer = SliceViewerDescriptor()


    def __init__(self, viewController):
        QWidget.__init__(self)

        self._currentViewer = None
        self._displayType = None
        self._displayMode = None
        self._dropEnabled = False
        self._mainLayout = QVBoxLayout(self)
        self._profileViewer = None
        self._secondaryActions = None
        self._toolbar = DataViewerToolbar()
        self._viewController = viewController
        self._viewerDisplayMode = self.VIEWER_STATIC

        for action in self.sliceViewer.qActions:
            action.setParent(self._toolbar)
            self._toolbar.addAction(action)

        self.setLayout(self._mainLayout)
        self._mainLayout.setContentsMargins(0, 0, 0, 0)

        self._toolbar.displayTypeSignal.connect(self._setDisplay)

        self._setToolbar(self._toolbar)
        self._setDisplay(self.DISPLAY_SLICEVIEWER)
        # self._setMode(self.MODE_STATIC)

        self._viewController.independentViewsEnabledSignal.connect(self._setDropEnabled)
        self._setDropEnabled(self._viewController.independentViewsEnabled)
        self._viewController.mainImageChangedSignal.connect(self._setMainImage)
        self._viewController.secondaryImageChangedSignal.connect(self._setSecondaryImage)


    def _dropEvent(self, e):
        if e.mimeData().hasText():
            if (e.mimeData().text() == 'image'):
                e.accept()
                self._setMainImage(self._viewController.selectedImage)
                return
        e.ignore()

    @property
    def currentViewer(self):
        return self._currentViewer

    def _setDisplay(self, displayType):
        if displayType == self._displayType:
            return

        if not (self._currentViewer is None):
            self._currentViewer.hide()

        self._displayType = displayType

        if self._displayType == self.DISPLAY_DVH:
            self._currentViewer = DVHPlot()

        if self._displayType == self.DISPLAY_NONE:
            self._currentViewer = BlackEmptyPlot()

        if self._displayType == self.DISPLAY_PROFILE:
            if self._profileViewer is None:
                self._profileViewer = ProfilePlot(self._viewController)

            self._currentViewer = self._profileViewer

        if self._displayType == self.DISPLAY_SLICEVIEWER:
            self.sliceViewer.qActions.resetVisibility()
            self._currentViewer = self.sliceViewer
            self._setDropEnabled(self._dropEnabled)

        self._toolbar.handleDisplayChange(self._currentViewer)

        if not (self._currentViewer is None):
            self._mainLayout.removeWidget(self._currentViewer)


        self._mainLayout.addWidget(self._currentViewer)
        self._currentViewer.show()


    def _setDropEnabled(self, enabled):
        self._dropEnabled = enabled

        if enabled and (self._displayType == self.DISPLAY_SLICEVIEWER):
            self._currentViewer.setAcceptDrops(True)
            self._currentViewer.dragEnterEvent = lambda event: event.accept()
            self._currentViewer.dropEvent = lambda event: self._dropEvent(event)
        else:
            self._currentViewer.setAcceptDrops(False)


    def _setMainImage(self, image):
        self._currentViewer.hide()
        if self._displayType == self.DISPLAY_SLICEVIEWER:
            if isinstance(image, Image3D):
                self._viewerDisplayMode = self.VIEWER_STATIC
            elif isinstance(image, Dynamic3DSequence):
                self._viewerDisplayMode = self.VIEWER_DYN
            elif image is None:
                pass
            else:
                raise ValueError('Image type not supported')

            self._currentViewer.primaryImage = image

            if not image is None:
                image.patient.imageRemovedSignal.connect(self._handleImageRemoved)

            self._currentViewer.show()


    def _setSecondaryImage(self, image):
        if self._displayType == self.DISPLAY_SLICEVIEWER:
            if self._currentViewer.secondaryImage == image:
                self._setSecondaryImage(None) # Currently default behavior but is it a good idea?
                return

            if image is None:
                oldImage = self._currentViewer.secondaryImage
                if oldImage is None:
                    return
            else:
                image.patient.imageRemovedSignal.connect(self._handleImageRemoved)

            self._currentViewer.secondaryImage = image


    def _handleImageRemoved(self, image):
        if self._displayType == self.DISPLAY_SLICEVIEWER and self._currentViewer.primaryImage == image:
            self._setMainImage(None)

        if self._displayType == self.DISPLAY_SLICEVIEWER and self._currentViewer.secondaryImage == image:
            self._setSecondaryImage(None)


    def _setToolbar(self, toolbar):
        self._toolbar = toolbar
        self._mainLayout.addWidget(self._toolbar)
