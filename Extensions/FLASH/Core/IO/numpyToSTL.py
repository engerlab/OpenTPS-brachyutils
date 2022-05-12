
# Adapted from https://raw.githubusercontent.com/anoved/phstl/


import sys
from struct import pack
from typing import Sequence

import numpy as np


def numpyToSTL(mat:np.ndarray, spacing:Sequence[float], fileName:str):
    zscale = 1.
    t = (-0.5, # 0 left edge of top left pixel
			 spacing[1],            # 1 pixel width
			 0,                      # 2
			 0.5, # 3 top edge of top left pixel
			 0,                      # 4
			-spacing[0])             # 5 pixel height)

    mat2 = np.zeros((mat.shape[0] + 1, mat.shape[1] + 1))
    mat2[:-1, :-1] = mat
    mat = mat2

    with stlwriter(fileName, facet_count=mat.shape[0]*mat.shape[1]*5) as mesh:
        y = mat.shape[0]-1
        x = mat.shape[0]-1

        b = (
            t[0] + (0 * t[1]) + (y * t[2]),
            t[3] + (0 * t[4]) + (y * t[5]),
            0
        )

        c = (
            t[0] + (x * t[1]) + (0 * t[2]),
            t[3] + (x * t[4]) + (0 * t[5]),
            0
        )

        a = (
            t[0] + (0 * t[1]) + (0 * t[2]),
            t[3] + (0 * t[4]) + (0 * t[5]),
            0
        )
        mesh.add_facet((a, b, c))

        d = (
            t[0] + (x * t[1]) + (y * t[2]),
            t[3] + (x * t[4]) + (y * t[5]),
            0
        )
        mesh.add_facet((d, c, b))


        for y in range(mat.shape[0]-1):
            for x in range(mat.shape[1]-1):

                # Elevation values of this pixel (a) and its neighbors (b, c, and d).
                av = mat[y, x]
                bv = mat[y, x]
                cv = mat[y, x]
                dv = mat[y, x]

                # Apply transforms to obtain output mesh coordinates of the
                # four corners composed of raster points a (x, y), b, c,
                # and d (x + 1, y + 1):
                #
                # a-c   a-c     c
                # |/| = |/  +  /|
                # b-d   b     b-d


                b = (
                    t[0] + (x* t[1]) + ((y + 1) * t[2]),
                    t[3] + (x* t[4]) + ((y + 1) * t[5]),
                    (zscale * (float(bv)))
                )

                c = (
                    t[0] + ((x + 1) * t[1]) + (y* t[2]),
                    t[3] + ((x + 1) * t[4]) + (y* t[5]),
                    (zscale * (float(cv)))
                )

                a = (
                    t[0] + (x* t[1]) + (y* t[2]),
                    t[3] + (x* t[4]) + (y* t[5]),
                    (zscale * (float(av)))
                )
                mesh.add_facet((a, b, c))

                d = (
                    t[0] + ((x + 1) * t[1]) + ((y + 1) * t[2]),
                    t[3] + ((x + 1) * t[4]) + ((y + 1) * t[5]),
                    (zscale * (float(dv)))
                )
                mesh.add_facet((d, c, b))



                if (mat[y,x] != mat[y, x+1]):
                    b = (
                        t[0] + ((x+1) * t[1]) + ((y + 1) * t[2]),
                        t[3] + ((x+1) * t[4]) + ((y + 1) * t[5]),
                        (zscale * (float(bv)))
                    )

                    c = (
                        t[0] + ((x+1) * t[1]) + (y * t[2]),
                        t[3] + ((x+1) * t[4]) + (y * t[5]),
                        mat[y, x+1]
                    )

                    a = (
                        t[0] + ((x+1) * t[1]) + (y * t[2]),
                        t[3] + ((x+1) * t[4]) + (y * t[5]),
                        (zscale * (float(av)))
                    )
                    mesh.add_facet((a, b, c))

                    d = (
                        t[0] + ((x+1) * t[1]) + ((y + 1) * t[2]),
                        t[3] + ((x+1) * t[4]) + ((y + 1) * t[5]),
                        mat[y, x+1]
                    )
                    mesh.add_facet((d, c, b))

                if (x==0 and (mat[y,x]!=0)):
                    b = (
                        t[0] + (x * t[1]) + ((y + 1) * t[2]),
                        t[3] + (x * t[4]) + ((y + 1) * t[5]),
                        (zscale * (float(bv)))
                    )

                    c = (
                        t[0] + (x * t[1]) + (y * t[2]),
                        t[3] + (x * t[4]) + (y * t[5]),
                        0
                    )

                    a = (
                        t[0] + (x * t[1]) + (y * t[2]),
                        t[3] + (x * t[4]) + (y * t[5]),
                        (zscale * (float(av)))
                    )
                    mesh.add_facet((a, b, c))

                    d = (
                        t[0] + (x * t[1]) + ((y + 1) * t[2]),
                        t[3] + (x * t[4]) + ((y + 1) * t[5]),
                        0
                    )
                    mesh.add_facet((d, c, b))

                if (mat[y,x] != mat[y+1, x]):
                    b = (
                        t[0] + (x * t[1]) + ((y + 1) * t[2]),
                        t[3] + (x * t[4]) + ((y + 1) * t[5]),
                        (zscale * (float(bv)))
                    )

                    c = (
                        t[0] + ((x + 1) * t[1]) + ((y + 1) * t[2]),
                        t[3] + ((x + 1) * t[4]) + ((y + 1) * t[5]),
                        mat[y+1, x]
                    )

                    a = (
                        t[0] + (x * t[1]) + ((y + 1) * t[2]),
                        t[3] + (x * t[4]) + ((y + 1) * t[5]),
                        mat[y+1, x]
                    )
                    mesh.add_facet((a, b, c))

                    d = (
                        t[0] + ((x + 1) * t[1]) + ((y + 1) * t[2]),
                        t[3] + ((x + 1) * t[4]) + ((y + 1) * t[5]),
                        (zscale * (float(dv)))
                    )
                    mesh.add_facet((d, c, b))

                if (y==0 and mat[y,x] != 0):
                    b = (
                        t[0] + (x * t[1]) + (y * t[2]),
                        t[3] + (x * t[4]) + (y * t[5]),
                        (zscale * (float(bv)))
                    )

                    c = (
                        t[0] + ((x + 1) * t[1]) + (y * t[2]),
                        t[3] + ((x + 1) * t[4]) + (y * t[5]),
                        0
                    )

                    a = (
                        t[0] + (x * t[1]) + (y * t[2]),
                        t[3] + (x * t[4]) + (y * t[5]),
                        0
                    )
                    mesh.add_facet((a, b, c))

                    d = (
                        t[0] + ((x + 1) * t[1]) + (y * t[2]),
                        t[3] + ((x + 1) * t[4]) + (y * t[5]),
                        (zscale * (float(dv)))
                    )
                    mesh.add_facet((d, c, b))



