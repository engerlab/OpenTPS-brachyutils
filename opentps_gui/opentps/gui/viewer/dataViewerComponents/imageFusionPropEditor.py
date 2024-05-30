from PyQt5.QtWidgets import QMainWindow, QGroupBox, QHBoxLayout, QWidget, QVBoxLayout, QLabel, QLineEdit
from matplotlib import pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.widgets import RangeSlider

from opentps.gui.viewer.dataForViewer.image3DForViewer import Image3DForViewer
from opentps.gui.viewer.dataViewerComponents.patientDataPropertyEditor import PatientDataPropertyEditor


class ImageFusionPropEditor(QMainWindow):
    def __init__(self, image, parent=None):
        super().__init__(parent)

        self.setWindowTitle('Secondary image')
        self.resize(800, 600)

        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        self._layout = QHBoxLayout()
        centralWidget.setLayout(self._layout)

        self._imageInfoGroup = QGroupBox(title='Image info')
        self._layout.addWidget(self._imageInfoGroup)
        vbox = QVBoxLayout()
        self._imageInfoGroup.setLayout(vbox)
        vbox.addWidget(PatientDataPropertyEditor(image, parent=self))

        self._imageProperties = QGroupBox(title='Image properties')
        self._layout.addWidget(self._imageProperties)
        vbox = QVBoxLayout()
        self._imageProperties.setLayout(vbox)


        image = Image3DForViewer(image)

        self._figure = plt.figure()

        axs = plt.axes([0.20, 0.3, 0.60, 0.6])
        n, bins, patches = axs.hist(image.imageArray.flatten(), bins=200)
        axs.set_title('Histogram of pixel intensities')
        axs.set_yscale('log')

        # Create the RangeSlider
        self._slider_ax = plt.axes([0.20, 0.1, 0.60, 0.03])
        self.slider = RangeSlider(self._slider_ax, "Range", bins[0], bins[-1], valinit=image.range, dragging=True)

        self.cm = plt.get_cmap(image.lookupTableName)

        bin_centers = 0.5 * (bins[:-1] + bins[1:])
        col = (bin_centers - image.range[0]) / (image.range[1] - image.range[0])
        for c, p in zip(col, patches):
            plt.setp(p, 'facecolor', self.cm(c))

        self.bin_centers = bin_centers
        self._image = image
        self.patches = patches
        self.slider.on_changed(self._update)

        self._canvas = FigureCanvasQTAgg(self._figure)
        vbox.addWidget(self._canvas)

        self._rangeEditor = RangeEditor(image)
        vbox.addWidget(self._rangeEditor)

        self._image.rangeChangedSignal.connect(self._updateSliderRange)

    def _updateSliderRange(self, range):
        self.slider.set_val(range)

    def _update(self, val):
        self._image.range = val
        col = (self.bin_centers - val[0]) / (val[1] - val[0])
        for c, p in zip(col, self.patches):
            plt.setp(p, 'facecolor', self.cm(c))

class RangeEditor(QWidget):
    def __init__(self, image, parent=None):
        super().__init__(parent)

        self._image = image

        self._mainLayout = QHBoxLayout(self)
        self.setLayout(self._mainLayout)

        self._txt = QLabel(self)
        self._txt.setText('Range: ')

        self._rangeEdit0 = QLineEdit(self)
        self._rangeEdit1 = QLineEdit(self)

        self._mainLayout.addWidget(self._txt)
        self._mainLayout.addWidget(self._rangeEdit0)
        self._mainLayout.addWidget(self._rangeEdit1)

        self._rangeEdit0.setText(str(self._image.range[0]))
        self._rangeEdit1.setText(str(self._image.range[1]))

        self._rangeEdit0.textEdited.connect(self._handleTextEdited)
        self._rangeEdit1.textEdited.connect(self._handleTextEdited)
        self._image.rangeChangedSignal.connect(self.setRangeValue)

    def setRangeValue(self, range):
        if float(self._rangeEdit0.text()) != range[0]:
            self._rangeEdit0.setText(str(range[0]))
        if float(self._rangeEdit1.text()) != range[1]:
            self._rangeEdit1.setText(str(range[1]))

    def _handleTextEdited(self, *args):
        self._image.range = (float(self._rangeEdit0.text()), float(self._rangeEdit1.text()))