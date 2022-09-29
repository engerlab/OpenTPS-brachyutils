import logging
import os
import sys

import numpy as np
from scipy import ndimage as nd
import math
import ctypes
import platform

from opentps.core.processing.rangeEnergy import rangeToEnergy
import opentps.core.processing.C_libraries as clibraries

logger = logging.getLogger(__name__)
currentWorkingDir = os.getcwd()


def WET_raytracing(SPR, beam_direction, ROI=[]):
    try:
        # import C library
        if (platform.system() == "Linux"):
            libRaytracing = ctypes.cdll.LoadLibrary(clibraries.__path__[0] + os.sep + "libRayTracing.so")
        elif (platform.system() == "Windows"):
            libRaytracing = ctypes.cdll.LoadLibrary(clibraries.__path__[0] + os.sep + "libRayTracing.dll")
        else:
            logger.error("Not compatible with " + platform.system() + " system.")
        float_array = np.ctypeslib.ndpointer(dtype=np.float32)
        int_array = np.ctypeslib.ndpointer(dtype=np.int32)
        bool_array = np.ctypeslib.ndpointer(dtype=np.bool)
        libRaytracing.raytrace_WET.argtypes = [float_array, bool_array, float_array, float_array, float_array,
                                               int_array, float_array]
        libRaytracing.raytrace_WET.restype = ctypes.c_void_p

        # prepare inputs for C library
        Offset = np.array(SPR.origin, dtype=np.float32, order='C')
        PixelSpacing = np.array(SPR.spacing, dtype=np.float32, order='C')
        GridSize = np.array(SPR.gridSize, dtype=np.int32, order='C')
        beam_direction = np.array(beam_direction, dtype=np.float32, order='C')
        WET = np.zeros(SPR.gridSize, dtype=np.float32, order='C')
        if ROI == []:
            ROI_mask = np.ones(SPR.gridSize)
        else:
            ROI_mask = ROI.Mask

        # call C function
        libRaytracing.raytrace_WET(SPR.imageArray.astype(np.float32), ROI_mask.astype(np.bool), WET, Offset,
                                   PixelSpacing, GridSize, beam_direction)


    except:
        logger.warning('Accelerated raytracing not enabled. The python implementation is used instead')
        Voxel_Coord_X = SPR.origin[0] + np.arange(SPR.gridSize[0]) * SPR.spacing[0]
        Voxel_Coord_Y = SPR.origin[1] + np.arange(SPR.gridSize[1]) * SPR.spacing[1]
        Voxel_Coord_Z = SPR.origin[2] + np.arange(SPR.gridSize[2]) * SPR.spacing[2]
        u = -beam_direction[0]
        v = -beam_direction[1]
        w = -beam_direction[2]

        WET = np.zeros(SPR.gridSize)

        for i in range(SPR.gridSize[0]):
            for j in range(SPR.gridSize[1]):
                for k in range(SPR.gridSize[2]):
                    if (ROI != []):
                        if (ROI.Mask[i, j, k] == 0): continue

                    # initialize raytracing for voxel ijk
                    voxel_WET = 0
                    x = Voxel_Coord_X[i] + 0.5 * SPR.spacing[0]
                    y = Voxel_Coord_Y[j] + 0.5 * SPR.spacing[1]
                    z = Voxel_Coord_Z[k] + 0.5 * SPR.spacing[2]
                    dist = np.array([1.0, 1.0, 1.0])

                    # raytracing loop
                    while True:
                        # check if we are still inside the SPR image
                        if x < Voxel_Coord_X[0] and u < 0: break
                        if x > Voxel_Coord_X[-1] and u > 0: break
                        if y < Voxel_Coord_Y[0] and v < 0: break
                        if y > Voxel_Coord_Y[-1] and v > 0: break
                        if z < Voxel_Coord_Z[0] and w < 0: break
                        if z > Voxel_Coord_Z[-1] and w > 0: break

                        # compute distante to next voxel
                        dist[0] = abs(((math.floor((x - SPR.origin[0]) / SPR.spacing[0]) + float(
                            u > 0)) * SPR.spacing[0] + SPR.origin[0] - x) / u)
                        dist[1] = abs(((math.floor((y - SPR.origin[1]) / SPR.spacing[1]) + float(
                            v > 0)) * SPR.spacing[1] + SPR.origin[1] - y) / v)
                        dist[2] = abs(((math.floor((z - SPR.origin[2]) / SPR.spacing[2]) + float(
                            w > 0)) * SPR.spacing[2] + SPR.origin[2] - z) / w)
                        step = dist.min() + 1e-3

                        # accumulate WET
                        voxel_SPR = SPR.get_SPR_at_position([x, y, z])
                        voxel_WET += voxel_SPR * step

                        # update position
                        x = x + step * u
                        y = y + step * v
                        z = z + step * w

                    WET[i, j, k] = voxel_WET

    return WET


