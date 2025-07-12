/* make_poly.cpp */

/* Creates a poly-energetic kernel given the energy-binned beam fluence and 
kernels for all of the beam energies. */

#include "defs.h"

//fillers for these entries in kernel structure
#define UNCERT 1.0
#define MEAN_RADIUS 0.0
#define MEAN_ANGLE 0.0

extern char errstr[200];  // error string that all routines have access to

int make_poly_kernel(MONO_KERNELS *mono, KERNEL *poly)
{
 
// There is a problem with the first block of commented statements, likely a memory leak

 KERNEL_CATEGORIES category;
 int i, j, e;
 float sum;

 poly->nradii = N_KERNEL_RADII;
 poly->ntheta = N_KERNEL_ANGLES;
 
 poly->radial_boundary = (float *)malloc(poly->nradii*sizeof(float));
 poly->angular_boundary = (float *)malloc(poly->ntheta*sizeof(float));

 //copy radial boundaries from first mono kernel
 for (i=0;i<poly->nradii;i++)
  poly->radial_boundary[i] = mono->kernel[0].radial_boundary[i];

 //copy angular boundaries from first mono kernel
 for (i=0;i<poly->ntheta;i++)
  poly->angular_boundary[i] = mono->kernel[0].angular_boundary[i];

 for (i=0;i<N_KERNEL_CATEGORIES;i++)
  if ( (poly->matrix[i] =
   (float *) malloc(poly->ntheta*poly->nradii*sizeof(float))) == NULL)
   {
	sprintf(errstr,"Cannot allocate space for matrix %d\n",i);
	return(FAILURE);
   }
 if ( (poly->total_matrix =
   (float *) malloc(poly->ntheta*poly->nradii*sizeof(float))) == NULL)
   {
	sprintf(errstr,"Cannot allocate space for total matrix\n");
	return(FAILURE);
   } 

 for (j=0;j<poly->ntheta;j++)
  for (i=0;i<poly->nradii;i++)
  {
   KERNEL_TOTAL_VALUE(poly,i,j) = 0.0;

   //weight of each mono kernel value in sum is fluence*energy*mu
   category = primary_;
   KERNEL_VALUE(poly,category,i,j) = 0.0;
   sum = 0.0;
   for (e=0;e<mono->nkernels;e++)
   {
    KERNEL_VALUE(poly,category,i,j) += mono->fluence[e]*mono->energy[e]*mono->mu[e]
	                                  * KERNEL_VALUE(&(mono->kernel[e]),category,i,j); 
    sum += mono->fluence[e]*mono->energy[e]*mono->mu[e]; 
   }
   KERNEL_VALUE(poly,category,i,j) /= sum;
   KERNEL_TOTAL_VALUE(poly,i,j) += KERNEL_VALUE(poly,category,i,j);

   category = first_scatter_;
   KERNEL_VALUE(poly,category,i,j) = 0.0;
   sum = 0.0;
   for (e=0;e<mono->nkernels;e++)
   {
    KERNEL_VALUE(poly,category,i,j) += mono->fluence[e]*mono->energy[e]*mono->mu[e]
	                                  * KERNEL_VALUE(&(mono->kernel[e]),category,i,j); 
    sum += mono->fluence[e]*mono->energy[e]*mono->mu[e]; 
   }
   KERNEL_VALUE(poly,category,i,j) /= sum;
   KERNEL_TOTAL_VALUE(poly,i,j) += KERNEL_VALUE(poly,category,i,j);

   category = second_scatter_;
   KERNEL_VALUE(poly,category,i,j) = 0.0;
   sum = 0.0;
   for (e=0;e<mono->nkernels;e++)
   {
    KERNEL_VALUE(poly,category,i,j) += mono->fluence[e]*mono->energy[e]*mono->mu[e]
	                                  * KERNEL_VALUE(&(mono->kernel[e]),category,i,j); 
    sum += mono->fluence[e]*mono->energy[e]*mono->mu[e]; 
   }
   KERNEL_VALUE(poly,category,i,j) /= sum;
   KERNEL_TOTAL_VALUE(poly,i,j) += KERNEL_VALUE(poly,category,i,j);

   category = multiple_scatter_;
   KERNEL_VALUE(poly,category,i,j) = 0.0;
   sum = 0.0;
   for (e=0;e<mono->nkernels;e++)
   {
    KERNEL_VALUE(poly,category,i,j) += mono->fluence[e]*mono->energy[e]*mono->mu[e]
	                                  * KERNEL_VALUE(&(mono->kernel[e]),category,i,j); 
    sum += mono->fluence[e]*mono->energy[e]*mono->mu[e]; 
   }
   KERNEL_VALUE(poly,category,i,j) /= sum;
   KERNEL_TOTAL_VALUE(poly,i,j) += KERNEL_VALUE(poly,category,i,j);

   category = brem_annih_;
   KERNEL_VALUE(poly,category,i,j) = 0.0;
   sum = 0.0;
   for (e=0;e<mono->nkernels;e++)
   {
    KERNEL_VALUE(poly,category,i,j) += mono->fluence[e]*mono->energy[e]*mono->mu[e]
	                                  * KERNEL_VALUE(&(mono->kernel[e]),category,i,j); 
    sum += mono->fluence[e]*mono->energy[e]*mono->mu[e]; 
   }
   KERNEL_VALUE(poly,category,i,j) /= sum;
   KERNEL_TOTAL_VALUE(poly,i,j) += KERNEL_VALUE(poly,category,i,j);

  }

 return(SUCCESS);

}
