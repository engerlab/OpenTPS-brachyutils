
import os
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import *


class ImageViewer(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self.data = 2


class DynamicImageViewer(ImageViewer):
    def __init__(self):
        super().__init__()


if __name__ == '__main__':

    app = QApplication.instance()
    if not app:
        app = QApplication([])

    app.exec_()

imgViewer = ImageViewer()
dynViewer = DynamicImageViewer

print(type(imgViewer))
print(type(dynViewer))