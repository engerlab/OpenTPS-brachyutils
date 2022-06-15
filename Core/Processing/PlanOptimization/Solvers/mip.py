import time

from Core.Processing.PlanOptimization.Solvers.lp import LP

import logging
import json

logger = logging.getLogger(__name__)
try:
    import gurobipy as gp
    from gurobipy import GRB
except ModuleNotFoundError:
    logger.info('No module Gurobi found\n!Licence required!\nGet free Academic license on '
                'https://www.gurobi.com/academia/academic-program-and-licenses/ ')
import numpy as np
from random import choice


class MIP(LP):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        params = kwargs
        # constraints
        self.maxSwitchUp = params.get('max_switch_ups', -1)
        # objectives
        self.noELCost = params.get('EL_cost', 'nocost') == 'nocost'
        self.machine = params.get('EL_cost', 'nocost') == "machine"
        self.timeWeight = params.get('ES_up_weight', -1)


        if self.noELCost: print("Warning: EL switch costs are taken into account")

    def createMIPModel(self):
        self.model = super().createModel()
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
                eID = np.ones((self.solStruct.nLayers + 2, self.solStruct.nLayers + 2), dtype=np.int) * (-1)
                for i in range(len(ESCost)):
                    for j in range(len(ESCost[i])):
                        if ESCost[i][j] >= 0:
                            assert i == sourceID or j == sinkID or self.plan.layers[i].beamID < self.plan.layers[
                                j].beamID, "{},{}".format(i, j)
                            eRaw.append(self.model.addVar(lb=0.0, ub=1.0, obj=0.0, vtype=GRB.BINARY,
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
                self.model.addConstr(incoming == outgoing, 'EL_flow_' + str(i))
            self.model.addConstr(outgoingSource == 1, 'EL_source')

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
                        self.model.addConstr(self.xVars[spot.id] <= incoming * self.M,
                                             "x_" + str(spot.id) + "_leq_e_" + str(i) + "xM")
                else:
                    for spot in self.plan.layers[i].spots:
                        self.model.addConstr(self.xVars[spot.id] <= incoming * self.M,
                                             "x_" + str(spot.id) + "_leq_e_" + str(i) + "xM")

            if self.maxSwitchUp >= 0:
                self.model.addConstr(pathCost <= self.maxSwitchUp, "ES_fixed_switch_ups")
            else:
                # self.model.setObjectiveN(path_cost, 1, 1, self.ESWeight, 0, 0, "minimize EL path cost")
                self.model.setObjectiveN(pathCost, 1, 0, self.timeWeight, 0, 0, "EL path cost")

    def solve(self, func, x0, **kwargs):
        startTime = time.time()
        self.solStruct.x = x0
        g = 1
        for n in np.linspace(self.groupSpotsInit, 0, self.groupSpotsIter + 1):
            if self.groupSpotsIter > 0 and g <= self.groupSpotsIter:
                logger.info("######################################### Group Iteration ", g)
                logger.info("----------- Optimizing grouping spots by {}".format(int(n)))
                self.solStruct.groupSpots(int(n))
                layers = self.solStruct.layersGrouped
                x = self.solStruct.xGrouped
                nSpots = self.solStruct.nSpotsGrouped

                # else:
            if (g > self.groupSpotsIter > 0) or self.groupSpotsIter == 0:
                print("########################################### Grouping done ! Complete OPTIMIZATION starts ")
                self.groupSpots = False
                layers = self.plan.layers
                x = self.solStruct.x
                nSpots = self.solStruct.nSpots

            self.createMIPModel()
            if n == 0:
                self.model.setParam('TimeLimit', self.timeLimit)
            else:
                self.model.setParam('TimeLimit', 1800 * g)

            # Tune your own parameters here
            # self.model.setParam('MIPGapAbs', 1e-2)
            # use barrier for the MIP root relaxation
            # self.model.setParam('Method', 2)
            # Limits the number of passes performed by presolve
            # self.model.setParam('PrePasses', 1)
            # Limits the amount of time spent in the NoRel heuristic before solving the root relaxation
            # self.model.setParam('NoRelHeurTime', 100)
            # find feasible solutions quickly
            # self.model.setParam('MIPFocus', 1)
            # self.model.setParam('Cuts', 0)
            # avoid multiple 'Total elapsed time' messages in the log immediately after the root relaxation log
            # self.model.setParam('DegenMoves', 0)
            # barrier only
            # self.model.setParam('CrossoverBasis', 0)
            # self.model.setParam('LogFile', "brain_mipfocus1.log")
            # self.model.write("brain_small.lp")
            # self.model.setParam('SolFiles', '/home/sophie/opentps/MCO/solutions/sol')

            try:
                addedConstraints = []
                nIter = self.LNSNIter
                if self.completeAfterLNS:
                    nIter += 1
                for i in range(1, nIter + 1):
                    for constr in addedConstraints:
                        self.model.remove(constr)
                    addedConstraints.clear()

                    if self.LNSNIter > 0 and i <= self.LNSNIter:
                        print("######################################### LNS Iteration ", i)
                        print("----------- LNS optimizing on {} % layers".format(self.LNSPercentLayers))
                        self.LNSPercentLayers += self.LNSPercentLayersInc
                        activeLayerBeamID = []
                        activeLayerID = []

                        for layerId, el in enumerate(layers):
                            elActivated = self.solStruct.isActivated(el)
                            if elActivated:
                                activeLayerBeamID.append(el.beamID)
                                activeLayerID.append(layerId)
                        randomLayerSelected = []
                        for b in self.plan.beams:
                            if b.id not in activeLayerBeamID:
                                randomLayerSelected.append(choice(b.layersIndices))

                        for el in layers:
                            elActivated = self.solStruct.isActivated(el)
                            # Select randomly layers to optimize
                            # if elActivated or randint(0,999) <= (self.LNS_percent_layers*10):
                            # Smarter way to obtain 1 layer for each beam angle
                            if elActivated or (el.id in randomLayerSelected):
                                if elActivated:
                                    itm = "* "
                                else:
                                    itm = " "
                                print("{}{}".format(el.id, itm), end=" ")
                            else:
                                for spotID in el.spotIndices:
                                    addedConstraints.append(self.model.addConstr(self.xVars[spotID] == x[spotID],
                                                                                 "fixed_spot_" + str(spotID)))
                        print("\n-----------")

                    if i > self.LNSNIter > 0:
                        print("########################################### LNS done ! Complete OPTIMIZATION starts ")

                    # set initial solution
                    if self.inputf is not None:
                        self.model.update()
                        self.model.read(self.inputf)
                    else:
                        if self.groupSpots:
                            self.solStruct.groupSol()
                            print("Re-grouped last solution size =", len(self.solStruct.xGrouped))
                            for k in range(self.solStruct.nSpots):
                                self.xVars[k].Start = self.solStruct.xGrouped[k]
                        else:
                            for k in range(self.solStruct.nSpots):
                                self.xVars[k].Start = self.solStruct.x[k]
                    # optimize
                    self.model.optimize()
                    # self.model.optimize(mycallback)
                    status = self.model.Status
                    if status not in (GRB.INF_OR_UNBD, GRB.INFEASIBLE, GRB.UNBOUNDED):
                        if status == GRB.OPTIMAL:
                            print("OPTIMAL SOLUTION FOUND")
                        else:
                            print("Time limit reached !")

                        print('Obj : {}'.format(self.model.objVal))
                        for o, objective in enumerate(self.plan.objectives.list):
                            if objective.Type == "Soft":
                                names_to_retrieve = []
                                M = len(np.nonzero(objective.Mask_vec)[0].tolist())
                                if objective.Metric == "Dmax" and objective.Condition == "<":
                                    name = objective.ROIName.replace(" ", "_") + '_maxObj'
                                    names_to_retrieve = (f"{name}[{i}]" for i in range(M))
                                    vars_obj = [self.model.getVarByName(name).X for name in names_to_retrieve]
                                    print(
                                        " Objective #{}: ROI Name: {}, Objective value = {}, obj v * weight = {} ".format(
                                            o, name, sum(vars_obj), sum(vars_obj) * objective.Weight / M))
                                elif objective.Metric == "Dmin" and objective.Condition == ">":
                                    name = objective.ROIName.replace(" ", "_") + '_minObj'
                                    names_to_retrieve = (f"{name}[{i}]" for i in range(M))
                                    vars_obj = [self.model.getVarByName(name).X for name in names_to_retrieve]
                                    print(
                                        " Objective #{}: ROI Name: {}, Objective value = {}, obj v * weight = {} ".format(
                                            o, name, sum(vars_obj), sum(vars_obj) * objective.Weight / M))
                                elif objective.Metric == "Dmean" and objective.Condition == "<":
                                    name = objective.ROIName.replace(" ", "_") + '_meanObj[0]'
                                    var_obj = self.model.getVarByName(name).X
                                    print(
                                        " Objective #{}: ROI Name: {}, Objective value = {}, obj v * weight = {} ".format(
                                            o, name, var_obj, var_obj * objective.Weight))

                        if self.solFile is not None:
                            self.model.write(self.solFile + str(i) + '_group_' + str(int(n)) + '.sol')

                        # update solution
                        if self.groupSpots:
                            for j in range(self.solStruct.nSpotsGrouped):
                                self.solStruct.xGrouped[j] = self.xVars[j].X
                                # print(" Grouped Spot {}, value = {}".format(j, self.sol.x_grouped[j]))
                        else:

                            for j in range(self.solStruct.nSpots):
                                self.solStruct.x[j] = self.xVars[j].X

                        x_ungrouped = np.zeros(self.solStruct.nSpots, dtype=np.float32)
                        # ungroup solution

                        if self.groupSpots:
                            for s in range(self.solStruct.nSpots):
                                idx = self.solStruct.spotNewID[s]
                                x_ungrouped[s] = self.solStruct.xGrouped[idx]
                            self.solStruct.loadSolution(x_ungrouped)

                        result = {'sol': self.solStruct.x, 'crit': status, 'niter': None,
                                  'time': time.time() - startTime, 'objective': self.model.objVal}
            except gp.GurobiError as e:
                print('Error code ' + str(e.errno) + ': ' + str(e))

            except AttributeError:
                print('Encountered an attribute error')
            g += 1
            return result
