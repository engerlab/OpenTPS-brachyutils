from opentps.core.data.images._roiMask import ROIMask
import numpy as np
import matplotlib.pyplot as plt

roi = ROIMask(name='TV')
roi.color = (255, 0, 0) # red
data = np.zeros((100, 100, 100)).astype(bool)
data[50:60, 50:60, 50:60] = True
roi.imageArray = data
radius = np.array([5,10,7])
roi.spacing = np.array([2,2,1])

plt.figure()
plt.imshow(roi.imageArray[55,:,:], cmap='gray')
plt.title("Original")

roi_scipy = roi.copy()
radius_scipy = radius.copy()
roi_scipy.dilate(radius=radius_scipy) #scipy
plt.figure()
plt.imshow(roi_scipy.imageArray[55,:,:], cmap='gray')
plt.title("Scipy")

roi_sitk = roi.copy()
radius_sitk = np.round(radius / roi.spacing).astype(int).tolist()
roi_sitk._dilateSITK(radius_sitk)
plt.figure()
plt.imshow(roi_sitk.imageArray[55,:,:], cmap='gray')
plt.title("SITK")

plt.show()