
import numpy as np
from vtkmodules.vtkIOImage import vtkImageImport

from opentps.gui.viewer.dataForViewer.genericImageForViewer import GenericImageForViewer


class Image2DForViewer(GenericImageForViewer):

    def __init__(self, image):
        super().__init__(image)

        if hasattr(self, '_dataImporter'):
            return

        # print('in image2DForViewer init', type(image))
        # print('in image2DForViewer init', type(self.data))


        self._dataImporter = vtkImageImport()
        self._selectedPosition = self.data.origin# + self.data.gridSizeInWorldUnit/2.
        self._range = (np.min(self.data.imageArray), np.max(self.data.imageArray))

        self.data.dataChangedSignal.connect(self._updateVTKOutputPort)
        self._updateVTKOutputPort()

    def _updateVTKOutputPort(self):
        print('in image2DForViewer _updateVTKOutputPort')
        print(self.gridSize)
        print(self.spacing)
        print(self.origin)

        shape = self.gridSize  ## dataMultiton magic makes all this available here
        imageOrigin = self.origin
        imageSpacing = self.spacing
        # imageData = np.swapaxes(self.imageArray, 0, 2)
        imageData = self.imageArray
        # imageData[100:140, 200:500] = 300
        imageData -= np.min(imageData)

        # imageData = np.tile(imageData, (3, 1, 1))
        # print(imageData.shape)
        # shape = imageData.shape
        # plt.figure()
        # plt.imshow(imageData)
        # plt.show()
        # shape = imageData.shape
        # print(shape)

        num_array = np.array(np.ravel(imageData), dtype=np.float32)

        self._dataImporter.SetNumberOfScalarComponents(1)
        self._dataImporter.SetDataExtent(0, shape[0] - 1, 0, shape[1] - 1, 0, 0)
        self._dataImporter.SetWholeExtent(0, shape[0] - 1, 0, shape[1] - 1, 0, 0)
        self._dataImporter.SetDataSpacing(imageSpacing[0], imageSpacing[1], 1)
        self._dataImporter.SetDataOrigin(imageOrigin[0], imageOrigin[1], imageOrigin[2])
        self._dataImporter.SetDataScalarTypeToFloat()

        data_string = num_array.tobytes()
        self._dataImporter.CopyImportVoidPointer(data_string, len(data_string))

        self._vtkOutputPort = self._dataImporter.GetOutputPort()

        import vtk

        mapper = vtk.vtkImageMapper()
        print(type(self._vtkOutputPort))
        mapper.SetInputConnection(self._vtkOutputPort)
        # mapper.SetInputData(self._vtkOutputPort)
        actor = vtk.vtkActor2D()
        actor.SetMapper(mapper)

        ren = vtk.vtkRenderer()
        ren.AddActor(actor)
        ren.SetBackground(0.1, 0.2, 0.4)

        renWin = vtk.vtkRenderWindow()
        renWin.AddRenderer(ren)
        renWin.SetSize(400, 400)

        iren = vtk.vtkRenderWindowInteractor()
        iren.SetRenderWindow(renWin)

        renWin.Render()
        iren.Start()

    @property
    def vtkOutputPort(self):
        return self._vtkOutputPort
