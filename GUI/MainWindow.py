from PyQt5.QtWidgets import QMainWindow, QHBoxLayout, QWidget, QToolBox

from GUI.Panels.patientDataPanel import PatientDataPanel


class MainWindow(QMainWindow):
    def __init__(self, viewController):
        QMainWindow.__init__(self)

        self.toolbox_width = 270

        self._viewController = viewController

        self.setWindowTitle('OpenTPS')
        self.resize(1400, 920)
        self.main_layout = QHBoxLayout()
        self.central_Widget = QWidget()
        self.central_Widget.setLayout(self.main_layout)
        self.setCentralWidget(self.central_Widget)

        self.toolbox_main = QToolBox()
        self.toolbox_main.setStyleSheet("QToolBox::tab {font: bold; color: #000000; font-size: 16px;}")
        self.main_layout.addWidget(self.toolbox_main)
        self.toolbox_main.setFixedWidth(self.toolbox_width)

        # initialize the 1st toolbox panel (patient data)
        self.patientDataPanel = PatientDataPanel(self._viewController)
        self.toolbox_main.addItem(self.patientDataPanel, 'Patient data')
