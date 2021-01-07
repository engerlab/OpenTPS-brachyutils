import numpy as np
import scipy.ndimage
import scipy.optimize
import scipy.sparse as sp
import pydicom
import time

try:
  import sparse_dot_mkl
  use_MKL = 1
except:
  use_MKL = 0

from Process.RTplan import *
from Process.C_libraries.libRayTracing_wrapper import *

from Process.pyOpti import functions,solvers,acceleration



def CreatePlanStructure(CT, Target, BeamNames, GantryAngles, CouchAngles, Scanner, RTV_margin = 7.0, SpotSpacing = 7.0, LayerSpacing = 6.0):
  start = time.time()

  plan = RTplan()
  plan.SOPInstanceUID = pydicom.uid.generate_uid()
  plan.SeriesInstanceUID = plan.SOPInstanceUID + ".1"
  plan.PlanName = "NewPlan"
  plan.Modality = "Ion therapy"
  plan.RadiationType = "Proton"
  plan.ScanMode = "MODULATED"
  plan.TreatmentMachineName = "Unknown"
  plan.NumberOfFractionsPlanned = 1

  # compute isocenter position as center of the target
  IsoCenter = ComputeIsocenter(Target.Mask, CT)

  # compute RTV = dilated target for spot placement
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
    plan.Beams[b].SpotSpacing = SpotSpacing
    plan.Beams[b].LayerSpacing = LayerSpacing

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



def OptimizeWeights(plan, contours, maxIter=50, ftol=1e-5, method="Scipy-lBFGS", step=1.0, output=None, *args):
  # Total Dose calculation
  Weights = np.ones((plan.beamlets.NbrSpots), dtype=np.float32)
  if use_MKL == 1:
    TotalDose = sparse_dot_mkl.dot_product_mkl(plan.beamlets.BeamletMatrix, Weights)
  else:
    TotalDose = sp.csc_matrix.dot(plan.beamlets.BeamletMatrix, Weights)

  # Weight normalization
  # variable change x = u²
  maxDose = np.max(TotalDose)
  x0 = np.sqrt(plan.Objectives.TargetPrescription/maxDose) * np.ones((plan.beamlets.NbrSpots), dtype=np.float32)

  # Callable functions
  plan.Objectives.initialize_objective_function(contours)
  f = lambda x, beamlets=plan.beamlets.BeamletMatrix, scenarios=plan.scenarios: plan.Objectives.compute_objective_function(x, beamlets, ScenariosBL=scenarios)
  g = lambda x, beamlets=plan.beamlets.BeamletMatrix, scenarios=plan.scenarios: plan.Objectives.compute_OF_gradient(x, beamlets, ScenariosBL=scenarios)

  start = time.time()
  f1 = functions.func()
  f1._eval = f
  f1._grad = g
  f2 = functions.dummy()

  # Need robust optimization?
  robust = False
  for objective in plan.Objectives.list:
    if objective.Robust == True: robust = True

  # Optimization methods
  if method=="Scipy-lBFGS":
    print ('\n======= Scipy Limited memory Broyden-Fletcher-Goldfarb-Shanno ======\n')
    grad64 = lambda x, beamlets=plan.beamlets.BeamletMatrix, scenarios=plan.scenarios: plan.Objectives.compute_OF_gradient(x, beamlets, ScenariosBL=scenarios, formatArray=64)
    def callbackF(Xi):
        print('cost function = {0:.6e}  '.format(f(Xi)))
        cost.append(f(Xi))
    cost = [f(x0)]
    ret = scipy.optimize.minimize(f, x0, method='L-BFGS-B', jac=grad64, callback=callbackF, options={'ftol': ftol, 'maxiter': maxIter})
    x = ret.x
    print ("  Scipy lBFGS terminated in {} Iter, x = {}, f(x) = {}, time elapsed {}, time per iter {}"\
    .format(ret.nit, x, f(x), time.time()-start, (time.time()-start)/ret.nit))

  elif method=="Gradient":
    print ('\n======= Steepest Descent ======\n')
    solver = solvers.gradient_descent(step = step)
    ret = solvers.solve([f1,f2],x0,plan,solver,atol=1e-5,rtol = 1e-5, maxit=maxIter, verbosity='ALL', output=output)
    x = ret['sol']
    print ("  Steepest Descent terminated in {} Iter, x = {}, f(x) = {}, time elapsed {}, time per iter {}"\
    .format(ret['niter'], x, f(x),ret['time'], ret['time']/ret['niter']))

  elif method=="BFGS":
    print ('\n======= Broyden-Fletcher-Goldfarb-Shanno ======\n')
    if(robust == False or plan.scenarios == []): accel = acceleration.linesearch()
    else: accel = acceleration.linesearch_v2()
    solver = solvers.bfgs(accel=accel, step = step)
    ret = solvers.solve([f1,f2],x0,plan,solver,atol=1e-5,rtol = 1e-5, maxit=maxIter, verbosity='ALL', output=output)
    x = ret['sol']

    print ("  BFGS terminated in {} Iter, x = {}, f(x) = {}, time elapsed {}, time per iter {}"\
    .format(ret['niter'], x, f(x), time.time()-start, ret['time']/ret['niter']))

  elif method=="L-BFGS":
    print ('\n======= Limited Memory Broyden-Fletcher-Goldfarb-Shanno ======\n')
    if(robust == False or plan.scenarios == []): accel = acceleration.linesearch()
    else: accel = acceleration.linesearch_v2()
    solver = solvers.lbfgs(accel=accel, step = step)
    ret = solvers.solve([f1,f2],x0,plan, solver,atol=1e-5,rtol = 1e-5, maxit=maxIter, verbosity='ALL',output=output)
    x = ret['sol']
    print ("  L-BFGS terminated in {} Iter, x = {}, f(x) = {}, time elapsed {}, time per iter {}"\
      .format(ret['niter'], x, f(x),ret['time'], ret['time']/ret['niter']))

  try:
    cost = ret['objective']
  except KeyError:
    # scipy syntax
    cost = f(x)
  Weights = np.square(x).astype(np.float32)

  if use_MKL == 1:
    TotalDose = sparse_dot_mkl.dot_product_mkl(plan.beamlets.BeamletMatrix, Weights)
  else:
    TotalDose = sp.csc_matrix.dot(plan.beamlets.BeamletMatrix, Weights)

  return Weights, TotalDose, cost


