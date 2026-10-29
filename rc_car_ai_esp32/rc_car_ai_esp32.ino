#include <Bluepad32.h>
#include <math.h>
#include "best_genome_weights.h"

/*
  ESP32-WROOM + 2 x TB6612FNG + 4WD differential-drive RC car
  Manual mode keeps the known v4 behavior. AI mode runs the exported Python NN.

  IMPORTANT:
  - AI mode is disabled until the five physical sensors are installed and checked.
  - Initial AI throttle and steering are limited for first tests.
  - First test: wheels lifted off the ground; then try a low-speed, enclosed track.
  - GP2Y0A21YK0F sensors are powered from a regulated 5V supply, not ESP32 3V3.
  - Use a divider on every analog sensor output (10k from sensor output to ADC node,
    20k from ADC node to GND); code multiplies ADC voltage by 1.5 to recover VO.
  - ESP32, sensor supply, driver boards, and motor battery grounds must be common.
  - TB6612FNG STBY pins are controlled by GPIO26/27. Do not also hard-wire STBY to 3V3.
*/

// ---------- Motor pins (kept from working manual v4) ----------
constexpr int MOTOR_TOP_PWMA = 18;
constexpr int MOTOR_TOP_AI1  = 15;
constexpr int MOTOR_TOP_AI2  = 4;
constexpr int MOTOR_TOP_PWMB = 19;
constexpr int MOTOR_TOP_BI1  = 16;
constexpr int MOTOR_TOP_BI2  = 17;
constexpr int MOTOR_TOP_STBY = 26;

constexpr int MOTOR_BOT_PWMA = 2;
constexpr int MOTOR_BOT_AIN1 = 21;
constexpr int MOTOR_BOT_AIN2 = 22;
constexpr int MOTOR_BOT_PWMB = 25;
constexpr int MOTOR_BOT_BIN1 = 23;
constexpr int MOTOR_BOT_BIN2 = 5;
constexpr int MOTOR_BOT_STBY = 27;

// ---------- Five analog IR distance sensors ----------
// Order must match the simulator: -60, -30, 0, +30, +60 degrees.
// In a top view, install them from the vehicle's left side to right side.
constexpr int SENSOR_PINS[AI_INPUTS] = {32, 33, 34, 35, 36};

// Leave false until five GP2Y0A21YK0F sensors are wired and their readings verified.
// Change to true and re-upload only after the physical sensors and voltage dividers are installed.
constexpr bool SENSOR_HARDWARE_READY = false;
// Enable only after wiring sensors if you want their values printed in Serial Monitor.
constexpr bool ENABLE_SENSOR_DIAGNOSTICS = false;

// ---------- Control tuning ----------
constexpr int MAX_PWM = 255;
constexpr int STICK_DEADZONE = 45;
constexpr float MANUAL_TURN_GAIN = 1.60f;
constexpr float INPUT_SMOOTHING = 0.38f;

// Conservative first-run limits for the imported AI. Raise only after safe testing.
constexpr int AUTO_MAX_PWM = 120;
constexpr float AUTO_THROTTLE_LIMIT = 0.45f;
constexpr float AUTO_STEERING_LIMIT = 0.45f;
constexpr float AUTO_TURN_GAIN = 1.0f;
constexpr uint32_t SERIAL_BAUD = 115200;
constexpr uint32_t SENSOR_UPDATE_INTERVAL_MS = 40;  // IR sensor response is ~38 ms
constexpr uint32_t DIAGNOSTIC_INTERVAL_MS = 500;

// GP2Y0A21YK0F: approximate voltage-to-distance curve, distance(cm) = 29.988 * V^-1.173.
// Output is divided by 2/3 before reaching the ESP32 ADC, then reconstructed below.
constexpr float ADC_TO_SENSOR_VOLTAGE_RATIO = 1.5f;
constexpr float SENSOR_MIN_VALID_OUTPUT_V = 0.15f;
constexpr float SENSOR_TOO_CLOSE_V = 2.80f;  // stop if approaching the <10 cm blind range
constexpr float SENSOR_DISTANCE_MIN_CM = 10.0f;
constexpr float SENSOR_DISTANCE_MAX_CM = 80.0f;

ControllerPtr controllers[BP32_MAX_GAMEPADS] = {};
float smoothedThrottle = 0.0f;
float smoothedSteering = 0.0f;
bool autonomousMode = false;
bool lastModeButton = false;
uint32_t lastSensorUpdateMs = 0;
uint32_t lastDiagnosticMs = 0;
uint32_t lastSensorErrorPrintMs = 0;

float clampUnit(float value) {
  if (value > 1.0f) return 1.0f;
  if (value < -1.0f) return -1.0f;
  return value;
}

