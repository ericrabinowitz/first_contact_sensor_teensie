/*
StatueConfig.h - Configuration for multi-statue bidirectional tone detection
This file defines which statue this code is running on and sets the appropriate
transmit and receive frequencies for detecting connections to multiple statues.

3. Optimized Non-Harmonic Set
Based on avoiding common intermodulation products:

1. Align with FFT Bin Centers
Your frequencies should fall exactly on FFT bin centers to maximize detection accuracy:
// Example with 44.1kHz sample rate, 1024-point FFT
float binWidth = 44100.0 / 1024.0; // = 43.07 Hz per bin

⚠️ Problem Found: 3rd Order Intermodulation
2×11,972 - 10,293 = 13,651 Hz
This is only 44 Hz (1 bin) away from 13,695 Hz!

// Choose frequencies that are integer multiples of binWidth
10,077 Hz (bin 234)
12,274 Hz (bin 285)
14,643 Hz (bin 340)
17,227 Hz (bin 400)
19,467 Hz (bin 452)
*/

#ifndef STATUE_CONFIG_H
#define STATUE_CONFIG_H

// Total number of statues defined (don't change this)
#define MAX_STATUES 5

// Number of statues active in current test (can be 2-5)
#define NUM_STATUES 5

// Define which statue this code is running on
// Change this to 'B' or 'C' when compiling for other statues
#define THIS_STATUE_ID 'A'

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

// Runtime configuration variables (can be updated via MQTT)
extern int statueFrequencies[MAX_STATUES];
extern char statueNames[MAX_STATUES][10];
extern int myStatueIndex;
extern int numStatues;
extern bool configReceived;

// Function to initialize runtime config from defaults
void initDefaultConfig();

#endif // STATUE_CONFIG_H
