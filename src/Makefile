# Canonical A180206 build. Project owner: Carlo Corti.
CC = gcc-13
CXX = g++-13
WARN = -Wall -Wextra -Wpedantic -Wshadow -Wconversion -Wdouble-promotion -Wformat=2
CFLAGS = -std=c17 -O3 -march=native -mtune=native -flto -funroll-loops -fomit-frame-pointer -fopenmp $(WARN)
CXXFLAGS = -std=c++17 -O3 -march=native -fopenmp $(WARN)
LDLIBS = -lcrypto
.PHONY: all ie test clean
all: a180206
ie: ../check/ie
a180206: a180206.c Makefile
	$(CC) $(CFLAGS) -DA180206_SOURCE_SHA256='"$(word 1,$(shell sha256sum a180206.c))"' -DA180206_MAKE_SHA256='"$(word 1,$(shell sha256sum Makefile))"' a180206.c -o $@ $(LDLIBS)
../check/ie: ../check/ie.cpp Makefile
	$(CXX) $(CXXFLAGS) -DA180206_IE_SHA256='"$(word 1,$(shell sha256sum ../check/ie.cpp))"' -DA180206_MAKE_SHA256='"$(word 1,$(shell sha256sum Makefile))"' $< -o $@ $(LDLIBS)
test: all ie
	python3 -B ../check/test.py
clean:
	rm -f a180206 ../check/ie
