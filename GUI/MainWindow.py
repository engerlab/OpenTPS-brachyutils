from PyQt5.QtWidgets import QMainWindow, QHBoxLayout, QWidget, QToolBox

from GUI.Panels.patientDataPanel import PatientDataPanel
from GUI.ViewControllers.gridFourElementController import GridFourElementController
from GUI.ViewControllers.patientDataPanelController import PatientDataPanelController
from GUI.Viewers.gridFourElements import GridFourElements


class MainWindow(QMainWindow):
    def __init__(self, viewController):
        QMainWindow.__init__(self)

        self.toolbox_width = 270

        self._viewController = viewController

        self.setWindowTitle('OpenTPS')
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

        mainGrid = GridFourElements(GridFourElementController(self._viewController))
        mainLayout.addWidget(mainGrid)

