from PyQt5 import QtCore
from PyQt5.QtCore import QDir, QMimeData, Qt, QModelIndex, pyqtSignal
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QDrag, QFont, QColor
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTreeView, QComboBox, QPushButton, QFileDialog, QDialog, \
    QStackedWidget, QListView, QLineEdit, QAbstractItemView, QMenu, QAction, QInputDialog, QHBoxLayout, QCheckBox

from pydicom.uid import generate_uid

from Controllers.api import API
from Controllers.DataControllers.patientController import PatientController
from Core.Data.dynamic3DSequence import Dynamic3DSequence
from Core.Data.dynamic3DModel import Dynamic3DModel
from Core.IO.serializedObjectIO import saveDataStructure



class PatientDataPanel(QWidget):

    currentPatientChangedSignal = pyqtSignal(object)
    patientAddedSignal = pyqtSignal(object)
    patientRemovedSignal = pyqtSignal(object)

    def __init__(self, viewController):
        QWidget.__init__(self)

        self._viewController = viewController
        self._currentPatientController = None

        self._viewController.patientAddedSignal.connect(self.patientAddedSignal.emit)
        self._viewController.patientAddedSignal.connect(self._handleNewPatient)

        self._viewController.patientRemovedSignal.connect(self.patientRemovedSignal.emit)
        self._viewController.patientRemovedSignal.connect(self._handleRemovedPatient)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.patientBox = PatientComboBox(self._viewController)
        self.layout.addWidget(self.patientBox)

        self.patientDataTree = PatientDataTree(self._viewController, self)
        self.layout.addWidget(self.patientDataTree)

        self.buttonLayout = QHBoxLayout()
        loadDataButton = QPushButton('Load Data')
        loadDataButton.clicked.connect(self.loadData)
        self.buttonLayout.addWidget(loadDataButton)
        saveDataButton = QPushButton('Save Data')
        saveDataButton.clicked.connect(self.saveData)
        self.buttonLayout.addWidget(saveDataButton)
        self.layout.addLayout(self.buttonLayout)

        self.dataPath = QDir.currentPath() # maybe not the ideal default data directory

    def _handleNewPatient(self, patientController):
        if self._currentPatientController is None:
            self.setCurrentPatientController(patientController)


    def _handleRemovedPatient(self, patientController):
        if self._currentPatientController == patientController:
            self.setCurrentPatientController(None)


    def getCurrentPatientController(self):
        return PatientController(self._currentPatientController)


    def getSelectedImageController(self):
        return self._viewController.getSelectedImageController()


    #@abstractmethod
    def getLeftClickMenu(self):
        pass


    def setCurrentPatientController(self, patientController):
        self._currentPatientController = patientController
        self.currentPatientChangedSignal.emit(self._currentPatientController)


    def loadData(self):
        filesOrFoldersList = _getOpenFilesAndDirs(caption="Open patient data files or folders", directory=QDir.currentPath())
        self.updateDataDirectory(filesOrFoldersList[0])

        API().loadData(filesOrFoldersList)
        #API().loadDummyImages(None) #test


    def updateDataDirectory(self, filePath):
        splitPath = filePath.split('/')
        withoutLastElementPath = ''
        for element in splitPath[:-1]:
            withoutLastElementPath += element + '/'
        self.dataPath = withoutLastElementPath


    def saveData(self):
        fileDialog = SaveData_dialog()
        savingPath, compressedBool, splitPatientsBool = fileDialog.getSaveFileName(None, dir=self.dataPath)

        patientList = [patient.data for patient in self._viewController.activePatientControllers]

        saveDataStructure(patientList, savingPath, compressedBool=compressedBool, splitPatientsBool=splitPatientsBool)


    ## temporary copy paste from 4D branch to take useful parts easier

    # def load_data_struct(self, dictFilePath):
    #
    #     self.Patients.loadDataStructure(dictFilePath)
    #     self.updateDataTreeView()

