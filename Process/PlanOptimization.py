
import numpy as np
import scipy.ndimage
import scipy.optimize
import scipy.sparse as sp
import pydicom
import math
import time

try:
  import sparse_dot_mkl
  use_MKL = 1
except:
  use_MKL = 0

from Process.RTplan import *


def CreatePlanStructure(CT, Target, BeamNames, GantryAngles, CouchAngles, Scanner):
  plan = RTplan()
  plan.SeriesInstanceUID = pydicom.uid.generate_uid()
  plan.PlanName = "NewPlan"
  plan.Modality = "Ion therapy"
  plan.RadiationType = "Proton"
  plan.ScanMode = "MODULATED"
  plan.TreatmentMachineName = "Unknown"
  plan.NumberOfFractionsPlanned = 1
  
  # compute isocenter position as center of the target
  IsoCenter = ComputeIsocenter(Target.Mask, CT)
  
  # compute RTV = dilated target for spot placement
  RTV_margin = 7.0 # mm
  RTV_margin_x = RTV_margin / CT.PixelSpacing[0] # voxels
  RTV_margin_y = RTV_margin / CT.PixelSpacing[1] # voxels
  RTV_margin_z = RTV_margin / CT.PixelSpacing[2] # voxels
  RTV_size = 2*np.ceil(np.array([RTV_margin_y, RTV_margin_x, RTV_margin_z])).astype(int)+1 # size of the structuring element
  struct = np.zeros(tuple(RTV_size)).astype(bool)
  for i in range(RTV_size[0]):
    for j in range(RTV_size[1]):
      for k in range(RTV_size[2]):
        y = i - math.floor(RTV_size[0]/2)
        x = j - math.floor(RTV_size[1]/2)
        z = k - math.floor(RTV_size[2]/2)
        if(y**2/RTV_margin_y**2 + x**2/RTV_margin_x**2 + z**2/RTV_margin_z**2 <= 1): # generate ellipsoid structuring element
          struct[i,j,k] = True
  RTV_mask = scipy.ndimage.binary_dilation(Target.Mask, structure=struct).astype(Target.Mask.dtype)
  
  # initialize each beam
  for b in range(len(GantryAngles)):
    plan.Beams.append(Plan_IonBeam())
    plan.Beams[b].BeamName = BeamNames[b]
    plan.Beams[b].GantryAngle = GantryAngles[b]
    plan.Beams[b].PatientSupportAngle = CouchAngles[b]
    plan.Beams[b].IsocenterPosition = IsoCenter
    plan.Beams[b].SpotSpacing = 7.0
    plan.Beams[b].LayerSpacing = 6.0
    
  # spot placement
  plan = SpotPlacement(plan, CT, RTV_mask, Scanner)
  
  plan.isLoaded = 1
  
  print("New plan created")
  print("Number of spots: " + str(plan.NumberOfSpots)) 
    
  return plan
  


