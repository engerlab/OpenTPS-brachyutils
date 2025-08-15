/* defs.h */

// libraries that will be needed throughout
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <malloc.h>

#define MAX_KERNELS 50	//max number of monoenergetic kernels to use for creating polyenergetic kernel
#define N_KERNEL_RADII 24  //number of radial increments in mono kernels 
#define N_KERNEL_ANGLES 48 //number of angular increments in mono kernels
#define N_KERNEL_CATEGORIES 5  //number of kernel categories (primary, first scatter...)

// upsample factors to determine insideness for voxels on aperture edge:
#define Mus  5
#define Nus  5
#define Qus  5

#define SUCCESS 1
#define FAILURE 0

#define doseCutoffThreshold 0.005 // doses less than this fraction of the maximum are cut off

#define RSAFE 2.0   // safety margin for dose_mask calculation in cm

#define PI 3.14152654

#define Y_DOSE_EXTENT 8.0  //optionally only calculate this many cm in y-direction (commented out in calc_dose)

#define NPHI 12  //number of azimuthal angles for convolution 
// #define DELR 0.4 //radial increments for convolution (adaptive to the problem now, in calc_dose)
#define NTHETA 6  //number of polar angles for convolution (must divide evenly into N_KERNEL_ANGLES)

/* #define NPHI 12	//number of azimuthal angles for convolution 
#define DELR 0.1 //radial increments for convolution
#define NTHETA 12  //number of polar angles for convolution (must divide evenly into N_KERNEL_ANGLES)  */

#define MAXX(x,y) ((x) > (y) ? (x) : (y))

//each kernel file contains 7 entries per voxel, the first five are these categores
typedef enum
{
 primary_,
 first_scatter_,
 second_scatter_,
 multiple_scatter_,
 brem_annih_
} KERNEL_CATEGORIES;

typedef struct
{
    float x;
    float y;
    float z;
} POINT;

//standard float precision grid structure, with dynamically allocated matrix 
//used for density, deff, terma, kerma, dose
typedef struct
{
    POINT start;
    POINT inc;
    int x_count;
    int y_count;
    int z_count;
    float *matrix;
} FLOAT_GRID;

//macro to access grid values
#define GRID_VALUE(GRID_ptr, i, j, k)\
    ((GRID_ptr)->matrix[(i) +\
                        (GRID_ptr)->x_count *\
                         ((j) + ((k) * (GRID_ptr)->y_count))])

// macro for 3D dot products
#define DOT3D(vec1,vec2) ((vec1[0])*(vec2[0])+(vec1[1])*(vec2[1])+(vec1[2])*(vec2[2]))

//kernel structure for each monoenergetic kernel and the polyenergetic kernel
typedef struct
{
 int nradii;
 int ntheta;
 float *radial_boundary;
 float *angular_boundary;
 float *matrix[N_KERNEL_CATEGORIES];  //kernel values for each category
 float *total_matrix;				   //sum of all categories (used for current convolution)
} KERNEL;

//macros for accessing kernel values
#define KERNEL_VALUE(kern_ptr,category,i,j) \
        (kern_ptr)->matrix[category][(i) + (j)*(kern_ptr)->nradii]
#define KERNEL_TOTAL_VALUE(kern_ptr,i,j) \
        (kern_ptr)->total_matrix[(i) + (j)*(kern_ptr)->nradii]

//infor and array of KERNEL structures for monoenergetic kernels 
typedef struct
{
 int nkernels;
 float *energy;
 float *fluence;
 float *mu;
 float *mu_en;
 KERNEL kernel[MAX_KERNELS];
} MONO_KERNELS;

//beam description (center and size)
typedef struct
{
 float ip[3];  // first aperture center vector
 float jp[3];  // second aperture center vector
 float kp[3];  // source direction vector
 float y_vec[3];   // source location vector

 // aperture parameters
 float xp;
 float yp;
 float del_xp;   // aperture width in ip direction
 float del_yp;   // aperture width in jp direction

 // source-axis distance (leave here for now because to ubiquitous)
 float SAD;

 // beam number to avoid ambiguity
 int num;
} BEAM;

/* Prototypes of utility functions */
float *fvector(int nl, int nh);
float **fmatrix(int nrl, int nrh, int ncl, int nch);

void free_fvector(float *v, int nl, int nh);
void free_fmatrix(float **m, int nrl, int nrh, int ncl, int nch);

int copy_grid_geometry(FLOAT_GRID *, FLOAT_GRID *);
int binSearch(float *, float, int);

void nrerror(char error_text[]);