def compute_position_from_range(SPR, spot_positions, spot_directions, spot_ranges):
    NumSpots = len(spot_positions)

    try:
        # import C library
        if platform.system() == "Linux":
            libRaytracing = ctypes.cdll.LoadLibrary(clibraries.__path__[0] + os.sep + "libRayTracing.so")
        elif platform.system() == "Windows":
            libRaytracing = ctypes.cdll.LoadLibrary(clibraries.__path__[0] + os.sep + "libRayTracing.dll")
        else:
            logger.error("Not compatible with " + platform.system() + " system.")
        float_array = np.ctypeslib.ndpointer(dtype=np.float32)
        int_array = np.ctypeslib.ndpointer(dtype=np.int32)
        libRaytracing.compute_position_from_range.argtypes = [float_array, float_array, float_array, int_array,
                                                              float_array, float_array, float_array, ctypes.c_int]
        libRaytracing.compute_position_from_range.restype = ctypes.c_void_p

        # prepare inputs for C library
        Offset = np.array(SPR.origin, dtype=np.float32, order='C')
        PixelSpacing = np.array(SPR.spacing, dtype=np.float32, order='C')
        GridSize = np.array(SPR.gridSize, dtype=np.int32, order='C')
        positions = np.array(spot_positions, dtype=np.float32, order='C')
        positions = positions.reshape(NumSpots * 3, order='C')
        directions = np.array(spot_directions, dtype=np.float32, order='C')
        directions = directions.reshape(NumSpots * 3, order='C')
        ranges = np.array(spot_ranges, dtype=np.float32, order='C')

        # call C function
        libRaytracing.compute_position_from_range(SPR.imageArray.astype(np.float32), Offset, PixelSpacing, GridSize,
                                                  positions, directions, ranges, NumSpots)

        CartesianSpotPositions = positions.reshape((NumSpots, 3), order='C').tolist()


    except:
        logger.warning('Accelerated raytracing not enabled. The python implementation is used instead')
        CartesianSpotPositions = []

        ImgBorders_x = [SPR.origin[0],
                        SPR.origin[0] + SPR.gridSize[0] * SPR.spacing[0]]
        ImgBorders_y = [SPR.origin[1],
                        SPR.origin[1] + SPR.gridSize[1] * SPR.spacing[1]]
        ImgBorders_z = [SPR.origin[2],
                        SPR.origin[2] + SPR.gridSize[2] * SPR.spacing[2]]

        for i in range(NumSpots):
            x = spot_positions[i][0]
            y = spot_positions[i][1]
            z = spot_positions[i][2]
            u = spot_directions[i][0]
            v = spot_directions[i][1]
            w = spot_directions[i][2]
            range_in_water = spot_ranges[i]

            WET = 0
            dist = np.array([1.0, 1.0, 1.0])

            # RayTracing algorithm
            while WET < range_in_water:
                # check if we are still inside the SPR image
                if x < ImgBorders_x[0] and u < 0: break
                if x > ImgBorders_x[1] and u > 0: break
                if y < ImgBorders_y[0] and v < 0: break
                if y > ImgBorders_y[1] and v > 0: break
                if z < ImgBorders_z[0] and w < 0: break
                if z > ImgBorders_z[1] and w > 0: break

                # compute distante to next voxel
                dist[0] = abs(((math.floor((x - SPR.origin[0]) / SPR.spacing[0]) + float(u > 0)) *
                               SPR.spacing[0] + SPR.origin[0] - x) / u)
                dist[1] = abs(((math.floor((y - SPR.origin[1]) / SPR.spacing[1]) + float(v > 0)) *
                               SPR.spacing[1] + SPR.origin[1] - y) / v)
                dist[2] = abs(((math.floor((z - SPR.origin[2]) / SPR.spacing[2]) + float(w > 0)) *
                               SPR.spacing[2] + SPR.origin[2] - z) / w)
                step = dist.min() + 1e-3

                voxel_SPR = SPR.get_SPR_at_position([x, y, z])

                WET += voxel_SPR * step
                x = x + step * u
                y = y + step * v
                z = z + step * w

            CartesianSpotPositions.append([x, y, z])

    return CartesianSpotPositions


