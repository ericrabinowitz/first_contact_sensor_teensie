#include "Haptics.h"
#include <Arduino.h>

void initHaptics() {
  analogWriteFrequency(HAPTIC_MOTOR_PIN, HAPTIC_MOTOR_FREQUENCY);
  analogWriteResolution(HAPTIC_MOTOR_RESOLUTION);
  pinMode(HAPTIC_MOTOR_PIN, OUTPUT);
}

void hapticMotorOn() {
  analogWrite(HAPTIC_MOTOR_PIN, HAPTIC_MOTOR_DUTY_CYCLE_VALUE);
}

void hapticMotorOff() {
  analogWrite(HAPTIC_MOTOR_PIN, 0);
}

void driveHaptics(const ContactState& state) {
  if (state.isUnchanged()) {
    return; // No change in state to report.
  }

  if (state.isLinked) {
    hapticMotorOn();
  } else {
    hapticMotorOff();
  }
}
