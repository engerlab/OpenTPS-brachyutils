import os
import threading
from typing import Sequence, Tuple

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QVBoxLayout, QLabel, QLineEdit, QMainWindow, \
    QFrame, QTableWidget, QTableWidgetItem, QGridLayout

from Core.Data.CTCalibrations.RayStationCalibration.rayStationCTCalibration import RayStationCTCalibration
from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.doseImage import DoseImage
from Core.Data.Images.image3D import Image3D
from Core.Data.Plan.rtPlan import RTPlan
from Core.Data.dvh import DVH
from Core.Data.roiContour import ROIContour
from Core.IO import mcsquareIO
from Core.Processing.ImageProcessing import imageTransform3D
from Core.event import Event
from Extensions.FLASH.Core.Processing.CEMOptimization import cemObjectives, workflows
from Extensions.FLASH.Core.Processing.CEMOptimization.workflows import SingleBeamCEMOptimizationWorkflow
from Extensions.FLASH.GUI.convergencePlot import ConvergencePlot
from GUI.Panels.patientDataPanel import PatientDataTree, PatientComboBox
from GUI.Viewer.DataForViewer.image3DForViewer import Image3DForViewer
from GUI.Viewer.DataViewerComponents.dvhPlot import DVHPlot
from GUI.Viewer.DataViewerComponents.imageViewer import ImageViewer

import Extensions.FLASH.DefaultData as defaultDataModule


class FlashWindow(QMainWindow):
    def __init__(self, viewController, parent=None):
        super().__init__(parent)

        self._viewController = viewController

        self._dvhs = []

        self.setWindowTitle('FLASH TPS')
        self.resize(800, 600)

        self.centralWidget = QWidget()
        self.setCentralWidget(self.centralWidget)
        self._mainLayout = QHBoxLayout()
        self.centralWidget.setLayout(self._mainLayout)

        self._leftPanel = UserInputPanel((self._viewController), self)
        self._leftPanel.setFixedWidth(400)

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
        self._bottomLayout = QGridLayout()
        self._bottomFrame.setLayout(self._bottomLayout)

        self._convergencePlot = ConvergencePlot()
        self._convergencePlot.setMinimumWidth(400)
        self._bottomLayout.addWidget(self._convergencePlot, 0, 0)

        self._dvhPlot = DVHPlot(self)
        self._dvhPlot.setMinimumWidth(400)
        self._bottomLayout.addWidget(self._dvhPlot, 0, 1)

        self._leftPanel.ctSelectedEvent.connect(self._viewers.setCT)
        self._leftPanel.doseUpdateEvent.connect(self._viewers.setDose)
        self._leftPanel.doseUpdateEvent.connect(self._updateDVHWithDose)
        self._leftPanel.fValEvent.connect(self._convergencePlot.appendFVal)
        self._leftPanel.contourSelectedEvent.connect(self._createDVHs)
        self._leftPanel.planUpdateEvent.connect(self._viewers.setPlan)

    def _updateDVHWithDose(self, dose:DoseImage):
        for dvh in self._dvhs:
            dvh.dose = dose
            dvh.computeDVH()

    def _createDVHs(self, rois):
        for dvh in self._dvhs:
            self._dvhPlot.removeDVH(dvh)

        self._dvhs = []
        for roi in rois:
            dvh = DVH(roi)
            self._dvhPlot.appendDVH(dvh, roi)
            self._dvhs.append(dvh)

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

    def setPlan(self, plan:RTPlan):
        self._viewer0.rtPlan = plan
        self._viewer1.rtPlan = plan
        self._viewer2.rtPlan = plan

    def _convertROIToMask(self):
        if isinstance(self._roi, ROIContour):
            if not self._ct is None:
                self._roi = self._roi.getBinaryMask(self._ct.origin, self._ct.gridSize, self._ct.spacing)

    def _setCTPositionToROICenter(self):
        if not self._ct is None:
            Image3DForViewer(self._ct).selectedPosition = self._roi.centerOfMass


