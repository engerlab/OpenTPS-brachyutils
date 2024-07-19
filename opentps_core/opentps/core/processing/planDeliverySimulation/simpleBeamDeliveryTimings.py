import numpy as np
from opentps.core.data.plan._rtPlan import RTPlan
from opentps.core.io.serializedObjectIO import saveRTPlan
from opentps.core.data.MCsquare import BDL
from opentps.core.processing.planDeliverySimulation.irradiationDurationLUT import IrradiationDurationLUT

class SimpleBeamDeliveryTimings:
    """
    Simple Beam Delivery Timings.
    This class computes the timings for each spot in the plan.

    Attributes
    ----------
    plan : RTPlan
        The plan assiocated with the timings.
    irradiationDurationLUT : IrradiationDurationLUT
        The look-up table (LUT) for the irradiation duration.
    scanningSpeed : float (default: 8000.)
        The scanning speed in mm/s.
    layerSwitchUpDuration : float (default: 6.)
        The layer switch up duration in s.
    layerSwitchDownDuration : float (default: 0.6)
        The layer switch down duration in s.
    """
    def __init__(self, plan: RTPlan):
        self.plan = plan
        self.irradiationDurationLUT = IrradiationDurationLUT()
        self.scanningSpeed: float = 8000. # mm/s
        self.layerSwitchUpDuration: float = 6.
        self.layerSwitchDownDuration: float = 0.6

    def getPBSTimings(self, sort_spots="true"):
        """
        Add timings for each spot in the plan

        Parameters
        ----------
        sort_spots : bool (default: True)
            If True, the spots are sorted by their start time.

        Returns
        -------
        plan : RTPlan
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
        """
        Compute the irradiation duration for a given energy and MU array.

        Parameters
        ----------
        energy : float
            The energy in MeV.
        mu : array of floats
            The MU.

        Returns
        -------
        irradiationDuration : array of floats
            The irradiation duration in s.
        """

        irradiationDuration = mu * np.interp(energy, self.irradiationDurationLUT.nominalEnergy, self.irradiationDurationLUT.duration)
        return irradiationDuration


    def getTimingsAndSavePlan(self, output_path):
        """
        Compute the timings for each spot in the plan and save the plan.

        Parameters
        ----------
        output_path : str
            The path to save the plan.
        """
        plan_with_timings = self.getPBSTimings(sort_spots="true")
        saveRTPlan(plan_with_timings, output_path)