def SpotPlacement(plan, CT, Target_mask, Scanner):
  
  SPR = SPRimage()
  SPR.convert_CT_to_SPR(CT, Scanner)
    
  CTborders_x = [CT.ImagePositionPatient[0], CT.ImagePositionPatient[0] + CT.GridSize[0] * CT.PixelSpacing[0]]
  CTborders_y = [CT.ImagePositionPatient[1], CT.ImagePositionPatient[1] + CT.GridSize[1] * CT.PixelSpacing[1]]
  CTborders_z = [CT.ImagePositionPatient[2], CT.ImagePositionPatient[2] + CT.GridSize[2] * CT.PixelSpacing[2]]
  
  plan.NumberOfSpots = 0
  
  for beam in plan.Beams:
    # generate hexagonal spot grid around isocenter
    SpotGrid = generate_hexagonal_SpotGrid(beam.IsocenterPosition, beam.SpotSpacing, beam.GantryAngle, beam.PatientSupportAngle)
    
    # compute direction vector
    u,v,w = 1e-10, 1.0, 1e-10 # BEV to 3D coordinates
    [u,v,w] = Rotate_vector([u,v,w], math.radians(beam.GantryAngle), 'z') # rotation for gantry angle
    [u,v,w] = Rotate_vector([u,v,w], math.radians(beam.PatientSupportAngle), 'y') # rotation for couch angle
    
    # prepare raytracing: translate initial positions at the CT image border
    for spot in SpotGrid:
      Translation = np.array([1.0, 1.0, 1.0])
      Translation[0] = (spot["x"] - CTborders_x[int(u<0)]) / u
      Translation[1] = (spot["y"] - CTborders_y[int(v<0)]) / v
      Translation[2] = (spot["z"] - CTborders_z[int(w<0)]) / w
      Translation = Translation.min()
      spot["x"] = spot["x"] - Translation * u
      spot["y"] = spot["y"] - Translation * v
      spot["z"] = spot["z"] - Translation * w
      
    # transport each spot until it reaches the target
    for spot in SpotGrid:
      spot["WET"] = 0
      dist = np.array([1.0, 1.0, 1.0])
      while True:      
        # check if we are still inside the CT image
        if(spot["x"] < CTborders_x[0] and u < 0): spot["WET"]=-1; break
        if(spot["x"] > CTborders_x[1] and u > 0): spot["WET"]=-1; break
        if(spot["y"] < CTborders_y[0] and v < 0): spot["WET"]=-1; break
        if(spot["y"] > CTborders_y[1] and v > 0): spot["WET"]=-1; break
        if(spot["z"] < CTborders_z[0] and w < 0): spot["WET"]=-1; break
        if(spot["z"] > CTborders_z[1] and w > 0): spot["WET"]=-1; break
        
        # check if we reached the target
        voxel = SPR.get_voxel_index([spot["x"], spot["y"], spot["z"]])
        if(voxel[0] >= 0 and voxel[1] >= 0 and voxel[2] >= 0 and voxel[0] < CT.GridSize[0] and voxel[1] < CT.GridSize[1] and voxel[2] < CT.GridSize[2]):
          if(Target_mask[voxel[1], voxel[0], voxel[2]]): break
          
        # compute distante to next voxel
        dist[0] = abs(((math.floor((spot["x"]-CT.ImagePositionPatient[0])/CT.PixelSpacing[0]) + float(u>0)) * CT.PixelSpacing[0] + CT.ImagePositionPatient[0] - spot["x"])/u)
        dist[1] = abs(((math.floor((spot["y"]-CT.ImagePositionPatient[1])/CT.PixelSpacing[1]) + float(v>0)) * CT.PixelSpacing[1] + CT.ImagePositionPatient[1] - spot["y"])/v)
        dist[2] = abs(((math.floor((spot["z"]-CT.ImagePositionPatient[2])/CT.PixelSpacing[2]) + float(w>0)) * CT.PixelSpacing[2] + CT.ImagePositionPatient[2] - spot["z"])/w)
        step = dist.min() + 1e-3
            
        voxel_SPR = SPR.get_SPR_at_position([spot["x"], spot["y"], spot["z"]])
            
        spot["WET"] += voxel_SPR * step
        spot["x"] = spot["x"] + step * u
        spot["y"] = spot["y"] + step * v
        spot["z"] = spot["z"] + step * w
        
        
    # remove spots that didn't reach the target
    minWET = 9999999
    for s in range(len(SpotGrid)-1, -1, -1):
      if(SpotGrid[s]["WET"] < 0): SpotGrid.pop(s)
      elif(SpotGrid[s]["WET"] < minWET): minWET = SpotGrid[s]["WET"]
      
    # raytrace remaining spots to define energy layers
    for spot in SpotGrid:
      NumLayer = math.ceil((spot["WET"] - minWET) / beam.LayerSpacing)
      Layer_WET = minWET + NumLayer * beam.LayerSpacing
      dist = np.array([1.0, 1.0, 1.0])
      while True:      
        # check if we are still inside the CT image
        if(spot["x"] < CTborders_x[0] and u < 0): break
        if(spot["x"] > CTborders_x[1] and u > 0): break
        if(spot["y"] < CTborders_y[0] and v < 0): break
        if(spot["y"] > CTborders_y[1] and v > 0): break
        if(spot["z"] < CTborders_z[0] and w < 0): break
        if(spot["z"] > CTborders_z[1] and w > 0): break
        
        # check if we reached the next layer
        if(spot["WET"] >= Layer_WET):
          voxel = SPR.get_voxel_index([spot["x"], spot["y"], spot["z"]])
          if(voxel[0] >= 0 and voxel[1] >= 0 and voxel[2] >= 0 and voxel[0] < CT.GridSize[0] and voxel[1] < CT.GridSize[1] and voxel[2] < CT.GridSize[2]):
            if(Target_mask[voxel[1], voxel[0], voxel[2]]):
              plan.NumberOfSpots += 1
              Energy = SPR.rangeToEnergy(Layer_WET/10)
              layer_found = 0
              for layer in beam.Layers:
                if(layer.NominalBeamEnergy == Energy):
                  # add spot to existing layer
                  layer.ScanSpotPositionMap_x.append(spot["BEV_x"])
                  layer.ScanSpotPositionMap_y.append(spot["BEV_y"])
                  layer.ScanSpotMetersetWeights.append(1.0)
                  layer.SpotMU.append(1.0)
                  layer_found = 1
              
              if(layer_found == 0):
                # add new layer
                beam.Layers.append(Plan_IonLayer())
                beam.Layers[-1].NominalBeamEnergy = Energy
                beam.Layers[-1].ScanSpotPositionMap_x.append(spot["BEV_x"])
                beam.Layers[-1].ScanSpotPositionMap_y.append(spot["BEV_y"])
                beam.Layers[-1].ScanSpotMetersetWeights.append(1.0)
                beam.Layers[-1].SpotMU.append(1.0)
              
          NumLayer += 1
          Layer_WET = minWET + NumLayer*beam.LayerSpacing
        
        # compute distante to next voxel
        dist[0] = abs(((math.floor((spot["x"]-CT.ImagePositionPatient[0])/CT.PixelSpacing[0]) + float(u>0)) * CT.PixelSpacing[0] + CT.ImagePositionPatient[0] - spot["x"])/u)
        dist[1] = abs(((math.floor((spot["y"]-CT.ImagePositionPatient[1])/CT.PixelSpacing[1]) + float(v>0)) * CT.PixelSpacing[1] + CT.ImagePositionPatient[1] - spot["y"])/v)
        dist[2] = abs(((math.floor((spot["z"]-CT.ImagePositionPatient[2])/CT.PixelSpacing[2]) + float(w>0)) * CT.PixelSpacing[2] + CT.ImagePositionPatient[2] - spot["z"])/w)
        step = dist.min() + 1e-3
            
        voxel_SPR = SPR.get_SPR_at_position([spot["x"], spot["y"], spot["z"]])
            
        spot["WET"] += voxel_SPR * step
        spot["x"] = spot["x"] + step * u
        spot["y"] = spot["y"] + step * v
        spot["z"] = spot["z"] + step * w
           
  return plan



