from PyQt5.QtWidgets import QVBoxLayout, QLabel, QLineEdit, QMainWindow, QWidget, QPushButton, QHBoxLayout


class ProgramSettingEditor(QMainWindow):
    def __init__(self, mainConfig, parent=None):
        super().__init__(parent=parent)

        self._mainConfig  = mainConfig

        self.setWindowTitle('Program settings')
        self.resize(400, 400)

        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        self._layout = QVBoxLayout()
        centralWidget.setLayout(self._layout)

        self._workspaceField = self.EditableSetting("Workspace", str(self._mainConfig.workspace), self.setWorkspace)

        self._layout.addWidget(self._workspaceField)

    def setWorkspace(self, text):
        self._mainConfig.workspace = text

    class EditableSetting(QWidget):
        def __init__(self, property, value, action, parent=None):
            super().__init__(parent)

            self._mainLayout = QHBoxLayout(self)
            self.setLayout(self._mainLayout)

            self._txt = QLabel(self)
            self._txt.setText(property)

            self._nameLineEdit = QLineEdit(self)

            self._validateButton = QPushButton(self)
            self._validateButton.setText("Validate")
            self._validateButton.clicked.connect(lambda *args : action(self._nameLineEdit.text()))

            self._nameLineEdit.setText(str(value))
            self._txt.setBuddy(self._nameLineEdit)

            self._mainLayout.addWidget(self._txt)
            self._mainLayout.addWidget(self._nameLineEdit)
            self._mainLayout.addWidget(self._validateButton)