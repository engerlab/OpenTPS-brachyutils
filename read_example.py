import datetime
import os
import sys
import numpy as np
import scipy.sparse as sp
import argparse

from matplotlib import pyplot as plt
from Process.PatientData import *
from Process.PlanOptimization import *
from Process.MCsquare import *
from Process.MCsquare_sparse_format import *
from Process.RTdose import *
from Process.DVH import *

def main(argv = None):

    if argv == None:
        argv = sys.argv[1:]


    description = "Script to launch the optimization"

    parser = argparse.ArgumentParser()
    parser.add_argument("-n","--nmax",default=500,type = int,help="number of iterations per job")
    parser.add_argument("--ftol",default=1e-10,type = float, help="Relative error in ifun(xopt) acceptable for convergence")
    parser.add_argument("--step",default=1.,type = float, help="Gradient step used (inverse of Lipschitz constant) ")
    parser.add_argument("-o","--output",default="test.npy",help="Output file name ")



    # create parser for Gradient, BFGS, L-BFGS  method
    parser.add_argument("--method",default="BFGS",help="Method to use to solve optimization (Gradient,BFGS,L-BFGS, Scipy-lBFGS)")

    options = parser.parse_args()

    return options

if __name__ == '__main__':

    options = main()
    print(options)

    home = os.getcwd()

    # user config:
    patient_data_path = "data/Prostate_3mm"

    # Load patient data
    Patients = PatientList()
    Patients.list_dicom_files(patient_data_path, 1)
    Patients.print_patient_list()
    Patients.list[0].import_patient_data() # import patient 0

    # Configure MCsquare
    mc2 = MCsquare()
    mc2.BDL.selected_BDL = mc2.BDL.list[1] # UMCG_P1_v2_RangeShifter
    mc2.Scanner.selected_Scanner = mc2.Scanner.list[0] # UCL_Toshiba
    mc2.NumProtons = 5e4
    mc2.dose2water = True

    # Plan parameters:
    ct = Patients.list[0].CTimages[0]
    Target = Patients.list[0].RTstructs[0].Contours[10] # MIROpt-struct
    OAR = Patients.list[0].RTstructs[0].Contours[4] # Rectum


    # Generate new plan
    #file_path = '/home/ucl/irec/swuycken/opentps/data/OpenTPS/Plan_arc_0-360_2_noAirVox_layerspacing4_spotspacing3_RTV6.tps'
    #file_path = '/home/ucl/irec/swuycken/opentps/data/Prostate_3mm/OpenTPS/Plan_arc_0-360_1-5_noAirVox_layerspacing4_spotspacing5_BDL_UMCG.tps'
    #file_path = '/home/ucl/irec/swuycken/opentps/data/OpenTPS/Plan_arc_0-360_1-5_noAirVox_layerspacing4_spotspacing5.tps'
    #file_path = '/home/ucl/irec/swuycken/opentps/data/OpenTPS/Plan_arc_m90-90_1_noAirVox_layerspacing4_spotspacing5.tps'
    #file_path = '/home/ucl/irec/swuycken/opentps/data/OpenTPS/Plan_arc_m90_90_1_noAirVox_layerspacing3.tps'
    #file_path = '/home/sophie/opentps/data/OpenTPS/Plan_arc_m90-90_1-5_noAirVox.tps'
    #file_path = os.path.join(patient_data_path,'OpenTPS/Plan_test_2beam.tps')
    file_path = os.path.join(patient_data_path,'OpenTPS/Plan_arc_m90-90_1-5_noAirVox.tps')
    plan = RTplan()
    plan.load(file_path)

    Patients.list[0].Plans.append(plan)

    # optimization objectives
    # MIROpt-structure
    plan.Objectives.setTarget("MIROpt-structure", 60.0)
    #plan.Objectives.setHotspotObj(65.0)
    plan.Objectives.list = []
    plan.Objectives.addObjective("MIROpt-structure", "Dmax", "<", 60.0, 1.0)
    plan.Objectives.addObjective("MIROpt-structure", "Dmin", ">", 60.0, 1.0)
    #plan.Objectives.addObjective("mask_hotSpot", "Dmax", "<", 60.0, 1.0)


    # Compute beamlets
    #beamlet_file = os.path.join(patient_data_path, "OpenTPS/BeamletMatrix_arc_0-360_2_noAirVox_layerspacing4_spotspacing3_RTV6.blm")
    #beamlet_file = os.path.join(patient_data_path, "OpenTPS/BeamletMatrix_arc_0-360_1-5_noAirVox_layerspacing4_spotspacing5_BDL_UMCG.blm")
    #beamlet_file = os.path.join(patient_data_path, "OpenTPS/BeamletMatrix_arc_0-360_1-5_noAirVox_layerspacing4_spotspacing5.blm")
    #beamlet_file = os.path.join(patient_data_path, "OpenTPS/BeamletMatrix_arc_m90_90_1_noAirVox_layerspacing4_spotspacing5.blm")
    #beamlet_file = os.path.join(patient_data_path, "OpenTPS/BeamletMatrix_arc_m90-90_1_noAirVox_layerspacing3.blm")
    #beamlet_file = os.path.join(patient_data_path, "OpenTPS/BeamletMatrix_test_2beam.blm")
    beamlet_file = os.path.join(patient_data_path, "OpenTPS/BeamletMatrix_arc__m90-90_1-5_noAirVox.blm")

    if os.path.isfile(beamlet_file):
      beamlets = MCsquare_sparse_format()
      beamlets.load(beamlet_file)
      beamlets.print_memory_usage()
    else:
      beamlets = mc2.MCsquare_beamlet_calculation(ct, plan) # already scaled to Gray units
      beamlets.save(beamlet_file)
    plan.beamlets = beamlets



    print("***********************************")
    print("*           INFO on job           *")
    print("***********************************\n")
    print("TPS file used: ", file_path)
    print("Beamlet file used: ", beamlet_file, "\n")
    print(" ### Input parameters ### \n")
    for arg in vars(options):
      print(' {} {}'.format(arg, getattr(options, arg) or ''))


    # Compute pre-optimization dose
    dose_vector = sp.csc_matrix.dot(beamlets.BeamletMatrix, beamlets.Weights)
    dose = RTdose()
    dose.Image = np.reshape(dose_vector, ct.GridSize, order='F')
    dose.Image = np.flip(dose.Image, (0,1)).transpose(1,0,2)
    dose.PixelSpacing = [ct.PixelSpacing[0],ct.PixelSpacing[1],ct.PixelSpacing[2]]
    #dose = RTdose().Initialize_from_beamlet_dose(plan.PlanName, plan.beamlets, dose_vector, ct)

    # Compute DVH
    Target_DVH = DVH(dose, Target)
    OAR_DVH = DVH(dose, OAR)

    # Display dose
    plt.figure(figsize=(10,10))
    plt.subplot(2,2,1)
    plt.imshow(ct.Image[:,:,22], cmap='gray')
    plt.imshow(Target.ContourMask[:,:,22], alpha=.2, cmap='binary') # PTV
    plt.imshow(dose.Image[:,:,22], cmap='jet', alpha=.4)
    plt.title("Pre-optimization dose")
    plt.subplot(2,2,2)
    plt.plot(Target_DVH.dose, Target_DVH.volume, label=Target_DVH.ROIName)
    plt.plot(OAR_DVH.dose, OAR_DVH.volume, label=OAR_DVH.ROIName)
    plt.title("Pre-optimization DVH")

    # Optimize treatment plan
    w, dose_vector, ps = OptimizeWeights(plan, Patients.list[0].RTstructs[0].Contours, options.nmax, options.ftol, options.method,options.step, options.output)
    beamlets.Weights = np.array(w, dtype=np.float32)

    dose.Image = np.reshape(dose_vector, ct.GridSize, order='F')
    dose.Image = np.flip(dose.Image, (0,1)).transpose(1,0,2)

    # Compute DVH
    Target_DVH = DVH(dose, Target)
    print('D95 = ' + str(Target_DVH.D95) + ' Gy')
    OAR_DVH = DVH(dose, OAR)

    # Display dose
    plt.subplot(2,2,3)
    plt.imshow(ct.Image[:,:,22], cmap='gray')
    #plt.imshow(ct.Image[:,:,53], cmap='gray')
    plt.imshow(Target.ContourMask[:,:,22], alpha=.2, cmap='binary') # PTV
    plt.imshow(dose.Image[:,:,22], cmap='jet', alpha=.4)
    plt.title("Optimized dose")
    plt.subplot(2,2,4)
    plt.plot(Target_DVH.dose, Target_DVH.volume, label=Target_DVH.ROIName)
    plt.plot(OAR_DVH.dose, OAR_DVH.volume, label=OAR_DVH.ROIName)
    plt.title("Optimized DVH")
    plt.show()



    #plan.update_spot_weights(w)
    # save plan
    '''output_path = os.path.join(patient_data_path, "OpenTPS")
    if not os.path.isdir(output_path):
        os.mkdir(output_path)
    plan_file = os.path.join(output_path, "Plan_" + plan.PlanName + "_" + datetime.datetime.today().strftime("%b-%d-%Y_%H-%M-%S") + ".tps")
    plan.save(plan_file)'''
