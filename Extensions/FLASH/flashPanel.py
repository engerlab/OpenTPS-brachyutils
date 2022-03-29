from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton

from Extensions.FLASH.GUI.flashWindow import FlashWindow


class FlashPanel(QWidget):
  def __init__(self, viewController):
    QWidget.__init__(self)

    self._viewController = viewController

    self._layout = QVBoxLayout()
    self.setLayout(self._layout)

    self.flashTPSButton = QPushButton("FLASH TPS")
    self.flashTPSButton.clicked.connect(lambda: FlashWindow(self._viewController, parent=self).show())
    self._layout.addWidget(self.flashTPSButton)