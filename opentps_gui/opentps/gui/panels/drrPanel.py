from PyQt5.QtGui import QImage, QPixmap, QPainter, QPalette, QBrush, QPolygon
from PyQt5.QtCore import QPoint
import numpy as np
import math


from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QDir#, pyqtSignal
from opentps.core import createDRRDynamic2DSequences



class DRRPanel(QWidget):

    # fluoroSeqCreated = pyqtSignal()

    def __init__(self, viewController):
        QWidget.__init__(self)

        self._viewController = viewController
        self._viewController.patientAddedSignal.connect(self.refreshDataList)

        self.patients = self._viewController.patientList
        # self.toolbox_width = toolbox_width
        self.data_path = QDir.currentPath()
        self.CT_disp_ID = ""

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.imageSelectionBox = QComboBox()
        # self.refreshDataList(self._viewController.currentPatient)

        self.layout.addWidget(self.imageSelectionBox) ## --> this must changed to a data selection box (self.imageSelectionBox)


        self.fluoSimButton = QPushButton('Fluoroscopy simulation')
        self.layout.addWidget(self.fluoSimButton)
        self.fluoSimButton.clicked.connect(self.selectProjectionAngles)

    def refreshDataList(self, patient):

        print('in DRRPanel refresh data list ')
        for data in patient.getPatientDataOfType('CTImage'):
            name = data.name
            self.imageSelectionBox.addItem(name, data)
        for data in patient.getPatientDataOfType('Dynamic3DSequence'):
            name = data.name
            self.imageSelectionBox.addItem(name, data)

    """
    class PatientComboBox(QComboBox):
    def __init__(self, viewController):
        QComboBox.__init__(self)

        self._viewController = viewController

        self._viewController.patientAddedSignal.connect(self._addPatient)
        self._viewController.patientRemovedSignal.connect(self._removePatient)

        self.currentIndexChanged.connect(self._setCurrentPatient)

    def _addPatient(self, patient):
        name = patient.name
        if name is None:
            name = 'None'

        self.addItem(name, patient)
        if self.count() == 1:
            self._viewController.currentPatient = patient

    def _removePatient(self, patient):
        self.removeItem(self.findData(patient))

    def _setCurrentPatient(self, index):
        self._viewController.currentPatient = self.currentData()
    """

    def Data_path_changed(self, data_path):
        self.data_path = data_path

    def selectProjectionAngles(self):

        fluoroAngleDialog = ChoseAngles_dialog(self._viewController.currentPatient.dynamic3DSequences[0].dyn3DImageList[0])

        if (fluoroAngleDialog.exec()):

            anglesAndAxisList = fluoroAngleDialog.anglesList
            print('in selectProjectionAngles', anglesAndAxisList)
            print('this should be change to use the currently selected patient and dyn seq if several')

            # fluoroSeq = self.createDRRs(angles, self._viewController.currentPatient.dynamic3DSequences[0].dyn3DImageList, self._viewController.currentPatient)

            print('in drrPanel selectProjectionAngles !!! source image is hard coded for now')
            sourceImageOrSeq = self._viewController.currentPatient.dynamic3DSequences[0]
            dyn2DDRRSeqList = createDRRDynamic2DSequences(sourceImageOrSeq, anglesAndAxisList)

            # plt.figure()
            # plt.imshow(dyn2DDRRSeqList[0].dyn2DImageList[0].imageArray)
            # plt.show()

            if sourceImageOrSeq.patient != None:
                for dyn2DSeq in dyn2DDRRSeqList:
                    sourceImageOrSeq.patient.appendPatientData(dyn2DSeq)

            # self.fluoroSeqCreated.emit()
            #self.data_path = QFileDialog.getExistingDirectory(self, "Select 4D data folder", self.data_path)
            #self.Patients.importDyn4DSeq(self.data_path)

            # display Dynamic series
