from typing import Sequence

from PyQt5 import QtCore
from PyQt5.QtCore import QMimeData, Qt
from PyQt5.QtGui import QStandardItemModel, QDrag, QFont, QStandardItem, QColor
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox, QTreeView, QAbstractItemView

from opentps.core.data.dynamicData._dynamic2DSequence import Dynamic2DSequence
from opentps.core.data.dynamicData._dynamic3DModel import Dynamic3DModel
from opentps.core.data.dynamicData._dynamic3DSequence import Dynamic3DSequence

from opentps.core.data.images import CTImage
from opentps.core.data.images import DoseImage
from opentps.core.data.images import Image2D
from opentps.core.data.images._image3D import Image3D
from opentps.core.data.images import VectorField3D
from opentps.core.data.plan._rtPlan import RTPlan
from opentps.core.data import PatientData

from opentps.gui.panels.patientDataPanel.patientDataMenu import PatientDataMenu
from opentps.gui.viewer.dataViewer import DroppedObject


class PatientDataSelection(QWidget):
    def __init__(self, viewController, parent=None):
        super().__init__(parent)

        self._viewController = viewController

        self._mainLayout = QVBoxLayout(self)
        self.setLayout(self._mainLayout)

        self.patientBox = PatientComboBox(self._viewController)

        self._patientDataTree = PatientDataTree(self._viewController, self)

        self._mainLayout.addWidget(self.patientBox)
        self._mainLayout.addWidget(self._patientDataTree)

    @property
    def selectedData(self) -> Sequence[PatientData]:
        selected = self._patientDataTree.selectedIndexes()
        selectedData = [self._patientDataTree.model().itemFromIndex(selectedData).data for selectedData in selected]

        return selectedData

class PatientComboBox(QComboBox):
    def __init__(self, viewController):
        QComboBox.__init__(self)

        self._viewController = viewController

        self._viewController.patientAddedSignal.connect(self._addPatient)
        self._viewController.patientRemovedSignal.connect(self._removePatient)
        self._viewController.currentPatientChangedSignal.connect(self._setCurrentPatient)

        self.currentIndexChanged.connect(self._setCurrentPatientInVC)

        self._initialize()

    def closeEvent(self, QCloseEvent):
        self._viewController.patientAddedSignal.disconnect(self._addPatient)
        self._viewController.patientRemovedSignal.disconnect(self._removePatient)
        self._viewController.currentPatientChangedSignal.disconnect(self._setCurrentPatient)

        super().closeEvent(QCloseEvent)

    def _initialize(self):
        for patient in self._viewController.patientList:
            self._addPatient(patient)

    def _addPatient(self, patient):
        name = patient.name
        if name is None:
            name = 'None'

        self.addItem(name, patient)
        if self.count() == 1:
            self._viewController.currentPatient = patient

    def _removePatient(self, patient):
        self.removeItem(self.findData(patient))

    def _setCurrentPatient(self, patient):
        if patient == self.currentData():
            return

        self.setCurrentIndex(self.findData(patient))


    def _setCurrentPatientInVC(self, index):
        self._viewController.currentPatient = self.currentData()


