from PyQt5.QtWidgets import QStatusBar, QPushButton

from Core.api import API, APILogger


class StatusBar(QStatusBar):
    def __init__(self):
        QStatusBar.__init__(self)

        API.appendLoggingFunction(self.setInstructionText)


    def setInstructionText(self, txt):
        self.showMessage(txt)
