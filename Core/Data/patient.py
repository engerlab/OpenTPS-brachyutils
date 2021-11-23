
class Patient:
    def __init__(self):
        self.age = 0
        self.patientID = None
        self.sex = None
        self.images = []

    def appendImage(self, image):
        self.images.append(image)

    def removeImage(self, image):
        self.images.remove(image)

