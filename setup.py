from setuptools import setup

setup(
    name='opentps',
    version='v1.0',
    packages=['GUI', 'GUI.Panels', 'GUI.Panels.PlanOptiPanel', 'GUI.Viewer', 'GUI.Viewer.DataForViewer',
              'GUI.Viewer.DataViewerComponents', 'GUI.Viewer.DataViewerComponents.ImageViewerComponents', 'Core',
              'Core.IO', 'Core.Data', 'Core.Data.Plan', 'Core.Data.Images', 'Core.Data.CTCalibrations',
              'Core.Processing', 'Core.Processing.Registration', 'Core.Processing.DoseCalculation',
              'Core.Processing.PlanOptimization', 'Core.Processing.PlanOptimization.Solvers',
              'Core.Processing.PlanOptimization.Objectives', 'Core.Processing.PlanOptimization.Acceleration',
              'Core.Processing.DeformableDataAugmentationToolBox'],
    url='http://www.opentps.org/',
    license='Apache 2.0',
    author='Université catholique de Louvain',
    author_email='',
    description='Open source TPS for advanced proton therapy'
)
