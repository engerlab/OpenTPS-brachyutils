/* parse_func.cpp */

/* Checks the validity of the arguments input to the convolution routine and 
transfers the Matlab-style arguments to the C structures defined in defs.h. */

/* This parse function operates on file inputs rather than on Matlab inputs. */

#include "defs.h"

// Markers that are searched for inside the kernel_filenames file, which is 
// passed to the load_kernels routine. The line after each of these markers
// in the kernel_filenames file is a filename corresponding to the marker.
#define kernel_header_line "kernel_header"
#define kernel_radii_line "kernel_radii"
#define kernel_angles_line "kernel_angles"
#define kernel_energies_line "kernel_energies"
#define kernel_primary_line "kernel_primary"
#define kernel_first_scatter_line "kernel_first_scatter"
#define kernel_second_scatter_line "kernel_second_scatter"
#define kernel_multiple_scatter_line "kernel_multiple_scatter"
#define kernel_brem_annih_line "kernel_brem_annih"
#define kernel_total_line "kernel_total"
#define kernel_fluence_line "kernel_fluence"
#define kernel_mu_line "kernel_mu"
#define kernel_mu_en_line "kernel_mu_en"

// Markers that are searched for inside the geometry_filenames, which is 
// passed to the load_geometry routine. These have the same meaning as
// the kernel_filenames markers.
#define geometry_header "./geometry_files/geometry_header.txt"
#define geometry_density "./geometry_files/density.bin"
#define beam_data "./geometry_files/beam_data.txt"

#define geometry_header_line "geometry_header"
#define geometry_density_line "geometry_density"
#define beam_data_line "beam_data"

extern char errstr[200];  // error string that all routines have access to

