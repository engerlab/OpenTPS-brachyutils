/* calc_deff.cpp */

/* Calculates the effective depth of each voxel in the tumor mask. */

#include "defs.h"

extern char errstr[200];  // error string that all routines have access to

//prototype for Siddon raytrace routine (point to point)
int raytrace(FLOAT_GRID *,FLOAT_GRID *,POINT,POINT);

int calc_deff(FLOAT_GRID *dens, FLOAT_GRID *deff, FLOAT_GRID *terma_mask, BEAM *bm)
{
 int i, j, k;

 // points that will be used for raytrace operation
 POINT p1;
 POINT p2;  

 // Raytracing is only done for voxels that non-zero in the terma_mask.

 //initialize deff, with -1 signifying voxels of interest in the raytrace
 for (k=0;k<deff->z_count;k++)
  for (j=0;j<deff->y_count;j++)
   for (i=0;i<deff->x_count;i++)
    // we only care about voxels for which the terma_mask is positive
	if (GRID_VALUE(terma_mask,i,j,k) > 0)
		GRID_VALUE(deff,i,j,k) = -1.0;
 
     // Set the x-ray origin to the the source location 
     p1.x = bm->y_vec[0];
     p1.y = bm->y_vec[1];
     p1.z = bm->y_vec[2];

     // calculate the radiological depth for all voxels in the terma_mask

     for (k=0;k<deff->z_count;k++)
      for (j=0;j<deff->y_count;j++)
       for (i=0;i<deff->x_count;i++)
	    if (GRID_VALUE(deff,i,j,k) == -1.0)
		{
	       // The start location is the center of the voxel at (i,j,k).
	       // Since raytrace works with voxel sides rather than centers,
	       // need to shift the input by half a voxel in the negative 
	       // direction for each voxel dimension.

	       p2.x = deff->start.x + ((float) i)*deff->inc.x;
	       p2.y = deff->start.y + ((float) j)*deff->inc.y;
           p2.z = deff->start.z + ((float) k)*deff->inc.z;

		   // extend the ray by a factor of 10 to include more voxels in the raytrace
		   p2.x = p1.x + (p2.x-p1.x)*(float)10.0;
		   p2.y = p1.y + (p2.y-p1.y)*(float)10.0;
		   p2.z = p1.z + (p2.z-p1.z)*(float)10.0;

	       // do the raytrace, filling in voxels that are passed on the way
	       raytrace(dens,deff,p1,p2);
		} 

 return(SUCCESS);
}
