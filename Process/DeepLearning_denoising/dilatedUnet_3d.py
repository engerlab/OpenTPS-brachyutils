import warnings
warnings.filterwarnings('ignore',category=FutureWarning)

from keras.layers import Input, Conv3D, Conv2D, Conv3DTranspose, Add
from keras.layers import MaxPooling3D, Cropping3D, Concatenate
from keras.layers import Lambda, Activation, BatchNormalization, Dropout
from keras.models import Model
from keras import backend as K
import numpy as np


def downsampling_block(input_tensor, filters, padding='valid',
                       batchnorm=False, dropout=0.0, strides=(1,2,2)):
                       
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

    return MaxPooling3D(pool_size=(2,2,2), strides=strides)(x), x

# ===== For 3D Maxpooling, change to pool_size = (2,2,2), strides=(2,2,2) for downsampling and conv3DTranspose  (Lines 29 and 38) ====== #

# ========================================================================================================== #

def upsampling_block(input_tensor, skip_tensor, filters, padding='valid',
                     batchnorm=False, dropout=0.0, strides=(1,2,2)):
    
    x = Conv3DTranspose(filters, kernel_size=(2,2,2), strides=strides, kernel_initializer='he_normal')(input_tensor)
    
    # compute amount of cropping needed for skip_tensor
    _, _, x_height, x_width, _ = K.int_shape(x)
    _, _, s_height, s_width, _ = K.int_shape(skip_tensor)
    h_crop = s_height - x_height
    w_crop = s_width - x_width

    assert h_crop >= 0
    assert w_crop >= 0
    if h_crop == 0 and w_crop == 0:
        y = skip_tensor
    else:
        cropping = ((h_crop//2, h_crop - h_crop//2), (w_crop//2, w_crop - w_crop//2))
        
        y = Cropping3D(cropping=cropping)(skip_tensor)

    x = Concatenate()([x, y])

    #inputs = [x, y]

    # no dilation in upsampling convolutions
    x = Conv3D(filters, kernel_size=(3,3,3), padding=padding, kernel_initializer='he_normal')(x)
    x = BatchNormalization()(x) if batchnorm else x
    x = Activation('relu')(x)
    x = Dropout(dropout)(x) if dropout > 0 else x
    
    x = Conv3D(filters, kernel_size=(3,3,3), padding=padding, kernel_initializer='he_normal')(x)
    x = BatchNormalization()(x) if batchnorm else x
    x = Activation('relu')(x)
    x = Dropout(dropout)(x) if dropout > 0 else x

    return x

# ========================================================================================================== #

def dilated_unet(height, width, channels, classes, features=64, depth=4,
                 temperature=1.0, padding='valid', batchnorm=False,
                 dropout=0.0, dilation_layers=5, residual=True, strides=(1,2,2)):
    """
    -------
      height  - input image height (pixels)
      width   - input image width  (pixels)
      channels - input image features (1 for grayscale, 3 for RGB)
      classes - number of output classes
      features - number of output features for first convolution
      
      depth  - number of downsampling operations 
      padding - 'valid' or 'same'
      batchnorm - include batch normalization layers before activations
      dropout - fraction of units to dropout, 0 to keep all units
      dilation_layers - number of dilated convolutions in innermost bottleneck

    Output:
      Dilated U-Net model expecting input shape (height, width, maps) and
      generates output with shape (output_height, output_width, classes).
      If padding is 'same', then output_height = height and
      output_width = width.

    """
    x = Input(shape=(classes, height, width, channels))
    #print(x.shape)
    inputs = x

    skips = []
    dilated_add = []
    for i in range(depth):
        x, x0 = downsampling_block(x, features, padding, batchnorm, dropout, strides=strides)
        #print(x.shape, x0.shape)
        skips.append(x0)
        features *= 2
       
    dilation_rate = 1
    for n in range(dilation_layers):
        x = Conv3D(filters=features, kernel_size=(3,3,3), padding=padding,
                   dilation_rate=dilation_rate, kernel_initializer='he_normal')(x)
        x = BatchNormalization()(x) if batchnorm else x
        x = Activation('relu')(x)
        x = Dropout(dropout)(x) if dropout > 0 else x
        dilation_rate *= 2

    for i in reversed(range(depth)):
        features //= 2
        
        x = upsampling_block(x, skips[i], features, padding,
                             batchnorm, dropout, strides=strides)

    _, depth, height, width, _ = K.int_shape(x)

    x = Conv3D(filters=1, kernel_size=(1,1,1), kernel_initializer='he_normal')(x)

    if residual:
        x = Activation(None)(x)
        x = Add()([x, inputs])
    else:
        x = Activation('relu')(x)
    
    return Model(inputs=inputs, outputs=x)