int load_kernels(MONO_KERNELS *mono_kernels, char kernel_filenames[])
/* Ensures that the kernel files have the following format:

               radii: [1xNradii float]
              angles: [1xNangles float]
            energies: [1xNenergies float]
             primary: [Nradii x Nangles x Nenergies float]
       first_scatter: [Nradii x Nangles x Nenergies float]
      second_scatter: [Nradii x Nangles x Nenergies float]
    multiple_scatter: [Nradii x Nangles x Nenergies float]
          brem_annih: [Nradii x Nangles x Nenergies float]
               total: [Nradii x Nangles x Nenergies float]
          mean_radii: [Nradii x Nangles x Nenergies float] (not used)
         mean_angles: [Nradii x Nangles x Nenergies float] (not used)
           helpfield: [any x any char] 
             fluence: [1xNenergies float]
                  mu: [1xNenergies float]
               mu_en: [1xNenergies float]

mistakes or inconsistencies will result in errors.

  Results are then stored in mono_kernels.

The names of the files containing all of these parameters are given
by the kernel_filenames file.

*/
{
	int j,k;
	int Nenergies, Nangles, Nradii;
	char str[200];
	// some strings to hold filenames
	char header_filename[200], radii_filename[200], angles_filename[200];
	char energies_filename[200], primary_filename[200], first_scatter_filename[200];
	char second_scatter_filename[200], multiple_scatter_filename[200];
	char brem_annih_filename[200], total_filename[200], fluence_filename[200];
	char mu_filename[200], mu_en_filename[200];

	// flags for file readin
	int header_flag = 0;
	int radii_flag = 0;
	int angles_flag = 0;
	int energies_flag = 0;
	int primary_flag = 0;
	int first_flag = 0;
	int second_flag = 0;
	int multiple_flag = 0;
	int brem_annih_flag = 0;
	int total_flag = 0;
	int fluence_flag = 0;
	int mu_flag = 0;
	int mu_en_flag = 0;

	FILE *fid;  // generic filename
	FILE *primary, *first, *second, *multiple, *brem_annih, *total;  // kernel files

	// read in the data filenames
	if ( (fid = fopen(kernel_filenames,"r")) == NULL)  // open the kernel filenames
	{
		sprintf(errstr,"Could not open the kernel filenames file");
		return(FAILURE);
	}

	while (fscanf(fid,"%s\n",str) != EOF)  // read until the end of the file
	{
	  if (!strcmp(str,kernel_header_line))
	    if (fscanf(fid,"%s\n",header_filename) != 1)
		{
			sprintf(errstr,"Failed to read-in the kernel_header filename from the kernel filenames file.");
			return(FAILURE);
		}
	    else
	      header_flag = 1;
	  else if (!strcmp(str,kernel_radii_line))
	    if (fscanf(fid,"%s\n",radii_filename) != 1)
		{
			sprintf(errstr,"Failed to read-in the kernel_radii filename from the kernel filenames file.");
			return(FAILURE);
		}
	    else
	      radii_flag = 1;
	  else if (!strcmp(str,kernel_angles_line))
	    if (fscanf(fid,"%s\n",angles_filename) != 1)
		{
			sprintf(errstr,"Failed to read-in the kernel_angles filename from the kernel filenames file.");
			return(FAILURE);
		}
            else
	      angles_flag = 1;
	  else if (!strcmp(str,kernel_energies_line))
        if (fscanf(fid,"%s\n",energies_filename) != 1)
		{
			sprintf(errstr,"Failed to read-in the kernel_energies filename from the kernel filenames file.");
			return(FAILURE);
		}
	    else
	      energies_flag = 1;
          else if (!strcmp(str,kernel_fluence_line))
	    if (fscanf(fid,"%s\n",fluence_filename) != 1)
		{
			sprintf(errstr,"Failed to read-in the kernel_fluence filename from the kernel filenames file.");
			return(FAILURE);
		}
	    else
	      fluence_flag = 1;
	  else if (!strcmp(str,kernel_primary_line))
        if (fscanf(fid,"%s\n",primary_filename) != 1)
		{
			sprintf(errstr,"Failed to read-in the kernel_primary filename from the kernel filenames file.");
			return(FAILURE);
		}
	    else
	      primary_flag = 1;
	  else if (!strcmp(str,kernel_first_scatter_line))
        if (fscanf(fid,"%s\n",first_scatter_filename) != 1)
		{
			sprintf(errstr,"Failed to read-in the kernel_first_scatter filename from the kernel filenames file.");
			return(FAILURE);
		}
	    else
	      first_flag = 1;
	  else if (!strcmp(str,kernel_second_scatter_line))
	    if (fscanf(fid,"%s\n",second_scatter_filename) != 1)
		{
			sprintf(errstr,"Failed to read-in the kernel_second_scatter filename from the kernel filenames file.");
			return(FAILURE);
		}
	    else
	      second_flag = 1;
	  else if (!strcmp(str,kernel_multiple_scatter_line))
        if (fscanf(fid,"%s\n",multiple_scatter_filename) != 1)
		{
			sprintf(errstr,"Failed to read-in the kernel_multiple_scatter filename from the kernel filenames file.");
			return(FAILURE);
		}
	    else
	      multiple_flag = 1;
	  else if (!strcmp(str,kernel_brem_annih_line))
	    if (fscanf(fid,"%s\n",brem_annih_filename) != 1)
		{
			sprintf(errstr,"Failed to read-in the kernel_brem_annih filename from the kernel filenames file.");
			return(FAILURE);
		}
	    else 
	      brem_annih_flag = 1;
	  else if (!strcmp(str,kernel_total_line))
	    if (fscanf(fid,"%s\n",total_filename) != 1)
	    {
			sprintf(errstr,"Failed to read-in the kernel_total filename from the kernel filenames file.");
			return(FAILURE);
		}
	    else
	      total_flag = 1;
	  else if (!strcmp(str,kernel_mu_line))
	    if (fscanf(fid,"%s\n",mu_filename) != 1)
		{
			sprintf(errstr,"Failed to read-in the kernel_mu filename from the kernel filenames file.");
			return(FAILURE);
		}
	    else
	      mu_flag = 1;
	  else if (!strcmp(str,kernel_mu_en_line))
	    if (fscanf(fid,"%s\n",mu_en_filename) != 1)
		{
			sprintf(errstr,"Failed to read-in the kernel_mu_en filename from the kernel filenames file.");
			return(FAILURE);
		}
	    else
	      mu_en_flag = 1;
	  else
	  {   
		    sprintf(errstr,"Unrecognized string in the kernel filenames file: %s\n",str);
			return(FAILURE);   
	  }
	}

	// confirm that all of the required filenames have been found
	if (header_flag == 0)
	{
	  sprintf(errstr,"Unable to find a kernel header filename.");
	  return(FAILURE);
	}
	else if (radii_flag == 0)
	{
	  sprintf(errstr,"Unable to find a kernel radii filename.");
	  return(FAILURE);
	}
	else if (angles_flag == 0)
	{
	  sprintf(errstr,"Unable to find a kernel angles filename.");
	  return(FAILURE);
	}
	else if (energies_flag == 0)
	{
	  sprintf(errstr,"Unable to find a kernel energies filename.");
	  return(FAILURE);
	}
	else if (primary_flag == 0)
	{
	  sprintf(errstr,"Unable to find a primary kernel filename.");
	  return(FAILURE);
	}
	else if (first_flag == 0)
	{
	  sprintf(errstr,"Unable to find a first scatter kernel filename.");
	  return(FAILURE);
	}
	else if (second_flag == 0)
	{
	  sprintf(errstr,"Unable to find a second scatter kernel filename.");
	  return(FAILURE);
	}
	else if (multiple_flag == 0)
	{
	  sprintf(errstr,"Unable to find a multiple scatter kernel filename.");
	  return(FAILURE);
	}
	else if (brem_annih_flag == 0)
	{
	  sprintf(errstr,"Unable to find a brem_annih kernel filename.");
	  return(FAILURE);
	}
	else if (total_flag == 0)
	{
	  sprintf(errstr,"Unable to find a total kernel filename.");
	  return(FAILURE);
	}
	else if (fluence_flag == 0)
	{
	  sprintf(errstr,"Unable to find a kernel fluence filename.");
	  return(FAILURE);
	}
	else if (mu_flag == 0)
	{
	  sprintf(errstr,"Unable to find a kernel mu filename.");
	  return(FAILURE);
	}
	else if (mu_en_flag == 0)
	{
	  sprintf(errstr,"Unable to find a kernel mu_en filename.");
	  return(FAILURE);
	}

	// read in the expected matrix sizes
	if ( (fid=fopen(header_filename,"r")) == NULL)
	{
		sprintf(errstr,"Missing kernel header file in kernel data folder.");
		return(FAILURE);
	}
	else
	{   
		fgets(str,100,fid); // pop-off the first line of the header
		if (fscanf(fid,"%d %d %d\n",&Nradii,&Nangles,&Nenergies) != 3)
		{
			sprintf(errstr,"Incorrect amount of data in kernel header file.");
			return(FAILURE);
		}
		fclose(fid);
	}

	mono_kernels->nkernels = Nenergies;

	// read in the energies, fluences, mu, and mu_en values
	if ( (fid = fopen(energies_filename,"rb")) == NULL)
	{
		sprintf(errstr,"Missing kernel energies file.");
		return(FAILURE);
	}
	else
	{
		if ((mono_kernels->energy = (float *)malloc(sizeof(float)*Nenergies)) == NULL)
		{
			sprintf(errstr,"Failed in memory allocation for kernel energies.");
			return(FAILURE);
		}
		if( (int)fread(mono_kernels->energy,sizeof(float),Nenergies,fid) != Nenergies)
		{
			sprintf(errstr,"Incorrect number of energies in kernel_energies file.");
			return(FAILURE);
		}
		fclose(fid);
	}

	if ( (fid = fopen(fluence_filename,"rb")) == NULL)
	{
		sprintf(errstr,"Missing kernel fluences file.");
		return(FAILURE);
	}
	else
	{
		if ((mono_kernels->fluence = (float *)malloc(sizeof(float)*Nenergies)) == NULL)
		{
			sprintf(errstr,"Failed in memory allocation for kernel fluences.");
			return(FAILURE);
		}
		if( (int)fread(mono_kernels->fluence,sizeof(float),Nenergies,fid) != Nenergies)
		{
			sprintf(errstr,"Incorrect number of fluences in kernel_fluences file.");
			return(FAILURE);
		}
		fclose(fid);
	}
	
	if ( (fid = fopen(mu_filename,"rb")) == NULL)
	{
		sprintf(errstr,"Missing kernel mu file.");
		return(FAILURE);
	}
	else
	{
		if ((mono_kernels->mu = (float *)malloc(sizeof(float)*Nenergies)) == NULL)
		{
			sprintf(errstr,"Failed in memory allocation for kernel mu.");
			return(FAILURE);
		}
		if( (int)fread(mono_kernels->mu,sizeof(float),Nenergies,fid) != Nenergies)
		{
			sprintf(errstr,"Incorrect number of mu values in kernel_mu file.");
			return(FAILURE);
		}
		fclose(fid);
	}

	if ( (fid = fopen(mu_en_filename,"rb")) == NULL)
	{
		sprintf(errstr,"Missing kernel mu_en file.");
		return(FAILURE);
	}
	else
	{
		if ((mono_kernels->mu_en = (float *)malloc(sizeof(float)*Nenergies)) == NULL)
		{
			sprintf(errstr,"Failed in memory allocation for kernel mu_en.");
			return(FAILURE);
		}
		if( (int)fread(mono_kernels->mu_en,sizeof(float),Nenergies,fid) != Nenergies)
		{
			sprintf(errstr,"Incorrect number of mu_en values in kernel_mu_en file.");
			return(FAILURE);
		}
		fclose(fid);
	}

	// Only assign memory for bin boundaries for the first kernel. Just point the other
	// boundary pointers at the values in the first kernel.

	if ( (fid = fopen(radii_filename,"rb")) == NULL)
	{
		sprintf(errstr,"Missing kernel radii file.");
		return(FAILURE);
	}
	else
	{
		mono_kernels->kernel[0].nradii = Nradii;
		if( (mono_kernels->kernel[0].radial_boundary = (float *)malloc(sizeof(float)*Nradii)) == NULL)
		{
			sprintf(errstr,"Failed to allocate memory for radial boundaries.");
			return(FAILURE);
		}
		if( (int)fread(mono_kernels->kernel[0].radial_boundary,sizeof(float),Nradii,fid) != Nradii)
		{
			sprintf(errstr,"Incorrect number of radii values in kernel_radii file.");
			return(FAILURE);
		}
		fclose(fid);
	}
	
	if ( (fid = fopen(angles_filename,"rb")) == NULL)
	{
		sprintf(errstr,"Missing kernel angles file.");
		return(FAILURE);
	}
	else
	{
		mono_kernels->kernel[0].ntheta = Nangles;
		if( (mono_kernels->kernel[0].angular_boundary = (float *)malloc(sizeof(float)*Nangles)) == NULL)
		{
			sprintf(errstr,"Failed to allocate memory for angular boundaries.");
			return(FAILURE);
		}
		if( (int)fread(mono_kernels->kernel[0].angular_boundary,sizeof(float),Nangles,fid) != Nangles)
		{
			sprintf(errstr,"Incorrect number of angular values in kernel_angles file.");
			return(FAILURE);
		}
		fclose(fid);
	}

	// allocate space for kernel matrices and copy bin boundaries for other kernel categories
	for (j=0;j<Nenergies;j++)  // loop through energies
	{
		if (j != 0)
		{
			mono_kernels->kernel[j].nradii = Nradii;
			mono_kernels->kernel[j].ntheta = Nangles;
	
			mono_kernels->kernel[j].radial_boundary = mono_kernels->kernel[0].radial_boundary;
			mono_kernels->kernel[j].angular_boundary = mono_kernels->kernel[0].angular_boundary;
		}

		// allocate space for kernels
		for (k=0;k<N_KERNEL_CATEGORIES;k++)
			if ((mono_kernels->kernel[j].matrix[k] 
				= (float *)malloc(sizeof(float)*Nradii*Nangles*N_KERNEL_CATEGORIES)) == NULL)
			{
				sprintf(errstr,"Failed to allocate memory for kernel matrix.");
				return(FAILURE);
			}
	}
	
	// load-in the kernels one at a time and fill-up the monoenergetic kernels
	
	// open the kernel files
	if ( (primary = fopen(primary_filename,"rb")) == NULL)
	{
		sprintf(errstr,"Missing primary kernel.");
		return(FAILURE);
	}

	if ( (first = fopen(first_scatter_filename,"rb")) == NULL)
	{
		sprintf(errstr,"Missing first scatter kernel.");
		return(FAILURE);
	}

	if ( (second = fopen(second_scatter_filename,"rb")) == NULL)
	{
		sprintf(errstr,"Missing second scatter kernel.");
		return(FAILURE);
	}

	if ( (multiple = fopen(multiple_scatter_filename,"rb")) == NULL)
	{
		sprintf(errstr,"Missing multiple scatter kernel.");
		return(FAILURE);
	}

	if ( (brem_annih = fopen(brem_annih_filename,"rb")) == NULL)
	{
		sprintf(errstr,"Missing brem_annih kernel.");
		return(FAILURE);
	}

	if ( (total = fopen(total_filename,"rb")) == NULL)
	{
		sprintf(errstr,"Missing total kernel.");
		return(FAILURE);
	}

	// loop through all energies, reading the kernel files in to the kernel structures
	for (j=0;j<Nenergies;j++)
	{
		if ( (int)fread(mono_kernels->kernel[j].matrix[0],sizeof(float),Nradii*Nangles,primary) 
			!= Nradii*Nangles)
		{
			sprintf(errstr,"Could not read the correct number of kernel values.");
			return(FAILURE);
		}

		if ( (int)fread(mono_kernels->kernel[j].matrix[1],sizeof(float),Nradii*Nangles,first) 
			!= Nradii*Nangles)
		{
			sprintf(errstr,"Could not read the correct number of kernel values.");
			return(FAILURE);
		}

		if ( (int)fread(mono_kernels->kernel[j].matrix[2],sizeof(float),Nradii*Nangles,second) 
			!= Nradii*Nangles)
		{
			sprintf(errstr,"Could not read the correct number of kernel values.");
			return(FAILURE);
		}

		if ( (int)fread(mono_kernels->kernel[j].matrix[3],sizeof(float),Nradii*Nangles,multiple) 
			!= Nradii*Nangles)
		{
			sprintf(errstr,"Could not read the correct number of kernel values.");
			return(FAILURE);
		}

		if ( (int)fread(mono_kernels->kernel[j].matrix[4],sizeof(float),Nradii*Nangles,brem_annih) 
			!= Nradii*Nangles)
		{
			sprintf(errstr,"Could not read the correct number of kernel values.");
			return(FAILURE);
		}
	}

	// close the kernel files
	fclose(primary);
	fclose(first);
	fclose(second);
	fclose(multiple);
	fclose(brem_annih);

	return(SUCCESS);
}

