import functools
from typing import Sequence

import matplotlib
from PyQt5.QtWidgets import QComboBox, QWidgetAction, QMenu, QAction

from opentps.gui.viewer.dataForViewer.image3DForViewer import Image3DForViewer
from opentps.gui.viewer.dataViewerComponents.dataViewerToolbar import DataViewerToolbar
from opentps.gui.viewer.dataViewerComponents.doseComparisonImageProvider import DoseComparisonImageProvider
from opentps.gui.viewer.dataViewerComponents.image3DViewer import Image3DViewer
from opentps.gui.viewer.dataViewerComponents.imageFusionPropEditor import ImageFusionPropEditor


class ImageViewerActions:
    def __init__(self, imageViewer:Image3DViewer):
        self._imageViewer = imageViewer

        self._viewTypeToStr = {self._imageViewer.ViewerTypes.AXIAL: 'Axial',
                               self._imageViewer.ViewerTypes.CORONAL: 'Coronal',
                               self._imageViewer.ViewerTypes.SAGITTAL: 'Sagittal'}
        self._strToViewType = {v: k for k, v in self._viewTypeToStr.items()}

        self._separator = None

        self._viewTypeCombo = QComboBox()
        self._viewTypeCombo.setFixedSize(80, 16)
        self._viewTypeCombo.addItems(list(self._viewTypeToStr.values()))

        self._viewTypeAction = QWidgetAction(None)
        self._viewTypeAction.setDefaultWidget(self._viewTypeCombo)

        self._primaryImageMenu = PrimaryImageMenu(self._imageViewer)
        self._secondaryImageMenu = SecondaryImageMenu(self._imageViewer)
        self._doseComparisonMenu = DoseComparisonMenu(self._imageViewer)
        self._rtPlanMenu = RTPlanMenu(self._imageViewer)

        self.hide()

        self._viewTypeCombo.setCurrentIndex(self._viewTypeToIndex(self._imageViewer.viewType))
        self._viewTypeCombo.currentIndexChanged.connect(self._handleViewTypeSelection)
        self._imageViewer.viewTypeChangedSignal.connect(self._handleExternalViewTypeChange)

    @property
    def doseComparisonDataViewer(self):
        return self._doseComparisonMenu.dataViewer

    @doseComparisonDataViewer.setter
    def doseComparisonDataViewer(self, dataViewer):
        self._doseComparisonMenu.dataViewer = dataViewer


    def _viewTypeToIndex(self, viewType):
        return list(self._viewTypeToStr.keys()).index(viewType)

    def setImageViewer(self, imageViewer):
        self._imageViewer = imageViewer

    def addToToolbar(self, toolbar:DataViewerToolbar):
        self._separator = toolbar.addSeparator()
        toolbar.addAction(self._viewTypeAction)
        toolbar.toolsMenu.addMenu(self._primaryImageMenu)
        toolbar.toolsMenu.addMenu(self._secondaryImageMenu)
        toolbar.toolsMenu.addMenu(self._doseComparisonMenu)
        toolbar.toolsMenu.addMenu(self._rtPlanMenu)

    def hide(self):
        if not self._separator is None:
            self._separator.setVisible(False)
        self._viewTypeAction.setVisible(False)

    def show(self):
        self._separator.setVisible(True)
        self._viewTypeAction.setVisible(True)

    def _handleViewTypeSelection(self, selectionIndex):
        selectionText = self._viewTypeCombo.itemText(selectionIndex)
        self._imageViewer.viewType = self._strToViewType[selectionText]

    def _handleExternalViewTypeChange(self, viewType):
        self._viewTypeCombo.setCurrentIndex(self._viewTypeToIndex(viewType))


class PrimaryImageMenu(QMenu):
    def __init__(self, imageViewer:Image3DViewer):
        super().__init__("Primary image")

        self._imageViewer = imageViewer

        self._wwlMenu = QMenu("Window level/width", self)
        self.addMenu(self._wwlMenu)

        self._presetMenu = QMenu("Presets", self)
        self._wwlMenu.addMenu(self._presetMenu)

        self._wwlActions = []
        for ps in presets():
            wwlAction = QAction(ps.name + ' ' + str((ps.wwl[1], ps.wwl[0])), self)
            wwlAction.triggered.connect(functools.partial(self._setPreset, ps))

            self._wwlActions.append(wwlAction)

            self._presetMenu.addAction(wwlAction)

    def _setPreset(self, ps):
        Image3DForViewer(self._imageViewer.primaryImage).wwlValue = ps.wwl

