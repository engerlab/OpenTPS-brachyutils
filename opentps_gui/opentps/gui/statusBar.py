from PyQt5.QtWidgets import QStatusBar

class StatusBar(QStatusBar):
    def __init__(self):
        QStatusBar.__init__(self)

    def setInstructionText(self, txt):
        self.showMessage(txt)
