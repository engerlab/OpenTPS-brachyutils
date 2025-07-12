/* terma_kerma.cpp */

/* Calculates the terma and the kerma of every voxel in the terma_mask.  */

#include "defs.h"

extern char errstr[200];  // error string that all routines have access to

int terma_kerma(FLOAT_GRID *deff, FLOAT_GRID *terma, FLOAT_GRID *kermac,
				MONO_KERNELS *mono, FLOAT_GRID *terma_mask)
{													 
 // insideness is accounted for with terma_mask
 int i, j, k, e;
 float kermac0, terma0;

 //calculate T and Kc at zero depth for use in hardening correction
 //see Hoban et al 1994 (PMB)
 kermac0 = terma0 = 0.0;
 for (e=0;e<mono->nkernels;e++)
 {
   kermac0 = mono->fluence[e]*mono->energy[e]*mono->mu_en[e];
   terma0 = mono->fluence[e]*mono->energy[e]*mono->mu[e];
 }

 for (j=0;j<deff->y_count;j++)
  for (k=0;k<deff->z_count;k++)
   for (i=0;i<deff->x_count;i++)
    if (GRID_VALUE(terma_mask,i,j,k) > 0)
    {
	  // The amount of each voxel that is inside the field (insideness) was
	  // was accounted in the calculation of the terma_mask

	  //sum terma and collision kerma over each energy in spectrum 
	  // (stored in mono kernel structure)
	  for (e=0;e<mono->nkernels;e++)
	  {
       GRID_VALUE(terma,i,j,k) += mono->fluence[e]*mono->energy[e]*mono->mu[e]
                              * exp(-mono->mu[e]*GRID_VALUE(deff,i,j,k));
       GRID_VALUE(kermac,i,j,k) += mono->fluence[e]*mono->energy[e]*mono->mu_en[e]
                              * exp(-mono->mu[e]*GRID_VALUE(deff,i,j,k));
	  }
	  
	  //adjust terma and collision kerma according to insideness
	  GRID_VALUE(terma,i,j,k) *= GRID_VALUE(terma_mask,i,j,k);
	  GRID_VALUE(kermac,i,j,k) *= GRID_VALUE(terma_mask,i,j,k);

	  // beam hardening correction
	  if (terma0 <= 0.0 || kermac0 <= 0.0)
		nrerror("Input spectrum must not sum to zero."); 
	  else
		GRID_VALUE(terma,i,j,k) *= (GRID_VALUE(kermac,i,j,k)/GRID_VALUE(terma,i,j,k))
								/(kermac0/terma0);
	}
	else
	{
		GRID_VALUE(terma,i,j,k) = 0.0;
		GRID_VALUE(kermac,i,j,k) = 0.0;
	}
    return(SUCCESS);
}
