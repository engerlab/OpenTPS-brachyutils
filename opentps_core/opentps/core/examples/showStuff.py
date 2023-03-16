from matplotlib import pyplot as plt
from matplotlib.animation import FuncAnimation


def showModelWithAnimatedFields(model):

    for field in model.deformationList:
        field.resample(spacing=model.midp.spacing, gridSize=model.midp.gridSize, origin=model.midp.origin)

    y_slice = int(model.midp.gridSize[1] / 2)

    plt.figure()
    fig = plt.gcf()



    def updateAnim(imageIndex):
        fig.clear()
        compX = model.deformationList[imageIndex].velocity.imageArray[:, y_slice, :, 0]
        compZ = model.deformationList[imageIndex].velocity.imageArray[:, y_slice, :, 2]
        plt.imshow(model.midp.imageArray[:, y_slice, :][::5, ::5], cmap='gray')
        plt.quiver(compZ[::5, ::5], compX[::5, ::5], alpha=0.2, color='red', angles='xy', scale_units='xy', scale=5)

    anim = FuncAnimation(fig, updateAnim, frames=len(model.deformationList), interval=300)
    # anim.save('D:/anim.gif')
    plt.show()
