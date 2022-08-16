from enum import Enum
from typing import Union, Optional

from PyQt5.QtWidgets import QWidget, QVBoxLayout

from Core.Data.Images.doseImage import DoseImage
from Core.Data.Images.image3D import Image3D
from Core.Data.Images.image2D import Image2D
from Core.Data.DynamicData.dynamic3DSequence import Dynamic3DSequence
from Core.Data.DynamicData.dynamic3DModel import Dynamic3DModel
from Core.Data.DynamicData.dynamic2DSequence import Dynamic2DSequence
from Core.Data.Plan.rtPlan import RTPlan
from Core.event import Event
from GUI.Viewer.DataViewerComponents.dvhViewerActions import DVHViewerActions
from GUI.Viewer.DataViewerComponents.image3DViewer import Image3DViewer
from GUI.Viewer.DataViewerComponents.dynamicImage3DViewer import DynamicImage3DViewer
from GUI.Viewer.DataViewerComponents.image2DViewer import Image2DViewer
from GUI.Viewer.DataViewerComponents.dynamicImage2DViewer import DynamicImage2DViewer
from GUI.Viewer.DataViewerComponents.imageViewerActions import ImageViewerActions
from GUI.Viewer.DataViewerComponents.dataViewerToolbar import DataViewerToolbar
from GUI.Viewer.DataViewerComponents.blackEmptyPlot import BlackEmptyPlot
from GUI.Viewer.DataViewerComponents.dvhPlot import DVHViewer
from GUI.Viewer.DataViewerComponents.profileViewer import ProfileViewer


