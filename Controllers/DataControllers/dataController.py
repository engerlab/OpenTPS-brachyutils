from PyQt5.QtCore import QObject


class DataController(QObject):
    _allDataControllers = []

    def __new__(cls, data):
        if isinstance(data, DataController):
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

        #else
        # It is important to call super().__init__() now and not before because if we init QObject we loose previously initialized pyqtSignals
        super().__init__()
        self.data = data


if __name__ == '__main__':
    data1 = 'jlj'

    p1 = DataController(data1)
    print(p1.data)
    p2 = DataController('khkh')
    print(p2.data)
    p3 =  DataController(data1)
    print(p1 == p3)