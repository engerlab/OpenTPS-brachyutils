from PyQt5.QtCore import QObject

class APIMethods:
    pass


class ModelController(QObject):
    apiMethods = APIMethods()

    def __init__(self):
        QObject.__init__(self)

    def getAPI(self):
        return self.apiMethods