#             for series in self.Patients.list[0].Dyn2DSeqList:
#                 if (series.isLoaded == 1):
#                     serieRoot = StandardItem(txt=series.SequenceName)
#                     for image in series.dyn2DImageList:
#                         imageName = StandardItem(txt=image.ImgName)
#                         serieRoot.appendRow(imageName)
#                     self.rootNode.appendRow(serieRoot)
#                     self.treeView.setModel(self.treeModel)
#                     self.treeView.expandAll()
#                     self.treeView.clicked.connect(self.getTreeViewValue)
#
    # def createDRRs(self, angleList, Dyn4DSeq, patient, orientation='Axial'):
    #
    #     try:
    #         import tomopy
    #
    #         for anglesAndOri in angleList:
    #
    #             angle = anglesAndOri[0]
    #             orientation = anglesAndOri[1]
    #
    #             fluoroSeq = Dynamic2DSequence()
    #             fluoroSeq.type = 'Fluoroscopy simulation'
    #             fluoroSeq.projectionAngle = angle
    #             fluoroSeq.SequenceName = 'FluoSim_' + anglesAndOri[1] + '_' + str(
    #                 int(np.round(angle * 360 / (2 * math.pi))))
    #             for imageIndex, image in enumerate(Dyn4DSeq.dyn3DImageList):
    #
    #                 # to rotate around Z axis
    #                 if orientation == 'Axial':
    #                     imageToUse = image.Image.transpose(2, 1, 0)
    #                 if orientation == 'Coronal':
    #                     imageToUse = image.Image.transpose(1, 2, 0)
    #                 if orientation == 'Sagittal':
    #                     imageToUse = image.Image.transpose(0, 2, 1)
    #
    #                 print('! ! ! in fluoroscopy_sim --> les orientation et transpose ici sont à vérifier! ! !')
    #                 fluoSimImage = tomopy.project(imageToUse, angle)[0]
    #
    #                 # plt.figure()
    #                 # plt.imshow(fluoSimImage)
    #                 # plt.show()
    #
    #                 image_2D = image2D()
    #                 image_2D.Image = fluoSimImage
    #                 image_2D.ImgName = str(imageIndex + 1)
    #                 image_2D.PixelSpacing = [1, 1]
    #                 fluoroSeq.dyn2DImageList.append(image_2D)
    #                 fluoroSeq.isLoaded = True
    #
    #             patient.Dyn2DSeqList.append(fluoroSeq)
    #
    #     except:
    #         print("No module tomopy available")
# class StandardItem(QStandardItem):
#   def __init__(self, txt="", fontSize = 12, setBold=False, color=QColor(0,0,0)):
#     super().__init__()
#     self.setEditable(False)
#     self.setForeground(color)
#     self.setText(txt)



class ChoseAngles_dialog(QDialog):

    def __init__(self, Image3D):

        # initialize the window
        QDialog.__init__(self)

        self.main_layout = QGridLayout()
        self.setLayout(self.main_layout)

        self.infoLabel = QLabel()
        self.infoLabel.viewer_palette = QPalette()
        self.infoLabel.viewer_palette.setColor(QPalette.Window, Qt.black)
        self.infoLabel.setAlignment(Qt.AlignTop)
        self.infoLabel.setStyleSheet('color: black')
        self.infoLabelText = ''
        self.main_layout.addWidget(self.infoLabel, 0, 0)

        self.imageLabel = QLabel()
        self.imageLabel.setMaximumSize(512, 512)
        self.imageLabel.setAlignment(Qt.AlignTop)
        self.main_layout.addWidget(self.imageLabel, 1, 0)

        self.orientation = "Z"
        self.image3D = self.prepare_image_for_viewer(Image3D.imageArray)
        self.imageShape = self.image3D.shape
        self.resolution = Image3D.spacing
        self.imageCenter = [self.imageLabel.pos().x() + int(self.imageLabel.width() / 2), self.imageLabel.pos().y() + int(self.imageLabel.height() / 2)]
        print('in ChoseAngles_dialog constructor', self.imageLabel.pos().x())
        print(self.imageCenter)
        self.distanceFromSourceToCenter = min(self.imageCenter[0], self.imageCenter[1]) - 10
        self.pannelWidth = min(self.imageLabel.width(), self.imageLabel.height())

        self.anglesList = []

        self.currentMousePos = QPoint(0, 0)
        self.angleBetweenMouseAndCenter = 0
        self.xRaySourcePoint = QPoint(0, 0)
        self.pannelPoint1 = QPoint(0, 0)
        self.pannelPoint2 = QPoint(0, 0)
        self.getPolygonPoints(self.angleBetweenMouseAndCenter)
        self.colorList = [Qt.cyan, Qt.red, Qt.blue]
        self.colorList *= 5

        # buttons
        self.ButtonLayout = QGridLayout()
        self.AddAngleButton = QPushButton('Add angle')
        self.AddAngleButton.clicked.connect(self.addAngle)
        self.ButtonLayout.addWidget(self.AddAngleButton, 1, 0)
        self.ValidateButton = QPushButton('OK')
        self.ValidateButton.clicked.connect(self.accept)
        self.ButtonLayout.addWidget(self.ValidateButton, 1, 1)
        self.CancelButton = QPushButton('Cancel')
        self.ButtonLayout.addWidget(self.CancelButton, 1, 2)
        self.CancelButton.clicked.connect(self.reject)
        self.XYButton = QPushButton('Z')
        self.XYButton.clicked.connect(self.changeImageView)
        self.ButtonLayout.addWidget(self.XYButton, 0, 0)
        self.YZButton = QPushButton('Y')
        self.YZButton.clicked.connect(self.changeImageView)
        self.ButtonLayout.addWidget(self.YZButton, 0, 1)
        self.XZButton = QPushButton('X')
        self.XZButton.clicked.connect(self.changeImageView)
        self.ButtonLayout.addWidget(self.XZButton, 0, 2)

        self.main_layout.addLayout(self.ButtonLayout, 2, 0)

        self.setWindowTitle('Select angles to use for fluoroscopy projections')

        self.selectSlice()
        self.resize(512, 512)
        self.update_viewer()

