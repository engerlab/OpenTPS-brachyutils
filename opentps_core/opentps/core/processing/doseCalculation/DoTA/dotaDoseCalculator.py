import numpy as np
import h5py
import json
import copy
from tensorflow.keras.utils import Sequence
from tensorflow_addons.optimizers import LAMB
from tensorflow.keras.callbacks import ModelCheckpoint, LearningRateScheduler
import random
import os
import sys

# from opentps.core.processing.imageProcessing import imageTransform3D
from opentps.core.processing.doseCalculation.DoTA.models import dota_energies
from opentps.core.processing.doseCalculation.DoTA.plot import plot_slice, plot_beam
# from opentps.core.data.images._doseImage import DoseImage

currentWorkingDir = os.getcwd()
sys.path.append(currentWorkingDir)
os.environ["CUDA_VISIBLE_DEVICES"] = "2"



class DoTADoseCalculator():
    """
    Generates a dota dose calculator.
    Assumes that the data is stored in a folder (e.g. /data) 
    inside a single .h5 file.

    *list_IDs: a list with the file identifiers.
    *batch_size: size of the mini-batch.
    *ikey, okey: input and output key identifiers.
    *shuffle: flag to shuffle IDs after each epoch.
    *scale: dict with max and min values
    """
    def __init__(self, path = "", scale = {"y_min":0., "y_max":1, "x_min":-1000.0, "x_max":2397.98291015625,
                 "e_min":70, "e_max":220}, batch_size = 8, num_rotations = 4, 
                 ikey='geometry', okey='dose', shuffle=True, train_all = True, train_split = 0.8, val_split = 0.1, num_epochs = 10,
                 learning_rate = 0.001, weight_decay = 0.0001, input_dim = (150,24,24), param_file = None,
                 path_weights = None, path_weights_new = None, inference_per_batch = False, cutoff = 0.5, dose = None):
        self.batch_size = batch_size
        self.path = path 
        self.ikey = ikey
        self.okey = okey
        self.shuffle = shuffle
        self.num_rotations = num_rotations
        self.train_all = train_all
        self.train_split = train_split
        self.val_split = val_split
        self.num_epoch = num_epochs
        self.learning_rate = learning_rate
        self.weight_decay = weight_decay
        self.num_File = len(path)
        self.scale = scale
        self.input_dim = input_dim
        self.paramFile = param_file
        with open(self.paramFile, 'r') as hfile:
            self.param = json.load(hfile)
        self.path_weights = path_weights
        self.path_weights_new = path_weights_new
        self.inference_per_batch = inference_per_batch
        self.cutoff = cutoff
        self.dose = np.zeros((self.input_dim))
        ## Define and train the transformer.
        self.transformer = dota_energies(
            num_tokens=self.param['num_tokens'],
            input_shape=self.param['data_shape'],
            projection_dim=self.param['projection_dim'],
            num_heads=self.param['num_heads'],
            num_transformers=self.param['num_transformers'], 
            kernel_size=self.param['kernel_size'],
            causal=True
        )
        self.transformer.summary()
        # Load weights from checkpoint.
        random.seed()

        # RAJOUTER UNE CONDITION SI PATH WEIGHT NONE ALORS METTRE DES POIDS RANDOM OU ...
        # creer une fonction load_weights

        self.transformer.load_weights(self.path_weights)
        
    def SplitDataSetList(self): 
        list_Energy = []
        list_Rot = []
        list_Files = []
        listIDs = []
        for j in range(self.num_File):
            with h5py.File(self.path[j], 'r') as fh:
                # avoir un nombre d'energie pas constant 
                nb_geometries = fh['geometry'].shape[-1]
                dose_keys = [key for key in fh.keys() if key.startswith("dose")]
                num_energies = len(dose_keys)
                if self.train_all == False :
                    listIDs += range(nb_geometries)
                    list_Files += np.ones(nb_geometries)*j
                else :
                    listIDs += [i for i in range(nb_geometries) for _ in range(self.num_rotations * self.num_energies)]
                    list_Rot += np.concatenate([np.arange(self.num_rotations) for i in range(nb_geometries * self.num_energies)]).tolist()
                    # Create alternating energy values for one geometry
                    geometry_energy = [energy for energy in range(self.num_energies) for _ in range(self.num_rotations)]

                    # Concatenate the energy values for all geometries
                    list_Energy += geometry_energy * nb_geometries
                    list_Files += [j] * (nb_geometries * self.num_rotations * self.num_energies)
        # Training, validation, test split.
        random.seed(333)
        # Create a common index array
        common_index = np.arange(len(listIDs))

        # Shuffle the common index array
        np.random.shuffle(common_index)
        trainEnergies = []
        valEnergies = []
        testEnergies = []
        trainRot = []
        valRot = []
        testRot = []

        # Shuffle the three arrays using the common index array
        listIDs = [listIDs[i] for i in common_index]
        list_Files = [list_Files[i] for i in common_index]
        if self.train_withDataAugmentation == True :
            list_Rot = [list_Rot[i] for i in common_index]
            list_Energy = [list_Energy[i] for i in common_index]

            trainEnergies = list_Energy[:int(round(self.train_split*len(listIDs)))]
            valEnergies = list_Energy[int(round(self.train_split*len(listIDs))):int(round((self.train_split+self.val_split)*len(listIDs)))]
            testEnergies = list_Energy[int(round((self.train_split+self.val_split)*len(listIDs))):]

            trainRot = list_Rot[:int(round(self.train_split*len(listIDs)))]
            valRot = list_Rot[int(round(self.train_split*len(listIDs))):int(round((self.train_split+self.val_split)*len(listIDs)))]
            testRot = list_Rot[int(round((self.train_split+self.val_split)*len(listIDs))):]

        trainFiles = list_Files[:int(round(self.train_split*len(listIDs)))]
        valFiles = list_Files[int(round(self.train_split*len(listIDs))):int(round((self.train_split+self.val_split)*len(listIDs)))]
        testFiles = list_Files[int(round((self.train_split+self.val_split)*len(listIDs))):]

        trainIDs = listIDs[:int(round(self.train_split*len(listIDs)))] #les définir en self. et les mettre en paramètres initialisés à 0
        valIDs = listIDs[int(round(self.train_split*len(listIDs))):int(round((self.train_split+self.val_split)*len(listIDs)))]
        testIDs = listIDs[int(round((self.train_split+self.val_split)*len(listIDs))):]
        #une fonction role : split dataSet et 
        # les deux dernieres lignes a appeler que quand on train
        train_gen = H5DataExtractor(trainIDs, self.batch_size, self.path, self.scale, train_withDataAugmentation = self.train_withDataAugmentation, ID_Energies = trainEnergies,ID_Rotation = trainRot, ID_Files = trainFiles)
        val_gen = H5DataExtractor(valIDs, self.batch_size, self.path, self.scale, train_withDataAugmentation = self.train_withDataAugmentation, ID_Energies = valEnergies, ID_Rotation = valRot, ID_Files = valFiles)

        return train_gen, val_gen, testIDs, testFiles, testEnergies, testRot
    
    def train(self, train_gen, val_gen):
        optimizer = LAMB(learning_rate=self.learning_rate, weight_decay_rate=self.weight_decay)
        self.transformer.compile(optimizer=optimizer, loss='mse', metrics=[])
        # Callbacks.
        # Save best model at the end of the epoch.
        checkpoint = ModelCheckpoint(
            filepath=self.path_weights_new,
            save_weights_only=True,
            save_best_only=True,
            monitor='val_loss',
            mode='min')

        # Learning rate scheduler. Manually reduce the learning rate.
        sel_epochs = [4,8,12,16,20,24,28]
        lr_scheduler = LearningRateScheduler(
            lambda epoch, lr: lr*0.5 if epoch in sel_epochs else lr,
            verbose=1)
        self.optimizer.learning_rate.assign(self.learning_rate)
        history = self.transformer.fit(
            x=train_gen,
            validation_data=val_gen,
            epochs=self.num_epoch,
            verbose=1,
            callbacks=[checkpoint, lr_scheduler]
            )
        self.transformer.save_weights(self.path_weights_new)

        return self.transformer


    def getBoxFromSpotAndAngle(self, spotXY, beamAngle, CTImage):
        box = None
        return box


    # def computePlanDose(self, plan, CTImage):

    #     dose = DoseImage().createEmptyDoseWithSameMetaData(CTImage)
    #     for beam in plan.beams:
    #         BEVImage = copy.copy(CTImage)
    #         imageTransform3D.dicomToIECGantry(BEVImage, beam, fillValue=0.)
    #         for layer in beam.layers:
    #             for spotXY in layer:
    #                 CTBox = self.getBoxFromSpotAndAngle(spotXY, beam.angle, CTImage)
    #                 dose = self.computeDoseBoxFromNumpyArray(CTBox, layer.nominalEnergy)
    #                 print(spotXY)


    def computeDoseBoxFromNumpyArray(self, CT = np.zeros((150,25,25)), energy= 70):
        geometry = np.expand_dims(CT[:, :-1, :-1], axis=(0, -1))
        inputs = (geometry - self.scale['x_min']) / (self.scale['x_max'] - self.scale['x_min'])
        energies = (energy - self.scale['e_min']) / (self.scale['e_max'] - self.scale['e_min'])

        prediction = self.transformer.predict([inputs, np.expand_dims(energies, -1)])
        prediction = prediction * (self.scale['y_max']-self.scale['y_min']) + self.scale['y_min']
        prediction[prediction<(self.cutoff/100)*self.scale['y_max']] = 0
        self.dose = np.squeeze(prediction)
        return self.dose


    def computeDoseBoxFromH5File(self, ID, FileNumber, EnergyID):
        dataPath = self.path[FileNumber]
        with h5py.File(dataPath, 'r') as fh:
                geometry = np.expand_dims(np.transpose(fh[self.ikey][:-1,:-1,:,ID]), axis=(0,-1))
                inputs = (geometry - self.scale['x_min']) / (self.scale['x_max'] - self.scale['x_min'])
                ground_truth = np.transpose(fh[self.okey+str(EnergyID)][:-1,:-1,:,ID])
                energies = (fh['energy'+str(EnergyID)][ID] - self.scale['e_min']) / (self.scale['e_max'] - self.scale['e_min'])

        # Predict dose distribution
        prediction = self.transformer.predict([inputs, np.expand_dims(energies, -1)])
        prediction = prediction * (self.scale['y_max']-self.scale['y_min']) + self.scale['y_min']
        prediction[prediction<(self.cutoff/100)*self.scale['y_max']] = 0
        return np.squeeze(prediction)


    def infer(self, transformer, testIDs=[], testFiles=[], testEnergies=[], testRot=[], fromFile=True, CT = np.zeros((150,25,25)), energy= 70, gt = np.zeros((150,25,25))):
        # fromh5File au lieu de fromFile
        # computeDoseOnTestSet
        # enlever le ground_truth (utilisation et evaluation du modele)
        if fromFile :
            for file_num in set(testFiles):
                # Get indices where list_files_temp == file_num
                indices = [i for i, num in enumerate(testFiles) if num == file_num]
                # Iterate over indices in batches
                if self.inference_per_batch == False :
                    for j in indices:
                        inputs, prediction, ground_truth = infer_(transformer, testIDs[j], self.path[file_num], self.scale,'geometry','dose', 0.5, testEnergies[j], fromFile)
                else :
                    inputs, prediction, ground_truth = infer_(transformer, testIDs[indices], self.path[indices], self.scale, 'geometry','dose', 0.5, testEnergies[indices], self.input_dim, fromFile)
        else : # rajouter pour pouvoir donner des batch et computer par batch meme les matrices et pas les h5 file
                inputs, prediction, ground_truth = infer_(transformer, scale=self.scale, ikey='geometry',okey='dose', cutoff=0.5, input_dim=self.input_dim, fromFile=fromFile, CT=CT, energy=energy, gt=gt)
        return inputs, prediction, ground_truth


