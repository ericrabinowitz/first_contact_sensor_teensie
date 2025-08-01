/*
StatueConfig.h - Configuration for two-statue bidirectional tone detection
This file defines which statue this code is running on and sets the appropriate
transmit and receive frequencies for bidirectional contact detection.
*/

#ifndef STATUE_CONFIG_H
#define STATUE_CONFIG_H

// Define which statue this code is running on
// Change this to 'B' when compiling for the second statue
#define THIS_STATUE_ID 'B'

// Frequency assignments
#define FREQ_STATUE_A 10000 // 10kHz
#define FREQ_STATUE_B 8000  // 8kHz

// Get frequencies based on statue ID
#if THIS_STATUE_ID == 'A'
#define MY_TX_FREQ FREQ_STATUE_A
#define OTHER_RX_FREQ FREQ_STATUE_B
#define MY_STATUE_NAME "EROS"
#else
#define MY_TX_FREQ FREQ_STATUE_B
#define OTHER_RX_FREQ FREQ_STATUE_A
#define MY_STATUE_NAME "ELEKTRA"
#endif

#endif // STATUE_CONFIG_H