##-----------------------------------------------------------------------------------------------------------
    def selectSlice(self):

        if self.orientation == 'Z':
            self.current_sliceIndex = round(self.imageShape[2] / 2)
            self.sliceToShow = self.image3D[:, :, self.current_sliceIndex].transpose(1,0)
        elif self.orientation == 'X':
            self.current_sliceIndex = round(self.imageShape[0] / 2)
            self.sliceToShow = np.flip(self.image3D[self.current_sliceIndex, :, :].transpose(1,0), 0)
        elif self.orientation == 'Y':
            self.current_sliceIndex = round(self.imageShape[1] / 2)
            self.sliceToShow = np.flip(self.image3D[:, self.current_sliceIndex, :].transpose(1,0), 0)

        self.sliceToShow = np.require(self.sliceToShow, np.uint8, 'C')


##-----------------------------------------------------------------------------------------------------------
    def getPolygonPoints(self, angle):

        print('in get polygon points')
        print(self.imageCenter)
        print(self.imageCenter[0] - 2 * (self.distanceFromSourceToCenter * math.sin(angle)))
        print(self.imageCenter[1] - 2 * (self.distanceFromSourceToCenter * math.cos(angle)))

        self.xRaySourcePoint = QPoint(int(self.imageCenter[0] - 2 * (self.distanceFromSourceToCenter * math.sin(angle))),
                                      int(self.imageCenter[1] - 2 * (self.distanceFromSourceToCenter * math.cos(angle))))
        self.pannelPoint1 = QPoint(int(self.imageCenter[0] + (self.distanceFromSourceToCenter * math.sin(angle)) + math.cos(angle)*self.pannelWidth/2),
                                    int(self.imageCenter[1] + (self.distanceFromSourceToCenter * math.cos(angle)) - math.sin(angle)*self.pannelWidth/2))
        self.pannelPoint2 = QPoint(int(self.imageCenter[0] + (self.distanceFromSourceToCenter * math.sin(angle)) - math.cos(angle)*self.pannelWidth/2),
                                      int(self.imageCenter[1] + (self.distanceFromSourceToCenter * math.cos(angle)) + math.sin(angle)*self.pannelWidth/2))

##-----------------------------------------------------------------------------------------------------------
    def update_viewer(self):

        # calculate scaling factor
        if self.orientation == 'Z':
            Yscaling = self.resolution[1] / self.resolution[0]
        elif self.orientation == 'X':
            Yscaling = self.resolution[2] / self.resolution[1]
        elif self.orientation == 'Y':
            Yscaling = self.resolution[2] / self.resolution[0]

        self.imageCenter = [self.imageLabel.pos()._x() + int(self.imageLabel.width() / 2),
                            self.imageLabel.pos()._y() + int(self.imageLabel.height() / 2)]
        self.distanceFromSourceToCenter = min(self.imageCenter[0], self.imageCenter[1]) - 10
        self.pannelWidth = min(self.imageLabel.width(), self.imageLabel.height())

        imageQT = QImage(self.sliceToShow, self.sliceToShow.shape[1], self.sliceToShow.shape[0], self.sliceToShow.shape[1], QImage.Format_Indexed8)
        imageQT = imageQT.convertToFormat(QImage.Format_ARGB32)
        MergedImage = QImage(self.sliceToShow.shape[1], round(self.sliceToShow.shape[0] * Yscaling), QImage.Format_ARGB32)
        MergedImage.fill(Qt.black)
        painter = QPainter()
        painter.begin(MergedImage)
        painter.scale(1.0, Yscaling)
        painter.drawImage(0, 0, imageQT)

        for angleIndex, angle in enumerate(self.anglesList):
            self.draw_polygon(angle[0], angleIndex, painter)
        self.draw_polygon(self.angleBetweenMouseAndCenter, -1, painter)

        painter.end()

        self.imageLabel.setPixmap(QPixmap.fromImage(MergedImage).scaledToWidth(self.width() - 10, mode=Qt.SmoothTransformation))

