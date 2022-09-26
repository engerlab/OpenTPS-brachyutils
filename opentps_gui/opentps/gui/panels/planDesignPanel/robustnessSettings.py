from enum import Enum
from typing import Sequence

from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt


class RobustnessParameters:
    class Strategies(Enum):
        DEFAULT = "DISABLED"
        DISABLED = "DISABLED"
        ERRORSPACE_REGULAR = "ERRORSPACE_REGULAR"
        ERRORSPACE_STAT = "ERRORSPACE_STAT"
        DOSESPACE = "DOSESPACE"

    def __init__(self):
        self.strategy = self.Strategies.DEFAULT
        self.systSetup:Sequence[float] = [5., 5., 5.]
        self.randSetup:Sequence[float] = [0., 0., 0.]
        self.systRange:float = 3.

class RobustnessSettings(QDialog):
    def __init__(self, planEvaluation=False):
        self._robustParam = RobustnessParameters()

        # initialize the window
        QDialog.__init__(self)
        self.setWindowTitle('Robustness Settings')
        self.resize(300, 300)
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        self.main_layout.addWidget(QLabel('<b>Scenario selection strategy:</b>'))
        self.Strategy = QComboBox()
        self.Strategy.setMaximumWidth(300 - 18)

        if (planEvaluation):
            self.Strategy.addItems(
                ['Dosimetric space (statistical)', 'Error space (statistical)', 'Error space (regular)'])
        else:
            self.Strategy.addItems(['Disabled', 'Error space (regular)'])

        if (self._robustParam.strategy == RobustnessParameters.Strategies.DISABLED):
            self.Strategy.setCurrentText('Disabled')
        elif (self._robustParam.strategy == RobustnessParameters.Strategies.ERRORSPACE_REGULAR):
            self.Strategy.setCurrentText('Error space (regular)')
        elif (self._robustParam.strategy == RobustnessParameters.Strategies.ERRORSPACE_STAT):
            self.Strategy.setCurrentText('Error space (statistical)')
        else:
            self.Strategy.setCurrentText('Dosimetric space (statistical)')

        self.main_layout.addWidget(self.Strategy)
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
        self.syst_setup_x = QLineEdit(str(self._robustParam.systSetup[0]))
        self.syst_setup_x.setMaximumWidth(30)
        self.ErrorLayout.addWidget(self.syst_setup_x, 1, 2)
        self.syst_setup_y = QLineEdit(str(self._robustParam.systSetup[1]))
        self.syst_setup_y.setMaximumWidth(30)
        self.ErrorLayout.addWidget(self.syst_setup_y, 1, 3)
        self.syst_setup_z = QLineEdit(str(self._robustParam.systSetup[2]))
        self.syst_setup_z.setMaximumWidth(30)
        self.ErrorLayout.addWidget(self.syst_setup_z, 1, 4)
        self.ErrorLayout.addWidget(QLabel('mm'), 1, 5)
        self.ErrorLayout.addWidget(QLabel('Random'), 2, 0)
        self.sigmaS_label = QLabel('&sigma;<sub>S</sub>')
        self.ErrorLayout.addWidget(self.sigmaS_label, 2, 1)
        self.rand_setup_x = QLineEdit(str(self._robustParam.randSetup[0]))
        self.rand_setup_x.setMaximumWidth(30)
        self.ErrorLayout.addWidget(self.rand_setup_x, 2, 2)
        self.rand_setup_y = QLineEdit(str(self._robustParam.randSetup[1]))
        self.rand_setup_y.setMaximumWidth(30)
        self.ErrorLayout.addWidget(self.rand_setup_y, 2, 3)
        self.rand_setup_z = QLineEdit(str(self._robustParam.randSetup[2]))
        self.rand_setup_z.setMaximumWidth(30)
        self.ErrorLayout.addWidget(self.rand_setup_z, 2, 4)
        self.ErrorLayout.addWidget(QLabel('mm'), 2, 5)
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
        self.ErrorLayout.addWidget(QLabel('<b>Range uncertainties:</b>'), 5, 0, 1, 4)
        self.ErrorLayout.addWidget(QLabel('Systematic'), 6, 0)
        self.SigmaR_label = QLabel('&Sigma;<sub>R</sub>')
        self.ErrorLayout.addWidget(self.SigmaR_label, 6, 1)
        self.syst_range = QLineEdit(str(self._robustParam.systRange))
        self.syst_range.setMaximumWidth(30)
        self.ErrorLayout.addWidget(self.syst_range, 6, 2)
        self.ErrorLayout.addWidget(QLabel('%'), 6, 3)
        self.ErrorLayout.addWidget(QLabel('Equiv. error:'), 7, 0, 1, 2)
        self.RangeError = QLabel('1.0')
        self.ErrorLayout.addWidget(self.RangeError, 7, 2)
        self.ErrorLayout.addWidget(QLabel('%'), 7, 3)
        self.main_layout.addSpacing(30)

        self.Strategy.currentIndexChanged.connect(self.update_robust_strategy)
        self.syst_setup_x.textChanged.connect(self.recompute_margin)
        self.syst_setup_y.textChanged.connect(self.recompute_margin)
        self.syst_setup_z.textChanged.connect(self.recompute_margin)
        self.rand_setup_x.textChanged.connect(self.recompute_margin)
        self.rand_setup_y.textChanged.connect(self.recompute_margin)
        self.rand_setup_z.textChanged.connect(self.recompute_margin)
        self.syst_range.textChanged.connect(self.recompute_margin)
        self.recompute_margin()
        if (self.Strategy.currentText() == 'Disabled'): self.update_robust_strategy()

        # buttons
        self.ButtonLayout = QHBoxLayout()
        self.main_layout.addLayout(self.ButtonLayout)
        self.CancelButton = QPushButton('Cancel')
        self.ButtonLayout.addWidget(self.CancelButton)
        self.CancelButton.clicked.connect(self.reject)
        self.OkButton = QPushButton('OK')
        self.OkButton.clicked.connect(self.return_parameters)
        self.ButtonLayout.addWidget(self.OkButton)

    @property
    def robustParam(self):
        return self._robustParam

    def update_robust_strategy(self):
        if (self.Strategy.currentText() == 'Disabled'):
            self.syst_setup_x.setEnabled(False)
            self.syst_setup_y.setEnabled(False)
            self.syst_setup_z.setEnabled(False)
            self.rand_setup_x.setEnabled(False)
            self.rand_setup_y.setEnabled(False)
            self.rand_setup_z.setEnabled(False)
            self.syst_range.setEnabled(False)

        elif (self.Strategy.currentText() == 'Error space (regular)'):
            self.syst_setup_x.setEnabled(True)
            self.syst_setup_y.setEnabled(True)
            self.syst_setup_z.setEnabled(True)
            self.rand_setup_x.setEnabled(True)
            self.rand_setup_y.setEnabled(True)
            self.rand_setup_z.setEnabled(True)
            self.syst_range.setEnabled(True)
            self.SigmaS_label.setText('E<sub>S</sub>')
            self.SigmaR_label.setText('E<sub>R</sub>')
            self.syst_setup_x.setText('5.0')
            self.syst_setup_y.setText('5.0')
            self.syst_setup_z.setText('5.0')
            self.rand_setup_x.setText('0.0')
            self.rand_setup_y.setText('0.0')
            self.rand_setup_z.setText('0.0')
            self.syst_range.setText('3.0')

        elif (self.Strategy.currentText() == 'Error space (statistical)'):
            self.syst_setup_x.setEnabled(True)
            self.syst_setup_y.setEnabled(True)
            self.syst_setup_z.setEnabled(True)
            self.rand_setup_x.setEnabled(True)
            self.rand_setup_y.setEnabled(True)
            self.rand_setup_z.setEnabled(True)
            self.syst_range.setEnabled(True)
            self.SigmaS_label.setText('&Sigma;<sub>S</sub>')
            self.SigmaR_label.setText('&Sigma;<sub>R</sub>')
            self.syst_setup_x.setText('2.0')
            self.syst_setup_y.setText('2.0')
            self.syst_setup_z.setText('2.0')
            self.rand_setup_x.setText('0.0')
            self.rand_setup_y.setText('0.0')
            self.rand_setup_z.setText('0.0')
            self.syst_range.setText('1.6')

        else:
            self.syst_setup_x.setEnabled(True)
            self.syst_setup_y.setEnabled(True)
            self.syst_setup_z.setEnabled(True)
            self.rand_setup_x.setEnabled(True)
            self.rand_setup_y.setEnabled(True)
            self.rand_setup_z.setEnabled(True)
            self.syst_range.setEnabled(True)
            self.SigmaS_label.setText('&Sigma;<sub>S</sub>')
            self.SigmaR_label.setText('&Sigma;<sub>R</sub>')
            self.syst_setup_x.setText('1.6')
            self.syst_setup_y.setText('1.6')
            self.syst_setup_z.setText('1.6')
            self.rand_setup_x.setText('1.4')
            self.rand_setup_y.setText('1.4')
            self.rand_setup_z.setText('1.4')
            self.syst_range.setText('1.6')

        self.recompute_margin()

    def recompute_margin(self):
        Sigma_x = float(self.syst_setup_x.text())
        sigma_x = float(self.rand_setup_x.text())
        Sigma_y = float(self.syst_setup_y.text())
        sigma_y = float(self.rand_setup_y.text())
        Sigma_z = float(self.syst_setup_z.text())
        sigma_z = float(self.rand_setup_z.text())
        range_sigma = float(self.syst_range.text())

        if (self.Strategy.currentText() == 'Error space (regular)'):
            margin_x = 1.0 * Sigma_x + 0.7 * sigma_x
            margin_y = 1.0 * Sigma_y + 0.7 * sigma_y
            margin_z = 1.0 * Sigma_z + 0.7 * sigma_z
            margin_r = 1.0 * range_sigma

        else:
            margin_x = 2.5 * Sigma_x + 0.7 * sigma_x
            margin_y = 2.5 * Sigma_y + 0.7 * sigma_y
            margin_z = 2.5 * Sigma_z + 0.7 * sigma_z
            margin_r = 1.5 * range_sigma

        if (self.Strategy.currentText() != 'Disabled'):
            self.SetupMarginX.setText('{:3.1f}'.format(margin_x))
            self.SetupMarginY.setText('{:3.1f}'.format(margin_y))
            self.SetupMarginZ.setText('{:3.1f}'.format(margin_z))
            self.RangeError.setText('{:3.1f}'.format(margin_r))

    def return_parameters(self):
        self._robustParam.systSetup = [float(self.syst_setup_x.text()), float(self.syst_setup_y.text()),
                                          float(self.syst_setup_z.text())]
        self._robustParam.randSetup = [float(self.rand_setup_x.text()), float(self.rand_setup_y.text()),
                                          float(self.rand_setup_z.text())]
        self._robustParam.systRange = float(self.syst_range.text())

        if (self.Strategy.currentText() == 'Disabled'):
            self._robustParam.strategy = RobustnessParameters.Strategies.DISABLED
        elif (self.Strategy.currentText() == 'Dosimetric space (statistical)'):
            self._robustParam.strategy = RobustnessParameters.Strategies.DOSESPACE
        elif (self.Strategy.currentText() == 'Error space (statistical)'):
            self._robustParam.strategy = RobustnessParameters.Strategies.ERRORSPACE_STAT
        else:
            self._robustParam.strategy = RobustnessParameters.Strategies.ERRORSPACE_REGULAR

        self.accept()
