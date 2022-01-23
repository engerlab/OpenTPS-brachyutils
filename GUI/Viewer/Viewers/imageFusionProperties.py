
from PyQt5.QtWidgets import QMainWindow, QGroupBox, QHBoxLayout, QWidget, QVBoxLayout
from matplotlib import pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.widgets import RangeSlider

from GUI.Viewer.DataForViewer.image3DForViewer import Image3DForViewer
from GUI.Viewer.Viewers.imageProperies import ImageProperties


class ImageFusionProperties(QMainWindow):
    def __init__(self, image, parent=None):
        super().__init__(parent)

        self.setWindowTitle('Secondary image')
        self.resize(400, 600)

        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        self._layout = QHBoxLayout()
        centralWidget.setLayout(self._layout)

        self._imageInfoGroup = QGroupBox(title='Image info')
        self._layout.addWidget(self._imageInfoGroup)
        vbox = QVBoxLayout()
        self._imageInfoGroup.setLayout(vbox)
        vbox.addWidget(ImageProperties(image, parent=self))

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

        self.cm = plt.cm.get_cmap('jet')

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

    def _update(self, val):
        self._image.range = val
        col = (self.bin_centers - val[0]) / (val[1] - val[0])
        for c, p in zip(col, self.patches):
            plt.setp(p, 'facecolor', self.cm(c))