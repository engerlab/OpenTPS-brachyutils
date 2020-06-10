
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
from Process.C_libraries.libRayTracing_wrapper import *


def CreatePlanStructure(CT, Target, BeamNames, GantryAngles, CouchAngles, Scanner):
  start = time.time()

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

  previous_energy = 999
  for beam in plan.Beams:
    beam.Layers.sort(reverse=True, key=(lambda element: element.NominalBeamEnergy))

    # # arc pt
    # for l in range(len(beam.Layers)):
    #   if(beam.Layers[l].NominalBeamEnergy < previous_energy):
    #     previous_energy = beam.Layers[l].NominalBeamEnergy
    #     beam.Layers = [beam.Layers[l]]
    #     print(beam.Layers[0].NominalBeamEnergy)
    #     break

    # if len(beam.Layers) > 1:
    #   previous_energy = beam.Layers[0].NominalBeamEnergy
    #   beam.Layers = [beam.Layers[0]]
    #   print(beam.Layers[0].NominalBeamEnergy)

  
  plan.isLoaded = 1
  
  print("New plan created in " + str(time.time()-start) + " sec")
  print("Number of spots: " + str(plan.NumberOfSpots)) 
    
  return plan
  


def SpotPlacement(plan, CT, Target_mask, Scanner):
  
  SPR = SPRimage()
  SPR.convert_CT_to_SPR(CT, Scanner)
    
  ImgBorders_x = [SPR.ImagePositionPatient[0], SPR.ImagePositionPatient[0] + SPR.GridSize[0] * SPR.PixelSpacing[0]]
  ImgBorders_y = [SPR.ImagePositionPatient[1], SPR.ImagePositionPatient[1] + SPR.GridSize[1] * SPR.PixelSpacing[1]]
  ImgBorders_z = [SPR.ImagePositionPatient[2], SPR.ImagePositionPatient[2] + SPR.GridSize[2] * SPR.PixelSpacing[2]]
  
  plan.NumberOfSpots = 0
  
  for beam in plan.Beams:
    # generate hexagonal spot grid around isocenter
    SpotGrid = generate_hexagonal_SpotGrid(beam.IsocenterPosition, beam.SpotSpacing, beam.GantryAngle, beam.PatientSupportAngle)
    NumSpots = len(SpotGrid["x"])
    
    # compute direction vector
    u,v,w = 1e-10, 1.0, 1e-10 # BEV to 3D coordinates
    [u,v,w] = Rotate_vector([u,v,w], math.radians(beam.GantryAngle), 'z') # rotation for gantry angle
    [u,v,w] = Rotate_vector([u,v,w], math.radians(beam.PatientSupportAngle), 'y') # rotation for couch angle
    
    # prepare raytracing: translate initial positions at the CT image border
    for s in range(NumSpots):
      Translation = np.array([1.0, 1.0, 1.0])
      Translation[0] = (SpotGrid["x"][s] - ImgBorders_x[int(u<0)]) / u
      Translation[1] = (SpotGrid["y"][s] - ImgBorders_y[int(v<0)]) / v
      Translation[2] = (SpotGrid["z"][s] - ImgBorders_z[int(w<0)]) / w
      Translation = Translation.min()
      SpotGrid["x"][s] = SpotGrid["x"][s] - Translation * u
      SpotGrid["y"][s] = SpotGrid["y"][s] - Translation * v
      SpotGrid["z"][s] = SpotGrid["z"][s] - Translation * w
      
    # transport each spot until it reaches the target
    transport_spots_to_target(SPR, Target_mask, SpotGrid, [u,v,w])
        
    # remove spots that didn't reach the target
    minWET = 9999999
    for s in range(NumSpots-1, -1, -1):
      if(SpotGrid["WET"][s] < 0): 
        SpotGrid["BEVx"].pop(s)
        SpotGrid["BEVy"].pop(s)
        SpotGrid["x"].pop(s)
        SpotGrid["y"].pop(s)
        SpotGrid["z"].pop(s)
        SpotGrid["WET"].pop(s)
      elif(SpotGrid["WET"][s] < minWET): minWET = SpotGrid["WET"][s]

    # raytracing of remaining spots to define energy layers
    transport_spots_inside_target(SPR, Target_mask, SpotGrid, [u,v,w], minWET, beam.LayerSpacing)

    # generate plan structure
    NumSpots = len(SpotGrid["x"])
    for s in range(NumSpots):
      for Energy in SpotGrid["EnergyLayers"][s]:
        plan.NumberOfSpots += 1
        layer_found = 0
        for layer in beam.Layers:
          if(layer.NominalBeamEnergy == Energy):
            # add spot to existing layer
            layer.ScanSpotPositionMap_x.append(SpotGrid["BEVx"][s])
            layer.ScanSpotPositionMap_y.append(SpotGrid["BEVy"][s])
            layer.ScanSpotMetersetWeights.append(1.0)
            layer.SpotMU.append(1.0)
            layer_found = 1
        
        if(layer_found == 0):
          # add new layer
          beam.Layers.append(Plan_IonLayer())
          beam.Layers[-1].NominalBeamEnergy = Energy
          beam.Layers[-1].ScanSpotPositionMap_x.append(SpotGrid["BEVx"][s])
          beam.Layers[-1].ScanSpotPositionMap_y.append(SpotGrid["BEVy"][s])
          beam.Layers[-1].ScanSpotMetersetWeights.append(1.0)
          beam.Layers[-1].SpotMU.append(1.0)
           
  return plan



