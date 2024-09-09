import requests
import numpy as np
from opentps.core.data.plan._rtPlan import RTPlan
from opentps.core.data.plan._scanAlgoPlan import ScanAlgoPlan
from opentps.core.io.serializedObjectIO import saveRTPlan
from opentps.core.processing.planDeliverySimulation.scanAlgoSimulationConfig import ScanAlgoSimulationConfig

class ScanAlgoBeamDeliveryTimings:
    """
    Beam Delivery Timings for ScanAlgo

    Attributes
    ----------
    plan: RTPlan
        Treatment plan without spot delivery timings information
    URL: str
        ScanAlgo REST gateway URL for sending request. If None, use default value in config file ScanAlgoSimulationConfig.cfg
    gantry: str
        Type of gantry, either 'POne' or 'PPlus'. If None, use default value in config file ScanAlgoSimulationConfig.cfg
    """
    def __init__(self, plan: RTPlan, URL:str=None, gantry:str=None, auth=None, spotTuneId=None):
        self.plan = plan
        if URL is None and gantry is None:
            config = ScanAlgoSimulationConfig()
            self.gantry = config.gantry
            self.url = config.gateway
        else:
            assert URL is not None and gantry is not None
            if not (gantry=="POne" or gantry=="PPlus"):
                raise ValueError(f"Gantry {gantry} not valid, type must be either 'POne' or 'PPlus'.")
            self.gantry = gantry
            self.url = URL
        self.auth=auth
        self.spotTuneId=spotTuneId


    def getPBSTimings(self, sort_spots="true"):
        """
        Returns a plan containing spot delivery timings.

        Parameters
        ----------
        sort_spots:str
            "true" to use scanAlgo automatic spot sorting. Otherwise use the order of the original plan
        Returns
        -------
        plan: RTPlan
            original plan with spot delivery timings information, i.e.
            plan[beamIndex][layerIndex].spotTimings: list of starting delivery times corresponding to each spot located at plan[beamIndex][layerIndex].spotXY
            plan[beamIndex][layerIndex].spotIrradiationDurations: list of duration of irradiation of each spot located at plan[beamIndex][layerIndex].spotXY

        Notes
        -----
        The number of spots of the returned might differ from self.plan because the spot might be delivered in multiple pulses.
        Thus the returned plan will contain multiple spots at the same (X,Y) location with different MUs and timings
        """
        plan = self.plan.copy()
        gantry_angles = [] if plan._beams==[] else [beam.gantryAngle for beam in plan._beams]
        for index,beam in enumerate(plan._beams):
            data = ScanAlgoPlan(plan, self.gantry, index, sort_spots=sort_spots, spotTuneId=self.spotTuneId)
            gantry_angle = float(data.gantryangle) if self.gantry=="PPlus" else float(data.gantryAngle)
            scanAlgo = requests.post(self.url,json=data.__dict__, auth=self.auth).json()
            if 'cause' in scanAlgo:
               print("!!!!!!!!! ScanAlgo ERROR in beam !!!!!!! ", index)
               print('\n')
               print(scanAlgo['cause'])
               print('\n')
            if 'error' in scanAlgo:
               print("ScanAlgo ERROR")
               print('\n')
               print(scanAlgo['message'])
               print('\n')
            else:
                if self.gantry == "PPlus":
                    index_beam = np.where(np.array(gantry_angles)==gantry_angle)[0][0]
                    plan = self.parsePPlusResponse(plan, scanAlgo, index_beam)
                elif self.gantry == "POne":
                    index_beam = np.where(np.array(gantry_angles)==gantry_angle)[0][0]
                    plan = self.parsePOneResponse(plan, scanAlgo, index_beam)
                else:
                    raise Exception(f'Unknown gantry type {self.gantry}')

        return plan


    def parsePPlusResponse(self, plan, scanAlgo, index_beam):
        """
        Parse response from ScanAlgo for PPlus gantry + reorder spots according to spot timings

        Parameters
        ----------
        plan: RTPlan
            original plan
        scanAlgo: dict
            output from scanAlgo
        index_beam: int
            index number of the beam in plan._beams

        Returns
        -------
        plan:RTPlan
            updated plan with timings
        """
        assert len(plan._beams[index_beam]._layers) == len(scanAlgo['layer'])
        for l in range(len(plan._beams[index_beam]._layers)):
            # identify current spot in layer
            original_layer = plan._beams[index_beam]._layers[l]
            SA_layer = scanAlgo['layer'][l]['spot']
            N = len(SA_layer)
            conversion_coeff = self.getChargeToMUConversion(original_layer, scanAlgo['layer'][l])
            new_layer = original_layer.copy()
            new_layer._x = np.array([])
            new_layer._y = np.array([])
            new_layer._mu = np.array([])
            new_layer._startTime = np.array([])
            new_layer._irradiationDuration = np.array([])
            SA_x = [SA_layer[i]['clinicalx'] for i in range(N)]
            SA_y = [SA_layer[i]['clinicaly'] for i in range(N)]
            exist, index_spot_original_plan = plan._beams[index_beam]._layers[l].spotDefinedInXY(SA_x, SA_y)
            assert np.all(exist)==True
            c = conversion_coeff[index_spot_original_plan]
            SA_w = [SA_layer[i]['charge'] * c[i] for i in range(N)]
            SA_t = [SA_layer[i]['start'] / 1000 for i in range(N)]
            SA_d = [SA_layer[i]['duration'] / 1000 for i in range(N)]
            new_layer.appendSpot(SA_x, SA_y, SA_w, SA_t, SA_d)

            # Reorder spots according to spot timings
            order = np.argsort(new_layer._startTime)
            new_layer.reorderSpots(order)
            plan._beams[index_beam]._layers[l] = new_layer
        return plan



    def parsePOneResponse(self, plan, scanAlgo, index_beam):
        """
        Parse response from ScanAlgo for POne gantry + reorder spots according to spot timings
        Since there is an intrinsec rescanning for the POne, the plan is modified accordingly, i.e.
            - Spots are added in the plan corresponding to the rescanning
            - SpotMU are weighted according to the dose delivered in each burst
        Timings are computed with postprocessing (i.e. layer time, burst time accumulation)

        Parameters
        ----------
        plan : RTPlan
            The plan for which the timings are computed.
        scanAlgo : dict
            The output from scanAlgo.
        index_beam : int
            index number of the beam in plan._beams

        Returns
        -------
        RTPlan
            The plan with timings.
        """
        assert len(plan._beams[index_beam]._layers) == len(scanAlgo['layers'])
        burst_switching_time = 150
        burst_start_time = 0.
        for l in range(len(plan._beams[index_beam]._layers)):
            assert 'bursts' in scanAlgo['layers'][l]
            original_layer = plan._beams[index_beam]._layers[l]
            SA_burst = scanAlgo['layers'][l]['bursts']

            conversion_coeff = self.getChargeToMUConversion(original_layer, scanAlgo['layers'][l])
            new_layer = original_layer.copy()
            new_layer._x = np.array([])
            new_layer._y = np.array([])
            new_layer._mu = np.array([])
            new_layer._startTime = np.array([])
            new_layer._irradiationDuration = np.array([])

            burst_start_time += float(scanAlgo['layers'][l]["switchingTime"])
            N_bursts = len(SA_burst)
            for b, burst in enumerate(SA_burst):
                N = len(burst['spots'])
                SA_x = np.array([burst['spots'][i]['clinicalX'] for i in range(N)])
                SA_y = np.array([burst['spots'][i]['clinicalY'] for i in range(N)])
                exist, index_spot_original_plan = plan._beams[index_beam]._layers[l].spotDefinedInXY(SA_x, SA_y)
                assert np.all(exist)==True
                c = conversion_coeff[index_spot_original_plan]
                SA_w = np.array([burst['spots'][i]['targetCharge'] * c[i] for i in range(N)])
                SA_t = np.array([burst['spots'][i]['startTime'] for i in range(N)])
                SA_t = (SA_t + burst_start_time) / 1000 # convert to seconds
                SA_d = np.array([burst['spots'][i]['duration'] / 1000 for i in range(N)])
                new_layer.appendSpot(SA_x, SA_y, SA_w, SA_t, SA_d)
                bst = burst_switching_time if b<N_bursts-1 else 0.
                burst_start_time += burst['spots'][-1]['startTime'] + burst['spots'][-1]['duration'] + bst

            # Reorder spots according to spot timings
            order = np.argsort(new_layer._startTime)
            new_layer.reorderSpots(order)
            plan._beams[index_beam]._layers[l] = new_layer
        return plan


    def findSpotIndexJson(self, json_arr, pos_x, pos_y, return_first=True):
        """
        Find index of spot corresposding to position (pos_x,pos_y) in JSON file

        Parameters
        ----------
        json_arr : dict
            The JSON file containing the spots.
        pos_x : float
            The x position of the spot.
        pos_y : float
            The y position of the spot.
        return_first : bool
            If True, return the first index found. If False, return all indices found.
        """
        if self.gantry=="PPlus":
            indices = []
            pos_x_name = 'clinicalx'
            pos_y_name = 'clinicaly'
            for i in range(len(json_arr['spot'])):
                if np.isclose(float(json_arr['spot'][i][pos_x_name]), float(pos_x)) and np.isclose(float(json_arr['spot'][i][pos_y_name]), float(pos_y)):
                    indices.append(i)
        else: # self.gantry=="POne"
            indices = {}
            pos_x_name = 'clinicalX'
            pos_y_name = 'clinicalY'
            for b, burst in enumerate(json_arr['bursts']):
                indices[b] = []
                for s, spot in enumerate(burst['spots']):
                    if np.isclose(float(spot[pos_x_name]), float(pos_x)) and np.isclose(float(spot[pos_y_name]), float(pos_y)):
                        indices[b].append(s)
                        assert len(indices[b])==1

        if len(indices)==0:
            return None
        elif len(indices)==1 or return_first:
            return indices[0]
        else:
            return indices


    def getChargeToMUConversion(self, original_layer, SA_layer):
        """
        ScanAlgo returns a charge delivered for each spot. This function computes the coefficient to go from charges to MU
        for each spot in the original_layer.

        Parameters
        ----------
        original_layer : Layer
            The layer from the plan.
        SA_layer : dict
            The layer from the scanAlgo output.

        Returns
        -------
        float
            The conversion coefficient.
        """
        if self.gantry == 'PPlus':
            conversion_coeff = np.zeros(len(original_layer._x))
            for i in range(len(original_layer._x)):
                index_spot_scanAlgo = self.findSpotIndexJson(SA_layer,
                        original_layer._x[i],
                        original_layer._y[i], return_first=False)
                if isinstance(index_spot_scanAlgo, list):
                    total_charge = sum([SA_layer['spot'][j]['charge'] for j in index_spot_scanAlgo])
                    conversion_coeff[i] = original_layer._mu[i] / total_charge
                else:
                    conversion_coeff[i] = original_layer._mu[i] / (SA_layer['spot'][index_spot_scanAlgo]['charge'])
        elif self.gantry == 'POne':
            conversion_coeff = np.zeros(len(original_layer._x))
            for i in range(len(original_layer._x)):
                index_spot_scanAlgo = self.findSpotIndexJson(SA_layer,
                        original_layer._x[i],
                        original_layer._y[i], return_first=False)
                total_charge = sum([SA_layer['bursts'][b]['spots'][s]['targetCharge'] for b,spot_ind in index_spot_scanAlgo.items() for s in spot_ind])
                conversion_coeff[i] = original_layer._mu[i] / total_charge
        else:
            raise NotImplementedError(f'{self.Gantry} not implemented')

        return conversion_coeff

    def getTimingsAndSavePlan(self, output_path):
        """
        Add timings for each spot in the plan and save the plan.

        Parameters
        ----------
        output_path : str
            The path where the plan will be saved.
        """
        plan_with_timings = self.getPBSTimings(sort_spots="true")
        saveRTPlan(plan_with_timings, output_path)