class DroppedObject:
    """
    This class aims to standardized object dropping
    TODO: we might want to move this to another file
    """
    class DropTypes:
        # DropTypes is not an Enum because Enum does not preserve string type of class attributes. But we want Drop types
        # to be string to be compatible with QMimeData
        IMAGE = 'IMAGE'
        PLAN = 'PLAN'

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

    class DropModes(Enum):
        AUTO = 'auto'
        PRIMARY = 'primary'
        SECONDARY = 'secondary'
        DEFAULT = 'auto'

    def __init__(self, viewController):
        QWidget.__init__(self)

        # It might seems weird to have a signal which is only used within the class but it is if someday we want to move the logical part out of this class.
        self.droppedImageSignal = Event(object)
        self.droppedPlanSignal = Event(object)
        self.displayTypeChangedSignal = Event(object)

        self._viewController = viewController

        self._currentViewer = None
        self._displayMode = self.DisplayModes.DEFAULT
        self._displayType = None

        self._dropMode = self._viewController.dropMode
        self._dropEnabled = False

        self._mainLayout = QVBoxLayout(self)
        self.setLayout(self._mainLayout)
        self._mainLayout.setContentsMargins(0, 0, 0, 0)

        self._toolbar = DataViewerToolbar(self)

        # For responsiveness, we instantiate all possible viewers and hide them == cached viewers:
        self._dvhViewer = DVHViewer(self)
        self._noneViewer = BlackEmptyPlot()
        self._staticProfileviewer = ProfileViewer(viewController)

        self._staticImage3DViewer = Image3DViewer(viewController)
        self._staticImage2DViewer = Image2DViewer(viewController)

        ## dynamic stuff
        self._dynImage3DViewer = DynamicImage3DViewer(viewController)
        self._dynImage2DViewer = DynamicImage2DViewer(viewController)

        self._staticProfileviewer.hide()
        self._noneViewer.hide()
        self._dvhViewer.hide()
        self._dynImage3DViewer.hide()
        self._staticImage3DViewer.hide()

        self._addViewersToLayout()

        self._setDisplayType(self.DisplayTypes.DEFAULT)

        # Logical control of the DataViewer is set here. We might want to move this to dedicated controller class
        self._initializeControl()

    def _addViewersToLayout(self):
        self._mainLayout.addWidget(self._toolbar)
        self._mainLayout.addWidget(self._dynImage3DViewer)
        self._mainLayout.addWidget(self._staticImage3DViewer)
        self._mainLayout.addWidget(self._staticProfileviewer)
        self._mainLayout.addWidget(self._noneViewer)
        self._mainLayout.addWidget(self._dvhViewer)

    @property
    def cachedDynamicImageViewer(self) -> DynamicImage3DViewer:
        """
            The dynamic image viewer currently in cache (read-only)

            :type: DynamicImageViewer
        """
        return self._dynImage3DViewer

    @property
    def cachedStaticDVHViewer(self) -> DVHViewer:
        """
            The DVH viewer currently in cache
        """
        return self._dvhViewer

    @property
    def cachedStaticImage3DViewer(self) -> Image3DViewer:
        """
            The static image 3D viewer currently in cache (read-only)

            :type: Image3DViewer
        """
        return self._staticImage3DViewer

    @property
    def cachedStaticImage2DViewer(self) -> Image2DViewer:
        """
            The static image 2D viewer currently in cache (read-only)

            :type: Image2DViewer
        """
        return self._staticImage2DViewer

    @property
    def cachedStaticProfileViewer(self) -> ProfileViewer:
        """
        The profile viewer currently in cache (read-only)

        :type: ProfilePlot
        """
        return self._staticProfileviewer

    @property
    def currentViewer(self) -> Optional[Union[DVHViewer, ProfileViewer, Image3DViewer]]:
        """
        The viewer currently displayed (read-only)viewerTypes

        :type: Optional[Union[DVHViewer, ProfilePlot, ImageViewer]]
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

    @property
    def dropMode(self):
        return self._dropMode

    @dropMode.setter
    def dropMode(self, mode):
        if mode==self._dropMode:
            return
        self._dropMode = mode

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
        self._currentViewer = self._dynImage3DViewer
        self.dropEnabled = self._dropEnabled

        self._viewController.crossHairEnabledSignal.disconnect(self._staticImage3DViewer.setCrossHairEnabled)
        self._viewController.profileWidgetEnabledSignal.disconnect(self._staticImage3DViewer.setProfileWidgetEnabled)
        self._viewController.showContourSignal.disconnect(self._staticImage3DViewer._contourLayer.setNewContour)
        self._viewController.showContourSignal.disconnect(self._dvhViewer.appendROI)
        self._viewController.windowLevelEnabledSignal.disconnect(self._staticImage3DViewer.setWWLEnabled)

        self._viewController.crossHairEnabledSignal.connect(self._dynImage3DViewer.setCrossHairEnabled)
        self._viewController.profileWidgetEnabledSignal.connect(self._dynImage3DViewer.setProfileWidgetEnabled)
        self._viewController.showContourSignal.connect(self._dynImage3DViewer._contourLayer.setNewContour)
        self._viewController.windowLevelEnabledSignal.connect(self._dynImage3DViewer.setWWLEnabled)

    def _setCurrentViewerToStaticImageViewer(self):
        self._currentViewer = self._staticImage3DViewer
        self.dropEnabled = self._dropEnabled

        self._viewController.crossHairEnabledSignal.disconnect(self._dynImage3DViewer.setCrossHairEnabled)
        self._viewController.profileWidgetEnabledSignal.disconnect(self._dynImage3DViewer.setProfileWidgetEnabled)
        self._viewController.showContourSignal.disconnect(self._dynImage3DViewer._contourLayer.setNewContour)
        self._viewController.windowLevelEnabledSignal.disconnect(self._dynImage3DViewer.setWWLEnabled)

        self._viewController.crossHairEnabledSignal.connect(self._staticImage3DViewer.setCrossHairEnabled)
        self._viewController.profileWidgetEnabledSignal.connect(self._staticImage3DViewer.setProfileWidgetEnabled)
        self._viewController.showContourSignal.connect(self._staticImage3DViewer._contourLayer.setNewContour)
        self._viewController.showContourSignal.connect(self._dvhViewer.appendROI)
        self._viewController.windowLevelEnabledSignal.connect(self._staticImage3DViewer.setWWLEnabled)

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
            droppedIsPlan = e.mimeData().text() == DroppedObject.DropTypes.PLAN

            if droppedIsImage:
                e.accept()
                self.droppedImageSignal.emit(self._viewController.selectedImage)
                return
            elif droppedIsPlan:
                e.accept()
                self.droppedPlanSignal.emit(self._viewController.selectedImage)
                return
        e.ignore()



    ####################################################################################################################
    # This is the logical part of the viewer. Should we migrate this to a dedicated controller?
    def _initializeControl(self):
        self._imageViewerActions = ImageViewerActions(self._staticImage3DViewer)
        self._dvhViewerActions = DVHViewerActions(self._dvhViewer)

        self._imageViewerActions.addToToolbar(self._toolbar)
        self._dvhViewerActions.addToToolbar(self._toolbar)

        self.displayTypeChangedSignal.connect(self._handleDisplayTypeChange)

        self._viewController.independentViewsEnabledSignal.connect(self.enableDrop)
        self._viewController.mainImageChangedSignal.connect(self._setMainImageAnSwitchDisplaydMode)
        self._viewController.secondaryImageChangedSignal.connect(self._setSecondaryImage)
        self._viewController.planChangedSignal.connect(self._setPlan)
        self._viewController.dropModeSignal.connect(self._setDropMode)
        self._viewController.droppedDataSignal.connect(self._setDroppedData)

        self.enableDrop(self._viewController.independentViewsEnabled)

        self._handleDisplayTypeChange(self.displayType) # Initialize with current display type

    def _handleDisplayTypeChange(self, displayType):
        self._imageViewerActions.hide()

        if displayType==self.DisplayTypes.DISPLAY_IMAGE:
            self._imageViewerActions.setImageViewer(self._currentViewer)
            self._imageViewerActions.show()

    def enableDrop(self, enabled):
        self.dropEnabled = enabled

        if enabled:
            # It might seems weird to have a signal connected within the class but it is if someday we want to move the logical part out of this class.
            # See also comment on dropEnabled : Should we implement drop directly in ImageViewer?
            self.droppedImageSignal.connect(self._setDroppedData)
            self.droppedPlanSignal.connect(self._setPlan)
        else:
            self.droppedImageSignal.disconnect(self._setDroppedData)
            self.droppedPlanSignal.disconnect(self._setPlan)

    def _setDropMode(self, dropMode):
        self.dropMode = dropMode

    def _setDroppedData(self, data):
        if isinstance(data, RTPlan):
            self._setPlan(data)
            return

        if self._dropMode==self.DropModes.PRIMARY:
            self._setMainImageAnSwitchDisplaydMode(data)
        if self._dropMode==self.DropModes.SECONDARY:
            self._setSecondaryImage(data)
        if self._dropMode==self.DropModes.AUTO:
            if isinstance(data, DoseImage):
                self._setSecondaryImage(data)
            else:
                self._setMainImageAnSwitchDisplaydMode(data)

    def _setMainImageAnSwitchDisplaydMode(self, image):
        """
            Switch display mode according to image type and then display image
        """
        if isinstance(image, Image3D) or isinstance(image, Dynamic3DModel) or isinstance(image, Image2D):
            self.displayMode = self.DisplayModes.STATIC
        elif isinstance(image, Dynamic3DSequence) or isinstance(image, Dynamic2DSequence):
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
            self.cachedStaticImage3DViewer.primaryImage = image
        elif isinstance(image, Image2D):
            self.cachedStaticImage2DViewer.primaryImage = image
        elif isinstance(image, Dynamic3DSequence):
            self.cachedDynamicImage3DViewer.primaryImage = image
        elif isinstance(image, Dynamic2DSequence):
            self.cachedDynamicImage2DViewer.primaryImage = image
        elif isinstance(image, Dynamic3DModel):
            self.cachedStaticImage3DViewer.primaryImage = image.midp
        elif image is None:
            pass
        else:
            raise ValueError('Image type not supported')

        if not image is None and not image.patient is None:
            image.patient.imageRemovedSignal.connect(self._removeImageFromViewers)

    def _setSecondaryImage(self, image: Optional[Image3D]):
        """
            Display the image (in static mode)
            Does not affect viewer visibility nor viewer type.
        """

        if image is None:
            oldImage = self.cachedStaticImage3DViewer.secondaryImage
            if oldImage is None:
                return
        elif not (image.patient is None):
            image.patient.imageRemovedSignal.connect(self._removeImageFromViewers)

        self.cachedStaticImage3DViewer.secondaryImage = image
        self._setDVHDose(image)

    def _setPlan(self, plan:Optional[RTPlan]):
        self.cachedStaticImage3DViewer.rtPlan = plan

    def _setDVHDose(self, image:Optional[DoseImage]):
        if image is None:
            self.cachedStaticDVHViewer.clear()
        else:
            self.cachedStaticDVHViewer.dose = image

    def _removeImageFromViewers(self, image: Image3D):
        """
        Remove image from all cached viewers.
        """
        ""
        if self.cachedStaticImage3DViewer.primaryImage == image:
            self._setMainImage(None)

        if self.cachedDynamicImageViewer.secondaryImage == image:
            self._setSecondaryImage(None)

        if self.cachedStaticDVHViewer.dose == image:
            self._setDVHDose(None)
