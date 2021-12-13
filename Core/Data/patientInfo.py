class PatientInfo:
    """
    The class PatientInfo contains the patient information

    Parameters
    ----------
    patientID: str
        Unique ID of the patient

    name: str
        Name of the patient

    birthDate: str
        Birth date of the patient

    sex: str
        Gender of the patient

    """

    def __init__(self, patientID="", name="", birthDate="", sex="O"):
        self.patientID = patientID
        self.name = name
        self.birthDate = birthDate
        self.sex = sex


    def __str__(self):
        """
        Overload __str__ function that is called when one print the object.
        """

        return "Patient ID: " + self.patientID + "\n" + \
                "Patient name: " + self.name + "\n" + \
                "Patient birth date: " + self.birthDate + "\n" + \
                "Patient sex: " + self.sex