class SecondaryImageMenu(QMenu):
    def __init__(self, imageViewer:Image3DViewer):
        super().__init__("Secondary image")

        self._imageViewer = imageViewer
        self._secondaryImageLayer = self._imageViewer.secondaryImageLayer

        self._resetAction = QAction("Reset", self)
        self._resetAction.triggered.connect(self._resetImage)
        self.addAction(self._resetAction)

        self._colorMapMenu = QMenu("Colormap", self)
        self.addMenu(self._colorMapMenu)

        self._colormapActions = []
        cms = matplotlib.pyplot.colormaps()

        for cm in cms:
            cmAction = QAction(cm, self._colorMapMenu)
            cmAction.triggered.connect(functools.partial(self.setFusion, cm))
            self._colorMapMenu.addAction(cmAction)
            self._colormapActions.append(cmAction)

        self._colorbarAction = QAction("Show/hide colorbar", self)
        self._colorbarAction.triggered.connect(self._setColorbarOnOff)
        self.addAction(self._colorbarAction)

        self._wwlAction = QAction("Window level/width", self)
        self._wwlAction.triggered.connect(self._showImageProperties)
        self.addAction(self._wwlAction)

    def _resetImage(self):
        self._imageViewer.secondaryImage = None

    def _setColorbarOnOff(self):
        self._secondaryImageLayer.colorbarOn = not self._secondaryImageLayer.colorbarOn

    def _showImageProperties(self):
        self._imageFusionProp = ImageFusionPropEditor(self._secondaryImageLayer.image.data)
        self._imageFusionProp.show()

    def setFusion(self, name:str):
        self._imageViewer.secondaryImageLayer.image.lookupTableName = name

class DoseComparisonMenu(QMenu):
    def __init__(self, imageViewer:Image3DViewer):
        super().__init__("Dose comparison")

        self.dataViewer = None

        self._imageViewer = imageViewer
        self._secondaryImageLayer = self._imageViewer.secondaryImageLayer

        self._metricsMenu = QMenu("Metrics", self)
        self.addMenu(self._metricsMenu)

        self._diffAction = QAction("Difference", self._metricsMenu)
        self._diffAction.triggered.connect(self._setDiffMetric)
        self._metricsMenu.addAction(self._diffAction)
        self._absDiffAction = QAction("Absolute difference", self._metricsMenu)
        self._absDiffAction.triggered.connect(self._setAbsDiffMetric)
        self._metricsMenu.addAction(self._absDiffAction)
        self._gammaAction = QAction("Gamma", self._metricsMenu)
        self._gammaAction.triggered.connect(self._setGammaMetric)
        self._metricsMenu.addAction(self._gammaAction)

        self._colorMapMenu = QMenu("Colormap", self)
        self.addMenu(self._colorMapMenu)

        self._colormapActions = []
        cms = matplotlib.pyplot.colormaps()

        for cm in cms:
            cmAction = QAction(cm, self._colorMapMenu)
            cmAction.triggered.connect(functools.partial(self.setFusion, cm))
            self._colorMapMenu.addAction(cmAction)
            self._colormapActions.append(cmAction)

        self._colorbarAction = QAction("Show/hide colorbar", self)
        self._colorbarAction.triggered.connect(self._setColorbarOnOff)
        self.addAction(self._colorbarAction)

        self._wwlAction = QAction("Window level/width", self)
        self._wwlAction.triggered.connect(self._showImageProperties)
        self.addAction(self._wwlAction)

    def _setColorbarOnOff(self):
        self._secondaryImageLayer.colorbarOn = not self._secondaryImageLayer.colorbarOn

    def _showImageProperties(self):
        self._imageFusionProp = ImageFusionPropEditor(self._secondaryImageLayer.image.data)
        self._imageFusionProp.show()

    def _setDiffMetric(self):
        self.dataViewer.comparisonMetric = DoseComparisonImageProvider.Metric.DIFFERENCE
    def _setAbsDiffMetric(self):
        self.dataViewer.comparisonMetric = DoseComparisonImageProvider.Metric.ABSOLUTE_DIFFERENCE
    def _setGammaMetric(self):
        self.dataViewer.comparisonMetric = DoseComparisonImageProvider.Metric.GAMMA

    def setFusion(self, name:str):
        self._imageViewer.secondaryImageLayer.lookupTableName = name

class RTPlanMenu(QMenu):
    def __init__(self, imageViewer:Image3DViewer):
        super().__init__("RT plan")

        self._imageViewer = imageViewer

        self._resetAction = QAction("Reset", self)
        self._resetAction.triggered.connect(self._resetPlan)
        self.addAction(self._resetAction)

    def _resetPlan(self):
        self._imageViewer.rtPlan = None

class WWLPreset:
    def __init__(self, name:str, wwl:Sequence[float]):
        self.name:str = name
        self.wwl:Sequence[float] = wwl

def presets() -> Sequence[WWLPreset]:
    presets = []

    ps = WWLPreset("Bone", (1600, 450))
    presets.append(ps)
    ps = WWLPreset("Brain", (100, 35))
    presets.append(ps)
    ps = WWLPreset("Dental", (2000, 400))
    presets.append(ps)
    ps = WWLPreset("Inner ear", (4000, 700))
    presets.append(ps)
    ps = WWLPreset("Larynx", (250, 40))
    presets.append(ps)
    ps = WWLPreset("Liver", (350, 50))
    presets.append(ps)
    ps = WWLPreset("Lung", (1600, -600))
    presets.append(ps)
    ps = WWLPreset("Mediastinum", (400, 40))
    presets.append(ps)
    ps = WWLPreset("Pelvis", (1000, 250))
    presets.append(ps)
    ps = WWLPreset("Soft tissue", (350, 40))
    presets.append(ps)
    ps = WWLPreset("Spine", (300, 35))
    presets.append(ps)
    ps = WWLPreset("Vertebrae", (2000, 350))
    presets.append(ps)

    return presets
