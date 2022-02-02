import os

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QFrame, QMessageBox, QFileDialog, QLabel, QHBoxLayout

from Core.api import API
from GUI.Panels.scriptingPanel.scriptingWindow import ScriptingWindow


class ScriptingPanel(QWidget):
    newScriptingWindowSignal = pyqtSignal()

    def __init__(self):
        QWidget.__init__(self)

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        self.newScriptButton = QPushButton('New scripting window')
        self.newScriptButton.clicked.connect(self.newScriptingWindow)
        self.layout.addWidget(self.newScriptButton)

        self.filesFrame = QFrame()
        self.filesFrame.setFrameShape(QFrame.StyledPanel)
        self.layout.addWidget(self.filesFrame)

        self.filesLayout = QVBoxLayout()
        self.filesLayout.setContentsMargins(0, 0, 0, 0)
        self.filesFrame.setLayout(self.filesLayout)

        self.newScriptFileButton = QPushButton('Select new script file')
        self.newScriptFileButton.clicked.connect(self.newScriptFile)
        self.layout.addWidget(self.newScriptFileButton)

        self.layout.addStretch()

    def newScriptFile(self):
        self.newScriptFile = ScriptingFileView()
        self.filesLayout.addWidget(self.newScriptFile)

    def newScriptingWindow(self):
        self.scriptingWindow = ScriptingWindow()
        self.scriptingWindow.show()


class ScriptingFileView(QWidget):
    _scriptPath = None

    def __init__(self):
        QWidget.__init__(self)

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        self.topFrame = QFrame()
        self.topFrame.setFrameShape(QFrame.StyledPanel)
        self.layout.addWidget(self.topFrame)

        self.bottomFrame = QFrame()
        self.bottomFrame.setFrameShape(QFrame.StyledPanel)
        self.layout.addWidget(self.bottomFrame)

        topLayout = QHBoxLayout()
        topLayout.setContentsMargins(0, 0, 0, 0)
        self.topFrame.setLayout(topLayout)

        bottomLayout = QHBoxLayout()
        bottomLayout.setContentsMargins(0, 0, 0, 0)
        self.bottomFrame.setLayout(bottomLayout)

        closeButton = QPushButton('X')
        closeButton.clicked.connect(self.close)
        topLayout.addWidget(closeButton)

        self.newScriptFileButton = QPushButton('Select file')
        self.newScriptFileButton.clicked.connect(self.selectFile)
        topLayout.addWidget(self.newScriptFileButton)

        runButton = QPushButton('Run')
        runButton.clicked.connect(self.runFile)
        topLayout.addWidget(runButton)

        self.fileLabel = QLabel()
        bottomLayout.addWidget(self.fileLabel)

    def close(self):
        self.setParent(None)

    def runFile(self):
        msg = QMessageBox()
        msg.setWindowTitle(os.path.basename(self._scriptPath))
        msg.setIcon(QMessageBox.Information)

        try:
            with open(self._scriptPath, 'r') as file:
                code = file.read()

            output = API.run(code)
            msg.setText(output)
        except Exception as err:
            msg.setText(format(err))

        msg.exec_()

    def selectFile(self):
        self._scriptPath, _ = QFileDialog.getOpenFileName(self, "Select a python script", self._scriptPath, "python script (*.py)")

        self.fileLabel.setText(os.path.basename(self._scriptPath))
