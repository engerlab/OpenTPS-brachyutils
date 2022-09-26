import os

from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog
from pyqtgraph import PlotWidget, PlotCurveItem, mkPen
from pyqtgraph.exporters import ImageExporter

import opentps.gui.res.icons as IconModule

class ProfileViewer(QWidget):
    def __init__(self, viewController, nbProfiles=10):
        QWidget.__init__(self)

        self._layout = QHBoxLayout(self)
        self._toolbar = _ProfileToolbar(self, viewController)
        self._viewController = viewController

        self._profilePlot = _ProfilePlot()
        self._profiles = []

        for i in range(nbProfiles):
            self._profiles.append(self._profilePlot.newProfile([0, 0], [0, 0]))

        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)
        self._layout.addWidget(self._toolbar)
        self._layout.addWidget(self._profilePlot)

    def count(self):
        return len(self._profiles)

    def drawProfile(self, profileIndex, *args, **kwargs):
        axY = self._profilePlot.getAxis('left')
        yRange = axY.range

        self.removeProfile(profileIndex)
        self._profiles[profileIndex] = self._profilePlot.newProfile(*args, **kwargs)

        if profileIndex>2:
            self._profilePlot.setYRange(yRange[0], yRange[1], padding=0.)

    def removeProfile(self, profileIndex):
        profile = self._profiles[profileIndex]
        self._profilePlot.removeItem(profile)

    @property
    def nbProfiles(self):
        return len(self._profiles)

    def erase(self):
        for profile in self._profiles:
            profile.setData([0, 0], [0, 0])

    def export(self):
        self._profilePlot.export()


class _ProfilePlot(PlotWidget):
    def __init__(self):
        PlotWidget.__init__(self)

        self.addLegend()
        self.getPlotItem().setContentsMargins(5, 0, 20, 5)
        self.setBackground('k')
        self.setTitle("Profiles")
        self.setLabel('left', 'Intensity')
        self.setLabel('bottom', 'Distance (mm)')

    def export(self):
        exporter = ImageExporter(self.getPlotItem())

        fileName = self.fileDialogForExporter(exporter)

        if fileName is None:
            return

        exporter.export(fileName[0])

    def fileDialogForExporter(self, exporter):
        dlg = QFileDialog()
        dlg.setAcceptMode(QFileDialog.AcceptSave)
        dlg.setFileMode(QFileDialog.AnyFile)

        supportedExtensions = exporter.getSupportedImageFormats()
        str = ''
        for extension in supportedExtensions:
            str += extension + ' (' + extension + ')' + ';;'
        str = str[:-2]

        fileName = dlg.getSaveFileName(filter=str)
        return fileName

    def newProfile(self, *args, **kwargs) -> PlotCurveItem:
        pl = PlotCurveItem(*args, **kwargs)
        self.addItem(pl)

        return pl

class _ProfileToolbar(QWidget):
    def __init__(self, profileViewer, viewController):
        QWidget.__init__(self)

        self._profileViewer = profileViewer
        self._viewController = viewController
        self._layout = QVBoxLayout(self)

        self.setLayout(self._layout)

        iconPath = IconModule.__path__[0] + os.path.sep

        icon = QIcon(iconPath+"pencil--plus.png")
        self._buttonNewProfile = QPushButton()
        self._buttonNewProfile.setIcon(icon)
        self._buttonNewProfile.setIconSize(QSize(16, 16))
        self._buttonNewProfile.clicked.connect(self._setProfileWidgetEnabled)

        icon = QIcon(iconPath + "cross.png")
        self._buttonStop = QPushButton()
        self._buttonStop.setIcon(icon)
        self._buttonStop.setIconSize(QSize(16, 16))
        self._buttonStop.clicked.connect(self._setProfileWidgetDisabled)

        icon = QIcon(iconPath + "disk.png")
        self._buttonSave = QPushButton()
        self._buttonSave.setIcon(icon)
        self._buttonSave.setIconSize(QSize(16, 16))
        self._buttonSave.clicked.connect(self._profileViewer.export)

        self.setLayout(self._layout)

        self.setAutoFillBackground(True)
        self._layout.addWidget(self._buttonNewProfile)
        self._layout.addWidget(self._buttonStop)
        self._layout.addWidget(self._buttonSave)

        self._layout.addStretch(1)

    def _setProfileWidgetEnabled(self):
        self._viewController.profileWidgetEnabled = True
        self._viewController.profileWidgetCallback.setPrimaryImageData = \
            lambda *args, **kwargs: self._drawImageProfile(0, *args, **kwargs, pen=mkPen(width=1, color=[125, 125, 125]))
        self._viewController.profileWidgetCallback.setSecondaryImageData = \
            lambda *args, **kwargs: self._drawImageProfile(1, *args, **kwargs, pen=mkPen(width=1, color=[255, 255, 255]))
        self._viewController.profileWidgetCallback.setContourData = \
            lambda *args, **kwargs: self._drawContourProfiles(*args, **kwargs)

    def _drawImageProfile(self, ind, *args, name='', **kwargs):
        self._profileViewer.drawProfile(ind, *args, **kwargs, name=name)

    def _drawContourProfiles(self, contourData, name=[], pen=[]):
        currentNbProfiles = self._profileViewer.count()
        for i in range(currentNbProfiles):
            if currentNbProfiles-i-1>1:
                self._profileViewer.drawProfile(currentNbProfiles-i-1, [0, 0], [0, 0])

        for i, n in enumerate(name):
            x, y = contourData[i]
            self._profileViewer.drawProfile(2+i, x, y, name=n, pen=pen[i])

    def _setProfileWidgetDisabled(self):
        self._viewController.profileWidgetEnabled = False
        self._viewController.profileWidgetCallback.setPrimaryImageData = lambda *args, **kwargs: None
        self._viewController.profileWidgetCallback.setSecondaryImageData = lambda *args, **kwargs: None
        self._viewController.profileWidgetCallback.setContourData = lambda *args, **kwargs: None
