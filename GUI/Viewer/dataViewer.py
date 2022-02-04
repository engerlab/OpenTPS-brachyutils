from enum import Enum
from typing import Union, Optional

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

        if instance._viewerDisplayMode == SliceViewerModes.STATIC:
            instance._viewController.crossHairEnabledSignal.connect(instance._staticViewer.setCrossHairEnabled)
            instance._viewController.lineWidgetEnabledSignal.connect(instance._staticViewer.setProfileWidgetEnabled)
            instance._viewController.showContourSignal.connect(instance._staticViewer._contourLayer.setNewContour)
            instance._viewController.windowLevelEnabledSignal.connect(instance._staticViewer.setWWLEnabled)

            instance._viewController.crossHairEnabledSignal.disconnect(instance._dynViewer.setCrossHairEnabled)
            instance._viewController.windowLevelEnabledSignal.disconnect(instance._dynViewer.setWWLEnabled)

            return instance._staticViewer

        elif instance._viewerDisplayMode == SliceViewerModes.DYN:
            instance._viewController.crossHairEnabledSignal.disconnect(instance._staticViewer.setCrossHairEnabled)
            instance._viewController.windowLevelEnabledSignal.disconnect(instance._staticViewer.setWWLEnabled)

            return instance._dynViewer
        
        else:
            raise ValueError("_viewerDisplayMode has invalid value.")


class ViewerTypes(Enum):
    VIEWER_DVH = 'DVH'
    NONE = 'None'
    VIEWER_PROFILE = 'PROFILE'
    VIEWER_SLICES = 'SLICE'


class SliceViewerModes(Enum):
    STATIC = 'STATIC'
    DYN = 'DYN'


class DataViewer(QWidget):
    _sliceViewer = SliceViewerDescriptor()

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
        self._viewerDisplayMode = SliceViewerModes.STATIC

        #for action in self._sliceViewer.qActions:
        #    action.setParent(self._toolbar)
        #    self._toolbar.addAction(action)

        self.setLayout(self._mainLayout)
        self._mainLayout.setContentsMargins(0, 0, 0, 0)

        self._toolbar.displayTypeSignal.connect(self._setDisplay)

        self._setToolbar(self._toolbar)
        self._setDisplay(ViewerTypes.VIEWER_SLICES)

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
    def currentViewer(self) -> Union[ImageViewer, DVHPlot, BlackEmptyPlot, ProfilePlot]:
        return self._currentViewer

    def _setDisplay(self, displayType):
        if displayType == self._displayType:
            return

        if not (self._currentViewer is None):
            self._currentViewer.hide()

        self._displayType = displayType

        if self._displayType == ViewerTypes.VIEWER_DVH:
            self._currentViewer = DVHPlot()

        if self._displayType == ViewerTypes.NONE:
            self._currentViewer = BlackEmptyPlot()

        if self._displayType == ViewerTypes.VIEWER_PROFILE:
            if self._profileViewer is None:
                self._profileViewer = ProfilePlot(self._viewController)

            self._currentViewer = self._profileViewer

        if self._displayType == ViewerTypes.VIEWER_SLICES:
            self._sliceViewer.qActions.resetVisibility()
            self._currentViewer = self._sliceViewer
            self._setDropEnabled(self._dropEnabled)

        self._toolbar.handleDisplayChange(self._currentViewer)

        if not (self._currentViewer is None):
            self._mainLayout.removeWidget(self._currentViewer)

        self._mainLayout.addWidget(self._currentViewer)
        self._currentViewer.show()


    def _setDropEnabled(self, enabled: bool):
        self._dropEnabled = enabled

        if enabled and (self._displayType == ViewerTypes.VIEWER_SLICES):
            self.setAcceptDrops(True)
            self.dragEnterEvent = lambda event: event.accept()
            self.dropEvent = lambda event: self._dropEvent(event)
        else:
            self.setAcceptDrops(False)


    def _setMainImage(self, image: Optional[Union[Image3D, Dynamic3DSequence]]):
        self._sliceViewer.hide()
        if self._displayType == ViewerTypes.VIEWER_SLICES:

            ## these two ifs check if the viewer display mode switches and notifies the dynamicDisplayController if necessary
            if isinstance(image, Image3D):
                if self._viewerDisplayMode == SliceViewerModes.DYN:
                    self._viewController.dynamicDisplayController.removeDynamicViewer(self._sliceViewer)
                    self._viewerDisplayMode = SliceViewerModes.STATIC

            elif isinstance(image, Dynamic3DSequence):
                if self._viewerDisplayMode == SliceViewerModes.STATIC:
                    self._viewerDisplayMode = SliceViewerModes.DYN
                    self._viewController.dynamicDisplayController.addDynamicViewer(self._sliceViewer)
            ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ##

            elif image is None:
                pass
            else:
                raise ValueError('Image type not supported')

            self._sliceViewer.primaryImage = image

            if not image is None:
                image.patient.imageRemovedSignal.connect(self._handleImageRemoved)

            self._mainLayout.removeWidget(self._sliceViewer)
            self._mainLayout.addWidget(self._sliceViewer)
            self._sliceViewer.show()


    def _setSecondaryImage(self, image: Optional[Image3D]):
        if self._displayType == ViewerTypes.VIEWER_SLICES:
            if self._sliceViewer.secondaryImage == image:
                self._setSecondaryImage(None) # Currently default behavior but is it a good idea?
                return

            if image is None:
                oldImage = self._sliceViewer.secondaryImage
                if oldImage is None:
                    return
            else:
                image.patient.imageRemovedSignal.connect(self._handleImageRemoved)

            self._sliceViewer.secondaryImage = image


    def _handleImageRemoved(self, image: Image3D):
        if self._displayType == ViewerTypes.VIEWER_SLICES and self._sliceViewer.primaryImage == image:
            self._setMainImage(None)

        if self._displayType == ViewerTypes.VIEWER_SLICES and self._sliceViewer.secondaryImage == image:
            self._setSecondaryImage(None)


    def _setToolbar(self, toolbar):
        self._toolbar = toolbar
        self._mainLayout.addWidget(self._toolbar)
