from pyqtgraph import PlotWidget


class BlackEmptyPlot(PlotWidget):
    def __init__(self):
        PlotWidget.__init__(self)

        self.getPlotItem().setContentsMargins(0, 0, 0, 0)
        self.setBackground('k')
        self.setTitle("No image")