def generate_hexagonal_SpotGrid(IsoCenter, SpotSpacing, GantryAngle, CouchAngle):
  FOV = 400 # max field size on IBA P+ is 30x40 cm
  NumSpotX = math.ceil(FOV / SpotSpacing)
  NumSpotY = math.ceil(FOV / (SpotSpacing * math.cos(math.pi/6)))

  SpotGrid = {}
  SpotGrid["BEVx"] = []
  SpotGrid["BEVy"] = []
  SpotGrid["x"] = []
  SpotGrid["y"] = []
  SpotGrid["z"] = []
  SpotGrid["WET"] = []
  SpotGrid["EnergyLayers"] = []

  for i in range(NumSpotX):
    for j in range(NumSpotY):
      spot = {}
      
      # coordinates in Beam-eye-view
      SpotGrid["BEVx"].append( (i-round(NumSpotX/2)+(j%2)*0.5)* SpotSpacing )
      SpotGrid["BEVy"].append( (j-round(NumSpotY/2)) * SpotSpacing * math.cos(math.pi/6) )
      
      # 3D coordinates
      x,y,z = SpotGrid["BEVx"][-1], 0, SpotGrid["BEVy"][-1]
      
      # rotation for gantry angle (around Z axis)
      [x,y,z] = Rotate_vector([x,y,z], math.radians(GantryAngle), 'z')
      
      # rotation for couch angle (around Y axis)
      [x,y,z] = Rotate_vector([x,y,z], math.radians(CouchAngle), 'y')
      
      # Dicom CT coordinates
      SpotGrid["x"].append( x + IsoCenter[0] )
      SpotGrid["y"].append( y + IsoCenter[1] )
      SpotGrid["z"].append( z + IsoCenter[2] )
  
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
  
  
  
def OptimizeWeights(plan, contours, method="Scipy-lBFGS"):
  # stopping criteria
  ftol = 1e-5   # tolerance (relative variation of objective function between two iterations)
  maxIter = 50  # maximum number of iterations
    
  #1 Total Dose calculation
  Weights = np.ones((plan.beamlets.NbrSpots), dtype=np.float32)
  if use_MKL == 1:
    TotalDose = sparse_dot_mkl.dot_product_mkl(plan.beamlets.BeamletMatrix, Weights)
  else:
    TotalDose = sp.csc_matrix.dot(plan.beamlets.BeamletMatrix, Weights)
    
  #2 Weight normalization
  # variable change x = u²
  maxDose = np.max(TotalDose)
  x0 = np.sqrt(plan.Objectives.TargetPrescription/maxDose) * np.ones((plan.beamlets.NbrSpots), dtype=np.float32)
  #x0 = np.sqrt(plan.Objectives.TargetPrescription/maxDose) * np.ones((plan.beamlets.NbrSpots), dtype=np.float32) + np.random.normal(0.0, 0.1, (plan.beamlets.NbrSpots)).astype(np.float32)

  # Callable functions
  plan.Objectives.initialize_objective_function(contours)
  #f = lambda x, a=plan.beamlets.BeamletMatrix, b=mask_TV, c=mask_OAR: fobj(x,a,b,c)
  #g = lambda x, a=plan.beamlets.BeamletMatrix,b =mask_TV, c=mask_OAR: dfobj(x,a,b,c)
  f = lambda x, beamlets=plan.beamlets.BeamletMatrix: plan.Objectives.compute_objective_function(x, beamlets)
  g = lambda x, beamlets=plan.beamlets.BeamletMatrix: plan.Objectives.compute_OF_gradient(x, beamlets)

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
    TotalDose = sparse_dot_mkl.dot_product_mkl(plan.beamlets.BeamletMatrix, Weights)
  else:
    TotalDose = sp.csc_matrix.dot(plan.beamlets.BeamletMatrix, Weights)

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
    fvar = abs(fk-fk1) / max(fk, fk1, 1)
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
      #print('  step modifier reduced: ' + str(c2))

    #print('  linesearch iteration', n, ':', stp, fn, flim)
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
    fvar = abs(fk-fk1) / max(fk, fk1, 1)
    print ("  iter={}, fvar={}, x={}, f(x)={}, alpha={}".format(i, fvar, xk1, fk1, alpha))

    # prepare next iter
    xk = xk1
    fk = fk1
    gk = gk1
    Hk = Hk1
    i+=1

  return xk, cost, i