def generate_hexagonal_SpotGrid(IsoCenter, SpotSpacing, GantryAngle, CouchAngle):
  FOV = 400 # max field size on IBA P+ is 30x40 cm
  NumSpotX = math.ceil(FOV / SpotSpacing)
  NumSpotY = math.ceil(FOV / (SpotSpacing * math.cos(math.pi/6)))
  SpotGrid = []
  for i in range(NumSpotX):
    for j in range(NumSpotY):
      spot = {}
      
      # coordinates in Beam-eye-view
      spot["BEV_x"] = (i-round(NumSpotX/2)+(j%2)*0.5)* SpotSpacing 
      spot["BEV_y"] = (j-round(NumSpotY/2)) * SpotSpacing * math.cos(math.pi/6)
      
      # 3D coordinates
      x,y,z = spot["BEV_x"], 0, spot["BEV_y"]
      
      # rotation for gantry angle (around Z axis)
      [x,y,z] = Rotate_vector([x,y,z], math.radians(GantryAngle), 'z')
      
      # rotation for couch angle (around Y axis)
      [x,y,z] = Rotate_vector([x,y,z], math.radians(CouchAngle), 'y')
      
      # Dicom CT coordinates
      spot["x"] = x + IsoCenter[0]
      spot["y"] = y + IsoCenter[1]
      spot["z"] = z + IsoCenter[2]
      SpotGrid.append(spot)
  
  return SpotGrid




