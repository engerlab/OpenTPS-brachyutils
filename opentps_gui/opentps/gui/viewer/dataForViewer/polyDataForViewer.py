
from opentps.core import Event
from opentps.gui.viewer.dataForViewer.genericImageForViewer import GenericImageForViewer


class PolyDataForViewer(GenericImageForViewer):

    def __init__(self, vtkPolyData):
        super().__init__(vtkPolyData)

        if hasattr(self, 'dataChangedSignal'):
            return
        
        self.dataChangedSignal = Event()

    @property
    def vtkOutputPort(self):
        return self.GetOutputPort()
