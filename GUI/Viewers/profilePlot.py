from pyqtgraph import PlotWidget


class ProfilePlot(PlotWidget):
    def __init__(self):
        PlotWidget.__init__(self)

        self.getPlotItem().setContentsMargins(5, 0, 20, 5)
        self.setBackground('k')
        self.setTitle("Profiles")
        self.setLabel('left', 'Intensity')
        self.setLabel('bottom', 'Distance (mm)')
