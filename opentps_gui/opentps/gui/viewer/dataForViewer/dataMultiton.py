
class DataMultiton(object):
    _allViewerDatas = []

    def __new__(cls, data):
        if data is None:
            return None

        # if there is already a DataMultiton for this data instance
        for dataMultiton in DataMultiton._allViewerDatas:
            if dataMultiton.data == data:
                dataMultiton.subClass(cls)
                return dataMultiton

        # else
        dataMultiton = super().__new__(cls)
        DataMultiton._allViewerDatas.append(dataMultiton)
        return dataMultiton

    def subClass(self, cls):
        self.__class__ = cls  # Subclass the existing DataMultiton

    def __init__(self, data):
        if data is None:
            return

        if hasattr(self, 'data'):
            return

        super().__init__()
        self.data = data

    def __getattribute__(self, item):
        try:
            return object.__getattribute__(self, item)
        except:
            # we cannot return data from data
            if item=='data':
                raise AttributeError("data not initialized in DataMultiton")
            return self.data.__getattribute__(item)
