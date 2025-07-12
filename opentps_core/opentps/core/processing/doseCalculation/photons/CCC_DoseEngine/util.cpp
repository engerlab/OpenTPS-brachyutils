/* util.c */
/* Functions that are used for utility throughout the routines used for the C/S 
calculation.  Most of these functions are from Numerical Recipes in C by Press. */

#include "defs.h"

#define NR_END 1
#define FREE_ARG char*

extern char errstr[200];  // error string that all routines have access to

void nrerror(char error_text[])
/* Numerical Recipes standard error handler */
{
 fprintf(stderr,"Numerical Recipes run-time error...\n");
 fprintf(stderr,"%s\n",error_text);
 fprintf(stderr,"...now exiting to system...\n");
 exit(1);
}

float *fvector(int nl, int nh)
/* allocate a float vector with subscript range v[nl..nh] */
{
 float *v;
 v=(float *)malloc((size_t) ((nh-nl+1+NR_END)*sizeof(float)));
 if (!v) nrerror("allocation failure in fvector()");
 return v-nl+NR_END;
}


void free_fvector(float *v, int nl, int nh)
/* free a float vector allocated with fvector() */
{
 free((FREE_ARG) (v+nl-NR_END));
}


float **fmatrix(int nrl, int nrh, int ncl, int nch)
/* allocate a float matrix with subscript range m[nrl..nrh][ncl..nch] */
{
 int i, nrow=nrh-nrl+1,ncol=nch-ncl+1;
 float **m;
 /* allocate pointers to rows */
 m=(float **) malloc((size_t)((nrow+NR_END)*sizeof(float*)));
 if (!m) nrerror("allocation failure 1 in matrix()");
 m += NR_END;
 m -= nrl;
 /* allocate rows and set pointers to them */
 m[nrl]=(float *) malloc((size_t)((nrow*ncol+NR_END)*sizeof(float)));
 if (!m[nrl]) nrerror("allocation failure 2 in matrix()");
 m[nrl] += NR_END;
 m[nrl] -= ncl;
 for(i=nrl+1;i<=nrh;i++) m[i]=m[i-1]+ncol;
 /* return pointer to array of pointers to rows */
 return m;
}

void free_fmatrix(float **m, int nrl, int nrh, int ncl, int nch)
/* free a float matrix allocated by fmatrix() */
{
 free((FREE_ARG) (m[nrl]+ncl-NR_END));
 free((FREE_ARG) (m+nrl-NR_END));
}

int copy_grid_geometry(FLOAT_GRID *grid_old, FLOAT_GRID *grid_new)
// Copies geometric grid information from grid_old to grid_new
{
	grid_new->start.x = grid_old->start.x;
	grid_new->start.y = grid_old->start.y;
	grid_new->start.z = grid_old->start.z;

	grid_new->inc.x = grid_old->inc.x;
	grid_new->inc.y = grid_old->inc.y;
	grid_new->inc.z = grid_old->inc.z;

	grid_new->x_count = grid_old->x_count;
	grid_new->y_count = grid_old->y_count;
	grid_new->z_count = grid_old->z_count;

	return(SUCCESS);
}

int binSearch(float *a, float searchnum, int M)
/* Accepts a float array of data of length M ordered lowest to highest and a number called searchnum. 
Returns the index of the first element of the array, a, that is less than the searchnum. 
If the searchnum is less than a[0], then -1 is returned, and if the searchnum is greater 
than or equal to M, then M is returned. */
{
    int found, mid, top, bottom;

    bottom = 0;
    top = M-1;

    found = 0;  // flag that is set to 1 once the proper index is found
 
    // Ensure that the search parameter lies inside boundaries
	if(searchnum >= a[top])
		return(M); 
	if(searchnum <= a[bottom])
		return(-1);

	while(!found)
	{
		mid = (top + bottom) / 2;
		if(searchnum == a[mid])
			found = 1;
		else
			if(searchnum < a[mid])
				top = mid - 1;
			else
				if(searchnum > a[mid + 1])
					bottom = mid + 1;
				else
					found = 1; 
	}
	return(mid);
}
