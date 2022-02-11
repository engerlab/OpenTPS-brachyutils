from PyQt5.QtWidgets import QStatusBar, QPushButton

from Core.api import API, FileLogger


class StatusBar(QStatusBar):
    def __init__(self):
        QStatusBar.__init__(self)

        API.logger.appendLoggingFunction(self.setInstructionText)


    def setInstructionText(self, txt):
        self.showMessage(txt)
