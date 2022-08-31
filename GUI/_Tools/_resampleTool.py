
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QMainWindow, QVBoxLayout, QPushButton, QFrame
from GUI.Panels.PatientDataPanel.patientDataSelection import PatientDataSelection



class ResampleWidget(QMainWindow):
    def __init__(self, viewController, parent=None):
        super().__init__(parent)

        self._viewController = viewController

        self.setWindowTitle('Crop tool')
        self.resize(800, 600)

        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        self._mainLayout = QHBoxLayout()
        centralWidget.setLayout(self._mainLayout)

        self._resampleOptions = ResampleOptions(self._viewController)

        self._cropDataButton = QPushButton('Resample all selected data')
        self._cropDataButton.clicked.connect(self._resampleData)

        self._dataSelection = PatientDataSelection((self._viewController))

        self._menuFrame = QFrame(self)
        self._menuFrame.setFixedWidth(200)
        self._menuLayout = QVBoxLayout(self._menuFrame)
        self._menuFrame.setLayout(self._menuLayout)

        self._mainLayout.addWidget(self._menuFrame)
        self._menuLayout.addWidget(self._dataSelection)
        self._menuLayout.addWidget(self._cropDataButton)
        self._mainLayout.addWidget(self._viewers)

    def _resampleData(self):
        pass

class ResampleOptions:
    def __init__(self, viewController):
        self._viewController = viewController
