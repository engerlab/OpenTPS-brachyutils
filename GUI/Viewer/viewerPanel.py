
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
        self._viewToolbar.playPauseSignal.connect(self.playOrPause)
        self._viewToolbar.fasterSignal.connect(self.playFaster)
        self._viewToolbar.slowerSignal.connect(self.playSlower)
        self._viewToolbar.refreshRateChangedSignal.connect(self.setRefreshRate)
        self._layout.addWidget(self._viewToolbar)

        self._viewController = viewController

        self._setToolbar(self._viewToolbar)
        self._setLayout(layoutType)
        if self._layoutType == self.LAYOUT_FOUR:
            self._viewController.numberOfViewerPanelElement = 4

        self._viewController.independentViewsEnabledSignal.connect(lambda enabled: self._setDropEnabled(not enabled))
        self._setDropEnabled(not self._viewController.independentViewsEnabled)

        # dynamic parameters
        self.isDynamic = False
        for dataViewer in self._viewerGrid._gridElements:
            dataViewer._sliceViewer.dynamicModeChangedSignal.connect(self.getViewersDynamicStatus)
        self.viewersDynamicStatusList = []
        self.getViewersDynamicStatus()

        self.currentSpeedCoef = 1
        self.refreshRateInFramePerSec = 24
        self.refreshRateInMS = int(round(1000 / self.refreshRateInFramePerSec))
        self.timerStepNumber = 0
        self.time = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.checkIfUpdate)


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


    def getViewersDynamicStatus(self):
        """
        This function check the list self._viewerGrid._gridElements to get for each dataViewer its _sliceViewer viewerMode.
        If one becomes dynamic, it switches the viewerPanel mode to dynamic.
        If they all become static, it switches the viewerPanel mode to static.
        """
        self.viewersDynamicStatusList = [dataViewer._sliceViewer.viewerMode for dataViewer in self._viewerGrid._gridElements]
        # print('Viewers dynamic status', self.viewersDynamicStatusList)
        if (self.MODE_DYNAMIC in self.viewersDynamicStatusList) and self.isDynamic == False:
            self.switchMode()
        elif not(self.MODE_DYNAMIC in self.viewersDynamicStatusList) and self.isDynamic == True:
            self.switchMode()


    def switchMode(self):
        """
        This function switches the mode from dynamic to static and inversely. It starts or stops the timer accordingly.
        """
        self.isDynamic = not self.isDynamic
        if self.isDynamic == True:
            print('Switch viewerPanel to dynamic mode')
            for dataViewer in self._viewerGrid._gridElements:
                dataViewer._sliceViewer.curPrimaryImgIdx = 0
                dataViewer._sliceViewer.loopStepNumber = 0
            self.time = 0
            self.timer.start(self.refreshRateInMS)
            self._viewToolbar.addDynamicButtons()

        elif self.isDynamic == False:
            self.timer.stop()
            self._viewToolbar.removeDynamicButtons()
            print('Switch viewerPanel to static mode')


    def checkIfUpdate(self):
        """
        This function checks if an update must occur at this time.
        It only works for dynamic3DSequences for now.
        """
        self.time += self.refreshRateInMS * self.currentSpeedCoef

        for dataViewerIndex, dataViewer in enumerate(self._viewerGrid._gridElements):

            if self.viewersDynamicStatusList[dataViewerIndex] == self.MODE_DYNAMIC:
                dyn3DSeqForViewer = dataViewer._sliceViewer.primaryImage
                timingsList = dyn3DSeqForViewer.dyn3DSeq.timingsList
                loopShift = timingsList[-1] * dataViewer._sliceViewer.loopStepNumber
                curIndex = dataViewer._sliceViewer.curPrimaryImgIdx

                if self.time-loopShift > timingsList[curIndex+1]:
                    newIndex = self.lookForClosestIndex(self.time-loopShift, curIndex, timingsList, dataViewer)
                    dataViewer._sliceViewer.nextImage(newIndex)


    def lookForClosestIndex(self, time, curIndex, timingsList, dataViewer):
        """
        This function return the index of the last position in timingList lower than time,
        meaning the time has passed this event and an update must occur.
        If the curIndex has reached the end of the timingsList, it returns 0
        """
        while timingsList[curIndex + 1] < time:
            curIndex += 1
            if curIndex == len(timingsList) - 1:    # has reach the end
                dataViewer._sliceViewer.loopStepNumber += 1
                return 0

        return curIndex


    def playOrPause(self, playPauseBool):
        if playPauseBool:
            self.currentSpeedCoef = 1
        else:
            self.currentSpeedCoef = 0


    def playFaster(self):
        self.currentSpeedCoef *= 2


    def playSlower(self):
        self.currentSpeedCoef /= 2


    def setRefreshRate(self, refreshRate):
        self.refreshRateInFramePerSec = refreshRate
        if self.refreshRateInFramePerSec < 0.2:
            self.refreshRateInFramePerSec = 0.2
        if self.refreshRateInFramePerSec > 200:
            self.refreshRateInFramePerSec = 200
        self.refreshRateInMS = int(round(1000 / self.refreshRateInFramePerSec))
        self.timer.stop()
        self.timer.start(self.refreshRateInMS)
        print('Refresh Rate Set to', self.refreshRateInFramePerSec, 'frames/sec --> Check every', self.refreshRateInMS, 'ms')