from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QButtonGroup, QRadioButton, QTableWidget, \
    QFileDialog, QPushButton

from opentps.core.io.dataExporter import ExportTypes, ExportConfig, exportPatient


class ExportWindow(QMainWindow):
    def __init__(self, viewController):
        super().__init__()

        self._viewController = viewController

        self.setWindowTitle('Export settings')
        self.resize(400, 400)

        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        self._layout = QVBoxLayout()
        centralWidget.setLayout(self._layout)

        self._exportTable = ExportTable(parent=self)
        self._layout.addWidget(self._exportTable)

        self._exportButton = QPushButton("Select folder and export")
        self._exportButton.clicked.connect(self._handleExport)
        self._layout.addWidget(self._exportButton)

        self._layout.addStretch()
        self.adjustSize()
        self.setFixedSize(self.size())

    def _handleExport(self):
        # TODO: Use export options defined in ExportTable

        folderpath = QFileDialog.getExistingDirectory(self, 'Select folder')

        if folderpath == "":
            return

        exportPatient(self._viewController.currentPatient, folderpath, self._exportTable.exportConfig)

class ExportTable(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        dataTypes = ExportConfig()
        self._exportTypes = [ExportTypes.DICOM, ExportTypes.MHD, ExportTypes.MCSQUARE, ExportTypes.PICKLE]
        self._buttonGroups = []
        self._radio_buttons = {}  # To keep track of the state of radio buttons

        rowNb = len(dataTypes)
        colNb = len(self._exportTypes)

        self.table = QTableWidget()
        self.table.setRowCount(rowNb)
        self.table.setColumnCount(colNb)
        self.table.setHorizontalHeaderLabels([exportType.value for exportType in self._exportTypes])
        self.table.setVerticalHeaderLabels([dataType.name for dataType in dataTypes])

        self.table.setFixedWidth((colNb+1)*self.table.columnWidth(0))

        self._layout = QHBoxLayout(self)
        self._layout.addWidget(self.table)

        for row, dataType in enumerate(dataTypes):
            button_group = QButtonGroup(self)
            button_group.setExclusive(False) 
            self._buttonGroups.append(button_group)

            for col, exportType in enumerate(self._exportTypes):
                checkbox = QRadioButton()
                button_group.addButton(checkbox, col)
                self.table.setCellWidget(row, col, checkbox)

                if exportType in dataType.exportTypes:
                    checkbox.setEnabled(True)
                    checkbox.setChecked(False) 
                    self._radio_buttons[(row, col)] = checkbox  
                    checkbox.toggled.connect(lambda checked, cb=checkbox, bg=button_group: self._toggle_radio_button(cb, bg, checked))
                else:
                    checkbox.setChecked(False)
                    checkbox.setEnabled(False)

    def _toggle_radio_button(self, checkbox, button_group, checked):
        if not checked:
            return  

        for btn in button_group.buttons():
            if btn != checkbox:
                btn.setChecked(False)

    @property
    def exportConfig(self) -> ExportConfig:
        config = ExportConfig()

        for i, dataType in enumerate(config):
            checked_id = self._buttonGroups[i].checkedId()
            if checked_id != -1:
                dataType.exportType = self._exportTypes[checked_id]
            else:
                dataType.exportType = None

        return config