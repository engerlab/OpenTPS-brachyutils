from pyqtgraph import PlotWidget


class DVHPlot(PlotWidget):
    def __init__(self):
        PlotWidget.__init__(self)

        self.getPlotItem().setContentsMargins(5, 0, 20, 5)
        self.setBackground('k')
        self.setTitle("DVH")
        self.setLabel('left', 'Volume (%)')
        self.setLabel('bottom', 'Dose (Gy)')
        self.showGrid(x=True, y=True)
        self.setXRange(0, 100, padding=0)
        self.setYRange(0, 100, padding=0)