##-----------------------------------------------------------------------------------------------------------
    def addAngle(self):
        self.anglesList.append([self.angleBetweenMouseAndCenter, self.orientation])
        self.infoLabelText += 'Angle ' + str(len(self.anglesList)) + ': ' + str(int(np.round(self.anglesList[-1][0]*(360/(2*math.pi))))) + '°' + '\n'
        self.infoLabel.setText(self.infoLabelText)

##-----------------------------------------------------------------------------------------------------------
    def draw_polygon(self, angle, angleIndex, painter):

        self.getPolygonPoints(angle)
        if angleIndex == -1:
            painter.setBrush(QBrush(Qt.yellow, Qt.Dense6Pattern))
        else:
            painter.setBrush(QBrush(self.colorList[angleIndex], Qt.Dense6Pattern))

        polygon = QPolygon([self.pannelPoint1,
                            self.pannelPoint2,
                            self.xRaySourcePoint])

        painter.drawPolygon(polygon)

    # def onClicked(self, item):
    #     print('test onClicked')

    # def onDoubleClick(self, item):
    #     print('test onDoubleClick')

##-----------------------------------------------------------------------------------------------------------
    def mouseMoveEvent(self, QMouseEvent):
        #print('Mouse coords: ( %d : %d )' % (QMouseEvent.x(), QMouseEvent.y()))
        self.currentMousePos.setX(QMouseEvent._x())
        self.currentMousePos.setY(QMouseEvent._y())
        self.getAngleFromMousePosition()

        self.infoLabel.setText(self.infoLabelText + "Current angle : " + str(int(np.round(self.angleBetweenMouseAndCenter*(360/6.28)))) + '°')
        self.update_viewer()

##-----------------------------------------------------------------------------------------------------------
    def getAngleFromMousePosition(self):

        if self.imageCenter[1] == self.currentMousePos.y() and self.imageCenter[0] > self.currentMousePos.x():
            self.angleBetweenMouseAndCenter = math.pi/2
        elif self.imageCenter[1] == self.currentMousePos.y() and self.imageCenter[0] < self.currentMousePos.x():
            self.angleBetweenMouseAndCenter = 3 * math.pi / 2
        elif self.imageCenter[1] < self.currentMousePos.y() and self.imageCenter[0] == self.currentMousePos.x():
            self.angleBetweenMouseAndCenter = math.pi
        elif self.imageCenter[1] > self.currentMousePos.y() and self.imageCenter[0] == self.currentMousePos.x():
            self.angleBetweenMouseAndCenter = 0
        elif self.imageCenter[0] > self.currentMousePos.x() and self.imageCenter[1] > self.currentMousePos.y():
            self.angleBetweenMouseAndCenter = math.atan(abs(self.imageCenter[0]-self.currentMousePos.x())/abs(self.imageCenter[1]-self.currentMousePos.y()))
        elif self.imageCenter[0] > self.currentMousePos.x() and self.imageCenter[1] < self.currentMousePos.y():
            self.angleBetweenMouseAndCenter = math.pi - math.atan(abs(self.imageCenter[0]-self.currentMousePos.x())/abs(self.imageCenter[1]-self.currentMousePos.y()))
        elif self.imageCenter[0] < self.currentMousePos.x() and self.imageCenter[1] < self.currentMousePos.y():
            self.angleBetweenMouseAndCenter = math.pi + math.atan(abs(self.imageCenter[0]-self.currentMousePos.x())/abs(self.imageCenter[1]-self.currentMousePos.y()))
        elif self.imageCenter[0] < self.currentMousePos.x() and self.imageCenter[1] > self.currentMousePos.y():
            self.angleBetweenMouseAndCenter = (2 * math.pi) - math.atan(abs(self.imageCenter[0]-self.currentMousePos.x())/abs(self.imageCenter[1]-self.currentMousePos.y()))

    ##-----------------------------------------------------------------------------------------------------------
    def changeImageView(self):
        self.orientation = self.sender().text()
        self.selectSlice()
        self.update_viewer()

    ##-----------------------------------------------------------------------------------------------------------
    def prepare_image_for_viewer(self, image):
        img_min = image.min()
        # img_max = self.Image.max()
        img_max = np.percentile(image, 99.995)
        img = 255 * (image.astype(np.float32) - img_min) / (
                    img_max - img_min + 1e-5)  # normalize data betwee, 0 and 255
        img[img > 255] = 255
        return img