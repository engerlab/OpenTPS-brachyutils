import os
from datetime import datetime

from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, pyqtSignal
from opentps.core.data import Patient
from opentps.core.data.plan import RTPlan
from opentps.core.processing.doseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
from opentps.core.processing.planEvaluation.robustnessEvaluation import RobustnessEval
from opentps.gui.panels.patientDataWidgets import PatientDataComboBox
from opentps.gui.panels.planDesignPanel.robustnessSettings import RobustnessSettings


class PlanEvaluationPanel(QWidget):
    Robustness_analysis_recomputed = pyqtSignal()

    def __init__(self, viewController):
        QWidget.__init__(self)

        self._patient:Patient = None
        self._viewController = viewController

        self.robustness_scenarios = []

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self._planLabel = QLabel('plan:')
        self.layout.addWidget(self._planLabel)
        self._planComboBox = PatientDataComboBox(patientDataType=RTPlan, patient=self._patient, parent=self)
        self.layout.addWidget(self._planComboBox)

        self._robustSettings = RobustnessSettings(self._viewController, planEvaluation=True, parent=self)
        self.layout.addWidget(self._robustSettings)

        self.layout.addSpacing(30)
        self.button_hLoayout = QHBoxLayout()
        self.layout.addLayout(self.button_hLoayout)
        self.ComputeScenariosButton = QPushButton('Compute \n Scenarios')
        self.ComputeScenariosButton.setEnabled(False)
        self.button_hLoayout.addWidget(self.ComputeScenariosButton)
        self.ComputeScenariosButton.clicked.connect(self.computeRobustnessScenarios)
        self.layout.addWidget(QLabel('<b>!!!Disabled (refactoring)!!!</b>'))
        self.layout.addWidget(QLabel('<b>!!!Plan evaluation soon available!!!</b>'))
        self.layout.addSpacing(40)

        self.layout.addWidget(QLabel('<b>Displayed dose:</b>'))
        self.DisplayedDose = QComboBox()
        self.DisplayedDose.addItems(['Nominal', 'Worst scenario', 'Voxel wise minimum', 'Voxel wise maximum'])
        self.layout.addWidget(self.DisplayedDose)
        self.layout.addSpacing(30)

        self.layout.addWidget(QLabel('<b>Prescription:</b>'))
        self.Prescription = QDoubleSpinBox()
        self.Prescription.setRange(0.0, 100.0)
        self.Prescription.setSingleStep(1.0)
        self.Prescription.setValue(60.0)
        self.Prescription.setSuffix(" Gy")
        self.layout.addWidget(self.Prescription)
        self.layout.addSpacing(10)

        self.layout.addWidget(QLabel('<b>Evaluation metric:</b>'))
        self.Metric = QComboBox()
        self.Metric.addItems(['D95', 'MSE'])
        self.layout.addWidget(self.Metric)
        self.layout.addSpacing(10)

        self.CI_label = QLabel('<b>Confidence interval:</b>')
        self.layout.addWidget(self.CI_label)
        self.CI = QSlider(Qt.Horizontal)
        self.CI.setMinimum(0)
        self.CI.setMaximum(100)
        self.CI.setValue(90)
        self.layout.addWidget(self.CI)
        self.layout.addStretch()

        self.Metric.currentIndexChanged.connect(self.recompute_robustness_analysis)
        self.DisplayedDose.currentIndexChanged.connect(self.recompute_robustness_analysis)
        self.Prescription.valueChanged.connect(self.recompute_robustness_analysis)

        self.setCurrentPatient(self._viewController.currentPatient)
        self._viewController.currentPatientChangedSignal.connect(self.setCurrentPatient)

        self.recompute_robustness_analysis()

    def setCurrentPatient(self, patient:Patient):
        self._planComboBox.setPatient(patient)

    @property
    def selectedPlan(self):
        return self._planComboBox.selectedPlan

    def computeRobustnessScenarios(self):
        # TODO: Take CT, target, etc. from plan.planDesign. Same for MC2 config

        # find selected CT image
        if (self.CT_disp_ID < 0):
            print("Error: No CT image selected")
            return
        ct_patient_id, ct_id = self.Patients.find_CT_image(self.CT_disp_ID)
        ct = self.Patients.list[ct_patient_id].CTimages[ct_id]

        # find selected plan
        if (self.Plan_disp_ID < 0):
            print("Error: No treatment plan selected")
            return
        plan_patient_id, plan_id = self.Patients.find_plan(self.Plan_disp_ID)
        plan = self.Patients.list[plan_patient_id].Plans[plan_id]

        # find contours
        Target_name = self.Target.currentText()
        patient_id, struct_id, contour_id = self.Patients.find_contour(Target_name)
        AllContours = self.Patients.list[patient_id].RTstructs[struct_id].Contours

        # configure MCsquare module
        doseCalculator = MCsquareDoseCalculator()
        doseCalculator.BDL.selected_BDL = self.Dose_calculation_param["BDL"]
        doseCalculator.Scanner.selected_Scanner = self.Dose_calculation_param["Scanner"]
        doseCalculator.NumProtons = self.Dose_calculation_param["NumProtons"]
        doseCalculator.MaxUncertainty = self.Dose_calculation_param["MaxUncertainty"]
        doseCalculator.dose2water = self.Dose_calculation_param["dose2water"]
        doseCalculator.SetupSystematicError = self.RobustEval["syst_setup"]
        doseCalculator.SetupRandomError = self.RobustEval["rand_setup"]
        doseCalculator.RangeSystematicError = self.RobustEval["syst_range"]

        if (self.RobustEval["Strategy"] == 'DoseSpace'):
            doseCalculator.Robustness_Strategy = "DoseSpace"
        elif (self.RobustEval["Strategy"] == 'ErrorSpace_stat'):
            doseCalculator.Robustness_Strategy = "ErrorSpace_stat"
        else:
            doseCalculator.Robustness_Strategy = "ErrorSpace_regular"

        # Crop CT image with contour:
        if (self.Dose_calculation_param["CropContour"] == "None"):
            doseCalculator.Crop_CT_contour = {}
        else:
            patient_id, struct_id, contour_id = self.Patients.find_contour(self.Dose_calculation_param["CropContour"])
            doseCalculator.Crop_CT_contour = self.Patients.list[patient_id].RTstructs[struct_id].Contours[contour_id]

        # run MCsquare simulation
        scenarios = doseCalculator.MCsquare_RobustScenario_calculation(ct, plan, AllContours)

        # save data
        output_path = os.path.join(self.data_path, "OpenTPS")
        if not os.path.isdir(output_path):
            os.mkdir(output_path)
        output_folder = os.path.join(output_path,
                                     "RobustnessTest_" + datetime.datetime.today().strftime("%b-%d-%Y_%H-%M-%S"))
        scenarios.save(output_folder)

        self.robustness_scenarios = scenarios
        self.recompute_robustness_analysis()

    def recompute_robustness_analysis(self):
        # TODO: Take CT, target, etc. from plan.planDesign. Same for MC2 config

        if (self.robustness_scenarios == []): return

        CI = self.CI.value()
        self.CI_label.setText('<b>Confidence interval:</b> &nbsp;&nbsp;&nbsp; ' + str(CI) + " %")

        # target contour
        Target_name = self.Target.currentText()
        if (Target_name == ''): return
        patient_id, struct_id, contour_id = self.Patients.find_contour(Target_name)
        Target = self.Patients.list[patient_id].RTstructs[struct_id].Contours[contour_id]
        TargetPrescription = self.Prescription.value()

        self.robustness_scenarios.DoseDistributionType = self.DisplayedDose.currentText()
        # TODO: update with new attribut robustnessEval.analysisStrategy.DOSIMETRIC
        if (self.robustness_scenarios.SelectionStrategy == RobustnessEval.Strategies.DOSIMETRIC):
            self.robustness_scenarios.dosimetric_space_analysis(self.Metric.currentText(), CI, Target,
                                                                TargetPrescription)
        else:
            self.robustness_scenarios.error_space_analysis(self.Metric.currentText(), Target, TargetPrescription)

        self.Robustness_analysis_recomputed.emit()