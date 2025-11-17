
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from opentps.core.data.plan import Robustness
from opentps.core.data.plan._robustnessProton import RobustnessProton
from opentps.core.data.plan._robustnessPhoton import RobustnessPhoton

class RobustnessSettings(QWidget):
    def __init__(self, viewController, planEvaluation=False, parent=None):
        QWidget.__init__(self, parent=parent)

        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)

        self.layout.setContentsMargins(0, 0, 0, 0)

        self.modality = "IMPT" #default
        self.planEval = planEvaluation

        self._robustnessSettingsButton = QPushButton('Modify robustness settings')
        self._robustnessSettingsButton.clicked.connect(self._openRobustnessSettings)
        self.layout.addWidget(self._robustnessSettingsButton)

        self._robustSettingsLabel = QLabel('')
        self.layout.addWidget(self._robustSettingsLabel)

        self._dialog = RobustnessSettingsDialog(self.modality, planEvaluation=self.planEval)
        self._robustParam = self._dialog.robustness
        RobustSettings = 'No robust settings'
        self._robustSettingsLabel.setText(RobustSettings)
        self._updateRobustSettings()

        #self._dialog = RobustnessSettingsDialog(modality="IMPT",planEvaluation=planEvaluation)
        #self._robustParam = self._dialog.robustness
        #self._robustParam = None
        #self._updateRobustSettings()
        
    @property
    def robustness(self) -> Robustness:
        return self._robustParam
    
    def _openRobustnessSettings(self):
        self._dialog = RobustnessSettingsDialog(self.modality, planEvaluation=self.planEval)
        #self._robustParam = self._dialog.robustness  # Always set this after creating the dialog
        if self._dialog.exec():
            self._robustParam = self._dialog.robustness
        self._updateRobustSettings()

    def _updateRobustSettings(self):
        RobustSettings = ''
        if (self._robustParam.selectionStrategy == self._robustParam.Strategies.ALL):
            if self.modality == "IMPT":
                self._robustParam.numScenarios = 81
                if(self._robustParam.setupSystematicError[0] == 0.0): self._robustParam.numScenarios/=3
                if(self._robustParam.setupSystematicError[1] == 0.0): self._robustParam.numScenarios/=3
                if(self._robustParam.setupSystematicError[2] == 0.0): self._robustParam.numScenarios/=3
                if(self._robustParam.rangeSystematicError == 0.0): self._robustParam.numScenarios/=3
            elif self.modality == "IMRT":
                self._robustParam.numScenarios = 27 if self._robustParam.setupSystematicError[0] != 0.0 else 1
            RobustSettings += '<b>Scenario</b>: '
            RobustSettings += 'All (' + str(int(self._robustParam.numScenarios)) + ' scenarios) <br>'
            RobustSettings += 'Syst. setup: E<sub>S</sub> = ' + str(self._robustParam.setupSystematicError) + ' mm<br>'
            if self.modality == "IMPT":
                RobustSettings += 'Rand. setup: &sigma;<sub>S</sub> = ' + str(self._robustParam.setupRandomError) + ' mm<br>'
                RobustSettings += 'Syst. range: E<sub>R</sub> = ' + str(self._robustParam.rangeSystematicError) + ' %<br>'
        elif (self._robustParam.selectionStrategy == self._robustParam.Strategies.REDUCED_SET):
            if self.modality == "IMPT":
                self._robustParam.numScenarios = 21
                if(self._robustParam.setupSystematicError[0] == 0.0): self._robustParam.numScenarios-=6
                if(self._robustParam.setupSystematicError[1] == 0.0): self._robustParam.numScenarios-=6
                if(self._robustParam.setupSystematicError[2] == 0.0): self._robustParam.numScenarios-=6
                if(self._robustParam.rangeSystematicError == 0.0): self._robustParam.numScenarios/=3
            elif self.modality == "IMRT":
                self._robustParam.numScenarios = 7 if self._robustParam.setupSystematicError[0] != 0.0 else 1
            RobustSettings += '<b>Scenario</b>: '
            RobustSettings += 'Reduced set (' + str(int(self._robustParam.numScenarios)) + ' scenarios) <br>'
            RobustSettings += 'Syst. setup: &Sigma;<sub>S</sub> = ' + str(self._robustParam.setupSystematicError) + ' mm<br>'
            if self.modality == "IMPT":
                RobustSettings += 'Rand. setup: &sigma;<sub>S</sub> = ' + str(self._robustParam.setupRandomError) + ' mm<br>'
                RobustSettings += 'Syst. range: &Sigma;<sub>R</sub> = ' + str(self._robustParam.rangeSystematicError) + ' %<br>'
        elif self._robustParam.selectionStrategy == self._robustParam.Strategies.RANDOM:
            RobustSettings += '<b>Scenario</b>: '
            RobustSettings += 'Random <br>'
            #RobustSettings += 'Syst. setup: &Sigma;<sub>S</sub> = ' + str(self._robustParam.setupSystematicError) + ' mm<br>'
            #RobustSettings += 'Rand. setup: &sigma;<sub>S</sub> = ' + str(self._robustParam.setupRandomError) + ' mm<br>'
            RobustSettings += 'Random num of scenarios = ' + str(int(self._robustParam.numRandomScenarios)) + '<br>'
            if self.modality == "IMPT": RobustSettings += 'Syst. range: &Sigma;<sub>R</sub> = ' + str(self._robustParam.rangeSystematicError) + ' %<br>'
        else:
            self._robustParam.selectionStrategy = self._robustParam.Strategies.DISABLED
            RobustSettings = 'No robust settings'

        self._robustSettingsLabel.setText(RobustSettings)

    def _updateForModality(self, modality):
        if modality == "IMRT":
            self.modality = "IMRT"
        elif modality == "IMPT":
            self.modality = "IMPT"
        else:
            raise ValueError("Unsupported modality selected")
    

