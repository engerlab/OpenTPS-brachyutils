from PyQt5 import QtCore
from PyQt5.QtCore import QDir, QMimeData, Qt, QModelIndex, pyqtSignal
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QDrag
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTreeView, QComboBox, QPushButton, QFileDialog, QDialog, \
    QStackedWidget, QListView, QLineEdit, QAbstractItemView, QMenu, QAction, QInputDialog

from Controllers.api import API
from Controllers.DataControllers.patientController import PatientController
from Core.Data.dynamic3DSequence import Dynamic3DSequence

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

        loadDataButton = QPushButton('Load data')
        loadDataButton.clicked.connect(self.loadData)
        self.layout.addWidget(loadDataButton)


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


    def setSelectedImageController(self, imageController):
        self._viewController.setSelectedImageController(imageController)


    def loadData(self):
        file = _getOpenFilesAndDirs(caption="Open patient data files or folders", directory=QDir.currentPath())
        API().loadData(file)
        #API().loadDummyImages(None) #test


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

    def updateDataTree(self, patientController): ## --> this version is specific to images --> must be changed to work with each data type using a dataController
        self.treeModel.clear()
        self.rootNode = self.treeModel.invisibleRootItem()

        if patientController is None:
            return

        try:
         patientController.imageAddedSignal.disconnect(self.appendImage)
        except:
            pass
        patientController.imageAddedSignal.connect(self.appendImage)

        imageControllers = patientController.getImageControllers()
        for imageController in imageControllers:
            self.appendImage(imageController)

        if len(imageControllers) > 0:
            self._viewController.setSelectedImageController(imageControllers[0])


    def dragEnterEvent(self, event):
        selection = self.selectionModel().selectedIndexes()[0]
        self._viewController.setSelectedImageController(self.model().itemFromIndex(selection).imageController)


    def setDataToDisplay(self, selection):

        self._viewController.setSelectedImageController(self.model().itemFromIndex(selection).dataController)
        self.patientController = self.patientDataPanel.getCurrentPatientController()  # not used for now

        # there are 2 options here, using a signal emitted and received in the viewController
        # or simply calling the necessary viewController function as it is passed to every item in the panel anyway
        # this is the example with an image selected but it must be differentiated for each relevant data type
        # option with _viewController use, in this case the signal is not used and can be removed from the class
        self._viewController.setMainImage(self.model().itemFromIndex(selection).dataController)
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

            if (dataType == 'dose'):
                self.export_action = QAction("Export")
                self.export_action.triggered.connect(
                    lambda checked, data_types=selectedDataTypeList, UIDs=UIDs: self.export_item(data_types, UIDs))
                self.context_menu.addAction(self.export_action)

            if (dataType != 'mixed'):
                self.rename_action = QAction("Rename")
                self.rename_action.triggered.connect(
                    lambda checked, data_type=dataType, UIDs=UIDs: self.rename_item(data_type, UIDs))
                self.context_menu.addAction(self.rename_action)

            if (dataType == 'CTImage' and len(selected) > 1):
                self.make_series_action = QAction("Make dynamic 3D sequence")
                self.make_series_action.triggered.connect(
                    lambda checked, data_types=selectedDataTypeList, selectedImages=selectedDataControllerList: self.createDynamic3DSequence(data_types, selectedImages))
                self.context_menu.addAction(self.make_series_action)

            if (dataType == 'CTImage'):
                self.crop_action = QAction("Crop")
                self.crop_action.triggered.connect(
                    lambda checked, data_type=dataType, UIDs=UIDs: self.crop_image(UIDs[0]))
                self.context_menu.addAction(self.crop_action)

            if (dataType == 'mixed' and len(UIDs) > 1 and selectedDataTypeList[0] == 'CTImage'):
                fields_only = True
                for i in range(len(selectedDataTypeList) - 1):
                    if selectedDataTypeList[i + 1] != 'field':
                        fields_only = False
                if fields_only:
                    self.make_4d_model_action = QAction("Make 4D model (MidP)")
                    self.make_4d_model_action.triggered.connect(
                        lambda checked, data_types=selectedDataTypeList, UIDs=UIDs: self.make_4d_model(data_types, UIDs))
                    self.context_menu.addAction(self.make_4d_model_action)

            if (dataType == '4DCT' and len(UIDs) == 1):
                self.start_midp_action = QAction("Compute 4D model (MidP)")
                self.start_midp_action.triggered.connect(
                    lambda checked, data_types=selectedDataTypeList, UIDs=UIDs: self.start_midp(data_types, UIDs))
                self.context_menu.addAction(self.start_midp_action)

            if (dataType == 'plan' and len(UIDs) == 1):
                plan = self.Patients.find_plan(UIDs[0])
                if (plan.ScanMode == 'LINE'):
                    self.convert_action = QAction("Convert line scanning to PBS plan")
                    self.convert_action.triggered.connect(lambda checked: plan.convert_LineScanning_to_PBS())
                    self.context_menu.addAction(self.convert_action)

                self.display_spot_action = []
                self.display_spot_action.append(QAction("Display spots (full plan)"))
                self.display_spot_action[0].triggered.connect(
                    lambda checked, beam=-1: self.Viewer_display_spots.emit(beam))
                self.context_menu.addAction(self.display_spot_action[0])
                for b in range(len(plan.Beams)):
                    self.display_spot_action.append(QAction("Display spots (Beam " + str(b + 1) + ")"))
                    self.display_spot_action[b + 1].triggered.connect(
                        lambda checked, beam=b: self.Viewer_display_spots.emit(beam))
                    self.context_menu.addAction(self.display_spot_action[b + 1])

                self.remove_spot_action = QAction("Remove displayed spots")
                self.remove_spot_action.triggered.connect(self.Viewer_clear_spots.emit)
                self.context_menu.addAction(self.remove_spot_action)

                self.print_plan_action = QAction("Print plan info")
                self.print_plan_action.triggered.connect(plan.print_plan_stat)
                self.context_menu.addAction(self.print_plan_action)

            self.delete_action = QAction("Delete")
            self.delete_action.triggered.connect(
                lambda checked, data_types=selectedDataTypeList, UIDs=UIDs: self.delete_item(data_types, UIDs))
            self.context_menu.addAction(self.delete_action)

            self.context_menu.popup(pos)

    def createDynamic3DSequence(self, data_types, selectedImages):

        newSeq = Dynamic3DSequence()
        #newSeq.SOPInstanceUID = generate_uid()
        newName, okPressed = QInputDialog.getText(self, "Set series name", "Series name:", QLineEdit.Normal, "4DCT")
        if (okPressed):
            newSeq.name = newName
            for i in range(len(data_types)):
                if (data_types[i] == 'CTImage'):
                    # patient_id = self.Patients.find_patient(UIDs[i])
                    # ct = self.Patients.find_CT_image(UIDs[i])
                    image = selectedImages[i].data
                    newSeq.dyn3DImageList.append(image)
                    self._viewController._currentPatientController.removeImage(image)

            self._viewController._currentPatientController.appendDyn3DSeq(newSeq)
            # newSeq.isLoaded = 1
            # self.Patients.list[patient_id].Dyn4DSeqList.append(newSeq)
            self.updateDataTree(self._viewController._currentPatientController)
            #self.updateDataTreeView()


class PatientDataItem(QStandardItem):
    def __init__(self, dataController):
        QStandardItem.__init__(self)

        self.dataController = dataController
        self.dataController.nameChangedSignal.connect(self.setName)

        self.setName(self.dataController.getName())


    def setName(self, name):
        self.setText(name)


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
