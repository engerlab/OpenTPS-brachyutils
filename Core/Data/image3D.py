
class Image3D:
    def __init__(self, data=None, origin=(0, 0, 0), spacing=(1, 1, 1)):
        self.data = data
        self.origin = origin
        self.spacing = spacing

    def __str__(self):
        gs = self.getGridSize()
        s = 'Image3D ' + str(gs[0]) + 'x' +  str(gs[1]) + 'x' +  str(gs[2]) + '\n'
        return s

    def getGridSize(self):
        if self.data is None:
            return (0, 0, 0)

        return self.data.shape
