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
from adafruit_midi.timing_clock import TimingClock
from adafruit_midi.system_exclusive import SystemExclusive
from adafruit_midi.start import Start
from adafruit_midi.stop import Stop
from adafruit_midi.midi_continue import Continue
from adafruit_midi.program_change import ProgramChange
from adafruit_midi.polyphonic_key_pressure import PolyphonicKeyPressure
from adafruit_midi.mtc_quarter_frame import MtcQuarterFrame

from cedargrove_midi_tools import note_to_name, cc_code_to_description


# And other stuff
import time
import random
from supervisor import ticks_ms

_TICKS_PERIOD = const(1<<29)
_TICKS_MAX = const(_TICKS_PERIOD-1)
_TICKS_HALFPERIOD = const(_TICKS_PERIOD//2)

def ticks_add(ticks, delta):
    "Add a delta to a base number of ticks, performing wraparound at 2**29ms."
    return (ticks + delta) % _TICKS_PERIOD

def ticks_diff(ticks1, ticks2):
    "Compute the signed difference between two ticks values, assuming that they are within 2**28 ticks"
    diff = (ticks1 - ticks2) & _TICKS_MAX
    diff = ((diff + _TICKS_HALFPERIOD) & _TICKS_MAX) - _TICKS_HALFPERIOD
    return diff

def ticks_less(ticks1, ticks2):
    "Return true iff ticks1 is less than ticks2, assuming that they are within 2**28 ticks"
    return ticks_diff(ticks1, ticks2) < 0




print("\n\n==================\n" + board_id + "\n")


MIDI_BAUDRATE	= const(31250)
I2C_FREQUENCY	= const(1_000_000)

WIDTH   		= const(128)
HEIGHT  		= const(32)

CHR_W   		= const(5+1)
CHR_H   		= const(8)

CHARS_PER_LINE  = const(WIDTH // CHR_W)		# 21.3
LR_FMT 			= "{}{:<" + str(CHARS_PER_LINE-1-4) + 				       "}{:>3}"
NOTE_FMT 		= "{}{:<" + str(CHARS_PER_LINE-1-5-4) + 			 "} Vel: {:>3}"
NOTE_PRS_FMT	= "{}{:<" + str(CHARS_PER_LINE-1-3-4-5-4) + "} P: {:>3} Vel: {:>3}"
MSG_MISSED		= "!"
MSG_NOT_MISSED	= " "
MSG_NONE		= ""
nBUT_DOWN   	= const(0)
nBUT_UP	 		= const(1)

LEVEL_DEV		= const(1)
LEVEL_ACTION	= const(2)
LEVEL_BANK   	= const(3)
LEVEL_ITEM   	= const(4)
LEVEL_SHOW   	= const(5)

LEVEL_TOP   	= const(LEVEL_DEV)
LEVEL_BOT   	= const(LEVEL_SHOW)

COLOR_BLK   	= const(0)
COLOR_BY		= const(1)


# Executable Actions
ACT_NONE			= const(-1)	# When selecting action
ACT_PROGRAM_CHANGE	= const(0)
ACT_SHOW_MIDI		= const(1)

action				= (ACT_PROGRAM_CHANGE,	ACT_SHOW_MIDI)
action_str			= ("Program Change",	"Show MIDI")

NUM_ACTIONS			= len(action)
assert 				  len(action_str) == NUM_ACTIONS


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
i2c = I2C(SCL, SDA, frequency=I2C_FREQUENCY)
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


# MIDI Devices (hard-coded)
midi_devices	= ("Roland TD-3",	"Volca Keys",	"Microfreak",	"Cobalt 8M")
midi_channels	= (10,				1,				3, 				4)
max_banks 		= (1,				1,				7,				2)
selected_banks	= []

selected_banks.append(0)
selected_banks.append(0)
selected_banks.append(3)
selected_banks.append(1)


NUM_DEVICES 	= len(midi_devices)
assert			  len(midi_channels) == NUM_DEVICES


# And variables


str_dev = ""
str_action = ""
str_bank = ""
str_item = ""
str_status = ""

level = LEVEL_TOP
index = 0
index_max = 0

current_device		= 0
current_action		= 0
current_bank		= 0

selected_channel	= 0
selected_action		= ACT_NONE

last_cc = -1
last_cc_name = ""
last_cc_value = 0
last_note = -1
last_note_name = ""
last_velocity = 0
last_pressure = 0
clear_status_row = False
do_clear = False
clear_next = True


def refreshDisplay(update_status_row, clear_now, clear_next):
	refresh = False
	
	if update_status_row:
		if clear_now:
			display.fill_rect(	0, 			0, WIDTH,	4*CHR_H, COLOR_BLK)
		else:
			display.fill_rect(	0,    CHR_H*3, WIDTH,	1*CHR_H, COLOR_BLK)

	elif clear_now:
		display.fill_rect(		 0, 		0, WIDTH,	3*CHR_H, COLOR_BLK)

	if clear_now:
		if level >= LEVEL_SHOW:
			display.text(str_dev,			0,			0*CHR_H, COLOR_BY)
			display.text(str_action,		0,			1*CHR_H, COLOR_BY)
			display.text(str_item,			0,			2*CHR_H, COLOR_BY, size=2)
		else:		
			if level >= LEVEL_DEV:
				display.text(str_dev,		0,			0*CHR_H, COLOR_BY)

			if level >= LEVEL_ACTION:
				display.text(str_action,	0,			1*CHR_H, COLOR_BY)
			if level >= LEVEL_BANK:
				display.text(str_bank,		0,			2*CHR_H, COLOR_BY)
			if level >= LEVEL_ITEM:
				display.text(str_item,		0,			3*CHR_H, COLOR_BY)
				update_status_row = False
					
		refresh = True
		clear_next = False

	if update_status_row:
		display.text(str_status,  			0,			3*CHR_H, COLOR_BY)
		refresh = True
		
	if refresh:
		refresh = False
		display.show()		

	return clear_next


def forwardMessage(m):
	midi.send(m, m.channel)
	
	

now = ticks_ms()
then = ticks_add(now, 1000)
ignored_messages = 0

while True:
	if level == LEVEL_DEV:
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

	elif selected_action == ACT_NONE:
		if level == LEVEL_ACTION:
			index_max = NUM_ACTIONS

			if index >= index_max:
				index = 0
				clear_next = True

			if clear_next:
				if index < NUM_ACTIONS:
					current_action = index
					str_action = action_str[current_action]					
		
	elif selected_action == ACT_PROGRAM_CHANGE:
		if level == LEVEL_ACTION:
			index_max = NUM_ACTIONS
			
		elif level == LEVEL_BANK:			
			index_max = max_banks[current_device]

			if index >= index_max:
				index = 0
				clear_next = True

			if clear_next:			
				str_bank = "Bank {}".format(index)
				
		elif level == LEVEL_ITEM:
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
					str_item = "ITEM 3"
					
	elif selected_action == ACT_SHOW_MIDI:
		if level == LEVEL_ACTION:
			index_max = NUM_ACTIONS
			
			if index >= index_max:
				index = 0
				clear_next = True

			if clear_next:
				if index < NUM_ACTIONS:
					current_action = index
					str_action = action_str[current_action]					
	
			


	do_clear = clear_next

	but_can_db.update()
	but_l_db.update()
	but_r_db.update()
	but_ok_db.update()


	if but_can_db.fell:
		print("CAN   at level: {} index: {} selected_action: {}".format(level, index, selected_action))
		
		if level == LEVEL_DEV:
			index = 0
			index_max = NUM_ACTIONS
			current_device = 0
			clear_next = True
			do_clear = False
			
		elif level == LEVEL_ACTION:
			index = current_device

		elif level == LEVEL_BANK:
			index = current_device
			
		elif level == LEVEL_ITEM:
			index = selected_banks[current_device]
			
		elif level == LEVEL_SHOW:
			str_status = MSG_NONE


		if level > LEVEL_TOP:
			level -= 1
			clear_next = True
			do_clear = False
			clear_status_row = True


	elif but_l_db.fell:
		print("LEFT  at level: {} index: {} selected_action: {}".format(level, index, selected_action))
		if index > 0:
			index -= 1
			clear_next = True
			do_clear = False
			clear_status_row = False
		print("LEFT -> level: {} index: {} selected_action: {} clear_status_row: {} clear_next: {} do_clear: {}".format(
			level, index, selected_action, clear_status_row, clear_next, do_clear))
			

	elif but_r_db.fell:
		print("RIGHT at level: {} index: {} selected_action: {}".format(level, index, selected_action))
		if index < index_max:
			index += 1
			clear_next = True
			do_clear = False
			clear_status_row = False
		print("RIGHT -> level: {} index: {} selected_action: {} clear_status_row: {} clear_next: {} do_clear: {}".format(
			level, index, selected_action, clear_status_row, clear_next, do_clear))

	elif but_ok_db.fell:
		print("OK    at level: {} index: {} selected_action: {}".format(level, index, selected_action))
		if level == LEVEL_DEV:
			level = LEVEL_ACTION
			index = 0
			index_max = NUM_ACTIONS
			current_action = 0
			clear_next = True
			do_clear = False
			
		elif level >= LEVEL_ACTION:
			if level == LEVEL_ACTION:
				selected_action = action[current_action]
			
			if selected_action == ACT_PROGRAM_CHANGE:
				if level == LEVEL_ACTION:
					level = LEVEL_BANK
					index = selected_banks[current_device]
					
					
				elif level == LEVEL_BANK:
					selected_banks[current_device] = index
					level = LEVEL_ITEM
					index = 0
					
				elif level == LEVEL_ITEM:
					level = LEVEL_SHOW
					str_status = MSG_NONE

					
				elif level == LEVEL_SHOW:
					pass
					
				else:
					assert False, "Invalid level {} for selected_action {}".format(level, selected_action)
					
				clear_next = True
				do_clear = False
				clear_status_row = True
					
			elif selected_action == ACT_SHOW_MIDI:
				if level == LEVEL_ACTION:
					str_bank = MSG_NONE
					str_item = MSG_NONE
					str_status = NOTE_FMT.format(" ", "---", "---")
					clear_next = True
					do_clear = False
					clear_status_row = True

		else:
			index = 0
			
		print("OK    -> level: {} index: {} selected_action: {} clear_status_row: {} clear_next: {} do_clear: {}".format(
			level, index, selected_action, clear_status_row, clear_next, do_clear))



	if clear_next and not do_clear and not clear_status_row:
		str_status = MSG_NONE
		
	clear_next = refreshDisplay(clear_status_row, do_clear, clear_next)
	clear_status_row = False
	
	if not clear_next:
		missed_messages = -1
		handle_message = None
		next_midi_message = midi.receive()
		# midi_message = next_midi_message
		while next_midi_message:
			forwardMessage(next_midi_message)
		
			if isinstance(next_midi_message, TimingClock):
				next_midi_message = midi.receive()
				
			else:
				midi_message = next_midi_message
				next_midi_message = midi.receive()
				if next_midi_message and not isinstance(next_midi_message, TimingClock):
					ignored_messages += 1
					# print(midi_message)
					
				if midi_message.channel == selected_channel:
					missed_messages += 1
					handle_message = midi_message
			
			

		
		if handle_message != None and selected_action == ACT_SHOW_MIDI:
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
				str_status = NOTE_FMT.format(missed, last_note_name, last_velocity)
				clear_status_row = True
			
			elif isinstance(midi_message, ChannelPressure):
				last_pressure = midi_message.pressure
				str_status = NOTE_PRS_FMT.format(missed, last_note_name, last_pressure, last_velocity)
				clear_status_row = True

			elif isinstance(midi_message, NoteOff):
				if last_note != midi_message.note:
					last_note = midi_message.note
					last_note_name = note_to_name(last_note)
					
				str_status = NOTE_FMT.format(missed, last_note_name, "---")
				clear_status_row = True
				
			elif isinstance(midi_message, ControlChange):
				if last_cc != midi_message.control:
					last_cc = midi_message.control
					last_cc_name = cc_code_to_description(last_cc)
					
				last_cc_value = midi_message.value
				str_status = LR_FMT.format(missed, last_cc_name, last_cc_value)
				clear_status_row = True
				
			else:
				print(midi_message)
					
	if str_status is MSG_NONE and selected_action == ACT_SHOW_MIDI:
		clear_status_row = True
			
	now = ticks_ms()
	if ticks_diff(now, then) > 0:
		then = ticks_add(now, 1000)
		if ignored_messages:
			print("MIDI messages ignored: {}".format(ignored_messages))
			ignored_messages = 0





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
