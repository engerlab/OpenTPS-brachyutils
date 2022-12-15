import numpy as np
from opentps.core.data.plan._rtPlan import RTPlan
from opentps.core.io.serializedObjectIO import saveRTPlan
from opentps.core.data.MCsquare import BDL
from opentps.core.processing.planDeliverySimulation.irradiationDurationLUT import IrradiationDurationLUT

class SimpleBeamDeliveryTimings:
    """
    Simple Beam Delivery Timings
    """
    def __init__(self, plan: RTPlan):
        self.plan = plan
        self.irradiationDurationLUT = IrradiationDurationLUT()
        self.scanningSpeed: float = 8000. # mm/s
        self.layerSwitchUpDuration: float = 6.
        self.layerSwitchDownDuration: float = 0.6

    def getPBSTimings(self, sort_spots="true"):
        """
        Add timings for each spot in the plan:
        OUTPUT:
            RTPlan with timings
        """
        plan = self.plan.copy()
        if np.any(plan.spotMUs<0.01):
            print("Warning: Plan contains spots MU < 0.01 --> Delivery timings might not be accurate.")
        if sort_spots:
            plan.reorderPlan()

        for b, beam in enumerate(plan.beams):
            accumul_layer_time = 0.
            for l, layer in enumerate(beam.layers):
                irradiationTime = self.computeIrradiationDuration(energy=layer.nominalEnergy, mu=layer.spotMUs)
                irradiationTime = np.maximum(250e-6, irradiationTime) #minimum 250us for irradiation
                layer._irradiationDuration = irradiationTime
                x = layer.spotX
                y = layer.spotY

                spotDist = np.sqrt(np.diff(x)*np.diff(x) + np.diff(y)*np.diff(y))
                scanningTime = spotDist / self.scanningSpeed
                if l==0:
                    scanningTime = np.append(0, scanningTime)
                else:
                    energyDiff = beam.layers[l].nominalEnergy - beam.layers[l-1].nominalEnergy
                    layerSwitchTime = self.layerSwitchDownDuration if energyDiff <=0 else self.layerSwitchUpDuration
                    scanningTime = np.append(layerSwitchTime, scanningTime)
                layer._startTime = np.cumsum(scanningTime) + np.cumsum(irradiationTime) - irradiationTime + accumul_layer_time
                accumul_layer_time += np.sum(scanningTime) + np.sum(irradiationTime)

        return plan

    
    def computeIrradiationDuration(self, energy, mu):
        return mu * np.interp(energy, self.irradiationDurationLUT.nominalEnergy, self.irradiationDurationLUT.duration)


    def getTimingsAndSavePlan(self, output_path):
        plan_with_timings = self.getPBSTimings(sort_spots="true")
        saveRTPlan(plan_with_timings, output_path)
