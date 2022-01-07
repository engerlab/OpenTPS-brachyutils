from PyQt5.QtCore import QObject, pyqtSignal


class DataController(QObject):
    _allDataControllers = []

    nameChangedSignal = pyqtSignal(str)
    dataChangedSignal = pyqtSignal(object)

    def __new__(cls, data):
        if isinstance(data, DataController):
            data.__class__ = cls # Subclass the existing data controller
            return data

        if data is None:
            return None

        # if there is already a data controller for this data instance
        for controller in DataController._allDataControllers:
            if controller.data == data:
                # we might need to subclass the existign data controller:
                return DataController.__new__(cls, controller)

        # else
        dataController = super().__new__(cls)
        DataController._allDataControllers.append(dataController)

        return dataController

    def __init__(self, data):
        if isinstance(data, DataController):
            return

        if data is None:
            return

        try:
            hasattr(self, 'data')
            return
        except:
            pass

        #else
        # It is important to call super().__init__() now and not before because if we init QObject we loose previously initialized pyqtSignals
        super().__init__()
        self.data = data

    def __setattr__(self, key, value):
        object.__setattr__(self, key, value)

    def getType(self):
        return self.data.__class__.__name__

    def getName(self):
        return self.data.name

    def setName(self, name):
        self.data.name = name
        self.nameChangedSignal.emit(self.data.name)

    def notifyDataChange(self):
        self.dataChangedSignal.emit(self.data)