int load_geometry(FLOAT_GRID *density, char geometry_filenames[])
/* Ensure that the GEOMETRY structure has the following format:
  Geometry = 

         start: [3 element float]
    voxel_size: [3 element float]
          data: [M x N x Q float]
          beam: [1x1 struct] 
		  
 Geometry.beam = 

    ip: [3 element float]
    jp: [3 element float]
    kp: [3 element float]
     y_vec: [3 element float]
        xp: [float scalar]
        yp: [float scalar]
    del_xp: [float scalar]
    del_yp: [float scalar]
	   SAD: [float scalar]
	

	and load the data into memory.  

The names of the files containing the above data are listed in two files:
geometry_filenames and beam_filenames.  The beam data are stored in a 
separate file since many dose calculations are done by changing the 
beam data and leaving the geometry data constant.  This way one can use
a separate beam file for each beam but the same geometry file.
*/
{
	int Ntotal;
	char str[200];   // dummy string
	char header_filename[200], density_filename[200];
	// flags for filename readin
	int header_flag = 0;
	int density_flag = 0;
	FILE *fid;          // dummy filename

	// read in the geometry filenames
	if ( (fid = fopen(geometry_filenames,"r")) == NULL)  // open the geometry filenames
	{
	  sprintf(errstr,"Could not open the geometry filenames file\n");
	  return(FAILURE);
	}

	// read in the non-beam geometric data
	while (fscanf(fid,"%s\n",str) != EOF)  // read until the end of the file
	{
	  if (!strcmp(str,geometry_header_line))
	    if (fscanf(fid,"%s\n",header_filename) != 1)
		{
			sprintf(errstr,"Failed to read-in the geometry_header filename from the geometry filenames file.");
		}
	    else
	      header_flag = 1;
	  else if (!strcmp(str,geometry_density_line))
	    if (fscanf(fid,"%s\n",density_filename) != 1)
		{
	        sprintf(errstr,"Failed to read-in the geometry_density filename from the geometry filenames file.");
			return(FAILURE);
		}
	    else
	      density_flag = 1;
	  else
	  {   
			sprintf("Unrecognized string in the geometry filenames file: %s\n",str);
			return(FAILURE);   
	  }
	}
	
    // confirm that all of the required filenames have been found
	if (header_flag == 0)
	{
	  sprintf(errstr,"Unable to find a geometry header filename.\n");
	  return(FAILURE);
	}
	else if (density_flag == 0)
	{
	  sprintf(errstr,"Unable to find a geometry density filename.\n");
	  return(FAILURE);
	}

	// read in geometric and beam data
	if( (fid = fopen(header_filename,"r")) == NULL)
	{
		sprintf(errstr,"Could not open geometry header file.");
		return(FAILURE);
	}
	else
	{
		// pop-off the first line of the header file
		if (fgets(str,100,fid) == NULL) 
		{
			sprintf(errstr,"Could not read from geometry header file.");
			return(FAILURE);
		}

		// read-in the CT data grid size
		if (fscanf(fid,"%d %d %d\n",&density->x_count,&density->y_count,&density->z_count) != 3)
		{
			sprintf(errstr,"Could not read-in data grid size.");
			return(FAILURE);
		}
		
		// pop-off the next line of the header file
		if (fgets(str,100,fid) == NULL) 
		{
			sprintf(errstr,"Could not read from geometry header  file.");
			return(FAILURE);
		}

		// read-in the CT data grid size
		if (fscanf(fid,"%f %f %f\n",&density->start.x,&density->start.y,&density->start.z) != 3)
		{
			sprintf(errstr,"Could not read-in density grid start position.");
			return(FAILURE);
		}

		// pop-off the next line of the header file
		if (fgets(str,100,fid) == NULL) 
		{
			sprintf(errstr,"Could not read from geometry header file.");
			return(FAILURE);
		}

		// read-in the CT data grid size
		if (fscanf(fid,"%f %f %f\n",&density->inc.x,&density->inc.y,&density->inc.z) != 3)
		{
			sprintf(errstr,"Could not read-in voxel size vector.");
			return(FAILURE);
		}

		Ntotal = density->x_count*density->y_count*density->z_count;
	}

	// read-in the CT density data
	if( (fid = fopen(density_filename,"rb")) == NULL)
	{
		sprintf(errstr,"Could not open CT density file.");
		return(FAILURE);
	}
	else
	{
		if( (density->matrix = (float *)malloc(sizeof(float)*Ntotal)) == NULL)
		{
			sprintf(errstr,"Unable to allocate space for CT density grid.");
			return(FAILURE);
		}
		else if ((int)fread(density->matrix,sizeof(float),Ntotal,fid) != Ntotal)
		{
			sprintf(errstr,"Unable to read-in CT density data.");
			return(FAILURE);
		}
	}
	return(SUCCESS);
}

