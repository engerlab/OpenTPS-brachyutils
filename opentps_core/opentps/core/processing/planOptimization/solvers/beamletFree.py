

class BLFree:
    """
    Beamlet free solver class. The beamlet free opitmization is done by the mcSquareDoseCalculator and thereby done directly in the mcSquare C code.
    This module is juste the interface between python and the C code.

    !! THIS CLASS IS NOT FULLY IMPLEMENTED YET !!
    To use the beamlet free solver, you need to call it via the mcSquareDoseCalculator.optimizeBeamletFree() method.
    """
    def __init__(self, **kwargs):
        params = kwargs
        self.mcSquareDoseCalculator = params.get("mcsquare_dose_calculator")

    def solve(self):
        # TODO : implement the solver
        """
        Solve the beamlet free optimization problem.
        """
        dose = self.mcSquareDoseCalculator.optimizeBeamletFree(self.ct, self.plan, self.roi)
        result = {'sol': res.x, 'crit': res.message, 'niter': res.nit, 'time': time.time() - startTime,
                  'objective': res.fun}

