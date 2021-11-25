from PyQt5.QtCore import QObject


class ModelController(QObject):
    apiMethods = object

    def __init__(self):
        QObject.__init__(self)
