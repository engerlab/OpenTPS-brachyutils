#include <stdio.h>
#include <stdlib.h>
#include <math.h> 
#include <stdbool.h>
#include <omp.h>

#if defined(_MSC_VER)
  #define DLLEXPORT_TAG __declspec(dllexport)
#else
  #define DLLEXPORT_TAG
#endif

// function declarations
#if defined(_MSC_VER)
DLLEXPORT_TAG void raytrace_WET(float *SPR, bool *ROI_mask, float *WET, float *Offset, float *PixelSpacing, int *GridSize, float *beam_direction);
DLLEXPORT_TAG void compute_position_from_range(float *SPR, float *Offset, float *PixelSpacing, int *GridSize, float *positions, float *directions, float *ranges, int NumSpots);
DLLEXPORT_TAG void transport_spots_to_target(float *SPR, bool *Target_mask, float *Offset, float *PixelSpacing, int *GridSize, float *positions, float *WETs, float *direction, int NumSpots);
DLLEXPORT_TAG void transport_spots_inside_target(float *SPR, bool *Target_mask, float *Offset, float *PixelSpacing, int *GridSize, float *positions, float *WETs, float *Layers, float *direction, int NumSpots, int max_number_layers, float minWET, float LayerSpacing);
#endif

// function definitions
DLLEXPORT_TAG void raytrace_WET(float *SPR, bool *ROI_mask, float *WET, float *Offset, float *PixelSpacing, int *GridSize, float *beam_direction){
  float *Voxel_Coord_X = (float*) malloc(GridSize[0] * sizeof(float));
  float *Voxel_Coord_Y = (float*) malloc(GridSize[1] * sizeof(float));
  float *Voxel_Coord_Z = (float*) malloc(GridSize[2] * sizeof(float));
  for(int i=0; i<GridSize[0]; i++) Voxel_Coord_X[i] = Offset[0] + i * PixelSpacing[0];
  for(int i=0; i<GridSize[1]; i++) Voxel_Coord_Y[i] = Offset[1] + i * PixelSpacing[1];
  for(int i=0; i<GridSize[2]; i++) Voxel_Coord_Z[i] = Offset[2] + i * PixelSpacing[2];
  
  float u = -beam_direction[0];
  float v = -beam_direction[1];
  float w = -beam_direction[2];

  for(int i=0; i<GridSize[0]; i++){
    for(int j=0; j<GridSize[1]; j++){
      #pragma omp parallel for
      for(int k=0; k<GridSize[2]; k++){

        int id_vox = k + GridSize[2] * (j + GridSize[1]*i); //order='C'
        if(ROI_mask[id_vox] == 0) continue;

        // initialize raytracing for voxel ijk
        float x = Voxel_Coord_X[i] + 0.5*PixelSpacing[0];
        float y = Voxel_Coord_Y[j] + 0.5*PixelSpacing[1];
        float z = Voxel_Coord_Z[k] + 0.5*PixelSpacing[2];
        float dist[3] = {1.0, 1.0, 1.0};
        float voxel_SPR, step;
        int id_x, id_y, id_z, id_SPR;

        // raytracing loop
        while(true){
          // check if we are still inside the SPR image
          if(x < Voxel_Coord_X[0] && u < 0) break;
          if(x > Voxel_Coord_X[GridSize[0]-1] && u > 0) break;
          if(y < Voxel_Coord_Y[0] && v < 0) break;
          if(y > Voxel_Coord_Y[GridSize[1]-1] && v > 0) break;
          if(z < Voxel_Coord_Z[0] && w < 0) break;
          if(z > Voxel_Coord_Z[GridSize[2]-1] && w > 0) break;

          // compute distante to next voxel
          dist[0] = fabs(((floor((x-Offset[0])/PixelSpacing[0]) + (u>0)) * PixelSpacing[0] + Offset[0] - x)/u);
          dist[1] = fabs(((floor((y-Offset[1])/PixelSpacing[1]) + (v>0)) * PixelSpacing[1] + Offset[1] - y)/v);
          dist[2] = fabs(((floor((z-Offset[2])/PixelSpacing[2]) + (w>0)) * PixelSpacing[2] + Offset[2] - z)/w);
          step = fmin(dist[0], fmin(dist[1], dist[2])) + 1e-3;

          // compute voxel index from position
          id_x = floor((x - Offset[0]) / PixelSpacing[0]);
          id_y = floor((y - Offset[1]) / PixelSpacing[1]);
          id_z = floor((z - Offset[2]) / PixelSpacing[2]);
          id_SPR = id_z + GridSize[2] * (id_y + GridSize[1]*id_x); //order='C'
      
          // accumulate WET
          voxel_SPR = SPR[id_SPR];
          WET[id_vox] += voxel_SPR * step;

          // update position
          x = x + step * u;
          y = y + step * v;
          z = z + step * w;

        }
      }
    }
  }

  free(Voxel_Coord_X);
  free(Voxel_Coord_Y);
  free(Voxel_Coord_Z);

}


