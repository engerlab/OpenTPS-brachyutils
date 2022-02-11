import os
import platform
import shutil

import MCsquare
from Core.Data.MCsquare.mcsquareConfig import MCsquareConfig


class MCsquareDoseEngine:
    def __init__(self):
        self.Path_MCsquareLib = str(MCsquare.__path__[0])
        self.WorkDir = os.path.join(os.path.expanduser('~'), "Work")
        self.DoseName = "MCsquare_dose"
        self.BDL = None
        self.Scanner = None
        self.NumProtons = 1e7
        self.MaxUncertainty = 2.0
        self.dose2water = 1
        self.PlanOptimization = "none"  # possible options: none, beamlet-free
        self.config = {}
        self.Robustness_Strategy = "Disabled"
        self.SetupSystematicError = [2.5, 2.5, 2.5]  # mm
        self.SetupRandomError = [1.0, 1.0, 1.0]  # mm
        self.RangeSystematicError = 3.0  # %
        self.Crop_CT_contour = {}
        self.SimulatedParticles = 0
        self.SimulatedStatUncert = -1
        self.Compute_DVH_only = 0

    def exportBDL(self, bdl, filePath):
        with open(filePath, 'w') as file:
            file.write(str(bdl))

    def exportConfig(self, config, filePath):
        with open(filePath, 'w') as file:
            file.write(str(config))

    def exportCT(self, CT, file_path, Crop_CT_contour):
        #TODO
        pass

    def exportPlan(self, plan, path):
        #TODO
        pass

    def importDose(self, plan):
        #TODO
        pass

    def init_simulation_directory(self):
        # Create simulation directory
        if not os.path.isdir(self.WorkDir):
            os.mkdir(self.WorkDir)

        # Clean structs directory
        struct_dir = os.path.join(self.WorkDir, "structs")
        if os.path.isdir(struct_dir):
            shutil.rmtree(struct_dir)

        # Clean output directory
        out_dir = os.path.join(self.WorkDir, "Outputs")
        if os.path.isdir(out_dir):
            file_list = os.listdir(out_dir)
            for file in file_list:

                if (file.endswith(".mhd")): os.remove(os.path.join(out_dir, file))
                if (file.endswith(".raw")): os.remove(os.path.join(out_dir, file))
                if (file.endswith(".txt")): os.remove(os.path.join(out_dir, file))
                if (file.endswith(".bin")): os.remove(os.path.join(out_dir, file))

                if (file == "tmp" and os.path.isdir(os.path.join(out_dir, file))):
                    folder_path = os.path.join(self.WorkDir, "Outputs", "tmp")
                    for root, dirs, files in os.walk(folder_path, topdown=False):
                        for name in files: os.remove(os.path.join(root, name))
                        for name in dirs: os.rmdir(os.path.join(root, name))

    def MCsquare_version(self):
        if (platform.system() == "Linux"):
            os.system(os.path.join(self.Path_MCsquareLib, "MCsquare_linux") + " -v")
        elif (platform.system() == "Windows"):
            os.system(os.path.join(self.Path_MCsquareLib, "MCsquare_win.exe") + " -v")
        else:
            print("Error: not compatible with " + platform.system() + " system.")

    def run(self, CT, Plan):
        print("Prepare MCsquare simulation")

        self.init_simulation_directory()

        # Export CT image
        self.exportCT(CT, os.path.join(self.WorkDir, "CT.mhd"), self.Crop_CT_contour)

        # Export treatment plan
        self.BDL.import_BDL()
        self.exportPlan(Plan, os.path.join(self.WorkDir, "PlanPencil.txt"), CT, self.BDL)

        # Generate MCsquare configuration file
        self.config = MCsquareConfig(self.WorkDir, self.NumProtons, self.Scanner.get_path(), self.BDL.get_path(), 'CT.mhd', 'PlanPencil.txt')
        if (self.dose2water > 0):
            self.config["Dose_to_Water_conversion"] = "OnlineSPR"
        else:
            self.config["Dose_to_Water_conversion"] = "Disabled"
        self.config["Stat_uncertainty"] = self.MaxUncertainty
        if (self.Compute_DVH_only > 0):
            self.config["Dose_MHD_Output"] = False
            self.config["Compute_DVH"] = True
        self.exportConfig(self.config)

        # Start simulation
        print("\nStart MCsquare simulation")
        if (platform.system() == "Linux"):
            os.system("cd " + self.WorkDir + " && " + os.path.join(self.Path_MCsquareLib, "MCsquare"))
        elif (platform.system() == "Windows"):
            os.system(self.WorkDir[0:2] + " && cd " + self.WorkDir + " && " + os.path.join(self.Path_MCsquareLib,
                                                                                           "MCsquare_win.bat"))
        else:
            print("Error: not compatible with " + platform.system() + " system.")

        # Import dose result
        mhd_dose = self.importDose(Plan)

        return mhd_dose
