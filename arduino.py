#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// Define motor control pins - using your original pin definitions
#define MOTOR1_FORWARD 8    // D8 - forwards 1
#define MOTOR1_BACKWARD 7   // D7 - backwards 1
#define MOTOR2_FORWARD 9    // D9 - forwards 2
#define MOTOR2_BACKWARD 10  // D10 - backwards 2

// BLE UUIDs - using your original UUIDs
#define SERVICE_UUID        "87654321-4321-4321-4321-0987654321ba"
#define CHARACTERISTIC_UUID "fedcbafe-4321-8765-4321-fedcbafedcba"

// Motor speed settings
#define PWM_FREQUENCY 5000
#define PWM_RESOLUTION 8  // 8-bit resolution (0-255)
#define PWM_MAX_DUTY 255
#define DEFAULT_SPEED 128 // 50% speed

// PWM channels
#define PWM_CHANNEL_1 0
#define PWM_CHANNEL_2 1

// Connection flag
bool deviceConnected = false;

// BLE Server pointers
BLEServer* pServer = NULL;
BLECharacteristic* pCharacteristic = NULL;

// Function prototypes
void stopMotors();
void processCommand(uint8_t* data, size_t length);

// Server callbacks
class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
      deviceConnected = true;
      Serial.println("Client connected");
    };

    void onDisconnect(BLEServer* pServer) {
      deviceConnected = false;
      Serial.println("Client disconnected");
      
      // Stop motors when client disconnects
      stopMotors();
      
      // Restart advertising
      BLEDevice::startAdvertising();
    }
};

// Characteristic callbacks
class MyCharacteristicCallbacks: public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pCharacteristic) {
      std::string rxValue = pCharacteristic->getValue();
      
      if (rxValue.length() > 0) {
        uint8_t* data = (uint8_t*)rxValue.data();
        size_t length = rxValue.length();
        
        // Check for header byte (0xAA)
        if (length > 0 && data[0] == 0xAA) {
          // Process the command (remove header byte)
          processCommand(data + 1, length - 1);
        }
      }
    }
};

void setup() {
  Serial.begin(115200);
  Serial.println("ESP32 BLE Motor Controller");
  
  // Initialize motor pins
  pinMode(MOTOR1_FORWARD, OUTPUT);
  pinMode(MOTOR1_BACKWARD, OUTPUT);
  pinMode(MOTOR2_FORWARD, OUTPUT);
  pinMode(MOTOR2_BACKWARD, OUTPUT);
  
  // Stop motors initially
  digitalWrite(MOTOR1_FORWARD, LOW);
  digitalWrite(MOTOR1_BACKWARD, LOW);
  digitalWrite(MOTOR2_FORWARD, LOW);
  digitalWrite(MOTOR2_BACKWARD, LOW);
  
  // Configure PWM
  ledcSetup(PWM_CHANNEL_1, PWM_FREQUENCY, PWM_RESOLUTION);
  ledcSetup(PWM_CHANNEL_2, PWM_FREQUENCY, PWM_RESOLUTION);
  ledcAttachPin(MOTOR1_FORWARD, PWM_CHANNEL_1);
  ledcAttachPin(MOTOR2_FORWARD, PWM_CHANNEL_2);
  
  // Initialize BLE
  BLEDevice::init("ESP32_Receiver");
  
  // Create BLE Server
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());
  
  // Create BLE Service
  BLEService *pService = pServer->createService(SERVICE_UUID);
  
  // Create BLE Characteristic
  pCharacteristic = pService->createCharacteristic(
                      CHARACTERISTIC_UUID,
                      BLECharacteristic::PROPERTY_WRITE
                    );
  
  pCharacteristic->setCallbacks(new MyCharacteristicCallbacks());
  
  // Start the service
  pService->start();
  
  // Start advertising
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(true);
  pAdvertising->setMinPreferred(0x06);  
  pAdvertising->setMinPreferred(0x12);
  BLEDevice::startAdvertising();
  
  Serial.println("BLE Motor Controller ready - waiting for connections...");
}

void loop() {
  // Nothing to do here - BLE handling is done in callbacks
  delay(100);
}

// Function to stop all motors
void stopMotors() {
  digitalWrite(MOTOR1_FORWARD, LOW);
  digitalWrite(MOTOR1_BACKWARD, LOW);
  digitalWrite(MOTOR2_FORWARD, LOW);
  digitalWrite(MOTOR2_BACKWARD, LOW);
  
  ledcWrite(PWM_CHANNEL_1, 0);
  ledcWrite(PWM_CHANNEL_2, 0);
  
  Serial.println("Motors stopped");
}

// Process the received command to control motors
void processCommand(uint8_t* data, size_t length) {
  // Check if we have enough data (at least one byte for command)
  if (length < 1) return;
  
  uint8_t command = data[0];
  uint8_t speed = (length > 1) ? data[1] : DEFAULT_SPEED;
  
  Serial.print("Command: ");
  Serial.print(command);
  Serial.print(", Speed: ");
  Serial.println(speed);
  
  switch (command) {
    case 1: // W - Forward
      Serial.println("Moving forward");
      digitalWrite(MOTOR1_BACKWARD, LOW);
      digitalWrite(MOTOR2_BACKWARD, LOW);
      
      // Use PWM for forward direction
      ledcWrite(PWM_CHANNEL_1, speed);
      ledcWrite(PWM_CHANNEL_2, speed);
      
      digitalWrite(MOTOR1_FORWARD, HIGH);
      digitalWrite(MOTOR2_FORWARD, HIGH);
      break;
      
    case 2: // S - Backward
      Serial.println("Moving backward");
      digitalWrite(MOTOR1_FORWARD, LOW);
      digitalWrite(MOTOR2_FORWARD, LOW);
      
      digitalWrite(MOTOR1_BACKWARD, HIGH);
      digitalWrite(MOTOR2_BACKWARD, HIGH);
      
      // Full speed for backward (no PWM)
      ledcWrite(PWM_CHANNEL_1, 0);
      ledcWrite(PWM_CHANNEL_2, 0);
      break;
      
    case 3: // A - Left
      Serial.println("Turning left");
      digitalWrite(MOTOR1_FORWARD, LOW);
      digitalWrite(MOTOR2_BACKWARD, LOW);
      
      digitalWrite(MOTOR1_BACKWARD, HIGH);
      digitalWrite(MOTOR2_FORWARD, HIGH);
      
      // PWM for right motor
      ledcWrite(PWM_CHANNEL_2, speed);
      break;
      
    case 4: // D - Right
      Serial.println("Turning right");
      digitalWrite(MOTOR1_BACKWARD, LOW);
      digitalWrite(MOTOR2_FORWARD, LOW);
      
      digitalWrite(MOTOR1_FORWARD, HIGH);
      digitalWrite(MOTOR2_BACKWARD, HIGH);
      
      // PWM for left motor
      ledcWrite(PWM_CHANNEL_1, speed);
      break;
      
    case 0: // Stop
      Serial.println("Stop command");
      stopMotors();
      break;
      
    default:
      Serial.print("Unknown command: ");
      Serial.println(command);
      break;
  }
}