class UserInputPanel(QWidget):
    _RUN_TXT = 'Run!'
    _CANCEL_TXT = 'Cancel!'
    _CANCELLING_TXT = 'Cancelling...'

    def __init__(self, viewController, parent=None):
        super().__init__(parent)

        self.ctSelectedEvent = Event(Image3D)
        self.doseUpdateEvent = Event(Image3D)
        self.contourSelectedEvent = Event(object)
        self.planUpdateEvent = Event(RTPlan)
        self.fValEvent = Event(Tuple)

        self._viewController = viewController

        self._WorkflowThread = None

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
        self._roiLabel.setText('Objectives:')
        self._mainLayout.addWidget(self._roiLabel)

        self._roiTable = ROITable(self._viewController, parent=self)
        self._mainLayout.addWidget(self._roiTable)

        self._beamEditor = BeamEditor(self)
        self._mainLayout.addWidget(self._beamEditor)

        self.runButton = QPushButton(self._RUN_TXT)
        self.runButton.clicked.connect(self._run)
        self._mainLayout.addWidget(self.runButton)

        self.cemOptimizer = SingleBeamCEMOptimizationWorkflow()
        self.cemOptimizer.doseUpdateEvent.connect(self._updateDose)
        self.cemOptimizer.planUpdateEvent.connect(self._updateCT)
        self.cemOptimizer.planUpdateEvent.connect(self.planUpdateEvent.emit)
        self.cemOptimizer.fValEvent.connect(self.fValEvent.emit)

    def _emitCT(self):
        selected = self.patientDataTree.selectedIndexes()
        selectedCT = [self.patientDataTree.model().itemFromIndex(selectedData).data for selectedData in selected]

        self.ctSelectedEvent.emit(selectedCT[0])

    def _run(self):
        if not (self._WorkflowThread is None):
            self._cancel()
            return

        selected = self.patientDataTree.selectedIndexes()
        selectedCT = [self.patientDataTree.model().itemFromIndex(selectedData).data for selectedData in selected]

        if len(selectedCT)>1:
            raise Exception('Only 1 CT can be selected')

        defaultDataPath = defaultDataModule.__path__[0]

        self.cemOptimizer.ctCalibration = RayStationCTCalibration(
            fromFiles=(defaultDataPath + os.path.sep + 'calibration_RS' + os.path.sep + 'calibration_cef.txt', defaultDataPath + os.path.sep + 'calibration_RS' + os.path.sep + 'materials_cef.txt'))
        self.cemOptimizer.beamModel = mcsquareIO.readBDL(defaultDataPath + os.path.sep + 'BDL_default_RS_Leuven_4_5_5.txt')
        self.cemOptimizer.gantryAngle = self._beamEditor.beamAngle
        self.cemOptimizer.apertureToIsocenter = self._beamEditor.apertureIsoDist
        self.cemOptimizer.beamEnergy = self._beamEditor.beamEnergy
        self.cemOptimizer.ct = selectedCT[0]
        self.cemOptimizer.spotSpacing = self._beamEditor.spotSpacing
        self.cemOptimizer.apertureDensity = self.cemOptimizer.ctCalibration.convertMassDensity2RSP(self._beamEditor.apertureDensity)
        self.cemOptimizer.cemRSP = self.cemOptimizer.ctCalibration.convertMassDensity2RSP(self._beamEditor.cemDensity)
        self.cemOptimizer.rangeShifterRSP = self.cemOptimizer.ctCalibration.convertMassDensity2RSP(self._beamEditor.rangeShifterDensity)
        self.cemOptimizer.objectives = self._roiTable.getObjectiveTerms()

        self.contourSelectedEvent.emit(self._roiTable.getROIs())

        self._WorkflowThread = threading.Thread(target=self.cemOptimizer.run)
        globalThread = threading.Thread(target=self._startrunThread)
        globalThread.start()

    def _startrunThread(self):
        self.runButton.setText(self._CANCEL_TXT)
        self._WorkflowThread.start()
        self._WorkflowThread.join()
        self.runButton.setText(self._RUN_TXT)

    def _cancel(self):
        self.runButton.setText(self._CANCELLING_TXT)
        self.runButton.setEnabled(False)
        self.cemOptimizer.abort()
        self._WorkflowThread.join()
        self.runButton.setText(self._RUN_TXT)
        self.runButton.setEnabled(True)

    def _updateDose(self, dose):
        Image3DForViewer(dose).range = [0, 41]

        self.doseUpdateEvent.emit(dose)

    def _updateCT(self, plan:RTPlan):
        ct = CTImage.fromImage3D(self.cemOptimizer.ct)

        # Update CT with CEM
        for beam in plan:
            cem = beam.cem

            if cem is None:
                continue

            if not cem.imageArray is None:
                [rsROI, cemROI] = cem.computeROIs()

                ct = imageTransform3D.intersect(ct, rsROI, fillValue=-1024, inPlace=False)

                ctArray = ct.imageArray
                ctArray[cemROI.imageArray.astype(bool)] = self.cemOptimizer.ctCalibration.convertRSP2HU(cem.cemRSP, energy=100.)
                ctArray[rsROI.imageArray.astype(bool)] = self.cemOptimizer.ctCalibration.convertRSP2HU(cem.rangeShifterRSP, energy=100.)

                if not (beam.aperture is None):
                    apertureROI = beam.aperture.computeROI()
                    apertureROI = imageTransform3D.intersect(apertureROI, ct, fillValue=0)
                    ctArray = ct.imageArray
                    ctArray[apertureROI.imageArray.astype(bool)] = self.cemOptimizer.ctCalibration.convertRSP2HU(beam.aperture.rsp, energy=100.)

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
        self._distanceLabel.setText('Aperture-isocenter distance: ')
        self._apertureDensityLabel = QLabel(self)
        self._apertureDensityLabel.setText('Aperture density: ')
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
        self._apertureDensityEdit = QLineEdit(self)
        self._apertureDensityEdit.setText(str(8.73))
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
        self._mainLayout.addWidget(self._spotSpacingLabel)
        self._mainLayout.addWidget(self._spotSpacingEdit)
        self._mainLayout.addWidget(self._apertureDensityLabel)
        self._mainLayout.addWidget(self._apertureDensityEdit)
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
    def apertureIsoDist(self) -> float:
        return float(self._distanceEdit.text())

    @property
    def apertureDensity(self) -> float:
        return float(self._apertureDensityEdit.text())

    @property
    def rangeShifterDensity(self):
        return float(self._rsDensityEdit.text())

    @property
    def cemDensity(self):
        return float(self._cemDensityEdit.text())

    @property
    def spotSpacing(self):
        return float(self._spotSpacingEdit.text())