def transport_spots_to_target(SPR, Target_mask, SpotGrid, direction):
    NumSpots = len(SpotGrid["x"])

    try:
        # import C library
        if platform.system() == "Linux":
            libRaytracing = ctypes.cdll.LoadLibrary(clibraries.__path__[0] + os.sep + "libRayTracing.so")
        elif platform.system() == "Windows":
            libRaytracing = ctypes.cdll.LoadLibrary(clibraries.__path__[0] + os.sep + "libRayTracing.dll")
        else:
            logger.error("Not compatible with " + platform.system() + " system.")
        float_array = np.ctypeslib.ndpointer(dtype=np.float32)
        int_array = np.ctypeslib.ndpointer(dtype=np.int32)
        bool_array = np.ctypeslib.ndpointer(dtype=np.bool)
        libRaytracing.transport_spots_to_target.argtypes = [float_array, bool_array, float_array, float_array,
                                                            int_array, float_array, float_array, float_array,
                                                            ctypes.c_int]
        libRaytracing.transport_spots_to_target.restype = ctypes.c_void_p

        # prepare inputs for C library
        Offset = np.array(SPR.origin, dtype=np.float32, order='C')
        PixelSpacing = np.array(SPR.spacing, dtype=np.float32, order='C')
        GridSize = np.array(SPR.gridSize, dtype=np.int32, order='C')
        positions = np.array([SpotGrid["x"], SpotGrid["y"], SpotGrid["z"]], dtype=np.float32, order='C').transpose(1, 0)
        positions = positions.reshape(NumSpots * 3, order='C')
        WETs = np.zeros(NumSpots, dtype=np.float32, order='C')
        direction = np.array(direction, dtype=np.float32, order='C')

        # call C function
        libRaytracing.transport_spots_to_target(SPR.imageArray.astype(np.float32),
                                                Target_mask.imageArray.astype(np.bool), Offset,
                                                PixelSpacing, GridSize, positions, WETs, direction, NumSpots)

        # post process results
        SpotGrid["WET"] = WETs.tolist()
        positions = positions.reshape((NumSpots, 3), order='C')
        SpotGrid["x"] = positions[:, 0].tolist()
        SpotGrid["y"] = positions[:, 1].tolist()
        SpotGrid["z"] = positions[:, 2].tolist()

    except:
        logger.warning('Accelerated raytracing not enabled. The python implementation is used instead')
        ImgBorders_x = [SPR.origin[0],
                        SPR.origin[0] + SPR.gridSize[0] * SPR.spacing[0]]
        ImgBorders_y = [SPR.origin[1],
                        SPR.origin[1] + SPR.gridSize[1] * SPR.spacing[1]]
        ImgBorders_z = [SPR.origin[2],
                        SPR.origin[2] + SPR.gridSize[2] * SPR.spacing[2]]

        # transport each spot until it reaches the target
        for s in range(NumSpots):
            SpotGrid["WET"].append(0.0)
            dist = np.array([1.0, 1.0, 1.0])
            while True:
                # check if we are still inside the CT image
                if SpotGrid["x"][s] < ImgBorders_x[0] and direction[0] < 0: SpotGrid["WET"][s] = -1; break
                if SpotGrid["x"][s] > ImgBorders_x[1] and direction[0] > 0: SpotGrid["WET"][s] = -1; break
                if SpotGrid["y"][s] < ImgBorders_y[0] and direction[1] < 0: SpotGrid["WET"][s] = -1; break
                if SpotGrid["y"][s] > ImgBorders_y[1] and direction[1] > 0: SpotGrid["WET"][s] = -1; break
                if SpotGrid["z"][s] < ImgBorders_z[0] and direction[2] < 0: SpotGrid["WET"][s] = -1; break
                if SpotGrid["z"][s] > ImgBorders_z[1] and direction[2] > 0: SpotGrid["WET"][s] = -1; break

                # check if we reached the target
                voxel = SPR.getVoxelIndexFromPosition([SpotGrid["x"][s], SpotGrid["y"][s], SpotGrid["z"][s]])
                if (voxel[0] >= 0 and voxel[1] >= 0 and voxel[2] >= 0 and voxel[0] < SPR.gridSize[0] and voxel[1] <
                        SPR.gridSize[1] and voxel[2] < SPR.gridSize[2]):
                    if Target_mask.imageArray[voxel[0], voxel[1], voxel[2]]: break

                # compute distante to next voxel
                dist[0] = abs(((math.floor(
                    (SpotGrid["x"][s] - SPR.origin[0]) / SPR.spacing[0]) + float(direction[0] > 0)) *
                               SPR.spacing[0] + SPR.origin[0] - SpotGrid["x"][s]) / direction[0])
                dist[1] = abs(((math.floor(
                    (SpotGrid["y"][s] - SPR.origin[1]) / SPR.spacing[1]) + float(direction[1] > 0)) *
                               SPR.spacing[1] + SPR.origin[1] - SpotGrid["y"][s]) / direction[1])
                dist[2] = abs(((math.floor(
                    (SpotGrid["z"][s] - SPR.origin[2]) / SPR.spacing[2]) + float(direction[2] > 0)) *
                               SPR.spacing[2] + SPR.origin[2] - SpotGrid["z"][s]) / direction[2])
                step = dist.min() + 1e-3

                voxel_SPR = SPR.get_SPR_at_position([SpotGrid["x"][s], SpotGrid["y"][s], SpotGrid["z"][s]])

                SpotGrid["WET"][s] += voxel_SPR * step
                SpotGrid["x"][s] = SpotGrid["x"][s] + step * direction[0]
                SpotGrid["y"][s] = SpotGrid["y"][s] + step * direction[1]
                SpotGrid["z"][s] = SpotGrid["z"][s] + step * direction[2]


