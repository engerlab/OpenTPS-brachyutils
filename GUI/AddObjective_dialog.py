from PyQt5.QtWidgets import *

class AddObjective_dialog(QDialog):

  def __init__(self, ContourList, RobustOpti=False):
    
    # initialize the window
    QDialog.__init__(self)
    self.setWindowTitle('Add objective')
    self.resize(300, 150)
    self.main_layout = QVBoxLayout()
    self.setLayout(self.main_layout)
    
    # contour
    self.main_layout.addWidget(QLabel('<b>Contour:</b>'))
    self.Contour = QComboBox()
    self.Contour.addItems(ContourList)
    self.Contour.setMaximumWidth(300-18)
    self.main_layout.addWidget(self.Contour)
    self.main_layout.addSpacing(15)
    
    # objective
    self.main_layout.addWidget(QLabel('<b>Objective:</b>'))
    self.ObjectiveLayout = QHBoxLayout()
    self.Metric = QComboBox()
    self.Metric.addItems(["Dmin", "Dmax", "Dmean"])
    self.ObjectiveLayout.addWidget(self.Metric)
    self.Condition = QComboBox()
    self.Condition.addItems([">", "<"])
    self.ObjectiveLayout.addWidget(self.Condition)
    self.LimitValue = QDoubleSpinBox()
    self.LimitValue.setRange(0.0, 200.0)
    self.LimitValue.setSingleStep(1.0)
    self.LimitValue.setValue(0.0)
    self.LimitValue.setSuffix(" Gy")
    self.ObjectiveLayout.addWidget(self.LimitValue)
    self.main_layout.addLayout(self.ObjectiveLayout)
    self.main_layout.addSpacing(15)
    
    # weight
    self.WeightLayout = QHBoxLayout()
    self.WeightLayout.addWidget(QLabel('<b>Weight:</b>'))
    self.Weight = QDoubleSpinBox()
    self.Weight.setRange(0.0, 1000.0)
    self.Weight.setSingleStep(1.0)
    self.Weight.setValue(1.0)
    self.WeightLayout.addWidget(self.Weight)
    self.main_layout.addLayout(self.WeightLayout)
    self.main_layout.addSpacing(30)
    
    # Robust
    self.RobustLayout = QHBoxLayout()
    self.RobustLayout.addWidget(QLabel('<b>Robust objective:</b>'))
    self.Robust = QCheckBox("")
    self.Robust.setChecked(False)
    if(RobustOpti == False): self.Robust.setDisabled(True)
    self.RobustLayout.addWidget(self.Robust)
    self.main_layout.addLayout(self.RobustLayout)
    self.main_layout.addSpacing(30)
    
    # buttons
    self.ButtonLayout = QHBoxLayout()
    self.main_layout.addLayout(self.ButtonLayout)
    self.CancelButton = QPushButton('Cancel')
    self.ButtonLayout.addWidget(self.CancelButton)
    self.CancelButton.clicked.connect(self.reject) 
    self.AddButton = QPushButton('Add')
    self.AddButton.clicked.connect(self.accept) 
    self.ButtonLayout.addWidget(self.AddButton)
