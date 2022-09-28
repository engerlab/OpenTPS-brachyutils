
import os

from PyQt5.QtCore import QSize, QDir
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QToolBar, QAction, QDialog, QPushButton, QLineEdit, QVBoxLayout, QFileDialog, \
    QStackedWidget, QListView, QComboBox, QWidgetAction

from opentps.core.io import dataLoader
from opentps.core import Event
from opentps.gui.viewer.dataViewer import DataViewer
from opentps.gui.viewer.exportWindow import ExportWindow
from opentps.gui.tools._cropTool import CropWidget
from opentps.gui.tools._resampleTool import ResampleWidget
from opentps.gui.programSettingEditor import ProgramSettingEditor

import opentps.gui.res.icons as IconModule

class ViewerToolbar(QToolBar):

    PLAY_STATUS = 1
    PAUSE_STATUS = 0

    def __init__(self, viewController, parent=None):
        super().__init__(parent)

        self._viewController = viewController
        self._cropWidgets = []
        self._resampleWidgets = []

        self.setIconSize(QSize(16, 16))

        self.iconPath = str(IconModule.__path__[0]) + os.path.sep

        self._buttonSettings = QAction(QIcon(self.iconPath + "settings-5-line.png"), "Settings", self)
        self._buttonSettings.triggered.connect(self._openSettings)

        self._buttonOpen = QAction(QIcon(self.iconPath + "folder-open.png"), "Open files or folder", self)
        self._buttonOpen.setStatusTip("Open files or folder")
        self._buttonOpen.triggered.connect(self._handleLoadData)
        self._buttonOpen.setCheckable(False)

        self._buttonSave = QAction(QIcon(self.iconPath + "save.png"), "Export", self)
        self._buttonSave.triggered.connect(self._handleExportData)

        self._buttonIndependentViews = QAction(QIcon(self.iconPath + "independent_views.png"), "Independent views", self)
        self._buttonIndependentViews.setStatusTip("Independent views")
        self._buttonIndependentViews.triggered.connect(self._handleButtonIndependentViews)
        self._buttonIndependentViews.setCheckable(True)
        self._buttonIndependentViews.setChecked(self._viewController.independentViewsEnabled)

        self._buttonWindowLevel = QAction(QIcon(self.iconPath + "contrast.png"), "Window level", self)
        self._buttonWindowLevel.setStatusTip("Window level")
        self._buttonWindowLevel.triggered.connect(self._handleWindowLevel)
        self._buttonWindowLevel.setCheckable(True)

        self._buttonCrossHair = QAction(QIcon(self.iconPath + "geolocation.png"), "Crosshair", self)
        self._buttonCrossHair.setStatusTip("Crosshair")
        self._buttonCrossHair.triggered.connect(self._handleCrossHair)
        self._buttonCrossHair.setCheckable(True)

        self._buttonCrop = QAction(QIcon(self.iconPath + "crop.png"), "Crop", self)
        self._buttonCrop.setStatusTip("Crop")
        self._buttonCrop.triggered.connect(self._handleCrop)
        self._buttonCrop.setCheckable(False)

        self._buttonResample = QAction(QIcon(self.iconPath + "resample.png"), "Resample", self)
        self._buttonResample.setStatusTip("Resample")
        self._buttonResample.triggered.connect(self._handleResample)
        self._buttonResample.setCheckable(False)

        self._dropModeCombo = QComboBox()
        self._dropModeToStr = {DataViewer.DropModes.AUTO: 'Drop mode: auto',
                               DataViewer.DropModes.PRIMARY: 'Drop as primary image',
                               DataViewer.DropModes.SECONDARY: 'Drop as secondaryImage'}
        self._strToDropMode = {v: k for k, v in self._dropModeToStr.items()}
        self._dropModeCombo.addItems(list(self._dropModeToStr.values()))
        self._dropModeCombo.setCurrentIndex(self._dropModeToIndex(self._viewController.dropMode))
        self._dropModeCombo.currentIndexChanged.connect(self._handleDropModeSelection)
        self._dropModeAction = QWidgetAction(None)
        self._dropModeAction.setDefaultWidget(self._dropModeCombo)

        self.addAction(self._buttonSettings)
        self.addAction(self._buttonOpen)
        self.addAction(self._buttonSave)
        self.addAction(self._buttonIndependentViews)
        self.addAction(self._buttonCrossHair)
        self.addAction(self._buttonWindowLevel)
        self.addAction(self._buttonCrop)
        self.addAction(self._buttonResample)
        self.addAction(self._dropModeAction)

        self.addSeparator()

        ## dynamic options buttons
        self._buttonFaster = QAction(QIcon(self.iconPath + "fast.png"), "Faster", self)
        self._buttonFaster.setStatusTip("Speed up the dynamic viewers evolution")
        self._buttonFaster.triggered.connect(self._handleFaster)

        self._buttonSlower = QAction(QIcon(self.iconPath + "slow.png"), "Slower", self)
        self._buttonSlower.setStatusTip("Slows the dynamic viewers evolution")
        self._buttonSlower.triggered.connect(self._handleSlower)

        self._buttonPlayPause = QAction(QIcon(self.iconPath + "play.png"), "Play/Pause", self)
        self._buttonPlayPause.setStatusTip("Classical Play Pause of course")
        self._buttonPlayPause.triggered.connect(self._handlePlayPause)
        self.playPauseStatus = self.PLAY_STATUS

        self._buttonRefreshRate = QAction('RR', self)
        self._buttonRefreshRate.setStatusTip("Change the refresh rate of the dynamic viewers")
        self._buttonRefreshRate.triggered.connect(self._handleRefreshRate)

        self.fasterSignal = Event()
        self.slowerSignal = Event()
        self.playPauseSignal = Event(bool)
        self.refreshRateChangedSignal = Event(float)
        self.refreshRateValue = 24
        # self.addDynamicButtons()

        self._viewController.independentViewsEnabledSignal.connect(self._handleButtonIndependentViews)
        self._viewController.windowLevelEnabledSignal.connect(self._handleWindowLevel)
        self._viewController.crossHairEnabledSignal.connect(self._handleCrossHair)

    def _dropModeToIndex(self, dropMode):
        return list(self._dropModeToStr.keys()).index(dropMode)

    def _indexToDropMode(self, index):
        return list(self._dropModeToStr.keys())[index]

    def _handleDropModeSelection(self, selectionIndex):
        self._viewController.dropMode = self._indexToDropMode(selectionIndex)

    def _openSettings(self, pressed):
        self._settingEditor = ProgramSettingEditor()
        self._settingEditor.show()

    def _handleButtonIndependentViews(self, pressed):
        # This is useful if controller emit a signal:
        if self._buttonIndependentViews.isChecked() != pressed:
            self._buttonIndependentViews.setChecked(pressed)
            return

        self._viewController.independentViewsEnabled = pressed

    def _handleCrossHair(self, pressed):
        # This is useful if controller emit a signal:
        if self._buttonCrossHair.isChecked() != pressed:
            self._buttonCrossHair.setChecked(pressed)
            return

        self._viewController.crossHairEnabled = pressed

    def _handleCrop(self):
        cw = CropWidget(self._viewController)
        # TODO
        # I don't know why but we must keep the reference to any CropWidget created even if we close it
        # This is an issue because _cropWidgets might become huge
        self._cropWidgets.append(cw)
        cw.show()

    def _handleResample(self):
        rw = ResampleWidget(self._viewController)
        self._resampleWidgets.append(rw)
        rw.show()

    def _handleLoadData(self):
        filesOrFoldersList = self._getOpenFilesAndDirs(caption="Open patient data files or folders",
                                                  directory=QDir.currentPath())
        if len(filesOrFoldersList) < 1:
            return

        splitPath = filesOrFoldersList[0].split('/')
        withoutLastElementPath = ''
        for element in splitPath[:-1]:
            withoutLastElementPath += element + '/'
        self.dataPath = withoutLastElementPath

        dataLoader.loadData(self._viewController._patientList, filesOrFoldersList)

    def _handleExportData(self):
        self._exportWindow = ExportWindow(self._viewController)
        self._exportWindow.show()

    def _handleWindowLevel(self, pressed):
        # This is useful if controller emit a signal:
        if self._buttonWindowLevel.isChecked() != pressed:
            self._buttonWindowLevel.setChecked(pressed)
            return

        self._viewController.windowLevelEnabled = pressed

    def addDynamicButtons(self):

        self.addAction(self._buttonSlower)
        self.addAction(self._buttonPlayPause)
        self._buttonPlayPause.setIcon(QIcon(self.iconPath + "pause.jpg"))
        self.addAction(self._buttonFaster)
        self.addAction(self._buttonRefreshRate)

    def removeDynamicButtons(self):

        self.removeAction(self._buttonSlower)
        self.removeAction(self._buttonPlayPause)
        self.removeAction(self._buttonFaster)
        self.removeAction(self._buttonRefreshRate)

    def _handleFaster(self):
        self.fasterSignal.emit()


    def _handleSlower(self):
        self.slowerSignal.emit()


    def _handlePlayPause(self):
        self.playPauseStatus = not self.playPauseStatus

        if self.playPauseStatus:
            self._buttonPlayPause.setIcon(QIcon(self.iconPath + "pause.jpg"))
        elif not self.playPauseStatus:
            self._buttonPlayPause.setIcon(QIcon(self.iconPath + "play.png"))

        self.playPauseSignal.emit(self.playPauseStatus)


    def _handleRefreshRate(self):

        refreshRateDialog = RefreshRateDialog(self.refreshRateValue)

        if (refreshRateDialog.exec()):
            self.refreshRateValue = float(refreshRateDialog.rRValueLine.text())
            self.refreshRateChangedSignal.emit(self.refreshRateValue)

    # TODO : this is duplicated from patientDataPanel
    def _getOpenFilesAndDirs(self, parent=None, caption='', directory='',
                             filter='', initialFilter='', options=None):
        def updateText():
            # update the contents of the line edit widget with the selected files
            selected = []
            for index in view.selectionModel().selectedRows():
                selected.append('"{}"'.format(index.data()))
            lineEdit.setText(' '.join(selected))

        dialog = QFileDialog(parent, windowTitle=caption)
        dialog.setFileMode(dialog.ExistingFiles)
        if options:
            dialog.setOptions(options)
        dialog.setOption(dialog.DontUseNativeDialog, True)
        if directory:
            dialog.setDirectory(directory)
        if filter:
            dialog.setNameFilter(filter)
            if initialFilter:
                dialog.selectNameFilter(initialFilter)

        # by default, if a directory is opened in file listing mode,
        # QFileDialog.accept() shows the contents of that directory, but we
        # need to be able to "open" directories as we can do with files, so we
        # just override accept() with the default QDialog implementation which
        # will just return exec_()
        dialog.accept = lambda: QDialog.accept(dialog)

        # there are many item views in a non-native dialog, but the ones displaying
        # the actual contents are created inside a QStackedWidget; they are a
        # QTreeView and a QListView, and the tree is only used when the
        # viewMode is set to QFileDialog.Details, which is not this case
        stackedWidget = dialog.findChild(QStackedWidget)
        view = stackedWidget.findChild(QListView)
        view.selectionModel().selectionChanged.connect(updateText)

        lineEdit = dialog.findChild(QLineEdit)
        # clear the line edit contents whenever the current directory changes
        dialog.directoryEntered.connect(lambda: lineEdit.setText(''))

        dialog.exec_()
        return dialog.selectedFiles()


class RefreshRateDialog(QDialog):

    def __init__(self, refreshRateValue):
        QDialog.__init__(self)

        self.RRVal = refreshRateValue

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        # self.slider = QScrollBar(self)   ## to select the refresh rate with a scroll bar, not used for now
        # self.slider.setOrientation(Qt.Horizontal)
        # self.slider.sliderMoved.connect(self.sliderval)
        # self.main_layout.addWidget(self.slider)

        self.rRValueLine = QLineEdit(str(self.RRVal))
        self.main_layout.addWidget(self.rRValueLine)

        okButton = QPushButton("ok", self)
        okButton.clicked.connect(self.accept)
        self.main_layout.addWidget(okButton)


    def sliderval(self):
        # getting current position of the slider
        value = self.slider.sliderPosition()
