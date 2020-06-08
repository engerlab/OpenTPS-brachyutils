from PyQt5.QtWidgets import *

class AddArc_dialog(QDialog):

  def __init__(self, ArcName):
    
    # initialize the window
    QDialog.__init__(self)
    self.setWindowTitle('Add arc')
    self.resize(300, 200)
    self.main_layout = QVBoxLayout()
    self.setLayout(self.main_layout)
    
    # form
    self.InputLayout = QGridLayout()
    self.main_layout.addLayout(self.InputLayout)
    
    self.InputLayout.addWidget(QLabel('<b>Name:</b>'), 0, 0)
    self.ArcName = QLineEdit(ArcName)
    self.InputLayout.addWidget(self.ArcName, 0, 1)
    
    self.InputLayout.addWidget(QLabel('<b>Start gantry angle:</b>'), 1, 0)
    self.StartGantryAngle = QDoubleSpinBox()
    self.StartGantryAngle.setRange(-360.0, 360.0)
    self.StartGantryAngle.setSingleStep(5.0)
    self.StartGantryAngle.setValue(0.0)
    self.StartGantryAngle.setSuffix("°")
    self.InputLayout.addWidget(self.StartGantryAngle, 1, 1)
    
    self.InputLayout.addWidget(QLabel('<b>Stop gantry angle:</b>'), 2, 0)
    self.StopGantryAngle = QDoubleSpinBox()
    self.StopGantryAngle.setRange(-360.0, 360.0)
    self.StopGantryAngle.setSingleStep(5.0)
    self.StopGantryAngle.setValue(360.0)
    self.StopGantryAngle.setSuffix("°")
    self.InputLayout.addWidget(self.StopGantryAngle, 2, 1)
    
    self.InputLayout.addWidget(QLabel('<b>Control point step:</b>'), 3, 0)
    self.AngularStep = QDoubleSpinBox()
    self.AngularStep.setRange(0.1, 360.0)
    self.AngularStep.setSingleStep(0.5)
    self.AngularStep.setValue(2.0)
    self.AngularStep.setSuffix("°")
    self.InputLayout.addWidget(self.AngularStep, 3, 1)
    
    self.InputLayout.addWidget(QLabel('<b>Couch angle:</b>'), 4, 0)
    self.CouchAngle = QDoubleSpinBox()
    self.CouchAngle.setRange(-360.0, 360.0)
    self.CouchAngle.setSingleStep(5.0)
    self.CouchAngle.setValue(0.0)
    self.CouchAngle.setSuffix("°")
    self.InputLayout.addWidget(self.CouchAngle, 4, 1)
    
    # buttons
    self.ButtonLayout = QHBoxLayout()
    self.main_layout.addLayout(self.ButtonLayout)
    self.CancelButton = QPushButton('Cancel')
    self.ButtonLayout.addWidget(self.CancelButton)
    self.CancelButton.clicked.connect(self.reject) 
    self.AddButton = QPushButton('Add')
    self.AddButton.clicked.connect(self.accept) 
    self.ButtonLayout.addWidget(self.AddButton)
    
    
