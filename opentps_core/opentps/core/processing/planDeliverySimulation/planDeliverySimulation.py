import re
from typing import Union, Optional, Sequence
import os
import numpy as np
np.random.seed(42)
import random
random.seed(42)
from opentps.core.data.dynamicData._dynamic3DModel import Dynamic3DModel
from opentps.core.data.dynamicData._dynamic3DSequence import Dynamic3DSequence
from opentps.core.data.plan._rtPlan import RTPlan
from opentps.core.data.images._ctImage import CTImage
from opentps.core.io import mcsquareIO
from opentps.core.processing.doseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
from opentps.core.utils.programSettings import ProgramSettings
from pydicom.uid import generate_uid
from opentps.core.data._rtStruct import ROIContour
from opentps.core.data.images._doseImage import DoseImage
from opentps.core.io.dicomIO import readDicomDose, writeRTDose
from opentps.core.processing.planDeliverySimulation.scanAlgoDeliveryTimings import BDT
from opentps.core.io.scannerReader import readScanner
from opentps.core.io.dataLoader import readSingleData
from opentps.core.processing.doseCalculation.doseCalculationConfig import DoseCalculationConfig
from opentps.core.data.images._deformation3D import Deformation3D
from opentps.core.data._dvh import DVH
from opentps.core.data._dvhBand import DVHBand
import time

