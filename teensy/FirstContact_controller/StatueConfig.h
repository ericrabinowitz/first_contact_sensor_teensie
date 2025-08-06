/*
StatueConfig.h - Configuration for multi-statue bidirectional tone detection
This file defines which statue this code is running on and sets the appropriate
transmit and receive frequencies for detecting connections to multiple statues.

3. Optimized Non-Harmonic Set
Based on avoiding common intermodulation products:

10.3 kHz
13.7 kHz
16.1 kHz
18.9 kHz

1. Align with FFT Bin Centers
Your frequencies should fall exactly on FFT bin centers to maximize detection accuracy:
// Example with 44.1kHz sample rate, 1024-point FFT
float binWidth = 44100.0 / 1024.0; // = 43.07 Hz per bin

// Choose frequencies that are integer multiples of binWidth
float freq1 = binWidth * 239; // = 10,293 Hz (bin 239)
float freq2 = binWidth * 318; // = 13,695 Hz (bin 318)
float freq3 = binWidth * 374; // = 16,097 Hz (bin 374)
float freq4 = binWidth * 439; // = 18,906 Hz (bin 439)

// Recommended: At least 3-5 bins separation
// This prevents spectral leakage overlap
Bin 239: 10,293 Hz
Bin 318: 13,695 Hz (79 bins apart ✓)
Bin 374: 16,097 Hz (56 bins apart ✓)
Bin 439: 18,906 Hz (65 bins apart ✓)
*/

#ifndef STATUE_CONFIG_H
#define STATUE_CONFIG_H

// Total number of statues defined (don't change this)
#define MAX_STATUES 5

// Number of statues active in current test (can be 2-5)
#define NUM_STATUES 5

// Define which statue this code is running on
// Change this to 'B' or 'C' when compiling for other statues
#define THIS_STATUE_ID 'E'

// Frequency table for all statues (in Hz) - always define all 5
const int STATUE_FREQUENCIES[MAX_STATUES] = {
    10077, // Statue A - EROS (bin 234)
    12274, // Statue B - ELEKTRA (bin 285)
    14643, // Statue C - ARIEL (bin 340)
    17227, // Statue D - SOPHIA (bin 400)
    19467, // Statue E - ULTIMO (bin 452)
};

// Name table for all statues - always define all 3
const char STATUE_NAMES[MAX_STATUES][10] = {"EROS", "ELEKTRA", "ARIEL",
                                            "SOPHIA", "ULTIMO"};

// Get this statue's index based on ID
#if THIS_STATUE_ID == 'A'
#define MY_STATUE_INDEX 0
#elif THIS_STATUE_ID == 'B'
#define MY_STATUE_INDEX 1
#elif THIS_STATUE_ID == 'C'
#define MY_STATUE_INDEX 2
#elif THIS_STATUE_ID == 'D'
#define MY_STATUE_INDEX 3
#elif THIS_STATUE_ID == 'E'
#define MY_STATUE_INDEX 4
#else
#error "Invalid THIS_STATUE_ID. Must be 'A', 'B', 'C', 'D', or 'E'"
#endif

// Validate configuration
#if NUM_STATUES < 2 || NUM_STATUES > MAX_STATUES
#error "NUM_STATUES must be between 2 and MAX_STATUES"
#endif

#if MY_STATUE_INDEX >= NUM_STATUES
#error "THIS_STATUE_ID is beyond NUM_STATUES range. Check your configuration."
#endif

// Get this statue's transmit frequency and name
#define MY_TX_FREQ STATUE_FREQUENCIES[MY_STATUE_INDEX]
#define MY_STATUE_NAME STATUE_NAMES[MY_STATUE_INDEX]

#endif // STATUE_CONFIG_H
