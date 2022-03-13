# -*- coding: utf-8 -*-
"""
Created on Wed Feb 23 09:09:09 2022

@author: grotsartdehe
"""
from Core.Data.patientData import PatientData
from Core.Processing.DeformableDataAugmentationToolBox.BreathingSignalGeneration import signalGeneration


#real breathing data 
class BreathingSignal(PatientData):
    def __init__(self, name="Breathing Signal", patientInfo=None):
        super().__init__(patientInfo=patientInfo, name=name)
        self.timestamps = None
        self.breathingSignal = None
        #to do


# synthetic breathing data
class SyntheticBreathingSignal(BreathingSignal):
    def __init__(self, amplitude=10, variationAmplitude=5, breathingPeriod=4, variationFrequency=0.5, shift=5, mean=0,
                 variance=0.1, samplingPeriod=0.2, simulationTime=100, meanEvent=2 / 30, patientInfo=None, name="Breathing Signal"):
        super().__init__(patientInfo=patientInfo, name=name)

        self.amplitude = amplitude  # amplitude (mm)
        self.variationAmplitude = variationAmplitude  # variation d amplitude possible (mm)
        self.breathingPeriod = breathingPeriod  # periode respiratoire (s)
        self.variationFrequency = variationFrequency  # variation de frequence possible (Hz)
        self.shift = shift  # shift du signal (mm)
        self.mean = mean
        self.variance = variance
        self.samplingPeriod = samplingPeriod  # periode d echantillonnage
        self.simulationTime = simulationTime  # temps de simulation
        self.meanEvent = meanEvent  # moyenne des evenements aleatoires


    def generateBreathingSignal(self):
        self.timestamps, self.breathingSignal = signalGeneration(self.amplitude, self.variationAmplitude, self.breathingPeriod,
                                                                 self.variationFrequency, self.shift, self.mean, self.variance,
                                                                 self.samplingPeriod, self.simulationTime, self.meanEvent)
        return self.breathingSignal