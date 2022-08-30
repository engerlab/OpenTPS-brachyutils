from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel


class BlackEmptyPlot(QWidget):
    def __init__(self, parent):
        super().__init__(parent)

        self._layout = QHBoxLayout()
        self.setLayout(self._layout)

        self._layout.addStretch(1)
        self.setContentsMargins(0, 0, 0, 0)

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet('background-color: black')