# Dynamic Detector Configuration

## Overview
Updated the AudioSense module to support dynamic detector configuration based on NUM_STATUES while maintaining static allocation requirements of the Teensy Audio library.

## Problem
- Previous implementation had hardcoded 2 detector pairs (for 3 statues max)
- With MAX_STATUES=4, we need up to 3 detector pairs
- Teensy Audio library requires static allocation of audio objects

## Solution
Create MAX_STATUES-1 detector pairs statically, but only use NUM_STATUES-1 at runtime.

## Changes Made

### 1. Added Third Detector Pair
```cpp
AudioAnalyzeToneDetect left_det_2;  // Third other statue
AudioAnalyzeToneDetect right_det_2;
```

### 2. Added AudioConnections for Third Pair
```cpp
AudioConnection patchCordL2(audioIn, 0, left_det_2, 0);
AudioConnection patchCordR2(audioIn, 1, right_det_2, 0);
```

### 3. Updated Detector Arrays
Changed from `NUM_STATUES-1` to `MAX_STATUES-1` size:
```cpp
AudioAnalyzeToneDetect *leftDetectors[MAX_STATUES - 1];
AudioAnalyzeToneDetect *rightDetectors[MAX_STATUES - 1];
```

### 4. Conditional Initialization
Initialize detector pointers based on MAX_STATUES value:
```cpp
leftDetectors[0] = &left_det_0;
rightDetectors[0] = &right_det_0;
if (MAX_STATUES > 2) {
  leftDetectors[1] = &left_det_1;
  rightDetectors[1] = &right_det_1;
}
if (MAX_STATUES > 3) {
  leftDetectors[2] = &left_det_2;
  rightDetectors[2] = &right_det_2;
}
```

### 5. Updated Buffer Arrays
Changed buffering arrays to use MAX_STATUES to prevent array out of bounds:
```cpp
static unsigned long bufferStartTime[MAX_STATUES] = {0};
static bool buffering[MAX_STATUES] = {false};
```

## Benefits
- Supports 2, 3, or 4 statue configurations without recompiling
- NUM_STATUES can be changed (within MAX_STATUES limit)
- Respects Teensy Audio library's static allocation requirements
- Minimal memory overhead (6 detector objects vs 4 previously)
- Unused detectors remain unconfigured and don't consume CPU

## Configuration
- Set `MAX_STATUES` to the maximum number of statues (currently 4)
- Set `NUM_STATUES` to the actual number being used (2, 3, or 4)
- Only NUM_STATUES-1 detector pairs will be configured and active