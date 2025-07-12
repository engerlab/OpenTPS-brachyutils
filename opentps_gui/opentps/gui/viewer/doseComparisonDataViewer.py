from typing import Optional

from opentps.core.data.images import DoseImage
from opentps.core.data.images._image3D import Image3D
from opentps.gui.viewer.dataViewerComponents.doseComparisonImageProvider import DoseComparisonImageProvider
from opentps.gui.viewer.dataViewer import DataViewer


class DoseComparisonDataViewer(DataViewer):
    def __init__(self, viewController):
        self._displayDoseComparison = False
        self._doseComparisonImageProvider = DoseComparisonImageProvider()

        super().__init__(viewController)


    ####################################################################################################################
    # This is the logical part of the viewer. Should we migrate this to a dedicated controller?
    def _initializeControl(self):
        super()._initializeControl()

        self._imageViewerActions.doseComparisonDataViewer = self

        self.displayTypeChangedSignal.connect(self._handleDisplayTypeChange)

        self._viewController.dose1ChangedSignal.connect(self._setDose1)
        self._viewController.dose2ChangedSignal.connect(self._setDose2)

    @property
    def comparisonMetric(self):
        return self._doseComparisonImageProvider.comparisonMetric

    @comparisonMetric.setter
    def comparisonMetric(self, metric):
        self._doseComparisonImageProvider.comparisonMetric = metric

    def _handleDisplayTypeChange(self, displayType):
        super()._handleDisplayTypeChange(displayType)

        if not self._displayDoseComparison:
            self._doseComparisonImageProvider.doseComparisonImageChangedSignal.disconnect(self._handleNewDoseComparisonImage)

    def _handleNewDoseComparisonImage(self, *ags):
        self._setSecondaryImage(self._doseComparisonImageProvider.doseComparisonImage)

    def _setSecondaryImage(self, image:Optional[Image3D]):
        if not self._displayDoseComparison:
            super()._setSecondaryImage(image)

        if image != self._doseComparisonImageProvider.doseComparisonImage:
            self._displayDoseComparison = False

        if image is None:
            oldImage = self.cachedStaticImage3DViewer.secondaryImage
            if oldImage is None:
                return
        elif not (image.patient is None):
            image.patient.imageRemovedSignal.connect(self._removeImageFromViewers)

        self.cachedStaticImage3DViewer.secondaryImage = image

        if self._displayDoseComparison:
            self._imageViewerActions.setImageViewer(self._currentViewer)
            self._imageViewerActions.hide()
        else:
            self.cachedStaticDVHViewer.dose2 = None

    def _setDose1(self, image:Optional[DoseImage]):
        self._doseComparisonImageProvider.doseComparisonImageChangedSignal.disconnect(self._handleNewDoseComparisonImage)

        self._displayDoseComparison = True
        self._doseComparisonImageProvider.doseComparisonImageChangedSignal.connect(self._handleNewDoseComparisonImage)
        self._handleNewDoseComparisonImage()

        image.patient.imageRemovedSignal.connect(self._removeImageFromViewers)

        self._doseComparisonImageProvider.dose1 = image
        self._dvhViewer.dose = image

    def _setDose2(self, image:Optional[DoseImage]):
        self._doseComparisonImageProvider.doseComparisonImageChangedSignal.disconnect(self._handleNewDoseComparisonImage)

        self._displayDoseComparison = True
        self._doseComparisonImageProvider.doseComparisonImageChangedSignal.connect(self._handleNewDoseComparisonImage)
        self._handleNewDoseComparisonImage()

        image.patient.imageRemovedSignal.connect(self._removeImageFromViewers)

        self._doseComparisonImageProvider.dose2 = image
        self._dvhViewer.dose2 = image

    def _setDVHDose(self, image:Optional[DoseImage]):
        if not self._displayDoseComparison:
            self.cachedStaticDVHViewer.dose2 = None
            super()._setDVHDose(image)
        else:
            return
