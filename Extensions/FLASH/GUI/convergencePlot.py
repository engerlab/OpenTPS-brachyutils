import numpy as np
from pyqtgraph import PlotWidget, PlotCurveItem


class ConvergencePlot(PlotWidget):
    def __init__(self):
        PlotWidget.__init__(self)

        self.addLegend()
        self.getPlotItem().setContentsMargins(5, 0, 20, 5)
        self.setBackground('k')
        self.setTitle("Convergence")
        self.setLabel('left', 'Function value')
        self.setLabel('bottom', 'Iteration')

        self.pl = None

        self.x = []
        self.y = []

    def appendFVal(self, xy):
        if not (self.pl is None):
            self.removeItem(self.pl)

        self.x.append(xy[0])
        self.y.append(xy[1])

        self.pl = PlotCurveItem(np.array(self.x), np.array(self.y))
        self.addItem(self.pl)