def transport_spots_inside_target(SPR, Target_mask, SpotGrid, direction, minWET, LayerSpacing):
    NumSpots = len(SpotGrid["x"])

    try:
        # import C library
        if platform.system() == "Linux":
            libRaytracing = ctypes.cdll.LoadLibrary(clibraries.__path__[0] + os.sep + "libRayTracing.so")
        elif platform.system() == "Windows":
            libRaytracing = ctypes.cdll.LoadLibrary(clibraries.__path__[0] + os.sep + "libRayTracing.dll")
        else:
            logger.error("Not compatible with " + platform.system() + " system.")
        float_array = np.ctypeslib.ndpointer(dtype=np.float32)
        int_array = np.ctypeslib.ndpointer(dtype=np.int32)
        bool_array = np.ctypeslib.ndpointer(dtype=np.bool)
        libRaytracing.transport_spots_inside_target.argtypes = [float_array, bool_array, float_array, float_array,
                                                                int_array, float_array, float_array, float_array,
                                                                float_array, ctypes.c_int, ctypes.c_int, ctypes.c_float,
                                                                ctypes.c_float]
        libRaytracing.transport_spots_inside_target.restype = ctypes.c_void_p

        # prepare input for C library
        Offset = np.array(SPR.origin, dtype=np.float32, order='C')
        PixelSpacing = np.array(SPR.spacing, dtype=np.float32, order='C')
        GridSize = np.array(SPR.gridSize, dtype=np.int32, order='C')
        positions = np.array([SpotGrid["x"], SpotGrid["y"], SpotGrid["z"]], dtype=np.float32, order='C').transpose(1, 0)
        positions = positions.reshape(NumSpots * 3, order='C')
        WETs = np.array(SpotGrid["WET"], dtype=np.float32, order='C')
        direction = np.array(direction, dtype=np.float32, order='C')
        max_number_layers = round((550 - minWET) / LayerSpacing)
        Layers = -1.0 * np.ones(NumSpots * max_number_layers, dtype=np.float32, order='C')

        # call C function
        libRaytracing.transport_spots_inside_target(SPR.imageArray.astype(np.float32),
                                                    Target_mask.imageArray.astype(np.bool),
                                                    Offset,
                                                    PixelSpacing, GridSize, positions, WETs, Layers, direction,
                                                    NumSpots, max_number_layers, minWET, LayerSpacing)

        # post process results
        Layers = Layers.reshape((NumSpots, max_number_layers), order='C')
        for s in range(NumSpots):
            SpotGrid["EnergyLayers"].append([])
            layers = Layers[s, :]
            layers = layers[layers >= 0]
            for layer in layers:
                Energy = rangeToEnergy(layer / 10)
                SpotGrid["EnergyLayers"][s].append(Energy)

    except:
        logger.warning('Accelerated raytracing not enabled. The python implementation is used instead')
        ImgBorders_x = [SPR.origin[0],
                        SPR.origin[0] + SPR.gridSize[0] * SPR.spacing[0]]
        ImgBorders_y = [SPR.origin[1],
                        SPR.origin[1] + SPR.gridSize[1] * SPR.spacing[1]]
        ImgBorders_z = [SPR.origin[2],
                        SPR.origin[2] + SPR.gridSize[2] * SPR.spacing[2]]

        for s in range(NumSpots):
            SpotGrid["EnergyLayers"].append([])
            NumLayer = math.ceil((SpotGrid["WET"][s] - minWET) / LayerSpacing)
            Layer_WET = minWET + NumLayer * LayerSpacing
            dist = np.array([1.0, 1.0, 1.0])
            while True:
                # check if we are still inside the CT image
                if SpotGrid["x"][s] < ImgBorders_x[0] and direction[0] < 0: break
                if SpotGrid["x"][s] > ImgBorders_x[1] and direction[0] > 0: break
                if SpotGrid["y"][s] < ImgBorders_y[0] and direction[1] < 0: break
                if SpotGrid["y"][s] > ImgBorders_y[1] and direction[1] > 0: break
                if SpotGrid["z"][s] < ImgBorders_z[0] and direction[2] < 0: break
                if SpotGrid["z"][s] > ImgBorders_z[1] and direction[2] > 0: break

                # check if we reached the next layer
                if SpotGrid["WET"][s] >= Layer_WET:
                    voxel = SPR.getVoxelIndexFromPosition([SpotGrid["x"][s], SpotGrid["y"][s], SpotGrid["z"][s]])
                    if (voxel[0] >= 0 and voxel[1] >= 0 and voxel[2] >= 0 and voxel[0] < SPR.gridSize[0] and voxel[1] <
                            SPR.gridSize[1] and voxel[2] < SPR.gridSize[2]):
                        if Target_mask.imageArray[voxel[0], voxel[1], voxel[2]]:
                            Energy = rangeToEnergy(Layer_WET / 10)
                            SpotGrid["EnergyLayers"][s].append(Energy)

                    NumLayer += 1
                    Layer_WET = minWET + NumLayer * LayerSpacing

                # compute distante to next voxel
                dist[0] = abs(((math.floor(
                    (SpotGrid["x"][s] - SPR.origin[0]) / SPR.spacing[0]) + float(direction[0] > 0)) *
                               SPR.spacing[0] + SPR.origin[0] - SpotGrid["x"][s]) / direction[0])
                dist[1] = abs(((math.floor(
                    (SpotGrid["y"][s] - SPR.origin[1]) / SPR.spacing[1]) + float(direction[1] > 0)) *
                               SPR.spacing[1] + SPR.origin[1] - SpotGrid["y"][s]) / direction[1])
                dist[2] = abs(((math.floor(
                    (SpotGrid["z"][s] - SPR.origin[2]) / SPR.spacing[2]) + float(direction[2] > 0)) *
                               SPR.spacing[2] + SPR.origin[2] - SpotGrid["z"][s]) / direction[2])
                step = dist.min() + 1e-3

                voxel_SPR = SPR.get_SPR_at_position([SpotGrid["x"][s], SpotGrid["y"][s], SpotGrid["z"][s]])

                SpotGrid["WET"][s] += voxel_SPR * step
                SpotGrid["x"][s] = SpotGrid["x"][s] + step * direction[0]
                SpotGrid["y"][s] = SpotGrid["y"][s] + step * direction[1]
                SpotGrid["z"][s] = SpotGrid["z"][s] + step * direction[2]


