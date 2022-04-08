import os
from typing import Sequence, Tuple

from PyQt5.QtGui import QPixmap, QColor, QIcon
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QVBoxLayout, QLabel, QLineEdit, QMainWindow, QCheckBox, \
    QFrame, QScrollArea

from Core.Data.CTCalibrations.RayStationCalibration.rayStationCTCalibration import RayStationCTCalibration
from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.doseImage import DoseImage
from Core.Data.Images.image3D import Image3D
from Core.Data.Images.roiMask import ROIMask
from Core.Data.Plan.rtPlan import RTPlan
from Core.Data.dvh import DVH
from Core.Data.patient import Patient
from Core.Data.roiContour import ROIContour
from Core.Data.rtStruct import RTStruct
from Core.IO import mcsquareIO
from Core.event import Event
from Extensions.FLASH.Core.Processing.CEMOptimization.workflows import SingleBeamCEMOptimizationWorkflow
from Extensions.FLASH.GUI.convergencePlot import ConvergencePlot
from GUI.Panels.patientDataPanel import PatientDataTree, PatientComboBox
from GUI.Viewer.DataForViewer.ROIContourForViewer import ROIContourForViewer
from GUI.Viewer.DataForViewer.ROIMaskForViewer import ROIMaskForViewer
from GUI.Viewer.DataForViewer.image3DForViewer import Image3DForViewer
from GUI.Viewer.DataViewerComponents.dvhPlot import DVHPlot
from GUI.Viewer.DataViewerComponents.imageViewer import ImageViewer

import Extensions.FLASH.DefaultData as defaultDataModule


class FlashWindow(QMainWindow):
    def __init__(self, viewController, parent=None):
        super().__init__(parent)

        self._viewController = viewController

        self._dvh = None

        self.setWindowTitle('FLASH TPS')
        self.resize(800, 600)

        self.centralWidget = QWidget()
        self.setCentralWidget(self.centralWidget)
        self._mainLayout = QHBoxLayout()
        self.centralWidget.setLayout(self._mainLayout)

        self._leftPanel = LeftPanel((self._viewController), self)
        self._leftPanel.setFixedWidth(200)

        self._mainLayout.addWidget(self._leftPanel)

        self._rightPanel = QFrame()
        self._mainLayout.addWidget(self._rightPanel)
        self._rightLayout = QVBoxLayout()
        self._rightPanel.setLayout(self._rightLayout)

        self._viewers = ThreeViewsGrid(self._viewController, self)
        self._rightLayout.addWidget(self._viewers)

        self._bottomFrame = QFrame()
        self._bottomFrame.setFixedHeight(400)
        self._rightLayout.addWidget(self._bottomFrame)
        self._bottomLayout = QHBoxLayout()
        self._bottomFrame.setLayout(self._bottomLayout)

        self._convergencePlot = ConvergencePlot()
        self._bottomLayout.addWidget(self._convergencePlot)

        self._dvhPlot = DVHPlot(self)
        self._bottomLayout.addWidget(self._dvhPlot)

        self._leftPanel.ctSelectedEvent.connect(self._viewers.setCT)
        self._leftPanel.doseUpdateEvent.connect(self._viewers.setDose)
        self._leftPanel.doseUpdateEvent.connect(self._updateDVHWithDose)
        self._leftPanel.contourSelectedEvent.connect(self._viewers.setROI)
        self._leftPanel.contourSelectedEvent.connect(self._updateDVHWithContour)
        self._leftPanel.fValEvent.connect(self._convergencePlot.appendFVal)

    def _updateDVHWithDose(self, dose:DoseImage):
        self._dvh.dose = dose
        self._dvh.computeDVH()

    def _updateDVHWithContour(self, roi):
        if not (self._dvh is None):
            self._dvhPlot.removeDVH(self._dvh)

        self._dvh = DVH(roi)
        self._dvhPlot.appendDVH(self._dvh, roi)

    def closeEvent(self, event):
        self._viewers.close()
        event.accept()

