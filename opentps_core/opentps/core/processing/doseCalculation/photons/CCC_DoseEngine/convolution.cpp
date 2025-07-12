/* Cconvolution.cpp */

#include "defs.h"

//function prototypes

int load_kernels(MONO_KERNELS *, char []);
int load_geometry(FLOAT_GRID *, char []);
int pop_beam(BEAM *, FILE *);
int calc_deff(FLOAT_GRID *,FLOAT_GRID *, FLOAT_GRID *, BEAM *);
int terma_kerma(FLOAT_GRID *,FLOAT_GRID *,FLOAT_GRID *,MONO_KERNELS *,FLOAT_GRID *);
int make_poly_kernel(MONO_KERNELS *, KERNEL *);
int calc_dose(FLOAT_GRID *,FLOAT_GRID *,FLOAT_GRID *,KERNEL *,BEAM *, FLOAT_GRID *);
int terma_dose_masks(FLOAT_GRID *, FLOAT_GRID *, BEAM *);
int convolution(MONO_KERNELS *, BEAM *, FLOAT_GRID *, FILE *);

char errstr[200];  // error string that all routines have access to

int main(int argc, char *argv[])
//  Expects four input arguments: 
// 1)  kernel_filenames -- contains a list of the kernel files
// 2)  geometry_filenames  -- contains a list of the geometry files
// 3)  beamspec batch file -- locations of beamspec files in batch
// 4)  beamlet batch   -- locations of resulting beamlets in batch
{
	int i,j,b,B;

	char tmpstr[200];

	FLOAT_GRID density;

	MONO_KERNELS mono_kernels;

	BEAM beam;

	FILE *beamspec_batch_file;
	FILE *beamlet_batch_file;

	/*	// print the arguments
	printf("Input arguments:\n");
	for (j=1;j<argc;j++)
	printf("%s\n",argv[j]); */

	if (argc != 5)
	{
		printf("Expecting four input command line arguments, received %d.\n",argc);
		return(FAILURE);
	}

	if (load_kernels(&mono_kernels,argv[1]) == FAILURE)
	{
		sprintf(tmpstr,"Failed at loading the kernels.\n");
		strcat(tmpstr,errstr);
		strcpy(errstr,tmpstr);
		printf("%s\n",errstr);
		return(FAILURE);
	}
        printf("Successfully loaded kernels\n");

	if (load_geometry(&density,argv[2]) == FAILURE)
	{
		sprintf(tmpstr,"Failed at loading the geometry.\n");
		strcat(tmpstr,errstr);
		strcpy(errstr,tmpstr);
		printf("%s\n",errstr);
		return(FAILURE);
	}
        printf("Successfully loaded geometry files.\n");

	/* 
	// diagnostic lines
	printf("SAD = %lf \n",beam.SAD);
	printf("xp = %lf \n",beam.xp);
	printf("yp = %lf \n",beam.yp);
	printf("del_xp = %lf \n",beam.del_xp);
	printf("del_yp = %lf \n",beam.del_yp);
	printf("y_vec = (%lf,%lf,%lf) \n",beam.y_vec[0],beam.y_vec[1],beam.y_vec[2]);
	printf("ip = (%lf,%lf,%lf) \n",beam.ip[0],beam.ip[1],beam.ip[2]);
	printf("jp = (%lf,%lf,%lf) \n",beam.jp[0],beam.jp[1],beam.jp[2]);
	printf("kp = (%lf,%lf,%lf) \n",beam.kp[0],beam.kp[1],beam.kp[2]);

	printf("Xcount = %d, Ycount = %d, Zcount = %d \n",density.x_count,density.y_count,density.z_count);
	printf("start = (%lf,%lf,%lf) \n",density.start.x,density.start.y,density.start.z);
	printf("inc = (%lf,%lf,%lf) \n",density.inc.x,density.inc.y,density.inc.z); */


	// open the beam specification batch file
	if ((beamspec_batch_file = fopen(argv[3],"r")) == NULL)
	{
		printf("Failed to open beamspec batch file %s\n",argv[3]);
		return(FAILURE);
	}
        printf("Successfully loaded beamspec files.\n");

	// open the dose batch file
	if ((beamlet_batch_file = fopen(argv[4],"wb")) == NULL)
	{
		printf("Failed to open beamlet batch file %s\n",argv[4]);
		return(FAILURE);
	}

	// get the number of beams from the beamspec batch file
	if (fgets(tmpstr,100,beamspec_batch_file) == NULL)  // pop off the first line
	{
		sprintf(errstr,"Could not read from beam data file.");
		printf("%s\n",errstr);
		return(FAILURE);
	}

	if (fscanf(beamspec_batch_file,"%d\n",&B) != 1)
	{
		sprintf(errstr,"Could not read-in number of beams from beamspec file.");
		printf("%s\n",errstr);
		return(FAILURE);
	}

	// write the number of beamlets in this batch as the first entry
	fwrite(&B,sizeof(int),1,beamlet_batch_file); 

	// Do convolution calculations for all consistent beamspec and dose
	// filenames.  If a calculation for a beamlet fails, print an error 
	// and move on to the next beamspec file.
	for (b=0;b<B;b++)
	{
		// pop off a beam
		if(pop_beam(&beam,beamspec_batch_file) == FAILURE)
		{
			sprintf(tmpstr,"Failed to load beamspec number %d:\n",b);
			strcat(tmpstr,errstr);
			strcpy(errstr,tmpstr);
			printf("%s\n",errstr);
		}
		else if (convolution(&mono_kernels,&beam,&density,beamlet_batch_file) == FAILURE)
		// An error occurred, so print the error string to standard out
		// but do not terminate the remaining beam batches.
		{
			j = 0;
			fwrite(&beam.num,sizeof(int),1,beamlet_batch_file);
			fwrite(&density.x_count,sizeof(int),1,beamlet_batch_file);
			fwrite(&density.y_count,sizeof(int),1,beamlet_batch_file);
			fwrite(&density.z_count,sizeof(int),1,beamlet_batch_file);
			fwrite(&j,sizeof(int),1,beamlet_batch_file);
			printf("Error in the calculation for beamlet number %d,\n so all zeros were saved for the resulting beamlet file.\n",b);
			printf("%s\n",errstr);
		}
		else
			printf("Successfully calculated beamlet %d of %s.\n",b,argv[3]); 
	}

	// close the beamlet file
	fclose(beamlet_batch_file);

	// free the density grid
	free(density.matrix);

	// only need to free angular and radial boundaries for the first
	// kernel, since other kernel boundaries just point to the same place
	free(mono_kernels.kernel[0].angular_boundary);
	free(mono_kernels.kernel[0].radial_boundary);

	// free the kernels
	free(mono_kernels.energy);
	free(mono_kernels.fluence);
	free(mono_kernels.mu);
	free(mono_kernels.mu_en);
 	for (i=0;i<mono_kernels.nkernels;i++)
		for (j=0;j<N_KERNEL_CATEGORIES;j++)
			free(mono_kernels.kernel[i].matrix[j]); 

	return(SUCCESS);
}

