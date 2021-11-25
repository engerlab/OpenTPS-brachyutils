import matplotlib.pyplot as plt
import numpy as np
from Process.Dyn2DSequence import Dynamic2DSequence
from Process.Image2D import image2D
import math


def fluoroscopy_sim(angleList, Dyn4DSeq, patient, orientation='Axial'):

    try:
        import tomopy

        for anglesAndOri in angleList:

            angle = anglesAndOri[0]
            orientation = anglesAndOri[1]

            fluoroSeq = Dynamic2DSequence()
            fluoroSeq.type = 'Fluoroscopy simulation'
            fluoroSeq.projectionAngle = angle
            fluoroSeq.SequenceName = 'FluoSim_' + anglesAndOri[1] + '_' + str(int(np.round(angle*360/(2*math.pi))))
            for imageIndex, image in enumerate(Dyn4DSeq.dyn3DImageList):

                # to rotate around Z axis
                if orientation == 'Axial':
                    imageToUse = image.Image.transpose(2, 1, 0)
                if orientation == 'Coronal':
                    imageToUse = image.Image.transpose(1, 2, 0)
                if orientation == 'Sagittal':
                    imageToUse = image.Image.transpose(0, 2, 1)

                print('! ! ! in fluoroscopy_sim --> les orientation et transpose ici sont à vérifier! ! !')
                fluoSimImage = tomopy.project(imageToUse, angle)[0]

                # plt.figure()
                # plt.imshow(fluoSimImage)
                # plt.show()

                image_2D = image2D()
                image_2D.Image = fluoSimImage
                image_2D.ImgName = str(imageIndex + 1)
                image_2D.PixelSpacing = [1, 1]
                fluoroSeq.dyn2DImageList.append(image_2D)
                fluoroSeq.isLoaded = True

            patient.Dyn2DSeqList.append(fluoroSeq)

    except:
        print("No module tomopy available")

