import inspect

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QApplication, QLineEdit

from Core.event import Event


class ImagePropEditor(QWidget):
    def __init__(self, image, parent=None):
        super().__init__(parent=parent)

        self._mainLayout = QVBoxLayout(self)
        self.setLayout(self._mainLayout)

        for property in inspect.getmembers(image):
            # to remove private and protected
            # functions
            if not property[0].startswith('_'):
                # To remove other methods that
                # doesnot start with a underscore
                if not inspect.ismethod(property[1]):
                    if not isinstance(property[1], Event):
                        self._mainLayout.addWidget(TwoRowElement(property, parent=self))


class TwoRowElement(QWidget):
    def __init__(self, property, parent=None):
        super().__init__(parent)

        self._mainLayout = QHBoxLayout(self)
        self.setLayout(self._mainLayout)

        self._txt = QLabel(self)
        self._txt.setText(property[0])
        self._nameLineEdit = QLineEdit(self)

        val = property[1]
        self._nameLineEdit.setText(str(val))
        self._txt.setBuddy(self._nameLineEdit)

        self._mainLayout.addWidget(self._txt)
        self._mainLayout.addWidget(self._nameLineEdit)




