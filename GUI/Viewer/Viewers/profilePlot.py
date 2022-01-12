import os

from PyQt5.QtCore import QSize, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QToolBar, QAction, QHBoxLayout, QGridLayout, QLabel, QPushButton, \
    QFileDialog
from pyqtgraph import PlotWidget, PlotCurveItem
from pyqtgraph.exporters import ImageExporter


class ProfilePlot(QWidget):
    def __init__(self, viewController):
        QWidget.__init__(self)

        self._layout = QHBoxLayout(self)
        self._profileCount = 0
        self._profilePlot = _ProfilePlot()
        self._toolbar = _ProfileToolbar()
        self._viewController = viewController

        self._toolbar.newProfileSignal.connect(self.addProfile)
        self._toolbar.removeAllSignal.connect(self.removeAll)
        self._toolbar.saveSignal.connect(self._profilePlot.export)
        self._toolbar.validateSignal.connect(self.validate)

        self._layout.setContentsMargins(0, 0, 0, 0)

        self._layout.addWidget(self._toolbar)
        self._layout.addWidget(self._profilePlot)

        self.setLayout(self._layout)

    def addProfile(self):
        pl = self._profilePlot.newProfile([0, 0], [0, 0], self._profileCount)
        self._profileCount += 1
        self._viewController._setLineWidgetEnabled(True, pl.setData)

    def removeAll(self):
        self.validate()
        self._profilePlot.removeAll()

    def validate(self):
        self._viewController._setLineWidgetEnabled(False)

class QStringList:
    pass


class _ProfilePlot(PlotWidget):
    def __init__(self):
        PlotWidget.__init__(self)

        self._items = []
        self.getPlotItem().setContentsMargins(5, 0, 20, 5)
        self.setBackground('k')
        self.setTitle("Profiles")
        self.setLabel('left', 'Intensity')
        self.setLabel('bottom', 'Distance (mm)')

    def export(self):
        exporter = ImageExporter(self.getPlotItem())

        dlg = QFileDialog()
        dlg.setAcceptMode(QFileDialog.AcceptSave)
        dlg.setFileMode(QFileDialog.AnyFile)
        supportedExtensions = exporter.getSupportedImageFormats()
        str = ''
        for extension in supportedExtensions:
            str += extension + ' (' + extension + ')' + ';;'
        str  = str[:-2]

        filename = dlg.getSaveFileName(filter=str)

        if filename is None:
            return

        exporter.export(filename[0])

    def newProfile(self, x, y, color):
        pl = PlotCurveItem(x, y, pen=({'color': color}))
        self.addItem(pl)
        self._items.append(pl)

        return pl

    def removeAll(self):
        for item in self._items:
            self.removeItem(item)

        self._items = []

class _ProfileToolbar(QWidget):
    newProfileSignal = pyqtSignal()
    removeAllSignal = pyqtSignal()
    saveSignal = pyqtSignal()
    validateSignal = pyqtSignal()

    def __init__(self):
        QWidget.__init__(self)

        self._layout = QVBoxLayout(self)

        self.setLayout(self._layout)

        iconPath = 'GUI' + os.path.sep + 'res' + os.path.sep + 'icons' + os.path.sep

        icon = QIcon(iconPath+"pencil--plus.png")
        self._buttonNewProfile = QPushButton()
        self._buttonNewProfile.setIcon(icon)
        self._buttonNewProfile.setIconSize(QSize(16, 16))
        self._buttonNewProfile.clicked.connect(self.newProfileSignal.emit)

        icon = QIcon(iconPath + "cross.png")
        self._buttonRemoveAll = QPushButton()
        self._buttonRemoveAll.setIcon(icon)
        self._buttonRemoveAll.setIconSize(QSize(16, 16))
        self._buttonRemoveAll.clicked.connect(self.removeAllSignal.emit)

        icon = QIcon(iconPath + "disk.png")
        self._buttonSave = QPushButton()
        self._buttonSave.setIcon(icon)
        self._buttonSave.setIconSize(QSize(16, 16))
        self._buttonSave.clicked.connect(self.saveSignal.emit)

        icon = QIcon(iconPath + "tick-button.png")
        self._buttonValidate = QPushButton()
        self._buttonValidate.setIcon(icon)
        self._buttonValidate.setIconSize(QSize(16, 16))
        self._buttonValidate.clicked.connect(self.validateSignal.emit)

        self.setLayout(self._layout)

        self.setAutoFillBackground(True)
        self._layout.addWidget(self._buttonNewProfile)
        self._layout.addWidget(self._buttonValidate)
        self._layout.addWidget(self._buttonRemoveAll)
        self._layout.addWidget(self._buttonSave)

        self._layout.addStretch(1)