class PlanDeliverySimulation():
    def __init__(self, plan:RTPlan, CT4D: Optional[Dynamic3DSequence]= None, 
    model3D: Optional[Dynamic3DModel]= None, deliverySimulationFolderName: Optional[str] = None,
    overwriteOutsideROI: Optional[ROIContour] = None, MCsquareSimulationPath: Optional[str] = None,
    saveDosesToFile:bool =True, saveDosesInObject:bool =False):
        self.plan = plan
        self.CT4D = CT4D
        self.model3D = model3D
        if deliverySimulationFolderName is None:
            self.deliverySimulationPath = os.path.join(ProgramSettings().simulationFolder, 'plan_delivery_simulations')
        else:
            self.deliverySimulationPath = os.path.join(ProgramSettings().simulationFolder, deliverySimulationFolderName)
        if not os.path.exists(self.deliverySimulationPath): os.mkdir(self.deliverySimulationPath)
        self.dir_4DD = os.path.join(self.deliverySimulationPath, '4DD')
        self.dir_4DDD = os.path.join(self.deliverySimulationPath, '4DDD')
        if self.CT4D is not None and self.model3D is None:
            self.model3D = Dynamic3DModel()
            self.model3D.name = 'MidP'
            self.model3D.seriesInstanceUID = generate_uid()
            self.model3D.computeMidPositionImage(CT4D, tryGPU=True)

        self.mc2 = self._initializeMCsquareParams(MCsquareSimulationPath, overwriteOutsideROI)
        self.computedDoses = []
        self.saveDosesToFile=saveDosesToFile
        self.saveDosesInObject=saveDosesInObject

    def simulate4DDose(self):
        """
        4D dose computation (range variation - no interplay). Steps:
        1) treatment plan `plan` is simulated on each phase of the 4DCT `CT4D`,
        2) each resulting dose is non-rigidly registered to the MidP CT `model3D.midp` 
        3) the average of these doses is computed
        All doses are saved in the simulation directory `simulation_dir`.
        """
        dir_4DD = os.path.join(self.deliverySimulationPath, '4DD')
        fx_dir = os.path.join(dir_4DD, f'{self.plan.numberOfFractionsPlanned}_fx')
        if not os.path.exists(dir_4DD):
            os.mkdir(dir_4DD)
        if not os.path.exists(fx_dir):
            os.mkdir(fx_dir)

        # Initialize reference dose on the MidP image
        dose_MidP = DoseImage().createEmptyDoseWithSameMetaData(self.model3D.midp)
        dose_MidP.name = "accumulated_4DD"
        for p in range(len(self.CT4D)):
            # Import CT
            CT = self.CT4D.dyn3DImageList[p]
            # MCsquare simulation
            dose = self.mc2.computeDose(CT, self.plan)
            dose.name = f"partial_4DD_p{p:03d}"
            if self.saveDosesInObject: self.computedDoses.append(dose)
            if self.saveDosesToFile: writeRTDose(dose, os.path.join(fx_dir, f"{dose.name}.dcm"))
            # Accumulate dose on MidP CT
            df = self.model3D.deformationList[p]
            dose_MidP._imageArray += df.deformImage(dose)._imageArray
        dose_MidP._imageArray /= len(self.CT4D)

        if self.saveDosesInObject: self.computedDoses.append(dose_MidP)
        if self.saveDosesToFile:
            output_accumulated_dose = os.path.join(fx_dir, dose_MidP.name + ".dcm")
            writeRTDose(dose_MidP, output_accumulated_dose)


    def simulate4DDynamicDose(self, save_partial_doses=True, start_phase=0):
        """
        4D dynamic dose computation (range variation + interplay). Steps:
        1) Delivery timings of the spots in `plan` are computed if not present
        2) treatment plan `plan` is dynamically simulated on the 4DCT `CT4D` in a loop until all spots are delivered,
        3) each resulting dose is non-rigidly registered to the MidP CT `model3D.midp` 
        3) the sum of these doses is computed
        All doses are saved in the simulation directory `simulation_dir`.
        """
        # Check if plan contains delivery timings
        if len(self.plan.spotTimings)==0:
            print('plan has no delivery timings. Querying ScanAlgo...')
            bdt = BDT(self.plan)
            self.plan = bdt.getPBSTimings(sort_spots="true")
        # plan.simplify()
            
        # Create necessary folders for simulations
        dir_4DDD = os.path.join(self.deliverySimulationPath, '4DDD')
        fx_dir = os.path.join(dir_4DDD, f'{self.plan.numberOfFractionsPlanned}_fx')
        if not os.path.exists(dir_4DDD):
            os.mkdir(dir_4DDD)
        if not os.path.exists(fx_dir):
            os.mkdir(fx_dir)
        
        # Create plans for simulations
        plan_4DCT = self._splitPlanToPhases(num_plans=len(self.CT4D), start_phase=start_phase)
        plan_names = list(plan_4DCT.keys())
        path_dose = os.path.join(fx_dir, f'starting_phase_{start_phase}')
        if not os.path.exists(path_dose):
            os.mkdir(path_dose)

        # Initialize reference dose on the MidP image
        dose_MidP = DoseImage().createEmptyDoseWithSameMetaData(self.model3D.midp)
        dose_MidP.name = f"accumulated_4DDD_starting_p{start_phase:03d}"
        
        for p in range(len(self.CT4D)):
            # Import CT
            CT = self.CT4D.dyn3DImageList[p]
            current_plan = plan_4DCT[plan_names[p]]

            # Create MCsquare simulation
            dose = self.mc2.computeDose(CT, current_plan)
            dose.name = f"partial_4DDD_p{p:03d}"
            if save_partial_doses:
                # if self.saveDosesInObject: self.computedDoses.append(dose)
                if self.saveDosesToFile: writeRTDose(dose, os.path.join(fx_dir, f"{dose.name}.dcm"))
            # Accumulate dose on MidP CT
            df = self.model3D.deformationList[p]
            dose_MidP._imageArray += df.deformImage(dose)._imageArray

        if self.saveDosesInObject: self.computedDoses.append(dose_MidP)
        if self.saveDosesToFile:
            output_accumulated_dose = os.path.join(path_dose, "accumulated_4DDD.dcm")
            writeRTDose(dose_MidP, output_accumulated_dose)

        return dose_MidP


    def simulate4DDynamicDoseScenarios(self, save_partial_doses=True, number_of_fractions=1, 
            number_of_starting_phases=1, number_of_fractionation_scenarios=1):
        """
        4D dynamic simulation under different scenarios.

        Parameters
        ----------
        plan : RTPlan
        CT4D : Dynamic3DSequence
        model3D : Dynamic3DModel
        simulation_dir : str
            Path to the simulation direcrotry where the doses are saved
        overwriteOutsideROI : ROIContour
            Overwrite values outside overwriteOutsideROI
        save_partial_doses: bool
            Whether or not to save partial doses, i.e. doses on each phase before accumulation
        number_of_fractions: int
            Number of fractions for delivering the treatment
        number_of_starting_phases: int
            Number of times we simulate the delivery where each time we start from a different phase.
            Hence, number_of_starting_phases <= len(4DCT)
        number_of_fractionation_scenarios: int
            Number fractionation scenarios: how many scenarios we select where each scenario
            is a random combination with replacement of 4DDD simulations with a specific starting phase
            For instance, if number_of_fractions=5 and number_of_fractionation_scenarios=3;
            Simulate 3 scenarios with starting phases [1,2,3,4,5]; [1,3,1,2,4]; [4, 5, 1, 4, 2].
        """
        self.plan.numberOfFractionsPlanned = number_of_fractions
        number_of_phases = len(self.CT4D)
        if number_of_starting_phases>number_of_phases:
            print(f"Number of starting phases must be smaller or equal to number of phases in 4DCT. Changing it to {number_of_phases}")
            number_of_starting_phases = number_of_phases
        if number_of_fractions==1 and number_of_fractionation_scenarios>1:
            print('There can only be one fractionation scenario when the number of fractions is 1.')
            return

        dir_4DDD = os.path.join(self.deliverySimulationPath, '4DDD')
        fx_dir = os.path.join(dir_4DDD, f'{number_of_fractions}_fx')
        dir_scenarios = os.path.join(fx_dir, 'scenarios')
        if not os.path.exists(dir_4DDD):
            os.mkdir(dir_4DDD)
        if not os.path.exists(fx_dir):
            os.mkdir(fx_dir)
        if not os.path.exists(dir_scenarios):
            os.mkdir(dir_scenarios)

        # 4DDD simulation
        accumulated_doses = []
        for start_phase in range(number_of_starting_phases):
            starting_phase_dir = os.path.join(fx_dir, f'starting_phase_{start_phase}')
            if not os.path.exists(starting_phase_dir):
                dose = self.simulate4DDynamicDose(save_partial_doses, start_phase)
                accumulated_doses.append(dose)
            else: # load accumulated dose
                dose = readDicomDose(os.path.join(starting_phase_dir, 'accumulated_4DDD.dcm'))
                accumulated_doses.append(dose)

        for scenario_number in range(number_of_fractionation_scenarios):
            # Initialize reference dose on the MidP image
            dose_MidP = DoseImage().createEmptyDoseWithSameMetaData(self.model3D.midp)
            dose_MidP.name = f'dose {number_of_fractions}fx scenario {str(scenario_number)}'
            selected_doses = self._randomCombinationWithReplacement(accumulated_doses, number_of_fractionation_scenarios)
            # Accumulate on MidP
            dose_MidP._imageArray += np.sum(np.stack([dose._imageArray for dose in selected_doses], axis=0), axis=0) / number_of_fractions
            if self.saveDosesInObject: self.computedDoses.append(dose_MidP)
            if self.saveDosesToFile:
                output_path = os.path.join(dir_scenarios, f'dose_scenario_{str(scenario_number)}.dcm')
                writeRTDose(dose_MidP, output_path)


    def simulatePlanOnContinuousSequence(self, midp: CTImage, ct_folder, def_fields_folder, sequence_timings, output_dose_path=None, save_all_doses=False, remove_interpolated_files=False, downsample=0, start_irradiation=0.):
        """
        4D dynamic simulation on a continuous sequence of CT. Same principle as simulate4DDD function but the 4DCT (i.e. continuous sequence)
        is not stored in the RAM.
        """
        if len(self.plan.spotTimings)==0:
            print('plan has no delivery timings. Querying ScanAlgo...')
            bdt = BDT(self.plan)
            self.plan = bdt.getPBSTimings(sort_spots="true")
        
        if output_dose_path is None:
            output_dose_path = os.path.join(ProgramSettings().simulationFolder, 'plan_delivery_simulations')
            if not os.path.exists(output_dose_path): os.mkdir(output_dose_path)
            output_dose_path = os.path.join(output_dose_path, 'continuous_seq')
            if not os.path.exists(output_dose_path): os.mkdir(output_dose_path)
        
        t_start = time.time()
        ctList = sorted(os.listdir(ct_folder))
        ctList = [x for x in ctList if not x.endswith('.raw') and not x.endswith('.RAW')]
        defList = sorted(os.listdir(def_fields_folder))
        defList = [x for x in defList if not x.endswith('.raw') and not x.endswith('.RAW')]

        # remove interpolated files
        if remove_interpolated_files:
            r1 = re.compile(r"_0\.[0-9]\.mhd$") # math _0.[0-9].mhd
            ctList = [x for x in ctList if r1.search(x) is None]
            defList = [x for x in defList if r1.search(x) is None]

        if downsample > 1:
            ctList = ctList[::downsample]
            defList = defList[::downsample]
            sequence_timings = sequence_timings[::downsample]

        assert len(ctList) == len(defList)
        assert len(ctList) == len(sequence_timings)

        # Split plan to list of plans
        plan_sequence = self._splitPlanToContinuousSequence(sequence_timings, start_irradiation)
        print(f'Plans splitted on the continuous sequence: results in {len(plan_sequence)} created.')

        # Initialize reference dose on the MidP image
        dose_MidP = DoseImage().createEmptyDoseWithSameMetaData(midp)
        dose_MidP.name = 'Accumulated dose'

        for i in plan_sequence:
            print(f"Importing CT {ctList[i]}")
            phaseImage = readSingleData(os.path.join(ct_folder, ctList[i]))

            dose_name = f"dose_on_phase_image_{str(i)}"
            self.mc2.nbPrimaries = np.minimum(1e5 * plan_sequence[i].numberOfSpots, 1e7)
            dose = self.mc2.computeDose(phaseImage, plan_sequence[i])
            dose.name = dose_name

            if save_all_doses:
                writeRTDose(dose, os.path.join(output_dose_path, dose_name+'.dcm'))

            ## Accumulate dose on MidP
            # Load deformation field on 3D image
            print(f"Importing deformation field {defList[i]}")
            df = readSingleData(os.path.join(def_fields_folder, defList[i]))
            df2 = Deformation3D()
            df2.initFromVelocityField(df)

            # Apply deformation field and accumulate on MidP
            dose_MidP._imageArray += df2.deformImage(dose)._imageArray


        t_end = time.time()
        print(f"it took {t_end-t_start} to simulate on the continuous sequence.")
        writeRTDose(dose_MidP, os.path.join(output_dose_path, "dose_midP_continuous_seq.dcm"))
        print("Total irradiation time:",self._getIrradiationTime(self.plan),"seconds")
        with open(os.path.join(output_dose_path, "treatment_info.txt"), 'w') as f:
            f.write(f"Total treatment time: {self._getIrradiationTime(self.plan)} seconds")
        self.mc2.nbPrimaries = 1e7 # set to default value


    def _splitPlanToPhases(self, num_plans=10, breathing_period=4., start_phase=0):
        """
        Split spots from `ReferencePlan` to `num_plans` plans according to the number of images in 4DCT, breathing period and start phase.
        Return a list of `num_plans` plans where each spot is assigned to a plan (=breathing phase)
        """
        time_per_phase = breathing_period / num_plans

        # Rearrange order of list CT4D to start at start_phase
        phase_number = np.append(np.arange(start_phase,num_plans), np.arange(0,start_phase))

        # Initialize plan for each image of the 4DCT
        plan_4DCT = {}
        for p in phase_number:
            plan_4DCT[p] = self.plan.createEmptyPlanWithSameMetaData()
            plan_4DCT[p].name = f"plan_phase_{p}"

        # Assign each spot to a phase depending on its timing
        num_beams = len(self.plan.beams)
        for b in range(num_beams):
            beam = self.plan.beams[b]
            current_beam_phase_offset = np.random.randint(num_plans) if b>0 else 0 # beams should start at different times
            print('current_beam_phase_offset',current_beam_phase_offset)
            for layer in beam.layers:
                # Assing each spot
                for s in range(len(layer.spotMUs)):
                    phase = int((layer.spotTimings[s] % breathing_period) // time_per_phase)
                    phase = (phase + current_beam_phase_offset) % num_plans
                    plan_4DCT[phase_number[phase]].appendSpot(beam, layer, s)

        return plan_4DCT


    def _splitPlanToContinuousSequence(self, sequence_timings, start_irradiation=0.):
        """
        Create a plan for each image in the continuous sequence where at least one spot is shot
        and assign each spot of the `ReferencePlan`to one of the created plans.
        Returns a dictionnary of plans where the index number corresponds to the image number in
        the continuous sequence.
        """
        # Check if plan include spot timings
        # start_irradiation \in [0,1] : moment at which to start the irradiation with beggining of 
        # continuous seq = 0. and end = 1.
        if len(self.plan.spotTimings)==0:
            print('plan has no delivery timings. Querying ScanAlgo...')
            bdt = BDT(self.plan)
            self.plan = bdt.getPBSTimings(sort_spots="true")

        # Iterate on spots from referencePlan and add each spot to a specific image of the continuous sequence:
        plan_sequence = {} # list of plans of the sequence
        start_time = start_irradiation * sequence_timings[-1]
        beam_fraction_time = (1 / len(self.plan.beams)) * sequence_timings[-1] # each beam must be started independently
        count_beam = 0
        for beam in self.plan.beams:
            beam_time = count_beam * beam_fraction_time
            count_beam += 1
            for layer in beam.layers:
                for t in range(len(layer.spotTimings)):
                    # Check closest sequence timing to spot timing
                    current_time = (start_time + beam_time + layer.spotTimings[t]) % sequence_timings[-1] # modulo operation to restart at beggining in a loop if spotTiming > sequence_timings[-1]
                    idx = np.nanargmin(np.abs(sequence_timings - current_time))
                    if idx not in plan_sequence:
                        # Create plan on image idx
                        plan_sequence[idx] = self.plan.createEmptyPlanWithSameMetaData()

                    plan_sequence[idx].appendSpot(beam, layer, t)
        return plan_sequence


    def _initializeMCsquareParams(self, workdir=None, overwriteOutsideROI=None):
        mc2 = MCsquareDoseCalculator()
        if workdir is not None:
            mc2.simulationDirectory = workdir

        mc2.ctCalibration = readScanner(DoseCalculationConfig().scannerFolder)
        mc2.beamModel = mcsquareIO.readBDL(DoseCalculationConfig().bdlFile)
        mc2.nbPrimaries = 1e7
        mc2.overwriteOutsideROI = overwriteOutsideROI
        return mc2


    def _randomCombinationWithReplacement(self, iterable, r):
        """
        Random selection from itertools.combinations_with_replacement(iterable, r)
        Taken from https://docs.python.org/3/library/itertools.html#itertools-recipes
        """
        pool = tuple(iterable)
        n = len(pool)
        indices = random.choices(range(n), k=r)
        return [pool[i] for i in indices]


    def _getIrradiationTime(self, plan):
        assert len(plan.spotTimings)>0
        total_time = [plan.beams[i].layers[-1].spotTimings[-1] for i in range(len(plan.beams))]
        return np.sum(total_time)


    def computeDVHBand(self, doseList:Sequence[DoseImage] = [], ROIList:Sequence[ROIContour] = []):
        dvh_bands = []
        median_dose = DoseImage().createEmptyDoseWithSameMetaData(doseList[0])
        median_dose._imageArray = np.median(np.stack([dose.imageArray for dose in doseList], axis=0), axis=0)
        for roi in ROIList:
            dvh = DVH(roi, doseList[0])
            volumes = dvh._volume.reshape(-1,1)
            for i in range(1,len(doseList)):
                dvh = DVH(roi, doseList[i])
                volumes = np.hstack((volumes, dvh._volume.reshape(-1,1)))
            dvh_band = DVHBand()
            dvh_band._roiName = roi.name
            dvh_band._dose = dvh._dose
            dvh_band._volumeLow = np.amin(volumes, axis=1)
            dvh_band._volumeHigh = np.amax(volumes, axis=1)
            dvh_band._nominalDVH = DVH(roi, median_dose)
            dvh_bands.append(dvh_band)
        return dvh_bands

    
    def computeDVHBand4DDD(self, ROIList, singleFraction=True):
        if singleFraction:
            # Results for the first fraction
            simulation_dir = os.path.join(self.deliverySimulationPath, '4DDD', f'{self.plan.numberOfFractionsPlanned}_fx')
            folders = [folder for folder in os.listdir(simulation_dir) if folder!="scenarios"]

            dose_list = []
            for folder in folders:
                dose_path = os.path.join(simulation_dir, folder, 'accumulated_4DDD.dcm')
                dose = readDicomDose(dose_path)
                dose_list.append(dose)
        else:
            # Results from all fractions
            simulation_dir = os.path.join(self.deliverySimulationPath, '4DDD', f'{self.plan.numberOfFractionsPlanned}_fx', 'scenarios')
            files = os.listdir(simulation_dir)

            dose_list = []
            for file in files:
                dose_path = os.path.join(simulation_dir, file)
                dose = readDicomDose(dose_path)
                dose_list.append(dose)
        
        dvh_bands = self.computeDVHBand(dose_list, ROIList)
        return dvh_bands

