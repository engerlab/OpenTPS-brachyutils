from PyQt5.QtWidgets import QWidget, QSplitter, QHBoxLayout, QPushButton, QTextEdit, QStatusBar
from PyQt5.QtCore import Qt

from Controllers.api import API
from GUI.Panels.scriptingPanel.pythonHighlighter import PythonHighlighter


class ScriptingWindow(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self.setWindowTitle('Script')

        layout = QHBoxLayout()

        splitter1 = QSplitter(Qt.Horizontal)
        splitter1.setOrientation(Qt.Horizontal)

        splitter2 = QSplitter(Qt.Vertical)
        splitter1.setOrientation(Qt.Horizontal)
        splitter2.addWidget(splitter1)

        layout.addWidget(splitter2)


        self.newRunButton = QPushButton('Run')
        self.newRunButton.clicked.connect(self.run)
        splitter2.addWidget(self.newRunButton)

        self.textEdit = QTextEdit()
        highlighter = PythonHighlighter(self.textEdit)
        splitter1.addWidget(self.textEdit)

        self.stdOutput = QTextEdit()
        self.stdOutput.setReadOnly(True)
        splitter1.addWidget(self.stdOutput)

        self.statusBar = QStatusBar()
        splitter2.addWidget(self.statusBar)

        self.setLayout(layout)

    def run(self):
        try:
            self.statusBar.showMessage("Executing...")

            code = self.textEdit.toPlainText()

            output = API.run(code)
            self.stdOutput.setText(output)

            self.statusBar.showMessage("Done.")
        except Exception as err:
            self.statusBar.showMessage(format(err))

