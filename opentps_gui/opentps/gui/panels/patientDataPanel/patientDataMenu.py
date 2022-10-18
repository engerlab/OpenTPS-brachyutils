
import copy
from typing import Sequence, Optional

from PyQt5.QtCore import QDir
from PyQt5.QtWidgets import QLineEdit, QMenu, QAction, QInputDialog, QMessageBox, QMainWindow

from pydicom.uid import generate_uid

from opentps.core.data.images import CTImage
from opentps.core.data.images._image3D import Image3D
from opentps.core.data.dynamicData._dynamic3DSequence import Dynamic3DSequence
from opentps.core.data.dynamicData._dynamic3DModel import Dynamic3DModel
from opentps.core.data import PatientData
from opentps.core.io.serializedObjectIO import saveSerializedObjects
from opentps.gui.viewer.dataViewerComponents.patientDataPropertyEditor import PatientDataPropertyEditor


class PatientDataMenu:
    def __init__(self, viewController, parent=None):
        self._actions = []
        self._contextMenu = QMenu(parent)
        self._selectedData = None
        self._viewController = viewController

        self.dataPath = QDir.currentPath()  # maybe not the ideal default data directory

    @property
    def selectedData(self) -> Optional[Sequence[PatientData]]:
        return self._selectedData

    @selectedData.setter
    def selectedData(self, selectedData:Sequence[PatientData]):
        self._selectedData = selectedData

        self._buildMenu()

    def _buildMenu(self):
        self._actions = []

        dataClass = self._selectedData[0].__class__
        for data in self._selectedData:
            if data.__class__ != dataClass:
                dataClass = 'mixed'
                break

        if (len(self._selectedData) > 0):
            if len(self._selectedData)==1:
                self.rename_action = QAction("Rename")
                self.rename_action.triggered.connect(lambda checked: self._openRenameDataDialog(self._selectedData[0]))
                self._actions.append(self.rename_action)

                self.copy_action = QAction("Copy")
                self.copy_action.triggered.connect(lambda checked: self._copyData(self._selectedData[0]))
                self._actions.append(self.copy_action)

                self.info_action = QAction("Info")
                self.info_action.triggered.connect(lambda checked: self._showImageInfo(self._selectedData[0]))
                self._actions.append(self.info_action)

            if not dataClass == 'mixed':
                # actions for 3D images
                if (dataClass == Image3D or issubclass(dataClass, Image3D)) and len(self._selectedData) == 1:
                    self.superimpose_action = QAction("Superimpose")
                    self.superimpose_action.triggered.connect(lambda checked: self._setSecondaryImage(self._selectedData[0]))
                    self._actions.append(self.superimpose_action)

                # actions for group of 3DImage
                if (dataClass == CTImage or issubclass(dataClass, CTImage)) and len(self._selectedData) > 1:  # to generalize to other modalities eventually
                    self.make_series_action = QAction("Make dynamic 3D sequence")
                    self.make_series_action.triggered.connect(lambda checked: self._createDynamic3DSequence(self._selectedData))
                    self._actions.append(self.make_series_action)

            if dataClass == 'mixed':
                self.no_action = QAction("No action available for this group of data")
                self.context_menu.addAction(self.no_action)

            # actions for single Dynamic3DSequence
            if (dataClass == Dynamic3DSequence and len(self._selectedData) == 1):  # or dataClass == 'Dynamic2DSequence'):
                self.compute3DModelAction = QAction("Compute 4D model (MidP)")
                self.compute3DModelAction.triggered.connect(lambda checked, selected3DSequence=self._selectedData[0]: self._computeDynamic3DModel(selected3DSequence))
                self._actions.append(self.compute3DModelAction)

            self.delete_action = QAction("Delete")
            self.delete_action.triggered.connect(lambda checked: self._openDeleteDataDialog(self._selectedData))
            self._actions.append(self.delete_action)

            self.export_action = QAction("Export serialized")
            self.export_action.triggered.connect(lambda checked, selectedData=self._selectedData: self._exportSerializedData(selectedData))
            self._actions.append(self.export_action)

    def asContextMenu(self) -> QMenu:
        for action in self._actions:
            self._contextMenu.addAction(action)

        return self._contextMenu

    def _setSecondaryImage(self, image):
        self._viewController.secondaryImage = image

    def _copyData(self, selectedData):
        new_img = copy.deepcopy(selectedData)
        # new_img.patient = selectedData
        new_img.name = selectedData.name + '_copy'
        new_img.patient = selectedData.patient

    def _createDynamic3DSequence(self, selectedImages):
        newName, okPressed = QInputDialog.getText(None, "Set series name", "Series name:", QLineEdit.Normal, "4DCT")

        if (okPressed):
            Dynamic3DSequence.fromImagesInPatientList(selectedImages, newName)

    def _computeDynamic3DModel(self, selected3DSequence):
        newName, okPressed = QInputDialog.getText(None, "Set dynamic 3D model name", "3D model name:", QLineEdit.Normal, "MidP")

        if (okPressed):
            newMod = Dynamic3DModel()
            newMod.name = newName
            newMod.seriesInstanceUID = generate_uid()
            newMod.computeMidPositionImage(selected3DSequence)
            self._viewController.currentPatient.appendPatientData(newMod)

    def _openRenameDataDialog(self, data):
        text, ok = QInputDialog.getText(None, 'Rename data', 'New name:', text=data.name)
        if ok:
            data.name = str(text)

    def _openDeleteDataDialog(self, data):
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText("Delete data")
        msgBox.setWindowTitle("Delete selected data?")
        msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)

        if msgBox.exec() == QMessageBox.Ok:
            for dataItem in data:
                dataItem.patient.removePatientData(dataItem)

    def _showImageInfo(self, image):
        w = QMainWindow(self._contextMenu.parent())
        w.setWindowTitle('Image info')
        w.resize(400, 400)
        w.setCentralWidget(PatientDataPropertyEditor(image, self._contextMenu.parent()))
        w.show()

    def _exportSerializedData(self, selectedData):
        from opentps.gui.panels.patientDataPanel.patientDataPanel import SaveData_dialog
        fileDialog = SaveData_dialog()
        savingPath, compressedBool, splitPatientsBool = fileDialog.getSaveFileName(None, dir=self.dataPath)

        saveSerializedObjects(selectedData, savingPath, compressedBool=compressedBool)