## ------------------------------------------------------------------------------------------
class PatientComboBox(QComboBox):
    def __init__(self, viewController):
        QComboBox.__init__(self)

        self._viewController = viewController

        self._viewController.patientAddedSignal.connect(self._addPatient)
        self._viewController.patientRemovedSignal.connect(self._removePatient)

        self._setActivePatientController = lambda index: self._viewController.setCurrentPatientController(self.currentData())
        self.currentIndexChanged.connect(self._setActivePatientController)

    def __del__(self):
        self.currentIndexChanged.disconnect(self._setActivePatientController)

    def _addPatient(self, patientController):
        name = patientController.getName()
        if name is None:
            name = 'None'

        self.addItem(name, patientController)
        if self.count() == 1:
            self._viewController.setCurrentPatientController(patientController)

    def _removePatient(self, patientController):
        self.removeItem(self.findData(patientController))


## ------------------------------------------------------------------------------------------
class PatientDataTree(QTreeView):

    dataSelectedSignal = pyqtSignal(object)

    def __init__(self, viewController, patientDataPanel):
        QTreeView.__init__(self)

        self.patientDataPanel = patientDataPanel
        self._viewController = viewController

        self.setHeaderHidden(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.viewport().installEventFilter(self)
        self.customContextMenuRequested.connect(lambda pos: self.DataTree_RightClick(pos))
        self.resizeColumnToContents(0)
        self.doubleClicked.connect(self.setDataToDisplay)
        self.treeModel = QStandardItemModel()
        self.setModel(self.treeModel)
        self.setColumnHidden(1, True)
        self.expandAll()

        self._viewController.currentPatientChangedSignal.connect(self.updateDataTree)

        self.patientController = self.patientDataPanel.getCurrentPatientController()
        self.updateDataTree(self.patientController)

        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)

    def appendImage(self, dataController):
        item = PatientDataItem(dataController)
        self.rootNode.appendRow(item)

    def mouseMoveEvent(self, event):
        drag = QDrag(self)
        mimeData = QMimeData()

        mimeData.setText('image')
        drag.setMimeData(mimeData)

        drag.exec_(QtCore.Qt.CopyAction)

    def updateDataTree(self, patientController):

        """
        What if instead of trying to put in bold the shown data, with the issues of UID that must saved for each viewer etc ...
        We simply show the image, dose, dyn seq and plan name on the viewer or on a QTip that shown when the mouse is over it ?
        """

        self.treeModel.clear()
        self.rootNode = self.treeModel.invisibleRootItem()
        font_b = QFont()
        font_b.setBold(True)

        if patientController is None:
            return

        try:
         patientController.imageAddedSignal.disconnect(self.appendImage)
        except:
            pass
        patientController.imageAddedSignal.connect(self.appendImage)

        #images
        imageControllers = patientController.getImageControllers()
        for imageController in imageControllers:
            item = PatientDataItem(imageController)
            self.rootNode.appendRow(item)

        if len(imageControllers) > 0:
            self._viewController.setSelectedImageController(imageControllers[0])

        # dynamic sequences
        sequenceControllers = patientController.getDynamic3DSequenceControllers()
        for dynSeqController in sequenceControllers:
            serieRoot = PatientDataItem(dynSeqController)
            imageControllers = dynSeqController.getImageControllers()
            for imageController in imageControllers:
                item = PatientDataItem(imageController)
                serieRoot.appendRow(item)
            self.rootNode.appendRow(serieRoot)

        # if len(dynSeqController) > 0:
        # self._viewController.setSelectedImageController(imageControllers[0])

        # dynamic models
        modelControllers = patientController.getDynamic3DModelControllers()
        for modelController in modelControllers:
            serieRoot = PatientDataItem(modelController)
            fieldControllers = modelController.getVectorFieldControllers()
            for fieldController in fieldControllers:
                item = PatientDataItem(fieldController)
                serieRoot.appendRow(item)
            self.rootNode.appendRow(serieRoot)

        # if len(dynSeqController) > 0:
        # self._viewController.setSelectedImageController(imageControllers[0])



    def dragEnterEvent(self, event):
        selection = self.selectionModel().selectedIndexes()[0]
        self._viewController.setSelectedImageController(self.model().itemFromIndex(selection).dataController)


    def setDataToDisplay(self, selection):

        selectedDataController = self.model().itemFromIndex(selection).dataController
        dataType = selectedDataController.getType()
        # self.patientController = self.patientDataPanel.getCurrentPatientController()  # not used for now
        # self._viewController.shownDataUIDsList.append(selectedDataController.data.seriesInstanceUID)  # not used for now

        if dataType == 'CTImage':
            self._viewController.setSelectedImageController(selectedDataController)

            # there are 2 options here, using a signal emitted and received in the viewController
            # or simply calling the necessary viewController function as it is passed to every item in the panel anyway
            # this is the example with an image selected but it must be differentiated for each relevant data type
            # option with _viewController use, in this case the signal is not used and can be removed from the class
            self._viewController.setMainImage(selectedDataController)
            # option with signal
            #self.dataSelectedSignal.emit(self.model().itemFromIndex(selection).imageController)

        #from 4D branch
        # selected_type = self.model().itemFromIndex(selection).whatsThis()
        # print(selected_type)
        # selected_UID = selection.model().data(selection.model().index(selection.row(), 1, selection.parent()))
        # is_bold = selection.model().itemFromIndex(selection).font().bold()
        #
        # if is_bold and selected_type != 'CT':
        #     print('Unselected for display:', selected_UID)
        # else:
        #     print('Selected for display:', selected_UID)
        #
        # if selected_type == 'CT':
        #     self.Current_CT_changed.emit(selected_UID)
        #     self.ROI_list_changed.emit()
        #     return
        # elif selected_type == 'dose':
        #     if is_bold:
        #         self.Current_dose_changed.emit("")
        #     else:
        #         self.Current_dose_changed.emit(selected_UID)
        #     return
        # elif selected_type == 'plan':
        #     if is_bold:
        #         self.Current_plan_changed.emit("")
        #     else:
        #         self.Current_plan_changed.emit(selected_UID)
        #     return
        # elif selected_type == 'field':
        #     if is_bold:
        #         self.Current_field_changed.emit("")
        #     else:
        #         self.Current_field_changed.emit(selected_UID)
        #     return
        #
        # for seriesIndex, series in enumerate(self.Patients.list[0].Dyn4DSeqList):
        #     serieRoot = series.SOPInstanceUID
        #     if serieRoot == selected_UID:
        #         print("Series selected", serieRoot, "seriesIndex:", seriesIndex)
        #         self.DynamicImage_selected.emit([selected_UID, 'dyn4DSeq', seriesIndex])
        #         return
        #
        # for seriesIndex, series in enumerate(self.Patients.list[0].Dyn2DSeqList):
        #     serieRoot = series.SOPInstanceUID
        #     if serieRoot == selected_UID:
        #         print("Series selected", serieRoot, "seriesIndex:", seriesIndex)
        #         self.DynamicImage_selected.emit([selected_UID, 'dyn2DSeq', seriesIndex])
        #         return


    def DataTree_RightClick(self, pos):

        UIDs = []
        selectedDataTypeList = []
        pos = self.mapToGlobal(pos)
        selected = self.selectedIndexes()
        selectedDataControllerList = [self.model().itemFromIndex(selectedData).dataController for selectedData in selected]

        dataType = selectedDataControllerList[0].getType()

        selectedDataTypeList = [dataController.getType() for dataController in selectedDataControllerList]
        print('In DataTree_RightClick, list of selected data types :', selectedDataTypeList)

        for i in range(len(selectedDataTypeList)):
            # UIDs.append(
            #     self.model().data(self.model().index(selected[i].row(), 1, selected[i].parent())))
            # selectedDataTypeList.append(self.model().itemFromIndex(selected[i]).whatsThis())
            if selectedDataTypeList[i] != dataType:
                dataType = 'mixed'

        print('Right clic options type: ', dataType)

        if (len(selected) > 0):
            self.context_menu = QMenu()

            # actions for dose data
            # if (dataType == 'dose'):
            #     self.export_action = QAction("Export")
            #     self.export_action.triggered.connect(
            #         lambda checked, data_types=selectedDataTypeList, UIDs=UIDs: self.export_item(data_types, UIDs))
            #     self.context_menu.addAction(self.export_action)

            # actions for any single data
            if (dataType != 'mixed' and len(selected) == 1):
                self.rename_action = QAction("Rename")
                self.rename_action.triggered.connect(
                    lambda checked, data_type=dataType, UIDs=UIDs: self.rename_item(data_type, UIDs))
                self.context_menu.addAction(self.rename_action)

            # actions for group of 3DImage
            if (dataType == 'CTImage' and len(selected) > 1):  # to generalize to other modalities eventually
                self.make_series_action = QAction("Make dynamic 3D sequence")
                self.make_series_action.triggered.connect(
                    lambda checked, selectedImages=selectedDataControllerList: self.createDynamic3DSequence(selectedImages))
                self.context_menu.addAction(self.make_series_action)

            # actions for any 3DImage
            # if (dataType == 'CTImage'):
            #     self.crop_action = QAction("Crop")
            #     self.crop_action.triggered.connect(
            #         lambda checked, data_type=dataType, UIDs=UIDs: self.crop_image(UIDs[0]))
            #     self.context_menu.addAction(self.crop_action)

            # actions specific to an image selected with deformation fields
            # if (dataType == 'mixed' and len(UIDs) > 1 and selectedDataTypeList[0] == 'CTImage'):
            #     fields_only = True
            #     for i in range(len(selectedDataTypeList) - 1):
            #         if selectedDataTypeList[i + 1] != 'field':
            #             fields_only = False
            #     if fields_only:
            #         self.make_4d_model_action = QAction("Make 4D model (MidP)")
            #         self.make_4d_model_action.triggered.connect(
            #             lambda checked, data_types=selectedDataTypeList, UIDs=UIDs: self.make_4d_model(data_types, UIDs))
            #         self.context_menu.addAction(self.make_4d_model_action)

            # actions for single Dynamic3DSequence
            if (dataType == 'Dynamic3DSequence' and len(selected) == 1):# or dataType == 'Dynamic2DSequence'):
                self.compute3DModelAction = QAction("Compute 4D model (MidP)")
                self.compute3DModelAction.triggered.connect(
                    lambda checked, selected3DSequence=selectedDataControllerList[0]: self.computeDynamic3DModel(selected3DSequence))
                self.context_menu.addAction(self.compute3DModelAction)

            # # actions for plans
            # if (dataType == 'plan' and len(UIDs) == 1):
            #     plan = self.Patients.find_plan(UIDs[0])
            #     if (plan.ScanMode == 'LINE'):
            #         self.convert_action = QAction("Convert line scanning to PBS plan")
            #         self.convert_action.triggered.connect(lambda checked: plan.convert_LineScanning_to_PBS())
            #         self.context_menu.addAction(self.convert_action)
            #
            #     self.display_spot_action = []
            #     self.display_spot_action.append(QAction("Display spots (full plan)"))
            #     self.display_spot_action[0].triggered.connect(
            #         lambda checked, beam=-1: self.Viewer_display_spots.emit(beam))
            #     self.context_menu.addAction(self.display_spot_action[0])
            #     for b in range(len(plan.Beams)):
            #         self.display_spot_action.append(QAction("Display spots (Beam " + str(b + 1) + ")"))
            #         self.display_spot_action[b + 1].triggered.connect(
            #             lambda checked, beam=b: self.Viewer_display_spots.emit(beam))
            #         self.context_menu.addAction(self.display_spot_action[b + 1])
            #
            #     self.remove_spot_action = QAction("Remove displayed spots")
            #     self.remove_spot_action.triggered.connect(self.Viewer_clear_spots.emit)
            #     self.context_menu.addAction(self.remove_spot_action)
            #
            #     self.print_plan_action = QAction("Print plan info")
            #     self.print_plan_action.triggered.connect(plan.print_plan_stat)
            #     self.context_menu.addAction(self.print_plan_action)

            self.delete_action = QAction("Delete")
            self.delete_action.triggered.connect(
                lambda checked, data_types=selectedDataTypeList, UIDs=UIDs: self.delete_item(data_types, UIDs))
            self.context_menu.addAction(self.delete_action)

            self.context_menu.popup(pos)


    def createDynamic3DSequence(self, selectedImageControllers):

        newName, okPressed = QInputDialog.getText(self, "Set series name", "Series name:", QLineEdit.Normal, "4DCT")

        if (okPressed):
            newSeq = Dynamic3DSequence()
            newSeq.name = newName
            newSeq.seriesInstanceUID = generate_uid()

            for i in range(len(selectedImageControllers)):
                image = selectedImageControllers[i].data
                newSeq.dyn3DImageList.append(image)
                self._viewController._currentPatientController.removeImage(image)

            self._viewController._currentPatientController.appendDyn3DSeq(newSeq)
            self.updateDataTree(self._viewController._currentPatientController)


    def computeDynamic3DModel(self, selected3DSequenceController):

        newName, okPressed = QInputDialog.getText(self, "Set dynamic 3D model name", "3D model name:", QLineEdit.Normal, "MidP")

        if (okPressed):
            newMod = Dynamic3DModel()
            newMod.name = newName
            newMod.seriesInstanceUID = generate_uid()
            newMod.computeMidPositionImage(selected3DSequenceController.data)
            self._viewController._currentPatientController.appendDyn3DMod(newMod)
            self.updateDataTree(self._viewController._currentPatientController)


