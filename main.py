# Copyright 2023 Fredrik Lundström


# Import all board pins.
from board import SCL, SDA, A2, A3, A4, A5, board_id, TX, RX
from busio import I2C, UART
from digitalio import DigitalInOut, Direction, Pull
from adafruit_debouncer import Debouncer
from time import sleep

# Import the SSD1306 module (Framebuf)
import adafruit_ssd1306

# Import the SSD1306 module (DisplayIO)
import displayio
import adafruit_displayio_ssd1306

# Import MIDI stuff
import time
import random
import adafruit_midi

from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff
from adafruit_midi.pitch_bend import PitchBend
from adafruit_midi.control_change import ControlChange

print("\n\n==================\n" + board_id + "\n")

MIDI_BAUDRATE = const(31250)

WIDTH   = const(128)
HEIGHT  = const(32)
CHR_W   = const(5+1)
CHR_H   = const(8)
CHARS_PER_LINE  = (WIDTH / CHR_W)# 21.3
nBUT_DOWN   = const(0)
nBUT_UP     = const(1)

MLVL_DEV    = const(1)
MLVL_BANK   = const(2)
MLVL_ITEM   = const(3)
MLVL_SHOW   = const(4)

LEVEL_TOP   = const(MLVL_DEV)
LEVEL_BOT   = const(MLVL_SHOW)

COLOR_BLK   = const(0)
COLOR_BY    = const(1)

# For Feather M0 Express, Metro M0 Express, Metro M4 Express, Circuit Playground Express, QT Py M0
#import neopixel
#led = neopixel.NeoPixel(board.NEOPIXEL, 1)

# For built in red LED on Feather M0 Basic
#led = DigitalInOut(board.D13)
#led.direction = Direction.OUTPUT

# A2/D16: CAN
but_can = DigitalInOut(A2)
but_can.direction = Direction.INPUT
but_can.pull = Pull.UP
but_can_db = Debouncer(but_can)

# A3/D17: LEFT
but_l = DigitalInOut(A3)
but_l.direction = Direction.INPUT
but_l.pull = Pull.UP
but_l_db = Debouncer(but_l)

# A4/D18: RIGHT
but_r = DigitalInOut(A4)
but_r.direction = Direction.INPUT
but_r.pull = Pull.UP
but_r_db = Debouncer(but_r)

# A5/D19: OK
but_ok = DigitalInOut(A5)
but_ok.direction = Direction.INPUT
but_ok.pull = Pull.UP
but_ok_db = Debouncer(but_ok)


addr = 0x3C  # Default I2C address unless otherwise found
# Create the I2C interface.
i2c = I2C(SCL, SDA, frequency=400_000)
i2c.try_lock()
lst = i2c.scan()
print("len=" + str(len(lst)))
if len(lst) > 0:
    addr = lst[0]
    print("addr=" + hex(addr))
else:
    print("I2C slave not found!")
i2c.unlock()

# Create the SSD1306 OLED class from FrameBuf.
# addr is optional. SSD1306 driver defaults to 0x3C, but we can also use the scanned address
display = adafruit_ssd1306.SSD1306_I2C(WIDTH, HEIGHT, i2c, addr=addr)
display.fill_rect(0, 0, WIDTH, CHR_H, COLOR_BLK)
display.show()


# Create the SSD1306 OLED class for DisplayIO.
#displayio.release_displays()
#display_bus = displayio.I2CDisplay(i2c, device_address=addr)
#display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=WIDTH, height=HEIGHT)
# Make the display context
#splash = displayio.Group()
#display.show(splash)


# Configure MIDI
midiuart = UART(TX, RX, baudrate=MIDI_BAUDRATE, timeout= 0.001)
midi = adafruit_midi.MIDI(midi_out=midiuart, midi_in=midiuart, out_channel=10)

print("Default output MIDI channel:", midi.out_channel + 1)


clear_next = 1
do_clear = clear_next
str_dev = "Dev???"
str_bank = "Bank???"
str_item = "Item ???"

level = LEVEL_TOP
index = 1
index_max = 0

midi_devices = ("Roland TD-3", "Volca Keys", "Microfreak", "Cobalt 8M")
midi_channels = (10, 1, 3, 4)
current_device = index-1
current_bank = index-1
current_midi_channel = 1

while True:
    if level == MLVL_DEV:
        index_max = 4

        if index > index_max:
            index = 1
            clear_next = 1

        if index-1  < len(midi_devices):
            current_device = index-1
            current_midi_channel = midi_channels[current_device]
            if current_midi_channel < 10:
                ch = " " + str(current_midi_channel)
            else:
                ch = "" + str(current_midi_channel)
            str_dev = "T" + str(index) + " Ch " + ch + ": " + midi_devices[current_device]

    elif level == MLVL_BANK:
        index_max = 128

        if index > index_max:
            index = 1
            clear_next = 1

        current_bank = index-1
        str_bank = "Bank " + str(current_bank)

    elif level == MLVL_ITEM:
        index_max = 3

        if index > index_max:
            index = 1
            clear_next = 1

        if index == 1:
            str_item = "ITEM 0"
        elif index == 2:
            str_item = "ITEM 1"
        elif index == 3:
            str_item = "SEND MIDI"

    do_clear = clear_next	

    but_can_db.update()
    but_l_db.update()
    but_r_db.update()
    but_ok_db.update()

    if but_can_db.fell:
        if level > LEVEL_TOP:
            level = level -1
            clear_next = 1

    if but_l_db.fell:
        if index > 1:
            index = index -1
            clear_next = 1

    elif but_r_db.fell:
        if index < index_max:
            index = index +1
            clear_next = 1

    elif but_ok_db.fell:
        if level < LEVEL_BOT:
            level = level +1
            index = 1
            clear_next = 1

    if do_clear:
        display.fill_rect(              0, 0, WIDTH,    3*CHR_H, COLOR_BLK)
        if level >= MLVL_SHOW:
            display.text(str_dev,       0,              0*CHR_H, COLOR_BY)
            display.text(str_item,      0,              1*CHR_H, COLOR_BY, size=2)
        else:
            if level >= MLVL_DEV:
                display.text(str_dev,   0,              0*CHR_H, COLOR_BY)
            if level >= MLVL_BANK:
                display.text(str_bank,  0,              1*CHR_H, COLOR_BY)
            if level >= MLVL_ITEM:
                display.text(str_item,  0,              2*CHR_H, COLOR_BY)
        display.show()
        clear_next = 0

    if not clear_next:
        midi_message = midi.receive()
        while midi_message:
            print("MIDI: " + str(midi_message))
            midi_message = midi.receive()


def sendMidi():
	print("Sending NoteOn G#2")
	midi.send(NoteOn(44, 120))  # G sharp 2nd octave
	time.sleep(0.25)
	pb_level = random.randint(0, 16383)
	a_pitch_bend = PitchBend(pb_level)
	print("Sending PitchBend("+str(pb_level)+")")
	midi.send(a_pitch_bend)
	time.sleep(0.25)
	print("Sending NoteOff G#2 + CC3(44)")
	midi.send([NoteOff("G#2", 120),
			   ControlChange(3, 44)])

