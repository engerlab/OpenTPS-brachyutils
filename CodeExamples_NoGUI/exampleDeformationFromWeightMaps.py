import numpy as np
import matplotlib.pyplot as plt

from Core.Data.dynamic3DModel import Dynamic3DModel
from Core.Data.dynamic3DSequence import Dynamic3DSequence
from Core.Data.Images.ctImage import CTImage
from Core.Processing.weightMaps import generateDeformationFromTrackers, generateDeformationFromTrackersAndWeightMaps

# GENERATE SYNTHETIC 4D INPUT SEQUENCE
CT4D = Dynamic3DSequence()
phase0 = np.full((170, 100, 100), -1000)
phase0[20:150,20:80,:] = 0
phase0[30:70,30:70,20:] = -800
phase0[100:140,30:70,20:] = -800
phase0[45:55,45:55,30:40] = 0
CT4D.dyn3DImageList.append(CTImage(imageArray=phase0, name='fixed', origin=[0,0,0], spacing=[1,1,1]))
phase1 = np.full((170, 100, 100), -1000)
phase1[20:150,20:80,:] = 0
phase1[30:70,30:70,30:] = -800
phase1[100:140,30:70,30:] = -800
phase1[42:52,45:55,40:50] = 0
CT4D.dyn3DImageList.append(CTImage(imageArray=phase1, name='fixed', origin=[0,0,0], spacing=[1,1,1]))
phase2 = np.full((170, 100, 100), -1000)
phase2[20:150,20:80,:] = 0
phase2[30:70,30:70,40:] = -800
phase2[100:140,30:70,40:] = -800
phase2[45:55,45:55,50:60] = 0
CT4D.dyn3DImageList.append(CTImage(imageArray=phase2, name='fixed', origin=[0,0,0], spacing=[1,1,1]))
phase3 = np.full((170, 100, 100), -1000)
phase3[20:150,20:80,:] = 0
phase3[30:70,30:70,30:] = -800
phase3[100:140,30:70,30:] = -800
phase3[48:58,45:55,40:50] = 0
CT4D.dyn3DImageList.append(CTImage(imageArray=phase3, name='fixed', origin=[0,0,0], spacing=[1,1,1]))

# CREATE TRACKER POSITIONS
trackers = [[50, 50, 30],
           [120, 50, 30]]

# GENERATE MIDP
Model4D = Dynamic3DModel()
Model4D.computeMidPositionImage(CT4D, 0, baseResolution=4, nbProcesses=1)

# GENERATE ADDITIONAL PHASES
df1, wm = generateDeformationFromTrackers(Model4D, [0, 2/4], [1, 1], trackers)
im1 = df1.deformImage(Model4D.midp, fillValue='closest')
df2, wm = generateDeformationFromTrackers(Model4D, [0.5/4, 1.5/4], [1, 1], trackers)
im2 = df2.deformImage(Model4D.midp, fillValue='closest')
df3 = generateDeformationFromTrackersAndWeightMaps(Model4D, [0, 2/4], [2, 2], wm)
im3 = df3.deformImage(Model4D.midp, fillValue='closest')

# RESAMPLE WEIGHT MAPS TO IMAGE RESOLUTION
for i in range(len(trackers)):
    wm[i].resampleToImageGrid(Model4D.midp)