float clampRange(float value, float low, float high) {
  if (value < low) return low;
  if (value > high) return high;
  return value;
}

void setMotor(int pwmPin, int in1Pin, int in2Pin, int speedValue) {
  speedValue = constrain(speedValue, -255, 255);
  analogWrite(pwmPin, 0);
  if (speedValue > 0) {
    digitalWrite(in1Pin, HIGH);
    digitalWrite(in2Pin, LOW);
    analogWrite(pwmPin, speedValue);
  } else if (speedValue < 0) {
    digitalWrite(in1Pin, LOW);
    digitalWrite(in2Pin, HIGH);
    analogWrite(pwmPin, -speedValue);
  } else {
    digitalWrite(in1Pin, LOW);
    digitalWrite(in2Pin, LOW);
  }
}

void driveCar(int leftSpeed, int rightSpeed) {
  leftSpeed = constrain(leftSpeed, -255, 255);
  rightSpeed = constrain(rightSpeed, -255, 255);
  setMotor(MOTOR_TOP_PWMA, MOTOR_TOP_AI1, MOTOR_TOP_AI2, leftSpeed);
  setMotor(MOTOR_BOT_PWMA, MOTOR_BOT_AIN1, MOTOR_BOT_AIN2, leftSpeed);
  setMotor(MOTOR_TOP_PWMB, MOTOR_TOP_BI1, MOTOR_TOP_BI2, rightSpeed);
  setMotor(MOTOR_BOT_PWMB, MOTOR_BOT_BIN1, MOTOR_BOT_BIN2, rightSpeed);
}

void stopCar() { driveCar(0, 0); }

void initializeMotorPins() {
  const int outputPins[] = {
    MOTOR_TOP_PWMA, MOTOR_TOP_AI1, MOTOR_TOP_AI2,
    MOTOR_TOP_PWMB, MOTOR_TOP_BI1, MOTOR_TOP_BI2,
    MOTOR_BOT_PWMA, MOTOR_BOT_AIN1, MOTOR_BOT_AIN2,
    MOTOR_BOT_PWMB, MOTOR_BOT_BIN1, MOTOR_BOT_BIN2,
    MOTOR_TOP_STBY, MOTOR_BOT_STBY
  };
  for (int pin : outputPins) {
    pinMode(pin, OUTPUT);
    digitalWrite(pin, LOW);
  }
  stopCar();
  digitalWrite(MOTOR_TOP_STBY, HIGH);
  digitalWrite(MOTOR_BOT_STBY, HIGH);
  delay(20);
  stopCar();
}

float normalizedAxis(int value) {
  const int magnitude = abs(value);
  if (magnitude <= STICK_DEADZONE) return 0.0f;
  float scaled = static_cast<float>(magnitude - STICK_DEADZONE) /
                 static_cast<float>(512 - STICK_DEADZONE);
  if (scaled > 1.0f) scaled = 1.0f;
  return (value < 0) ? -scaled : scaled;
}

int commandToManualPwm(float command) {
  command = clampUnit(command);
  const float magnitude = fabsf(command);
  if (magnitude < 0.005f) return 0;
  const float curved = powf(magnitude, 0.45f);  // keep known-good v4 curve
  const int pwm = static_cast<int>(curved * MAX_PWM + 0.5f);
  return (command < 0.0f) ? -pwm : pwm;
}

int commandToAutoPwm(float command) {
  command = clampUnit(command);
  const float magnitude = fabsf(command);
  if (magnitude < 0.02f) return 0;
  // Same general response curve as manual, but limited to AUTO_MAX_PWM for the first tests.
  const int pwm = static_cast<int>(powf(magnitude, 0.45f) * AUTO_MAX_PWM + 0.5f);
  return (command < 0.0f) ? -pwm : pwm;
}

void processGamepad(ControllerPtr ctl) {
  const float targetThrottle = -normalizedAxis(ctl->axisY());
  const float targetSteering = -normalizedAxis(ctl->axisRX());  // keep v4 steering direction
  smoothedThrottle += (targetThrottle - smoothedThrottle) * INPUT_SMOOTHING;
  smoothedSteering += (targetSteering - smoothedSteering) * INPUT_SMOOTHING;
  float left = clampUnit(smoothedThrottle + smoothedSteering * MANUAL_TURN_GAIN);
  float right = clampUnit(smoothedThrottle - smoothedSteering * MANUAL_TURN_GAIN);
  driveCar(commandToManualPwm(left), commandToManualPwm(right));
}

