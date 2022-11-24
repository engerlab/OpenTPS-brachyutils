from PyQt5.QtWidgets import *


class BeamDialog(QDialog):
    def __init__(self, BeamName, RangeShifterList=[]):
        RangeShifterList = ["None"] + RangeShifterList

        # initialize the window
        QDialog.__init__(self)
        self.setWindowTitle('Add beam')
        self.resize(300, 150)
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        # form
        self.InputLayout = QGridLayout()
        self.main_layout.addLayout(self.InputLayout)

        self.InputLayout.addWidget(QLabel('<b>Name:</b>'), 0, 0)
        self.BeamName = QLineEdit(BeamName)
        self.InputLayout.addWidget(self.BeamName, 0, 1)

        self.InputLayout.addWidget(QLabel('<b>Gantry angle:</b>'), 1, 0)
        self.GantryAngle = QDoubleSpinBox()
        self.GantryAngle.setRange(0.0, 360.0)
        self.GantryAngle.setSingleStep(5.0)
        self.GantryAngle.setValue(0.0)
        self.GantryAngle.setSuffix("°")
        self.InputLayout.addWidget(self.GantryAngle, 1, 1)

        self.InputLayout.addWidget(QLabel('<b>Couch angle:</b>'), 2, 0)
        self.CouchAngle = QDoubleSpinBox()
        self.CouchAngle.setRange(0.0, 360.0)
        self.CouchAngle.setSingleStep(5.0)
        self.CouchAngle.setValue(0.0)
        self.CouchAngle.setSuffix("°")
        self.InputLayout.addWidget(self.CouchAngle, 2, 1)

        self.InputLayout.addWidget(QLabel('<b>Range shifter:</b>'), 3, 0)
        self.RangeShifter = QComboBox()
        self.RangeShifter.addItems(RangeShifterList)
        self.InputLayout.addWidget(self.RangeShifter, 3, 1)

        # buttons
        self.ButtonLayout = QHBoxLayout()
        self.main_layout.addLayout(self.ButtonLayout)
        self.CancelButton = QPushButton('Cancel')
        self.ButtonLayout.addWidget(self.CancelButton)
        self.CancelButton.clicked.connect(self.reject)
        self.AddButton = QPushButton('Add')
        self.AddButton.clicked.connect(self.accept)
        self.ButtonLayout.addWidget(self.AddButton)
