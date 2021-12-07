import os

from PyQt5.QtCore import QSize, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QToolBar, QAction, QHBoxLayout, QGridLayout, QLabel, QPushButton
from pyqtgraph import PlotWidget, PlotCurveItem


class ProfilePlot(QWidget):
    newProfileSignal = pyqtSignal(object)

    def __init__(self):
        QWidget.__init__(self)

        self._layout = QHBoxLayout(self)
        self._profilePlot = _ProfilePlot()
        self._toolbar = _ProfileToolbar()

        self._toolbar.newProfileSignal.connect(self.addProfile)

        self._layout.setContentsMargins(0, 0, 0, 0)

        self._layout.addWidget(self._toolbar)
        self._layout.addWidget(self._profilePlot)

        self.setLayout(self._layout)

    def addProfile(self):
        pl = self._profilePlot.newProfile([0, 0], [0, 0])
        self.newProfileSignal.emit(pl.setData)

class _ProfilePlot(PlotWidget):
    def __init__(self):
        PlotWidget.__init__(self)

        self.getPlotItem().setContentsMargins(5, 0, 20, 5)
        self.setBackground('k')
        self.setTitle("Profiles")
        self.setLabel('left', 'Intensity')
        self.setLabel('bottom', 'Distance (mm)')

    def newProfile(self, x, y):
        pl = PlotCurveItem(x, y)
        self.addItem(pl)

        return pl

class _ProfileToolbar(QWidget):
    newProfileSignal = pyqtSignal()

    def __init__(self):
        QWidget.__init__(self)

        self._layout = QHBoxLayout(self)

        self.setLayout(self._layout)

        iconPath = 'GUI' + os.path.sep + 'res' + os.path.sep + 'icons' + os.path.sep

        icon = QIcon(iconPath+"pencil--plus.png")
        self._buttonNewProfile = QPushButton()
        self._buttonNewProfile.setIcon(icon)
        self._buttonNewProfile.setIconSize(QSize(16, 16))
        self._buttonNewProfile.clicked.connect(self.newProfileSignal.emit)

        self.setLayout(self._layout)

        self.setAutoFillBackground(True)
        self._layout.addWidget(self._buttonNewProfile)

    def _handleNewProfile(self):
        pass

