
import os

from PyQt5.QtWidgets import QMainWindow, QHBoxLayout, QWidget, QToolBox
from PyQt5.QtGui import QIcon

from GUI.Panels.patientDataPanel import PatientDataPanel
from GUI.Panels.viewerPanel.viewerPanel import ViewerPanel
from GUI.ViewControllers.patientDataPanelController import PatientDataPanelController
from GUI.ViewControllers.viewerPanelControllers.viewerPanelController import ViewerPanelController


class MainWindow(QMainWindow):
    def __init__(self, viewController):
        QMainWindow.__init__(self)

        self.toolbox_width = 270

        self._viewController = viewController

        self.setWindowTitle('OpenTPS')
        self.setWindowIcon(QIcon('GUI' + os.path.sep + 'res' + os.path.sep + 'icons' + os.path.sep + 'OpenTPS_icon.png'))
        self.resize(1400, 920)

        mainLayout = QHBoxLayout()

        centralWidget = QWidget()
        centralWidget.setLayout(mainLayout)
        self.setCentralWidget(centralWidget)

        mainToolbox = QToolBox()
        mainToolbox.setStyleSheet("QToolBox::tab {font: bold; color: #000000; font-size: 16px;}")
        mainToolbox.setFixedWidth(self.toolbox_width)

        mainLayout.addWidget(mainToolbox)


        # initialize the 1st toolbox panel (patient data)
        patientDataPanelController = PatientDataPanelController(self._viewController)
        patientDataPanel = PatientDataPanel(patientDataPanelController)
        mainToolbox.addItem(patientDataPanel, 'Patient data')

        viewerPanel = ViewerPanel(ViewerPanelController(self._viewController))
        mainLayout.addWidget(viewerPanel)