DLLEXPORT_TAG void compute_position_from_range(float *SPR, float *Offset, float *PixelSpacing, int *GridSize, float *positions, float *directions, float *ranges, int NumSpots){

  float ImgBorders_x[2], ImgBorders_y[2], ImgBorders_z[2];
  ImgBorders_x[0] = Offset[0];
  ImgBorders_x[1] = Offset[0] + GridSize[0] * PixelSpacing[0];
  ImgBorders_y[0] = Offset[1];
  ImgBorders_y[1] = Offset[1] + GridSize[1] * PixelSpacing[1];
  ImgBorders_z[0] = Offset[2];
  ImgBorders_z[1] = Offset[2] + GridSize[2] * PixelSpacing[2];

  #pragma omp parallel for
  for(int s=0; s<NumSpots; s++){
  	float x = positions[s*3+0];
  	float y = positions[s*3+1];
  	float z = positions[s*3+2];
  	float u = directions[s*3+0];
  	float v = directions[s*3+1];
  	float w = directions[s*3+2];
  	float range_in_water = ranges[s];

  	float WET = 0.0;
  	float dist[3] = {1.0, 1.0, 1.0};
  	float step, voxel_SPR;
  	int id_x, id_y, id_z, id_vox;

  	while(WET < range_in_water){
  		// check if we are still inside the SPR image
  		if(x < ImgBorders_x[0] && u < 0) break;
  		if(x > ImgBorders_x[1] && u > 0) break;
  		if(y < ImgBorders_y[0] && v < 0) break;
  		if(y > ImgBorders_y[1] && v > 0) break;
  		if(z < ImgBorders_z[0] && w < 0) break;
  		if(z > ImgBorders_z[1] && w > 0) break;

  		// compute distante to next voxel
  		dist[0] = fabs(((floor((x-Offset[0])/PixelSpacing[0]) + (u>0)) * PixelSpacing[0] + Offset[0] - x)/u);
  		dist[1] = fabs(((floor((y-Offset[1])/PixelSpacing[1]) + (v>0)) * PixelSpacing[1] + Offset[1] - y)/v);
  		dist[2] = fabs(((floor((z-Offset[2])/PixelSpacing[2]) + (w>0)) * PixelSpacing[2] + Offset[2] - z)/w);
  		step = fmin(dist[0], fmin(dist[1], dist[2])) + 1e-3;

  		// compute voxel index from position
  		id_x = floor((x - Offset[0]) / PixelSpacing[0]);
      id_y = floor((y - Offset[1]) / PixelSpacing[1]);
      id_z = floor((z - Offset[2]) / PixelSpacing[2]);
      id_vox = id_z + GridSize[2] * (id_y + GridSize[1]*id_x); //order='C'
      
  		voxel_SPR = SPR[id_vox];
        
  		WET += voxel_SPR * step;
  		x = x + step * u;
  		y = y + step * v;
  		z = z + step * w;
  	}

  	positions[s*3+0] = x;
  	positions[s*3+1] = y;
  	positions[s*3+2] = z;
  }
}



DLLEXPORT_TAG void transport_spots_to_target(float *SPR, bool *Target_mask, float *Offset, float *PixelSpacing, int *GridSize, float *positions, float *WETs, float *direction, int NumSpots){
  
  int NumVox = GridSize[0]*GridSize[1]*GridSize[2];
  float ImgBorders_x[2], ImgBorders_y[2], ImgBorders_z[2];
  ImgBorders_x[0] = Offset[0];
  ImgBorders_x[1] = Offset[0] + GridSize[0] * PixelSpacing[0];
  ImgBorders_y[0] = Offset[1];
  ImgBorders_y[1] = Offset[1] + GridSize[1] * PixelSpacing[1];
  ImgBorders_z[0] = Offset[2];
  ImgBorders_z[1] = Offset[2] + GridSize[2] * PixelSpacing[2];

  //#pragma omp parallel for
  for(int s=0; s<NumSpots; s++){
  	float x = positions[s*3+0];
  	float y = positions[s*3+1];
  	float z = positions[s*3+2];

  	float dist[3] = {1.0, 1.0, 1.0};
  	float step, voxel_SPR;
  	int id_x, id_y, id_z, id_vox;

  	while(true){
  		// check if we are still inside the SPR image
  		if(x < ImgBorders_x[0] && direction[0] < 0){ WETs[s]=-1; break; }
  		if(x > ImgBorders_x[1] && direction[0] > 0){ WETs[s]=-1; break; }
  		if(y < ImgBorders_y[0] && direction[1] < 0){ WETs[s]=-1; break; }
  		if(y > ImgBorders_y[1] && direction[1] > 0){ WETs[s]=-1; break; }
  		if(z < ImgBorders_z[0] && direction[2] < 0){ WETs[s]=-1; break; }
  		if(z > ImgBorders_z[1] && direction[2] > 0){ WETs[s]=-1; break; }

  		// compute voxel index from position
  		id_x = floor((x - Offset[0]) / PixelSpacing[0]);
      id_y = floor((y - Offset[1]) / PixelSpacing[1]);
      id_z = floor((z - Offset[2]) / PixelSpacing[2]);
      id_vox = id_z + GridSize[2] * (id_y + GridSize[1]*id_x); //order='C'

      // check if we reached the target
      if(id_vox > 0 && id_vox < NumVox){
        if(Target_mask[id_vox]) break;
      }

      // compute distante to next voxel
  		dist[0] = fabs(((floor((x-Offset[0])/PixelSpacing[0]) + (direction[0]>0)) * PixelSpacing[0] + Offset[0] - x)/direction[0]);
  		dist[1] = fabs(((floor((y-Offset[1])/PixelSpacing[1]) + (direction[1]>0)) * PixelSpacing[1] + Offset[1] - y)/direction[1]);
  		dist[2] = fabs(((floor((z-Offset[2])/PixelSpacing[2]) + (direction[2]>0)) * PixelSpacing[2] + Offset[2] - z)/direction[2]);
  		step = fmin(dist[0], fmin(dist[1], dist[2])) + 1e-3;

      if(id_vox > 0 && id_vox < NumVox) voxel_SPR = SPR[id_vox];
      else voxel_SPR = 0.001;
        
  		WETs[s] += voxel_SPR * step;
  		x = x + step * direction[0];
  		y = y + step * direction[1];
  		z = z + step * direction[2];

  	}

  	positions[s*3+0] = x;
  	positions[s*3+1] = y;
  	positions[s*3+2] = z;
  }

}



