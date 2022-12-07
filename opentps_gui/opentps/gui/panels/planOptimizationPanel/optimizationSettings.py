from PyQt5.QtWidgets import *


class OptiSettingsDialog(QDialog):

    def __init__(self, optiParams):

        self.optiParam = optiParams

        # initialize the window
        QDialog.__init__(self)

        self.setWindowTitle('Optimization Settings')
        self.resize(300, 300)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.layout.addWidget(QLabel('<b>Optimization algorithm:</b>'))
        self.algorithm = QComboBox()
        self.algorithm.addItems(['Scipy-LBFGS (recommended)', 'Scipy-BFGS', 'In-house Gradient', 'In-house BFGS', 'In-house LBFGS', 'FISTA'])
        self.algorithm.setCurrentText(self.optiParam['method'])
        self.layout.addWidget(self.algorithm)

        self.layout.addSpacing(20)

        self._genParamLayout = QHBoxLayout()
        self.layout.addLayout(self._genParamLayout)

        self._genParamLayout.addWidget(QLabel('<b>General Parameters:</b>'))

        self._maxIterLayout = QHBoxLayout()
        self.layout.addLayout(self._maxIterLayout)

        self._maxIterLabel = QLabel('Max iterations:')
        self._maxIterLayout.addWidget(self._maxIterLabel)
        self._maxIterSpin = QDoubleSpinBox()
        self._maxIterSpin.setGroupSeparatorShown(True)
        self._maxIterSpin.setRange(0, 1e6)
        self._maxIterSpin.setSingleStep(50)
        self._maxIterSpin.setValue(1000)
        self._maxIterSpin.setDecimals(0)
        self._maxIterLayout.addWidget(self._maxIterSpin)

        self._stepLayout = QHBoxLayout()
        self.layout.addLayout(self._stepLayout)
        self._stepLabel = QLabel('Step:')
        self._stepLayout.addWidget(self._stepLabel)
        self._stepSpin = QDoubleSpinBox()
        self._stepSpin.setGroupSeparatorShown(True)
        self._stepSpin.setRange(0.0, 10.)
        self._stepSpin.setSingleStep(0.01)
        self._stepSpin.setValue(0.01)
        self._stepSpin.setEnabled(False)
        self._stepLayout.addWidget(self._stepSpin)
        self.layout.addSpacing(15)

        self._boundsLayout = QHBoxLayout()
        self.layout.addLayout(self._boundsLayout)
        self._boundsLabel = QLabel('MU Bounds constraints:')
        # self._boundsLabel.toggled.connect(self._setScoringSpacingVisible)
        self._boundsLayout.addWidget(self._boundsLabel)


        self._boundMinSpin = QDoubleSpinBox()
        self._boundMinSpin.setGroupSeparatorShown(True)
        self._boundMinSpin.setRange(0.0, 10.)
        self._boundMinSpin.setSingleStep(0.01)
        self._boundMinSpin.setValue(0.0)
        self._boundsLayout.addWidget(self._boundMinSpin)

        self._boundMaxSpin = QDoubleSpinBox()
        self._boundMaxSpin.setGroupSeparatorShown(True)
        self._boundMaxSpin.setRange(0.0, 1000.)
        self._boundMaxSpin.setSingleStep(5)
        self._boundMaxSpin.setValue(999.)
        self._boundsLayout.addWidget(self._boundMaxSpin)

        self.algorithm.setCurrentText(self.optiParam['method'])
        self.updateOptiParams()

        self.algorithm.currentIndexChanged.connect(self.updateOptiParams)

        # buttons
        self.buttonLayout = QHBoxLayout()
        self.layout.addLayout(self.buttonLayout)
        self.cancelButton = QPushButton('Cancel')
        self.buttonLayout.addWidget(self.cancelButton)
        self.cancelButton.clicked.connect(self.reject)
        self.okButton = QPushButton('OK')
        self.okButton.clicked.connect(self.returnParameters)
        self.buttonLayout.addWidget(self.okButton)

    def updateOptiParams(self):
        if self.algorithm.currentText() == 'Scipy-LBFGS (recommended)' or self.algorithm.currentText() == 'Scipy-BFGS':
            self._stepSpin.setEnabled(False)
            self._boundMinSpin.setEnabled(True)
            self._boundMaxSpin.setEnabled(True)
            self._boundsLabel.setEnabled(True)
        else:
            self._stepSpin.setEnabled(True)
            self._boundMinSpin.setEnabled(False)
            self._boundMaxSpin.setEnabled(False)
            self._boundsLabel.setEnabled(False)


    def returnParameters(self):

        self.optiParam["maxIter"] = int(self._maxIterSpin.value())
        try:
            self.optiParam["step"] = self._stepSpin.value()
        except ValueError:
            self.optiParam["step"] = None
        try:
            if self._boundMinSpin.value() == 0. and self._boundMaxSpin.value() == 999.:
                self.optiParam["bounds"] = None
            else:
                self.optiParam["bounds"] = self._boundMinSpin.value(), self._boundMaxSpin.value()
        except ValueError:
            self.optiParam["bounds"] = None
        print
        self.optiParam["method"] = self.algorithm.currentText()

        self.accept()
