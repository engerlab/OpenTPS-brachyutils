class RangeShifter:
    def __init__(self):
        self.ID = ''
        self.type = ''
        self.material = -1
        self.density = 0.0
        self.WET = 0.0

    def __str__(self):
        s = ''
        s = s + 'RS_ID = ' + self.ID
        s = s + 'RS_type = ' + self.type
        s = s + 'RS_material = ' + str(self.material)
        s = s + 'RS_density = ' + str(self.density)
        s = s + 'RS_WET = ' + str(self.WET)

        return s