# DISPLAY RESULTS
fig, ax = plt.subplots(3, 3)
ax[0,0].imshow(Model4D.midp.imageArray[:, 49, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
s0 = wm[0].imageArray[:, 49, :].T[::-1, ::1]
s1 = wm[1].imageArray[:, 49, :].T[::-1, ::1]
ax[0,0].imshow(s0, cmap='Reds', origin='upper', vmin=0, vmax=1, alpha=0.3)
ax[0,0].imshow(s1, cmap='Blues', origin='upper', vmin=0, vmax=1, alpha=0.3)
ax[1,0].imshow(s0, cmap='Reds', origin='upper', vmin=0, vmax=1)
ax[2,0].imshow(s1, cmap='Blues', origin='upper', vmin=0, vmax=1)
ax[0,0].plot(50,100-30,'ro')
ax[0,0].plot(120,100-30,'bo')
ax[1,0].plot(50,100-30,'ro')
ax[2,0].plot(120,100-30,'bo')
ax[1,0].plot(50,100-30,'ro')
ax[2,0].plot(120,100-30,'bo')
ax[0,1].imshow(Model4D.midp.imageArray[49, :, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
s0 = wm[0].imageArray[49, :, :].T[::-1, ::1]
s1 = wm[1].imageArray[49, :, :].T[::-1, ::1]
ax[0,1].imshow(s0, cmap='Reds', origin='upper', vmin=0, vmax=1, alpha=0.3)
ax[0,1].imshow(s1, cmap='Blues', origin='upper', vmin=0, vmax=1, alpha=0.3)
ax[1,1].imshow(s0, cmap='Reds', origin='upper', vmin=0, vmax=1)
ax[2,1].imshow(s1, cmap='Blues', origin='upper', vmin=0, vmax=1)
ax[0,1].plot(50,100-30,'ro')
ax[0,1].plot(50,100-30,'bo')
ax[1,1].plot(50,100-30,'ro')
ax[2,1].plot(50,100-30,'bo')
ax[1,1].plot(50,100-30,'ro')
ax[2,1].plot(50,100-30,'bo')
ax[0,2].imshow(Model4D.midp.imageArray[:, :, 49].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
s0 = wm[0].imageArray[:, :, 49].T[::-1, ::1]
s1 = wm[1].imageArray[:, :, 49].T[::-1, ::1]
ax[0,2].imshow(s0, cmap='Reds', origin='upper', vmin=0, vmax=1, alpha=0.3)
ax[0,2].imshow(s1, cmap='Blues', origin='upper', vmin=0, vmax=1, alpha=0.3)
ax[1,2].imshow(s0, cmap='Reds', origin='upper', vmin=0, vmax=1)
ax[2,2].imshow(s1, cmap='Blues', origin='upper', vmin=0, vmax=1)
ax[0,2].plot(50,50,'ro')
ax[0,2].plot(120,50,'bo')
ax[1,2].plot(50,50,'ro')
ax[2,2].plot(120,50,'bo')
ax[1,2].plot(50,50,'ro')
ax[2,2].plot(120,50,'bo')

fig, ax = plt.subplots(2, 4)
fig.tight_layout()
y_slice = round(Model4D.midp.imageArray.shape[1]/2)-1
ax[0,0].imshow(CT4D.dyn3DImageList[0].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
ax[0,0].title.set_text('Phase 0')
ax[0,1].imshow(CT4D.dyn3DImageList[1].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
ax[0,1].title.set_text('Phase 1')
ax[0,2].imshow(CT4D.dyn3DImageList[2].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
ax[0,2].title.set_text('Phase 2')
ax[0,3].imshow(CT4D.dyn3DImageList[3].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
ax[0,3].title.set_text('Phase 3')
ax[1,0].imshow(Model4D.midp.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
ax[1,0].imshow(wm[0].imageArray[:, y_slice, :].T[::-1, ::1], cmap='Reds', origin='upper', vmin=0, vmax=1, alpha=0.3)
ax[1,0].imshow(wm[1].imageArray[:, y_slice, :].T[::-1, ::1], cmap='Blues', origin='upper', vmin=0, vmax=1, alpha=0.3)
ax[1,0].plot(50,100-30,'ro')
ax[1,0].plot(120,100-30,'bo')
ax[1,0].title.set_text('MidP and weight maps')
ax[1,1].imshow(im1.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
ax[1,1].title.set_text('phases [0,2] - amplitude 1')
ax[1,2].imshow(im2.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
ax[1,2].title.set_text('phases [0.5,1.5] - amplitude 1')
ax[1,3].imshow(im3.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
ax[1,3].title.set_text('phases [0,2] - amplitude 2')

plt.show()

print('done')
print(' ')
