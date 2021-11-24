from PyQt5.QtCore import QObject


class DataController(QObject):
    _allDataControllers = []

    def __new__(cls, data):
        if isinstance(data, cls):
            return data

        if data is None:
            return None

        # if there is already a data controller for this data instance
        for controller in cls._allDataControllers:
            if controller.data == data:
                return controller

        # else
        dataController = super(DataController, cls).__new__(DataController)
        DataController._allDataControllers.append(dataController)

        return dataController

    def __init__(self, data):
        if isinstance(data, self.__class__):
            return

        if data is None:
            return

        #else
        self.data = data

        super(DataController, self).__init__()
        