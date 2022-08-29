import os

from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QToolBar, QAction, QMenu, QWidgetAction, QPushButton


class DataViewerToolbar(QToolBar):
    def __init__(self, dataViewer):
        QToolBar.__init__(self)

        self._dataViewer = dataViewer

        self.setIconSize(QSize(16, 16))

        iconPath = 'GUI' + os.path.sep + 'res' + os.path.sep + 'icons' + os.path.sep

        self._buttonDVH = QAction(QIcon(iconPath + "dvh.png"), "DVH", self)
        self._buttonDVH.setStatusTip("DVH")
        self._buttonDVH.triggered.connect(self._handleButtonDVH)
        self._buttonDVH.setCheckable(True)

        self._buttonProfile = QAction(QIcon(iconPath + "profile.png"), "Graph", self)
        self._buttonProfile.setStatusTip("Graph")
        self._buttonProfile.triggered.connect(self._handleButtonGraph)
        self._buttonProfile.setCheckable(True)

        self._buttonViewer = QAction(QIcon(iconPath + "x-ray.png"), "Image viewer", self)
        self._buttonViewer.setStatusTip("Image viewer")
        self._buttonViewer.triggered.connect(self._handleButtonViewer)
        self._buttonViewer.setCheckable(True)

        self.addAction(self._buttonViewer)
        self.addAction(self._buttonProfile)
        self.addAction(self._buttonDVH)

        self._menuButton = QPushButton("Tools", self)
        self._menu = QMenu(self._menuButton)
        self._menuButton.setMenu(self._menu)
        self._menuAction = QWidgetAction(None)
        self._menuAction.setDefaultWidget(self._menuButton)
        self.addAction(self._menuAction)

        self._dataViewer.displayTypeChangedSignal.connect(self._handleDisplayTypeChange)

    @property
    def toolsMenu(self) -> QMenu:
        return self._menu

    def _handleButtonDVH(self, pressed):
        if pressed:
            self._dataViewer.displayType = self._dataViewer.DisplayTypes.DISPLAY_DVH

    def _handleButtonGraph(self, pressed):
        if pressed:
            self._dataViewer.displayType = self._dataViewer.DisplayTypes.DISPLAY_PROFILE

    def _handleButtonViewer(self, pressed):
        if pressed:
            self._dataViewer.displayType = self._dataViewer.DisplayTypes.DISPLAY_IMAGE

    def _handleDisplayTypeChange(self, displayType):
        self._uncheckAllDisplayButton()

        if displayType == self._dataViewer.DisplayTypes.DISPLAY_DVH:
            self._buttonDVH.setChecked(True)
        elif displayType == self._dataViewer.DisplayTypes.DISPLAY_PROFILE:
            self._buttonProfile.setChecked(True)
        elif displayType == self._dataViewer.DisplayTypes.DISPLAY_IMAGE3D:
            self._buttonViewer.setChecked(True)

    def _uncheckAllDisplayButton(self):
        self._buttonDVH.setChecked(False)
        self._buttonProfile.setChecked(False)
        self._buttonViewer.setChecked(False)
