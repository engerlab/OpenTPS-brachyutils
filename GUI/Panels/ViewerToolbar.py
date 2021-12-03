import os

from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QToolBar, QAction


class ViewerToolbar(QToolBar):
    def __init__(self, controller):
        QToolBar.__init__(self)

        self._controller = controller
        self.setIconSize(QSize(16, 16))

        iconPath = 'GUI' + os.path.sep + 'res' + os.path.sep + 'icons' + os.path.sep

        self._buttonChain = QAction(QIcon(iconPath+"chain.png"), "Crosshair", self)
        self._buttonChain.setStatusTip("Indepedent views")
        self._buttonChain.triggered.connect(self._handleButtonChain)
        self._buttonChain.setCheckable(True)

        self._buttonChain.setChecked(not self._controller.getIndependentViewsEnabled())

        self.addAction(self._buttonChain)

        # TODO: get independentViewsEnabled signal from controller

    def _handleButtonChain(self, pressed):
        # This is useful if controller emit a signal:
        if self._buttonChain.isChecked() != pressed:
            self._buttonChain.setChecked(pressed)
            return

        self._controller.setIndependentViewsEnabled(not pressed)
