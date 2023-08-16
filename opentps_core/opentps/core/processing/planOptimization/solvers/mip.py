from opentps.core.processing.planOptimization.solvers.lp import LP
from opentps.core.data.plan._rtPlan import RTPlan

import logging

logger = logging.getLogger(__name__)
try:
    import gurobipy as gp
    from gurobipy import GRB
except ModuleNotFoundError:
    logger.warning("Ignore the following warning if not using Gurobi linear optimizer. Gurobi not required for most features provided in OpenTPS")
    logger.warning('No module Gurobi found\n!Licence required!\nGet free Academic license on '
                'https://www.gurobi.com/academia/academic-program-and-licenses/ ')
import numpy as np


class MIP(LP):
    """
    Mixed Integer Programming solver for the sequencing problem. The solver is based on the Gurobi solver. Inherit from LP.

    Parameters
    ----------
    plan : RTPlan
        The plan to be optimized
    **kwargs
        Additional parameters for the solver.
        Arguments are:
        - max_switch_ups : int
            Maximum number of energy layer switches. If -1, the number of switches is not limited
        - EL_cost : bool
            If True, the energy layer switch costs are taken into account
        - ES_up_weight : float
            Weight of the energy layer switch costs in the objective function
    max_switch_ups : int (default: -1)
        Maximum number of energy layer switches. If -1, the number of switches is not limited
    no_EL_cost : bool (default: False)
        If True, the energy layer switch costs are not taken into account
    machine : bool (default: False)
        If True, the energy layer switch costs are calculated based on the machine
    time_weight : float (default: -1)
        Weight of the energy layer switch costs in the objective function
    """
    def __init__(self, plan: RTPlan, **kwargs):
        super().__init__(plan, **kwargs)
        params = kwargs
        # constraints
        self.maxSwitchUp = params.get('max_switch_ups', -1)
        # objectives
        self.noELCost = params.get('EL_cost', False)
        self.machine = params.get('EL_cost', False)
        self.timeWeight = params.get('ES_up_weight', -1)


        if self.noELCost: print("Warning: EL switch costs are taken into account")

    def createModel(self, name = "MIP"):
        """
        Create the model for the MIP solver. Inherit from LP.createModel().

        Parameters
        ----------
        name : str (default: "MIP")
            Name of the model

        Returns
        -------
        model : gurobipy.Model
            The model for the MIP solver
        """
        model = super().createModel(name)

        # Energy sequencing
        # Define the digraph for the EL path
        sourceID = self.solStruct.nLayers
        sinkID = self.solStruct.nLayers + 1
        # ESCost[i][j] = cost of switch from EL i to EL j ; cost = -1 if the arc (ij) is not allowed (e.g. i and j on the same beam)
        ESCost = np.ones((self.solStruct.nLayers + 2, self.solStruct.nLayers + 2)) * (-1)
        for el1 in self.plan.layers:
            ESCost[sourceID][el1.id] = 0.0
            ESCost[el1.id][sinkID] = 0.0
            for el2 in self.plan.layers:
                if el2.beamID <= el1.beamID: continue
                # arc with depth > 5 not allowed
                # if el2.beam_id - el1.beam_id > 5: continue
                if self.machine:
                    if el1.nominalEnergy < el2.nominalEnergy:
                        ESCost[el1.id][el2.id] = 6.5
                    elif el1.nominalEnergy > el2.nominalEnergy:
                        ESCost[el1.id][el2.id] = 1.6
                    elif el1.nominalEnergy == el2.nominalEnergy:
                        ESCost[el1.id][el2.id] = 1.2
                elif self.noELCost:
                    ESCost[el1.id][el2.id] = 0.0
                else:
                    ESCost[el1.id][el2.id] = 1.0 * (el1.nominalEnergy < el2.nominalEnergy)
                assert ESCost[el1.id][el2.id] == -1 or ESCost[el1.id][el2.id] >= 0, ""

         # Linear model
        eRaw = []
        eID = np.ones((self.solStruct.nLayers + 2, self.solStruct.nLayers + 2), dtype=int) * (-1)
        for i in range(len(ESCost)):
            for j in range(len(ESCost[i])):
                if ESCost[i][j] >= 0:
                    assert i == sourceID or j == sinkID or self.plan.layers[i].beamID < self.plan.layers[
                        j].beamID, "{},{}".format(i, j)
                    eRaw.append(model.addVar(lb=0.0, ub=1.0, obj=0.0, vtype=GRB.BINARY,
                                                  name="e_" + str(i) + "_" + str(j)))
                    eID[i][j] = len(eRaw) - 1
                else:
                    assert ESCost[i][j] == -1, "{}, {}: {}".format(i, j, ESCost[i][j])

        # Flow
        outgoingSource = gp.LinExpr()
        incomingSink = gp.LinExpr()
        for i in range(len(ESCost)):
            if eID[sourceID][i] >= 0:
                # outgoing_source += e_raw_matrix[eID[sourceID][i]]
                outgoingSource.add(eRaw[eID[sourceID][i]])
            if eID[i][sinkID] >= 0:
                incomingSink.add(eRaw[eID[i][sinkID]])
            if i == sourceID or i == sinkID: continue
            incoming = gp.LinExpr()
            outgoing = gp.LinExpr()
            for j in range(len(ESCost[i])):
                if eID[j][i] >= 0:
                    assert j != sinkID, ''
                    assert j == sourceID or self.plan.layers[j].beamID < self.plan.layers[
                        i].beamID, "{}, {}".format(j, i)
                    assert ESCost[j][i] >= 0 and j != sinkID, "{} , {}: {}".format(j, i, ESCost[j][i])

                    incoming.add(eRaw[eID[j][i]])
                else:
                    assert ESCost[j][i] == -1, "{}, {} : {}".format(j, i, ESCost[j][i])

                if eID[i][j] >= 0:
                    assert j != sourceID, ''
                    assert j == sinkID or self.plan.layers[i].beamID < self.plan.layers[j].beamID, "{}, {}".format(
                        i, j)
                    assert ESCost[i][j] >= 0 and j != sourceID, "{} , {}: {}".format(i, j, ESCost[i][j])

                    outgoing.add(eRaw[eID[i][j]])
                else:
                    assert ESCost[i][j] == -1, "{}, {} : {}".format(i, j, ESCost[i][j])
            model.addConstr(incoming == outgoing, 'EL_flow_' + str(i))
        model.addConstr(outgoingSource == 1, 'EL_source')

        # ES path cost
        pathCost = gp.LinExpr()
        for i in range(len(ESCost)):
            for j in range(len(ESCost[i])):
                if eID[i][j] >= 0:
                    assert ESCost[i][j] >= 0, "{}, {} : {}".format(i, j, ESCost[i][j])
                    assert eID[i][j] < len(eRaw), "{} geq {}".format(eID[i][j], len(eRaw))
                    pathCost.add(eRaw[eID[i][j]] * ESCost[i][j])

        # Link x with e
        for i in range(len(ESCost)):
            if i == sourceID or i == sinkID: continue
            incoming = gp.quicksum(eRaw[eID[j][i]] for j in range(len(ESCost[i])) if eID[j][i] >= 0)
            if self.groupSpots:
                for spot in self.solStruct.layersGrouped[i].spots:
                    model.addConstr(self.xVars[spot.id] <= incoming * self.M,
                                         "x_" + str(spot.id) + "_leq_e_" + str(i) + "xM")
            else:
                for spot in self.plan.layers[i].spots:
                    model.addConstr(self.xVars[spot.id] <= incoming * self.M,
                                         "x_" + str(spot.id) + "_leq_e_" + str(i) + "xM")

        if self.maxSwitchUp >= 0:
            model.addConstr(pathCost <= self.maxSwitchUp, "ES_fixed_switch_ups")
        else:
            # model.setObjectiveN(path_cost, 1, 1, self.ESWeight, 0, 0, "minimize EL path cost")
            model.setObjectiveN(pathCost, 1, 0, self.timeWeight, 0, 0, "EL path cost")
        return model
