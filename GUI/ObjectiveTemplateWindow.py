from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt

from Process.OptimizationObjectives import *

from GUI.AddObjective_dialog import *

class ObjectiveTemplateWindow(QDialog):

  def __init__(self, ContourList, Templates):
    self.Templates = Templates
    self.ContourList = ContourList

    # initialize the window
    QDialog.__init__(self)
    self.setWindowTitle('Optimization objective templates')
    self.resize(800, 400)
    self.main_layout = QHBoxLayout()
    self.setLayout(self.main_layout)

    # List of templates
    self.TemplatesLayout = QVBoxLayout()
    self.main_layout.addLayout(self.TemplatesLayout)
    self.TemplatesLayout.addWidget(QLabel('<b>Templates:</b>'))
    self.TemplateList = QListWidget()
    self.TemplateList.setSpacing(2)
    #self.TemplateList.setAlternatingRowColors(True)
    self.TemplateList.currentRowChanged.connect(self.template_selected) 
    self.TemplatesLayout.addWidget(self.TemplateList)

    for template in Templates.list:
      self.TemplateList.addItem(template.Name)

    # Buttons acting on list of templates
    self.TemplateButtons = QHBoxLayout()
    self.TemplatesLayout.addLayout(self.TemplateButtons)
    self.AddTemplate = QPushButton('Add')
    self.TemplateButtons.addWidget(self.AddTemplate)
    self.AddTemplate.clicked.connect(self.addTemplate) 
    self.DeleteTemplate = QPushButton('Delete')
    self.TemplateButtons.addWidget(self.DeleteTemplate)
    self.DeleteTemplate.clicked.connect(self.deleteTemplate) 
    self.TemplateButtons.addStretch()
    self.SaveTemplates = QPushButton('Save templates')
    self.TemplateButtons.addWidget(self.SaveTemplates)
    self.SaveTemplates.clicked.connect(self.saveTemplates) 
    self.SaveTemplates.setStyleSheet("background-color: red")
    self.SaveTemplates.hide()

    # List of objectives
    self.ObjectiveLayout = QVBoxLayout()
    self.main_layout.addLayout(self.ObjectiveLayout)
    self.ObjectiveLayout.addWidget(QLabel('<b>Objectives:</b>'))
    self.ObjectiveList =  QListWidget()
    self.ObjectiveList.setSpacing(2)
    self.ObjectiveList.setAlternatingRowColors(True)
    self.ObjectiveLayout.addWidget(self.ObjectiveList)

    # Buttons acting on list of objectives
    self.ObjectiveButtons = QHBoxLayout()
    self.ObjectiveLayout.addLayout(self.ObjectiveButtons)
    self.AddObjective = QPushButton('Add')
    self.ObjectiveButtons.addWidget(self.AddObjective)
    self.AddObjective.clicked.connect(self.addObjective) 
    self.DeleteObjective = QPushButton('Delete')
    self.ObjectiveButtons.addWidget(self.DeleteObjective)
    self.DeleteObjective.clicked.connect(self.deleteObjective) 
    self.ObjectiveButtons.addStretch()
    self.LoadObjectives = QPushButton('Load objectives')
    self.ObjectiveButtons.addWidget(self.LoadObjectives)
    self.LoadObjectives.clicked.connect(self.loadObjectives) 

    self.objective_setDisabled(True)



  def loadObjectives(self):
    if(self.SaveTemplates.isVisible()):
      reply = QMessageBox.warning(self, 'Template not saved', 'Some modifications were not saved.', QMessageBox.Ok | QMessageBox.Cancel)
      if reply == QMessageBox.Cancel: return

    self.accept()



  def objective_setDisabled(self, state):
    self.ObjectiveList.setDisabled(state)
    self.AddObjective.setDisabled(state)
    self.DeleteObjective.setDisabled(state)
    self.LoadObjectives.setDisabled(state)



  def deleteTemplate(self):
    template_id = self.TemplateList.currentRow()
    self.TemplateList.takeItem(template_id)
    self.Templates.list.pop(template_id)
    self.SaveTemplates.show()



  def deleteObjective(self):
    template_id = self.TemplateList.currentRow()
    objective_id = self.ObjectiveList.currentRow()
    self.ObjectiveList.takeItem(objective_id)
    self.Templates.list[template_id].Objectives.pop(objective_id)
    self.SaveTemplates.show()

  

  def addTemplate(self):
    resp = QInputDialog.getText(self, 'New template', 'Template name:')

    if resp[1] == True:
      new = ObjectiveTemplate()
      new.Name = resp[0]
      self.Templates.list.append(new)
      self.SaveTemplates.show()

      self.TemplateList.addItem(resp[0])
      self.TemplateList.setCurrentRow(self.TemplateList.count()-1)



  def addObjective(self):
    template_id = self.TemplateList.currentRow()

    dialog = AddObjective_dialog(self.ContourList)

    if(dialog.exec()):
      new = OptimizationObjective()
      new.ROIName = dialog.Contour.currentText()
      new.Metric = dialog.Metric.currentText()
      new.Condition = dialog.Condition.currentText()
      new.LimitValue = dialog.LimitValue.value()
      new.Weight = dialog.Weight.value()
      new.Robust = dialog.Robust.isChecked()

      self.Templates.list[template_id].Objectives.append(new)
      self.SaveTemplates.show()

      
      if(new.Robust == True):
        self.ObjectiveList.addItem(new.ROIName + ":\n" + new.Metric + " " + new.Condition + " " + str(new.LimitValue) + " Gy   (w=" + str(new.Weight) + ", robust)")
      else:
        self.ObjectiveList.addItem(new.ROIName + ":\n" + new.Metric + " " + new.Condition + " " + str(new.LimitValue) + " Gy   (w=" + str(new.Weight) + ")")




  def saveTemplates(self):
    self.Templates.SaveTemplates()
    self.SaveTemplates.hide()



  def template_selected(self):
    template_id = self.TemplateList.currentRow()
    template = self.Templates.list[template_id]
    self.Templates.SelectedID = template_id

    self.objective_setDisabled(False)
    self.ObjectiveList.clear()

    for objective in template.Objectives:
      self.ObjectiveList.addItem(objective.ROIName + ":\n" + objective.Metric + " " + objective.Condition + " " + str(objective.LimitValue) + " Gy   (w=" + str(objective.Weight) + ")")
      if not objective.ROIName in self.ContourList:
        self.ObjectiveList.item(self.ObjectiveList.count()-1).setForeground(Qt.lightGray)
