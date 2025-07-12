import os

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QFrame, QMessageBox, QFileDialog, QLabel, QHBoxLayout

from opentps.core import APIInterpreter
from opentps.gui.panels.scriptingPanel.scriptingWindow import ScriptingWindow


class ScriptingPanel(QWidget):
    newScriptingWindowSignal = pyqtSignal()

    def __init__(self):
        QWidget.__init__(self)

        self._layout = QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

        self._newScriptingWindowButton = QPushButton('New scripting window')
        self._newScriptingWindowButton.clicked.connect(self.newScriptingWindow)
        self._layout.addWidget(self._newScriptingWindowButton)

        self._newScriptFileViewButton = QPushButton('Select new script file')
        self._newScriptFileViewButton.clicked.connect(self.newScriptFile)
        self._layout.addWidget(self._newScriptFileViewButton)

        self._scriptFileViewsFrame = QFrame()
        self._scriptFileViewsFrame.setFrameShape(QFrame.StyledPanel)
        self._layout.addWidget(self._scriptFileViewsFrame)

        self._scriptFileViewsLayout = QVBoxLayout()
        self._scriptFileViewsLayout.setContentsMargins(0, 0, 0, 0)
        self._scriptFileViewsFrame.setLayout(self._scriptFileViewsLayout)

        self._layout.addStretch()

    def newScriptingWindow(self):
        self.scriptingWindow = ScriptingWindow()
        self.scriptingWindow.show()

    def newScriptFile(self):
        self._scriptFileViewsLayout.addWidget(ScriptingFileView())


class ScriptingFileView(QWidget):
    _scriptPath = None

    def __init__(self):
        QWidget.__init__(self)

        self._layout = QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

        self._topFrame = QFrame()
        self._topFrame.setFrameShape(QFrame.StyledPanel)
        self._layout.addWidget(self._topFrame)

        self._bottomFrame = QFrame()
        self._bottomFrame.setFrameShape(QFrame.StyledPanel)
        self._layout.addWidget(self._bottomFrame)

        topLayout = QHBoxLayout()
        topLayout.setContentsMargins(0, 0, 0, 0)
        self._topFrame.setLayout(topLayout)

        bottomLayout = QHBoxLayout()
        bottomLayout.setContentsMargins(0, 0, 0, 0)
        self._bottomFrame.setLayout(bottomLayout)

        closeButton = QPushButton('X')
        closeButton.clicked.connect(self.close)

        selectFileButton = QPushButton('Select file')
        selectFileButton.clicked.connect(self._selectAndSetFile)

        runButton = QPushButton('Run')
        runButton.clicked.connect(self._runFile)

        topLayout.addWidget(closeButton)
        topLayout.addWidget(selectFileButton)
        topLayout.addWidget(runButton)

        self._fileNameLabel = QLabel()
        bottomLayout.addWidget(self._fileNameLabel)

    def close(self):
        self.setParent(None)

    def _selectAndSetFile(self):
        self._scriptPath = self._openFileSelection()
        self._setFileNameLabel()

    def _openFileSelection(self):
        filePath, _ = QFileDialog.getOpenFileName(self, "Select a python script", self._scriptPath, "python script (*.py)")
        return filePath

    def _setFileNameLabel(self):
        self._fileNameLabel.setText(os.path.basename(self._scriptPath))

    def _runFile(self):
        msg = QMessageBox()
        msg.setWindowTitle(os.path.basename(self._scriptPath))
        msg.setIcon(QMessageBox.Information)

        code = self._readFile()

        try:
            output = APIInterpreter.run(code)
            msg.setText(output)
        except Exception as err:
            msg.setText(format(err))
            raise err from err

        msg.exec_()

    def _readFile(self):
        code = ''

        with open(self._scriptPath, 'r') as file:
            code = file.read()

        return code
