
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import QTimer

from Core.Data.dynamic2DSequence import Dynamic2DSequence
from Core.Data.dynamic3DSequence import Dynamic3DSequence
from GUI.Viewer.gridFourElements import GridFourElements
from GUI.Viewer.viewerToolbar import ViewerToolbar


class ViewerPanel(QWidget):

    LAYOUT_FOUR = 'LAYOUT_FOUR'

    MODE_DYNAMIC = 'DYNAMIC'
    MODE_STATIC = 'STATIC'

    def __init__(self, viewController, layoutType='LAYOUT_FOUR'):
        QWidget.__init__(self)

        self._dropEnabled = False
        self._layout = QVBoxLayout(self)
        self._layoutType = None
        self._viewerGrid = None

        self._viewToolbar = ViewerToolbar(viewController)
        # self._viewToolbar.playPauseSignal.connect(self.playOrPause)
        # self._viewToolbar.fasterSignal.connect(self.playFaster)
        # self._viewToolbar.slowerSignal.connect(self.playSlower)
        # self._viewToolbar.refreshRateChangedSignal.connect(self.setRefreshRate)
        self._layout.addWidget(self._viewToolbar)

        self._viewController = viewController

        self._setToolbar(self._viewToolbar)
        self._setLayout(layoutType)
        if self._layoutType == self.LAYOUT_FOUR:
            self._viewController.numberOfViewerPanelElement = 4

        self._viewController.independentViewsEnabledSignal.connect(lambda enabled: self._setDropEnabled(not enabled))
        self._setDropEnabled(not self._viewController.independentViewsEnabled)

        # dynamic parameters
        # self.isDynamic = False
        # for dataViewer in self._viewerGrid._gridElements:
        #     dataViewer._sliceViewer.dynamicModeChangedSignal.connect(self.getViewersDynamicStatus)
        # self.viewersDynamicStatusList = []
        # self.getViewersDynamicStatus()
        #
        # self.currentSpeedCoef = 1
        # self.refreshRateInFramePerSec = 24
        # self.refreshRateInMS = int(round(1000 / self.refreshRateInFramePerSec))
        # self.timerStepNumber = 0
        # self.time = 0
        # self.timer = QTimer()
        # self.timer.timeout.connect(self.checkIfUpdate)


    def _dropEvent(self, e):
        if e.mimeData().hasText():
            if (e.mimeData().text() == 'image'):
                e.accept()
                self._viewController.mainImage = self._viewController.selectedImage
                return
        e.ignore()

    def _setDropEnabled(self, enabled):
        self._dropEnabled = enabled

        if enabled:
            self._viewerGrid.setAcceptDrops(True)
            self._viewerGrid.dragEnterEvent = lambda event: event.accept()
            self._viewerGrid.dropEvent = lambda event: self._dropEvent(event)
        else:
            self._viewerGrid.setAcceptDrops(False)

    def _setLayout(self, layoutType):
        self._layoutType = layoutType

        if not self._viewerGrid is None:
            self._layoutType.removeWidget(self._viewerGrid)

        if self._layoutType == self.LAYOUT_FOUR:
            self._viewerGrid = GridFourElements(self._viewController)

        if self._viewerGrid==None:
            return

        self._layout.addWidget(self._viewerGrid)

        if self._layoutType == self.LAYOUT_FOUR:
            self._viewerGrid.setEqualSize()

    def _setToolbar(self, toolbar):
        #TODO: remove toolbar if already existing add add newToolabr above
        self._toolbar = toolbar
        self._layout.addWidget(self._toolbar)