def Rotate_vector(vec, angle, axis):
  if axis == 'x':
    x = vec[0]
    y = vec[1] * math.cos(angle) - vec[2] * math.sin(angle)
    z = vec[1] * math.sin(angle) + vec[2] * math.cos(angle)
  elif axis ==  'y':
    x = vec[0] * math.cos(angle) + vec[2] * math.sin(angle)
    y = vec[1]
    z = -vec[0] * math.sin(angle) + vec[2] * math.cos(angle)
  elif axis == 'z':
    x = vec[0] * math.cos(angle) - vec[1] * math.sin(angle)
    y = vec[0] * math.sin(angle) + vec[1] * math.cos(angle)
    z = vec[2]
      
  return [x,y,z]
    
    
    
def ComputeIsocenter(Target_mask, CT):
  maskY,maskX,maskZ = np.nonzero(Target_mask)
  return [np.mean(CT.VoxelX[maskX]), np.mean(CT.VoxelY[maskY]), np.mean(CT.VoxelZ[maskZ])]
  
  
  
def OptimizeWeights(BLMatrix, Target, OAR, method="Scipy-lBFGS"):
  # parameters (TODO: move to the treatment objective class)
  global p, Dmin, Dmean, Dmax, w1, w2, w3, w4, w
  p = 60.
  Dmin = 56.
  Dmean = 20.
  Dmax = 64.
  w1 = 5.
  w2 = 2.
  w3 = 1.
  w4 = 2.
  w = np.array([w1,w2,w3,w4])
  
  # stopping criteria
  ftol = 1e-5   # tolerance (relative variation of objective function between two iterations)
  maxIter = 50  # maximum number of iterations

  # vectorize ROI
  mask_TV = np.flip(Target.Mask, (0,1)).transpose(1,0,2)
  mask_TV = np.ndarray.flatten(mask_TV, 'F')
  mask_OAR = np.flip(OAR.Mask, (0,1)).transpose(1,0,2)
  mask_OAR = np.ndarray.flatten(mask_OAR, 'F')
    
  #1 Total Dose calculation
  Weights = np.ones((BLMatrix.shape[1]), dtype=np.float32)
  if use_MKL == 1:
    TotalDose = sparse_dot_mkl.dot_product_mkl(BLMatrix, Weights)
  else:
    TotalDose = sp.csc_matrix.dot(BLMatrix, Weights)
  maxDose = np.max(TotalDose)
  print("max dose = ", maxDose)
    
  #2 Weight normalization
  # variable change x = u²
  x0 = np.sqrt(p/maxDose) * np.ones((BLMatrix.shape[1]), dtype=np.float32)
  #x0 = np.sqrt(p/maxDose) * np.ones((BLMatrix.shape[1]), dtype=np.float32) + np.random.normal(0.0, 0.1, (BLMatrix.shape[1])).astype(np.float32)

  # Callable functions
  f = lambda x,a=BLMatrix,b=mask_TV,c=mask_OAR: fobj(x,a,b,c)
  g = lambda x,a=BLMatrix,b=mask_TV,c=mask_OAR: dfobj(x,a,b,c)

  start = time.time()

  # Optimization methods
  if method=="Scipy-lBFGS":
    print ('\n======= Scipy Limited memory Broyden-Fletcher-Goldfarb-Shanno ======\n')
    def callbackF(Xi):
      print('{0:.6e}  '.format(f(Xi)))
      cost.append(f(Xi))

    cost = [f(x0)]
    result = scipy.optimize.minimize(f, x0, method='L-BFGS-B', jac=g, callback=callbackF)
    x = result.x
    print("Optimization finished in " + str(time.time()-start) + " sec")
    print ("  Scipy lBFGS terminated in {} maxIter, x = {}, f(x) = {}, time elapsed {}, time per iter {}"\
      .format(result.nit, x, f(x), time.time()-start, (time.time()-start)/result.nit))

  elif method=="Gradient":
    print ('\n======= Steepest Descent ======\n')
    x, cost, n_iter = steepest_descent(f,g , x0, maxIter, ftol)
    print ("  Steepest Descent terminated in {} maxIter, x = {}, f(x) = {}, time elapsed {}, time per iter {}"\
      .format(n_iter, x, f(x), time.time()-start, (time.time()-start)/n_iter))

  elif method=="BFGS":
    print ('\n======= Broyden-Fletcher-Goldfarb-Shanno ======\n')
    x, cost, n_iter = bfgs(f, g, x0, maxIter, ftol)
    print ("  BFGS terminated in {} maxIter, x = {}, f(x) = {}, time elapsed {}, time per iter {}"\
      .format(n_iter, x, f(x), time.time()-start, (time.time()-start)/n_iter))

  Weights = np.square(x).astype(np.float32)
  if use_MKL == 1:
    TotalDose = sparse_dot_mkl.dot_product_mkl(BLMatrix, Weights)
  else:
    TotalDose = sp.csc_matrix.dot(BLMatrix, Weights)

  return Weights, TotalDose, cost 



