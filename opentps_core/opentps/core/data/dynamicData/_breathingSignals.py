# -*- coding: utf-8 -*-
"""
Created on Wed Feb 23 09:09:09 2022

@author: grotsartdehe
"""
import numpy as np
from opentps.core.data._patientData import PatientData
from opentps.core.processing.deformableDataAugmentationToolBox.BreathingSignalGeneration import signalGeneration, signal2DGeneration, signal3DGeneration


#real breathing data 
class BreathingSignal(PatientData):
    """
    Breathing signal class. Inherits from PatientData.

    Attributes
    ----------
    name : str (default = "Breathing Signal")
        Name of the breathing signal.
    timestamps : array_like
        Timestamps of the breathing signal.
    breathingSignal : array_like
        Breathing signal.
    """
    def __init__(self, name="Breathing Signal"):
        super().__init__(name=name)
        self.timestamps = None
        self.breathingSignal = None
        # TODO


# synthetic breathing data
class SyntheticBreathingSignal(BreathingSignal):

    """
    Synthetic breathing signal class. Inherits from BreathingSignal.

    Attributes
    ----------
    amplitude : float (default = 10)
        Amplitude of the breathing signal.
    breathingPeriod : float (default = 4)
        Breathing period.
    meanNoise : float (default = 0)
        Mean of the noise.
    varianceNoise : float (default = 1)
        Variance of the noise.
    samplingPeriod : float (default = 0.2)
        Sampling period.
    simulationTime : float (default = 100)
        Simulation time.
    coeffMin : float (default = 0.10)
        Minimal coefficient for the change of amplitude.
    coeffMax : float (default = 0.15)
        Maximal coefficient for the change of amplitude.
    meanEvent : float (default = 1/60)
        Mean number of events.
    meanEventApnea : float (default = 0/120)
        Mean number of apnea events.
    isNormalized : bool (default = False)
        Boolean indicating if the breathing signal is normalized.
    """
    def __init__(self, amplitude=10, breathingPeriod=4, meanNoise=0,
                 varianceNoise=1, samplingPeriod=0.2, simulationTime=100, coeffMin = 0.10, coeffMax = 0.15, meanEvent = 1/60, meanEventApnea=0/120, name="Breathing Signal"):
        super().__init__(name=name)

        self.amplitude = amplitude  # amplitude (mm)
        self.breathingPeriod = breathingPeriod  # periode respiratoire (s)
        self.meanNoise = meanNoise
        self.varianceNoise = varianceNoise
        self.samplingPeriod = samplingPeriod  # periode d echantillonnage
        self.simulationTime = simulationTime  # temps de simulation
        self.coeffMin = coeffMin #coefficient minimal pour le changement d amplitude
        self.coeffMax = coeffMax #coefficient maximal pour le changement d amplitude
        self.meanEvent = meanEvent #nombre moyen d evenements
        self.meanEventApnea = meanEventApnea #nombre moyen d apnees
        self.isNormalized = False


    def generate1DBreathingSignal(self):
        """
        Generate a 1D breathing signal based on the attributes of the synthetic breathing signal object.
        Update the timestamps and breathingSignal attributes.

        Returns
        -------
        breathingSignal : array_like
            1D breathing signal.
        """
        self.timestamps, self.breathingSignal = signalGeneration(self.amplitude, self.breathingPeriod, self.meanNoise, self.varianceNoise, self.samplingPeriod, self.simulationTime, self.coeffMin, self.coeffMax,self.meanEvent, self.meanEventApnea)
        return self.breathingSignal

    def generate2DBreathingSignal(self):
        """
        Generate a 2D breathing signal based on the attributes of the synthetic breathing signal object.
        Update the timestamps and breathingSignal attributes.

        Returns
        -------
        breathingSignal : array_like
            2D breathing signal.
        """
        # this can be improved to be a single function with a dimension parameter
        self.timestamps, self.breathingSignal = signal2DGeneration(self.amplitude,self.breathingPeriod, self.meanNoise, self.varianceNoise, self.samplingPeriod, self.simulationTime, self.coeffMin, self.coeffMax,self.meanEvent, self.meanEventApnea)
        return self.breathingSignal

    def generate3DBreathingSignal(self):
        """
        Generate a 3D breathing signal based on the attributes of the synthetic breathing signal object.
        Update the timestamps and breathingSignal attributes.

        Returns
        -------
        breathingSignal : array_like
            3D breathing signal.
        """
        # this can be improved to be a single function with a dimension parameter
        self.timestamps, self.breathingSignal = signal3DGeneration(self.amplitude,self.breathingPeriod, self.meanNoise, self.varianceNoise, self.samplingPeriod, self.simulationTime, self.coeffMin, self.coeffMax,self.meanEvent, self.meanEventApnea)
        return self.breathingSignal

    def normalize(self, bound = None):
        """
        Normalize the breathing signal. If bound is None, the breathing signal is normalized between 0 and 1. Else, the breathing signal is normalized between -bound and bound.
        Change the isNormalized attribute to True.
        """

        if bound is None :
            self.breathingSignal -= np.min(self.breathingSignal)
            self.breathingSignal = self.breathingSignal / np.max(self.breathingSignal)
        else :
            self.breathingSignal = (self.breathingSignal-np.min(self.breathingSignal))/(np.max(self.breathingSignal)-np.min(self.breathingSignal))
            self.breathingSignal = (1-2*bound)*self.breathingSignal + bound
        self.isNormalized = True