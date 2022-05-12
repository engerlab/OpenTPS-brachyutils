# -*- coding: utf-8 -*-
"""
Created on Wed Feb 16 08:43:30 2022

@author: grotsartdehe
"""
import numpy as np 
import matplotlib.pyplot as plt 

#genere des variables suivant une loi de exponentielle
def events(L,Tend):
    timestamp = [0]
    U = np.random.uniform(0,1)
    t1 = -np.log(U)/L
    while t1 <= Tend:
        timestamp.append(t1)
        U = np.random.uniform(0,1)
        t1 += -np.log(U)/L
    return timestamp

#entre deux timestamps successifs, un event est créé
#Un event correspond a une fonction echellon qui est ensuite bruitee
def vectorSimulation(L,diff,mean,sigma,Tend,t,timestamp):
    #timestamp = events(L,Tend)        
    y = np.zeros(len(t))
    i = 0
    while i < len(timestamp):
        if i+2 < len(timestamp):
            a = np.random.uniform(-diff,diff)
            t1 = timestamp[i+1]
            t2 = timestamp[i+2]
            y[(t>=t1) & (t<=t2)] = a
        i+=2
    #noise = np.random.normal(mean,diff/100,len(t))
    #noise = np.random.normal(loc=mean,scale=sigma,size=len(t))  
    #noise = np.ones(len(t))
    #y += noise
    return y



#creation des donnees respiratoires
def signalGeneration(amplitude=10, dA=5, period=4.0, df=0.5, dS=5, mean=0, sigma=1, step=0.2, signalDuration=100, L=2 / 30):
    freq = 1 / period
    timestamps = np.arange(0, signalDuration, step)
    listOfEvents = events(L,signalDuration)
    listOfEventsApnea = events(L,signalDuration)
    
    amplitude += vectorSimulation(L, dA, mean, sigma, signalDuration, timestamps,listOfEvents)
    s = vectorSimulation(L, dS, mean, sigma, signalDuration, timestamps,listOfEvents)
    freq += vectorSimulation(L, df, mean, sigma, signalDuration, timestamps,listOfEvents)
    
    noise = np.random.normal(loc=mean,scale=sigma,size=len(timestamps))
    
    #signal = (amplitude / 2) * np.sin(2 * np.pi * freq * (timestamps % (1 / freq))) + s ## we talk about breathing amplitude in mm so its more the total amplitude than the half one, meaning it must be divided by two here
    signal = (amplitude / 2) * np.sin(2 * np.pi * freq * timestamps) + s 
    
    i = 0
    while i < len(listOfEventsApnea):
        if i+2 < len(listOfEventsApnea):
            index = np.abs(timestamps - listOfEventsApnea[i+1])
            indexApnea = np.argmin(index)
            a = signal[indexApnea]
            t1 = listOfEventsApnea[i+1]
            t2 = listOfEventsApnea[i+2]
            signal[(timestamps>=t1) & (timestamps<=t2)] = a
        i+=2
    signal += noise
    return timestamps * 1000, signal

def signal3DGeneration(amplitude=10, dA=5, period=4.0, df=0.5, dS=5, mean=0, sigma=1, step=0.2, signalDuration=100, L=2 / 30, otherDimensionsRatio = [0.3, 0.4], otherDimensionsNoiseVar = [0.1, 0.05]):

    timestamps, mainMotionSignal = signalGeneration(amplitude=amplitude, dA=dA, period=period, df=df, dS=dS, mean=mean, sigma=sigma, step=step, signalDuration=100, L=2 / 30)

    secondMotionSignal = mainMotionSignal * otherDimensionsRatio[0] + np.random.normal(loc=0, scale=otherDimensionsNoiseVar[0], size=mainMotionSignal.shape[0])
    thirdMotionSignal = mainMotionSignal * otherDimensionsRatio[1] + np.random.normal(loc=0, scale=otherDimensionsNoiseVar[1], size=mainMotionSignal.shape[0])

    signal3D = np.vstack((mainMotionSignal, secondMotionSignal, thirdMotionSignal))
    signal3D = signal3D.transpose(1, 0)

    plt.figure()
    plt.plot(signal3D[:, 0])
    plt.plot(signal3D[:, 1])
    plt.plot(signal3D[:, 2])
    plt.show()

    return timestamps, signal3D

"""
#parametres changeables
amplitude = 10 #amplitude (mm)
dA = 5 #variation d amplitude possible (mm)
period = 4.0 #periode respiratoire (s)
df = 0.5 #variation de frequence possible (Hz)
dS = 5 #shift du signal (mm)
step = 0.2 #periode d echantillonnage
signalDuration = 100 #temps de simulation
L = 2/30 #moyenne des evenements aleatoires

time,samples = signalGeneration()
time = np.arange(0, signalDuration, step)
plt.figure(figsize=(15,10))
plt.plot(time,samples)
plt.xlabel("Time [s]")
plt.ylabel("Amplitude [mm]")
plt.title("Breathing signal part 1")
plt.xlim((0,100))



