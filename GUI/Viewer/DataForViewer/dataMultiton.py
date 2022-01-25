
class DataMultiton(object):
    _allViewerDatas = []

    def __new__(cls, data):
        if isinstance(data, DataMultiton):
            data.__class__ = cls # Subclass the existing ViewerData
            return data

        if data is None:
            return None

        # if there is already a ViewerData for this data instance
        for viewerData in DataMultiton._allViewerDatas:
            if viewerData.data == data:
                # we might need to subclass the existing ViewerData:
                return DataMultiton.__new__(cls, viewerData)

        # else
        viewerData = super().__new__(cls)
        DataMultiton._allViewerDatas.append(viewerData)

        return viewerData

    def __init__(self, data):
        if isinstance(data, DataMultiton):
            return

        if data is None:
            return

        try:
            if hasattr(self, 'data'):
                return
        except:
            pass

        super().__init__()
        self.data = data

    def __setattr__(self, key, value):
        object.__setattr__(self, key, value)

    def __getattribute__(self, item):
        try:
            return super().__getattribute__(item)
        except Exception as e:
            if item=='data':
                raise(e)
            return self.data.__getattribute__(item)