class ROITable(QTableWidget):
    DMIN_THRESH = 0.
    DMAX_THRESH = 999.
    DEFAULT_WEIGHT = 1.

    def __init__(self, viewController, parent=None):
        super().__init__(100, 4, parent)

        self._rois = []

        self._viewController = viewController
        self._fillRoiTable()
        self.resizeColumnsToContents()
        self.resizeRowsToContents()


    def _fillRoiTable(self):
        patient = self._viewController.currentPatient

        self._rois = []
        i = 0
        for rtStruct in patient.rtStructs:
            for contour in rtStruct.contours:
                newitem = QTableWidgetItem(contour.name)
                self.setItem(i, 0, newitem)
                self.setItem(i, 1, QTableWidgetItem(str(self.DEFAULT_WEIGHT)))
                self.setItem(i, 2, QTableWidgetItem(str(self.DMIN_THRESH)))
                self.setItem(i, 3, QTableWidgetItem(str(self.DMAX_THRESH)))

                self._rois.append(contour)

                i += 1

        for roiMask in patient.roiMasks:
            newitem = QTableWidgetItem(roiMask.name)
            self.setItem(i, 0, newitem)
            self.setItem(i, 1, QTableWidgetItem(str(self.DEFAULT_WEIGHT)))
            self.setItem(i, 2, QTableWidgetItem(str(self.DMIN_THRESH)))
            self.setItem(i, 3, QTableWidgetItem(str(self.DMAX_THRESH)))

            self._rois.append(roiMask)

            i += 1

        self.setHorizontalHeaderLabels(['ROI', 'Weight', 'Dmin', 'Dmax'])

    def getObjectiveTerms(self) -> Sequence[workflows.Objective]:
        terms = []

        for i in range(len(self._rois)):
            weight = float(self.item(i, 1).text())
            # Dmin
            dmin = float(self.item(i, 2).text())
            if dmin > self.DMIN_THRESH:
                obj = cemObjectives.DoseMinObjective(self._rois[i], dmin)
                objective = workflows.Objective(objectiveTerm=obj, weight=weight)
                terms.append(objective)
            # Dmax
            dmax = float(self.item(i, 3).text())
            if dmax < self.DMAX_THRESH:
                obj = cemObjectives.DoseMaxObjective(self._rois[i], dmax)
                objective = workflows.Objective(objectiveTerm=obj, weight=weight)
                terms.append(objective)

        return terms

    def getROIs(self):
        rois = []

        for i in range(len(self._rois)):
            # Dmin
            dmin = float(self.item(i, 2).text())
            if dmin > self.DMIN_THRESH:
                rois.append(self._rois[i])
            # Dmax
            dmax = float(self.item(i, 3).text())
            if dmax < self.DMAX_THRESH:
                rois.append(self._rois[i])

        return rois