#
# NormalVector
#
# Calculate the normal vector of a triangle. (Unit vector perpendicular to
# triangle surface, pointing away from the "outer" face of the surface.)
# Computed using 32-bit float operations for consistency with other tools.
#
# Parameters:
#  triangle vertices (nested x y z tuples)
#
# Returns:
#  normal vector (x y z tuple)
#
def NormalVector(t):
    (ax, ay, az) = t[0]
    (bx, by, bz) = t[1]
    (cx, cy, cz) = t[2]

    # first edge
    e1x = np.float32(ax) - np.float32(bx)
    e1y = np.float32(ay) - np.float32(by)
    e1z = np.float32(az) - np.float32(bz)

    # second edge
    e2x = np.float32(bx) - np.float32(cx)
    e2y = np.float32(by) - np.float32(cy)
    e2z = np.float32(bz) - np.float32(cz)

    # cross product
    cpx = np.float32(e1y * e2z) - np.float32(e1z * e2y)
    cpy = np.float32(e1z * e2x) - np.float32(e1x * e2z)
    cpz = np.float32(e1x * e2y) - np.float32(e1y * e2x)

    # return cross product vector normalized to unit length
    mag = np.sqrt(np.power(cpx, 2) + np.power(cpy, 2) + np.power(cpz, 2))
    return (cpx /mag, cpy /mag, cpz /mag)

# stlwriter is a simple class for writing binary STL meshes.
# Class instances are constructed with a predicted face count.
# The output file header is overwritten upon completion with
# the actual face count.
class stlwriter():

    # path: output binary stl file path
    # facet_count: predicted number of facets
    def __init__(self, path, facet_count=0):

        self.f = open(path, 'wb')

        # track number of facets actually written
        self.written = 0

        # write binary stl header with predicted facet count
        self.f.write(str.encode('\0' * 80))
        # (facet count is little endian 4 byte unsigned int)
        self.f.write(pack('<I', facet_count))

    # t: ((ax, ay, az), (bx, by, bz), (cx, cy, cz))
    def add_facet(self, t):
        # facet normals and vectors are little endian 4 byte float triplets
        # strictly speaking, we don't need to compute NormalVector,
        # as other tools could be used to update the output mesh.
        self.f.write(pack('<3f', *NormalVector(t)))
        for vertex in t:
            self.f.write(pack('<3f', *vertex))
        # facet records conclude with two null bytes (unused "attributes")
        self.f.write(str.encode('\0\0'))
        self.written += 1

    def done(self):
        # update final facet count in header before closing file
        self.f.seek(80)
        self.f.write(pack('<I', self.written))
        self.f.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.done()

def fail(msg):
    print >> sys.stderr, msg
    exit(1)


if __name__ == "__main__":
    a = np.array([[1, 1], [3, 4]])
    numpyToSTL(a, [2, 1], 'test.stl')
