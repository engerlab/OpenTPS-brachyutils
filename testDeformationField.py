from Process.DeformationField import *
from Process.PatientData import *

CT_path = '/mnt/c/Users/vhamaide/Desktop/UCL/ARIES/data/liver/patient_0/MidP_CT'
Patients = PatientList()
Patients.list_dicom_files(CT_path, 1)
Patients.list[0].import_patient_data()
CT_list = [Patients.list[0].CTimages[0]]
ct = CT_list[0]

def_path = '/mnt/c/Users/vhamaide/Desktop/UCL/ARIES/data/liver/patient_0/deformation_fields/df_p0_to_MidP_log.dcm'
df = DeformationField()
df.DcmFile = def_path
df.import_Dicom_DF(CT_list)

dose_image = df.Image
ct_img = ct.Image.transpose(1,0,2)
print("ct.shape",ct_img.shape)
print("df.shape",dose_image.shape)

# Plot X-Y field
u = dose_image[:,:,86,0]
v = dose_image[:,:,86,1]
fig, ax = plt.subplots(2,2)
ax[0,0].imshow(ct_img[:,:,86].T[::3,::3], cmap='gray', origin='upper')
ax[0,0].quiver(u.T[::3,::3],v.T[::3,::3], alpha=0.5, color='red')
ax[0,0].set_xlabel('x')
ax[0,0].set_ylabel('y')
ax[0,0].set_title('x-y for z=86')
#ax[0,0].set_ylim(ax[0,0].get_ylim()[1], ax[0,0].get_ylim()[0]) # inverse y axis to have 0,0 start at upper left

# Plot X-Z field
compX = dose_image[:,297,:,0]
compZ = dose_image[:,297,:,2]
ax[0,1].imshow(ct_img[:,297,:].T[::3,::3], cmap='gray', origin='upper')
ax[0,1].quiver(compX.T[::3,::3],compZ.T[::3,::3], alpha=0.5, color='red')
ax[0,1].set_xlabel('x')
ax[0,1].set_ylabel('z')
ax[0,1].set_title('x-z for y=297')
#ax[0,1].set_ylim(ax[0,1].get_ylim()[1], ax[0,1].get_ylim()[0])

# Plot Y-Z field
compY = dose_image[167,:,:,1]
compZ = dose_image[167,:,:,2]
ax[1,0].imshow(ct_img[167,:,:].T[::3,::3], cmap='gray', origin='upper')
ax[1,0].quiver(compY.T[::3,::3],compZ.T[::3,::3], alpha=0.5, color='red')
ax[1,0].set_xlabel('y')
ax[1,0].set_ylabel('z')
# ax[1,0].set_ylim(ax[1,0].get_ylim()[1], ax[1,0].get_ylim()[0])
ax[1,0].set_title('y-z for x=167')
plt.show()

# Plot CT sagittal view
# ax[1,1].imshow(ct.Image[280,:,:][::3,::3], cmap='gray', origin='upper')
# ax[1,1].set_xlabel('x')
# ax[1,1].set_ylabel('z')
# ax[1,1].set_title('coronal slice 280')
# plt.show()