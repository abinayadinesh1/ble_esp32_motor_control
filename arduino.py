from machine import Pin, PWM
import bluetooth
import time
import struct

# BLE setup constants
_IRQ_CENTRAL_CONNECT = 1
_IRQ_CENTRAL_DISCONNECT = 2
_IRQ_GATTS_WRITE = 3

# Initialize pins for digital control
in1_pin = Pin(7, Pin.OUT)
in2_pin = Pin(8, Pin.OUT)
in3_pin = Pin(9, Pin.OUT)
in4_pin = Pin(10, Pin.OUT)

# Set all pins LOW
in1_pin.value(0)
in2_pin.value(0)
in3_pin.value(0)
in4_pin.value(0)

# Status LED
led = Pin(13, Pin.OUT)

# Flag to track if test is running
test_running = False

# Emergency stop function
def emergency_stop():
    global test_running
    print("EMERGENCY STOP ACTIVATED")
    
    # First reset all pins as digital outputs
    in1 = Pin(7, Pin.OUT)
    in2 = Pin(8, Pin.OUT)
    in3 = Pin(9, Pin.OUT)
    in4 = Pin(10, Pin.OUT)
    
    # Set all pins LOW
    in1.value(0)
    in2.value(0)
    in3.value(0)
    in4.value(0)
    
    # Set test_running flag to False to interrupt the test
    test_running = False
    
    # Flash LED rapidly to indicate emergency stop
    for _ in range(5):
        led.value(1)
        time.sleep(0.05)
        led.value(0)
        time.sleep(0.05)
    
    print("Motors stopped")

# Your test_motors function
def test_motors():
    global test_running
    test_running = True
    print("Starting motor test sequence")
    
    try:
        # Initialize pins without specifying Pin.OUT mode
        in1_pin = Pin(7)
        in2_pin = Pin(8)
        in3_pin = Pin(9)
        in4_pin = Pin(10)
        
        # Create PWM objects with frequency and duty in constructor
        pwm3 = PWM(in3_pin, freq=5000, duty=0)  # forwards 2
        pwm4 = PWM(in4_pin, freq=5000, duty=0)  # backwards 2
        
        # Test all motors stopped
        print("All motors should be stopped now")
        pwm3.duty(0)
        pwm4.duty(0)
        time.sleep(1)  # Shorter initial wait
        
        # Periodically check if we should stop
        if not test_running:
            return
            
        # Test motor speed ramping for Motor B - faster ramp-up
        print("Testing Motor B speed ramping (forward)")
        # Faster ramp-up with larger step size (200 instead of 100)
        for duty in range(0, 1024, 200):
            if not test_running:
                break
            print(f"Motor B speed: {duty/10.23:.0f}%")
            pwm3.duty(duty)
            time.sleep(0.2)  # Shorter delay between steps (0.2s instead of 0.5s)
        
        # Run at full speed for a longer time
        print("Running Motor B forward at full speed")
        pwm3.duty(1023)  # Full speed
        
        # Check for stop command during the 5-second run
        for _ in range(50):  # 50 x 0.1s = 5 seconds
            if not test_running:
                break
            time.sleep(0.1)
            
        pwm3.duty(0)
        time.sleep(1)  # Short pause between directions
        
        if not test_running:
            pwm3.deinit()
            pwm4.deinit()
            return
        
        # Test motor speed ramping for Motor B backwards - faster ramp-up
        print("Testing Motor B speed ramping (backward)")
        for duty in range(0, 1024, 200):
            if not test_running:
                break
            print(f"Motor B speed: {duty/10.23:.0f}%")
            pwm4.duty(duty)
            time.sleep(0.2)  # Shorter delay between steps
        
        # Run at full speed for a longer time
        print("Running Motor B backward at full speed")
        pwm4.duty(1023)  # Full speed
        
        # Check for stop command during the 5-second run
        for _ in range(50):  # 50 x 0.1s = 5 seconds
            if not test_running:
                break
            time.sleep(0.1)
            
        pwm4.duty(0)
        
        print("Motor test sequence completed")
        
    except Exception as e:
        print(f"Error during test: {e}")
    
    finally:
        # Cleanup - ensure PWM is properly shut down
        try:
            pwm3.duty(0)
            pwm4.duty(0)
            pwm3.deinit()
            pwm4.deinit()
        except:
            # If PWM objects weren't created, force digital stop
            emergency_stop()
    
    test_running = False

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
        
        print("BLE Server initialized - send 'start' to begin or 'stop' to halt")
    
    def ble_irq(self, event, data):
        global test_running
        
        if event == _IRQ_CENTRAL_CONNECT:
            self.connected = True
            print("BLE Central connected")
            led.value(1)  # Turn LED on when connected
        
        elif event == _IRQ_CENTRAL_DISCONNECT:
            self.connected = False
            print("BLE Central disconnected")
            led.value(0)  # Turn LED off when disconnected
            # Stop motors if test is running and we disconnect
            if test_running:
                emergency_stop()
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
                    if message == 'start' and not test_running:
                        print("Start command received")
                        # Indicate receipt with LED blinks
                        for _ in range(3):
                            led.value(0)
                            time.sleep(0.1)
                            led.value(1)
                            time.sleep(0.1)
                        
                        # Run the test_motors function
                        import _thread
                        _thread.start_new_thread(test_motors, ())
                        
                    elif message == 'stop':
                        print("Stop command received")
                        # Emergency stop
                        emergency_stop()
                        
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

# Make sure motors are stopped at startup
emergency_stop()

# Initialize BLE server
server = BLEServer()

# Main loop - just keep the program running
while True:
    time.sleep(0.1)
