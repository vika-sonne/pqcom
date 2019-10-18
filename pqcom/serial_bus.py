
from typing import Iterable, Optional, Callable

import sys
import queue

import threading
import logging

import serial
from serial.tools import list_ports

import re


VID_PID = Iterable[int]

BYTE_SIZE_DICT = {5: serial.FIVEBITS, 6: serial.SIXBITS, 7: serial.SEVENBITS, 8: serial.EIGHTBITS}

PARITY_DICT = {'N': serial.PARITY_NONE,
	'E': serial.PARITY_EVEN, 'O': serial.PARITY_ODD,
	'M': serial.PARITY_MARK, 'S': serial.PARITY_SPACE}

STOP_BITS_DICT = {'1': serial.STOPBITS_ONE, '1.5': serial.STOPBITS_ONE_POINT_FIVE, '2': serial.STOPBITS_TWO}

PORT_NAME_FILTER = ['ACM', 'USB', 'COM', 'cu.']

DEFAULT_TIMEOUT = 0.2

def get_ports() -> Iterable[str]:
	'''Gets list of names of available com ports'''

	def port_name_filter(port_name: str) -> bool:
		for _ in PORT_NAME_FILTER:
			if _ in port_name:
				return True
		return False

	ret = [ p.device for p in list_ports.comports() if port_name_filter(p.name) ]
	ret.sort()
	return ret

def find_port_by_vidpid_list(vidpid: Iterable[VID_PID]) -> Optional[str]:
	for p in list_ports.comports():
		for vid_pid in vidpid:
			if vid_pid[0] == p.vid and vid_pid[1] == p.pid:
				return p.device
	return None

class SerialParameters():

	def __init__(self, baud=115200, bytesize=8, stopbits='1', parity='N'):
		self.set_baud(baud)
		self.set_bytesize(bytesize)
		self.set_stopbits(stopbits)
		self.set_parity(parity)

	def set(self, parameters: str):
		'Sets parameters from string, example: 115200 8N1'
		m = re.match('(\d+)\s+([5678])([NEOMS])([125\.]+)', parameters)
		if not m:
			raise Exception('Wrong com port parameters')
		self.set_baud(int(m.group(1)))
		self.set_bytesize(int(m.group(2)))
		self.set_parity(m.group(3))
		print(m.group(4))
		self.set_stopbits(m.group(4))

	def set_baud(self, baud: int):
		self.baud = baud

	def set_bytesize(self, bytesize: int):
		self.bytesize = BYTE_SIZE_DICT[bytesize]

	def set_stopbits(self, stopbits: str):
		self.stopbits = STOP_BITS_DICT[stopbits]

	def set_parity(self, parity: str):
		self.parity = PARITY_DICT[parity.upper()]

	def __str__(self) -> str:
		return '{} {}{}{}'.format(self.baud, self.bytesize, self.parity, self.stopbits)

	@staticmethod
	def get_vidpid_list(vidpid: Optional[str]) -> Iterable[VID_PID]:
		'Gets from HEX values: VID:PID[,VID:PID[...]]'
		ret = []
		if vidpid:
			for vid_pid in vidpid.split(','):
				vid_pid = vid_pid.split(':')
				if len(vid_pid) == 2:
					ret.append((int(vid_pid[0].strip(), 16), int(vid_pid[1].strip(), 16)))
		return ret


class SerialBus(object):
	'Multithreaded & queued com port RX/TX'

	def __init__(self, on_received: Optional[Callable]=None, on_failed: Optional[Callable]=None):
		self.notify = on_received
		self.fail = on_failed

		self._is_open = False

		self.tx_queue = queue.Queue()
		self.rx_queue = queue.Queue()
		self.serial = None
		self.tx_thread = None
		self.rx_thread = None

		self.stop_event = threading.Event()

	@property
	def is_open(self):
		return self._is_open

	@property
	def port(self):
		return self.serial.port if self.serial else ''

	@property
	def port_and_properties(self):
		if self.serial:
			ret = '{} @ {} {}{}{}'.format(self.serial.port, self.serial.baudrate, self.serial.bytesize,
				self.serial.parity, self.serial.stopbits)
			return ret
		return ''

	def start(self, parameters: SerialParameters,
			port_name: Optional[str]=None, vid_pid: Optional[Iterable[VID_PID]]=None):
		'Starts for RX/TX'

		# close port
		if self.serial:
			self.serial.close()
		self._is_open = False

		if vid_pid:
			# USB VID:PID list
			port_name = find_port_by_vidpid_list(vid_pid)
			if not port_name:
				# VID:PID not found
				self._is_open = False
				if self.fail:
					self.fail()
				return

		# open port
		try:
			self.serial = serial.Serial(port=port_name,
				baudrate=parameters.baud,
				bytesize=parameters.bytesize,
				stopbits=parameters.stopbits,
				parity=parameters.parity,
				timeout=DEFAULT_TIMEOUT)
			self.tx_queue.queue.clear()
			self.rx_queue.queue.clear()
			self.stop_event.set()
			self.tx_thread = threading.Thread(target=self._send)
			self.rx_thread = threading.Thread(target=self._recv)
			self.stop_event.clear()
			self.tx_thread.start()
			self.rx_thread.start()
			self._is_open = True
		except IOError as e:
			logging.warning(e)
			self._is_open = False
			if self.fail:
				self.fail()

	def join(self):
		self.stop_event.set()
		if self.tx_thread:
			self.tx_thread.join()
			self.rx_thread.join()

		if self.serial:
			self.serial.close()
		self._is_open = False

	def write(self, data):
		self.tx_queue.put(data)

	def read(self):
		return self.rx_queue.get()

	def _send(self):
		logging.info('tx thread is started')
		while not self.stop_event.is_set():
			try:
				data = self.tx_queue.get(True, 1)
				logging.info('tx:' + data)
				self.serial.write(data.encode())
			except queue.Empty:
				continue
			except IOError as e:
				logging.warning(e)
				self.serial.close()
				self._is_open = False
				self.stop_event.set()
				if self.fail:
					self.fail()

		logging.info('tx thread exits')

	def _recv(self):
		logging.info('rx thread is started')
		while not self.stop_event.is_set():
			try:
				data = self.serial.read(1024)

				if data and len(data) > 0:
					data = data.decode('utf-8', 'replace')
					logging.info('rx:' + data)
					self.rx_queue.put(data)
					if self.notify:
						self.notify()
			except IOError as e:
				logging.warning(e)
				self.serial.close()
				self._is_open = False
				self.stop_event.set()
				if self.fail:
					self.fail()

		logging.info('rx thread exits')


if __name__ == '__main__':

	# test for USB VID:PID list

	vidpid_list = SerialParameters.get_vidpid_list('03eb:6124,03eb:2404')
	print('Wait for VID:PIDs: ', vidpid_list)

	p = SerialParameters()
	s = SerialBus()
	try:
		s.start(parameters=p, vid_pid=vidpid_list)
		print('Opened port: '+s.port_and_properties)
		while True:
			print(s.read())
	except Exception as e:
		print(e)