class RobustnessSettingsDialog(QDialog):
    def __init__(self, modality, planEvaluation=False):
        super().__init__()
        self.modality = modality

        if self.modality == "IMRT":
            self._robustParam = RobustnessPhoton()
        elif self.modality == "IMPT":
            self._robustParam = RobustnessProton()
        else:
            raise ValueError("Unsupported modality selected")

        self._initialize_dialog()
        
    def _initialize_dialog(self):
        QDialog.__init__(self)
        self.setWindowTitle('Robustness Settings')
        self.resize(300, 300)
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        self.main_layout.addWidget(QLabel('<b>Scenario selection strategy:</b>'))
        self._strategyBox = QComboBox()
        self._strategyBox.setMaximumWidth(300 - 18)

        self._strategyBox.addItems(['Disabled', 'Reduced set','All','Random'])

        self.main_layout.addWidget(self._strategyBox)
        self.main_layout.addSpacing(20)
        self.ErrorLayout = QGridLayout()
        self.main_layout.addLayout(self.ErrorLayout)
        self.ErrorLayout.addWidget(QLabel('<b>Setup errors:</b>'), 0, 0, 1, 2)
        self.ErrorLayout.addWidget(QLabel('X'), 0, 2, 1, 1, Qt.AlignCenter)
        self.ErrorLayout.addWidget(QLabel('Y'), 0, 3, 1, 1, Qt.AlignCenter)
        self.ErrorLayout.addWidget(QLabel('Z'), 0, 4, 1, 1, Qt.AlignCenter)
        self.ErrorLayout.setRowMinimumHeight(0, 25)
        self.ErrorLayout.addWidget(QLabel('Systematic'), 1, 0)
        self.SigmaS_label = QLabel('&Sigma;<sub>S</sub>')
        self.ErrorLayout.addWidget(self.SigmaS_label, 1, 1)
        self.syst_setup_x = QLineEdit(str(self._robustParam.setupSystematicError[0]))
        self.syst_setup_x.setMaximumWidth(30)
        self.ErrorLayout.addWidget(self.syst_setup_x, 1, 2)
        self.syst_setup_y = QLineEdit(str(self._robustParam.setupSystematicError[1]))
        self.syst_setup_y.setMaximumWidth(30)
        self.ErrorLayout.addWidget(self.syst_setup_y, 1, 3)
        self.syst_setup_z = QLineEdit(str(self._robustParam.setupSystematicError[2]))
        self.syst_setup_z.setMaximumWidth(30)
        self.ErrorLayout.addWidget(self.syst_setup_z, 1, 4)
        self.ErrorLayout.addWidget(QLabel('mm'), 1, 5)
        
        self.ErrorLayout.addWidget(QLabel('Equiv. margin:'), 3, 0, 1, 2)
        self.SetupMarginX = QLabel('1.0')
        self.ErrorLayout.addWidget(self.SetupMarginX, 3, 2)
        self.SetupMarginY = QLabel('1.0')
        self.ErrorLayout.addWidget(self.SetupMarginY, 3, 3)
        self.SetupMarginZ = QLabel('1.0')
        self.ErrorLayout.addWidget(self.SetupMarginZ, 3, 4)
        self.ErrorLayout.addWidget(QLabel('mm'), 3, 5)
        self.ErrorLayout.setRowMinimumHeight(3, 25)
        self.ErrorLayout.setRowMinimumHeight(4, 25)

        self.numRandSceLabel = QLabel('<b> Number of random scenarios: ')
        self.ErrorLayout.addWidget(self.numRandSceLabel)
        self.numRandSceSpin = QSpinBox()
        self.numRandSceSpin.setGroupSeparatorShown(True)
        self.numRandSceSpin.setRange(0, 100)
        self.numRandSceSpin.setSingleStep(1)
        self.numRandSceSpin.setValue(50)
        self.ErrorLayout.addWidget(self.numRandSceSpin)
        self.numRandSceLabel.hide()
        self.numRandSceSpin.hide()
        
        if self.modality == "IMPT":
            self.ErrorLayout.addWidget(QLabel('Random'), 2, 0)
            self.sigmaS_label = QLabel('&sigma;<sub>S</sub>')
            self.ErrorLayout.addWidget(self.sigmaS_label, 2, 1)
            self.rand_setup_x = QLineEdit(str(self._robustParam.setupRandomError[0]))
            self.rand_setup_x.setMaximumWidth(30)
            self.ErrorLayout.addWidget(self.rand_setup_x, 2, 2)
            self.rand_setup_y = QLineEdit(str(self._robustParam.setupRandomError[1]))
            self.rand_setup_y.setMaximumWidth(30)
            self.ErrorLayout.addWidget(self.rand_setup_y, 2, 3)
            self.rand_setup_z = QLineEdit(str(self._robustParam.setupRandomError[2]))
            self.rand_setup_z.setMaximumWidth(30)
            self.ErrorLayout.addWidget(self.rand_setup_z, 2, 4)
            self.ErrorLayout.addWidget(QLabel('mm'), 2, 5)

            self.ErrorLayout.addWidget(QLabel('<b>Range uncertainties:</b>'), 5, 0, 1, 4)
            self.ErrorLayout.addWidget(QLabel('Systematic'), 6, 0)
            self.SigmaR_label = QLabel('&Sigma;<sub>R</sub>')
            self.ErrorLayout.addWidget(self.SigmaR_label, 6, 1)
            self.syst_range = QLineEdit(str(self._robustParam.rangeSystematicError))
            self.syst_range.setMaximumWidth(30)
            self.ErrorLayout.addWidget(self.syst_range, 6, 2)
            self.ErrorLayout.addWidget(QLabel('%'), 6, 3)
            self.ErrorLayout.addWidget(QLabel('Equiv. error:'), 7, 0, 1, 2)
            self.RangeError = QLabel('1.0')
            self.ErrorLayout.addWidget(self.RangeError, 7, 2)
            self.ErrorLayout.addWidget(QLabel('%'), 7, 3)
            self.syst_range.textChanged.connect(self.recompute_margin)
        self.main_layout.addSpacing(30)

        self._strategyBox.currentIndexChanged.connect(self.updateRobustStrategy)
        self.syst_setup_x.textChanged.connect(self.recompute_margin)
        self.syst_setup_y.textChanged.connect(self.recompute_margin)
        self.syst_setup_z.textChanged.connect(self.recompute_margin)
        if self.modality=="IMPT":
            self.rand_setup_x.textChanged.connect(self.recompute_margin)
            self.rand_setup_y.textChanged.connect(self.recompute_margin)
            self.rand_setup_z.textChanged.connect(self.recompute_margin)
        self.recompute_margin()
        if (self._strategyBox.currentText() == 'Disabled'): self.updateRobustStrategy()

        # buttons
        self.ButtonLayout = QHBoxLayout()
        self.main_layout.addLayout(self.ButtonLayout)
        self.CancelButton = QPushButton('Cancel')
        self.ButtonLayout.addWidget(self.CancelButton)
        self.CancelButton.clicked.connect(self.reject)
        self.OkButton = QPushButton('OK')
        self.OkButton.clicked.connect(self.return_parameters)
        self.ButtonLayout.addWidget(self.OkButton)

        self.updateRobustStrategy()

    @property
    def robustness(self) -> Robustness:
        self._updateRobustParam()
        return self._robustParam

    @robustness.setter
    def robustness(self, r:Robustness):
        self._robustParam = r
        self.updateRobustStrategy()


    def _updateRobustParam(self):
        self._robustParam.setupSystematicError = [float(self.syst_setup_x.text()), float(self.syst_setup_y.text()),
                                                  float(self.syst_setup_z.text())]
        
        if self.modality=="IMPT":
            self._robustParam.setupRandomError = [float(self.rand_setup_x.text()), float(self.rand_setup_y.text()),
                                              float(self.rand_setup_z.text())]
            self._robustParam.rangeSystematicError = float(self.syst_range.text())
        self._robustParam.numRandomScenarios = self.numRandSceSpin.value()

        if (self._strategyBox.currentText() == 'Disabled'):
            self._robustParam.selectionStrategy = Robustness.Strategies.DISABLED
        elif (self._strategyBox.currentText() == 'All'):
            self._robustParam.selectionStrategy = Robustness.Strategies.ALL
        elif (self._strategyBox.currentText() == 'Reduced set'):
            self._robustParam.selectionStrategy = Robustness.Strategies.REDUCED_SET
        elif (self._strategyBox.currentText() == 'Random'):
            self._robustParam.selectionStrategy = Robustness.Strategies.RANDOM

    @property
    def robustStrategie(self):
        return self._robustParam.selectionStrategy

    @robustStrategie.setter
    def robustStrategie(self, strategy):
        if strategy == Robustness.Strategies.DISABLED:
            self._strategyBox.setCurrentText('Disabled')
        elif strategy == Robustness.Strategies.ALL:
            self._strategyBox.setCurrentText('ALL')
        elif strategy == Robustness.Strategies.REDUCED_SET:
            self._strategyBox.setCurrentText('Reduced set')
        elif strategy == Robustness.Strategies.RANDOM:
            self._strategyBox.setCurrentText('Random')

        self.updateRobustStrategy()

    def updateRobustStrategy(self):
        if (self._strategyBox.currentText() == 'Disabled'):
            self.syst_setup_x.setEnabled(False)
            self.syst_setup_y.setEnabled(False)
            self.syst_setup_z.setEnabled(False)

            self.numRandSceLabel.show()
            self.numRandSceSpin.show()
            self.numRandSceSpin.setEnabled(False)
            
            if self.modality=="IMPT":
                self.rand_setup_x.setEnabled(False)
                self.rand_setup_y.setEnabled(False)
                self.rand_setup_z.setEnabled(False)
                self.syst_range.setEnabled(False)

        elif (self._strategyBox.currentText() == 'All'):
            self.syst_setup_x.setEnabled(True)
            self.syst_setup_y.setEnabled(True)
            self.syst_setup_z.setEnabled(True)

            if self.modality=="IMPT":
                self.rand_setup_x.setEnabled(True)
                self.rand_setup_y.setEnabled(True)
                self.rand_setup_z.setEnabled(True)
                self.syst_range.setEnabled(True)
            self.SigmaS_label.setText('E<sub>S</sub>')
            
            self.syst_setup_x.setText('5.0')
            self.syst_setup_y.setText('5.0')
            self.syst_setup_z.setText('5.0')

            if self.modality=="IMPT": 
                self.rand_setup_x.setText('0.0')
                self.rand_setup_y.setText('0.0')
                self.rand_setup_z.setText('0.0')
                self.syst_range.setText('3.0')
                self.SigmaR_label.setText('E<sub>R</sub>')
            
            self.numRandSceLabel.hide()
            self.numRandSceSpin.hide()

        elif (self._strategyBox.currentText() == 'Reduced set'):
            self.syst_setup_x.setEnabled(True)
            self.syst_setup_y.setEnabled(True)
            self.syst_setup_z.setEnabled(True)
            if self.modality=="IMPT": 
                self.rand_setup_x.setEnabled(True)
                self.rand_setup_y.setEnabled(True)
                self.rand_setup_z.setEnabled(True)
                self.syst_range.setEnabled(True)
                self.SigmaR_label.setText('&Sigma;<sub>R</sub>')
            self.SigmaS_label.setText('&Sigma;<sub>S</sub>')
            self.syst_setup_x.setText('2.0')
            self.syst_setup_y.setText('2.0')
            self.syst_setup_z.setText('2.0')

            if self.modality=="IMPT": 
                self.rand_setup_x.setText('0.0')
                self.rand_setup_y.setText('0.0')
                self.rand_setup_z.setText('0.0')
                self.syst_range.setText('1.6')

            self.numRandSceLabel.hide()
            self.numRandSceSpin.hide()

        else:
            self.syst_setup_x.setEnabled(False)
            self.syst_setup_y.setEnabled(False)
            self.syst_setup_z.setEnabled(False)

            if self.modality=="IMPT":
                self.rand_setup_x.setEnabled(False)
                self.rand_setup_y.setEnabled(False)
                self.rand_setup_z.setEnabled(False) 
                self.syst_range.setEnabled(False)
                self.SigmaR_label.setText('&Sigma;<sub>R</sub>')
                self.rand_setup_x.setText('1.4')
                self.rand_setup_y.setText('1.4')
                self.rand_setup_z.setText('1.4')
            self.SigmaS_label.setText('&Sigma;<sub>S</sub>')  
            self.syst_setup_x.setText('1.6')
            self.syst_setup_y.setText('1.6')
            self.syst_setup_z.setText('1.6')
        

            self.numRandSceLabel.show()
            self.numRandSceSpin.show()
            self.numRandSceSpin.setEnabled(True)

            if self.modality=="IMPT": self.syst_range.setText('1.6')

        self.recompute_margin()

    def recompute_margin(self):
        Sigma_x = float(self.syst_setup_x.text())
        Sigma_y = float(self.syst_setup_y.text())
        Sigma_z = float(self.syst_setup_z.text())
        if self.modality=="IMPT":
            sigma_x = float(self.rand_setup_x.text())
            sigma_y = float(self.rand_setup_y.text())
            sigma_z = float(self.rand_setup_z.text())
        if hasattr(self,"syst_range"):
            range_sigma = float(self.syst_range.text())
        else:
            range_sigma = 1
        if not (hasattr(self,"sigma_x") and hasattr(self,"sigma_y") and hasattr(self,"sigma_z")):
            sigma_x=1
            sigma_y=1
            sigma_z=1

        if (self._strategyBox.currentText() == 'Reduced set'):
            margin_x = 1.0 * Sigma_x + 0.7 * sigma_x
            margin_y = 1.0 * Sigma_y + 0.7 * sigma_y
            margin_z = 1.0 * Sigma_z + 0.7 * sigma_z
            margin_r = 1.0 * range_sigma

        else:
            margin_x = 2.5 * Sigma_x + 0.7 * sigma_x
            margin_y = 2.5 * Sigma_y + 0.7 * sigma_y
            margin_z = 2.5 * Sigma_z + 0.7 * sigma_z
            margin_r = 1.5 * range_sigma

        if (self._strategyBox.currentText() != 'Disabled'):
            self.SetupMarginX.setText('{:3.1f}'.format(margin_x))
            self.SetupMarginY.setText('{:3.1f}'.format(margin_y))
            self.SetupMarginZ.setText('{:3.1f}'.format(margin_z))
            if self.modality=="IMPT": self.RangeError.setText('{:3.1f}'.format(margin_r))

    def return_parameters(self):
        self._updateRobustParam()
        self.accept()