## ------------------------------------------------------------------------------------------
class PatientDataItem(QStandardItem):
    def __init__(self, dataController, txt="", type="", color=QColor(125, 125, 125)):
        QStandardItem.__init__(self)

        self.dataController = dataController
        self.dataController.nameChangedSignal.connect(self.setName)

        self.setName(self.dataController.getName())

        # self.setEditable(False)
        # self.setForeground(color)
        # self.setText(txt)
        # self.setWhatsThis(type)

    def setName(self, name):
        self.setText(name)


## ------------------------------------------------------------------------------------------
def _getOpenFilesAndDirs(parent=None, caption='', directory='',
                          filter='', initialFilter='', options=None):
    def updateText():
      # update the contents of the line edit widget with the selected files
      selected = []
      for index in view.selectionModel().selectedRows():
        selected.append('"{}"'.format(index.data()))
      lineEdit.setText(' '.join(selected))

    dialog = QFileDialog(parent, windowTitle=caption)
    dialog.setFileMode(dialog.ExistingFiles)
    if options:
      dialog.setOptions(options)
    dialog.setOption(dialog.DontUseNativeDialog, True)
    if directory:
      dialog.setDirectory(directory)
    if filter:
      dialog.setNameFilter(filter)
      if initialFilter:
        dialog.selectNameFilter(initialFilter)

    # by default, if a directory is opened in file listing mode,
    # QFileDialog.accept() shows the contents of that directory, but we
    # need to be able to "open" directories as we can do with files, so we
    # just override accept() with the default QDialog implementation which
    # will just return exec_()
    dialog.accept = lambda: QDialog.accept(dialog)

    # there are many item views in a non-native dialog, but the ones displaying
    # the actual contents are created inside a QStackedWidget; they are a
    # QTreeView and a QListView, and the tree is only used when the
    # viewMode is set to QFileDialog.Details, which is not this case
    stackedWidget = dialog.findChild(QStackedWidget)
    view = stackedWidget.findChild(QListView)
    view.selectionModel().selectionChanged.connect(updateText)

    lineEdit = dialog.findChild(QLineEdit)
    # clear the line edit contents whenever the current directory changes
    dialog.directoryEntered.connect(lambda: lineEdit.setText(''))

    dialog.exec_()
    return dialog.selectedFiles()


