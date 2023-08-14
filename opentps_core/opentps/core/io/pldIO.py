import os, sys
import numpy as np
import logging
from opentps.core.data.plan._rtPlan import RTPlan
from opentps.core.data.plan._planIonBeam import PlanIonBeam
from opentps.core.data.plan._planIonLayer import PlanIonLayer

logger = logging.getLogger(__name__)

def exportPlanPLD(plan:RTPlan, outputPath:str):
    """
    Export a plan to PLD format

    Parameters
    ----------
    plan:RTPlan
        The RTplan to export
    outputPath:str
        The path to the output file
    """

    plan.simplify(threshold=0.01) # remove MU lower than 0.01 MU
    plan.spotMUs = np.around(plan.spotMUs, 2)

    # Write header file
    logger.info("Write PLD file: " + outputPath)
    with open(outputPath, "w") as fid:
        for beam in plan.beams:
            cumulative_layer_meterset_weight = np.sum([layer.meterset/layer.scalingFactor for layer in beam.layers])
            fid.write(f"Beam,Patient ID,Patient Name,Patient Initial,Patient Firstname,Plan Label,Beam Name,{beam.meterset:.2f},{cumulative_layer_meterset_weight:.2f},{len(beam.layers)}")                  
            fid.write("\n") 
            cumulative_layer_meterset = 0
            for layer in beam.layers:
                cumulative_layer_meterset += layer.meterset / layer.scalingFactor
                fid.write(f'Layer,Spot1,{layer.nominalEnergy:.2f},{cumulative_layer_meterset:.2f},{2*layer.numberOfSpots}') # ,{layer.numberOfPaintings}
                fid.write("\n") 
                for i in range(layer.numberOfSpots):
                    fid.write(f'Element,{layer.spotX[i]:.2f},{layer.spotY[i]:.2f},0.0,0.0')
                    fid.write("\n") 
                    fid.write(f'Element,{layer.spotX[i]:.2f},{layer.spotY[i]:.2f},{layer.spotWeights[i]:.2f},0.0')
                    fid.write("\n")


def importPlanPLD(inputPath:str):
    """
    Import a plan from PLD format

    Parameters
    ----------
    inputPath:str
        The path to the input file

    Returns
    -------
    plan:RTPlan
        The RTplan
    """
    plan = RTPlan()
    with open(inputPath, "r") as fid:
        for line in fid:
            if line.startswith("Beam"):
                values = line.split(",")
                scalingFactor = float(values[-3]) / float(values[-2])
                plan.appendBeam(PlanIonBeam())
                continue
            if line.startswith("Layer"):
                values = line.split(",")
                layer = PlanIonLayer(nominalEnergy=float(values[2]))
                plan.beams[-1].appendLayer(layer)
                continue
            if line.startswith("Element"):
                values = line.split(",")
                if float(values[3])==0:
                    continue
                plan.beams[-1].layers[-1].appendSpot(float(values[1]),float(values[2]),float(values[3])*scalingFactor)
    return plan