from opentps.core.data.plan._robustness import Robustness


class RobustnessProton(Robustness):
    """
    This class creates an object that stores the robustness parameters of an ion plan and robust scenarios (optimization).

    Attributes
    ----------
    rangeSystematicError : float (default = 1.6) (%)
        The range systematic error in %.
    """

    def __init__(self):
        self.rangeSystematicError = 1.6  # %

        super().__init__()