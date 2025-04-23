// The is the code for the ESP32 microcontroller to communicate through a bluetooth terminal.
// It is used to unlock the gate based on the serial input from the safety gate controller.
// Currently this needs to be uploaded to the ESP32 microcontroller via the Arduino IDE, ran with a windows machine.

// Author: Max Chen
// Date: 2025-03-04
// v0.1.3

// Wiring: ESP32 Pin D2 -- Onboard LED
// Wiring: ESP32 Pin D5 -- Green LED -- GND
// Wiring: ESP32 Pin D25 -- Red LED -- GND
// Wiring: ESP32 Pin D26 -- Electric Lock -- Lowside MOSFET Switch

// This is the code for the ESP32 microcontroller to communicate through a bluetooth terminal.
#include <BluetoothSerial.h>

BluetoothSerial ESP_BT;     // Bluetooth Serial Object
const int ledPin = 2;       // Onboard LED pin is on Pin D2
const int greenLEDPin = 5;  // Green LED pin for Unlocked state on Pin D5
const int redLEDPin = 25;   // Red LED pin for Locked state on Pin D25
const int lock = 26;        // The Electric Lock is on Pin D26

// Define states
enum State { LOCKED, UNLOCKED };
State currentState = LOCKED;  // Initial state set to LOCKED

void setup() 
{
  Serial.begin(115200);  // Start serial communication at 115200 baud
  
  // Set up pins for outputs
  pinMode(ledPin, OUTPUT);
  pinMode(greenLEDPin, OUTPUT);  
  pinMode(redLEDPin, OUTPUT);    
  pinMode(lock, OUTPUT);         
  
  // Initialize state to locked on startup
  digitalWrite(greenLEDPin, LOW);    // Turn off green LED
  digitalWrite(redLEDPin, HIGH);     // Turn on red LED
  digitalWrite(lock, HIGH);          // Set lock to locked state
  
  // Start Bluetooth with a name
  ESP_BT.begin("I_AM_A_GATE-ESP32");
  Serial.println("Bluetooth device is ready to pair.");
  Serial.println("Enter 'send' to send a message over Bluetooth.");
  
  // Send initial lock message
  delay(1000);  // Small delay to allow Bluetooth to initialize

  ESP_BT.println("LOCK THE GATE!");
  Serial.println("Initial lock message sent!");
  
  dashDot();  // Visual indicator for lock command
}

void loop() 
{
  // Check if data is available in the serial buffer
  if (Serial.available())  
  {
    String input = Serial.readStringUntil('\n');  // Read the serial input until a newline character
    
    // Trim any leading/trailing whitespace and convert to lowercase
    input.trim();
    
    // Check if the input matches the word "unlock"
    if (input == "unlock" && currentState != UNLOCKED) 
    {
      // Send Bluetooth message
      ESP_BT.println("OPEN THE GATE!");
      Serial.println("Message sent!");
      currentState = UNLOCKED;  // Update state

      // Blink the LED after sending the message
      dotdotdot();
      digitalWrite(greenLEDPin, HIGH);  // Turn on green LED
      digitalWrite(redLEDPin, LOW);     // Turn off red LED

      // Set lock to unlock
      digitalWrite(lock, LOW);
    }

    // Check if the input matches the word "lock"
    if (input == "lock" && currentState != LOCKED) 
    {
      // Send Bluetooth message
      ESP_BT.println("LOCK THE GATE!");
      Serial.println("Message sent!");
      currentState = LOCKED;  // Update state

      // Blink the LED after sending the message
      dashDot();
      digitalWrite(greenLEDPin, LOW);   // Turn off green LED
      digitalWrite(redLEDPin, HIGH);    // Turn on red LED

      // Set lock to lock
      digitalWrite(lock, HIGH);
    }
  }
}

// Blink the Onboard LED for -.
void dashDot()
{
  digitalWrite(ledPin, HIGH);  // Turn LED on
  delay(175);                  // Wait for 175ms
  digitalWrite(ledPin, LOW);   // Turn LED off
  delay(75);                   // Wait for 75ms
  digitalWrite(ledPin, HIGH);  // Turn LED on
  delay(75);                   // Wait for 75ms
  digitalWrite(ledPin, LOW);   // Turn LED off
  delay(75);                   // Wait for 75ms
}

// Blink the Onboard LED for ...
void dotdotdot() 
{
  for (int i = 0; i <= 3; i++) 
  {
    digitalWrite(ledPin, HIGH);  // Turn LED on
    delay(75);                   // Wait for 75ms
    digitalWrite(ledPin, LOW);   // Turn LED off
    delay(75);                   // Wait for 75ms
  }
}