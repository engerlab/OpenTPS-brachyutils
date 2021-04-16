import warnings
warnings.filterwarnings('ignore',category=FutureWarning)

try:
  from keras.layers import Input, Conv3D, Conv2D, Conv3DTranspose, Add
  from keras.layers import MaxPooling3D, Cropping3D, Concatenate
  from keras.layers import Lambda, Activation, BatchNormalization, Dropout
  from keras.models import Model
  from keras import backend as K
  use_keras = 1
except:
  use_keras = 0


import numpy as np


def conv_layer(input_tensor, filters, padding='valid',
                       batchnorm=False, dropout=0.0):

  if use_keras == 0: return

  _, _, height, width, _ = K.int_shape(input_tensor)
  assert height % 2 == 0
  assert width % 2 == 0

  x = Conv3D(filters, kernel_size=(3,3,3), padding=padding,
               dilation_rate=1, kernel_initializer='he_normal')(input_tensor)
  x = BatchNormalization()(x) if batchnorm else x
  x = Activation('relu')(x)
  x = Dropout(dropout)(x) if dropout > 0 else x

  x = Conv3D(filters, kernel_size=(3,3,3), padding=padding, dilation_rate=2, kernel_initializer='he_normal')(x)
  x = BatchNormalization()(x) if batchnorm else x
  x = Activation('relu')(x)
  x = Dropout(dropout)(x) if dropout > 0 else x

  return x


# ========================================================================================================== #

def simpleNet(height, width, channels, classes, features=64, depth=4,
              padding='valid', batchnorm=False, dropout=0.0):
    """
    -------
      height  - input image height (pixels)
      width   - input image width  (pixels)
      channels - input image features (1 for grayscale, 3 for RGB)
      classes - number of output classes
      features - number of output features for first convolution

      depth  - number of convolutional layers
      padding - 'valid' or 'same'
      batchnorm - include batch normalization layers before activations
      dropout - fraction of units to dropout, 0 to keep all units

    Output:
      Model expecting input shape (height, width, maps) and
      generates output with shape (output_height, output_width, classes).
      If padding is 'same', then output_height = height and
      output_width = width.

    """
    
    if use_keras == 0: return

    x = Input(shape=(classes, height, width, channels))
    inputs = x

    for i in range(depth):
        x = conv_layer(x, features, padding, batchnorm, dropout)
        # print(x.shape, x0.shape)
        #features *= 2

    _, depth, height, width, _ = K.int_shape(x)
    x = Conv3D(filters=1, kernel_size=(1, 1, 1), kernel_initializer='he_normal')(x)

    x = Activation('relu')(x)

    return Model(inputs=inputs, outputs=x)
