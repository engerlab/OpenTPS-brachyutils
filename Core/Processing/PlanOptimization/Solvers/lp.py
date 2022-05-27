import logging

logger = logging.getLogger(__name__)
try:
    import gurobipy as gp
    from gurobipy import GRB
except:
    logger.exception('No module Gurobi found')
import numpy as np
import json
from random import randint, choice
from Core.Data.Plan.rtPlan import RTPlan
from Core.Processing.PlanOptimization.tools import WeightStructure


class LP:
    def __init__(self, plan: RTPlan, **kwargs):
        self.plan = plan
        self.model = None
        self.solStruct = WeightStructure(plan)
        self.xVars = None
        params = kwargs
        # LNS
        self.LNSNIter = params.get('LNS_n_iter', 0)
        self.LNSPercentLayers = params.get('LNS_percent_layers', -1)
        self.completeAfterLNS = params.get('complete_after_LNS', self.LNSNIter < 1)
        self.LNSPercentLayersInc = params.get('LNS_percent_layers_inc', 0)
        # Spot grouping
        self.groupSpotsInit = params.get('group_spots_init', 0)
        self.groupSpotsIter = params.get('group_spots_iter', 0)
        self.completeAfterGroup = params.get('complete_after_group', self.groupSpotsIter < 1)
        self.groupSpots = self.groupSpotsInit > 0

        self.M = params.get('max_spot_MU', 20)
        self.timeLimit = params.get('time_limit', 300)

        assert self.LNSNIter == 0 or self.LNSPercentLayers > 0, ""
        if self.groupSpotsIter > 0:
            assert self.groupSpotsInit % self.groupSpotsIter == 0, "If you want to use spot grouping method, you must " \
                                                                   "provide values where group_spots_init % " \
                                                                   "group_spots_iter == 0 "

    def solve(self, func, x0, **kwargs):
        param = kwargs
        inputf = param.get('inputf', None)
        outputf = param.get('outputf', None)
        solFile = param.get('solFile', None)
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

            self.createModel()
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

                        for el in layers:
                            elActivated = self.solStruct.isActivated(el)
                            if elActivated:
                                activeLayerBeamID.append(el.beamID)
                                activeLayerID.append(el.id)
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
                    if inputf is not None:
                        self.model.update()
                        self.model.read(inputf)
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

                        if solFile is not None:
                            self.model.write(solFile + str(i) + '_group_' + str(int(n)) + '.sol')

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

                        # print("recompute cost : {}".format(self.sol.getCost()))
                        if outputf is not None:
                            jOut = {"optimal": (status == GRB.OPTIMAL and (
                                    self.LNSPercentLayers >= 100 or self.LNSNIter == 0)), "solution": self.solStruct.x}
                            with open(outputf, 'w') as f:
                                json.dump(jOut, f)
                            print("--> Solution written to output file")

            except gp.GurobiError as e:
                print('Error code ' + str(e.errno) + ': ' + str(e))

            except AttributeError:
                print('Encountered an attribute error')
            g += 1

    def createModel(self):
        self.model = gp.Model("LP")
        self.model.ModelSense = GRB.MINIMIZE
        if self.groupSpots:
            logger.info("number of spots grouped = ", self.solStruct.nSpotsGrouped)
            self.xVars = self.model.addMVar(shape=(self.solStruct.nSpotsGrouped,), lb=0.0, ub=self.M,
                                            vtype=GRB.CONTINUOUS,
                                            name='x')
        else:
            self.xVars = self.model.addMVar(shape=(self.plan.numberOfSpots,), lb=0.0, ub=self.M, vtype=GRB.CONTINUOUS,
                                            name='x')

        if self.groupSpots:
            N = self.solStruct.nSpotsGrouped
        else:
            N = self.plan.numberOfSpots
        fidelity = self.model.addMVar(1, name='fidelity')
        for objective in self.plan.objectives.fidObjList:
            M = len(np.nonzero(objective.Mask_vec)[0].tolist())
            print("ROI Name: {}, NNZ voxels= {}".format(objective.ROIName, M))
            nnz = np.nonzero(objective.Mask_vec)[0].tolist()

            if self.groupSpots:
                beamlets = self.solStruct.sparseMatrixGrouped[nnz, ]
            else:
                beamlets = self.solStruct.beamletMatrix[nnz, ]
            dose = beamlets @ self.xVars
            p = np.ones((len(nnz),)) * objective.limitValue
            if objective.metric == "Dmax" and objective.condition == "<":
                if objective.Type == "Soft":
                    vmax = self.model.addMVar(M, lb=0, name=objective.roiName.replace(" ", "_") + '_maxObj')
                    self.model.addConstr((vmax >= dose - p), name=objective.roiName.replace(" ", "_") + "_maxConstr")
                    fidelity += vmax.sum() * (objective.weight / M)
                else:
                    self.model.addConstr(dose <= p, name=objective.roiName.replace(" ", "_") + "_maxConstr")

            elif objective.metric == "Dmin" and objective.condition == ">":
                if objective.type == "Soft":
                    vmin = self.model.addMVar(M, lb=0, name=objective.roiName.replace(" ", "_") + '_minObj')
                    self.model.addConstr((vmin >= p - dose), name=objective.roiName.replace(" ", "_") + "_minConstr")
                    fidelity += vmin.sum() * (objective.weight / M)
                else:
                    self.model.addConstr(dose >= p, name=objective.roiName.replace(" ", "_") + "_minConstr")
            elif objective.metric == "Dmean" and objective.condition == "<":
                vmean = self.model.addMVar((1,), lb=0, name=objective.roiName.replace(" ", "_") + '_meanObj')
                aux = self.model.addMVar(M, name=objective.roiName.replace(" ", "_") + '_aux')
                self.model.addConstr(aux == dose, name=objective.roiName.replace(" ", "_") + "_auxConstr")
                self.model.addConstr((vmean >= (aux.sum() / M) - objective.limitValue),
                                     name=objective.ROIName.replace(" ", "_") + "_meanConstr")
                fidelity += vmean * objective.weight
