
import vtkmodules.vtkCommonCore as vtkCommonCore


class LookupTables:
    def __getitem__(self, item):
        if item=='fusion':
            return LookupTables.getFusion

        if item=='gray':
            return LookupTables.getGray

    @staticmethod
    def getFusion(range, opacity):
        table = vtkCommonCore.vtkLookupTable()
        table.SetRange(range[0], range[1])  # image intensity range
        table.SetValueRange(0.0, 1.0)  # from black to white
        table.SetSaturationRange(0.0, 0.0)  # no color saturation
        table.SetRampToLinear()

        table.SetNumberOfTableValues(11)
        table.SetTableValue(0, (0, 0, 0.6667, 0))
        table.SetTableValue(1, (0, 0, 1.0000, opacity))
        table.SetTableValue(2, (0, 0.3333, 1.0000, opacity))
        table.SetTableValue(3, (0, 0.6667, 1.0000, opacity))
        table.SetTableValue(4, (0, 1.0000, 1.0000, opacity))
        table.SetTableValue(5, (0.3333, 1.0000, 0.6667, opacity))
        table.SetTableValue(6, (0.6667, 1.0000, 0.3333, opacity))
        table.SetTableValue(7, (1.0000, 1.0000, 0, opacity))
        table.SetTableValue(8, (1.0000, 0.6667, 0, opacity))
        table.SetTableValue(9, (1.0000, 0.3333, 0, opacity))
        table.SetTableValue(10, (1.0000, 0, 0, opacity))

        table.SetBelowRangeColor(0, 0, 0, 0)
        table.SetUseBelowRangeColor(True)
        table.SetAboveRangeColor(1.0000, 0, 0, opacity)
        table.SetUseAboveRangeColor(True)
        table.Build()

        return table

    @staticmethod
    def getGray(range):
        table = vtkCommonCore.vtkLookupTable()
        table.SetRange(range[0], range[1])  # image intensity range
        table.SetValueRange(0.0, 1.0)  # from black to white
        table.SetSaturationRange(0.0, 0.0)  # no color saturation
        table.SetRampToLinear()
        table.Build()

        return table