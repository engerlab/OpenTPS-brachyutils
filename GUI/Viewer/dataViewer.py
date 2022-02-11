from enum import Enum
from typing import Union, Optional

from PyQt5.QtWidgets import QWidget, QVBoxLayout

from Core.Data.Images.image3D import Image3D
from Core.Data.dynamic3DSequence import Dynamic3DSequence
from Core.event import Event
from GUI.Viewer.DataViewerComponents.imageViewer import ImageViewer
from GUI.Viewer.DataViewerComponents.dynamicImageViewer import DynamicImageViewer
from GUI.Viewer.DataViewerComponents.imageViewerActions import ImageViewerActions
from GUI.Viewer.DataViewerComponents.secondaryImageActions import SecondaryImageActions
from GUI.Viewer.DataViewerComponents.dataViewerToolbar import DataViewerToolbar
from GUI.Viewer.DataViewerComponents.blackEmptyPlot import BlackEmptyPlot
from GUI.Viewer.DataViewerComponents.dvhPlot import DVHPlot
from GUI.Viewer.DataViewerComponents.profilePlot import ProfilePlot


class DroppedObject:
    """
    This class aims to standardized object dropping
    TODO: we might want to move this to another file
    """
    class DropTypes:
        # DropTypes is not an Enum because Enum does not preserve string type of class attributes. But we want Drop types
        # to be string to be compatible with QMimeData
        IMAGE = 'IMAGE'

    def __init__(self, dropType, droppedData):
        self.dropType = dropType
        self.droppedData = droppedData