// Convert a GP2Y0A21YK0F analog sensor into an NN input in [0,1].
// The Python NN uses pixel_distance / 150; we map the physical 10..80 cm span to 0..1.
bool readOneSensor(int pin, float &normalizedDistance, float &distanceCm, float &sensorOutputV) {
  normalizedDistance = 0.0f;
  distanceCm = NAN;
  sensorOutputV = 0.0f;
  uint32_t totalMilliVolts = 0;
  constexpr int SAMPLE_COUNT = 5;
  for (int i = 0; i < SAMPLE_COUNT; ++i) {
    totalMilliVolts += analogReadMilliVolts(pin);  // voltage at ADC node, after divider
    delayMicroseconds(250);
  }
  const float adcNodeV = (static_cast<float>(totalMilliVolts) / SAMPLE_COUNT) / 1000.0f;
  sensorOutputV = adcNodeV * ADC_TO_SENSOR_VOLTAGE_RATIO;

  // An open/short sensor or an object inside the unreliable <10 cm zone fails safe.
  if (adcNodeV < 0.08f || sensorOutputV < SENSOR_MIN_VALID_OUTPUT_V ||
      sensorOutputV > SENSOR_TOO_CLOSE_V) {
    return false;
  }

  distanceCm = 29.988f * powf(sensorOutputV, -1.173f);
  if (!isfinite(distanceCm)) return false;
  distanceCm = clampRange(distanceCm, SENSOR_DISTANCE_MIN_CM, SENSOR_DISTANCE_MAX_CM);
  normalizedDistance = (distanceCm - SENSOR_DISTANCE_MIN_CM) /
                       (SENSOR_DISTANCE_MAX_CM - SENSOR_DISTANCE_MIN_CM);
  normalizedDistance = clampUnit(normalizedDistance);
  return true;
}

bool readAllSensors(float inputs[AI_INPUTS], float distancesCm[AI_INPUTS], float voltages[AI_INPUTS]) {
  bool allValid = true;
  for (int i = 0; i < AI_INPUTS; ++i) {
    if (!readOneSensor(SENSOR_PINS[i], inputs[i], distancesCm[i], voltages[i])) {
      allValid = false;
    }
  }
  return allValid;
}

// Exact inference structure for ai/neural_network.py:
// x=clip(sensor/150,0,1); hidden=tanh(x@W1+b1); output=tanh(hidden@W2+b2).
// Inputs here are already normalized to [0,1]. output[0]=steering, output[1]=throttle.
void predictAI(const float inputs[AI_INPUTS], float output[AI_OUTPUTS]) {
  float hidden[AI_HIDDEN];
  for (int j = 0; j < AI_HIDDEN; ++j) {
    float sum = BEST_GENOME_WEIGHTS[40 + j];  // b1
    for (int i = 0; i < AI_INPUTS; ++i) {
      sum += inputs[i] * BEST_GENOME_WEIGHTS[i * AI_HIDDEN + j]; // W1 row-major
    }
    hidden[j] = tanhf(sum);
  }
  for (int k = 0; k < AI_OUTPUTS; ++k) {
    float sum = BEST_GENOME_WEIGHTS[64 + k];  // b2
    for (int j = 0; j < AI_HIDDEN; ++j) {
      sum += hidden[j] * BEST_GENOME_WEIGHTS[48 + j * AI_OUTPUTS + k]; // W2 row-major
    }
    output[k] = tanhf(sum);
  }
}

void printSensorDiagnostics() {
  if (!ENABLE_SENSOR_DIAGNOSTICS || millis() - lastDiagnosticMs < DIAGNOSTIC_INTERVAL_MS) return;
  lastDiagnosticMs = millis();
  float inputs[AI_INPUTS] = {};
  float distances[AI_INPUTS] = {};
  float volts[AI_INPUTS] = {};
  bool validSensors[AI_INPUTS] = {};
  bool allValid = true;
  for (int i = 0; i < AI_INPUTS; ++i) {
    validSensors[i] = readOneSensor(SENSOR_PINS[i], inputs[i], distances[i], volts[i]);
    if (!validSensors[i]) allValid = false;
  }
  Serial.print("Sensor test: ");
  for (int i = 0; i < AI_INPUTS; ++i) {
    if (validSensors[i]) {
      Serial.printf("S%d=%.1fcm/%.2fV ", i + 1, distances[i], volts[i]);
    } else {
      Serial.printf("S%d=INVALID/%.2fV ", i + 1, volts[i]);
    }
  }
  Serial.println(allValid ? " OK" : " CHECK SENSOR / DISTANCE");
}

