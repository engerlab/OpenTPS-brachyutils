import functools

from PyQt5.QtWidgets import QVBoxLayout, QLabel, QLineEdit, QMainWindow, QWidget, QPushButton, QHBoxLayout, QCheckBox

from opentps.core.processing.doseCalculation.doseCalculationConfig import DoseCalculationConfig
from opentps.gui.panels.mainToolbar import MainToolbar
from opentps.core.utils.programSettings import ProgramSettings


class EditableSetting(QWidget):
    def __init__(self, property, value, action, parent=None):
        super().__init__(parent)

        self._mainLayout = QHBoxLayout(self)
        self.setLayout(self._mainLayout)

        if not (property is None or property==""):
            self._txt = QLabel(self)
            self._txt.setText(property)
            self._mainLayout.addWidget(self._txt)

        self._nameLineEdit = QLineEdit(self)

        self._validateButton = QPushButton(self)
        self._validateButton.setText("Validate")
        self._validateButton.clicked.connect(lambda *args: action(self._nameLineEdit.text()))

        self._nameLineEdit.setText(str(value))

        if not (property is None or property == ""):
            self._txt.setBuddy(self._nameLineEdit)

        self._mainLayout.addWidget(self._nameLineEdit)
        self._mainLayout.addWidget(self._validateButton)

class ProgramSettingEditor(QMainWindow):
    # singleton class!

    _staticVars = {"programSettings": None, "mainToolbar": None}

    def __init__(self):
        super().__init__()

        self.setWindowTitle('Program settings')
        self.resize(400, 400)

        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        self._layout = QVBoxLayout()
        centralWidget.setLayout(self._layout)

        self._workspaceField = EditableSetting("Workspace", str(self.programSettings.workspace), self.setWorkspace)
        self._layout.addWidget(self._workspaceField)

        self._machineParam = MCsquareConfigEditor()
        self._layout.addWidget(self._machineParam)

        self._activeExtensions = ActiveExtensions(self.mainToolbar)
        self._layout.addWidget(self._activeExtensions)

    @property
    def programSettings(self) -> ProgramSettings:
        return self._staticVars["programSettings"]

    @staticmethod
    def setProgramSettings(config):
        ProgramSettingEditor._staticVars["programSettings"] = config

    @property
    def mainToolbar(self):
        return self._staticVars["mainToolbar"]

    @staticmethod
    def setMainToolbar(mainToolbar):
        ProgramSettingEditor._staticVars["mainToolbar"] = mainToolbar

    def setWorkspace(self, text):
        self.programSettings.workspace = text


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

class MCsquareConfigEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._dcConfig = DoseCalculationConfig()

        self._layout = QVBoxLayout(self)
        self.setLayout(self._layout)

        self._txt = QLabel(self)
        self._txt.setText("Scanner folder")
        self._layout.addWidget(self._txt)
        self._scannerField = EditableSetting("", str(self._dcConfig.scannerFolder), self._setScanner)
        self._layout.addWidget(self._scannerField)

        self._txt2 = QLabel(self)
        self._txt2.setText("BDL file")
        self._layout.addWidget(self._txt2)
        self._bdlField = EditableSetting("", str(self._dcConfig.bdlFile), self._setBDL)
        self._layout.addWidget(self._bdlField)

    def _setScanner(self, text):
        self._dcConfig.scannerFolder = text

    def _setBDL(self, text):
        self._dcConfig.bdlFile = text