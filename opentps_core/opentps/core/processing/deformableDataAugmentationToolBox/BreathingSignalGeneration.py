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
    """
    Generate the timestamps of the events.

    Parameters
    ----------
    L : float
        parameter of the exponential distribution.
    meanDurationEvents : float
        mean duration of the events.
    varianceDurationEvents : float
        variance of the duration of the events.
    Tend : float
        duration of the signal.

    Returns
    -------
    timestamp : list
        list of the timestamps of the events.

    """
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
def vectorSimulation(coeffMin,coeffMax,amplitude,frequency,timestamps,listOfEvents):
    """
    Generate the amplitude and the frequency of the signal.

    Parameters
    ----------
    coeffMin : float
        minimum value of the coefficient of the variation of the amplitude and the frequency.
    coeffMax : float
        maximum value of the coefficient of the variation of the amplitude and the frequency.
    amplitude : float
        amplitude of the signal.
    frequency : float
        frequency of the signal.
    timestamps : array
        timestamps of the signal.
    listOfEvents : list
        list of the timestamps of the events.

    Returns
    -------
    y_amplitude : array
        amplitude of the signal.
    y_frequency : array
        frequency of the signal.
    """
    t = timestamps      
    y_amplitude = np.zeros(len(t))
    y_frequency = np.zeros(len(t))
    i = 0
    while i < len(listOfEvents):
        if i+2 < len(listOfEvents):
            dA = np.random.uniform(coeffMin,coeffMax)*amplitude #amplitude variation
            df = np.abs(frequency-(1/frequency+np.random.uniform(coeffMin,coeffMax))**-1) #frequency variation
            value_amplitude = np.random.uniform(-dA,dA)
            value_frequency = np.random.uniform(-df,df)
            t1 = listOfEvents[i+1]
            t2 = listOfEvents[i+2]
            y_amplitude[(t>=t1) & (t<=t2)] = value_amplitude
            y_frequency[(t>=t1) & (t<=t2)] = value_frequency
        i+=2
    return y_amplitude,y_frequency

#creation des donnees respiratoires
def signalGeneration(amplitude=10, period=4.0, mean=0, sigma=3, step=0.5, signalDuration=100, coeffMin = 0.10, coeffMax = 0.15, meanEvent = 1/20, meanEventApnea=1/120):
    """
    Generate the breathing signal.

    Parameters
    ----------
    amplitude : float
        amplitude of the signal. default is 10.
    period : float
        period of the signal. default is 4.0.
    mean : float
        mean of the noise. default is 0.
    sigma : float
        standard deviation of the noise. default is 3.
    step : float
        step of the timestamps. default is 0.5.
    signalDuration : float
        duration of the signal. default is 100.
    coeffMin : float
        minimum value of the coefficient of the variation of the amplitude and the frequency. default is 0.10.
    coeffMax : float
        maximum value of the coefficient of the variation of the amplitude and the frequency. default is 0.15.
    meanEvent : float
        mean of the duration of the events. default is 1/20.
    meanEventApnea : float
        mean of the duration of the apnea events. default is 1/120.

    Returns
    -------
    timestamps : array
        timestamps of the signal.
    signal : array
        breathing signal.
    """
    amp = amplitude
    freq = 1 / period
    timestamps = np.arange(0,signalDuration,step)
    #creation des events
    #s il y a un changement d amplitude, alors il y a un changement de frequence
    meanDurationEvents = 10
    varianceDurationEvents = 5
    meanDurationEventsApnea = 15
    varianceDurationEventsApnea = 5
    listOfEvents = events(meanEvent,meanDurationEvents,varianceDurationEvents,signalDuration)
    listOfEventsApnea = events(meanEventApnea,meanDurationEventsApnea,varianceDurationEventsApnea,signalDuration)
    sigma *= amp/20
    
    y_amplitude, y_frequency = vectorSimulation(coeffMin,coeffMax,amp,freq,timestamps,listOfEvents)
    amplitude += y_amplitude
    freq += y_frequency
    noise = np.random.normal(loc=mean,scale=sigma,size=len(timestamps))
    phi = np.random.uniform(0,2*np.pi)
    signal = (amplitude / 2) * np.sin(2 * np.pi * freq * (timestamps % (1 / freq))+phi) ## we talk about breathing amplitude in mm so its more the total amplitude than the half one, meaning it must be divided by two here
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
    """
    Generate a 3D breathing signal.

    Parameters
    ----------
    amplitude : float
        amplitude of the breathing signal. default is 20.
    period : float
        period of the breathing signal. default is 4.0.
    mean : float
        mean of the noise. default is 0.
    sigma : float
        standard deviation of the noise. default is 3.
    step : float
        step between two timestamps. default is 0.5.
    signalDuration : float
        duration of the signal. default is 100.
    coeffMin : float
        minimum coefficient of the breathing signal. default is 0.10.
    coeffMax : float
        maximum coefficient of the breathing signal. default is 0.45.
    meanEvent : float
        mean of the event. default is 1/20.
    meanEventApnea : float
        mean of the apnea event. default is 1/120.
    otherDimensionsRatio : list
        list of the ratio of the other dimensions. default is [0.3, 0.4].
    otherDimensionsNoiseVar : list
        list of the noise variance of the other dimensions. default is [0.1, 0.05].

    Returns
    -------
    timestamps : array
        timestamps of the signal.
    signal3D : array
        3D breathing signal.

    """
    timestamps, mainMotionSignal = signalGeneration(amplitude=amplitude, period=period, mean=mean, sigma=sigma, step=step, signalDuration=signalDuration, coeffMin=coeffMin, coeffMax=coeffMax, meanEvent=meanEvent, meanEventApnea=meanEventApnea)

    secondMotionSignal = mainMotionSignal * otherDimensionsRatio[0] + np.random.normal(loc=0, scale=otherDimensionsNoiseVar[0], size=mainMotionSignal.shape[0])
    thirdMotionSignal = mainMotionSignal * otherDimensionsRatio[1] + np.random.normal(loc=0, scale=otherDimensionsNoiseVar[1], size=mainMotionSignal.shape[0])

    signal3D = np.vstack((mainMotionSignal, secondMotionSignal, thirdMotionSignal))
    signal3D = signal3D.transpose(1, 0)

    # plt.figure()
    # plt.plot(signal3D[:, 0])
    # plt.plot(signal3D[:, 1])
    # plt.plot(signal3D[:, 2])
    # plt.show()

    return timestamps, signal3D