DLLEXPORT_TAG void transport_spots_inside_target(float *SPR, bool *Target_mask, float *Offset, float *PixelSpacing, int *GridSize, float *positions, float *WETs, float *Layers, float *direction, int NumSpots, int max_number_layers, float minWET, float LayerSpacing){
  
  int NumVox = GridSize[0]*GridSize[1]*GridSize[2];
  float ImgBorders_x[2], ImgBorders_y[2], ImgBorders_z[2];
  ImgBorders_x[0] = Offset[0];
  ImgBorders_x[1] = Offset[0] + GridSize[0] * PixelSpacing[0];
  ImgBorders_y[0] = Offset[1];
  ImgBorders_y[1] = Offset[1] + GridSize[1] * PixelSpacing[1];
  ImgBorders_z[0] = Offset[2];
  ImgBorders_z[1] = Offset[2] + GridSize[2] * PixelSpacing[2];

  //#pragma omp parallel for
  for(int s=0; s<NumSpots; s++){
  	float x = positions[s*3+0];
  	float y = positions[s*3+1];
  	float z = positions[s*3+2];

    int NumLayer = ceil((WETs[s] - minWET) / LayerSpacing);
    float Layer_WET = minWET + NumLayer * LayerSpacing;

  	float dist[3] = {1.0, 1.0, 1.0};
  	float step, voxel_SPR;
  	int id_x, id_y, id_z, id_vox, id_layer;
  	int count = 0;

  	while(true){
  		// check if we are still inside the SPR image
  		if(x < ImgBorders_x[0] && direction[0] < 0) break;
  		if(x > ImgBorders_x[1] && direction[0] > 0) break;
  		if(y < ImgBorders_y[0] && direction[1] < 0) break;
  		if(y > ImgBorders_y[1] && direction[1] > 0) break;
  		if(z < ImgBorders_z[0] && direction[2] < 0) break;
  		if(z > ImgBorders_z[1] && direction[2] > 0) break;

  		// compute voxel index from position
  		id_x = floor((x - Offset[0]) / PixelSpacing[0]);
      id_y = floor((y - Offset[1]) / PixelSpacing[1]);
      id_z = floor((z - Offset[2]) / PixelSpacing[2]);
      id_vox = id_z + GridSize[2] * (id_y + GridSize[1]*id_x); //order='C'

      if(id_vox < 0 || id_vox >= NumVox) break;

  		// check if we reached the next layer
      if(WETs[s] >= Layer_WET){
      	// check if we are still inside the target
        if(Target_mask[id_vox]){
          id_layer = s*max_number_layers + count;
          Layers[id_layer] = Layer_WET;
          count++;
        }
        NumLayer++;
        Layer_WET = minWET + NumLayer * LayerSpacing;
      }

      // compute distante to next voxel
  		dist[0] = fabs(((floor((x-Offset[0])/PixelSpacing[0]) + (direction[0]>0)) * PixelSpacing[0] + Offset[0] - x)/direction[0]);
  		dist[1] = fabs(((floor((y-Offset[1])/PixelSpacing[1]) + (direction[1]>0)) * PixelSpacing[1] + Offset[1] - y)/direction[1]);
  		dist[2] = fabs(((floor((z-Offset[2])/PixelSpacing[2]) + (direction[2]>0)) * PixelSpacing[2] + Offset[2] - z)/direction[2]);
  		step = fmin(dist[0], fmin(dist[1], dist[2])) + 1e-3;

  		voxel_SPR = SPR[id_vox];
        
  		WETs[s] += voxel_SPR * step;
  		x = x + step * direction[0];
  		y = y + step * direction[1];
  		z = z + step * direction[2];

  	}

  	positions[s*3+0] = x;
  	positions[s*3+1] = y;
  	positions[s*3+2] = z;
  }

}