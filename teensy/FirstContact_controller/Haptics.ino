#include "Haptics.h"
#include <Arduino.h>

// Haptic motor on-duration constant (ms)
const unsigned long HAPTIC_MOTOR_ON_DURATION_MS = 500;

// Timer variables for haptic motor auto-off
static unsigned long hapticTimerStart = 0;
static bool hapticTimerActive = false;

void initHaptics() {
  analogWriteFrequency(HAPTIC_MOTOR_PIN, HAPTIC_MOTOR_FREQUENCY);
  analogWriteResolution(HAPTIC_MOTOR_RESOLUTION);
  pinMode(HAPTIC_MOTOR_PIN, OUTPUT);
}

void hapticMotorOn() {
  analogWrite(HAPTIC_MOTOR_PIN, HAPTIC_MOTOR_DUTY_CYCLE_VALUE);
  hapticTimerStart = millis();
  hapticTimerActive = true;
}

void hapticMotorOff() {
  analogWrite(HAPTIC_MOTOR_PIN, 0);
  hapticTimerActive = false;
}

// Check if the timer has expired and turn off motor if needed.
void handleHapticTimer() {
  if (hapticTimerActive && (millis() - hapticTimerStart >= HAPTIC_MOTOR_ON_DURATION_MS)) {
    hapticMotorOff();
  }
}

void driveHaptics(const ContactState& state) {
  handleHapticTimer();
  if (state.isUnchanged()) {
    return; // No change in state to report.
  }

  if (state.isLinked) {
    hapticMotorOn();
  } else {
    hapticMotorOff();
  }
}
