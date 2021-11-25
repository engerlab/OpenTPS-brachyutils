
default: all

all: libRayTracing.so libInterp3.so

libRayTracing.so: libRayTracing.c
	gcc -shared -O2 -fopenmp -std=c99 -o libRayTracing.so -fPIC libRayTracing.c

libInterp3.so: libInterp3.c
	gcc -shared -O2 -fopenmp -std=c99 -o libInterp3.so -fPIC libInterp3.c