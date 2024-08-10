import machine
from machine import ADC, Pin, Timer
import random
import st7789
import vga1_bold_16x32 as font
import network
import time
import socket
from umqtt.simple import MQTTClient
import umqtt.simple
import urequests


# Function to connect to Wi-Fi
def connect_to_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('Connecting to network...')
        wlan.connect(ssid, password)
        while not wlan.isconnected():
            pass
    return wlan


# Function to display
def display_message(display, message, x, y, bg, fg):
    display.text(font, message, x, y, bg, fg)
    

# Call back when a publishing message is received from the server
def on_message(topic, msg):
    global latest_cpu_info, latest_memory_info
    if topic == b'cpu/info':  
        # Decode and update the global variable
        latest_cpu_info = msg.decode('utf-8')  
    if topic == b'memory/info':  
        # Decode and update the global variable
        latest_memory_info = msg.decode('utf-8')  


# Function to initiate mqtt client
def connect_mqtt():
    client_id = "RunqiaoLi"
    client = MQTTClient(client_id, MQTT_BROKER, port=MQTT_PORT)
    # Set the callback function
    client.set_callback(on_message)
    client.connect()
    print("Connected to %s MQTT broker" % MQTT_BROKER)
    return client
    

# Function to subscribe topic
def subscribe(client,topics):
    for topic in topics:
        client.subscribe(topic)
        print("Subscribed to %s" % topic)


# Function to publish to topic
def publish_volume_info(client):
    global pot_value
    pot_value = int((adc.read()/4095) * 100) # Read potentiometer value
    client.publish("volume/info", str(pot_value))


class State:
    MENU1, MENU2, MENU3, MENU4, OPTION1, OPTION2, OPTION3, OPTION4 = range(8)


# Switching button logic
def next_button_isr(pin):
    global menu_option_index, last_trigger_time
    current_time = time.ticks_ms()
    if time.ticks_diff(current_time, last_trigger_time) > debounce_time_ms:
        if current_state == State.MENU1:
            menu_option_index = (menu_option_index + 1) % 3
        last_trigger_time = current_time


# Selection button logic
def select_button_isr(pin):
    global current_state, menu_option_index, last_trigger_time
    current_time = time.ticks_ms()
    if time.ticks_diff(current_time, last_trigger_time) > debounce_time_ms:
        if current_state == State.MENU1:
            if menu_option_index == 0:
                current_state = State.MENU2
            elif menu_option_index == 1:
                current_state = State.MENU3
            elif menu_option_index == 2:
                current_state = State.MENU4
        elif current_state in [State.MENU2, State.MENU3, State.MENU4]:
            current_state = State.MENU1
            display.fill(st7789.color565(0,0,0))
            display.fill(st7789.color565(0,0,0))
        last_trigger_time = current_time
    if current_state == State.MENU4:
        try:
            # Hostname or IP address should be changed based on network environment
            # response = urequests.get('http://192.168.1.42:5000/open_page')
            response = urequests.get('http://172.20.10.2:5000/open_page')
            print(response.text)
        except Exception as e:
            print("Failed to send request:", e)


# Parameter for dealing with hardware button bouncing issue
last_trigger_time = 0
debounce_time_ms = 500


# Initialize the state of page and option
current_state = State.MENU1
selected_option = State.OPTION1

# Initialization for IPS LCD Display
spi = machine.SPI(2, baudrate=40000000, polarity=1, sck=machine.Pin(18), mosi=machine.Pin(23))
cs_pin = machine.Pin(5, machine.Pin.OUT)
display = st7789.ST7789(spi, 240, 320, reset=machine.Pin(27, machine.Pin.OUT), dc=machine.Pin(14, machine.Pin.OUT), rotation = 1)
display.init()
display.fill(st7789.color565(0,0,0))
col_max = display.width() - font.WIDTH*6
row_max = display.height() - font.HEIGHT
display_message(display, "Welcome to Your", 12, 120, st7789.color565(50, 168, 151), st7789.color565(168, 50, 50))
display_message(display, "Interaction Hub", 12, 150, st7789.color565(50, 168, 151), st7789.color565(168, 50, 50))
time.sleep(1)

# Connect to Wi-Fi
# ssid and password should be changed according to your wifi settings
ssid = ''
password = ''
wlan = connect_to_wifi(ssid, password)

# Replace with your MQTT broker's hostname or IP
MQTT_BROKER = "172.20.10.2"
MQTT_PORT = 1883
topics = ["cpu/info", "memory/info"]
MQTT_TOPIC = "cpu/info"
menu_option_index = 0

# Initialization of ADC pin
adc = ADC(Pin(32))
adc.atten(ADC.ATTN_11DB)
pot_value = 0

# Initialize mqtt client
client = connect_mqtt()
subscribe(client,topics)

# Initialize PINs
display.fill(st7789.color565(0,0,0))
next_button = Pin(2, Pin.IN, Pin.PULL_DOWN)
select_button = Pin(4, Pin.IN, Pin.PULL_DOWN)
next_button.irq(trigger=Pin.IRQ_RISING, handler=next_button_isr)
select_button.irq(trigger=Pin.IRQ_RISING, handler=select_button_isr)


# Update display according to different services
def timer_callback(timer):
    global current_state, menu_option_index
    if current_state == State.MENU1:
        for i in range(3):
            option_color = st7789.color565(255, 0, 0) if i == menu_option_index else st7789.color565(0, 255, 0)
            if i == 0:
                display_message(display, "Data Monitor", 12, 30, option_color, st7789.color565(50, 10, 151))
            elif i == 1:
                display_message(display, "Volume", 12, 80, option_color, st7789.color565(50, 10, 151))
            elif i == 2:
                display_message(display, "Open Page", 12, 130, option_color, st7789.color565(50, 10, 151))
    elif current_state == State.MENU2:
        display.fill(st7789.color565(0,0,0))
        client.check_msg()
        display_message(display, "CPU usage: ", 12, 40, st7789.color565(50, 10, 151), st7789.color565(0, 255, 0))
        display_message(display, latest_cpu_info + "%", 230, 40, st7789.color565(50, 10, 151), st7789.color565(0, 255, 0))
        display_message(display, "Memory usage", 12, 80, st7789.color565(50, 10, 151), st7789.color565(0, 255, 0))
        display_message(display, latest_memory_info + "%", 230, 80, st7789.color565(50, 10, 151), st7789.color565(0, 255, 0))
    elif current_state == State.MENU3:
        display.fill(st7789.color565(0,0,0))
        display_message(display, "Current volume: " + str(pot_value) + "%", 12, 100, st7789.color565(50, 10, 151), st7789.color565(0, 255, 0))
        publish_volume_info(client)
    elif current_state == State.MENU4:
        display.fill(st7789.color565(0,0,0))
        display_message(display, "Page Opened", 12, 100, st7789.color565(50, 10, 151), st7789.color565(0, 255, 0))


timer = Timer(-1)
timer.init(period=500, mode=Timer.PERIODIC, callback=timer_callback)
