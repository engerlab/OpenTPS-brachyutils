
import vtkmodules.vtkRenderingOpenGL2 #This is necessary to avoid a seg fault
import vtkmodules.vtkRenderingFreeType  #This is necessary to avoid a seg fault
from vtkmodules.vtkRenderingCore import vtkTextActor


class TextLayer:
    def __init__(self, renderer, renderWindow):
        self._primaryText = ['', '', '']
        self._secondaryText = ['', '', '']
        self._renderer = renderer
        self._renderWindow = renderWindow
        self._primaryTextActor = vtkTextActor()
        self._secondaryTextActor = vtkTextActor()
        self._visible = True

        self._primaryTextActor.GetTextProperty().SetFontSize(14)
        self._primaryTextActor.GetTextProperty().SetColor(1, 0.5, 0)
        self._primaryTextActor.GetPositionCoordinate().SetCoordinateSystemToNormalizedViewport()
        self._primaryTextActor.SetPosition(0.02, 0.85)
        self._secondaryTextActor.GetTextProperty().SetJustificationToLeft()
        self._secondaryTextActor.GetTextProperty().SetVerticalJustificationToTop()

        self._secondaryTextActor.GetTextProperty().SetFontSize(14)
        self._secondaryTextActor.GetTextProperty().SetColor(1, 0.5, 0)
        self._secondaryTextActor.GetPositionCoordinate().SetCoordinateSystemToNormalizedViewport()
        self._secondaryTextActor.SetPosition(0.02, 0.02)
        self._secondaryTextActor.GetTextProperty().SetJustificationToLeft()
        self._secondaryTextActor.GetTextProperty().SetVerticalJustificationToBottom()

        self._renderer.AddActor(self._primaryTextActor)
        self._renderer.AddActor(self._secondaryTextActor)

    def close(self):
        pass

    @property
    def primaryText(self):
        return self._primaryText

    def setPrimaryTextLine(self, line, text):
        self._primaryText[line] = text
        self._primaryTextActor.SetInput(self._primaryText[0] + '\n' + self._primaryText[1] + '\n' + self._primaryText[2])
        self._renderWindow.Render()

    @property
    def secondaryText(self):
        return self._secondaryText

    def setSecondaryTextLine(self, line, text):
        self._secondaryText[line] = text
        self._secondaryTextActor.SetInput(
            self._secondaryText[0] + '\n' + self._secondaryText[1] + '\n' + self._secondaryText[2])
        self._renderWindow.Render()

    @property
    def visible(self):
        return self._visible

    @visible.setter
    def visible(self, visible):
        self._primaryTextActor.SetVisibility(visible)
        self._secondaryTextActor.SetVisibility(visible)
        self._visible = visible