class H5DataExtractor(Sequence):
    """
    Generates data for Keras.
    Assumes that the data is stored in a folder (e.g. /data) 
    inside a single .h5 file.

    *list_IDs: a list with the file identifiers.
    *batch_size: size of the mini-batch.
    *ikey, okey: input and output key identifiers.
    *shuffle: flag to shuffle IDs after each epoch.
    *scale: dict with max and min values
    """
    def __init__(self, list_IDs, batch_size, path, scale,
                 ikey='geometry', okey='dose', shuffle=True, train_withDataAugmentation = True, ID_Energies = [], ID_Rotation = [], ID_Files = []):

        self.batch_size = batch_size
        self.list_IDs = list_IDs
        self.path = path 
        self.ikey = ikey
        self.okey = okey
        self.shuffle = shuffle
        self.train_withDataAugmentation = train_withDataAugmentation
        self.ID_Energies = ID_Energies
        self.ID_Rotation = ID_Rotation
        self.ID_Files = ID_Files
        self.on_epoch_end()

        # Get input and output dimensions
        # TODO: won't be needed with beam shape, this step basically
        # reduces the original data dimension (e.g., (25, 25)) to something
        # that is convolutionally friendly (e.g., (24, 24))
        with h5py.File(self.path[0], 'r') as fh:
            input_shape = tuple(reversed(fh[self.ikey].shape[:-1]))
            self.input_dim = tuple(map(lambda i, j: i - j, input_shape, (0,1,1)))
        with h5py.File(self.path[0], 'r') as fh:
            output_shape = tuple(reversed(fh[self.okey+'0'].shape[:-1]))
            self.output_dim = tuple(map(lambda i, j: i - j, output_shape, (0,1,1)))

        # If Height = Width rotate 90 degrees, else 180
        self.rotk = np.arange(4) if self.input_dim[-1]==self.input_dim[-2] else [0,2]

        # Load scaling factors
        self.x_min = scale['x_min']
        self.x_max = scale['x_max']
        self.y_min = scale['y_min']
        self.y_max = scale['y_max']
        self.min_energy = scale['e_min']
        self.max_energy = scale['e_max']
        
    def __len__(self):
        # Calculates the number of batches per epoch.
        return int(np.floor(len(self.list_IDs) / self.batch_size))

    def __getitem__(self, index):
        # Generate one batch of data.
        # Generate indexes of the batch.
        indexes = self.indexes[index*self.batch_size:(index+1)*self.batch_size]
        print(indexes)
        # Find list of IDs.
        list_IDs_temp = [self.list_IDs[k] for k in indexes]
        list_files_temp = [self.ID_Files[k] for k in indexes]
        list_rot_temp = []
        list_energ_temp = []
        if self.train_withDataAugmentation == True:
            list_rot_temp = [self.ID_Rotation[k] for k in indexes]
            list_energ_temp = [self.ID_Energies[k] for k in indexes]

        # Generate data.
        X, y = self.__get_data(list_IDs_temp, list_energ_temp, list_rot_temp, list_files_temp)

        return X, y

    def on_epoch_end(self):
        # Updates indexes after each epoch.
        self.indexes = np.arange(len(self.list_IDs))
        if self.shuffle == True:
            np.random.shuffle(self.indexes)


    def __get_data(self, list_IDs_temp = [], list_energ_temp = [], list_rot_temp = [], list_files_temp = []):
        # Generates data containing batch_size samples.
        X = np.empty((self.batch_size, *self.input_dim))
        y = np.empty((self.batch_size, *self.output_dim))
        energies = np.empty((self.batch_size))
        
        if self.train_withDataAugmentation == False:
            # Iterate over unique file numbers in list_files_temp
            for file_num in set(list_files_temp):
                with h5py.File(self.path[file_num], 'r') as fh:
                    dose_keys = [key for key in fh.keys() if key.startswith("dose")]
                    num_energies = len(dose_keys)
                    for i, ID in enumerate(list_IDs_temp):
                        dose_index = random.choice(list(range(self.num_energies)))
                        tmpGeometry = np.transpose(fh[self.ikey][:,:,:,ID])
                        tmpDose = np.transpose(fh[self.okey+str(dose_index)][:,:,:,ID])
                        energies[i] = fh['energy'+str(dose_index)][ID]

                        # Augment data.
                        # TODO: remove last slicing for shapes (see above)
                        rot = np.random.choice(self.rotk)
                        X[i,] = np.rot90(tmpGeometry, rot, (1,2))[:,:-1,:-1] 
                        y[i,] = np.rot90(tmpDose, rot, (1,2))[:,:-1,:-1]
        else :
            # Iterate over unique file numbers in list_files_temp
            for file_num in set(list_files_temp):
                # Get indices where list_files_temp == file_num
                indices = [i for i, num in enumerate(list_files_temp) if num == file_num]
                # Load data from the current file
                with h5py.File(self.path[file_num], 'r') as fh:
                    # Iterate over indices in batches
                    for j in indices:
                        dose_index = list_energ_temp[j]
                        ID_index = list_IDs_temp[j]
                        tmpGeometry = np.transpose(fh[self.ikey][:,:,:,ID_index])
                        tmpDose = np.transpose(fh[self.okey+str(dose_index)][:,:,:,ID_index])
                        energies[j] = fh['energy'+str(dose_index)][ID_index]
                        rot = list_rot_temp[j]
                        X[j,] = np.rot90(tmpGeometry, rot, (1,2))[:,:-1,:-1] 
                        y[j,] = np.rot90(tmpDose, rot, (1,2))[:,:-1,:-1]
                
        X = (X - self.x_min) / (self.x_max - self.x_min)
        y = (y - self.y_min) / (self.y_max - self.y_min)
        energies = (energies - self.min_energy) / (self.max_energy - self.min_energy)

        return [np.expand_dims(X, -1), np.expand_dims(energies, -1)], np.expand_dims(y, -1)