def fobj(u, BLMatrix, mask_TV, mask_OAR):
  weights = np.square(u).astype(np.float32)

  if use_MKL == 1:
    doseTotal = sparse_dot_mkl.dot_product_mkl(BLMatrix,weights)
  else:
    doseTotal = sp.csc_matrix.dot(BLMatrix,weights)

  f_min_TV = np.mean(np.minimum(0,doseTotal[mask_TV]-Dmin))
  f_max_TV = np.mean(np.maximum(0,doseTotal[mask_TV]-Dmax))
  f_mean_OAR = np.maximum(0,np.mean(doseTotal[mask_OAR], dtype=np.float32)-Dmean)
  f_max_OAR = np.mean(np.maximum(0,doseTotal[mask_OAR]-p))

  #fTot = w[0] * np.square(f_min_TV) + w[1] * np.square(f_max_TV) + w[2] * np.square(f_mean_OAR) + w[3] * np.square(f_max_OAR)
  fTot = w[0] * f_min_TV**2 + w[1] * f_max_TV**2 + w[2] * f_mean_OAR**2 + w[3] * f_max_OAR**2

  return fTot



def dfobj(u, BLMatrix, mask_TV, mask_OAR):
  weights = np.square(u).astype(np.float32)

  if use_MKL == 1:
    doseTotal = sparse_dot_mkl.dot_product_mkl(BLMatrix,weights)
  else:
    doseTotal = sp.csc_matrix.dot(BLMatrix,weights)

  f_min_TV = np.minimum(0,doseTotal[mask_TV]-Dmin)
  f_max_TV = np.maximum(0,doseTotal[mask_TV]-Dmax)
  f_mean_OAR = np.maximum(0,np.mean(doseTotal[mask_OAR], dtype=np.float32)-Dmean)
  f_max_OAR = np.maximum(0,doseTotal[mask_OAR]-p)

  uDiag = sp.diags(u.astype(np.float32), format='csc')

  if use_MKL == 1:
    doseTmp = sparse_dot_mkl.dot_product_mkl(BLMatrix,uDiag)
    tmp = sp.diags(f_min_TV.astype(np.float32), format='csc')
    df_min_TV = sparse_dot_mkl.dot_product_mkl(tmp, doseTmp[mask_TV,:])
    tmp = sp.diags(f_max_TV.astype(np.float32), format='csc')
    df_max_TV = sparse_dot_mkl.dot_product_mkl(tmp, doseTmp[mask_TV,:])
    tmp = sp.diags(f_max_OAR.astype(np.float32), format='csc')
    df_max_OAR = sparse_dot_mkl.dot_product_mkl(tmp, doseTmp[mask_OAR,:])
    df_mean_OAR = sp.csr_matrix.multiply(doseTmp[mask_OAR,:], f_mean_OAR)
    dfTot = 4*(w[0]*sp.csr_matrix.mean(df_min_TV,axis=0) + w[1]*sp.csr_matrix.mean(df_max_TV,axis=0) +w[2]*sp.csr_matrix.mean(df_mean_OAR,axis=0) +w[3]*sp.csr_matrix.mean(df_max_OAR,axis=0))
  else:
    doseTmp = sp.csc_matrix.dot(BLMatrix,uDiag)
    doseTmp = sp.csc_matrix.transpose(doseTmp)
    df_min_TV = sp.csr_matrix.multiply(doseTmp[:,mask_TV], f_min_TV)
    df_max_TV = sp.csr_matrix.multiply(doseTmp[:,mask_TV], f_max_TV)
    df_max_OAR = sp.csr_matrix.multiply(doseTmp[:,mask_OAR], f_max_OAR)
    df_mean_OAR = sp.csr_matrix.multiply(doseTmp[:,mask_OAR], f_mean_OAR)
    dfTot = 4*(w[0]*sp.csr_matrix.mean(df_min_TV,axis=1) + w[1]*sp.csr_matrix.mean(df_max_TV,axis=1) +w[2]*sp.csr_matrix.mean(df_mean_OAR,axis=1) +w[3]*sp.csr_matrix.mean(df_max_OAR,axis=1))

  dfTot = np.squeeze(np.asarray(dfTot))

  return dfTot



