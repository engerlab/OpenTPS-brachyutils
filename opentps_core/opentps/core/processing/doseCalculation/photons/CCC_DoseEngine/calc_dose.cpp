/* calc_dose.cpp */

/* The dose at all voxels in the grid dose_mask is calculated using a convolution
method that uses a polyenergetic kernel. Inhomogeneities are accounted for by kernel
scaling, and an inverse square correction is applied after the convolution of the terma
grid with the kernel, rather than being applied directly to the terma grid before
the convolution. */

#include <stdio.h>
#include <stdlib.h>
#include <malloc.h>
#include <math.h>
#include <string.h>
#include "defs.h"

extern char errstr[200];  // error string that all routines have access to

int calc_dose(FLOAT_GRID *density, FLOAT_GRID *terma,FLOAT_GRID *dose, KERNEL *kern, 
			  BEAM *bm, FLOAT_GRID *dose_mask)
{
 int i, j, k, l;
 int p, q, r;
 int M, N, Q;  // dimensions of CT array
 int inter_i, inter_j, inter_k;
 int r_index;
 int baseindex;
 float SAD;
 float del_x, del_y, del_z;
 float current_x, current_y, current_z;
 float inter_x, inter_y, inter_z;
 float r_eff, delr_eff, inter_r_eff;
 float kval;
 float cumval, last_cumval;
 float length;
 float *ip, *jp, *kp;
 float dx, dy, dz;
 float delr;  // convolution step size
 float t, u, v, f;
 float *x, *y, *z;  // vectors of CT coordinates
 float *phi, *theta, *sinphi, *cosphi, *sintheta, *costheta;
 float one;
 float rho;

 one = (float)1.0; 

 // copy CT dimensions and voxel sizes for shorter references later
 M = density->x_count;
 N = density->y_count;
 Q = density->z_count;

 dx = density->inc.x;
 dy = density->inc.y;
 dz = density->inc.z;

 // copy vectors describing the beam's eye view coordinate system as well
 ip = fvector(0,2);   // ip and jp span the beam's eye view
 jp = fvector(0,2);
 kp = fvector(0,2);   // beam direction
 
 // create the unit vector describing the beam direction
 for (j=0;j<3;j++) ip[j] = bm->ip[j];
 for (j=0;j<3;j++) jp[j] = bm->jp[j];
 for (j=0;j<3;j++) kp[j] = bm->kp[j];

 // vectors describing the location of each voxel
 x = fvector(0,M-1);
 y = fvector(0,N-1);
 z = fvector(0,Q-1);

 // lookup table for vectors in polar coordinates
 phi = fvector(0,NPHI-1);
 theta = fvector(0,NTHETA-1);
 sinphi = fvector(0,NPHI-1);
 cosphi = fvector(0,NPHI-1);
 sintheta = fvector(0,NTHETA-1);
 costheta = fvector(0,NTHETA-1);

 //kernel with fewer elements for faster calculation
 //see defs.h
 KERNEL smallkern;
 smallkern.radial_boundary = (float *)malloc(kern->nradii*sizeof(float));
 smallkern.angular_boundary = (float *)malloc(kern->ntheta*sizeof(float));
 //small kernel dimensions
 smallkern.nradii = N_KERNEL_RADII;	 //same as original kernel
 smallkern.ntheta = NTHETA;	//must divide evenly into N_KERNEL_ANGLES

 SAD = bm->SAD;
 
 for (i=0;i<N_KERNEL_CATEGORIES;i++)
  if ( (smallkern.matrix[i] =
   (float *) calloc(smallkern.ntheta*smallkern.nradii,sizeof(float))) == NULL)
   {
	sprintf(errstr,"Cannot allocate space for matrix %d\n",i);
	return(FAILURE);
   }
 
 if ( (smallkern.total_matrix =
   (float *) calloc(smallkern.ntheta*smallkern.nradii,sizeof(float))) == NULL)
   {
	sprintf(errstr,"Cannot allocate space for total matrix\n");
	return(FAILURE);
   }
  
 //set up boundaries
 for (i=0;i<smallkern.ntheta;i++)
  smallkern.angular_boundary[i]	= ( (float) i + 1) * (float)180.0/(float) smallkern.ntheta;
 for (i=0;i<smallkern.nradii;i++)
  smallkern.radial_boundary[i] = kern->radial_boundary[i];
  
 //initialise 
  for (i=0;i<smallkern.nradii;i++)
   for (j=0;j<smallkern.ntheta;j++)
   {
    KERNEL_TOTAL_VALUE(&smallkern,i,j) = (float)0.0;
    for (l=0;l<N_KERNEL_CATEGORIES;l++)
      KERNEL_VALUE(&smallkern,l,i,j) = (float)0.0;
   }

 //create kernel values
 for (i=0;i<smallkern.nradii;i++)
  for (j=0;j<smallkern.ntheta;j++)
  {   
   //first angular index in original kernel for this element 
   baseindex = j*N_KERNEL_ANGLES/NTHETA;
   //for each category, sum values from original kernel 
   for (l=0;l<N_KERNEL_CATEGORIES;l++)
    for (k=0;k<N_KERNEL_ANGLES/NTHETA;k++)
     KERNEL_VALUE(&smallkern,l,i,j) += KERNEL_VALUE(kern,l,i,baseindex+k);
   //and for total kernel
   for (k=0;k<N_KERNEL_ANGLES/NTHETA;k++)
    KERNEL_TOTAL_VALUE(&smallkern,i,j) += KERNEL_TOTAL_VALUE(kern,i,baseindex+k);
  }
 
 //Make cumulative kernel (with radius)
 //this is what is used for the dose calculation 
 for (p=0;p<smallkern.ntheta;p++)
  for (r=0;r<smallkern.nradii;r++)
  { 
   for (i=0;i<N_KERNEL_CATEGORIES;i++)
    if (r > 0)
     KERNEL_VALUE(&smallkern,i,r,p)
     = KERNEL_VALUE(&smallkern,i,r-1,p) + KERNEL_VALUE(&smallkern,i,r,p);
   if (r > 0)
    KERNEL_TOTAL_VALUE(&smallkern,r,p)
    = KERNEL_TOTAL_VALUE(&smallkern,r-1,p) + KERNEL_TOTAL_VALUE(&smallkern,r,p);
  }

  // fill the coordinate vectors
 for (i=0;i<M;i++) x[i] = density->start.x + (float)i*dx;
 for (j=0;j<N;j++) y[j] = density->start.y + (float)j*dy;
 for (k=0;k<Q;k++) z[k] = density->start.z + (float)k*dz;

 // fill in the polar coordinates vectors
 for (q=0;q<NPHI;q++) 
 {
	 phi[q] = ((float)q + (float)0.5)*(float)2.0*(float)PI/(float)NPHI;
	 sinphi[q] = (float)sin(phi[q]);
	 cosphi[q] = (float)cos(phi[q]);
 }

 // Theta is subtracted from PI is because direction of travel along kernel ray is actually opposite of 
 // direction along which energy is radiating, so need to use a source voxel direction that 
 // is reflected about horizontal.  This can be thought of as the kernel inversion line.

 for (p=0;p<smallkern.ntheta;p++)
  if (p == 0)
  {
   theta[p] = (float)0.5*smallkern.angular_boundary[0]*(float)PI/(float)180.0;
   sintheta[p] = (float)sin((float)PI - theta[p]);
   costheta[p] = (float)cos((float)PI - theta[p]);
  }
  else
  {
   theta[p] = (float)0.5*(smallkern.angular_boundary[p-1] + smallkern.angular_boundary[p])*(float)PI/(float)180.0;
   sintheta[p] = (float)sin((float)PI - theta[p]);
   costheta[p] = (float)cos((float)PI - theta[p]);
  }
 
 // store the sines and cosines in a lookup table

 // the step size for the convolution integration is the smallest voxel side length
 if (dx <= dy && dx <= dz)
	 delr = (float)2.0*dx;
 else if (dy <= dx && dy <= dz)
	 delr = (float)2.0*dy;
 else
	 delr = (float)2.0*dz;

 //calculate dose at each point
 //done from deposition (catcher's) point of view
 for (k=0;k<Q; k++)
  for (j=0;j<N; j++)
   for (i=0;i<M; i++)
	if (GRID_VALUE(dose_mask,i,j,k) > 0)  // only calculate dose inside dose mask
	{
	// do the integral for the point in the ROI
	for (p=0;p<smallkern.ntheta;p++) //polar
	 for (q=0;q<NPHI;q++) //azimuthal
	 {
	  //initialise position of current voxel
	  current_x = x[i];
	  current_y = y[j];
	  current_z = z[k];

	  //initialise effective radius along kernel direction
	  r_eff = 0.0;
	  //initialise cumulative kernel value for this direction
	  last_cumval = 0.0;

      //Using reciprocity technique where dose at point A due to point B
	  //is dose at point B due to point A 

      //x ,y, z increments along ray
	  del_x = delr*(ip[0]*cosphi[q]*sintheta[p] + jp[0]*sinphi[q]*sintheta[p]
			      + kp[0]*costheta[p]);
	  del_y = delr*(ip[1]*cosphi[q]*sintheta[p] + jp[1]*sinphi[q]*sintheta[p]
			      + kp[1]*costheta[p]);
	  del_z = delr*(ip[2]*cosphi[q]*sintheta[p] + jp[2]*sinphi[q]*sintheta[p]
			      + kp[2]*costheta[p]);

	  //initialise physical radius
	  r = 0;
	  do
	  {
	    //interaction point is at mid-point of curent increment
	    inter_x = current_x + (float)0.5*del_x;
	    inter_y = current_y + (float)0.5*del_y;
	    inter_z = current_z + (float)0.5*del_z;

	    //voxel containing interaction point
	    inter_i = (int) ((inter_x - density->start.x)/dx);
	    inter_j = (int) ((inter_y - density->start.y)/dy);
	    inter_k = (int) ((inter_z - density->start.z)/dz);
	   
	   // stop the integral if interaction point is outside the dose calculation limits
	   if (    (inter_i < 0) || (inter_i + 1 >= M)
	        || (inter_j < 0) || (inter_j + 1 >= N)
	   	    || (inter_k < 0) || (inter_k + 1 >= Q)
			|| (GRID_VALUE(dose_mask,inter_i,inter_j,inter_k) <= 0.0))
		  break;

	   	// Position of the end of the increment.  Interaction point is at the
	    // midpoint.
        current_x += del_x;
	    current_y += del_y;
	    current_z += del_z;
        
        //effective distance increment
        delr_eff = delr*GRID_VALUE(density,inter_i,inter_j,inter_k);
		//effective radius of interaction point
		inter_r_eff = r_eff + (float)0.5*delr_eff;
	    r_eff += delr_eff;

		// trilinear interpolation method of the terma contribution, f

		// relative differences between the interaction point and the lower voxel bound
		t = (inter_x - x[inter_i])/dx;
		u = (inter_y - y[inter_j])/dy;
		v = (inter_z - z[inter_k])/dz; 

		f = GRID_VALUE(terma,inter_i,inter_j,inter_k)*(one-t)*(one-u)*(one-v)
		  + GRID_VALUE(terma,inter_i,inter_j,inter_k+1)*(one-t)*(one-u)*v
		  + GRID_VALUE(terma,inter_i,inter_j+1,inter_k+1)*(one-t)*u*v
		  + GRID_VALUE(terma,inter_i+1,inter_j+1,inter_k+1)*t*u*v
		  + GRID_VALUE(terma,inter_i,inter_j+1,inter_k)*(one-t)*u*(one-v)
		  + GRID_VALUE(terma,inter_i+1,inter_j+1,inter_k)*t*u*(one-v)
		  + GRID_VALUE(terma,inter_i+1,inter_j,inter_k+1)*t*(one-u)*v
		  + GRID_VALUE(terma,inter_i+1,inter_j,inter_k)*t*(one-u)*(one-v); 

		/* 
		// interpolate density at the interaction point
		rho = GRID_VALUE(density,inter_i,inter_j,inter_k)*(one-t)*(one-u)*(one-v)
		    + GRID_VALUE(density,inter_i,inter_j,inter_k+1)*(one-t)*(one-u)*v
		    + GRID_VALUE(density,inter_i,inter_j+1,inter_k+1)*(one-t)*u*v
		    + GRID_VALUE(density,inter_i+1,inter_j+1,inter_k+1)*t*u*v
		    + GRID_VALUE(density,inter_i,inter_j+1,inter_k)*(one-t)*u*(one-v)
		    + GRID_VALUE(density,inter_i+1,inter_j+1,inter_k)*t*u*(one-v)
		    + GRID_VALUE(density,inter_i+1,inter_j,inter_k+1)*t*(one-u)*v
		    + GRID_VALUE(density,inter_i+1,inter_j,inter_k)*t*(one-u)*(one-v); */

		// perform kernel lookup for r_eff, r_index is the kernel index of the first 
		// bin boundary below the effective radius of the voxel
		r_index = binSearch(smallkern.radial_boundary,inter_r_eff,smallkern.nradii);

		// interpolate to obtain the effective cumulative kernel value
		if (r_index == -1)  // radius is between zero and the first bin boundary
		{
			// fractional difference between inter_r_eff and the first bin boundary
			t = inter_r_eff/smallkern.radial_boundary[0];
			cumval = (1-t)*KERNEL_TOTAL_VALUE(&smallkern,0,p);
		}
		else if (r_index >= smallkern.nradii-1)  // overshot the kernel bin boundaries
		{
			cumval = KERNEL_TOTAL_VALUE(&smallkern,smallkern.nradii-1,p);
		}
		else  // inter_r_eff is between the first upper bin boundary and the last
		{
			t = (inter_r_eff - smallkern.radial_boundary[r_index])
				/(smallkern.radial_boundary[r_index + 1] - smallkern.radial_boundary[r_index]);
			cumval = (1-t)*KERNEL_TOTAL_VALUE(&smallkern,r_index,p)
				       + t*KERNEL_TOTAL_VALUE(&smallkern,r_index+1,p);
		}

        kval = cumval - last_cumval;

      	last_cumval = cumval;

		// Kernel value to use is current increment in cumulative value
        // Note that this is the fractional dose deposited at i,j,k due to
        // terma in an effective increment (increment*density) along the kernel ray at the 
		// interaction point. The value comes from the fractional dose deposited in an 
		// effective increment along the ray	at i,j,k due to terma at the current 
		// interaction point.

	    //Increment dose value.
	    //Note that to include the effect of density at i,j,k on ENERGY deposited at i,j,k, 
	    //there should be a density term, but this cancels on conversion of energy to dose as indicated below
	    // if (GRID_VALUE(terma,inter_i,inter_j,inter_k) > 0.001)
	    GRID_VALUE(dose,i,j,k) += f*kval;

	   r++;
	  }
	  while (r<10000);
	 }	//p,q
 
      GRID_VALUE(dose,i,j,k)/= NPHI;
    }

 //Inverse square correction to dose
 //This works better than applying the inverse square correction to terma
 //See Papanikolaou and Mackie 1993
 for (k=0;k<Q;k++)
  for (j=0;j<N;j++)
	for (i=0;i<M;i++)
   if (GRID_VALUE(dose,i,j,k) > 0.0)
   {
	   // squared difference between the source and the voxel
	   length = (float)pow(x[i] - bm->y_vec[0],2.0f) + (float)pow(y[j] - bm->y_vec[1],2.0f) 
		   + (float)pow(z[k] - bm->y_vec[2],2.0f);
	   
	   if (length > 0.0)
	      GRID_VALUE(dose,i,j,k) *= SAD*SAD/length;
   } 

   // free vectors
   free_fvector(ip,0,2);
   free_fvector(jp,0,2);
   free_fvector(kp,0,2);
   free_fvector(x,0,M-1);
   free_fvector(y,0,N-1);
   free_fvector(z,0,Q-1);
   
   free(smallkern.angular_boundary);
   free(smallkern.radial_boundary);
   // free(poly_kernel.total_matrix);
   for (j=0;j<N_KERNEL_CATEGORIES;j++)
	   free(smallkern.matrix[j]);

   return(SUCCESS);
}
