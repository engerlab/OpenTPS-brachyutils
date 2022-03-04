from PyQt5.QtWidgets import *
from PyQt5.QtGui import QColor, QPixmap, QIcon

from Core.Data.Images.roiMask import ROIMask
from Core.Data.patient import Patient
from Core.Data.rtStruct import RTStruct
from GUI.Viewer.DataForViewer.ROIContourForViewer import ROIContourForViewer
from GUI.Viewer.DataForViewer.ROIMaskForViewer import ROIMaskForViewer


class ROIPanel(QWidget):
  def __init__(self, viewController):
    QWidget.__init__(self)

    self.items = []
    self.layout = QVBoxLayout()
    self._patient = None
    self._viewController = viewController

    self.setLayout(self.layout)

    self.setCurrentPatient(self._viewController.currentPatient)
    self._viewController.currentPatientChangedSignal.connect(self.setCurrentPatient)

  def addRTStruct(self, rtStruct:RTStruct):
    for contour in rtStruct.contours:
      checkbox = ROIItem(ROIContourForViewer(contour), self._viewController)

      self.layout.addWidget(checkbox)
      self.items.append(checkbox)

    self.layout.addStretch()

  def addROIMask(self, roiMask:ROIMask):
    checkbox = ROIItem(ROIMaskForViewer(roiMask), self._viewController)

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

    self.setChecked(self._contour.visible)

    self._contour.visibleChangedSignal.connect(self.setChecked)

    self.clicked.connect(lambda c: self.handleClick(c))

    pixmap = QPixmap(100, 100)
    pixmap.fill(QColor(contour.color[0], contour.color[1], contour.color[2], 255))
    self.setIcon(QIcon(pixmap))

  @property
  def contour(self):
    return self._contour

  def handleClick(self, isChecked):
    self._contour.visible = isChecked
    self._viewController.showContour(self._contour)
