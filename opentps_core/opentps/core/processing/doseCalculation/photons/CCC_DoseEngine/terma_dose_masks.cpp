/* terma_dose_masks.cpp */

/* All voxels that lie within a cylinder of radius RAPERTURE + RSAFE, centered
on the central beam axis, are marked in the dose_mask grid.  These voxels will
be used in the dose calculation.  The voxels that are marked in the terma_mask
grid are a subset of those that are marked in the dose_mask grid. The terma_mask
grid contains values that specify the fraction of each voxel that lies inside
of the beam aperture in the beam's eye view plane, which exists at a distance
SAD from the x-ray source location. */

/* Determination of voxel "insideness" for the terma_mask:
If it is discovered that a voxel is intersected by an aperture boundary in the
beam's eye view plane, then that voxel is broken-up into Mus x Nus x Qus sub-
voxels (upsampled).  The fraction of the sub-voxels that lie inside the beam
aperture in the beam's eye view then becomes the insideness for that voxel. */

#include "defs.h"

extern char errstr[200];  // error string that all routines have access to

int terma_dose_masks(FLOAT_GRID *terma_mask, FLOAT_GRID *dose_mask, BEAM *bm)
// The user must allocate space for terma_mask and dose_mask before calling 
// this function.
// The validity of all of the arguments to this function are assumed to be 
// checked with the parse_func, which acts as a gatekeeper for the convolution
// program.
{
	// scalars
	int i,j,k,m;     // indices
	int ius,jus,kus;  // upsample voxel indices
	int M,N,Q;     // grid dimensions
	float dx,dy,dz;  // voxel dimensions
	float xp,yp,SAD; // aperture center in ip,jp,kp coordinate system
	float xsub,ysub,zsub;  // coordinates of sub-voxels
	float del_xp,del_yp; // width of beamlet field in plane at SAD
	float Rmax,Rcurr,Rcyl,Rvox,Rcyl_sqr,Rproj;
	float eta,gamma,delta;  // dummy variables

	// vectors
	float *x,*y,*z;  // x,y,z coordinate vectors
	float *dxus,*dyus,*dzus;  // upsample vectors
	float *y_vec,*ip,*jp,*kp,*d_hat;  // beam vectors

	// matrices
	float **c;  // matrix of the 8 corners of voxel grid
	
	// Ensure that upsample factors are all greater than zero
	if (Mus < 1 || Nus < 1 || Qus < 1)
	{
		sprintf(errstr,"Upsample factors must all be greater than zero.");
		return(FAILURE);
	}

	// record the sizes of terma_mask and dose_mask
	M = terma_mask->x_count;
	N = terma_mask->y_count;
	Q = terma_mask->z_count;

	if (M != dose_mask->x_count || N != dose_mask->y_count 
		|| Q != dose_mask->z_count)
	{
		sprintf(errstr,"dose_mask and terma_mask dimensions are incompatible.");
		return(FAILURE);
	}

	dx = terma_mask->inc.x;
	dy = terma_mask->inc.y;
	dz = terma_mask->inc.z;
	
	// initialize vectors
	x = fvector(0,M-1);
	y = fvector(0,N-1);
	z = fvector(0,Q-1);

	dxus = fvector(0,Mus-1);
	dyus = fvector(0,Nus-1);
	dzus = fvector(0,Qus-1);

	y_vec = fvector(0,2);
	ip = fvector(0,2);
	jp = fvector(0,2);
	kp = fvector(0,2);
	d_hat = fvector(0,2);

	// initialize matrices
	c = fmatrix(0,7,0,2);

	// fill-in the voxel coordinate vectors
	for (i=0;i<M;i++) x[i] = terma_mask->start.x + (float)i*dx;
	for (j=0;j<N;j++) y[j] = terma_mask->start.y + (float)j*dy;
	for (k=0;k<Q;k++) z[k] = terma_mask->start.z + (float)k*dz;

	// fill-in the upsample vectors
	// For a voxel at (i,j,k), the xyz coordinates of a sub-voxel (ius,jus,kus)
	// are (x[i] + dxus[ius], y[j] + dyus[jus], z[k] + dzus[k])
	dxus[0] = -0.5*dx*(1-1/Mus);
	for (ius=1;ius<Mus;ius++)  dxus[ius] = dxus[ius-1] + dx/Mus;

	dyus[0] = -0.5*dy*(1-1/Nus);
	for (jus=1;jus<Nus;jus++) dyus[jus] = dyus[jus-1] + dy/Nus;

	dzus[0] = -0.5*dz*(1-1/Qus);
	for (kus=1;kus<Qus;kus++) dzus[kus] = dzus[kus-1] + dz/Qus;

	// rewrite beam vectors for quick reference later
	y_vec[0] = bm->y_vec[0];
	y_vec[1] = bm->y_vec[1];
	y_vec[2] = bm->y_vec[2];

	// coordinate system in beam's eye view
	for (j=0;j<3;j++) ip[j] = bm->ip[j];
	for (j=0;j<3;j++) jp[j] = bm->jp[j];
	for (j=0;j<3;j++) kp[j] = bm->kp[j];

	// aperture center in beam's eye view
	xp = bm->xp;
	yp = bm->yp;

	// aperture size in beam's eye view
	del_xp = bm->del_xp;
	del_yp = bm->del_yp;

	// source-axis distance of the beam
	SAD = bm->SAD;

	// calculate the max distance between the source vector and each grid corner
	Rmax = 0.0;
	
	// the the matrix c with the coordinates of the eight corners of the grid.
	for (i=0;i<=1;i++)
	  for (j=0;j<=1;j++)
	    for (k=0;k<=1;k++)
		{ 
		  //                     0 => lower corners         1 => upper corners
		  c[i+j*2+k*4][0] = (1-(float)i)*(x[0]-dx/2.0) + (float)i*(x[M-1]+dx/2.0);
		  c[i+j*2+k*4][1] = (1-(float)j)*(y[0]-dy/2.0) + (float)j*(y[N-1]+dy/2.0);
		  c[i+j*2+k*4][2] = (1-(float)k)*(z[0]-dz/2.0) + (float)k*(z[Q-1]+dz/2.0);
		}

	// find which corner is the farthest from the source
	for (m=0;m<=7;m++)
	{
		Rcurr = sqrt(pow(y_vec[0] - c[m][0],2.0f)
			       + pow(y_vec[1] - c[m][1],2.0f)
				   + pow(y_vec[2] - c[m][2],2.0f));
		if (Rcurr > Rmax)
			Rmax = Rcurr;
	}

	// Fill the dose_mask

	// Radius of cylinder about y_vec + kp that will contain all voxels
	// to be used in the dose calculation.
	Rcyl = sqrt(del_xp*del_xp + del_yp*del_yp)*Rmax/SAD;  // project Rmax to aperture plane
	Rcyl_sqr = Rcyl*Rcyl + RSAFE*RSAFE;  // add an empirical safety margin to the radius squared

	// calculate the true source direction
	// d_hat points at the center of the aperture from the source location
	d_hat[0] = xp*ip[0] + yp*jp[0] + SAD*kp[0];
	d_hat[1] = xp*ip[1] + yp*jp[1] + SAD*kp[1];
	d_hat[2] = xp*ip[2] + yp*jp[2] + SAD*kp[2];

	// normalize d_hat so it's a true "hat" vector
	delta = sqrt(d_hat[0]*d_hat[0] + d_hat[1]*d_hat[1] + d_hat[2]*d_hat[2]);
	d_hat[0] = d_hat[0]/delta;
	d_hat[1] = d_hat[1]/delta;
	d_hat[2] = d_hat[2]/delta;

	for (k=0;k<Q;k++)
	 for (j=0;j<N;j++)
	  for (i=0;i<M;i++)
	  {
		  // squared distance between the voxel and the source:
		  eta = (x[i] - y_vec[0])*(x[i] - y_vec[0])
			  + (y[j] - y_vec[1])*(y[j] - y_vec[1])
			  + (z[k] - y_vec[2])*(z[k] - y_vec[2]);

		  // squared distance between the voxel and the source along source direction, 
	      // y_vec + kp:
		  gamma = pow((x[i] - y_vec[0])*d_hat[0]
				    + (y[j] - y_vec[1])*d_hat[1]
				    + (z[k] - y_vec[2])*d_hat[2],2.0f);

		  // printf("%lf %lf\n",eta, gamma);

		  // squared difference between the voxel and the axis of the cylinder
		  delta = eta - gamma;

		  // If the voxel is inside the cylinder about y_vec + ip of radius Rcyl plus
		  // a safety margin then mark it in dose_mask.
		  if (delta <= Rcyl_sqr)
			  GRID_VALUE(dose_mask,i,j,k) = 1.0;
		  else
			  GRID_VALUE(dose_mask,i,j,k) = 0.0;
	  }

	// Fill the terma_mask, including the insideness of each voxel

	// Each voxel is enclosed with in a sphere of the following radius:
	Rvox = 0.5*sqrt(dx*dx + dy*dy + dz*dz);

	for (i=0;i<M;i++)
	 for (j=0;j<N;j++)
	  for (k=0;k<Q;k++)
	   // deal only with voxels that are marked in the dose_mask
	   if (GRID_VALUE(dose_mask,i,j,k) > 0.0)
	   {
		 // distance between source and voxel in the kp direction
	     delta = kp[0]*(x[i] - y_vec[0])
               + kp[1]*(y[j] - y_vec[1])
               + kp[2]*(z[k] - y_vec[2]);

		 // voxel's projected offset on the aperture plane in the ip direction:
		 eta = (SAD/delta)*(  ip[0]*(x[i] - y_vec[0])
				            + ip[1]*(y[j] - y_vec[1])
						    + ip[2]*(z[k] - y_vec[2])) - xp;
		 // voxel's projected offset on the aperture plane in the jp direction:
		 gamma = (SAD/delta)*(  jp[0]*(x[i] - y_vec[0])
				              + jp[1]*(y[j] - y_vec[1])
						      + jp[2]*(z[k] - y_vec[2])) - yp;

		 // take absolute value of offsets
		 eta = fabs(eta);
		 gamma = fabs(gamma);

		 Rproj = Rvox*SAD/delta;  // voxel radius projected to plane at SAD

		 // Determine where the voxel lies with respect to the aperture:
		 if (eta <= 0.5*del_xp+Rproj && gamma <= 0.5*del_yp+Rproj)
		 // voxel is inside aperture plus a half-voxel margin:
			if (eta >= 0.5*del_xp-Rproj || gamma >= 0.5*del_yp-Rproj)
		    // voxel is between the aperture plus/minus a half-voxel margin:
			// (true at this point if the voxel size is larger than the aperture size)
			{
			    // Determine insideness of the voxel by breaking it up
				// into subvoxels and projecting the parts to the aperture plane.
				m = 0;  // number of subvoxels inside aperture
	            // project each subvoxel onto the aperture at SAD
		        for (ius=0;ius<Mus;ius++)
			     for (jus=0;jus<Nus;jus++)
			      for (kus=0;kus<Qus;kus++)
				  {
			        // find the center of the subvoxel
			        xsub = x[i] + dxus[ius];
			        ysub = y[j] + dyus[jus];
			        zsub = z[k] + dzus[kus];

			        // project the subvoxel onto the aperture
			        // distance between source and subvoxel in the kp direction
			        delta = kp[0]*(xsub - y_vec[0])
				          + kp[1]*(ysub - y_vec[1])
					      + kp[2]*(zsub - y_vec[2]);

			        // projected offset on aperture plane in the ip direction:
			        eta = (SAD/delta)*(  ip[0]*(xsub - y_vec[0])
				                       + ip[1]*(ysub - y_vec[1])
								       + ip[2]*(zsub - y_vec[2])) - xp;
			        // projected offset on aperture plane in the jp direction:
			        gamma = (SAD/delta)*(  jp[0]*(xsub - y_vec[0])
				                         + jp[1]*(ysub - y_vec[1])
								         + jp[2]*(zsub - y_vec[2])) - yp;

		            eta = fabs(eta);
			        gamma = fabs(gamma);

			        // check if the subvoxel is inside the aperture at SAD
			        if (eta <= 0.5*del_xp && gamma <= 0.5*del_yp)
				       m++;
				  }

		        // the fraction of subvoxels inside the aperture becomes the insidness
	            GRID_VALUE(terma_mask,i,j,k) = (float)m/(float)(Mus*Nus*Qus);
			}
			else
			// voxel is inside the aperture minus a half-voxel margin
				GRID_VALUE(terma_mask,i,j,k) = 1.0;
		 else
		 // voxel outside the aperture plus the half-voxel margin
		    GRID_VALUE(terma_mask,i,j,k) = 0.0;
	   }

	// free vectors
	free_fvector(x,0,M-1);
	free_fvector(y,0,N-1);
	free_fvector(z,0,Q-1);

	free_fvector(dxus,0,Mus-1);
	free_fvector(dyus,0,Nus-1);
	free_fvector(dzus,0,Qus-1);

	free_fvector(y_vec,0,2);
	free_fvector(ip,0,2);
	free_fvector(jp,0,2);
	free_fvector(kp,0,2);
	free_fvector(d_hat,0,2);

	// free matrices
	free_fmatrix(c,0,7,0,2);

	return(SUCCESS);
}
