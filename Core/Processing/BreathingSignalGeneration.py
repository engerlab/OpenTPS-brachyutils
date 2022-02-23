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
def vectorSimulation(L,diff,mean,sigma,Tend,t):
    timestamp = events(L,Tend)        
    y = np.zeros(len(t))
    i = 0
    while i < len(timestamp):
        if i+2 < len(timestamp):
            a = np.random.uniform(-diff,diff)
            t1 = timestamp[i+1]
            t2 = timestamp[i+2]
            y[(t>=t1) & (t<=t2)] = a
        i+=2
    #noise = np.random.normal(0,diff/50,len(t))
    noise = np.random.normal(mean,sigma,len(t))
    y += noise
    return y

#creation des donnees respiratoires
def signal(A=10,dA=5,T=4,df=0.5,dS=5,mean=0,sigma=0.1,step=0.2,Tend=100,L=2/30):
    f = 1/T  
    t = np.arange(0,Tend,step)
    
    A += vectorSimulation(L,dA,mean,sigma,Tend,t)
    s = vectorSimulation(L,dS,mean,sigma,Tend,t)
    f += vectorSimulation(L,df,mean,sigma,Tend,t)
    
    y = A*np.sin(2*np.pi*f*(t%(1/f))) + s
    return t,y
"""
#parametres changeables
A = 10 #amplitude (mm)
dA = 5 #variation d amplitude possible (mm)
T = 4.0 #periode respiratoire (s)
df = 0.5 #variation de frequence possible (Hz)
dS = 5 #shift du signal (mm)
step = 0.2 #periode d echantillonnage
Tend = 100 #temps de simulation
L = 2/30 #moyenne des evenements aleatoires

time,samples = signal(A,dA,T,df,dS,step,Tend,L)
plt.figure()
plt.plot(time,samples)
plt.xlabel("Time [s]")
plt.ylabel("Amplitude [mm]")
plt.title("Breathing signal")
plt.xlim((0,50))
"""