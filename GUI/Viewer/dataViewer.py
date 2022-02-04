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
     dataViewer.viewerMode = dataViewer.ViewerModes.STATIC # Static mode (for data which are not time series)
     dataViewer.viewerType = dataViewer.ViewerTypes.VIEWER_IMAGE # Show an image viewer
     dataViewer.viewerMode = dataViewer.ViewerTypes.VIEWER_DVH # Switch to a DVH viewer
    Currently the DataViewer has its own logic based on events in viewController. Should we have a controller to specifically handle the logical part?
    """
    class DisplayTypes(Enum):
        """
            Viewer types
        """
        DEFAULT = 'VIEWER_IMAGE'
        NONE = None
        VIEWER_DVH = 'VIEWER_DVH'
        VIEWER_PROFILE = 'VIEWER_PROFILE'
        VIEWER_IMAGE = 'VIEWER_IMAGE'

    class ViewerModes(Enum):
        """
            Viewer modes
        """
        DEFAULT = 'STATIC'
        STATIC = 'STATIC'
        DYNAMIC = 'DYNAMIC'

    def __init__(self, viewController):
        QWidget.__init__(self)

        # It might seems weird to have a signal which is only used within the class but it is if someday we want to move the logical part out of this class.
        self.droppedImageSignal = Event(object)

        self._currentViewer = None
        self._dropEnabled = False
        self._displayType = None
        self._mainLayout = QVBoxLayout(self)
        self._toolbar = DataViewerToolbar()
        self._viewController = viewController
        self._viewerMode = self.ViewerModes.DEFAULT

        self.setLayout(self._mainLayout)
        self._mainLayout.setContentsMargins(0, 0, 0, 0)

        # For responsiveness, we instantiate all possible viewers and hide them == cached viewers:
        self._dvhViewer = DVHPlot()
        self._dynViewer = DynamicImageViewer(viewController)
        self._noneViewer = BlackEmptyPlot()
        self._profileViewer = ProfilePlot(viewController)
        self._staticViewer = ImageViewer(viewController)

        self._profileViewer.hide()
        self._noneViewer.hide()
        self._dvhViewer.hide()
        self._dynViewer.hide()
        self._staticViewer.hide()

        self._mainLayout.addWidget(self._toolbar)
        self._mainLayout.addWidget(self._dynViewer)
        self._mainLayout.addWidget(self._staticViewer)
        self._mainLayout.addWidget(self._profileViewer)
        self._mainLayout.addWidget(self._noneViewer)
        self._mainLayout.addWidget(self._dvhViewer)

        self._setDisplayType(self.DisplayTypes.DEFAULT)


        # This is the logical part. Should we migrate this to a dedicated controller?
        self._toolbar.displayTypeSignal.connect(self._setDisplayType)

        self._viewController.independentViewsEnabledSignal.connect(self._setDropEnabled)
        self._viewController.mainImageChangedSignal.connect(self._setMainImage)
        self._viewController.secondaryImageChangedSignal.connect(self._setSecondaryImage)

        self._setDropEnabled(self._viewController.independentViewsEnabled)

    @property
    def cachedDynamicImageViewer(self) -> DynamicImageViewer:
        """
            The dynamic image viewer currently in cache (read-only)

            :type: DynamicImageViewer
        """
        return self._dynViewer

    @property
    def cachedStaticDVHViewer(self) -> DVHPlot:
        """
            The DVH viewer currently in cache
        """
        return self._dvhViewer

    @property
    def cachedStaticImageViewer(self) -> ImageViewer:
        """
            The static image viewer currently in cache (read-only)

            :type: ImageViewer
        """
        return self._staticViewer

    @property
    def cachedStaticProfileViewer(self) -> ProfilePlot:
        """
        The profile viewer currently in cache (read-only)

        :type: ProfilePlot
        """
        return self._profileViewer

    @property
    def currentViewer(self) -> Optional[Union[DVHPlot, ProfilePlot, ImageViewer]]:
        """
        The viewer currently displayed (read-only)viewerTypes

        :type: Optional[Union[DVHPlot, ProfilePlot, ImageViewer]]
        """
        return self._currentViewer

    @property
    def displayType(self):
        """
        The display type of the data viewer tells whether a image viewer, a dvh viewer, ... is displayed

        :type: DataViewer.viewerTypes
        """
        return self._displayType

    @displayType.setter
    def displayType(self, displayType):
        self._setDisplayType(displayType)

    def _setDisplayType(self, displayType):
        if displayType == self._displayType:
            return

        if self._viewerMode == self.ViewerModes.DYNAMIC:
            self._setDisplayTypeInDynamicMode(displayType)
        else:
            self._setDisplayTypeInStaticMode(displayType)

    @property
    def viewerMode(self):
        """
        The mode of the viewer can be dynamic for dynamic data (time series) or static for static data
        """
        return self._viewerMode

    @viewerMode.setter
    def viewerMode(self, viewerMode):
        self._viewerMode = viewerMode

        # Reset display
        if self._viewerMode==self.ViewerModes.DYNAMIC:
            self._setDisplayTypeInDynamicMode(self._displayType)
        else:
            self._setDisplayTypeInStaticMode(self._displayType)

    def _setDisplayTypeInDynamicMode(self, displayType):
        if not (self._currentViewer is None):
            self._currentViewer.hide()

        self._displayType = displayType

        if self._displayType == self.DisplayTypes.VIEWER_IMAGE:
            self._currentViewer = self._dynViewer
            self.dropEnabled = self._dropEnabled

            self._viewController.crossHairEnabledSignal.disconnect(self._staticViewer.setCrossHairEnabled)
            self._viewController.windowLevelEnabledSignal.disconnect(self._staticViewer.setWWLEnabled)
        else:
            raise ValueError('Invalid viewer type: ' + str(self._displayType))

        self._toolbar.handleDisplayChange(self.displayType)

        self._currentViewer.show()

    def _setDisplayTypeInStaticMode(self, displayType):
        if not (self._currentViewer is None):
            self._currentViewer.hide()

        self._displayType = displayType

        if self._displayType == self.DisplayTypes.VIEWER_DVH:
            self._currentViewer = self._dvhViewer
        elif self._displayType == self.DisplayTypes.NONE:
            self._currentViewer = self._noneViewer
        elif self._displayType == self.DisplayTypes.VIEWER_PROFILE:
            self._currentViewer = self._profileViewer
        elif self._displayType == self.DisplayTypes.VIEWER_IMAGE:
            self._currentViewer = self._staticViewer
            self.dropEnabled = self._dropEnabled

            self._viewController.crossHairEnabledSignal.connect(self._staticViewer.setCrossHairEnabled)
            self._viewController.lineWidgetEnabledSignal.connect(self._staticViewer.setProfileWidgetEnabled)
            self._viewController.showContourSignal.connect(self._staticViewer._contourLayer.setNewContour)
            self._viewController.windowLevelEnabledSignal.connect(self._staticViewer.setWWLEnabled)

            self._viewController.crossHairEnabledSignal.disconnect(self._dynViewer.setCrossHairEnabled)
            self._viewController.windowLevelEnabledSignal.disconnect(self._dynViewer.setWWLEnabled)
        else:
            raise ValueError('Invalid viewer type: ' + str(self._displayType))

        self._toolbar.handleDisplayChange(self.displayType)

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

        if enabled and (self._displayType == self.DisplayTypes.VIEWER_IMAGE):
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



    ####################################################################################################################
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
            # Stop dynamic image viewer
            if self.viewerMode == self.ViewerModes.DYNAMIC:
                self._viewController.dynamicDisplayController.removeDynamicViewer(self.cachedDynamicImageViewer)
            self.cachedDynamicImageViewer.primaryImage = None

            self.viewerMode = self.ViewerModes.STATIC
            self.cachedStaticImageViewer.primaryImage = image
        elif isinstance(image, Dynamic3DSequence):
            # Stop static image viewer
            self.cachedStaticImageViewer.primaryImage = None
            if self.displayType == self.DisplayTypes.VIEWER_IMAGE:
                self._viewController.dynamicDisplayController.addDynamicViewer(self.cachedDynamicImageViewer)

            self.viewerMode = self.ViewerModes.DYNAMIC
            self.cachedDynamicImageViewer.primaryImage = image
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

