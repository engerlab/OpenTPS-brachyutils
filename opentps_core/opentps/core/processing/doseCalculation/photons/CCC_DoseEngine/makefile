CC = g++
CFLAGS = -O2
OBJECTS = convolution.o calc_deff.o parse_func.o make_poly.o raytrace.o terma_dose_masks.o terma_kerma.o calc_dose.o util.o

Cconvolution : $(OBJECTS)
	 $(CC) $(CFLAGS) $(OBJECTS) -o CCC_DoseEngine

%.o : %.cpp
	$(CC) $(CFLAGS) -c $<

clean : 
	rm -f $(OBJECTS) CCC_DoseEngine
