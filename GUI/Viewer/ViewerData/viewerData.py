
class ViewerData:
    _allViewerDatas = []

    def __new__(cls, data):
        if isinstance(data, ViewerData):
            data.__class__ = cls # Subclass the existing ViewerData
            return data

        if data is None:
            return None

        # if there is already a ViewerData for this data instance
        for viewerData in ViewerData._allViewerDatas:
            if viewerData.data == data:
                # we might need to subclass the existing ViewerData:
                return ViewerData.__new__(cls, viewerData)

        # else
        viewerData = super().__new__(cls)
        ViewerData._allViewerDatas.append(viewerData)

        return ViewerData

    def __init__(self, data):
        if isinstance(data, ViewerData):
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
