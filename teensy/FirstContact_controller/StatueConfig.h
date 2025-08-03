/*
StatueConfig.h - Configuration for multi-statue bidirectional tone detection
This file defines which statue this code is running on and sets the appropriate
transmit and receive frequencies for detecting connections to multiple statues.
*/

#ifndef STATUE_CONFIG_H
#define STATUE_CONFIG_H

// Total number of statues defined (don't change this)
#define MAX_STATUES 3

// Number of statues active in current test (can be 2 or 3)
#define NUM_STATUES 3 // Change to 2 for two-statue test

// Define which statue this code is running on
// Change this to 'B' or 'C' when compiling for other statues
#define THIS_STATUE_ID 'B'

// Frequency table for all statues (in Hz) - always define all 3
const int STATUE_FREQUENCIES[MAX_STATUES] = {
    10000, // Statue A - EROS
    17000, // Statue B - ELEKTRA
    14000  // Statue C - SOPHIA
};

// Name table for all statues - always define all 3
const char STATUE_NAMES[MAX_STATUES][10] = {"EROS", "ELEKTRA", "SOPHIA"};

// Get this statue's index based on ID
#if THIS_STATUE_ID == 'A'
#define MY_STATUE_INDEX 0
#elif THIS_STATUE_ID == 'B'
#define MY_STATUE_INDEX 1
#elif THIS_STATUE_ID == 'C'
#define MY_STATUE_INDEX 2
#else
#error "Invalid THIS_STATUE_ID. Must be 'A', 'B', or 'C'"
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
