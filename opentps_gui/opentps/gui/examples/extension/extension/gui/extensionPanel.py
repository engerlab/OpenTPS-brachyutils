from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton

class ExtensionPanel(QWidget):
  def __init__(self, viewController):
    QWidget.__init__(self)

    self._viewController = viewController

    self._layout = QVBoxLayout()
    self.setLayout(self._layout)

    self.flashTPSButton = QPushButton("This button does nothing")
    self._layout.addWidget(self.flashTPSButton)
