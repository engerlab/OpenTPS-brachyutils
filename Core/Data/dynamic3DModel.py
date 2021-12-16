import numpy as np
from pydicom.uid import generate_uid

from Core.Data.patientData import PatientData
from Core.Data.Images.deformation3D import Deformation3D
from Core.Processing.Registration.registrationMorphons import RegistrationMorphons


class Dynamic3DModel(PatientData):

    def __init__(self):
        super().__init__()
        self.SOPInstanceUID = ""
        self.ModelName = "MidP"
        self.motionFieldList = []
        self.midp = []

    def computeMidPositionImage(self, CT4D, refIndex=0, morphonsResolution=2.5, nbProcesses=-1):

        if refIndex >= len(CT4D.dyn3DImageList):
            print("Reference index is out of bound")
            return -1

        averageField = Deformation3D()

        # perform registrations
        self.motionFieldList = []

        for i in range(len(CT4D.dyn3DImageList)):

            if i == refIndex:
                self.motionFieldList.append(Deformation3D())
            else:
                print('\nRegistering phase', refIndex, 'to phase', i, '...')
                reg = RegistrationMorphons(CT4D.dyn3DImageList[i], CT4D.dyn3DImageList[refIndex], baseResolution=morphonsResolution, nbProcesses=nbProcesses)
                self.motionFieldList.append(reg.compute())
                if (max(averageField.getGridSize()) == 0):
                    averageField.initFromImage(self.motionFieldList[i])

            averageField.data += self.motionFieldList[i].data

        self.motionFieldList[refIndex].initFromImage(averageField)
        averageField.velocity /= len(self.motionFieldList)

        # compute fields to midp
        for i in range(len(CT4D.dyn3DImageList)):
            self.motionFieldList[i].FieldName = 'def ' + CT4D.dyn3DImageList[i].ImgName
            self.motionFieldList[i].velocity = averageField.velocity - self.motionFieldList[i].velocity

        # deform images
        def3DImageList = []
        for i in range(len(CT4D.dyn3DImageList)):
            def3DImageList.append(self.motionFieldList[i].deform_image(CT4D.dyn3DImageList[i],
                                                                                fillValue='closest'))

        # invert fields (to have them from midp to phases)
        for i in range(len(CT4D.dyn3DImageList)):
            self.motionFieldList[i].displacement = []
            self.motionFieldList[i].velocity = -self.motionFieldList[i].velocity

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
        field.displacement = []
        if phase1 == phase2:
            field.velocity = amplitude * self.motionFieldList[int(phase1)].velocity
        else:
            w1 = abs(phase - np.ceil(phase))
            w2 = abs(phase - np.floor(phase))
            if abs(w1+w2-1.0) > 1e-6:
                print('Error in phase interpolation.')
                return
            field.velocity = amplitude * (w1 * self.motionFieldList[int(phase1)].velocity + w2 * self.motionFieldList[int(phase2)].velocity)

        output = self.midp.copy()
        output.Image = field.deform_image(self.midp, fillValue='closest')

        return output
