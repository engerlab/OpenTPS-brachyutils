
import os

from PyQt5.QtWidgets import QMainWindow, QHBoxLayout, QWidget, QToolBox
from PyQt5.QtGui import QIcon

class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)

        self.toolbox_width = 270

        self.setWindowTitle('OpenTPS')
        self.setWindowIcon(QIcon('GUI' + os.path.sep + 'res' + os.path.sep + 'icons' + os.path.sep + 'OpenTPS_icon.png'))
        self.resize(1400, 920)

        self.mainLayout = QHBoxLayout()

        centralWidget = QWidget()
        centralWidget.setLayout(self.mainLayout)
        self.setCentralWidget(centralWidget)

    def setLateralToolbar(self, toolbar):
        self.mainLayout.addWidget(toolbar)
        toolbar.setFixedWidth(self.toolbox_width)

    def setMainPanel(self, mainPanel):
        self.mainLayout.addWidget(mainPanel)
