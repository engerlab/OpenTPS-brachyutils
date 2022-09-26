

class BLFree:
    def __init__(self, **kwargs):
        params = kwargs
        self.mcSquareDoseCalculator = params.get("mcsquare_dose_calculator")

    def solve(self):
        dose = self.mcSquareDoseCalculator.optimizeBeamletFree(self.ct, self.plan, self.roi)
        result = {'sol': res.x, 'crit': res.message, 'niter': res.nit, 'time': time.time() - startTime,
                  'objective': res.fun}