int pop_beam(BEAM *bm, FILE *beamspec_batch_file)
/*  Pops a beam off of the beamspec_batch_file file and loads it into a BEAM structure.

  Ensure that the beam data file has the following format:
 Geometry.beam = 

        ip: [3 element float]
        jp: [3 element float]
        kp: [3 element float]
     y_vec: [3 element float]
        xp: [float scalar]
        yp: [float scalar]
    del_xp: [float scalar]
    del_yp: [float scalar]
	   SAD: [float scalar]
	   num: [int scalar]
	
	and load the data into memory.  
*/
{
	char str[200];      // dummy string

	// read-in the beam data
	// pop-off the first line of the beam data file

	// read-in the CT data grid size
	if (fgets(str,100,beamspec_batch_file) == NULL) 
	{
		sprintf(errstr,"Could not read from beam data file.");
		return(FAILURE);
	}

	if (fscanf(beamspec_batch_file,"%d\n",&bm->num) != 1)
	{
		sprintf(errstr,"Could not read-in beam data.");
		return(FAILURE);
	}

	if (fgets(str,100,beamspec_batch_file) == NULL) 
	{
		sprintf(errstr,"Could not read from beam data file.");
		return(FAILURE);
	}

	// read-in the CT data grid size
	if (fscanf(beamspec_batch_file,"%f %f %f %f %f\n",&bm->SAD,&bm->xp,&bm->yp,&bm->del_xp,&bm->del_yp) != 5)
	{
		sprintf(errstr,"Could not read-in beam data.");
		return(FAILURE);
	}

	// pop-off the next line of the beam data file
	if (fgets(str,100,beamspec_batch_file) == NULL) 
	{
		sprintf(errstr,"Could not read from from beam data file.");
		return(FAILURE);
	}

	// read-in the source position vector
	if (fscanf(beamspec_batch_file,"%f %f %f\n",&bm->y_vec[0],&bm->y_vec[1],&bm->y_vec[2]) != 3)
	{
		sprintf(errstr,"Could not read-in source location vector.");
		return(FAILURE);
	}

	// pop-off the next line of the beam data file
	if (fgets(str,100,beamspec_batch_file) == NULL) 
	{
		sprintf(errstr,"Could not read from from beam data file.");
		return(FAILURE);
	}

	// read-in the beam's eye view vectors, ip first
	if (fscanf(beamspec_batch_file,"%f %f %f\n",&bm->ip[0],&bm->ip[1],&bm->ip[2]) != 3)
	{
		sprintf(errstr,"Could not read-in ip vector.");
		return(FAILURE);
	}

	// pop-off the next line of the beam data file
	if (fgets(str,100,beamspec_batch_file) == NULL) 
	{
		sprintf(errstr,"Could not read from from beam data file.");
		return(FAILURE);
	}

	// read-in the second beam's eye view vector, jp
	if (fscanf(beamspec_batch_file,"%f %f %f\n",&bm->jp[0],&bm->jp[1],&bm->jp[2]) != 3)
	{
		sprintf(errstr,"Could not read-in jp vector.");
		return(FAILURE);
	}

	// pop-off the next line of the beam data file
	if (fgets(str,100,beamspec_batch_file) == NULL) 
	{
		sprintf(errstr,"Could not read from from beam data file.");
		return(FAILURE);
	}

	// read-in the third beam's eye view vector, kp
	if (fscanf(beamspec_batch_file,"%f %f %f\n",&bm->kp[0],&bm->kp[1],&bm->kp[2]) != 3)
	{
		sprintf(errstr,"Could not read-in kp vector.");
		return(FAILURE);
	}
	
	// ensure that ip,jp,kp are orthonormal and form a right-handed coordinate system
	if (   (fabs(bm->ip[0]*bm->ip[0] + bm->ip[1]*bm->ip[1] + bm->ip[2]*bm->ip[2] - 1.0) > 5e-6)
		|| (fabs(bm->jp[0]*bm->jp[0] + bm->jp[1]*bm->jp[1] + bm->jp[2]*bm->jp[2] - 1.0) > 5e-6)
		|| (fabs(bm->kp[0]*bm->kp[0] + bm->kp[1]*bm->kp[1] + bm->kp[2]*bm->kp[2] - 1.0) > 5e-6)
		|| (fabs(bm->ip[0]*bm->jp[0] + bm->ip[1]*bm->jp[1] + bm->ip[2]*bm->jp[2]) > 5e-6)
		|| (fabs(bm->ip[0]*bm->kp[0] + bm->ip[1]*bm->kp[1] + bm->ip[2]*bm->kp[2]) > 5e-6)
		|| (fabs(bm->jp[0]*bm->kp[0] + bm->jp[1]*bm->kp[1] + bm->jp[2]*bm->kp[2]) > 5e-6))
	{
		sprintf(errstr,"Beam's eye view unit vectors ip, jp, and kp must be orthonormal.");
		return(FAILURE);
	}

	// check that cross(ip,jp) = kp
	if (   (fabs(bm->ip[1]*bm->jp[2] - bm->ip[2]*bm->jp[1] - bm->kp[0]) > 5e-6)
		|| (fabs(bm->ip[2]*bm->jp[0] - bm->ip[0]*bm->jp[2] - bm->kp[1]) > 5e-6)
		|| (fabs(bm->ip[0]*bm->jp[1] - bm->ip[1]*bm->jp[0] - bm->kp[2]) > 5e-6))
	{
		sprintf(errstr,"Must have cross(ip,jp) = kp for beam's eye view");
		return(FAILURE);
	}

	return(SUCCESS);
}
