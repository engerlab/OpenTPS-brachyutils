# -*- coding: utf-8 -*-
"""
Created on Wed Feb 23 09:09:09 2022

@author: grotsartdehe
"""
from Core.Data.patientData import PatientData
from Core.Processing.BreathingSignalGeneration import signal

#synthetic breathing data 
class SyntheticBreathingSignal(PatientData):
    def __init__(self,amplitude,variationAmplitude,breathingPeriod,variationFrequency,shift,mean,variance,samplingPeriod,simulationTime,meanEvent):
        super().__init__()
        
        self.amplitude = amplitude #amplitude (mm)
        self.variationAmplitude = variationAmplitude #variation d amplitude possible (mm)
        self.breathingPeriod = breathingPeriod #periode respiratoire (s)
        self.variationFrequency = variationFrequency #variation de frequence possible (Hz)
        self.shift = shift #shift du signal (mm)
        self.mean = mean
        self.variance = variance
        self.samplingPeriod = samplingPeriod #periode d echantillonnage
        self.simulationTime = simulationTime #temps de simulation
        self.meanEvent = meanEvent #moyenne des evenements aleatoires
        self.timestamps = None
        self.breathingSignal = None 
        
    #return timestamps and the corresponding breathing data
    def generateBreathingSignal(self):
        self.timestamps, self.breathingSignal = signal(self.amplitude,self.variationAmplitude,self.breathingPeriod,self.variationFrequency,self.shift,self.mean,self.variance,self.samplingPeriod,self.simulationTime,self.meanEvent)
        return self.breathingSignal

#real breathing data 
class BreathingSignal(PatientData):
    def __init__(self):
        super().__init__()
        #to do