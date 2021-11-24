import numpy as np
from pydicom.uid import generate_uid

from Process.Registration import *
from Core.Data.patientData import PatientData

class Dynamic3DModel(PatientData):

    def __init__(self):
        self.SOPInstanceUID = ""
        self.ModelName = "MidP"
        self.motionFieldList = []
        self.midp = []

    def computeMidPositionImage(self, CT4D, ref_index=0, morphon_resolution=2.5, nb_processes=-1):

        if ref_index >= len(CT4D.dyn3DImageList):
            print("Reference index is out of bound")
            return -1

        average_field = DeformationField()

        # perform registrations
        self.motionFieldList = []

        for i in range(len(CT4D.dyn3DImageList)):

            if i == ref_index:
                self.motionFieldList.append(DeformationField())
            else:
                print('\nRegistering phase', ref_index , 'to phase', i, '...')
                reg = Registration(CT4D.dyn3DImageList[i], CT4D.dyn3DImageList[ref_index])
                self.motionFieldList.append(reg.Registration_morphons(base_resolution=morphon_resolution, nb_processes=nb_processes))
                field_shape = self.motionFieldList[i].Velocity.shape[0:3]
                if (max(average_field.GridSize) == 0):
                    average_field.Init_Field_Zeros(field_shape)

            average_field.Velocity += self.motionFieldList[i].Velocity

        self.motionFieldList[ref_index].Init_Field_Zeros(field_shape)
        average_field.Velocity /= len(self.motionFieldList)

        # compute fields to midp
        for i in range(len(CT4D.dyn3DImageList)):
            self.motionFieldList[i].FieldName = 'def ' + CT4D.dyn3DImageList[i].ImgName
            self.motionFieldList[i].Velocity = average_field.Velocity - self.motionFieldList[i].Velocity

        # deform images
        def3DImageList = []
        for i in range(len(CT4D.dyn3DImageList)):
            def3DImageList.append(self.motionFieldList[i].deform_image(CT4D.dyn3DImageList[i],
                                                                                fill_value='closest'))

        # invert fields (to have them from midp to phases)
        for i in range(len(CT4D.dyn3DImageList)):
            self.motionFieldList[i].Displacement = []
            self.motionFieldList[i].Velocity = -self.motionFieldList[i].Velocity

        # compute MidP
        self.midp = CT4D.dyn3DImageList[0].copy()
        self.midp.SOPInstanceUID = generate_uid()
        self.midp.Image = np.median(def3DImageList, axis=0)

        # set SOPInstanceUID
        self.SOPInstanceUID = self.midp.SOPInstanceUID


    def generate3DImage(self, phase, amplitude=1.0):
        if not(bool(self.midp)):
            print('Model is empty. Mid-position image must be computed first.')
            return

        phase *= len(self.motionFieldList)
        phase1 = np.floor(phase) % len(self.motionFieldList)
        phase2 = np.ceil(phase) % len(self.motionFieldList)

        field = self.motionFieldList[int(phase1)].copy()
        field.Displacement = []
        if phase1 == phase2:
            field.Velocity = amplitude * self.motionFieldList[int(phase1)].Velocity
        else:
            w1 = abs(phase - np.ceil(phase))
            w2 = abs(phase - np.floor(phase))
            if abs(w1+w2-1.0) > 1e-6:
                print('Error in phase interpolation.')
                return
            field.Velocity = amplitude * (w1 * self.motionFieldList[int(phase1)].Velocity + w2 * self.motionFieldList[int(phase2)].Velocity)

        output = self.midp.copy()
        output.Image = field.deform_image(self.midp, fill_value='closest')

        return output