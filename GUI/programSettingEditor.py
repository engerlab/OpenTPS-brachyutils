import functools

from PyQt5.QtWidgets import QVBoxLayout, QLabel, QLineEdit, QMainWindow, QWidget, QPushButton, QHBoxLayout, QCheckBox
from GUI.Panels.mainToolbar import MainToolbar


class ProgramSettingEditor(QMainWindow):
    # singleton class!

    _staticVars = {"mainConfig": None, "mainToolbar": None}

    def __init__(self):
        super().__init__()

        self.setWindowTitle('Program settings')
        self.resize(400, 400)

        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        self._layout = QVBoxLayout()
        centralWidget.setLayout(self._layout)

        self._workspaceField = self.EditableSetting("Workspace", str(self.mainConfig.workspace), self.setWorkspace)

        self._layout.addWidget(self._workspaceField)

        self._activeExtensions = ActiveExtensions(self.mainToolbar)
        self._layout.addWidget(self._activeExtensions)

    @property
    def mainConfig(self):
        return self._staticVars["mainConfig"]

    @staticmethod
    def setMainConfig(config):
        ProgramSettingEditor._staticVars["mainConfig"] = config

    @property
    def mainToolbar(self):
        return self._staticVars["mainToolbar"]

    @staticmethod
    def setMainToolbar(mainToolbar):
        ProgramSettingEditor._staticVars["mainToolbar"] = mainToolbar

    def setWorkspace(self, text):
        self.mainConfig.workspace = text

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


class ActiveExtensions(QWidget):
    def __init__(self, toolbar:MainToolbar):
        super().__init__()

        self._mainLayout = QVBoxLayout(self)
        self.setLayout(self._mainLayout)

        for item in toolbar.items:
            itemCheckBox = QCheckBox(item.panelName)
            itemCheckBox.setChecked(item.visible)
            itemCheckBox.setCheckable(True)
            itemCheckBox.clicked.connect(functools.partial(self._handleItemChecked, item))

            self._mainLayout.addWidget(itemCheckBox)

    def _handleItemChecked(self, item, checked):
        item.visible = checked
