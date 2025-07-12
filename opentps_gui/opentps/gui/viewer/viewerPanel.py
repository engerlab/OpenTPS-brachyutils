from enum import Enum

from PyQt5.QtWidgets import QWidget, QVBoxLayout

from opentps.gui.viewer.dataViewer import DroppedObject
from opentps.gui.viewer.gridFourElements import GridFourElements
from opentps.gui.viewer.viewerToolbar import ViewerToolbar

class ViewerPanel(QWidget):
    class LayoutTypes(Enum):
        DEFAULT = 'GRID_2BY2'
        GRID_2BY2 = 'GRID_2BY2'

    def __init__(self, viewController, parent):
        super().__init__(parent)

        self._layoutType = None
        self._viewerGrid = None

        self._viewController = viewController

        self._dropEnabled = False
        self._onDropEvent = None

        self._layout = QVBoxLayout(self)

        self._viewToolbar = ViewerToolbar(viewController, parent=self)
        self._layout.addWidget(self._viewToolbar)

        self._setLayoutType(self.LayoutTypes.DEFAULT)

        self._iniializeControl()

    def closeEvent(self, QCloseEvent):
        for element in self._viewerGrid.gridElements:
            element.close()
        super().closeEvent(QCloseEvent)

    def _dropEvent(self, e):
        if e.mimeData().hasText():
            if (e.mimeData().text() == DroppedObject.DropTypes.IMAGE):
                e.accept()
                if not self._onDropEvent is None:
                    self._onDropEvent(self._viewController.selectedImage)
                return
        e.ignore()

    @property
    def onDropEvent(self):
        """
            Function to execute on drop event
        """
        return self._onDropEvent

    @onDropEvent.setter
    def onDropEvent(self, func):
        self._onDropEvent = func

    @property
    def dropEnabled(self) -> bool:
        """
            Drag and drop enabled

            :type: bool
        """
        return self._dropEnabled

    @dropEnabled.setter
    def dropEnabled(self, enabled: bool):
        self._setDropEnabled(enabled)

    def _setDropEnabled(self, enabled: bool):
        self._dropEnabled = enabled

        if enabled:
            self._viewerGrid.setAcceptDrops(True)
            self._viewerGrid.dragEnterEvent = lambda event: event.accept()
            self._viewerGrid.dropEvent = lambda event: self._dropEvent(event)
        else:
            self._viewerGrid.setAcceptDrops(False)

    @property
    def layoutType(self)->LayoutTypes:
        """
            Layout type defined in ViewerPanel.LayoutTypes
        """
        return self._layoutType

    @layoutType.setter
    def layoutType(self, layoutType:LayoutTypes):
        self._setLayoutType(layoutType)

    def _setLayoutType(self, layoutType:LayoutTypes):
        self._layoutType = layoutType

        if not self._viewerGrid is None:
            self._layoutType.removeWidget(self._viewerGrid)

        if self._layoutType == self.LayoutTypes.GRID_2BY2:
            self._viewerGrid = GridFourElements(self._viewController, self)
            self._viewerGrid.setEqualSize()
        elif self._viewerGrid==None:
            return

        self._layout.addWidget(self._viewerGrid)


####################################################################################################################
    # This is the logical part of the viewer. Should we migrate this to a dedicated controller?
    def _iniializeControl(self):
        self._viewController.dynamicDisplayController.setToolBar(self._viewToolbar)
        self._viewController.independentViewsEnabledSignal.connect(lambda enabled: self._setDropEnabled(not enabled))
        self.onDropEvent = self._setViewControllerMainImage # It might seems weird to pass a function within the class but it is if someday we want to move the logical part out of this class.
        self._setDropEnabled(not self._viewController.independentViewsEnabled)

    def _setViewControllerMainImage(self, patientData):
        self._viewController.droppedImage = patientData
