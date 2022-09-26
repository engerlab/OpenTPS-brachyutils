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
    def __init__(self, name="Breathing Signal"):
        super().__init__(name=name)
        self.timestamps = None
        self.breathingSignal = None
        #to do


# synthetic breathing data
class SyntheticBreathingSignal(BreathingSignal):
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
        self.timestamps, self.breathingSignal = signalGeneration(self.amplitude, self.breathingPeriod, self.meanNoise, self.varianceNoise, self.samplingPeriod, self.simulationTime, self.coeffMin, self.coeffMax,self.meanEvent, self.meanEventApnea)
        return self.breathingSignal

    def generate2DBreathingSignal(self):
        """
        this can be improved to be a single function with a dimension parameter
        """
        self.timestamps, self.breathingSignal = signal2DGeneration(self.amplitude,self.breathingPeriod, self.meanNoise, self.varianceNoise, self.samplingPeriod, self.simulationTime, self.coeffMin, self.coeffMax,self.meanEvent, self.meanEventApnea)
        return self.breathingSignal

    def generate3DBreathingSignal(self):
        """
                this can be improved to be a single function with a dimension parameter
                """
        self.timestamps, self.breathingSignal = signal3DGeneration(self.amplitude,self.breathingPeriod, self.meanNoise, self.varianceNoise, self.samplingPeriod, self.simulationTime, self.coeffMin, self.coeffMax,self.meanEvent, self.meanEventApnea)
        return self.breathingSignal

    def normalize(self, bound = None):

        if bound is None :
            self.breathingSignal -= np.min(self.breathingSignal)
            self.breathingSignal = self.breathingSignal / np.max(self.breathingSignal)
        else :
            self.breathingSignal = (self.breathingSignal-np.min(self.breathingSignal))/(np.max(self.breathingSignal)-np.min(self.breathingSignal))
            self.breathingSignal = (1-2*bound)*self.breathingSignal + bound
        self.isNormalized = True