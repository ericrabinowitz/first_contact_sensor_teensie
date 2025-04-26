#pragma once

#include "AudioSense.h"

// Haptic motor configuration
#define HAPTIC_MOTOR_PIN 29
#define HAPTIC_MOTOR_FREQUENCY 400
#define HAPTIC_MOTOR_RESOLUTION 10 // 10-bit resolution i.e. 0-1023
#define HAPTIC_MOTOR_DUTY_CYCLE_VALUE 512

void initHaptics();
void driveHaptics(const ContactState& state);
