from enum import Enum
from typing import Union, Optional

from PyQt5.QtWidgets import QWidget, QVBoxLayout

from Core.Data.Images.image3D import Image3D
from Core.Data.dynamic3DSequence import Dynamic3DSequence
from Core.event import Event
from GUI.Viewer.Viewers.imageViewer import ImageViewer
from GUI.Viewer.Viewers.dynamicImageViewer import DynamicImageViewer
from GUI.Viewer.dataViewerToolbar import DataViewerToolbar
from GUI.Viewer.Viewers.blackEmptyPlot import BlackEmptyPlot
from GUI.Viewer.Viewers.dvhPlot import DVHPlot
from GUI.Viewer.Viewers.profilePlot import ProfilePlot


class DataViewer(QWidget):
    """
    This class displays the type of viewer specified as input and a toolbar to switch between them.
    All viewers are cached for responsiveness.
    Example::
     dataViewer = DataViewer(viewController)
     dataViewer.viewerType = dataViewer.viewerTypes.VIEWER_IMAGE # Show an image viewer
     dataViewer.viewerType = dataViewer.viewerTypes.VIEWER_IMAGE_DYN # Switch to a dynamic viewer
     dataViewer.viewerMode = dataViewer.viewerTypes.VIEWER_DVH # Switch to a DVH viewer
    Currently the DataViewer has its own logic based on events in viewController. Should we have a controller to specifically handle the logical part?
    """
    class viewerTypes(Enum):
        """
            Viewer types
        """
        DEFAULT = 'VIEWER_IMAGE_AUTO'
        NONE = None
        VIEWER_DVH = 'VIEWER_DVH'
        VIEWER_PROFILE = 'VIEWER_PROFILE'
        VIEWER_IMAGE_AUTO = 'VIEWER_IMAGE_AUTO' # Automatically switches to VIEWER_IMAGE_DYN if it already has an image to show
        VIEWER_IMAGE = 'VIEWER_IMAGE'
        VIEWER_IMAGE_DYN = 'VIEWER_IMAGE_DYN'

    def __init__(self, viewController):
        QWidget.__init__(self)

        # It might seems weird to have a signal which is only used within the class but it is if someday we want to move the logical part out of this class.
        self.droppedImageSignal = Event(object)

        self._currentViewer = None
        self._dropEnabled = False
        self._secondaryActions = None
        self._toolbar = DataViewerToolbar()
        self._viewerType = None
        self.viewerQActions = []
        self._viewController = viewController

        self._dvhViewer = DVHPlot()
        self._dynViewer = DynamicImageViewer(viewController)
        self._mainLayout = QVBoxLayout(self)
        self._noneViewer = BlackEmptyPlot()
        self._profileViewer = ProfilePlot(viewController)
        self._staticViewer = ImageViewer(viewController)

        self._profileViewer.hide()
        self._noneViewer.hide()
        self._dvhViewer.hide()
        self._dynViewer.hide()
        self._staticViewer.hide()

        self.setLayout(self._mainLayout)
        self._mainLayout.setContentsMargins(0, 0, 0, 0)

        self._mainLayout.addWidget(self._toolbar)
        self._mainLayout.addWidget(self._dynViewer)
        self._mainLayout.addWidget(self._staticViewer)
        self._mainLayout.addWidget(self._profileViewer)
        self._mainLayout.addWidget(self._noneViewer)
        self._mainLayout.addWidget(self._dvhViewer)

        self._toolbar.displayTypeSignal.connect(self._setViewerType)

        self._setViewerType(self.viewerTypes.DEFAULT)


        # This is the logical part. Should we migrate this to a dedicated controller?
        self._viewController.independentViewsEnabledSignal.connect(self._setDropEnabled)
        self._viewController.mainImageChangedSignal.connect(self._setMainImage)
        self._viewController.secondaryImageChangedSignal.connect(self._setSecondaryImage)

        self._setDropEnabled(self._viewController.independentViewsEnabled)

    @property
    def cachedDynamicImageViewer(self):
        """
            The dynamic image viewer currently in cache (read-only)

            :type: DynamicImageViewer
        """
        return self._dynViewer

    @property
    def cachedStaticImageViewer(self):
        """
            The static image viewer currently in cache (read-only)

            :type: ImageViewer
        """
        return self._staticViewer

    @property
    def currentViewer(self) -> Optional[Union[DVHPlot, ProfilePlot, ImageViewer]]:
        """
        The viewer currently displayed (read-only)viewerTypes

        :type: Optional[Union[DVHPlot, ProfilePlot, ImageViewer]]
        """
        return self._currentViewer

    @property
    def viewerType(self):
        """
        The type of data viewer currently displayed

        :type: DataViewer.viewerTypes
        """
        return self._viewerType

    @viewerType.setter
    def viewerType(self, viewerType):
        self._setViewerType(viewerType)

    def _setViewerType(self, viewerType):
        if viewerType == self._viewerType:
            return

        if not (self._currentViewer is None):
            self._currentViewer.hide()

        self._viewerType = viewerType

        if self._viewerType == self.viewerTypes.VIEWER_DVH:
            self._currentViewer = self._dvhViewer
        elif self._viewerType == self.viewerTypes.NONE:
            self._currentViewer = self._noneViewer
        elif self._viewerType == self.viewerTypes.VIEWER_PROFILE:
            self._currentViewer = self._profileViewer
        elif self._viewerType == self.viewerTypes.VIEWER_IMAGE_AUTO:
            if self._viewerType==self.viewerTypes.VIEWER_IMAGE or self._viewerType==self.viewerTypes.VIEWER_IMAGE_DYN:
                return
            elif not (self._dynViewer.primaryImage is None):
                self._setViewerType(self.viewerTypes.VIEWER_IMAGE_DYN)
            else:
                self._setViewerType(self.viewerTypes.VIEWER_IMAGE)
            return
        elif self._viewerType == self.viewerTypes.VIEWER_IMAGE:
            self._currentViewer = self._staticViewer
            self.dropEnabled = self._dropEnabled

            self._viewController.crossHairEnabledSignal.connect(self._staticViewer.setCrossHairEnabled)
            self._viewController.lineWidgetEnabledSignal.connect(self._staticViewer.setProfileWidgetEnabled)
            self._viewController.showContourSignal.connect(self._staticViewer._contourLayer.setNewContour)
            self._viewController.windowLevelEnabledSignal.connect(self._staticViewer.setWWLEnabled)

            self._viewController.crossHairEnabledSignal.disconnect(self._dynViewer.setCrossHairEnabled)
            self._viewController.windowLevelEnabledSignal.disconnect(self._dynViewer.setWWLEnabled)
        elif self._viewerType == self.viewerTypes.VIEWER_IMAGE_DYN:
            self._currentViewer = self._dynViewer
            self.dropEnabled = self._dropEnabled

            self._viewController.crossHairEnabledSignal.disconnect(self._staticViewer.setCrossHairEnabled)
            self._viewController.windowLevelEnabledSignal.disconnect(self._staticViewer.setWWLEnabled)
        else:
            raise ValueError('Invalid viewer type: ' + str(self._viewerType))

        self._toolbar.handleDisplayChange(self.viewerType)

        self._currentViewer.show()

    @property
    def dropEnabled(self) -> bool:
        """
        Drag and drop enabled

        :type: bool
        """
        return self._dropEnabled

    @dropEnabled.setter
    def dropEnabled(self, enabled: bool):
        self._dropEnabled = enabled

        if enabled and (self._viewerType == self.viewerTypes.VIEWER_IMAGE or self._viewerType == self.viewerTypes.VIEWER_IMAGE_DYN):
            self.setAcceptDrops(True)
            self.dragEnterEvent = lambda event: event.accept()
            self.dropEvent = lambda event: self._dropEvent(event)
        else:
            self.setAcceptDrops(False)

    def _dropEvent(self, e):
        """
            Handles a drop in the data viewer
        """
        if e.mimeData().hasText():
            if (e.mimeData().text() == 'image'):
                e.accept()
                self.droppedImageSignal.emit(self._viewController.selectedImage)
                return
        e.ignore()


    # This is the logical part of the viewer. Should we migrate this to a dedicated controller?
    def _setDropEnabled(self, enabled):
        self.dropEnabled = enabled

        if enabled:
            # It might seems weird to have a signal connected within the class but it is if someday we want to move the logical part out of this class.
            self.droppedImageSignal.connect(self._setMainImage)
        else:
            self.droppedImageSignal.disconnect(self._setMainImage)

    def _setMainImage(self, image: Optional[Union[Image3D, Dynamic3DSequence]]):
        """
        Selects the slice viewer type according to the image type and display the image.
        Does not affect viewer visibility.
        """
        if isinstance(image, Image3D):
            self.viewerType = self.viewerTypes.VIEWER_IMAGE
            self.cachedStaticImageViewer.primaryImage = image

            # Stop dynamic image viewer
            self.cachedDynamicImageViewer.primaryImage = None
            if self.viewerType == self.viewerTypes.VIEWER_IMAGE_DYN:
                self._viewController.dynamicDisplayController.removeDynamicViewer(self.cachedDynamicImageViewer)
        elif isinstance(image, Dynamic3DSequence):
            self.viewerType = self.viewerTypes.VIEWER_IMAGE_DYN
            self.cachedDynamicImageViewer.primaryImage = image

            # Stop static image viewer
            self.cachedStaticImageViewer.primaryImage = None
            if self.viewerType == self.viewerTypes.VIEWER_IMAGE:
                self._viewController.dynamicDisplayController.addDynamicViewer(self.cachedDynamicImageViewer)
        elif image is None:
            pass
        else:
            raise ValueError('Image type not supported')

        if not image is None:
            image.patient.imageRemovedSignal.connect(self._removeImage)

    def _setSecondaryImage(self, image: Optional[Image3D]):
        """
            Display the image.
            Does not affect viewer visibility nor viewer type.
        """
        if self.cachedStaticImageViewer.secondaryImage == image:
            self.cachedStaticImageViewer.secondaryImage = None # Currently default behavior but is it a good idea?
            return

        if image is None:
            oldImage = self.cachedStaticImageViewer.secondaryImage
            if oldImage is None:
                return
        else:
            image.patient.imageRemovedSignal.connect(self._removeImage)

        self.cachedStaticImageViewer.secondaryImage = image


    def _removeImage(self, image: Image3D):
        """
        Remove image from all cached viewers.
        """
        ""
        if self.cachedStaticImageViewer.primaryImage == image:
            self._setMainImage(None)

        if self.cachedDynamicImageViewer.secondaryImage == image:
            self._setSecondaryImage(None)