int convolution(MONO_KERNELS *mono_kernels, BEAM *beam, FLOAT_GRID *density, FILE *beamlet_batch_file)
// routine that actually performs the convolution for a given kernel, beam, and geometry
{
	int i,j,M,N,Q,Nind,Ntotal;  // dimensions of the CT density grid
	int *dose_ind;
	float *dose_data, doseMax;
	char tmpstr[200];  // temporary string

	FLOAT_GRID terma_mask;
	FLOAT_GRID dose_mask;
	FLOAT_GRID deff;
	FLOAT_GRID terma;
	FLOAT_GRID kermac;
	FLOAT_GRID dose;

	KERNEL poly_kernel;

	// copy the density grid dimensions to the calculation grids
	copy_grid_geometry(density,&terma_mask);
	copy_grid_geometry(density,&dose_mask);
	copy_grid_geometry(density,&deff);
	copy_grid_geometry(density,&terma);
	copy_grid_geometry(density,&kermac);
	copy_grid_geometry(density,&dose);

	// dimensions of all the grids
	M = density->x_count;
	N = density->y_count;
	Q = density->z_count;

	Ntotal = M*N*Q;

	// Allocate memory for all of the grids and fill them all with zeros
	if ((terma_mask.matrix = (float *)malloc(sizeof(float)*Ntotal)) == NULL)
	{
		sprintf(errstr,"Could not allocate memory for terma_mask.");
		return(FAILURE);
	}

	if ((dose_mask.matrix = (float *)malloc(sizeof(float)*Ntotal)) == NULL)
	{
		sprintf(errstr,"Could not allocate memory for dose_mask.");
		return(FAILURE);
	}

	if ((deff.matrix = (float *)malloc(sizeof(float)*Ntotal)) == NULL)
	{
		sprintf(errstr,"Could not allocate memory for deff.");
		return(FAILURE);
	}

	if ((terma.matrix = (float *)malloc(sizeof(float)*Ntotal)) == NULL)
	{
		sprintf(errstr,"Could not allocate memory for terma.");
		return(FAILURE);
	}

	if ((kermac.matrix = (float *)malloc(sizeof(float)*Ntotal)) == NULL)
	{
		sprintf(errstr,"Could not allocate memory for kermac.");
		return(FAILURE);
	}

	if ((dose.matrix = (float *)malloc(sizeof(float)*Ntotal)) == NULL)
	{
		sprintf(errstr,"Could not allocate memory for dose.");
		return(FAILURE);
	}
	
	for (i=0;i<Ntotal;i++)
	{
		terma_mask.matrix[i] = 0.0;
		dose_mask.matrix[i] = 0.0;
		deff.matrix[i] = 0.0;
		terma.matrix[i] = 0.0;
		kermac.matrix[i] = 0.0;
		dose.matrix[i] = 0.0;
	} 
	
	/* start calculations */

	// If a failure occurs in any calculation, append the error
	// onto the error string and then return a FAILURE.

	// create terma and dose masks
	if (SUCCESS != terma_dose_masks(&terma_mask,&dose_mask,beam))
	{
		sprintf(tmpstr,"Failed in terma_dose_masks!\n");
		strcat(tmpstr,errstr);
		strcpy(errstr,tmpstr);
		return(FAILURE);
	}

	//create polyenergetic kernel from mono kernels and fluence,mu data
	if (SUCCESS != make_poly_kernel(mono_kernels,&poly_kernel) )
	{
		sprintf(tmpstr,"Failed making polyenergetic kernel!\n");
		strcat(tmpstr,errstr);
		strcpy(errstr,tmpstr);
		return(FAILURE);
	}
	
	//create effective depth array from density array
	if (SUCCESS != calc_deff(density,&deff,&terma_mask,beam))
	{
		sprintf(tmpstr,"Failed in calc_deff!\n");
		strcat(tmpstr,errstr);
		strcpy(errstr,tmpstr);
		return(FAILURE);
	}
        // printf("Successfully calculated deff for beam %d.\n", beam->num);

	//create kerma and terma arrays
	//note kerma is collision kerma and is used for a kernel hardening correction
	if (SUCCESS != terma_kerma(&deff,&terma,&kermac,mono_kernels,&terma_mask))
	{
		sprintf(tmpstr,"Failed in terma_kerma calculation!\n");
		strcat(tmpstr,errstr);
		strcpy(errstr,tmpstr);
		return(FAILURE);
	}
        // printf("Successfully calculated terma for beam %d.\n", beam->num);

	//use all this stuff to calculate dose
	if ( (SUCCESS != calc_dose(density,&terma,&dose,&poly_kernel,beam,&dose_mask)) ) 
	{
		sprintf(tmpstr,"Failed calculating dose!\n");
		strcat(tmpstr,errstr);
		strcpy(errstr,tmpstr);
		return(FAILURE);
	}
        // printf("Successfully calculated dose for beam %d.\n", beam->num);

	/* //diagnostic lines:
	FILE *fid;
	fid = fopen("dose.bin","wb");
	fwrite(dose.matrix,sizeof(float),Ntotal,fid);
	fclose(fid);

	fid = fopen("terma.bin","wb");
	fwrite(terma.matrix,sizeof(float),Ntotal,fid);
	fclose(fid);

	fid = fopen("kermac.bin","wb");
	fwrite(kermac.matrix,sizeof(float),Ntotal,fid);
	fclose(fid);

	fid = fopen("deff.bin","wb");
	fwrite(deff.matrix,sizeof(float),Ntotal,fid);
	fclose(fid);

	fid = fopen("terma_mask.bin","wb");
	fwrite(terma_mask.matrix,sizeof(float),Ntotal,fid);
	fclose(fid);

	fid = fopen("dose_mask.bin","wb");
	fwrite(dose_mask.matrix,sizeof(float),Ntotal,fid);
	fclose(fid);

	fid = fopen("density.bin","wb");
	fwrite(density->matrix,sizeof(float),Ntotal,fid);
	fclose(fid); //*/

    // find maximum dose
	doseMax = 0.0;
	for (i=0;i<Ntotal;i++)
		if (dose.matrix[i] > doseMax)
			doseMax = dose.matrix[i];

	// count the number of non-zero dose values
	Nind = 0;
	for (i=0;i<Ntotal;i++)
		if (dose.matrix[i] >= doseMax*doseCutoffThreshold
			&& dose.matrix[i] > 0.0)
			Nind++;
		else
			dose.matrix[i] = 0.0;  // turn off doses below threshold

	// allocate memory for sparse dose data
	dose_ind = (int *)malloc(sizeof(int)*Nind);
	dose_data = (float *)malloc(sizeof(float)*Nind);

	// store the sparse data	
	j = 0;   // index just for the sparse data
	for (i=0;i<Ntotal;i++)
		if (dose.matrix[i] >= doseMax*doseCutoffThreshold
			&& dose.matrix[i] > 0.0)
		{
			dose_ind[j] = i;
			dose_data[j] = dose.matrix[i];
			j++; 
		}

	// save dose to a file

	// save the total file size first, then the number of non-zero elements
	fwrite(&beam->num,sizeof(int),1,beamlet_batch_file);
	fwrite(&M,sizeof(int),1,beamlet_batch_file);
	fwrite(&N,sizeof(int),1,beamlet_batch_file);
	fwrite(&Q,sizeof(int),1,beamlet_batch_file);
    fwrite(&Nind,sizeof(int),1,beamlet_batch_file);
	fwrite(dose_ind,sizeof(int),Nind,beamlet_batch_file);
	fwrite(dose_data,sizeof(float),Nind,beamlet_batch_file);

	free(dose_ind);
	free(dose_data);

	// free the calculation grids
	free(terma_mask.matrix);
	free(dose_mask.matrix);
	free(deff.matrix);
	free(terma.matrix);
	free(kermac.matrix);
	free(dose.matrix);

	free(poly_kernel.angular_boundary);
	free(poly_kernel.radial_boundary);
	// free(poly_kernel.total_matrix);
	for (j=0;j<N_KERNEL_CATEGORIES;j++)
		free(poly_kernel.matrix[j]);

	return(SUCCESS);
}