class DataViewer(QWidget):
    """
    This class displays the type of viewer specified as input and a toolbar to switch between them.
    All viewers are cached for responsiveness.
    Example::
     dataViewer = DataViewer(viewController)
     dataViewer.viewerMode = dataViewer.ViewerModes.STATIC # Static mode (for data which are not time series)
     dataViewer.displayType = dataViewer.ViewerTypes.VIEWER_IMAGE # Show an image viewer
     dataViewe.displayMode = dataViewer.ViewerTypes.VIEWER_DVH # Switch to a DVH viewer
    Currently the DataViewer has its own logic based on events in viewController. Should we have a controller to specifically handle the logical part?
    """
    class DisplayTypes(Enum):
        """
            Viewer types
        """
        DEFAULT = 'DISPLAY_IMAGE'
        NONE = None
        DISPLAY_DVH = 'DISPLAY_DVH'
        DISPLAY_PROFILE = 'DISPLAY_PROFILE'
        DISPLAY_IMAGE = 'DISPLAY_IMAGE'

    class DisplayModes(Enum):
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
        self.displayTypeChangedSignal = Event(object)

        self._currentViewer = None
        self._displayMode = self.DisplayModes.DEFAULT
        self._displayType = None

        self._dropEnabled = False
        self._viewController = viewController

        self._mainLayout = QVBoxLayout(self)
        self.setLayout(self._mainLayout)
        self._mainLayout.setContentsMargins(0, 0, 0, 0)

        self._toolbar = DataViewerToolbar(self)

        # For responsiveness, we instantiate all possible viewers and hide them == cached viewers:
        self._dvhViewer = DVHPlot()
        self._dynImageViewer = DynamicImageViewer(viewController)
        self._noneViewer = BlackEmptyPlot()
        self._staticProfileviewer = ProfilePlot(viewController)
        self._staticImageViewer = ImageViewer(viewController)

        self._staticProfileviewer.hide()
        self._noneViewer.hide()
        self._dvhViewer.hide()
        self._dynImageViewer.hide()
        self._staticImageViewer.hide()

        self._mainLayout.addWidget(self._toolbar)
        self._mainLayout.addWidget(self._dynImageViewer)
        self._mainLayout.addWidget(self._staticImageViewer)
        self._mainLayout.addWidget(self._staticProfileviewer)
        self._mainLayout.addWidget(self._noneViewer)
        self._mainLayout.addWidget(self._dvhViewer)

        self._setDisplayType(self.DisplayTypes.DEFAULT)

        # Logical control of the DataViewer is set here. We might want to move this to dedicated controller class
        self._initializeControl()

    @property
    def cachedDynamicImageViewer(self) -> DynamicImageViewer:
        """
            The dynamic image viewer currently in cache (read-only)

            :type: DynamicImageViewer
        """
        return self._dynImageViewer

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
        return self._staticImageViewer

    @property
    def cachedStaticProfileViewer(self) -> ProfilePlot:
        """
        The profile viewer currently in cache (read-only)

        :type: ProfilePlot
        """
        return self._staticProfileviewer

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

        isModeDynamic = self._displayMode == self.DisplayModes.DYNAMIC

        if isModeDynamic:
            self._setDisplayInDynamicMode(displayType)
        else:
            self._setDisplayInStaticMode(displayType)

        self.displayTypeChangedSignal.emit(displayType)

    @property
    def displayMode(self):
        """
        The mode of the viewer can be dynamic for dynamic data (time series) or static for static data
        """
        return self._displayMode

    @displayMode.setter
    def displayMode(self, mode):
        if mode == self._displayMode:
            return

        # Notify dynamicDisplayController - we have a problem of multiple responsibilities here
        previousModeWasStatic = self.displayMode == self.DisplayModes.STATIC
        if previousModeWasStatic:
            self._viewController.dynamicDisplayController.addDynamicViewer(self.cachedDynamicImageViewer)
        else:
            self._viewController.dynamicDisplayController.removeDynamicViewer(self.cachedDynamicImageViewer)

        self._displayMode = mode

        # Reset display
        isModeDynamic = self._displayMode == self.DisplayModes.DYNAMIC
        
        if isModeDynamic:
            self._setDisplayInDynamicMode(self._displayType)
        else:
            self._setDisplayInStaticMode(self._displayType)

    def _setDisplayInDynamicMode(self, displayType):
        if not (self._currentViewer is None):
            self._currentViewer.hide()

        self._displayType = displayType

        if self._displayType == self.DisplayTypes.DISPLAY_IMAGE:
            self._setCurrentViewerToDynamicImageViewer()
        elif self._displayType == self.DisplayTypes.DISPLAY_PROFILE:
            self._currentViewer = self._staticProfileviewer
        elif self._displayType == self.DisplayTypes.NONE:
            self._currentViewer = self._noneViewer
        else:
            raise ValueError('Invalid display type: ' + str(self._displayType))

        self._currentViewer.show()

    def _setDisplayInStaticMode(self, displayType):
        if not (self._currentViewer is None):
            self._currentViewer.hide()

        self._displayType = displayType

        if self._displayType == self.DisplayTypes.DISPLAY_DVH:
            self._currentViewer = self._dvhViewer
        elif self._displayType == self.DisplayTypes.NONE:
            self._currentViewer = self._noneViewer
        elif self._displayType == self.DisplayTypes.DISPLAY_PROFILE:
            self._currentViewer = self._staticProfileviewer
        elif self._displayType == self.DisplayTypes.DISPLAY_IMAGE:
            self._setCurrentViewerToStaticImageViewer()
        else:
            raise ValueError('Invalid display type: ' + str(self._displayType))

        self._currentViewer.show()

    def _setCurrentViewerToDynamicImageViewer(self):
        self._currentViewer = self._dynImageViewer
        self.dropEnabled = self._dropEnabled

        self._viewController.crossHairEnabledSignal.disconnect(self._staticImageViewer.setCrossHairEnabled)
        self._viewController.lineWidgetEnabledSignal.disconnect(self._staticImageViewer.setProfileWidgetEnabled)
        self._viewController.showContourSignal.disconnect(self._staticImageViewer._contourLayer.setNewContour)
        self._viewController.windowLevelEnabledSignal.disconnect(self._staticImageViewer.setWWLEnabled)

        self._viewController.crossHairEnabledSignal.connect(self._dynImageViewer.setCrossHairEnabled)
        self._viewController.lineWidgetEnabledSignal.connect(self._dynImageViewer.setProfileWidgetEnabled)
        self._viewController.showContourSignal.connect(self._dynImageViewer._contourLayer.setNewContour)
        self._viewController.windowLevelEnabledSignal.connect(self._dynImageViewer.setWWLEnabled)

    def _setCurrentViewerToStaticImageViewer(self):
        self._currentViewer = self._staticImageViewer
        self.dropEnabled = self._dropEnabled

        self._viewController.crossHairEnabledSignal.disconnect(self._dynImageViewer.setCrossHairEnabled)
        self._viewController.lineWidgetEnabledSignal.disconnect(self._dynImageViewer.setProfileWidgetEnabled)
        self._viewController.showContourSignal.disconnect(self._dynImageViewer._contourLayer.setNewContour)
        self._viewController.windowLevelEnabledSignal.disconnect(self._dynImageViewer.setWWLEnabled)

        self._viewController.crossHairEnabledSignal.connect(self._staticImageViewer.setCrossHairEnabled)
        self._viewController.lineWidgetEnabledSignal.connect(self._staticImageViewer.setProfileWidgetEnabled)
        self._viewController.showContourSignal.connect(self._staticImageViewer._contourLayer.setNewContour)
        self._viewController.windowLevelEnabledSignal.connect(self._staticImageViewer.setWWLEnabled)

    @property
    def dropEnabled(self) -> bool:
        """
        Drag and drop enabled

        :type: bool
        """
        return self._dropEnabled

    @dropEnabled.setter
    #TODO: Should not drop be implemented in each specific viewer?
    def dropEnabled(self, enabled: bool):
        self._dropEnabled = enabled

        if enabled:
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
            droppedIsImage = e.mimeData().text() == DroppedObject.DropTypes.IMAGE

            if droppedIsImage:
                e.accept()
                self.droppedImageSignal.emit(self._viewController.selectedImage)
                return
        e.ignore()



    ####################################################################################################################
    # This is the logical part of the viewer. Should we migrate this to a dedicated controller?
    def _initializeControl(self):
        self._secondaryImageActions = SecondaryImageActions(self._staticImageViewer.secondaryImageLayer)
        self._imageViewerActions = ImageViewerActions(self._staticImageViewer)

        self._secondaryImageActions.addToToolbar(self._toolbar)
        self._imageViewerActions.addToToolbar(self._toolbar)

        self.displayTypeChangedSignal.connect(self._handleDisplayTypeChange)

        self._viewController.independentViewsEnabledSignal.connect(self.enableDropForMainImage)
        self._viewController.mainImageChangedSignal.connect(self._setMainImageAnSwitchDisplaydMode)
        self._viewController.secondaryImageChangedSignal.connect(self._setSecondaryImage)

        self.enableDropForMainImage(self._viewController.independentViewsEnabled)

        self._handleDisplayTypeChange(self.displayType) # Initialize with current display type

    def _handleDisplayTypeChange(self, displayType):
        self._imageViewerActions.hide()
        self._secondaryImageActions.hide()

        if displayType==self.DisplayTypes.DISPLAY_IMAGE:
            self._imageViewerActions.setImageViewer(self._currentViewer)
            self._imageViewerActions.show()
            self._secondaryImageActions.show()


    def enableDropForMainImage(self, enabled):
        """
            Set main image to the appropriate cached image viewer.
            Does not affect viewer visibility.
        """
        self.dropEnabled = enabled

        if enabled:
            # It might seems weird to have a signal connected within the class but it is if someday we want to move the logical part out of this class.
            # See also comment on dropEnabled : Should we implement drop directly in ImageViewer?
            self.droppedImageSignal.connect(self._setMainImageAnSwitchDisplaydMode)
        else:
            self.droppedImageSignal.disconnect(self._setMainImageAnSwitchDisplaydMode)

    def _setMainImageAnSwitchDisplaydMode(self, image):
        """
            Switch display mode according to image type and then display image
        """
        if isinstance(image, Image3D):
            self.displayMode = self.DisplayModes.STATIC
        elif isinstance(image, Dynamic3DSequence):
            self.displayMode = self.DisplayModes.DYNAMIC
        elif image is None:
            pass
        else:
            raise ValueError('Image type not supported')

        self._setMainImage(image)

    def _setMainImage(self, image: Optional[Union[Image3D, Dynamic3DSequence]]):
        """
        Set main image to the appropriate cached image viewer.
        Does not affect viewer visibility.
        """
        if isinstance(image, Image3D):
            self.cachedStaticImageViewer.primaryImage = image
        elif isinstance(image, Dynamic3DSequence):
            self.cachedDynamicImageViewer.primaryImage = image
        elif image is None:
            pass
        else:
            raise ValueError('Image type not supported')

        if not image is None:
            image.patient.imageRemovedSignal.connect(self._removeImageFromViewers)

    def _setSecondaryImage(self, image: Optional[Image3D]):
        """
            Display the image (in static mode)
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
            image.patient.imageRemovedSignal.connect(self._removeImageFromViewers)

        self.cachedStaticImageViewer.secondaryImage = image


    def _removeImageFromViewers(self, image: Image3D):
        """
        Remove image from all cached viewers.
        """
        ""
        if self.cachedStaticImageViewer.primaryImage == image:
            self._setMainImage(None)

        if self.cachedDynamicImageViewer.secondaryImage == image:
            self._setSecondaryImage(None)