void processAutonomous() {
  if (millis() - lastSensorUpdateMs < SENSOR_UPDATE_INTERVAL_MS) return;
  lastSensorUpdateMs = millis();

  float inputs[AI_INPUTS], distances[AI_INPUTS], volts[AI_INPUTS];
  if (!readAllSensors(inputs, distances, volts)) {
    stopCar();
    if (millis() - lastSensorErrorPrintMs >= 1000) {
      lastSensorErrorPrintMs = millis();
      Serial.println("AUTO STOP: sensor invalid/too close. Check sensors or move car away from wall.");
    }
    return;
  }

  float output[AI_OUTPUTS];
  predictAI(inputs, output);
  float steering = clampRange(output[0], -AUTO_STEERING_LIMIT, AUTO_STEERING_LIMIT);
  float throttle = clampRange(output[1], -AUTO_THROTTLE_LIMIT, AUTO_THROTTLE_LIMIT);

  float left = clampUnit(throttle + steering * AUTO_TURN_GAIN);
  float right = clampUnit(throttle - steering * AUTO_TURN_GAIN);
  driveCar(commandToAutoPwm(left), commandToAutoPwm(right));
}

void onConnectedController(ControllerPtr ctl) {
  for (int i = 0; i < BP32_MAX_GAMEPADS; ++i) {
    if (controllers[i] == nullptr) {
      controllers[i] = ctl;
      smoothedThrottle = 0.0f;
      smoothedSteering = 0.0f;
      autonomousMode = false;  // always connect in manual mode
      lastModeButton = false;
      Serial.printf("Controller connected in slot %d\n", i);
      stopCar();
      return;
    }
  }
  Serial.println("Controller connected, but no free slot was available.");
  stopCar();
}

void onDisconnectedController(ControllerPtr ctl) {
  for (int i = 0; i < BP32_MAX_GAMEPADS; ++i) {
    if (controllers[i] == ctl) controllers[i] = nullptr;
  }
  autonomousMode = false;
  smoothedThrottle = 0.0f;
  smoothedSteering = 0.0f;
  stopCar();
  Serial.println("Controller disconnected; motors stopped and manual mode selected.");
}

void setup() {
  Serial.begin(SERIAL_BAUD);
  delay(200);
  initializeMotorPins();
  analogReadResolution(12);
  for (int pin : SENSOR_PINS) {
    analogSetPinAttenuation(pin, ADC_11db);
  }

  Serial.println();
  Serial.println("ESP32 RC car: manual + AI firmware");
  Serial.printf("Loaded best genome: generation %d, fitness %.3f\n",
                AI_MODEL_GENERATION, AI_MODEL_FITNESS);
  Serial.println("Manual: left stick up/down = forward/reverse; right stick = steering.");
  Serial.println("Y button toggles manual/AI only when SENSOR_HARDWARE_READY=true.");
  Serial.println("Sensor diagnostics can be enabled with ENABLE_SENSOR_DIAGNOSTICS=true.");
  Serial.println("Hold B for emergency stop (returns to manual mode).");
  if (!SENSOR_HARDWARE_READY) {
    Serial.println("AI MODE DISABLED: install and verify 5 analog distance sensors, then set SENSOR_HARDWARE_READY=true.");
  }

  BP32.setup(&onConnectedController, &onDisconnectedController);
}

void loop() {
  BP32.update();
  ControllerPtr activeController = nullptr;
  for (int i = 0; i < BP32_MAX_GAMEPADS; ++i) {
    if (controllers[i] != nullptr && controllers[i]->isConnected() && controllers[i]->isGamepad()) {
      activeController = controllers[i];
      break;
    }
  }

  if (activeController == nullptr) {
    autonomousMode = false;
    smoothedThrottle = 0.0f;
    smoothedSteering = 0.0f;
    lastModeButton = false;
    stopCar();
    delay(10);
    return;
  }

  // Hold B as a dead-man/emergency stop. Releasing it returns to manual handling.
  if (activeController->b()) {
    autonomousMode = false;
    smoothedThrottle = 0.0f;
    smoothedSteering = 0.0f;
    lastModeButton = activeController->y();
    stopCar();
    delay(10);
    return;
  }

  const bool modeButton = activeController->y();
  if (modeButton && !lastModeButton) {
    if (!SENSOR_HARDWARE_READY) {
      Serial.println("AI mode request ignored: SENSOR_HARDWARE_READY is false.");
    } else {
      autonomousMode = !autonomousMode;
      smoothedThrottle = 0.0f;
      smoothedSteering = 0.0f;
      lastSensorUpdateMs = 0;
      stopCar();
      Serial.println(autonomousMode ? "MODE: AUTONOMOUS AI" : "MODE: MANUAL");
    }
  }
  lastModeButton = modeButton;

  if (autonomousMode) {
    processAutonomous();
  } else {
    processGamepad(activeController);
    printSensorDiagnostics();
  }
  delay(10);
}
