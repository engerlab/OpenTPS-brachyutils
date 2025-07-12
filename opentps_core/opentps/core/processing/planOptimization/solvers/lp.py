import logging

logger = logging.getLogger(__name__)
try:
    import gurobipy as gp
    from gurobipy import GRB
except ModuleNotFoundError:
    logger.warning("Ignore the following warning if not using Gurobi linear optimizer. Gurobi not required for most features provided in OpenTPS")
    logger.warning('No module Gurobi found\n!Licence required!\nGet free Academic license on '
                'https://www.gurobi.com/academia/academic-program-and-licenses/ ')
    gp = None
import numpy as np
import time
from random import choice
from opentps.core.data.plan._rtPlan import RTPlan
from opentps.core.data.plan import FidObjective
from opentps.core.processing.planOptimization.tools import WeightStructure


class LP:
    """
    LP is a wrapper for the Gurobi linear optimizer.

    Attributes
    ----------
    plan : RTPlan
        The plan to be optimized.
    solStruct : WeightStructure
        The structure of the solution.
    xVars : list
        The list of the variables.
    fidWeight : float (default: 1)
        The weight for the dose fidelity term.
    LNSNIter : int (default: 0)
        The number of LNS iterations.
    LNSPercentLayers : float (default: -1)
        The percentage of layers to be optimized in each LNS iteration.
    completeAfterLNS : bool (default: True)
        If True, the optimization is completed after the LNS iterations.
    LNSPercentLayersInc : float (default: 0)
        The increment of the percentage of layers to be optimized in each LNS iteration.
    groupSpotsInit : int (default: 0)
        The number of spots to be grouped in the first iteration.
    groupSpotsIter : int (default: 0)
        The number of iterations for the spot grouping.
    completeAfterGroup : bool (default: True)
        If True, the optimization is completed after the spot grouping iterations.
    groupSpots : bool (default: False)
        If True, the spots are grouped.
    M : int (default: 20)
        The maximum number of MU per spot.
    timeLimit : int (default: 300)
        The time limit for the optimization.
    inputf : str (default: None)
        The name of the input file.
    solFile : str (default: None)
        The name of the solution file.
    """
    def __init__(self, plan: RTPlan, **kwargs):
        self.plan = plan
        self.solStruct = WeightStructure(plan)
        self.xVars = None

        params = kwargs
        # global weight for dose fidelity term
        self.fidWeight = params.get('Fid_weight', 1)
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

        self.inputf = params.get('inputf', None)
        self.solFile = params.get('solFile', None)

    def solve(self, func, x0, **kwargs):
        """
        Solves the planOptimization problem using the Gurobi linear optimizer.

        Parameters
        ----------
        func : list of functions
            The functions to be optimized.
        x0 : list
            The initial guess.
        kwargs : dict
            The parameters for the Gurobi linear optimizer.

        Returns
        -------
        result : dict
            The result of the planOptimization.
            The keys are:
                sol : list
                    The solution.
                crit : str
                    The termination criterion.
                niter : int
                    The number of iterations.
                time : float
                    The time.
                objective : float
                    The objective function value.
        """
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

            model = self.createModel()

            if n == 0:
                model.setParam('TimeLimit', self.timeLimit)
            else:
                model.setParam('TimeLimit', 1800 * g)

            # Tune your own parameters here
            # model.setParam('MIPGapAbs', 1e-2)
            # use barrier for the MIP root relaxation
            # model.setParam('Method', 2)
            # Limits the number of passes performed by presolve
            # model.setParam('PrePasses', 1)
            # Limits the amount of time spent in the NoRel heuristic before solving the root relaxation
            # model.setParam('NoRelHeurTime', 100)
            # find feasible solutions quickly
            # model.setParam('MIPFocus', 1)
            # model.setParam('Cuts', 0)
            # avoid multiple 'Total elapsed time' messages in the log immediately after the root relaxation log
            # model.setParam('DegenMoves', 0)
            # barrier only
            # model.setParam('CrossoverBasis', 0)
            # model.setParam('LogFile', "brain_mipfocus1.log")
            # model.write("brain_small.lp")
            # model.setParam('SolFiles', '/home/sophie/opentps_core/MCO/solutions/sol')

            try:
                addedConstraints = []
                nIter = self.LNSNIter
                if self.completeAfterLNS:
                    nIter += 1

                for i in range(1, nIter + 1):
                    for constr in addedConstraints:
                        model.remove(constr)
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
                                    addedConstraints.append(model.addConstr(self.xVars[spotID] == x[spotID],
                                                                                 "fixed_spot_" + str(spotID)))
                        print("\n-----------")

                    if i > self.LNSNIter > 0:
                        print("########################################### LNS done ! Complete OPTIMIZATION starts ")

                    # set initial solution
                    if self.inputf is not None:
                        model.update()
                        model.read(self.inputf)
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
                    model.optimize()
                    # model.optimize(mycallback)
                    status = model.Status
                    if status not in (GRB.INF_OR_UNBD, GRB.INFEASIBLE, GRB.UNBOUNDED):
                        if status == GRB.OPTIMAL:
                            print("OPTIMAL SOLUTION FOUND")
                        else:
                            print("Time limit reached !")

                        print('Obj : {}'.format(model.objVal))
                        for o, objective in enumerate(self.plan.planDesign.objectives.fidObjList):
                            if objective.kind == "Soft":
                                names_to_retrieve = []
                                M = len(np.nonzero(objective.maskVec)[0].tolist())
                                if objective.metric == FidObjective.Metrics.DMAX :
                                    name = objective.roiName.replace(" ", "_") + '_maxObj'
                                    names_to_retrieve = (f"{name}[{i}]" for i in range(M))
                                    vars_obj = [model.getVarByName(name).X for name in names_to_retrieve]
                                    print(
                                        " Objective #{}: ROI Name: {}, Objective value = {}, obj v * weight = {} ".format(
                                            o, name, sum(vars_obj), sum(vars_obj) * objective.weight / M))
                                elif objective.metric == FidObjective.Metrics.DMIN :
                                    name = objective.roiName.replace(" ", "_") + '_minObj'
                                    names_to_retrieve = (f"{name}[{i}]" for i in range(M))
                                    vars_obj = [model.getVarByName(name).X for name in names_to_retrieve]
                                    print(
                                        " Objective #{}: ROI Name: {}, Objective value = {}, obj v * weight = {} ".format(
                                            o, name, sum(vars_obj), sum(vars_obj) * objective.weight / M))
                                elif objective.metric == FidObjective.Metrics.DMEAN:
                                    name = objective.roiName.replace(" ", "_") + '_meanObj[0]'
                                    var_obj = model.getVarByName(name).X
                                    print(
                                        " Objective #{}: ROI Name: {}, Objective value = {}, obj v * weight = {} ".format(
                                            o, name, var_obj, var_obj * objective.weight))

                        if self.solFile is not None:
                            model.write(self.solFile + str(i) + '_group_' + str(int(n)) + '.sol')

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

                        result = {'sol': self.solStruct.x, 'crit': status, 'niter': 1,
                                  'time': time.time() - startTime, 'objective': model.objVal}
            except gp.GurobiError as e:
                print('Error code ' + str(e.errno) + ': ' + str(e))

            except AttributeError:
                print('Encountered an attribute error')
            g += 1
            return result

    def createModel(self, name = "LP"):
        """
        Creates the Gurobi model.

        Parameters
        ----------
        name : str (default: "LP")
            The name of the model.

        Returns
        -------
        model : Gurobi model
            The Gurobi model.
        """
        if gp is None:
            raise Exception("Third-party toolbox Gurobi must be installed and requires a license")
        model = gp.Model(name)
        model.ModelSense = GRB.MINIMIZE
        if self.groupSpots:
            logger.info("number of spots grouped = ", self.solStruct.nSpotsGrouped)
            self.xVars = model.addMVar(shape=(int(self.solStruct.nSpotsGrouped),), lb=0.0, ub=self.M,
                                            vtype=GRB.CONTINUOUS,
                                            name='x')
        else:
            self.xVars = model.addMVar(shape=(int(self.plan.numberOfSpots),), lb=0.0, ub=self.M, vtype=GRB.CONTINUOUS,
                                            name='x')

        if self.groupSpots:
            N = self.solStruct.nSpotsGrouped
        else:
            N = self.plan.numberOfSpots
        fidelity = model.addMVar(1, name='fidelity')
        for objective in self.plan.planDesign.objectives.fidObjList:
            M = len(np.nonzero(objective.maskVec)[0].tolist())
            print("ROI Name: {}, NNZ voxels= {}".format(objective.roiName, M))
            nnz = np.nonzero(objective.maskVec)[0].tolist()

            if self.groupSpots:
                beamlets = self.solStruct.sparseMatrixGrouped[nnz,]
            else:
                beamlets = self.solStruct.beamletMatrix[nnz,]
            dose = beamlets @ self.xVars
            p = np.ones((len(nnz),)) * objective.limitValue
            if objective.metric == FidObjective.Metrics.DMAX:
                if objective.kind == "Soft":
                    vmax = model.addMVar(M, lb=0, name=objective.roiName.replace(" ", "_") + '_maxObj')
                    model.addConstr((vmax >= dose - p), name=objective.roiName.replace(" ", "_") + "_maxConstr")
                    fidelity += vmax.sum() * (objective.weight / M)
                else:
                    model.addConstr(dose <= p, name=objective.roiName.replace(" ", "_") + "_maxConstr")

            elif objective.metric == FidObjective.Metrics.DMIN:
                if objective.kind == "Soft":
                    vmin = model.addMVar(M, lb=0, name=objective.roiName.replace(" ", "_") + '_minObj')
                    model.addConstr((vmin >= p - dose), name=objective.roiName.replace(" ", "_") + "_minConstr")
                    fidelity += vmin.sum() * (objective.weight / M)
                else:
                    model.addConstr(dose >= p, name=objective.roiName.replace(" ", "_") + "_minConstr")
            elif objective.metric == FidObjective.Metrics.DMEAN:
                vmean = model.addMVar((1,), lb=0, name=objective.roiName.replace(" ", "_") + '_meanObj')
                aux = model.addMVar(M, name=objective.roiName.replace(" ", "_") + '_aux')
                model.addConstr(aux == dose, name=objective.roiName.replace(" ", "_") + "_auxConstr")
                model.addConstr((vmean >= (aux.sum() / M) - objective.limitValue),
                                     name=objective.roiName.replace(" ", "_") + "_meanConstr")
                fidelity += vmean * objective.weight
            else:
                raise Exception(str(objective.metric) + " objectives are not implemented for the LP method")

        model.setObjective(fidelity)
        #model.setObjectiveN(fidelity, 0, 0, self.fidWeight, 0, 0, "Fidelity cost")
        return model
