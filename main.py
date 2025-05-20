from machine import Pin, PWM
import bluetooth
import time
import struct

# BLE setup constants
_IRQ_CENTRAL_CONNECT = 1
_IRQ_CENTRAL_DISCONNECT = 2
_IRQ_GATTS_WRITE = 3

# Initialize pins for digital control
in1_pin = Pin(7, Pin.OUT)  # backwards 1
in2_pin = Pin(8, Pin.OUT)  # forwards 1

# Set all pins to LOW initially
in1_pin.value(0)
in2_pin.value(0)

# Program state
program_running = False

# Function to stop motors
def stop_motors():
    in1_pin.value(0)
    in2_pin.value(0)

# Motor control functions
def forward(duration=2):
    stop_motors()
    in2_pin.value(1)
    time.sleep(duration)
    stop_motors()

# Function to run the main program
def run_program():
    print("Starting main program")
    # Example program sequence
    forward(3)   # Move forward for 3 seconds
    time.sleep(1)
    backward(3)  # Move backward for 3 seconds
    time.sleep(1)
    left(2)      # Turn left for 2 seconds
    time.sleep(1)
    right(2)     # Turn right for 2 seconds
    time.sleep(1)
    print("Program completed")

class BLEServer:
    def __init__(self):
        self.name = "MotorControl"
        self.ble = bluetooth.BLE()
        self.ble.active(True)
        self.ble.irq(self.ble_irq)
        self.register_services()
        
        # Flag to track connection state
        self.connected = False
        
        # Start advertising
        self.advertise()
        
        print("BLE Server initialized - waiting for commands")
    
    def ble_irq(self, event, data):
        global program_running
        
        if event == _IRQ_CENTRAL_CONNECT:
            self.connected = True
            print("BLE Central connected")
            led.value(1)  # Turn LED on when connected
        
        elif event == _IRQ_CENTRAL_DISCONNECT:
            self.connected = False
            print("BLE Central disconnected")
            led.value(0)  # Turn LED off when disconnected
            program_running = False  # Stop program if disconnected
            stop_motors()  # Safety stop
            # Start advertising again
            self.advertise()
        
        elif event == _IRQ_GATTS_WRITE:
            # Get the data from the write
            buffer = self.ble.gatts_read(self.rx_handle)
            if buffer:
                try:
                    message = buffer.decode('utf-8')
                    print(f"Received: {message}")
                    
                    # Process commands
                    if message == 'start':
                        program_running = True
                        forward()
                        print("Program started remotely")
                    elif message == 'stop':
                        program_running = False
                        stop_motors()
                        print("Program stopped remotely")
                    
                except Exception as e:
                    print(f"Error processing message: {e}")
    
    def register_services(self):
        # Define UART service
        UART_UUID = bluetooth.UUID('6E400001-B5A3-F393-E0A9-E50E24DCCA9E')
        UART_TX = bluetooth.UUID('6E400003-B5A3-F393-E0A9-E50E24DCCA9E')
        UART_RX = bluetooth.UUID('6E400002-B5A3-F393-E0A9-E50E24DCCA9E')
        
        # Create service
        services = (
            (UART_UUID, (
                (UART_TX, bluetooth.FLAG_NOTIFY),
                (UART_RX, bluetooth.FLAG_WRITE),
            )),
        )
        
        # Add the service
        ((self.tx_handle, self.rx_handle),) = self.ble.gatts_register_services(services)
    
    def advertise(self):
        # Simple advertisement data
        name = bytes(self.name, 'utf-8')
        
        # Make advertising payload
        adv_payload = bytearray()
        adv_payload.extend(struct.pack('BB', 0x02, 0x01))  # Flags
        adv_payload.extend(bytes([0x06]))
        adv_payload.extend(struct.pack('BB', len(name) + 1, 0x09))  # Name
        adv_payload.extend(name)
        
        # Start advertising
        self.ble.gap_advertise(100, adv_payload)
        print(f"Advertising as {self.name}")

# Initialize BLE server
server = BLEServer()

# Main loop
print("System ready - send 'start' over Bluetooth to begin program and run the motor")
while True:
    if program_running:
        run_program()
        program_running = False  # Program runs once then stops
    time.sleep(0.1)
