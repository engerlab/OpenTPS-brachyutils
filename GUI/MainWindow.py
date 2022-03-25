
import os
from PyQt5.QtWidgets import QMainWindow, QHBoxLayout, QWidget
from PyQt5.QtGui import QIcon

from Extensions.FLASH.GUI.flashWindow import FlashWindow
from GUI.Panels.mainToolbar import MainToolbar
from GUI.Viewer.viewerPanel import ViewerPanel
from GUI.statusBar import StatusBar


class MainWindow(QMainWindow):
    def __init__(self, viewControler):
        QMainWindow.__init__(self)

        self.fWindow = FlashWindow(viewControler, self)
        self.fWindow = self.fWindow.show()

        self.setWindowTitle('OpenTPS')
        self.setWindowIcon(QIcon('GUI' + os.path.sep + 'res' + os.path.sep + 'icons' + os.path.sep + 'OpenTPS_icon.png'))
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

        # create and add the viewer panel
        self.viewerPanel = ViewerPanel(self._viewControler)
        self.mainLayout.addWidget(self.viewerPanel)

        self.statusBar = StatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.show()

    def setLateralToolbar(self, toolbar):
        self.mainLayout.addWidget(toolbar)
        toolbar.setFixedWidth(self.toolbox_width)

    def setMainPanel(self, mainPanel):
        self.mainLayout.addWidget(mainPanel)