## ------------------------------------------------------------------------------------------
class SaveData_dialog(QFileDialog):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.defaultName = "Patient"

    def getSaveFileName(self, parent=None,
                        caption="Select folder and file name to save data tree",
                        dir=".",
                        filter='',
                        initialFilter='',
                        defaultName="Patient",
                        options=None):

        self.setWindowTitle(caption)
        self.setDirectory(dir)
        self.selectFile(defaultName)
        self.setAcceptMode(QFileDialog.AcceptSave)  # bouton "Save"
        self.setOption(QFileDialog.DontUseNativeDialog, True)

        layout = self.layout()
        # checkBoxLayout = QHBoxLayout
        self.compressBox = QCheckBox("Compress Data", self)
        self.compressBox.setToolTip('This will compress the data before saving them, it takes longer to save the data this way')
        layout.addWidget(self.compressBox, 4, 0)
        self.splitPatientsBox = QCheckBox("Split Patients", self)
        self.splitPatientsBox.setToolTip('This will split patients into multiple files if multiple patients data are loaded')
        layout.addWidget(self.splitPatientsBox, 4, 1)
        self.setLayout(layout)

        if self.exec_():
            return self.selectedFiles()[0], self.compressBox.isChecked(), self.splitPatientsBox.isChecked()
        else:
            return "", ""