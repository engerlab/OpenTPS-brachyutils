/* C_RAYTRACE.C ***************************************************************/
#include "defs.h"

extern char errstr[200];  // error string that all routines have access to

int raytrace(FLOAT_GRID *electron_density_grid,FLOAT_GRID *radiological_depth_grid,
             POINT point1,POINT point2)
/*
--------------------------------------------------------------------------------
   NAME
 	c_raytrace
 
   SYNOPSIS
        point1 and point2 are the end points of the ray. 

   DESCRIPTION
        This function traces the ray from point x to point y (in real 
        coords), assigning depth to any voxels which that ray crosses. The 
        technique used is that described by Siddon R.L. (Med Phys 12 (2), 
        1985). This routine will not be understood without thorough reading 
        of that paper! Point1 and point2 are the start and end points of the 
        ray, respectively. External structures of type GRID are assumed to 
        exist, where electron_density_grid are the electron densities, and 
        radiological_depth_grid is the output grid for these calculations.
        Voxels in radiological_depth_grid are initially set -ve prior to 
        calling this function.
 
   AUTHOR
        Written by David C. Murray
                   University of Waikato
                   Private Bag 3105
                   Hamilton
                   New Zealand
        and Copyright (1991) to
                   David C. Murray and Peter W. Hoban,
                   Cancer Society of New Zealand Inc., and 
                   University of Waikato.
--------------------------------------------------------------------------------
*/

