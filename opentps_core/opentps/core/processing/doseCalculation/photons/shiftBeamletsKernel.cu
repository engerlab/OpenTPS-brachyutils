#include <stdio.h>
#include <stdlib.h>
#include <math.h>

// Device function to retrieve an element from the sparse array given an index
// Performs a binary search on the index array to find the element at the target position
__device__ float getElement(int *index, int size, int target, float *sparse);

// Device function to perform linear interpolation between three points
// Takes x and values (xi0, xi1, xi2) along with corresponding function values (yi0, yi1, yi2)
// Interpolates the value of y at the given x based on the intervals
__device__ float linearInterpolation(float x, float xi0, float xi1, float xi2, float yi0, float yi1, float yi2);

// Device function to return the sign of a given floating point number
// Returns 1 for positive, -1 for negative, and 0 for zero
__device__ int sign(float x);

// Kernel function to shift beamlet indices and perform interpolation on sparse data
// This function shifts the positions of beamlets in the sparse representation and interpolates their values
// Arguments:
// sparse - input sparse array with beamlet values
// sparseShifted - output array to store shifted and interpolated values
// index - array containing original indices of the sparse data
// indexShifted - output array for storing shifted indices
// shift - array containing the shift values in each dimension
// gridSize - size of the computational grid (unused in this code)
// shiftValue - the amount of fractional shift to be applied for interpolation
// indexNumberOfElements - the number of elements in the index array
__global__ void shiftSparse(float *sparse, float *sparseShifted, int *index, int *indexShifted, int *shift, int *gridSize, float shiftValue, int indexNumberOfElements, int sparseSize) {
    // Calculate the global index for this thread
    int start = threadIdx.x + blockIdx.x * blockDim.x;
    
    // Only process elements within the bounds of the index array
    if (start < indexNumberOfElements) {
        // Shift the first coordinate by the first value in the shift array
        int new_index = index[start] + shift[0];
        if (new_index < sparseSize){
            indexShifted[2 * start] = index[start] + shift[0];

            // If a non-zero shift value is provided, perform interpolation
            if (shiftValue != 0.0) {
                // Retrieve neighboring values for interpolation
                int index0 = index[start] + shift[1];
                float value0 = getElement(index, indexNumberOfElements, index0, sparse); // Previous value
                
                float value1 = sparse[start]; // Current value
                    
                int index2 = index[start] + shift[2];
                float value2 = getElement(index, indexNumberOfElements, index2, sparse); // Next value
                
                // Perform linear interpolation for both shifted positions
                sparseShifted[2 * start] = linearInterpolation(shiftValue * -1, -1, 0, 1, value0, value1, value2);
                sparseShifted[2 * start + 1] = linearInterpolation(sign(shiftValue) - shiftValue, -1, 0, 1, value0, value1, value2);
                    
                // Adjust values if neighboring beamlets exist
                if (value2 != 0.0)
                    sparseShifted[2 * start + 1] /= 2;
                if (value0 != 0.0)
                    sparseShifted[2 * start] /= 2;
                
                // Set the shifted index for the second position
                indexShifted[2 * start + 1] = indexShifted[2 * start] + shift[2];
            }
            // If no shift value, copy the original sparse data
            else {
                sparseShifted[2 * start] = sparse[start];
            }          
        }
    }         
}

// Device function to retrieve an element from the sparse array using binary search
// Searches the index array for the target value and returns the corresponding value from the sparse array
// If the target value is not found, returns 0
__device__ float getElement(int index[], int size, int target, float sparse[]) {
    int left = 0;
    int right = size - 1;

    // Perform binary search
    while (left <= right) {
        int mid = left + (int) ((right - left) / 2);
        
        if (index[mid] == target) {
            return sparse[mid]; // Element found, return its value
        } else if (index[mid] < target) {
            left = mid + 1; // Search the right half
        } else {
            right = mid - 1; // Search the left half
        }
    }
    return 0; // Element not found, return 0
}        

// Device function to perform linear interpolation between three points (xi0, xi1, xi2)
// and their corresponding values (yi0, yi1, yi2) to estimate the value of y at a given x
__device__ float linearInterpolation(float x, float xi0, float xi1, float xi2, float yi0, float yi1, float yi2) {
    // Check which interval x belongs to and interpolate accordingly
    if ((xi0 <= x) && (x <= xi1)) {
        return (yi1 - yi0) / (xi1 - xi0) * (x - xi0) + yi0; 
    } else if ((xi1 < x) && (x <= xi2)) {
        return (yi2 - yi1) / (xi2 - xi1) * (x - xi1) + yi1; 
    } else {
        return -1000; // Return a default value if x is outside the interpolation range
    }
}          

// Device function to determine the sign of a floating point number
// Returns 1 if positive, -1 if negative, and 0 if zero
__device__ int sign(float x) {
    if (x > 0) {
        return 1; 
    } else if (x < 0) {
        return -1; 
    } else {
        return 0;
    }
}
