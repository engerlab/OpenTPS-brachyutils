
import os
from PyQt5.QtWidgets import QMainWindow, QHBoxLayout, QWidget
from PyQt5.QtGui import QIcon

from opentps.gui.panels.mainToolbar import MainToolbar
from opentps.gui.viewer.viewerPanel import ViewerPanel
from opentps.gui.programSettingEditor import ProgramSettingEditor
from opentps.gui.statusBar import StatusBar
from opentps.core.utils.programSettings import ProgramSettings
import opentps.gui.res.icons as IconModule

class MainWindow(QMainWindow):
    def __init__(self, viewControler):
        QMainWindow.__init__(self)

        self.setWindowTitle('OpenTPS')
        self.setWindowIcon(QIcon(IconModule.__path__[0] + os.path.sep + 'OpenTPS_icon.png'))
        self.resize(1400, 920)

        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        self.mainLayout = QHBoxLayout()  ## not sure the "self" is necessary for mainLayout, it shoudnt be called outside this constructor
        centralWidget.setLayout(self.mainLayout)

        self._viewControler = viewControler

        # create and add the tool panel on the left
        self.toolbox_width = 270
        self.mainToolbar = MainToolbar(self._viewControler)
        self.mainToolbar.setFixedWidth(self.toolbox_width)
        self.mainLayout.addWidget(self.mainToolbar)

        ProgramSettingEditor.setProgramSettings(ProgramSettings())
        ProgramSettingEditor.setMainToolbar(self.mainToolbar)

        # create and add the viewer panel
        self.viewerPanel = ViewerPanel(self._viewControler, self)
        self.mainLayout.addWidget(self.viewerPanel)

        self.statusBar = StatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.show()

    @property
    def viewController(self):
        return self._viewControler

    def closeEvent(self, QCloseEvent):
        self.viewerPanel.close()
        super().closeEvent(QCloseEvent)


    def setLateralToolbar(self, toolbar):
        self.mainLayout.addWidget(toolbar)
        toolbar.setFixedWidth(self.toolbox_width)

    def setMainPanel(self, mainPanel):
        self.mainLayout.addWidget(mainPanel)
