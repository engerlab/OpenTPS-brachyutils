
__docformat__ = "restructuredtext en"
__all__ = ['ResampleWidget']

from typing import Sequence

import numpy as np
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QMainWindow, QVBoxLayout, QPushButton, QFrame, QLabel, QDoubleSpinBox

from opentps.core.processing.imageProcessing import resampler3D
from opentps.gui.panels.patientDataPanel.patientDataSelection import PatientDataSelection


class ResampleWidget(QMainWindow):
    def __init__(self, viewController, parent=None):
        super().__init__(parent)

        self._viewController = viewController

        self.setWindowTitle('Crop tool')

        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        self._mainLayout = QHBoxLayout()
        centralWidget.setLayout(self._mainLayout)

        self._resampleOptions = ResampleOptions(self._viewController)

        self._cropDataButton = QPushButton('Resample all selected data')
        self._cropDataButton.clicked.connect(self._resampleData)

        self._dataSelection = PatientDataSelection((self._viewController))

        self._menuFrame = QFrame(self)
        self._menuFrame.setMaximumWidth(400)
        self._menuLayout = QVBoxLayout(self._menuFrame)
        self._menuFrame.setLayout(self._menuLayout)

        self._mainLayout.addWidget(self._menuFrame)
        self._menuLayout.addWidget(self._dataSelection)
        self._menuLayout.addWidget(self._resampleOptions)
        self._menuLayout.addWidget(self._cropDataButton)

    def _resampleData(self):
        newSpacing = np.array(self._resampleOptions.newSpacing)

        for data in self._dataSelection.selectedData:
            resampler3D.resampleImage3D(data, newSpacing, inPlace=True)


class ResampleOptions(QWidget):
    def __init__(self, viewController):
        super().__init__()

        self._viewController = viewController

        self._mainLayout = QVBoxLayout()
        self.setLayout(self._mainLayout)

        self._layerLabel = QLabel('New spacing:')
        self._mainLayout.addWidget(self._layerLabel)
        self._spacing1Spin = QDoubleSpinBox()

        self._spacingFrame = QFrame(self)
        self._mainLayout.addWidget(self._spacingFrame)
        self._spacingFrame.setFixedWidth(200)
        self._spacingLayout = QHBoxLayout(self._spacingFrame)
        self._spacingFrame.setLayout(self._spacingLayout)

        self._spacing1Spin.setGroupSeparatorShown(True)
        self._spacing1Spin.setRange(0.1, 100.0)
        self._spacing1Spin.setSingleStep(1.0)
        self._spacing1Spin.setValue(2.0)
        self._spacing1Spin.setSuffix(" mm")
        self._spacingLayout.addWidget(self._spacing1Spin)

        self._spacing2Spin = QDoubleSpinBox()
        self._spacing2Spin.setGroupSeparatorShown(True)
        self._spacing2Spin.setRange(0.1, 100.0)
        self._spacing2Spin.setSingleStep(1.0)
        self._spacing2Spin.setValue(2.0)
        self._spacing2Spin.setSuffix(" mm")
        self._spacingLayout.addWidget(self._spacing2Spin)

        self._spacing3Spin = QDoubleSpinBox()
        self._spacing3Spin.setGroupSeparatorShown(True)
        self._spacing3Spin.setRange(0.1, 100.0)
        self._spacing3Spin.setSingleStep(1.0)
        self._spacing3Spin.setValue(2.0)
        self._spacing3Spin.setSuffix(" mm")
        self._spacingLayout.addWidget(self._spacing3Spin)

    @property
    def newSpacing(self) -> Sequence[float]:
        return (self._spacing1Spin.value(), self._spacing2Spin.value(), self._spacing3Spin.value())