{
/* Variable descriptions:
   x1,x2,y1,y2,z1,z2 are the coordinates of the ray end points 
     (i.e. (x1,y1,z1)=source, (x2,y2,z2)=point beyond phantom) 
   xp1,yp1,zp1 are the real coords of voxel region origin (in cm) 
   Nx,Ny,Nz are (no. of voxels + 1) in each direction 
   dx,dy,dz are the widths in cm of the voxels
*/
float         x1,y1,z1,
              x2,y2,z2,
              xp1,yp1,zp1,
              dx,dy,dz;
int           Nx,Ny,Nz;

/*General ray-trace algorithm variables*/
float xpN, ypN, zpN;			/*real coords in cm of region limits*/ 
float alpha_x_min,alpha_y_min,alpha_z_min,alpha_x_max,alpha_y_max,alpha_z_max;
					/*limits of alpha x,y,z parameters*/
float alpha_min, alpha_max;		/*limits of alpha parameter*/
int i_min,i_max,j_min,j_max,k_min,k_max;/*limits of indices for x,y,z dirns*/
float *alpha_x,*alpha_y,*alpha_z;	/*hold sets of x,y,z alpha values*/
float *alpha;				/*holds merged set of alpha values*/
int i_index,j_index,k_index;		/*loop indices for merging alphas*/
int a;					/*loop counter*/
int max_index;				/*max index of merged alpha array*/
float d12;				/*distance between ray end points*/
float alpha_mid;			/*mid-point of intersection length*/
float length;				/*intersection length*/
int i,j,k;				/*indices of voxel with int. length*/
float rpl = 0.0;			/*radiological path length in cm*/
float voxel_density;			/*temporary voxel density*/
float lmax;  // best possible penetration pathlength for a voxel
float pnorm;  // absolute difference between p1 and p2

/* Assign variables */
/******************************************************************************/
x1 = point1.x;
y1 = point1.y;
z1 = point1.z;
x2 = point2.x;
y2 = point2.y;
z2 = point2.z;
Nx = electron_density_grid->x_count + 1;
Ny = electron_density_grid->y_count + 1;
Nz = electron_density_grid->z_count + 1;
dx = electron_density_grid->inc.x;
dy = electron_density_grid->inc.y;
dz = electron_density_grid->inc.z;

// (xp1,yp1,zp1) are the locations of the first grid planes for each dimension
xp1 = electron_density_grid->start.x - 0.5*dx;
yp1 = electron_density_grid->start.y - 0.5*dy;
zp1 = electron_density_grid->start.z - 0.5*dz;

pnorm = sqrt((x2-x1)*(x2-x1) + (y2-y1)*(y2-y1) + (z2-z1)*(z2-z1));

// this is the largest pathlength possible for a ray through a voxel:
lmax = sqrt(pow((x2-x1)*dx,2.0f)+pow((y2-y1)*dy,2.0f)+pow((z2-z1)*dz,2.0f))/pnorm;

/* Calculate xpN,ypN,zpN */
/******************************************************************************/
xpN = xp1 + (Nx-1)*dx;
ypN = yp1 + (Ny-1)*dy;
zpN = zp1 + (Nz-1)*dz;

/*Calculate alpha_min and alpha_max*/
/******************************************************************************/
/*Avoid division by zero*/
if (x1==x2)
  x2 += 0.00001;
if (y1==y2)
  y2 += 0.00001;
if (z1==z2)
  z2 += 0.00001;
if ((fabs(x1-x2)<dx) && (fabs(y1-y2)<dy) && (fabs(z1-z2)<dz))
{
	sprintf(errstr,"Error - ray trace region too small.");
	return(FAILURE);
}

alpha_x_min = (((xp1-x1)/(x2-x1))<((xpN-x1)/(x2-x1))) ? ((xp1-x1)/(x2-x1)) 
                                                      : ((xpN-x1)/(x2-x1));
alpha_y_min = (((yp1-y1)/(y2-y1))<((ypN-y1)/(y2-y1))) ? ((yp1-y1)/(y2-y1)) 
                                                      : ((ypN-y1)/(y2-y1));
alpha_z_min = (((zp1-z1)/(z2-z1))<((zpN-z1)/(z2-z1))) ? ((zp1-z1)/(z2-z1)) 
                                                      : ((zpN-z1)/(z2-z1));
alpha_x_max = (((xp1-x1)/(x2-x1))>((xpN-x1)/(x2-x1))) ? ((xp1-x1)/(x2-x1)) 
                                                      : ((xpN-x1)/(x2-x1));
alpha_y_max = (((yp1-y1)/(y2-y1))>((ypN-y1)/(y2-y1))) ? ((yp1-y1)/(y2-y1)) 
                                                      : ((ypN-y1)/(y2-y1));
alpha_z_max = (((zp1-z1)/(z2-z1))>((zpN-z1)/(z2-z1))) ? ((zp1-z1)/(z2-z1)) 
                                                      : ((zpN-z1)/(z2-z1));
alpha_min = (alpha_x_min>alpha_y_min) ? alpha_x_min : alpha_y_min;
if (alpha_z_min>alpha_min) 
  alpha_min = alpha_z_min;
if (alpha_min<0)
  alpha_min = 0;
alpha_max = (alpha_x_max<alpha_y_max) ? alpha_x_max : alpha_y_max;
if (alpha_z_max<alpha_max) 
  alpha_max = alpha_z_max;
if (alpha_max>1)
  alpha_max = 1;

// Monitor lines...
/*
printf("    alpha_x,y,z_min: %7.4f %7.4f %7.4f\n",
                alpha_x_min,alpha_y_min,alpha_z_min);
printf("    alpha_x,y,z_max: %7.4f %7.4f %7.4f\n",
                alpha_x_max,alpha_y_max,alpha_z_max);
printf("    alpha_min,alpha_max: %7.4f %7.4f\n",alpha_min,alpha_max);
printf("Nx, xpN, x2,x1, dx = %d %5.2f %5.2f %5.2f %5.2f\n",Nx,xpN,x2,x1,dx); */

/*Determine the ranges of i,j,k indices*/
/******************************************************************************/
/*The following assignments require conversion from float to integer types*/
/*The value 0.001 is added/subtracted to ensure that the ceiling and floor*/
/*functions convert to the correct value. Note that the range of these*/
/*variables is from 1 to Nx,Ny,Nz, NOT 0 to Nx-1,Ny-1,Nz-1*/
		
i_min = (x2>x1) ? (int) ceil((float) Nx - (xpN-alpha_min*(x2-x1)-x1)/dx-0.001)
                : (int) ceil((float) Nx - (xpN-alpha_max*(x2-x1)-x1)/dx-0.001);
i_max = (x2>x1) ? (int) floor(1.0000 + (x1+alpha_max*(x2-x1)-xp1)/dx+0.001)
                : (int) floor(1.0000 + (x1+alpha_min*(x2-x1)-xp1)/dx+0.001);
j_min = (y2>y1) ? (int) ceil((float) Ny - (ypN-alpha_min*(y2-y1)-y1)/dy-0.001)
                : (int) ceil((float) Ny - (ypN-alpha_max*(y2-y1)-y1)/dy-0.001);
j_max = (y2>y1) ? (int) floor(1.0000 + (y1+alpha_max*(y2-y1)-yp1)/dy+0.001)
                : (int) floor(1.0000 + (y1+alpha_min*(y2-y1)-yp1)/dy+0.001);
k_min = (z2>z1) ? (int) ceil((float) Nz - (zpN-alpha_min*(z2-z1)-z1)/dz-0.001)
                : (int) ceil((float) Nz - (zpN-alpha_max*(z2-z1)-z1)/dz-0.001);
k_max = (z2>z1) ? (int) floor(1.0000 + (z1+alpha_max*(z2-z1)-zp1)/dz+0.001)
                : (int) floor(1.0000 + (z1+alpha_min*(z2-z1)-zp1)/dz+0.001); 

/*Monitor lines...
fprintf(stdout,"    i,j,k_min: %3d %3d %3d\n",i_min,j_min,k_min);
fprintf(stdout,"    i,j,k_max: %3d %3d %3d\n",i_max,j_max,k_max);
*/
/*Generate sets of alpha values,reversing order if necessary*/
/******************************************************************************/
/*allocate array space on stack*/
if ((alpha_x = (float*) calloc(Nx+1,sizeof(float))) == NULL)
{
	sprintf(errstr,"Error - insufficient heap for alpha_x allocation.");
	return(FAILURE);
}

if ((alpha_y = (float*) calloc(Ny+1,sizeof(float))) == NULL)
{
	sprintf(errstr,"Error - insufficient heap for alpha_y allocation.");
	return(FAILURE);
}

if ((alpha_z = (float*) calloc(Nz+1,sizeof(float))) == NULL)
{
	sprintf(errstr,"Error - insufficient heap for alpha_z allocation.");
	return(FAILURE);
}

/* 
printf("Nx = %d, i_min = %d, i_max = %d\n",Nx,i_min,i_max);
printf("Ny = %d, j_min = %d, j_max = %d\n",Ny,j_min,j_max);
printf("Nz = %d, k_min = %d, k_max = %d\n",Nz,k_min,k_max); */
 
if (i_min <= i_max)
  if (x2>x1)
    {
    alpha_x[0] = ((xp1+(i_min-1)*dx)-x1)/(x2-x1);
    for (a=1;a<=i_max-i_min;a++)
      alpha_x[a] = alpha_x[a-1]+dx/(x2-x1);
    }
  else
    {
    alpha_x[i_max-i_min] = ((xp1+(i_min-1)*dx)-x1)/(x2-x1);
    for (a=i_max-i_min-1;a>=0;a--)
      alpha_x[a] = alpha_x[a+1]+(dx/(x2-x1));
    }
alpha_x[i_max-i_min+1] = 10000.0;
if (j_min <= j_max)
  if (y2>y1)
    {
    alpha_y[0] = ((yp1+(j_min-1)*dy)-y1)/(y2-y1);
    for (a=1;a<=j_max-j_min;a++)
      alpha_y[a] = alpha_y[a-1]+dy/(y2-y1);
    }
  else
    {
    alpha_y[j_max-j_min] = ((yp1+(j_min-1)*dy)-y1)/(y2-y1);
    for (a=j_max-j_min-1;a>=0;a--)
      alpha_y[a] = alpha_y[a+1]+(dy/(y2-y1));
    }
alpha_y[j_max-j_min+1] = 10001.0;
if (k_min <= k_max)
  if (z2>z1)
    {
    alpha_z[0] = ((zp1+(k_min-1)*dz)-z1)/(z2-z1);
    for (a=1;a<=k_max-k_min;a++)
      alpha_z[a] = alpha_z[a-1]+(dz/(z2-z1));
    }
  else
    {
    alpha_z[k_max-k_min] = ((zp1+(k_min-1)*dz)-z1)/(z2-z1);
    for (a=k_max-k_min-1;a>=0;a--)
      alpha_z[a] = alpha_z[a+1]+(dz/(z2-z1));
  }
alpha_z[k_max-k_min+1] = 10002.0; 


/*Monitor lines...
if (i_max<i_min)
  fprintf(stdout,"    No alpha_x values\n");
else
  fprintf(stdout,"    First & last alpha_x values: %7.4f %7.4f\n",
                 alpha_x[0],alpha_x[i_max-i_min]);
if (j_max<j_min)
  fprintf(stdout,"    No alpha_y values\n");
else
  fprintf(stdout,"    First & last alpha_y values: %7.4f %7.4f\n",
                 alpha_y[0],alpha_y[j_max-j_min]);
if (k_max<k_min)
  fprintf(stdout,"    No alpha_z values\n");
else
  fprintf(stdout,"    First & last alpha_z values: %7.4f %7.4f\n",
                 alpha_z[0],alpha_z[k_max-k_min]);
*/
/*Generate merged set of alpha values*/


/******************************************************************************/
if ((alpha = (float*) calloc(Nx+Ny+Nz+3,sizeof(float))) == NULL)
{
	sprintf(errstr,"Error - insufficient heap for alpha allocation.");
	return(FAILURE);
}

max_index = (i_max-i_min+1)+(j_max-j_min+1)+(k_max-k_min+1)+1;
alpha[0] = alpha_min;
i_index = 0;
j_index = 0;
k_index = 0;
for (a=1;a<=max_index-1;a++)
  if (alpha_x[i_index]<alpha_y[j_index])
    if (alpha_x[i_index]<alpha_z[k_index])
      {
      alpha[a] = alpha_x[i_index];
      i_index += 1;
      }
    else
      {
      alpha[a] = alpha_z[k_index];
      k_index += 1;
      }
  else
    if (alpha_y[j_index]<alpha_z[k_index])
      {
      alpha[a] = alpha_y[j_index];
      j_index += 1;
      }
    else
      {
      alpha[a] = alpha_z[k_index];
      k_index += 1;
      }
alpha[max_index] = alpha_max;
free(alpha_x);				//deallocate temp array storage
free(alpha_y);
free(alpha_z);
/*Monitor lines...
fprintf(stdout,"    Number of elements in merged set = %4d\n",max_index+1);
for (a=0;a<=max_index;a++)
  fprintf(stdout,"      Element %3d = %7.5f\n",a,alpha[a]);
*/
/*Calculate voxel lengths and indices, and assign radiological depth*/
/******************************************************************************/
d12 = sqrt((x2-x1)*(x2-x1)+(y2-y1)*(y2-y1)+(z2-z1)*(z2-z1));
					//d12 is distance between ray end pts
// printf("made it this far in raytrace.\n");
for (a=1;a<=max_index;a++)
  {
  length = d12*(alpha[a]-alpha[a-1]);	//length is voxel intersection length
  if (fabs(length)>0.01)		//do not process unless > 0.01 cm
    {
    alpha_mid = (alpha[a]+alpha[a-1])/2.0;
					//alpha_mid is middle of int. length
    i = (int) floor((x1 + alpha_mid*(x2-x1) - xp1)/dx);
    j = (int) floor((y1 + alpha_mid*(y2-y1) - yp1)/dy);
    k = (int) floor((z1 + alpha_mid*(z2-z1) - zp1)/dz);
					//i,j,k are indices of voxel

    // Remember that this function traces only a single ray.
    // rpl has been set to zero during initialisation.

    voxel_density = GRID_VALUE(electron_density_grid,i,j,k);
    rpl += length * voxel_density/2.0;  // add first half of int. length
    // store pathlength only if the voxel is intersected almost directly
	// by the ray
    if (length>=0.75/2*lmax && GRID_VALUE(radiological_depth_grid,i,j,k)<0.0)
      GRID_VALUE(radiological_depth_grid, i, j, k) = rpl;
    
    rpl += length * voxel_density/2.0;  //add second half of int. length  
    }    
  } 
free(alpha); 			//deallocate remaining array storage 

return(SUCCESS);

} 					/*End of s_raytrace routine*/