## ------------------------------------------------------------------------------------------
class PatientDataTree(QTreeView):
    def __init__(self, viewController, patientDataPanel):
        QTreeView.__init__(self)

        self._currentPatient = None
        self.patientDataPanel = patientDataPanel
        self._viewController = viewController

        self.setHeaderHidden(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.viewport().installEventFilter(self)
        self.customContextMenuRequested.connect(self._handleRightClick)
        self.resizeColumnToContents(0)
        self.doubleClicked.connect(self._handleDoubleClick)
        self.treeModel = QStandardItemModel()
        self.setModel(self.treeModel)
        self.setColumnHidden(1, True)
        self.expandAll()

        self.buildDataTree(self._viewController.currentPatient)
        self._viewController.currentPatientChangedSignal.connect(self.buildDataTree)

        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)

    def closeEvent(self, QCloseEvent):
        self._disconnectCurrentPatientAndItems()
        self._viewController.currentPatientChangedSignal.disconnect(self.buildDataTree)

        super().closeEvent(QCloseEvent)

    def _appendData(self, data):
        if isinstance(data, Image3D) or isinstance(data, RTPlan) or isinstance(data, Dynamic3DSequence) or isinstance(data, Dynamic2DSequence):
            rootItem = PatientDataItem(data)
            self.rootNode.appendRow(rootItem)

            if isinstance(data, Dynamic3DSequence):
                for image in data.dyn3DImageList:
                    item = PatientDataItem(image)
                    rootItem.appendRow(item)
                self.rootNode.appendRow(rootItem)

            if isinstance(data, Dynamic2DSequence):
                for image in data.dyn2DImageList:
                    item = PatientDataItem(image)
                    rootItem.appendRow(item)
                self.rootNode.appendRow(rootItem)

    def _removeData(self, data):
        items = []

        for row in range(self.model().rowCount()):
            item = self.model().itemFromIndex(self.model().index(row, 0))
            items.append(item)

        for item in items:
            if item.data == data:
                self.rootNode.removeRow(item.row())
                item.disconnectAll() #Do this explicitely to be sure signals are disconnected

    def mouseMoveEvent(self, event):
        drag = QDrag(self)
        mimeData = QMimeData()

        mimeData.setText(DroppedObject.DropTypes.IMAGE)
        drag.setMimeData(mimeData)

        drag.exec_(QtCore.Qt.CopyAction)

    def buildDataTree(self, patient):
        self._disconnectCurrentPatientAndItems()

        self.treeModel.clear()
        self.rootNode = self.treeModel.invisibleRootItem()
        font_b = QFont()
        font_b.setBold(True)

        self._currentPatient = patient

        if self._currentPatient is None:
            return

        self._currentPatient.patientDataAddedSignal.connect(self._appendData)
        self._currentPatient.patientDataRemovedSignal.connect(self._removeData)

        #TODO: Same with other data

        #images
        images = self._currentPatient.images
        for image in images:
            self._appendData(image)

        if len(images) > 0:
            self._viewController.selectedImage = images[0]

        for plan in patient.plans:
            self._appendData(plan)

        # dynamic sequences
        for dynSeq in patient.dynamic3DSequences:
            self._appendData(dynSeq)

        for dynSeq in patient.dynamic2DSequences:
            self._appendData(dynSeq)

        # dynamic models
        for model in self._currentPatient.dynamic3DModels:
            serieRoot = PatientDataItem(model)
            for field in model.deformationList:
                item = PatientDataItem(field)
                serieRoot.appendRow(item)
            self.rootNode.appendRow(serieRoot)

    def _disconnectCurrentPatientAndItems(self):
        # Disconnect signals
        if not (self._currentPatient is None):
            self._currentPatient.patientDataAddedSignal.disconnect(self._appendData)
            self._currentPatient.patientDataRemovedSignal.disconnect(self._removeData)

        # Do this explicitely to be sure signals are disconnected
        for row in range(self.model().rowCount()):
            item = self.model().itemFromIndex(self.model().index(row, 0))
            if isinstance(item, PatientDataItem):
                item.disconnectAll()

    def dragEnterEvent(self, event):
        selection = self.selectionModel().selectedIndexes()[0]
        self._viewController.selectedImage = self.model().itemFromIndex(selection).data

    def _handleDoubleClick(self, selection):
        selectedData = self.model().itemFromIndex(selection).data

        if isinstance(selectedData, CTImage) or isinstance(selectedData, Dynamic3DSequence) or isinstance(selectedData, Dynamic2DSequence) or isinstance(selectedData, Image2D):
            self._viewController.mainImage = selectedData
        if isinstance(selectedData, RTPlan):
            self._viewController.plan = selectedData
        elif isinstance(selectedData, Dynamic3DModel):
            self._viewController.mainImage = selectedData.midp
        elif isinstance(selectedData, DoseImage):
            self._viewController.secondaryImage = selectedData

    def _handleRightClick(self, pos):
        pos = self.mapToGlobal(pos)

        selected = self.selectedIndexes()
        selectedData = [self.model().itemFromIndex(selectedData).data for selectedData in selected]

        dataMenu = PatientDataMenu(self._viewController, self)
        dataMenu.selectedData = selectedData
        dataMenu.asContextMenu().popup(pos)



## ------------------------------------------------------------------------------------------
class PatientDataItem(QStandardItem):
    def __init__(self, data, txt="", dataType="", color=QColor(75, 75, 75)):
        QStandardItem.__init__(self)


        # print('in patientDataSelection.py, PatientDataItem init', type(data), data.getTypeAsString())
        self.data = data
        # print(data.__dict__)
        self.data.nameChangedSignal.connect(self.setName)

        self.setEditable(False)

        defaultColor = color
        dynSeqColor = QColor(109, 119, 125)
        planColor = QColor(56, 130, 176)
        doseColor = QColor(166, 63, 104)
        modelColor = QColor(194, 130, 35)
        vectorFieldColor = QColor(201, 111, 50)

        if isinstance(data, CTImage):
            self.setName('CT' + ' - ' + self.data.name)
            self.setForeground(defaultColor)
        elif isinstance(data, Dynamic3DSequence):
            self.setName('3D Seq' + ' - ' + self.data.name)
            self.setForeground(dynSeqColor)
        elif isinstance(data, Dynamic2DSequence):
            self.setName('2D Seq' + ' - ' + self.data.name)
            self.setForeground(dynSeqColor)
        elif isinstance(data, Image2D):
            self.setName('2D Img' + ' - ' + self.data.name)
            self.setForeground(defaultColor)
        elif isinstance(data, RTPlan):
            self.setName('plan' + ' - ' + self.data.name)
            self.setForeground(planColor)
        elif isinstance(data, Dynamic3DModel):
            self.setName('DynMod' + ' - ' + self.data.name)
            self.setForeground(modelColor)
        elif isinstance(data, VectorField3D):
            self.setName('Vec Field' + ' - ' + self.data.name)
            self.setForeground(vectorFieldColor)
        elif isinstance(data, DoseImage):
            self.setName('Dose' + ' - ' + self.data.name)
            self.setForeground(doseColor)
        else:
            self.setName(data.getTypeAsString() + ' - ' + self.data.name)
            self.setForeground(defaultColor)

        # self.setText(txt)
        # self.setWhatsThis(type)

    def disconnectAll(self):
        self.data.nameChangedSignal.disconnect(self.setName)

    # No effect: it seems that C destructor of QStandardItem does not trigger __del__
    def __del__(self):
        self.disconnectAll()

    def setName(self, name):
        self.setText(name)
