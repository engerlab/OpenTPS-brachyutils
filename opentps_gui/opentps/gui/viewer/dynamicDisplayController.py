from PyQt5.QtCore import QTimer


class DynamicDisplayController():

    # MODE_DYNAMIC = 'DYNAMIC'
    # MODE_STATIC = 'STATIC'

    def __init__(self, viewController):

        self._viewController = viewController
        self._viewerPanelToolBar = None

        self.isDynamic = False
        self.dynamicViewerUnitList = []

        self.currentSpeedCoef = 1
        self.refreshRateInFramePerSec = 24
        self.refreshRateInMS = int(round(1000 / self.refreshRateInFramePerSec))
        self.timerStepNumber = 0
        self.time = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.checkIfUpdate)


    def setToolBar(self, viewerPanelToolBar):
        self._viewerPanelToolBar = viewerPanelToolBar
        self.connectToolBar()


    def connectToolBar(self):
        self._viewerPanelToolBar.playPauseSignal.connect(self.playOrPause)
        self._viewerPanelToolBar.fasterSignal.connect(self.playFaster)
        self._viewerPanelToolBar.slowerSignal.connect(self.playSlower)
        self._viewerPanelToolBar.refreshRateChangedSignal.connect(self.setRefreshRate)


    def addDynamicViewer(self, viewer):
        # print('in displayController addDynViewer', type(viewer))
        if viewer not in self.dynamicViewerUnitList:
            self.dynamicViewerUnitList.append(viewer)
        else:
            return
        if self.isDynamic == False:
            self.switchDynamicMode()


    def removeDynamicViewer(self, viewer):
        # print('in displayController removeDynamicViewer', type(viewer))
        if viewer in self.dynamicViewerUnitList:
            viewer.resetDynamicParameters()
            self.dynamicViewerUnitList.remove(viewer)
        else:
            return
        if not self.dynamicViewerUnitList:
            self.switchDynamicMode()


    def switchDynamicMode(self):
        """
        This function switches the mode from dynamic to static and inversely. It starts or stops the timer accordingly.
        """
        self.isDynamic = not self.isDynamic
        if self.isDynamic == True:
            print('Switch to dynamic mode')
            self.time = 0
            self.timer.start(self.refreshRateInMS)
            self._viewerPanelToolBar.addDynamicButtons()

        elif self.isDynamic == False:
            self.timer.stop()
            self._viewerPanelToolBar.removeDynamicButtons()
            print('Switch to static mode')


    def checkIfUpdate(self):
        """
        This function checks if an update must occur at this time.
        It only works for dynamic3DSequences for now.
        """
        self.time += self.refreshRateInMS * self.currentSpeedCoef
        for dynamicViewerUnit in self.dynamicViewerUnitList:

            # print(type(dynamicViewerUnit))

            dyn3DSeqForViewer = dynamicViewerUnit.primaryImage
            timingsList = dyn3DSeqForViewer.data.timingsList
            loopShift = timingsList[-1] * dynamicViewerUnit.loopStepNumber
            curIndex = dynamicViewerUnit.curPrimaryImgIdx

            # print('in dynamicDisplayController, checkIfUpdate', timingsList)

            if self.time - loopShift > timingsList[curIndex + 1]:
                newIndex = self.lookForClosestIndex(self.time - loopShift, curIndex, timingsList, dynamicViewerUnit)
                dynamicViewerUnit.nextImage(newIndex)


    def lookForClosestIndex(self, time, curIndex, timingsList, dataViewer):
        """
        This function return the index of the last position in timingList lower than time,
        meaning the time has passed this event and an update must occur.
        If the curIndex has reached the end of the timingsList, it returns 0
        """
        while timingsList[curIndex + 1] < time:
            curIndex += 1
            if curIndex == len(timingsList) - 1:  # has reach the end
                dataViewer.loopStepNumber += 1
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