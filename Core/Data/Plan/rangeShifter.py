class RangeShifter:
    def __init__(self):
        self.ID = ''
        self.type = ''
        self.material = -1
        self.density = 0.0
        self.WET = 0.0

    def __str__(self):
        s = ''
        s = s + 'RS_ID = ' + self.ID + '\n'
        s = s + 'RS_type = ' + self.type + '\n'
        s = s + 'RS_material = ' + str(self.material) + '\n'
        s = s + 'RS_density = ' + str(self.density) + '\n'
        s = s + 'RS_WET = ' + str(self.WET) + '\n'

        return s