def infer_(model, IDs=0, filename="", scale="", ikey='geometry', okey='dose', cutoff=0.5, ID_Energies = 0, input_dim = (150,24,24), fromFile = False, CT = np.zeros((150,25,25)), energy= 70, gt = np.zeros((150,25,25))):
    """
    Get model prediction from test sample ID.
    """
    if fromFile :
        if isinstance(IDs, int):
            # Load test sample input and ground truth
            with h5py.File(filename, 'r') as fh:
                geometry = np.expand_dims(np.transpose(fh[ikey][:-1,:-1,:,IDs]), axis=(0,-1))
                inputs = (geometry - scale['x_min']) / (scale['x_max'] - scale['x_min'])
                ground_truth = np.transpose(fh[okey+str(ID_Energies)][:-1,:-1,:,IDs])
                energies = (fh['energy'+str(ID_Energies)][IDs] - scale['e_min']) / (scale['e_max'] - scale['e_min'])

            # Predict dose distribution
            prediction = model.predict([inputs, np.expand_dims(energies, -1)])
            prediction = prediction * (scale['y_max']-scale['y_min']) + scale['y_min']
            prediction[prediction<(cutoff/100)*scale['y_max']] = 0
        else :
            batch_size = len(IDs)
            inputs = np.empty((batch_size, *input_dim, 1))
            ground_truth = np.empty((batch_size, *input_dim, 1))
            energies = np.empty((batch_size))

            # Load test sample input and ground truth
            with h5py.File(filename, 'r') as fh:
                for i, ID in enumerate(IDs):
                    inputs[i,] = np.expand_dims(np.transpose(fh[ikey][:-1,:-1,:,ID]), axis=(0,-1))
                    inputs[i,] = (inputs[i,] - scale['x_min']) / (scale['x_max'] - scale['x_min'])
                    ground_truth[i,] = np.transpose(fh[okey+str(ID_Energies[i])][:-1,:-1,:,ID])
                    energies[i,] = (fh['energy'+str(ID_Energies[i])][ID] - scale['e_min']) / (scale['e_max'] - scale['e_min'])

            # Predict dose distribution
            prediction = model.predict([inputs, np.expand_dims(energies, -1)], batch_size=batch_size)
            prediction = prediction * (scale['y_max']-scale['y_min']) + scale['y_min']
            prediction[prediction<(cutoff/100)*scale['y_max']] = 0
    else :
        geometry = np.expand_dims(CT[:, :-1, :-1], axis=(0, -1))
        inputs = (geometry - scale['x_min']) / (scale['x_max'] - scale['x_min'])
        ground_truth = gt[:, :-1, :-1]

        prediction = model.predict([inputs, np.expand_dims(energy, -1)])
        prediction = prediction * (scale['y_max']-scale['y_min']) + scale['y_min']
        prediction[prediction<(cutoff/100)*scale['y_max']] = 0
    return np.squeeze(geometry), np.squeeze(prediction), np.squeeze(ground_truth)
