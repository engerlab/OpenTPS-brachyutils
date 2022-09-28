from PyQt5.QtWidgets import *
from PyQt5.QtGui import QColor, QPixmap, QIcon

from opentps.core.data.images import ROIMask
from opentps.core.data._patient import Patient
from opentps.core.data._roiContour import ROIContour
from opentps.core.data._rtStruct import RTStruct
from opentps.gui.viewer.dataForViewer.ROIContourForViewer import ROIContourForViewer
from opentps.gui.viewer.dataForViewer.ROIMaskForViewer import ROIMaskForViewer


class ROIPanel(QWidget):
  def __init__(self, viewController):
    QWidget.__init__(self)

    self.items = []
    self.layout = QVBoxLayout()
    self._patient = None
    self._viewController = viewController

    self.setLayout(self.layout)

    self._filterEdit = QLineEdit(self)
    self._filterEdit.setPlaceholderText('Filter')
    self._filterEdit.textEdited.connect(self._setFilteredROIs)
    self.layout.addWidget(self._filterEdit)

    self._listFrame = QFrame(self)
    self.layout.addWidget(self._listFrame)
    self._listLayout = QVBoxLayout()
    self._listFrame.setLayout(self._listLayout)

    self.layout.addStretch()

    self.setCurrentPatient(self._viewController.currentPatient)
    self._viewController.currentPatientChangedSignal.connect(self.setCurrentPatient)

  def setCurrentPatient(self, patient:Patient):
    if patient==self._patient:
      return
    elif not self._patient is None:
      self._patient.rtStructAddedSignal.disconnect(self._setFilteredROIs)
      self._patient.rtStructRemovedSignal.disconnect(self._setFilteredROIs)
      self._patient.roiMaskAddedSignal.disconnect(self._setFilteredROIs)
      self._patient.roiMaskRemovedSignal.disconnect(self._setFilteredROIs)

      self._resetList()

    self._patient = patient

    self._setFilteredROIs()

    if not (self._patient is None):
      self._patient.rtStructAddedSignal.connect(self._setFilteredROIs)
      self._patient.rtStructRemovedSignal.connect(self._setFilteredROIs)
      self._patient.roiMaskAddedSignal.connect(self._setFilteredROIs)
      self._patient.roiMaskRemovedSignal.connect(self._setFilteredROIs)

  def _resetList(self):
    for widget in self.items:
      if isinstance(widget, ROIItem):
        widget.setVisible(False)
        self._listLayout.removeWidget(widget)
    self.items = []

  def _setFilteredROIs(self, *args):
    if self._patient is None:
      return

    enteredText = self._filterEdit.text().lower()

    self._resetList()

    for rtStruct in self._patient.rtStructs:
      for contour in rtStruct.contours:
        if enteredText in contour.name.lower() or enteredText=='':
          self.addROIContour(contour)

    for roiMask in self._patient.roiMasks:
      if enteredText in roiMask.name.lower() or enteredText=='':
        self.addROIMask(roiMask)

  def addROIContour(self, contour:ROIContour):
      checkbox = ROIItem(ROIContourForViewer(contour), self._viewController)

      self._listLayout.addWidget(checkbox)
      self.items.append(checkbox)

  def addROIMask(self, roiMask:ROIMask):
    checkbox = ROIItem(ROIMaskForViewer(roiMask), self._viewController)

    self._listLayout.addWidget(checkbox)
    self.items.append(checkbox)

  def removeRTStruct(self, rtStruct:RTStruct):
    for contour in rtStruct.contours:
      for item in self.items:
        if item._contour == contour:
          self._listLayout.removeWidget(item)
          item.setParent(None)
          return

  def removeROIMask(self, roiMask:ROIMask):
    for item in self.items:
        if item._contour == roiMask:
          self._listLayout.removeWidget(item)
          item.setParent(None)
          return

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
    self._viewController.showContour(self._contour.data)
