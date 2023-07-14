# Copyright 2023 Fredrik Lundström


# Import all board pins.
from board import SCL, SDA, A2, A3, A4, A5, board_id, TX, RX
from busio import I2C, UART
from digitalio import DigitalInOut, Direction, Pull
from adafruit_debouncer import Debouncer

# Import the SSD1306 module (Framebuf)
import adafruit_ssd1306

# Import the SSD1306 module (DisplayIO)
import displayio
import adafruit_displayio_ssd1306

# Import MIDI stuff
import adafruit_midi

from adafruit_midi.midi_message import MIDIMessage
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff
from adafruit_midi.pitch_bend import PitchBend
from adafruit_midi.control_change import ControlChange
from adafruit_midi.channel_pressure import ChannelPressure

from cedargrove_midi_tools import note_to_name, cc_code_to_description


# And other stuff
import time
import random


print("\n\n==================\n" + board_id + "\n")

MIDI_BAUDRATE	= const(31250)

WIDTH   		= const(128)
HEIGHT  		= const(32)
CHR_W   		= const(5+1)
CHR_H   		= const(8)
CHARS_PER_LINE  = WIDTH / CHR_W		# 21.3
LR_FMT 			= "{}{:<" + str(CHARS_PER_LINE-1-4) + 				       "}{:>3}"
NOTE_FMT 		= "{}{:<" + str(CHARS_PER_LINE-1-5-4) + 			 "} Vel: {:>3}"
NOTE_PRS_FMT	= "{}{:<" + str(CHARS_PER_LINE-1-3-4-5-4) + "} P: {:>3} Vel: {:>3}"
MSG_MISSED		= "!"
MSG_NOT_MISSED	= " "
MSG_NONE		= ""
nBUT_DOWN   	= const(0)
nBUT_UP	 		= const(1)

MLVL_DEV		= const(1)
MLVL_BANK   	= const(2)
MLVL_ITEM   	= const(3)
MLVL_SHOW   	= const(4)

MAX_BANKS		= const(128)

LEVEL_TOP   	= const(MLVL_DEV)
LEVEL_BOT   	= const(MLVL_SHOW)

COLOR_BLK   	= const(0)
COLOR_BY		= const(1)

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
midiuart = UART(TX, RX, baudrate=MIDI_BAUDRATE, timeout=0.001)
midi = adafruit_midi.MIDI(midi_out=midiuart, midi_in=midiuart, out_channel=10)

print("Default output MIDI channel:", midi.out_channel + 1)

midi_devices = ("Roland TD-3", "Volca Keys", "Microfreak", "Cobalt 8M")
midi_channels = (10, 1, 3, 4)
selected_banks = []

selected_banks.append(7)
selected_banks.append(9)
selected_banks.append(3)
selected_banks.append(17)


NUM_DEVICES = len(midi_devices)

str_dev = ""
str_bank = ""
str_item = ""
midi_message_str = ""

level = LEVEL_TOP
index = 0
index_max = 0

current_device = index
current_bank = index
selected_channel = 0

last_cc = -1
last_cc_name = ""
last_cc_value = 0
last_note = -1
last_note_name = ""
last_velocity = 0
last_pressure = 0
update_midi = False
do_clear = False
clear_next = True



def refreshDisplay(update_midi_row, clear_now, clear_next):
	refresh = False
	
	if update_midi_row:
		if clear_now:
			display.fill_rect(		 0, 0, WIDTH,	4*CHR_H, COLOR_BLK)
		else:
			display.fill_rect( 0, CHR_H*3, WIDTH,	1*CHR_H, COLOR_BLK)

	elif clear_now:
		display.fill_rect(			 0, 0, WIDTH,	3*CHR_H, COLOR_BLK)

	if clear_now:
		if level >= MLVL_SHOW:
			display.text(str_dev,		0,			0*CHR_H, COLOR_BY)
			display.text(str_item,		0,			1*CHR_H, COLOR_BY, size=2)
		else:
			if level >= MLVL_DEV:
				display.text(str_dev,   0,			0*CHR_H, COLOR_BY)
			if level >= MLVL_BANK:
				display.text(str_bank,  0,			1*CHR_H, COLOR_BY)
			if level >= MLVL_ITEM:
				display.text(str_item,  0,			2*CHR_H, COLOR_BY)
		refresh = True
		clear_next = False

	if update_midi_row:
		display.text(midi_message_str,  0,			3*CHR_H, COLOR_BY)
		refresh = True
		
	if refresh:
		refresh = False
		display.show()		

	return clear_next




