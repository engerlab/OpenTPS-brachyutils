from pyqtgraph import *

class Viewer_DVH(PlotWidget):

  def __init__(self):
    PlotWidget.__init__(self)

    self.DVH_list = []
    self.DVHband_list = []

    self.getPlotItem().setContentsMargins(5, 0, 20, 5)
    self.setBackground('k')
    self.setTitle("DVH")
    self.setLabel('left', 'Volume (%)')
    self.setLabel('bottom', 'Dose (Gy)')
    #self.addLegend()
    self.showGrid(x=True, y=True)
    self.setXRange(0, 100, padding=0)
    self.setYRange(0, 100, padding=0)
    self.viewer_DVH_proxy = SignalProxy(self.scene().sigMouseMoved, rateLimit=120, slot=self.DVH_mouseMoved)
    self.viewer_DVH_label = TextItem("", color=(255,255,255), fill=(0,0,0,250), anchor=(0,1))
    self.viewer_DVH_label.hide()
    self.addItem(self.viewer_DVH_label)



  def set_DVH_list(self, DVH_list):
    self.DVH_list = DVH_list
    self.DVHband_list = []
    self.update_DVH()



  def set_DVHband_list(self, DVHband_list):
    self.DVH_list = []
    self.DVHband_list = DVHband_list
    self.update_DVH()



  def clear_DVH(self):
    self.DVH_list = []
    self.update_DVH()



  def update_DVH(self):
    self.clear()

    # display DVH-bands
    for dvh_band in self.DVHband_list:
      color = [dvh_band.ROIDisplayColor[2], dvh_band.ROIDisplayColor[1], dvh_band.ROIDisplayColor[0]]
      phigh = PlotCurveItem(dvh_band.dose, dvh_band.volume_high, pen=color, name=dvh_band.ROIName)           
      plow = PlotCurveItem(dvh_band.dose, dvh_band.volume_low, pen=color, name=dvh_band.ROIName)          
      pnominal = PlotCurveItem(dvh_band.nominalDVH.dose, dvh_band.nominalDVH.volume, pen=color, name=dvh_band.ROIName)  
      pnominal.DVH = dvh_band.nominalDVH
      pfill = FillBetweenItem(phigh, plow, brush=tuple(color + [100]))
      pfill.DVHband = dvh_band
      #self.addItem(phigh)
      #self.addItem(plow)
      self.addItem(pfill)
      self.addItem(pnominal)

    # display DVHs
    for dvh in self.DVH_list:
      pen = mkPen(color=(dvh.ROIDisplayColor[2], dvh.ROIDisplayColor[1], dvh.ROIDisplayColor[0]), width=2)
      curve = PlotCurveItem(dvh.dose, dvh.volume, pen=pen, name=dvh.ROIName)   
      curve.DVH = dvh
      self.addItem(curve)

    self.addItem(self.viewer_DVH_label)



  def DVH_mouseMoved(self, evt):
    self.viewer_DVH_label.hide()

    if self.sceneBoundingRect().contains(evt[0]):
      mousePoint = self.getViewBox().mapSceneToView(evt[0])
      for item in self.scene().items():
        if hasattr(item, "DVH"):
          data = item.getData()
          y, y2 = np.interp([mousePoint.x(), mousePoint.x()*1.01], data[0], data[1])
          #if item.mouseShape().contains(mousePoint):
          # check if mouse.y is close to f(mouse.x)
          if abs(y-mousePoint.y()) < 2.0+abs(y2-y): # abs(y2-y) is to increase the distance in high gradient
            self.viewer_DVH_label.setHtml("<b><font color='#" + "{:02x}{:02x}{:02x}".format(item.DVH.ROIDisplayColor[2], item.DVH.ROIDisplayColor[1], item.DVH.ROIDisplayColor[0]) + "'>" + \
              item.name() + ":</font></b>" + \
              "<br>D95 = {:.1f} Gy".format(item.DVH.D95) + \
              "<br>D5 = {:.1f} Gy".format(item.DVH.D5) + \
              "<br>Dmean = {:.1f} Gy".format(item.DVH.Dmean) )
            self.viewer_DVH_label.setPos(mousePoint)
            if(mousePoint.x() < 50 and mousePoint.y() < 50): self.viewer_DVH_label.setAnchor((0,1))
            elif(mousePoint.x() < 50 and mousePoint.y() >= 50): self.viewer_DVH_label.setAnchor((0,0))
            elif(mousePoint.x() >= 50 and mousePoint.y() < 50): self.viewer_DVH_label.setAnchor((1,1))
            elif(mousePoint.x() >= 50 and mousePoint.y() >= 50): self.viewer_DVH_label.setAnchor((1,0))
            self.viewer_DVH_label.show()
            break

        elif hasattr(item, "DVHband"):
          #if item.isUnderMouse():
          data = item.curves[0].getData()
          y0 = np.interp(mousePoint.x(), data[0], data[1])
          data = item.curves[1].getData()
          y1 = np.interp(mousePoint.x(), data[0], data[1])
          # check if mouse is inside the band
          if(y1 < mousePoint.y() < y0):
            self.viewer_DVH_label.setHtml("<b><font color='#" + "{:02x}{:02x}{:02x}".format(item.DVHband.ROIDisplayColor[2], item.DVHband.ROIDisplayColor[1], item.DVHband.ROIDisplayColor[0]) + "'>" + \
              item.DVHband.ROIName + ":</font></b>" + \
              "<br>D95 = {:.1f} - {:.1f} Gy".format(item.DVHband.D95[0], item.DVHband.D95[1]) + \
              "<br>D5 = {:.1f} - {:.1f} Gy".format(item.DVHband.D5[0], item.DVHband.D5[1]) + \
              "<br>Dmean = {:.1f} - {:.1f} Gy".format(item.DVHband.Dmean[0], item.DVHband.Dmean[1]) )
            self.viewer_DVH_label.setPos(mousePoint)
            if(mousePoint.x() < 50 and mousePoint.y() < 50): self.viewer_DVH_label.setAnchor((0,1))
            elif(mousePoint.x() < 50 and mousePoint.y() >= 50): self.viewer_DVH_label.setAnchor((0,0))
            elif(mousePoint.x() >= 50 and mousePoint.y() < 50): self.viewer_DVH_label.setAnchor((1,1))
            elif(mousePoint.x() >= 50 and mousePoint.y() >= 50): self.viewer_DVH_label.setAnchor((1,0))
            self.viewer_DVH_label.show()
            break


