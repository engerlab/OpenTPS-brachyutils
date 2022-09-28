from PyQt5.QtWidgets import QWidget, QSplitter, QHBoxLayout, QPushButton, QTextEdit, QStatusBar
from PyQt5.QtCore import Qt

from opentps.core import APIInterpreter
from opentps.gui.panels.scriptingPanel.pythonHighlighter import PythonHighlighter


class ScriptingWindow(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self.setWindowTitle('Script')

        layout = QHBoxLayout()
        self.setLayout(layout)

        horizontalSplitter = QSplitter(Qt.Horizontal)
        verticalSplitter = QSplitter(Qt.Vertical)
        verticalSplitter.addWidget(horizontalSplitter)

        layout.addWidget(verticalSplitter)

        self._runButton = QPushButton('Run')
        self._runButton.clicked.connect(self._runCode)

        self._statusBar = QStatusBar()

        verticalSplitter.addWidget(self._runButton)
        verticalSplitter.addWidget(self._statusBar)

        self._codeTextEdit = QTextEdit()
        PythonHighlighter(self._codeTextEdit)

        self._stdOutput = QTextEdit()
        self._stdOutput.setReadOnly(True)

        horizontalSplitter.addWidget(self._codeTextEdit)
        horizontalSplitter.addWidget(self._stdOutput)


    def _runCode(self):
        try:
            self._statusBar.showMessage("Executing...")

            output = APIInterpreter.run(self._getCode())
            self._stdOutput.setText(output)

            self._statusBar.showMessage("Done.")
        except Exception as err:
            self._statusBar.showMessage(format(err))

    def _getCode(self):
        return self._codeTextEdit.toPlainText()