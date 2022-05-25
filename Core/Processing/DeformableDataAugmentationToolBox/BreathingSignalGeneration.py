# -*- coding: utf-8 -*-
"""
Created on Wed Feb 16 08:43:30 2022

@author: grotsartdehe
"""
import numpy as np 
import matplotlib.pyplot as plt 

#genere des variables suivant une loi de exponentielle
#Un timestamp correspond le debut ou la fin d un event
def events(L,meanDurationEvents,varianceDurationEvents,Tend):
    timestamp = [0]
    U = np.random.uniform(0,1)
    if L == 0:
        return timestamp
    else:
        t1 = -np.log(U)/L
        while t1 <= Tend:
            timeEvents = np.random.normal(meanDurationEvents,varianceDurationEvents)
            timestamp.append(t1)
            t1 += timeEvents
            if t1 <= Tend:
                timestamp.append(t1)
            U = np.random.uniform(0,1)
            t1 += -np.log(U)/L
        return timestamp

#entre deux timestamps successifs, un event est cree
#Un event correspond a une fonction echellon 
def vectorSimulation(diff,timestamps,listOfEvents): 
    t = timestamps      
    y = np.zeros(len(t))
    i = 0
    while i < len(listOfEvents):
        if i+2 < len(listOfEvents):
            value = np.random.uniform(-diff,diff)
            t1 = listOfEvents[i+1]
            t2 = listOfEvents[i+2]
            y[(t>=t1) & (t<=t2)] = value
        i+=2
    return y

#creation des donnees respiratoires
def signalGeneration(amplitude=20, period=4.0, mean=0, sigma=3, step=0.5, signalDuration=100, coeffMin = 0.10, coeffMax = 0.45, meanEvent = 1/20, meanEventApnea=1/120):
    amp = amplitude
    freq = 1 / period
    dA = np.random.uniform(coeffMin,coeffMax)*amp #amplitude variation
    df = np.abs(freq-(period+np.random.uniform(coeffMin,coeffMax))**-1) #frequency variation
    timestamps = np.arange(0,signalDuration,step)
    #creation des events
    #s il y a un changement d amplitude, alors il y a un changement de frequence
    meanDurationEvents = 10
    varianceDurationEvents = 5
    meanDurationEventsApnea = 15
    varianceDurationEventsApnea = 5
    listOfEvents = events(meanEvent,meanDurationEvents,varianceDurationEvents,signalDuration)
    listOfEventsApnea = events(meanEventApnea,meanDurationEventsApnea,varianceDurationEventsApnea,signalDuration)
   
    
    amplitude += vectorSimulation(dA,timestamps,listOfEvents)
    freq += vectorSimulation(df,timestamps,listOfEvents)
    noise = np.random.normal(loc=mean,scale=sigma,size=len(timestamps))
    
    signal = (amplitude / 2) * np.sin(2 * np.pi * freq * (timestamps % (1 / freq))) ## we talk about breathing amplitude in mm so its more the total amplitude than the half one, meaning it must be divided by two here
    signal += noise
    
    #pour chaque event, la valeur min de tout le signal doit rester identique, meme s il y a un changement
    #d amplitude 
    i = 0
    while i < len(listOfEvents):
        if i+2 < len(listOfEvents):
            t1 = listOfEvents[i+1]
            t2 = listOfEvents[i+2]
            newAmplitude = amplitude[int(((t1+t2)/2)/step)]
            signal[(timestamps>=t1) & (timestamps<=t2)] += (-amp/2+newAmplitude/2) 
        i+= 2
    
    #pendant une apnea, le signal respiratoire ne varie quasi pas
    timeApnea = []
    i = 0
    while i < len(listOfEventsApnea):
        if i+2 < len(listOfEventsApnea):
            index = np.abs(timestamps - listOfEventsApnea[i+1])
            indexApnea = np.argmin(index)
            a = signal[indexApnea]
            if a < 0 and a < -0.8*amp/2:
                t1 = listOfEventsApnea[i+1]
            else:
                newIndexApnea = indexApnea + np.argmin(signal[indexApnea:int(indexApnea+period//step)]) #+ np.random.randint(-int(period/(2*step)),0)
                t1 = timestamps[newIndexApnea]
                a = signal[newIndexApnea]
                
            t2 = listOfEventsApnea[i+2]
            diff_i = np.argmin(np.abs(timestamps-t2))-np.argmin(np.abs(timestamps-t1))
            timeDec = np.arange(0,t2-t1,step)[0:diff_i]
            noiseApnea = np.random.normal(loc=0,scale=sigma/5,size=len(timeDec))
            signal[np.argmin(np.abs(timestamps-t1)):np.argmin(np.abs(timestamps-t2))] = -timeDec/(t2-t1)+a + noiseApnea
            timeApnea.append(np.argmin(np.abs(timestamps-t2)))
        i+=2
    
    #apres une apnee, le signal a une amplitude plus grande car le patient doit reprendre son souffle
    for timeIndex in timeApnea:
        timeAfterApnea = np.arange(0,np.random.normal(15,5),step)
        cst = np.random.uniform(1.4,2.0)
        ampSig = cst*(amp/2)
        noiseSig = np.random.normal(loc=mean,scale=sigma,size=len(timeAfterApnea))
        sig = ampSig*np.sin(2*np.pi*timeAfterApnea/period)+ (ampSig-amp/2) + noiseSig
        if timeIndex+len(timeAfterApnea) < len(signal):
            signal[timeIndex:timeIndex+len(timeAfterApnea)] = sig[:]
        else:
            signal[timeIndex::] = sig[0:len(signal)-timeIndex]
        
    
    return timestamps * 1000, signal


def signal3DGeneration(amplitude=20, period=4.0, mean=0, sigma=3, step=0.5, signalDuration=100, coeffMin = 0.10, coeffMax = 0.45, meanEvent = 1/20, meanEventApnea=1/120, otherDimensionsRatio = [0.3, 0.4], otherDimensionsNoiseVar = [0.1, 0.05]):

    timestamps, mainMotionSignal = signalGeneration(amplitude=20, period=4.0, mean=0, sigma=3, step=0.5, signalDuration=100, coeffMin = 0.10, coeffMax = 0.45, meanEvent = 1/20, meanEventApnea=1/120)

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




# for i in range(10):
#     time,samples,amplitude = signalGeneration()
#     time = np.arange(0,100,0.5)
#     plt.figure(figsize=(15,10))
#     plt.plot(time,samples)
#     plt.plot(time,amplitude)
#     plt.xlabel("Time [s]")
#     plt.ylabel("Amplitude [mm]")
#     plt.title("Breathing signal part 1")
#     #plt.xlim((0,100))
#     plt.ylim((-30,30))


