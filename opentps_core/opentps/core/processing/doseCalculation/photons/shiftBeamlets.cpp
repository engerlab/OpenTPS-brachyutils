#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <thread>
#include <cmath> 
#include <chrono>

extern "C" {

// Function prototypes
float getElement(const int *index, int target,const float *sparse, int start, int end);
float linearInterpolation(float x, float xi0, float xi1, float xi2, float yi0, float yi1, float yi2);
int sign(float x);
void shiftSparse(const float* sparse, float* imageShifted, const int* index, const int* shift, float shiftValue, int indexNumberOfElements, float weight, int beamletStart, int start, int end);
void parallelShiftSparse(const float* sparse, float* imageShifted, const int* index, const int* shift, float shiftValue, int beamletStart, int indexNumberOfElements, float weight, int numThreads);
void printNonZeroElements(const float* arr, int size);
std::pair<std::vector<int>, std::vector<float>> getNonZeroElements(const float* arr, int size) ;
int getNumberOfNoneZeros(std::array<double, 3>& arr);
float FLOAT_TOLERANCE = 1e-7;

std::array<double, 3> elementWiseRest(const std::array<double, 3>& arr2, const std::array<int, 3>& arr1) {
    std::array<double, 3> result;
    for (std::size_t i = 0; i < arr1.size(); ++i) {
        result[i] = arr2[i] - arr1[i];
    }
    return result;
}

void roundToThirdDigit(std::array<double, 3>& arr) {
    for (double& value : arr) {
        value = std::round(value * 1000.0) / 1000.0;
    }
}

float elementWiseSum(std::array<double, 3>& arr) {
    float sum = 0;
    for (double& value : arr) {
        sum += value;
    }
    return sum;
}

float elementWiseSumAbs(std::array<double, 3>& arr) {
    float sum = 0;
    for (double& value : arr) {
        sum += std::abs(value);
    }
    return sum;
}

std::array<int, 3> elementWiseSign(std::array<double, 3>& arr) {
    std::array<int, 3> result;
    for (std::size_t i = 0; i < arr.size(); ++i) {
        result[i] = sign(float(arr[i]));
    }
    return result;
}

std::array<int, 3> truncateToIntegers(const std::array<double, 3>& arr) {
    std::array<int, 3> truncatedArray;
    for (std::size_t i = 0; i < arr.size(); ++i) {
        truncatedArray[i] = static_cast<int>(arr[i]);
    }
    return truncatedArray;
}

std::array<int, 3> scalarProduct(const std::array<int, 3>& arr, int scalar) {
    std::array<int, 3> result;
    for (std::size_t i = 0; i < arr.size(); ++i) {
        result[i] = arr[i] * scalar;
    }
    return result;
}

std::array<double, 3> correctShift(const float*  setup, double angle) {
    double cosAngle = std::cos(angle);
    double sinAngle = std::sin(angle);
    
    double correctedX = (setup[0] * cosAngle - setup[1] * sinAngle) * cosAngle;
    double correctedY = (setup[0] * cosAngle - setup[1] * sinAngle) * sinAngle;
    double correctedZ = setup[2];

    return {correctedX, correctedY, correctedZ};
}

int convertTo1DcoordFortran(const std::array<int, 3>& arr, const int* size) {
    return arr[0] + arr[1] * size[0] + arr[2] * size[1] * size[0];
}

double custom_mod(double a, double b) {
    double result = std::fmod(a, b);
    if (result < 0) {
        result += b;
    }
    return result;
}

void pushToSparseMatrix(const float* imageShifted, int size, float* nonZeroValuesShifted, int* nonZeroIndexesShifted, int beamletStart, int jump) {
    std::pair<std::vector<int>, std::vector<float>> nonZeroIndexValues = getNonZeroElements(imageShifted, size);
    for (int i = 0; i < nonZeroIndexValues.first.size(); ++i) {
        nonZeroIndexesShifted[beamletStart * 2 * jump + i] = nonZeroIndexValues.first[i];
        nonZeroValuesShifted[beamletStart * 2 * jump + i] = nonZeroIndexValues.second[i];
    }
}

void shiftWithoutInterpolation(const float* nonZeroValues, float* nonZeroValuesShifted, const int* indexes, int* nonZeroIndexesShifted, int beamletStart, int beamletSize, int shift, int jump) {
    for (int i = 0; i < beamletSize; ++i) {
        nonZeroIndexesShifted[beamletStart * 2 * jump + i] = indexes[beamletStart + i] + shift;
        nonZeroValuesShifted[beamletStart * 2 * jump + i] = nonZeroValues[beamletStart + i];
    }
}

/**
 * @brief Shifts beamlets based on setup shifts and beamlet angles.
 *
 * @param nonZeroValues Pointer to the non-zero values of the sparse matrix.
 * @param nonZeroValuesShifted Pointer to store the shifted non-zero values.
 * @param indexes Pointer to the indexes of non-zero elements.
 * @param nonZeroIndexesShifted Pointer to store the shifted indexes.
 * @param beamIndexes Pointer to the beamlet indexes.
 * @param setUpShift Pointer to the setup shift values.
 * @param gridSize Pointer to the grid size dimensions.
 * @param beamletAngles_rad Pointer to the beamlet angles in radians.
 * @param nOfBeamlets Number of beamlets to shift.
 * @param numThreads Number of threads for parallel execution.
 */
void shiftBeamlets(const float* nonZeroValues, float* nonZeroValuesShifted, const int* indexes, int* nonZeroIndexesShifted, int* beamIndexes, const float* setUpShift, const int* gridSize, const float* beamletAngles_rad, int nOfBeamlets, int numThreads) {
    for (int i = 0; i < nOfBeamlets; ++i) {
        int beamletStart = beamIndexes[i];
        int numberOfElementsInBeamlet = beamIndexes[i + 1] - beamletStart;
        std::array<double, 3> correctedShift = correctShift(setUpShift, beamletAngles_rad[i]);
        roundToThirdDigit(correctedShift);
        int shiftTrunctated = convertTo1DcoordFortran(truncateToIntegers(correctedShift), gridSize);
        std::array<double, 3> shiftSmallVoxel = elementWiseRest(correctedShift , truncateToIntegers(correctedShift));
        float shiftSmallVoxelAbsSum = elementWiseSumAbs(shiftSmallVoxel);
        float* imageShifted = new float[gridSize[0]*gridSize[1]*gridSize[2]]();
        if (shiftSmallVoxelAbsSum!=0){
            int j = 0;
            for (double& shift : shiftSmallVoxel){
                if (shift != 0){
                    float weight = std::abs(shift) / shiftSmallVoxelAbsSum;
                    std::array<double, 3> directionalShiftCorrected_voxel = {0.0, 0.0, 0.0};
                    directionalShiftCorrected_voxel[j] = shift;
                    int magnitude = shiftTrunctated;
                    int direction = convertTo1DcoordFortran(elementWiseSign(directionalShiftCorrected_voxel), gridSize);
                    int directionNeg = convertTo1DcoordFortran(scalarProduct(elementWiseSign(directionalShiftCorrected_voxel), -1), gridSize);

                    std::array<int, 3> Shift_voxel = {magnitude, directionNeg, direction};
                    parallelShiftSparse(nonZeroValues, imageShifted, indexes, Shift_voxel.data(), custom_mod(shift, 1), beamletStart, numberOfElementsInBeamlet, weight,  numThreads);
                    j+=1;
                }
                else{
                    j+=1;
                }   
            }
            pushToSparseMatrix(imageShifted, gridSize[0]*gridSize[1]*gridSize[2], nonZeroValuesShifted, nonZeroIndexesShifted, beamletStart, 3);
            delete[] imageShifted;
            imageShifted = nullptr; 
        }
        else{
            shiftWithoutInterpolation(nonZeroValues, nonZeroValuesShifted, indexes, nonZeroIndexesShifted, beamletStart, numberOfElementsInBeamlet, shiftTrunctated, 3);
        }
    }
}

/**
 * @brief Distributes the shifting of the sparse matrix across multiple threads.
 *
 * @param sparse Pointer to the original sparse matrix.
 * @param imageShifted Pointer to the shifted image array.
 * @param index Pointer to the index array.
 * @param shift Pointer to the shift array.
 * @param shiftValue The fractional shift value.
 * @param beamletStart Starting index of the beamlet.
 * @param indexNumberOfElements Number of elements in the beamlet.
 * @param weight Weight factor for the shift.
 * @param numThreads Number of threads for parallel processing.
 */
void parallelShiftSparse(const float* sparse, float* imageShifted, const int* index, const int* shift, float shiftValue, int beamletStart, int indexNumberOfElements, float weight, int numThreads) {

    std::vector<std::thread> threads;
    int chunkSize = indexNumberOfElements / numThreads;
    for (int i = 0; i < numThreads; ++i) {
        int start = i * chunkSize;
        int end = (i == numThreads - 1) ? indexNumberOfElements : start + chunkSize;
        start += beamletStart;
        end += beamletStart;
        
        threads.emplace_back(shiftSparse, sparse, imageShifted, index, shift, shiftValue, indexNumberOfElements, weight, beamletStart, start, end);
    }

    for (auto& t : threads) {
        t.join();
    }
}

/**
 * @brief Shifts a sparse matrix by applying linear interpolation to its values.
 *
 * @param sparse Pointer to the original sparse matrix.
 * @param imageShifted Pointer to the output array where shifted values will be stored.
 * @param index Pointer to the index array.
 * @param shift Pointer to the shift array.
 * @param shiftValue The fractional shift value.
 * @param indexNumberOfElements Number of elements in the beamlet.
 * @param weight Weight factor for the shift.
 * @param beamletStart Starting index of the beamlet.
 * @param start Start index for the chunk of data to process.
 * @param end End index for the chunk of data to process.
 */
void shiftSparse(const float* sparse, float* imageShifted, const int* index, const int* shift, float shiftValue, int indexNumberOfElements, float weight, int beamletStart,  int start, int end) {  
    for (int i = start; i < end; ++i) {
        if (shiftValue != 0.0) {
            int index0 = index[i] + shift[1];
            float value0 = getElement(index, index0, sparse, beamletStart, beamletStart + indexNumberOfElements); 

            float value1 = sparse[i];

            int index2 = index[i] + shift[2];
            float value2 = getElement(index, index2, sparse, beamletStart, beamletStart + indexNumberOfElements); 
            int indexShifted0  = index[i] + shift[0];
            int indexShifted1  = indexShifted0 + shift[2];

            if (value0 != 0.0)
                imageShifted[indexShifted0] += linearInterpolation(shiftValue * -1, -1, 0, 1, value0, value1, value2) / 2 * weight;
            else
                imageShifted[indexShifted0] += linearInterpolation(shiftValue * -1, -1, 0, 1, value0, value1, value2) * weight;

            if (value2 != 0.0)
                imageShifted[indexShifted1] += linearInterpolation(sign(shiftValue) - shiftValue, -1, 0, 1, value0, value1, value2) / 2 * weight;
            else
                imageShifted[indexShifted1] += linearInterpolation(sign(shiftValue) - shiftValue, -1, 0, 1, value0, value1, value2) * weight;

        } else {
            imageShifted[i] += sparse[i];
        }
    }
}

// Implementation of getElement
float getElement(const int *index, int target, const float *sparse, int start, int end) {
    while (start <= end) {
        int mid = start + (end - start) / 2;
        if (index[mid] == target) {
            return sparse[mid];
        } else if (index[mid] < target) {
            start = mid + 1;
        } else {
            end = mid - 1;
        }
    }
    return 0; // Element not found
}

// Implementation of linearInterpolation
float linearInterpolation(float x, float xi0, float xi1, float xi2, float yi0, float yi1, float yi2) {
    if ((xi0 <= x) && (x <= xi1)) {
        return (yi1 - yi0) / (xi1 - xi0) * (x - xi0) + yi0;
    } else if ((xi1 < x) && (x <= xi2)) {
        return (yi2 - yi1) / (xi2 - xi1) * (x - xi1) + yi1;
    } else {
        return -1000;
    }
}

// Implementation of sign
int sign(float x) {
    if (x > 0) {
        return 1;
    } else if (x < 0) {
        return -1;
    } else {
        return 0;
    }
}

void printNonZeroElements(const float* arr, int size) {
    std::cout << "Printing non-zero elements" << std::endl;
    for (int i = 0; i < size; ++i) {
        if (arr[i] > FLOAT_TOLERANCE) {
            std::cout << "Non-zero element at index " << i << ": " << arr[i] << std::endl;
        }
    }
}

int getNumberOfNoneZeros(std::array<double, 3>& arr) {
    int count = 0;
    for (int i = 0; i < arr.size(); ++i) {
        if (arr[i] > FLOAT_TOLERANCE) {
            count++;
        }
    }
    return count;
}

std::pair<std::vector<int>, std::vector<float>> getNonZeroElements(const float* arr, int size) {
    std::vector<int> indices;
    std::vector<float> values;

    for (int i = 0; i < size; ++i) {
        if (arr[i] > FLOAT_TOLERANCE) {
            indices.push_back(i);
            values.push_back(arr[i]);
        }
    }

    return {indices, values};
}
} // extern "C"
