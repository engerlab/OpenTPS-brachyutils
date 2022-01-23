
class DataForViewer(object):
    _allViewerDatas = []

    def __new__(cls, data):
        if isinstance(data, DataForViewer):
            data.__class__ = cls # Subclass the existing DataForViewer
            return data

        if data is None:
            return None

        # if there is already a DataForViewer for this data instance
        for viewerData in DataForViewer._allViewerDatas:
            if viewerData.data == data:
                # we might need to subclass the existing DataForViewer:
                return DataForViewer.__new__(cls, viewerData)

        # else
        viewerData = super().__new__(cls)
        DataForViewer._allViewerDatas.append(viewerData)

        return viewerData

    def __init__(self, data):
        if isinstance(data, DataForViewer):
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
        except:
            if item=='data':
                raise()
            return self.data.__getattribute__(item)