class ThreeViewsGrid(QWidget):
    def __init__(self, viewController, parent=None):
        super().__init__(parent)

        self._viewController = viewController

        self._mainLayout = QHBoxLayout(self)
        self.setLayout(self._mainLayout)

        self._viewer0 = ImageViewer(viewController)
        self._viewer1 = ImageViewer(viewController)
        self._viewer2 = ImageViewer(viewController)

        self._viewer0.viewType = ImageViewer.ViewerTypes.CORONAL
        self._viewer1.viewType = ImageViewer.ViewerTypes.AXIAL
        self._viewer2.viewType = ImageViewer.ViewerTypes.SAGITTAL

        self._viewer0.crossHairEnabled = True
        self._viewer1.crossHairEnabled = True
        self._viewer2.crossHairEnabled = True

        self._mainLayout.addWidget(self._viewer0)
        self._mainLayout.addWidget(self._viewer1)
        self._mainLayout.addWidget(self._viewer2)

        self._ct = None
        self._roi = None

    def closeEvent(self, event):
        self._viewer0.close()
        self._viewer1.close()
        self._viewer2.close()

        event.accept()

    def setCT(self, ct:CTImage):
        self._viewer0.primaryImage = ct
        self._viewer1.primaryImage = ct
        self._viewer2.primaryImage = ct

        if not (self._ct is None):
            if not (self._roi is None):
                self._ct = ct
                self._convertROIToMask()
                self._setCTPositionToROICenter()
            else:
                Image3DForViewer(ct).selectedPosition = Image3DForViewer(self._ct).selectedPosition

        self._ct = ct

    def setDose(self, dose:DoseImage):
        self._viewer0.secondaryImage = dose
        self._viewer1.secondaryImage = dose
        self._viewer2.secondaryImage = dose

    def setROI(self, roi):
        self._viewer0._contourLayer.setNewContour(roi)
        self._viewer1._contourLayer.setNewContour(roi)
        self._viewer2._contourLayer.setNewContour(roi)

        self._roi = roi

        self._convertROIToMask()
        self._setCTPositionToROICenter()

    def _convertROIToMask(self):
        if isinstance(self._roi, ROIContour):
            if not self._ct is None:
                self._roi = self._roi.getBinaryMask(self._ct.origin, self._ct.gridSize, self._ct.spacing)

    def _setCTPositionToROICenter(self):
        if not self._ct is None:
            Image3DForViewer(self._ct).selectedPosition = self._roi.centerOfMass


