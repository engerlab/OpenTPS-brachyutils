from enum import Enum
from typing import Sequence

from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QButtonGroup, QRadioButton, QTableWidget, \
    QFileDialog, QPushButton

from Core.IO import dataExporter


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

        self._workspaceField = ExportTable(parent=self)
        self._layout.addWidget(self._workspaceField)

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

        dataExporter.exportPatientAsDicom(self._viewController.currentPatient, folderpath)


class ExportTypes(Enum):
    DICOM = "Dicom"
    MHD = "MHD"
    MCSQUARE = "MCsquare"
    PICKLE = "Pickle"

class DataType:
    def __init__(self, name:str, exportTypes:Sequence):
        self.name = name
        self.exportTypes = exportTypes

class DataTypes:
    def __init__(self):
        self._types = [DataType("Image", [ExportTypes.DICOM, ExportTypes.MHD, ExportTypes.MCSQUARE, ExportTypes.PICKLE]),
                       DataType("Dose", [ExportTypes.DICOM, ExportTypes.MHD, ExportTypes.PICKLE]),
                       DataType("Plan", [ExportTypes.DICOM, ExportTypes.MCSQUARE, ExportTypes.PICKLE]),
                       DataType("Contours", [ExportTypes.DICOM, ExportTypes.MHD, ExportTypes.PICKLE]),
                       DataType("Other", [ExportTypes.DICOM, ExportTypes.MHD, ExportTypes.MCSQUARE, ExportTypes.PICKLE])]

    def __len__(self):
        return len(self._types)

    def __getitem__(self, item):
        return self._types[item]

class ExportTable(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        dataTypes = DataTypes()
        exportTypes = [ExportTypes.DICOM, ExportTypes.MHD, ExportTypes.MCSQUARE, ExportTypes.PICKLE]

        rowNb = len(dataTypes)
        colNb = len(exportTypes)

        self.table = QTableWidget()
        self.table.setRowCount(rowNb)
        self.table.setColumnCount(colNb)
        self.table.setHorizontalHeaderLabels([exportType.value for exportType in exportTypes])
        self.table.setVerticalHeaderLabels([dataType.name for dataType in dataTypes])

        self.table.setFixedWidth((colNb+1)*self.table.columnWidth(0))

        self._layout = QHBoxLayout(self)
        self._layout.addWidget(self.table)

        for row, dataType in enumerate(dataTypes):
            button_group = QButtonGroup(self)
            button_group.setExclusive(True)

            dataTypeHasOneOptionChecked = False
            for col, exportType in enumerate(exportTypes):
                checkbox = QRadioButton()
                button_group.addButton(checkbox)
                self.table.setCellWidget(row, col, checkbox)

                if exportType in dataType.exportTypes:
                    checkbox.setEnabled(True)
                    if not dataTypeHasOneOptionChecked:
                        checkbox.setChecked(True)
                        dataTypeHasOneOptionChecked = True
                    else:
                        checkbox.setChecked(False)
                else:
                    checkbox.setChecked(False)
                    checkbox.setEnabled(False)