global layer_maps
layer_maps = []


def transport_spots_inside_target_map(SPR, Target_mask, SpotGrid, direction, minWET, LayerSpacing):
    NumSpots = len(SpotGrid["x"])

    try:
        # import C library
        if platform.system() == "Linux":
            libRaytracing = ctypes.cdll.LoadLibrary(clibraries.__path__[0] + os.sep + "libRayTracing.so")
        elif platform.system() == "Windows":
            libRaytracing = ctypes.cdll.LoadLibrary(clibraries.__path__[0] + os.sep + "libRayTracing.dll")
        else:
            logger.error("Not compatible with " + platform.system() + " system.")
        float_array = np.ctypeslib.ndpointer(dtype=np.float32)
        int_array = np.ctypeslib.ndpointer(dtype=np.int32)
        bool_array = np.ctypeslib.ndpointer(dtype=np.bool)
        libRaytracing.transport_spots_inside_target.argtypes = [float_array, bool_array, float_array, float_array,
                                                                int_array, float_array, float_array, float_array,
                                                                float_array, ctypes.c_int, ctypes.c_int, ctypes.c_float,
                                                                ctypes.c_float]
        libRaytracing.transport_spots_inside_target.restype = ctypes.c_void_p

        # prepare input for C library
        Offset = np.array(SPR.origin, dtype=np.float32, order='C')
        PixelSpacing = np.array(SPR.spacing, dtype=np.float32, order='C')
        GridSize = np.array(SPR.gridSize, dtype=np.int32, order='C')
        positions = np.array([SpotGrid["x"], SpotGrid["y"], SpotGrid["z"]], dtype=np.float32, order='C').transpose(1, 0)
        positions = positions.reshape(NumSpots * 3, order='C')
        WETs = np.array(SpotGrid["WET"], dtype=np.float32, order='C')
        direction = np.array(direction, dtype=np.float32, order='C')
        max_number_layers = round((550 - minWET) / LayerSpacing)
        Layers = -1.0 * np.ones(NumSpots * max_number_layers, dtype=np.float32, order='C')

        # call C function
        libRaytracing.transport_spots_inside_target(SPR.Image.astype(np.float32), Target_mask.astype(np.bool), Offset,
                                                    PixelSpacing, GridSize, positions, WETs, Layers, direction,
                                                    NumSpots, max_number_layers, minWET, LayerSpacing)

        # post process results
        Layers = Layers.reshape((NumSpots, max_number_layers), order='C')
        for s in range(NumSpots):
            SpotGrid["EnergyLayers"].append([])
            layers = Layers[s, :]
            layers = layers[layers >= 0]
            for layer in layers:
                Energy = SPR.rangeToEnergy(layer / 10)
                SpotGrid["EnergyLayers"][s].append(Energy)

    except:
        logger.warning('Accelerated raytracing not enabled. The python implementation is used instead')
        ImgBorders_x = [SPR.origin[0],
                        SPR.origin[0] + SPR.gridSize[0] * SPR.spacing[0]]
        ImgBorders_y = [SPR.origin[1],
                        SPR.origin[1] + SPR.gridSize[1] * SPR.spacing[1]]
        ImgBorders_z = [SPR.origin[2],
                        SPR.origin[2] + SPR.gridSize[2] * SPR.spacing[2]]

        global layer_maps
        layer_maps.append(-1 * np.ones(SPR.imageArray.shape))

        for s in range(NumSpots):
            SpotGrid["EnergyLayers"].append([])
            NumLayer = math.ceil((SpotGrid["WET"][s] - minWET) / LayerSpacing)
            Layer_WET = minWET + NumLayer * LayerSpacing
            dist = np.array([1.0, 1.0, 1.0])
            while True:
                # check if we are still inside the CT image
                if SpotGrid["x"][s] < ImgBorders_x[0] and direction[0] < 0: break
                if SpotGrid["x"][s] > ImgBorders_x[1] and direction[0] > 0: break
                if SpotGrid["y"][s] < ImgBorders_y[0] and direction[1] < 0: break
                if SpotGrid["y"][s] > ImgBorders_y[1] and direction[1] > 0: break
                if SpotGrid["z"][s] < ImgBorders_z[0] and direction[2] < 0: break
                if SpotGrid["z"][s] > ImgBorders_z[1] and direction[2] > 0: break

                voxel = SPR.get_voxel_index([SpotGrid["x"][s], SpotGrid["y"][s], SpotGrid["z"][s]])
                if (voxel[0] >= 0 and voxel[1] >= 0 and voxel[2] >= 0 and voxel[0] < SPR.gridSize[0] and voxel[1] <
                        SPR.gridSize[1] and voxel[2] < SPR.gridSize[2]):
                    if Target_mask[voxel[1], voxel[0], voxel[2]]:
                        layer_maps[-1][voxel[1], voxel[0], voxel[2]] = NumLayer

                # check if we reached the next layer
                if SpotGrid["WET"][s] >= Layer_WET:
                    voxel = SPR.get_voxel_index([SpotGrid["x"][s], SpotGrid["y"][s], SpotGrid["z"][s]])
                    if (voxel[0] >= 0 and voxel[1] >= 0 and voxel[2] >= 0 and voxel[0] < SPR.gridSize[0] and voxel[1] <
                            SPR.gridSize[1] and voxel[2] < SPR.gridSize[2]):
                        if Target_mask.imageArray[voxel[0], voxel[1], voxel[2]]:
                            Energy = rangeToEnergy(Layer_WET / 10)
                            SpotGrid["EnergyLayers"][s].append(Energy)

                    NumLayer += 1
                    Layer_WET = minWET + NumLayer * LayerSpacing

                # compute distante to next voxel
                dist[0] = abs(((math.floor(
                    (SpotGrid["x"][s] - SPR.origin[0]) / SPR.spacing[0]) + float(direction[0] > 0)) *
                               SPR.spacing[0] + SPR.origin[0] - SpotGrid["x"][s]) / direction[0])
                dist[1] = abs(((math.floor(
                    (SpotGrid["y"][s] - SPR.origin[1]) / SPR.spacing[1]) + float(direction[1] > 0)) *
                               SPR.spacing[1] + SPR.origin[1] - SpotGrid["y"][s]) / direction[1])
                dist[2] = abs(((math.floor(
                    (SpotGrid["z"][s] - SPR.origin[2]) / SPR.spacing[2]) + float(direction[2] > 0)) *
                               SPR.spacing[2] + SPR.origin[2] - SpotGrid["z"][s]) / direction[2])
                step = dist.min() + 1e-3

                voxel_SPR = SPR.get_SPR_at_position([SpotGrid["x"][s], SpotGrid["y"][s], SpotGrid["z"][s]])

                SpotGrid["WET"][s] += voxel_SPR * step
                SpotGrid["x"][s] = SpotGrid["x"][s] + step * direction[0]
                SpotGrid["y"][s] = SpotGrid["y"][s] + step * direction[1]
                SpotGrid["z"][s] = SpotGrid["z"][s] + step * direction[2]

        # interpolate layer map between spots
        ind = nd.distance_transform_edt(layer_maps[-1] < 0, return_distances=False, return_indices=True)
        data = layer_maps[-1][tuple(ind)]
        data[~Target_mask] = -1
        # layer_maps[-1] = data
        layer_maps[-1] = data[Target_mask]