class LeftPanel(QWidget):
    def __init__(self, viewController, parent=None):
        super().__init__(parent)

        self.ctSelectedEvent = Event(Image3D)
        self.doseUpdateEvent = Event(Image3D)
        self.contourSelectedEvent = Event(object)
        self.fValEvent = Event(Tuple)

        self._viewController = viewController

        self._mainLayout = QVBoxLayout(self)
        self.setLayout(self._mainLayout)

        self._ctLabel = QLabel(self)
        self._ctLabel.setText('Select CT: ')
        self._mainLayout.addWidget(self._ctLabel)

        self.patientBox = PatientComboBox(self._viewController)
        self._mainLayout.addWidget(self.patientBox)

        self.patientDataTree = PatientDataTree(self._viewController, self)
        self.patientDataTree.setMaximumHeight(400)
        self._mainLayout.addWidget(self.patientDataTree)

        self.patientDataTree.clicked.connect(self._emitCT)

        self._roiLabel = QLabel(self)
        self._roiLabel.setText('Select ROI: ')
        self._mainLayout.addWidget(self._roiLabel)

        self.roiPanel = ROIPanel(self._viewController, self)
        scrollArea = QScrollArea(self)
        scrollArea.setWidgetResizable(True)
        scrollArea.setMaximumHeight(400)
        self._mainLayout.addWidget(scrollArea)
        scrollArea.setWidget(self.roiPanel)

        self.roiPanel.selectionEvent.connect(self.contourSelectedEvent.emit)

        self._beamEditor = BeamEditor(self)
        self._mainLayout.addWidget(self._beamEditor)

        self.runButton = QPushButton('Run!')
        self.runButton.clicked.connect(self._run)
        self._mainLayout.addWidget(self.runButton)

        self.cemOptimizer = SingleBeamCEMOptimizationWorkflow()
        self.cemOptimizer.doseUpdateEvent.connect(self._updateDose)
        self.cemOptimizer.planUpdateEvent.connect(self._updateCT)
        self.cemOptimizer.fValEvent.connect(self.fValEvent.emit)

    def _emitCT(self):
        selected = self.patientDataTree.selectedIndexes()
        selectedCT = [self.patientDataTree.model().itemFromIndex(selectedData).data for selectedData in selected]

        self.ctSelectedEvent.emit(selectedCT[0])

    def _run(self):
        selected = self.patientDataTree.selectedIndexes()
        selectedCT = [self.patientDataTree.model().itemFromIndex(selectedData).data for selectedData in selected]

        if len(self.roiPanel.selected)>1:
            raise Exception('Only 1 contour/ROI can be selected as the target ROI')

        if len(selectedCT)>1:
            raise Exception('Only 1 CT can be selected')

        defaultDataPath = defaultDataModule.__path__[0]

        self.cemOptimizer.ctCalibration = RayStationCTCalibration(
            fromFiles=(defaultDataPath + os.path.sep + 'calibration_cef.txt', defaultDataPath + os.path.sep + 'materials_cef.txt'))
        self.cemOptimizer.beamModel = mcsquareIO.readBDL(defaultDataPath + os.path.sep + 'BDL_default_RS_Leuven_4_5_5.txt')
        self.cemOptimizer.targetROI = self.roiPanel.selected[0].contour
        self.cemOptimizer.gantryAngle = self._beamEditor.beamAngle
        self.cemOptimizer.cemToIsocenter = self._beamEditor.cemIsoDist
        self.cemOptimizer.beamEnergy = self._beamEditor.beamEnergy
        self.cemOptimizer.ct = selectedCT[0]
        self.cemOptimizer.targetDose = self._beamEditor.targetDose
        self.cemOptimizer.spotSpacing = self._beamEditor.spotSpacing
        self.cemOptimizer.cemRSP = self.cemOptimizer.ctCalibration.convertMassDensity2RSP(self._beamEditor.cemDensity)
        self.cemOptimizer.rangeShifterRSP = self.cemOptimizer.ctCalibration.convertMassDensity2RSP(self._beamEditor.rangeShifterDensity)

        self.cemOptimizer.run()

    def _updateDose(self, dose):
        Image3DForViewer(dose).range = [0, self.cemOptimizer.targetDose+1]

        self.doseUpdateEvent.emit(dose)

    def _updateCT(self, plan:RTPlan):
        ct = CTImage.fromImage3D(self.cemOptimizer.ct)

        # Update CT with CEM
        for beam in plan:
            cem = beam.cem

            if not cem.imageArray is None:
                [rsROI, cemROI] = cem.computeROIs(ct, beam)

                ctArray = ct.imageArray
                ctArray[cemROI.imageArray.astype(bool)] = self.cemOptimizer.ctCalibration.convertRSP2HU(cem.cemRSP, energy=100.)
                ctArray[rsROI.imageArray.astype(bool)] = self.cemOptimizer.ctCalibration.convertRSP2HU(cem.rangeShifterRSP, energy=100.)

                ct.imageArray = ctArray

        self.ctSelectedEvent.emit(ct)

class BeamEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._mainLayout = QVBoxLayout(self)
        self.setLayout(self._mainLayout)

        self._energyLabel = QLabel(self)
        self._energyLabel.setText('Energy: ')
        self._angleLabel = QLabel(self)
        self._angleLabel.setText('Angle: ')
        self._distanceLabel = QLabel(self)
        self._distanceLabel.setText('CEM-isocenter distance: ')
        self._doseLabel = QLabel(self)
        self._doseLabel.setText('Dose in target: ')
        self._rsDensityLabel = QLabel(self)
        self._rsDensityLabel.setText('Range shifter density: ')
        self._cemDensityLabel = QLabel(self)
        self._cemDensityLabel.setText('CEM density: ')
        self._spotSpacingLabel = QLabel(self)
        self._spotSpacingLabel.setText('Spot spacing: ')

        self._energyEdit = QLineEdit(self)
        self._energyEdit.setText(str(226))
        self._angleEdit = QLineEdit(self)
        self._angleEdit.setText(str(0))
        self._distanceEdit = QLineEdit(self)
        self._distanceEdit.setText(str(100))
        self._doseEdit = QLineEdit(self)
        self._doseEdit.setText(str(40))
        self._rsDensityEdit = QLineEdit(self)
        self._rsDensityEdit.setText(str(2.7))
        self._cemDensityEdit = QLineEdit(self)
        self._cemDensityEdit.setText(str(1.2))
        self._spotSpacingEdit = QLineEdit(self)
        self._spotSpacingEdit.setText(str(5))

        self._mainLayout.addWidget(self._energyLabel)
        self._mainLayout.addWidget(self._energyEdit)
        self._mainLayout.addWidget(self._angleLabel)
        self._mainLayout.addWidget(self._angleEdit)
        self._mainLayout.addWidget(self._distanceLabel)
        self._mainLayout.addWidget(self._distanceEdit)
        self._mainLayout.addWidget(self._doseLabel)
        self._mainLayout.addWidget(self._doseEdit)
        self._mainLayout.addWidget(self._spotSpacingLabel)
        self._mainLayout.addWidget(self._spotSpacingEdit)
        self._mainLayout.addWidget(self._rsDensityLabel)
        self._mainLayout.addWidget(self._rsDensityEdit)
        self._mainLayout.addWidget(self._cemDensityLabel)
        self._mainLayout.addWidget(self._cemDensityEdit)

    @property
    def beamEnergy(self) -> float:
        return float(self._energyEdit.text())

    @property
    def beamAngle(self) -> float:
        return float(self._angleEdit.text())

    @property
    def cemIsoDist(self) -> float:
        return float(self._distanceEdit.text())

    @property
    def targetDose(self) -> float:
        return float(self._doseEdit.text())

    @property
    def rangeShifterDensity(self):
        return float(self._rsDensityEdit.text())

    @property
    def cemDensity(self):
        return float(self._cemDensityEdit.text())

    @property
    def spotSpacing(self):
        return float(self._spotSpacingEdit.text())


class ROIPanel(QWidget):
  def __init__(self, viewController, parent=None):
    super().__init__(parent)

    self.selectionEvent = Event(object)

    self.items:Sequence[ROIItem] = []
    self.layout = QVBoxLayout()
    self._patient = None
    self._viewController = viewController

    self.setLayout(self.layout)

    self.setCurrentPatient(self._viewController.currentPatient)
    self._viewController.currentPatientChangedSignal.connect(self.setCurrentPatient)

  @property
  def selected(self):
      selected  = []

      for item in self.items:
          if item.isChecked():
              selected.append(item)

      return selected

  def addRTStruct(self, rtStruct:RTStruct):
    for contour in rtStruct.contours:
      checkbox = ROIItem(ROIContourForViewer(contour), self._viewController)
      checkbox.selectedEvent.connect(self.selectionEvent.emit)

      self.layout.addWidget(checkbox)
      self.items.append(checkbox)

    self.layout.addStretch()

  def addROIMask(self, roiMask:ROIMask):
    checkbox = ROIItem(ROIMaskForViewer(roiMask), self._viewController)
    checkbox.selectedEvent.connect(self.selectionEvent.emit)

    self.layout.addWidget(checkbox)
    self.items.append(checkbox)
    self.layout.addStretch()

  def removeRTStruct(self, rtStruct:RTStruct):
    for contour in rtStruct.contours:
      for item in self.items:
        if item._contour == contour:
          self.layout.removeWidget(item)
          item.setParent(None)
          return

  def setCurrentPatient(self, patient:Patient):
    if patient==self._patient:
      return

    self._patient = patient
    for rtStruct in self._patient.rtStructs:
      self.addRTStruct(rtStruct)

    for roiMask in self._patient.roiMasks:
      self.addROIMask(roiMask)

    self._patient.rtStructAddedSignal.connect(self.addRTStruct)
    self._patient.rtStructRemovedSignal.connect(self.removeRTStruct)

    self._patient.roiMaskAddedSignal.connect(self.addROIMask)
    #TODO remove ROI mask


class ROIItem(QCheckBox):
  def __init__(self, contour, viewController):
    super().__init__(contour.name)

    self._contour = contour
    self._viewController = viewController

    self.selectedEvent = Event(object)

    self.setChecked(self._contour.visible)

    self._contour.visibleChangedSignal.connect(self.setChecked)

    self.clicked.connect(lambda c: self.handleClick(c))

    pixmap = QPixmap(100, 100)
    pixmap.fill(QColor(contour.color[0], contour.color[1], contour.color[2], 255))
    self.setIcon(QIcon(pixmap))

  @property
  def contour(self):
    return self._contour.data

  def handleClick(self, isChecked):
    self._contour.visible = isChecked
    self.selectedEvent.emit(self._contour.data)