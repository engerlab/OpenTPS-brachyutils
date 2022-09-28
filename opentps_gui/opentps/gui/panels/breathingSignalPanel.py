from PyQt5.QtWidgets import QWidget,QVBoxLayout,QPushButton, QGridLayout,QLabel,QDoubleSpinBox, QSpinBox, QComboBox
import pyqtgraph as pg

from opentps.core.processing.deformableDataAugmentationToolBox.BreathingSignalGeneration import signalGeneration
from PyQt5.QtCore import Qt
class BreathingSignalPanel(QWidget):
    
    def __init__(self, viewController):
        QWidget.__init__(self)
        
        self._viewController = viewController
        
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        
        self.Breath_param = {"Period": "", "Amplitude": "", "Duration": "", 
                             "Step": "", "Variance": "", "Mean": "", "ROI": "",
                             "nbrImage": "", "Way": ""}
        self.default_param = {"Period": 3.5, "Amplitude": 10.0, "Duration": 120, 
                             "Step": 0.2, "Variance": 0.0, "Mean": 0, 
                             "nbrImage": 3}

        self.layout.addWidget(QLabel('<b>Period:</b>'))
        self.TimePeriod = QDoubleSpinBox()
        self.TimePeriod.setGroupSeparatorShown(True)
        self.TimePeriod.setRange(0.0, 10.0)
        self.TimePeriod.setSingleStep(0.1)
        self.TimePeriod.setValue(self.default_param["Period"])
        self.TimePeriod.setSuffix(" seconds")
        self.TimePeriod.valueChanged.connect(self.Update_Breath_param)
        self.layout.addWidget(self.TimePeriod)
        self.layout.addSpacing(15)
        
        self.layout.addWidget(QLabel('<b>Amplitude:</b>'))
        self.Amplitude = QDoubleSpinBox()
        self.Amplitude.setGroupSeparatorShown(True)
        self.Amplitude.setRange(0.0, 30.0)
        self.Amplitude.setSingleStep(0.5)
        self.Amplitude.setValue(self.default_param["Amplitude"])
        self.Amplitude.setSuffix(" millimeter")
        self.Amplitude.valueChanged.connect(self.Update_Breath_param)
        self.layout.addWidget(self.Amplitude)
        self.layout.addSpacing(15)
        
        self.layout.addWidget(QLabel('<b>Duration:</b>'))
        self.Duration = QSpinBox()
        self.Duration.setGroupSeparatorShown(True)
        self.Duration.setRange(0, 600)
        self.Duration.setSingleStep(30)
        self.Duration.setValue(self.default_param["Duration"])
        self.Duration.setSuffix(" seconds")
        self.Duration.valueChanged.connect(self.Update_Breath_param)
        self.layout.addWidget(self.Duration)
        self.layout.addSpacing(15)
        
        self.layout.addWidget(QLabel('<b>Step size:</b>'))
        self.Step = QDoubleSpinBox()
        self.Step.setGroupSeparatorShown(True)
        self.Step.setRange(0.0, 1.0)
        self.Step.setSingleStep(0.05)
        self.Step.setValue(self.default_param["Step"])
        self.Step.valueChanged.connect(self.Update_Breath_param)
        self.layout.addWidget(self.Step)
        self.layout.addSpacing(15)
        
        self.layout.addWidget(QLabel('<b>Noise:</b>'))
        self.layout.addWidget(QLabel('Variance:'))
        self.Variance = QDoubleSpinBox()
        self.Variance.setGroupSeparatorShown(True)
        self.Variance.setRange(0.0, 10.0)
        self.Variance.setSingleStep(0.1)
        self.Variance.setValue(self.default_param["Variance"])
        self.Variance.valueChanged.connect(self.Update_Breath_param)
        self.layout.addWidget(self.Variance)
        self.layout.addWidget(QLabel('Mean:'))
        self.Mean = QSpinBox()
        self.Mean.setGroupSeparatorShown(True)
        self.Mean.setRange(0, 100)
        self.Mean.setSingleStep(1)
        self.Mean.setValue(self.default_param["Mean"])
        self.Mean.valueChanged.connect(self.Update_Breath_param)
        self.layout.addWidget(self.Mean)
        self.layout.addSpacing(15)
        
        self.layout.addWidget(QLabel('<b>ROI:</b>'))
        self.ROI = QComboBox()
        #self.ROI.setMaximumWidth(self.toolbox_width-18)
        self.ROI.currentIndexChanged.connect(self.Update_Breath_param)
        #self.ROI.addItems(["None"])
        self.layout.addWidget(self.ROI)
        self.layout.addSpacing(15)
        self.ROI_loaded = 0
        
        self.layout.addWidget(QLabel('<b>Number of images:</b>'))
        self.nbrImage = QSpinBox()
        self.nbrImage.setGroupSeparatorShown(True)
        self.nbrImage.setRange(0, 10)
        self.nbrImage.setSingleStep(1)
        self.nbrImage.setValue(self.default_param["nbrImage"])
        self.nbrImage.valueChanged.connect(self.Update_Breath_param)
        self.layout.addWidget(self.nbrImage)
        self.layout.addSpacing(15)
        
        self.layout.addWidget(QLabel('<b>Way:</b>'))
        self.way = QComboBox()
        #self.way.setMaximumWidth(self.toolbox_width-18)
        self.way.addItems(["Normal", "Random"])
        self.way.currentIndexChanged.connect(self.Update_Breath_param)
        self.layout.addWidget(self.way)
        self.layout.addSpacing(15)
        
        
        #self.Roi_name()#None if we do not load patient data
        #self.Update_Breath_param#in the case where we do not change the default values
        
        self.newSignalButton = QPushButton('Signal generation')
        self.layout.addWidget(self.newSignalButton)
        self.newSignalButton.clicked.connect(self.signalGeneration)
        
        self.layout.addStretch()
        
        self.xOnClick = 0
        self.yOnClick = 0

        
    def signalGeneration(self):       
        A = self.Amplitude.value() #amplitude (mm)
        dA = 5 #variation d amplitude possible (mm)
        T = self.TimePeriod.value() #periode respiratoire (s)
        df = 0.5 #variation de frequence possible (Hz)
        dS = 5 #shift du signal (mm)
        mean = self.Mean.value()
        sigma = self.Variance.value()
        step = self.Step.value() #periode d echantillonnage
        Tend = self.Duration.value() #temps de simulation
        L = 2/30 #moyenne des evenements aleatoires
        
        self.t,self.y = signalGeneration(A, dA, T, df, dS, mean, sigma, step, Tend, L)
        
        self.widget = QWidget()
        self.layout = QGridLayout()
        self.widget.setLayout(self.layout)
        self.coordSown = QLabel()
        self.graphWidget = pg.plot()#pg.GraphicsLayoutWidget()
        #self.graphWidget.showGrid(x = True, y = True)
        
        self.widget.setWindowTitle('Display the breathing signal')
        self.graphWidget.setBackground('w')
        self.widget.resize(1000, 1000) 
        cursor = Qt.CrossCursor
        self.graphWidget.setCursor(cursor)
        """
        self.plot_item = self.graphWidget.addPlot(title = "Breathing signal")
        self.plot_item.setLabel("left", 'Amplitude', units = 'mm')
        self.plot_item.setLabel("bottom", 'Time', units = 's')
        curve = self.plot_item.plot()
        curve.setData(self.t,self.y)

        """
        self.graphWidget.setLabel("left", 'Amplitude', units = 'mm')
        self.graphWidget.setLabel("bottom", 'Time', units = 's')
        self.graphWidget.setTitle("Breathing signal")
        self.graphWidget.plot(self.t,self.y)
        
        
        self.coordSown.setText("x={:.1f}".format(self.xOnClick) + ", " + "y={:.1f}".format(self.yOnClick))
        self.layout.addWidget(self.coordSown, 0, 0,1,2)
        self.layout.addWidget(self.graphWidget, 1, 0)
        
        self.graphWidget.scene().sigMouseClicked.connect(self.onClick)
        
        # buttons
        self.ButtonLayout = QGridLayout()
        
        self.ValidateButton = QPushButton('OK')
        self.ValidateButton.clicked.connect(self.acceptFunct)
        self.ButtonLayout.addWidget(self.ValidateButton, 1, 0)
        
        self.RefreshButton = QPushButton('Refresh')
        self.RefreshButton.clicked.connect(self.refreshFunct)
        self.ButtonLayout.addWidget(self.RefreshButton, 1, 1)
        
        self.CancelButton = QPushButton('Cancel')
        self.CancelButton.clicked.connect(self.rejectFunct)
        self.ButtonLayout.addWidget(self.CancelButton, 1, 2)
        
        self.layout.addLayout(self.ButtonLayout, 2, 0)
        self.Roi_name()#None if we do not load patient data
        #self.Update_Breath_param()#in the case where we do not change the default values
        self.widget.show()
        
    def Update_Breath_param(self):
        self.Breath_param["Period"] = self.TimePeriod.value()
        self.Breath_param["Amplitude"] = self.Amplitude.value()
        self.Breath_param["Duration"] = self.Duration.value()
        self.Breath_param["Step"] = self.Step.value()
        self.Breath_param["Variance"] = self.Variance.value()
        self.Breath_param["Mean"] = self.Mean.value()
        self.Breath_param["ROI"] = self.ROI.currentText()
        self.Breath_param["nbrImage"] = self.nbrImage.value()
        self.Breath_param["Way"] = self.way.currentText()
        #self.Compute_Breath(plot = False
        #self.Roi_name()
    def Roi_name(self):
        if self.ROI_loaded == 0:
            rts = self._viewController.currentPatient.rtStructs#.name
            listOfNames = []
            for i in range(len(rts)):
                for j in range(len(rts[i].contours)):
                    listOfNames.append(rts[i].contours[j].name)
                
            self.ROI.addItems(listOfNames)
            self.ROI_loaded = 1
    
    def acceptFunct(self):
        print("Chosen parameters ", self.Breath_param)
        self.widget.close()
    
    def rejectFunct(self):
        print("Reject breathing signal")
        self.widget.close()
        
    def refreshFunct(self):
        print("Refresh signal")
        self.signalGeneration()
        
    def onClick(self, event):
        #print("hello")
        p = self.graphWidget.plotItem.vb.mapSceneToView(event.scenePos())
        #p = self.graphWidget.vb.mapSceneToView(event.scenePos())
        #self.graphWidget.setText("x={:.1f}".format(p.x()))
        #self.label_y.setText("y={:.1f}".format(p.y()))
        self.coordSown.setText("x={:.1f}".format(p.x()) + ", " + "y={:.1f}".format(p.y()))
        #self.graphWidget.plotItem.setText("x={:.1f}".format(p.x()) + ", " + "y={:.1f}".format(p.y()))
        print(f"x: {p.x()}, y: {p.y()}")
        self.xOnClick = p.x()
        self.yOnClick = p.y()
        
        
        
    