def steepest_descent(f, g, x0, maxIter, ftol):
  xk = x0
  fk = f(xk)
  cost = [fk]
  fvar = ftol+1
  alpha = 0.02
  i = 0

  while fvar > ftol and i < maxIter:
    # compute search direction
    pk = -g(xk)

    # update x
    xk1 = xk + alpha * pk

    # compute stopping criteria
    fk1 = f(xk1)
    cost.append(fk1)
    fvar = (fk-fk1) / max(fk, fk1, 1)
    print ("  iter={}, fvar={}, x={}, f(x)={}, alpha={}".format(i, fvar, xk1, fk1, alpha))

    # prepare next iter
    xk = xk1
    fk = fk1
    i += 1

  return xk, cost, i



def BacktrackingLineSearch(f, df, xk, pk, df_xk = None, f_xk = None, args = (), c1 = 5e-5, c2 = 0.8, eps = 1e-8):
  """
  Backtracking linesearch
  f: objective function
  df: gradient function
  xk: current point
  pk: direction of search
  df_xk: gradient at x
  f_xk = f(xk) (Optional)
  args: optional arguments to f (optional)
  c1, c2: backtracking parameters
  eps: (Optional) quit if norm of step produced is less than this
  """

  if f_xk is None:
    f_xk = f(xk, *args)
  if df_xk is None:
    df_xk = df(xk, *args)

  assert df_xk.T.shape == pk.shape

  derphi = np.dot(df_xk, pk)

  stp = 1.0
  n = 0
  fn = f(xk + stp * pk, *args)
  flim = f_xk + c1 * stp * derphi
  len_p = np.linalg.norm(pk)

  #Loop until Armijo condition is satisfied
  while fn > flim:
    stp *= c2
    n += 1
    fn1 = f(xk + stp * pk, *args)
    if fn1 < fn:
      fn = fn1
    else: # we passed the minimum
      c2 = (c2+1)/2 # reduce the step modifier
      if 1-c2 < eps: break
      print('  step modifier reduced:' + str(c2))

    print('  linesearch iteration', n, ':', stp, fn, flim)
    if stp * len_p < eps:
      print('  Step is  too small, stop')
      break

  print('  Linesearch done (' + str(n) + ' iter)')

  return stp




def bfgs(f, g, x0, maxIter, ftol):
  xk = x0
  fk = f(xk)
  gk = g(xk)
  cost = [fk]
  fvar = ftol+1
  c2 = 0.9
  I = np.identity(xk.size)
  Hk = I
  i = 0

  while fvar > ftol and i < maxIter:
    # compute search direction
    pk = -Hk.dot(gk)

    # obtain step length by line search
    alpha = BacktrackingLineSearch(f, g, xk, pk)

    # update x
    xk1 = xk + alpha * pk

    # compute H_{k+1} by BFGS update
    gk1 = g(xk1)
    sk = xk1 - xk
    yk = gk1 - gk
    rho_k = float(1.0 / yk.dot(sk))
    Hk1 = (I - rho_k * np.outer(sk, yk)).dot(Hk).dot(I - rho_k * np.outer(yk, sk)) + rho_k * np.outer(sk, sk)

    # compute stopping criteria
    fk1 = f(xk1)
    cost.append(fk1)
    if fk1 < fk:
      fvar = (fk-fk1) / max(fk, fk1, 1)
    print ("  iter={}, fvar={}, x={}, f(x)={}, alpha={}".format(i, fvar, xk1, fk1, alpha))

    # prepare next iter
    xk = xk1
    fk = fk1
    gk = gk1
    Hk = Hk1
    i+=1

  return xk, cost, i