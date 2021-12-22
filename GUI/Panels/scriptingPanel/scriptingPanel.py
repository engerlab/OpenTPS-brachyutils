from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QFrame

from GUI.Panels.scriptingPanel.scriptingWindow import ScriptingWindow


class ScriptingPanel(QWidget):
    newScriptingWindowSignal = pyqtSignal()

    def __init__(self):
        QWidget.__init__(self)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.newScriptButton = QPushButton('New scripting window')
        self.newScriptButton.clicked.connect(self.newScriptingWindowSignal.emit)
        self.layout.addWidget(self.newScriptButton)

        # self.filesFrame = QFrame()
        # self.filesFrame.setFrameShape(QFrame.StyledPanel)
        # self.layout.addWidget(self.filesFrame)
        #
        # self.filesLayout = QVBoxLayout()
        # self.filesFrame.setLayout(self.filesLayout)
        #
        # self.newScriptFileButton = QPushButton('Select new script file')
        # self.newScriptFileButton.clicked.connect(self.newScriptFile)
        # self.layout.addWidget(self.newScriptFileButton)

        self.layout.addStretch()

    def newScriptFile(self):
        pass
        # self.newScriptFile = ScriptingFileView(self._PatientList, self._toolbox_width)
        # self.filesLayout.addWidget(self.newScriptFile)

    def run(self):
        pass