def signal2DGeneration(amplitude=20, period=4.0, mean=0, sigma=3, step=0.5, signalDuration=100, coeffMin = 0.10, coeffMax = 0.45, meanEvent = 1/20, meanEventApnea=1/120, otherDimensionsRatio = [0.3, 0.4], otherDimensionsNoiseVar = [0.1, 0.05]):
    """
    Generate a 2D breathing signal.

    Parameters
    ----------
    amplitude : float
        amplitude of the breathing signal. default is 20.
    period : float
        period of the breathing signal. default is 4.0.
    mean : float
        mean of the noise. default is 0.
    sigma : float
        standard deviation of the noise. default is 3.
    step : float
        step between two timestamps. default is 0.5.
    signalDuration : float
        duration of the signal. default is 100.
    coeffMin : float
        minimum coefficient of the breathing signal. default is 0.10.
    coeffMax : float
        maximum coefficient of the breathing signal. default is 0.45.
    meanEvent : float
        mean of the event. default is 1/20.
    meanEventApnea : float
        mean of the apnea event. default is 1/120.
    otherDimensionsRatio : list
        list of the ratio of the other dimensions. default is [0.3, 0.4].
    otherDimensionsNoiseVar : list
        list of the noise variance of the other dimensions. default is [0.1, 0.05].

    Returns
    -------
    timestamps : array
        timestamps of the signal.
    signal2D : array
        2D breathing signal.
    """
    timestamps, mainMotionSignal = signalGeneration(amplitude=amplitude, period=period, mean=mean, sigma=sigma, step=step, signalDuration=signalDuration, coeffMin=coeffMin, coeffMax=coeffMax, meanEvent=meanEvent, meanEventApnea=meanEventApnea)

    secondMotionSignal = mainMotionSignal * otherDimensionsRatio[0] + np.random.normal(loc=0, scale=otherDimensionsNoiseVar[0], size=mainMotionSignal.shape[0])

    signal2D = np.vstack((mainMotionSignal, secondMotionSignal))
    signal2D = signal2D.transpose(1, 0)

    # plt.figure()
    # plt.plot(signal3D[:, 0])
    # plt.plot(signal3D[:, 1])
    # plt.show()

    return timestamps, signal2D




# for i in range(1):
#     time,samples = signalGeneration()
#     time = np.arange(0,100,0.5)
#     plt.figure(figsize=(15,10))
#     plt.plot(time,samples)
#     plt.xlabel("Time [s]")
#     plt.ylabel("Amplitude [mm]")
#     plt.title("Breathing signal part 1")
#     plt.xlim((0,100))
#     plt.ylim((-30,30))


