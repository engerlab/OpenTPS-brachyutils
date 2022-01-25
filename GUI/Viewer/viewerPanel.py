
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import QTimer

from GUI.Viewer.gridFourElements import GridFourElements
from GUI.Viewer.viewerToolbar import ViewerToolbar


class ViewerPanel(QWidget):
    LAYOUT_FOUR = 'LAYOUT_FOUR'

    def __init__(self, viewController, layoutType='LAYOUT_FOUR'):
        QWidget.__init__(self)

        self._dropEnabled = False
        self._layout = QVBoxLayout(self)
        self._layoutType = None
        self._viewerGrid = None
        self._viewToolbar = ViewerToolbar(viewController)
        self._layout.addWidget(self._viewToolbar)
        self._viewController = viewController

        self._setToolbar(self._viewToolbar)
        self._setLayout(layoutType)
        if self._layoutType == self.LAYOUT_FOUR:
            self._viewController.numberOfViewerPanelElement = 4

        self._viewController.independentViewsEnabledSignal.connect(lambda enabled: self._setDropEnabled(not enabled))
        self._setDropEnabled(not self._viewController.independentViewsEnabled)
        # self._viewController.dynamicOrStaticModeChangedSignal.connect(self.switchMode)

        self.mode = 'static'

        # dynamic parameters
        self.speedFactor = 1
        self.refreshRate = 60
        self.timerStepNumber = 0
        self.time = 0
        self.timer = QTimer()


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


    def isThereADynViewer(self):

        print('!!!!!!!!!!!!!!!!!! i stopped here yesterday')
        for viewer in self._viewerGrid._gridElements:
            viewer.currentMode
        ## TODO : check on each viewer if its data is dynamic or static
        return False


    def switchMode(self, data):

        if (data.getType() == 'Dynamic3DSequence' or data.getType() == 'Dynamic2DSequence') and self.mode == 'static':
            # switch to dynamic
            self.mode = 'dynamic'
            print('in if')

        elif (data.getType() == 'Dynamic3DSequence' or data.getType() == 'Dynamic2DSequence') and self.mode == 'dynamic':
            # stays dynamic
            self.mode = 'dynamic'

        elif not (isinstance(data, Dynamic3DSequence) or isinstance(data, Dynamic2DSequence)) and self.mode == 'dynamic':

            print('must check if all the viewers are static')
            # must check if all the viewers are static to pass or not to static mode
            self.mode = 'dynamic'

        else:
            self.mode == 'static'
            # switch to static

            self.mode = 'static'

        if self.mode == 'dynamic':
            self.timer.timeout.connect(self.checkIfUpdate)
            self.timer.start(self.refreshRate)


    def checkIfUpdate(self):
        print('coucou')
