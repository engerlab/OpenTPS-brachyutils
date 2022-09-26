#include <stdio.h>
#include <stdlib.h>
#include <math.h> 
#include <omp.h>

#if defined(_MSC_VER)
  #define DLLEXPORT_TAG __declspec(dllexport)
#else
  #define DLLEXPORT_TAG
#endif

// function declarations
DLLEXPORT_TAG void Trilinear_Interpolation(float *Image, int *GridSize, float *InterpolatedPoints, int NumPoints, float fill_value, float *Intepolated_img);


// function definitions
DLLEXPORT_TAG void Trilinear_Interpolation(float *Image, int *GridSize, float *InterpolatedPoints, int NumPoints, float fill_value, float *Intepolated_img){

  #pragma omp parallel for
  for(int p=0; p<NumPoints; p++){

    int Id_x, Id_y, Id_z, Id1, Id2;
    float C00, C10, C01, C11, C0, C1;

    Id_x = floor(InterpolatedPoints[3*p+0]);
    Id_y = floor(InterpolatedPoints[3*p+1]);
    Id_z = floor(InterpolatedPoints[3*p+2]);

    if(Id_x < 0 || Id_x >= GridSize[0] || Id_y < 0 || Id_y >= GridSize[1] || Id_z < 0 || Id_z >= GridSize[2]){
      Intepolated_img[p] = fill_value;
    }
    else{

      if(Id_x > GridSize[0]-2) Id_x = GridSize[0]-2;
      if(Id_y > GridSize[1]-2) Id_y = GridSize[1]-2;
      if(Id_z > GridSize[2]-2) Id_z = GridSize[2]-2;

      // voxel coordinates corresponding to order='C'
      Id1 = (Id_z) + GridSize[2] * ((Id_y) + GridSize[1]*(Id_x));
      Id2 = (Id_z) + GridSize[2] * ((Id_y) + GridSize[1]*(Id_x+1));
      C00 = (Image[Id2] - Image[Id1]) * (InterpolatedPoints[3*p+0] - Id_x) + Image[Id1];

      Id1 = (Id_z) + GridSize[2] * ((Id_y+1) + GridSize[1]*(Id_x));
      Id2 = (Id_z) + GridSize[2] * ((Id_y+1) + GridSize[1]*(Id_x+1));
      C10 = (Image[Id2] - Image[Id1]) * (InterpolatedPoints[3*p+0] - Id_x) + Image[Id1];

      Id1 = (Id_z+1) + GridSize[2] * ((Id_y) + GridSize[1]*(Id_x));
      Id2 = (Id_z+1) + GridSize[2] * ((Id_y) + GridSize[1]*(Id_x+1));
      C01 = (Image[Id2] - Image[Id1]) * (InterpolatedPoints[3*p+0] - Id_x) + Image[Id1];

      Id1 = (Id_z+1) + GridSize[2] * ((Id_y+1) + GridSize[1]*(Id_x));
      Id2 = (Id_z+1) + GridSize[2] * ((Id_y+1) + GridSize[1]*(Id_x+1));
      C11 = (Image[Id2] - Image[Id1]) * (InterpolatedPoints[3*p+0] - Id_x) + Image[Id1];

      C0 = (C10 - C00) * (InterpolatedPoints[3*p+1] - Id_y) + C00;
      C1 = (C11 - C01) * (InterpolatedPoints[3*p+1] - Id_y) + C01;

      Intepolated_img[p] = (C1 - C0) * (InterpolatedPoints[3*p+2] - Id_z) + C0;
    }
  }
  

}