while True:
	if level == MLVL_DEV:
		index_max = NUM_DEVICES

		if index >= index_max:
			index = 0
			clear_next = True

		if clear_next:
			if index < NUM_DEVICES:
				current_device = index
				selected_channel = midi_channels[current_device]
				str_dev = "T{} Ch {:>2}: {}".format(index, selected_channel, midi_devices[current_device])
				selected_channel -= 1	# Keep 0-aligned henceforth

	elif level == MLVL_BANK:
		index_max = MAX_BANKS

		if index >= index_max:
			index = 0
			clear_next = True

		if clear_next:			
			str_bank = "Bank {}".format(index)

	elif level == MLVL_ITEM:
		index_max = 3

		if index >= index_max:
			index = 0
			clear_next = True

		if clear_next:
			if index == 0:
				str_item = "ITEM 0"
			elif index == 1:
				str_item = "ITEM 1"
			elif index == 2:
				str_item = "SEND MIDI"

	do_clear = clear_next

	but_can_db.update()
	but_l_db.update()
	but_r_db.update()
	but_ok_db.update()


	if but_can_db.fell:
		if level == MLVL_DEV:
			index = 0
			
		elif level == MLVL_BANK:
			index = current_device
			
		elif level == MLVL_ITEM:
			index = selected_banks[current_device]
			
		elif level == MLVL_SHOW:
			index = index


		if level > LEVEL_TOP:
			level -= 1
			clear_next = True
			do_clear = False

	elif but_l_db.fell:
		if index > 0:
			index -= 1
			clear_next = True
			do_clear = False

	elif but_r_db.fell:
		if index < index_max-1:
			index += 1
			clear_next = True
			do_clear = False

	elif but_ok_db.fell:
		if level == MLVL_DEV:
			index = selected_banks[current_device]
			
		elif level == MLVL_BANK:
			selected_banks[current_device] = index
			
		elif level == MLVL_ITEM:
			index = index

		else:
			index = 0


		if level < LEVEL_BOT:
			level += 1
			clear_next = True
			do_clear = False

	if clear_next and not do_clear:
		midi_message_str = MSG_NONE
		
	clear_next = refreshDisplay(update_midi, do_clear, clear_next)
	update_midi = False
	
	if not clear_next:
		missed_messages = -1
		handle_message = None
		next_midi_message = midi.receive()
		# midi_message = next_midi_message
		while next_midi_message:
			midi_message = next_midi_message
			next_midi_message = midi.receive()
			dropped_messages += 1
			if midi_message.channel == selected_channel:
				missed_messages += 1
				handle_message = midi_message
			

		
		if handle_message  != None:
			midi_message = handle_message
			if missed_messages > 0:
				missed = MSG_MISSED
			else:
				missed = MSG_NOT_MISSED

			if isinstance(midi_message, NoteOn):
				if last_note != midi_message.note:
					last_note = midi_message.note
					last_note_name = note_to_name(last_note)
					
				last_velocity = midi_message.velocity
				midi_message_str = NOTE_FMT.format(missed, last_note_name, last_velocity)
				update_midi = True
			
			elif isinstance(midi_message, ChannelPressure):
				last_pressure = midi_message.pressure
				midi_message_str = NOTE_PRS_FMT.format(missed, last_note_name, last_pressure, last_velocity)
				update_midi = True

			elif isinstance(midi_message, NoteOff):
				if last_note != midi_message.note:
					last_note = midi_message.note
					last_note_name = note_to_name(last_note)
					
				midi_message_str = NOTE_FMT.format(missed, last_note_name, "---")
				update_midi = True
				
			elif isinstance(midi_message, ControlChange):
				if last_cc != midi_message.control:
					last_cc = midi_message.control
					last_cc_name = cc_code_to_description(last_cc)
					
				last_cc_value = midi_message.value
				midi_message_str = LR_FMT.format(missed, last_cc_name, last_cc_value)
				update_midi = True
					
	if midi_message_str is MSG_NONE:
		update_midi = True
			





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

