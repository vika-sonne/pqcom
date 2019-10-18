#!/usr/bin/env python3


from typing import Iterable, Optional

import sys
import os
import subprocess
import threading
from time import sleep
import pickle
import argparse

from PyQt5.QtGui import QIcon, QKeySequence, QTextCursor
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog, QAction, QActionGroup, QMenu, QShortcut
from PyQt5.QtCore import Qt, pyqtSignal as Signal
# from PyQt5 import QtSvg

from pqcom import serial_bus
from pqcom import pqcom_translator as translator
from pqcom import setup_dialog
from pqcom import about_ui
from pqcom import main_ui
from pqcom.util import resource_path


PQCOM_DATA_FILE = os.path.join(os.path.expanduser('~'), '.pqcom_data3')
ICON_LIB = {'N': 'img/normal.svg', 'H': 'img/0x.svg', 'E': 'img/ex.svg'}

DEFAULT_EOF = '\n'

serial: Optional[serial_bus.SerialBus] = None


class AboutDialog(QDialog, about_ui.Ui_Dialog):
	def __init__(self, parent=None):
		super(AboutDialog, self).__init__(parent)
		self.setupUi(self)
		self.setWindowFlags(self.windowFlags() ^ Qt.WindowContextHelpButtonHint)

class MainWindow(QMainWindow, main_ui.Ui_MainWindow):
	serial_failed = Signal()
	data_received = Signal()

	def __init__(self, args={}, parent=None):
		super(MainWindow, self).__init__(parent)
		self.setupUi(self)

		self.setWindowIcon(QIcon(resource_path('img/pqcom-logo.png')))

		self.is_last_error = False # is last error or receiving data
		self._reconnect_timer_id = -1

		self.aboutDialog = AboutDialog(self)
		self.setupDialog = setup_dialog.SetupDialog(self)
		self.setupDialog.set_baud(args.baudrate)
		if args.port_parameters and len(args.port_parameters) > 2:
			self.setupDialog.set_bytebits(int(args.port_parameters[0]))
			self.setupDialog.set_parity(args.port_parameters[1])
			self.setupDialog.set_stopbits(args.port_parameters[2:])
		if args.vid_pid:
			self.setupDialog.set_vidpid(args.vid_pid)
		if args.r:
			self.setupDialog.set_reconnect()

		# self.actionNew.setIcon(QIcon(resource_path('img/new.svg')))
		# self.actionSetup.setIcon(QIcon(resource_path('img/settings.svg')))
		# self.actionRun.setIcon(QIcon(resource_path('img/run.svg')))
		# self.actionHex.setIcon(QIcon(resource_path('img/hex.svg')))
		# self.actionClear.setIcon(QIcon(resource_path('img/clear.svg')))
		# self.actionPin.setIcon(QIcon(resource_path('img/pin.svg')))
		# self.actionAbout.setIcon(QIcon(resource_path('img/about.svg')))

		self.actionUseCR = QAction('EOL - \\r', self)
		self.actionUseCR.setCheckable(True)
		self.actionUseLF = QAction('EOL - \\n', self)
		self.actionUseLF.setCheckable(True)
		self.actionUseCRLF = QAction('EOL - \\r\\n', self)
		self.actionUseCRLF.setCheckable(True)
		self.actionUseCRLF.setChecked(True)
		eolGroup = QActionGroup(self)
		eolGroup.addAction(self.actionUseCR)
		eolGroup.addAction(self.actionUseLF)
		eolGroup.addAction(self.actionUseCRLF)
		eolGroup.setExclusive(True)

		self.actionAppendEol = QAction('Append extra EOL', self)
		self.actionAppendEol.setCheckable(True)

		# popup menu
		popupMenu = QMenu(self)
		popupMenu.addAction(self.actionUseCR)
		popupMenu.addAction(self.actionUseLF)
		popupMenu.addAction(self.actionUseCRLF)
		popupMenu.addSeparator()
		popupMenu.addAction(self.actionAppendEol)
		self.sendButton.setMenu(popupMenu)

		# history
		self.input_history = ''
		self.output_history = []
		self.repeater = Repeater()
		self.outputHistoryActions = []
		self.outputHistoryMenu = QMenu(self)
		self.outputHistoryMenu.addAction('None')
		self.historyButton.setMenu(self.outputHistoryMenu)

		self.collectActions = []
		self.collectMenu = QMenu(self)
		self.collectMenu.setTearOffEnabled(True)
		self.collections = []
		try:
			saved = open(PQCOM_DATA_FILE, 'rb')
			self.collections = pickle.load(saved)
			saved.close()
		except IOError:
			pass
		if not self.collections:
			self.collectMenu.addAction('None')
		else:
			for item in self.collections:
				icon = QIcon(resource_path(ICON_LIB[item[0]]))
				action = self.collectMenu.addAction(icon, item[1])
				self.collectActions.append(action)

		self.collectButton.setMenu(self.collectMenu)
		self.collectButton.setIcon(QIcon(resource_path('img/star.svg')))

		self.collectMenu.setContextMenuPolicy(Qt.CustomContextMenu)
		# self.connect(self.collectMenu, QtCore.SIGNAL('customContextMenuRequested(const QPoint&)'),
					#  self.on_collect_context_menu)
		self.collectContextMenu = QMenu(self)
		self.removeCollectionAction = QAction('Remove', self)
		self.removeAllCollectionsAction = QAction('Remove all', self)
		self.collectContextMenu.addAction(self.removeCollectionAction)
		self.collectContextMenu.addAction(self.removeAllCollectionsAction)

		self.activeCollectAction = None

		# connect signals/slots

		self.removeCollectionAction.triggered.connect(self.remove_collection)
		self.removeAllCollectionsAction.triggered.connect(self.remove_all_collections)

		self.sendButton.clicked.connect(self.send)
		self.repeatCheckBox.toggled.connect(self.repeat)
		self.actionSetup.triggered.connect(self.setup)
		self.actionNew.triggered.connect(self.new)
		self.actionRun.toggled.connect(self.run)
		self.actionHex.toggled.connect(self.convert)
		self.actionClear.triggered.connect(self.clear)
		self.actionPin.toggled.connect(self.pin)
		self.actionAbout.triggered.connect(self.aboutDialog.show)
		self.show_send(False)
		self.actionShowSend.toggled.connect(self.show_send)
		self.outputHistoryMenu.triggered.connect(self.on_history_item_clicked)
		self.collectButton.clicked.connect(self.collect)
		self.collectMenu.triggered.connect(self.on_collect_item_clicked)

		self.serial_failed.connect(self.handle_serial_error)
		self.data_received.connect(self.display)

		QShortcut(QKeySequence('Ctrl+Return'), self.sendPlainTextEdit, self.send)

		def gen_shortcut_callback(n):
			def on_shortcut():
				self.send_collection(n - 1)

			return on_shortcut

		for i in range(1, 10):
			QShortcut(QKeySequence('Ctrl+' + str(i)), self, gen_shortcut_callback(i))

		# self.extendRadioButton.setVisible(False)
		self.periodSpinBox.setVisible(False)

		self._show_port_status()

	def _show_port_status(self):
		if serial:
			self.setWindowTitle('pqcom - ' + serial.port_and_properties + (' opened' if serial.is_open else ' closed'))
		else:
			self.setWindowTitle('pqcom')

	def new(self):
		save = open(PQCOM_DATA_FILE, 'wb')
		pickle.dump(self.collections, save)
		save.close()

		args = sys.argv
		if args != [sys.executable]:
			args = [sys.executable] + args
		subprocess.Popen(args)

	def send(self):
		if self.repeatCheckBox.isChecked():
			if self.sendButton.text().find('Stop') >= 0:
				self.repeater.stop()
				self.sendButton.setText('Start')
				return

		raw = str(self.sendPlainTextEdit.toPlainText())
		data = raw
		form = 'N'
		if self.normalRadioButton.isChecked():
			if self.actionAppendEol.isChecked():
				data += '\n'

			if self.actionUseCRLF.isChecked():
				data = data.replace('\n', '\r\n')
			elif self.actionUseCR.isChecked():
				data = data.replace('\n', '\r')
		elif self.hexRadioButton.isChecked():
			form = 'H'
			data = translator.from_hex_string(data)
		else:
			form = 'E'
			data = translator.from_extended_string(data)

		if self.repeatCheckBox.isChecked():
			self.repeater.start(data, self.periodSpinBox.value())
			self.sendButton.setText('Stop')
		else:
			serial.write(data)

		# record history
		record = [form, raw, data]
		if record in self.output_history:
			self.output_history.remove(record)

		self.output_history.insert(0, record)

		self.outputHistoryActions = []
		self.outputHistoryMenu.clear()
		for item in self.output_history:
			icon = QIcon(resource_path(ICON_LIB[item[0]]))

			action = self.outputHistoryMenu.addAction(icon, item[1])
			self.outputHistoryActions.append(action)

	def repeat(self, is_true):
		if is_true:
			self.periodSpinBox.setVisible(True)
			self.sendButton.setText('Start')
		else:
			self.periodSpinBox.setVisible(False)
			self.sendButton.setText('Send')
			self.repeater.stop()

	def on_history_item_clicked(self, action):
		try:
			index = self.outputHistoryActions.index(action)
		except ValueError:
			return

		form, raw, data = self.output_history[index]
		if form == 'H':
			self.hexRadioButton.setChecked(True)
		elif form == 'E':
			self.extendRadioButton.setChecked(True)
		else:
			self.normalRadioButton.setChecked(True)

		self.sendPlainTextEdit.clear()
		self.sendPlainTextEdit.insertPlainText(raw)
		self.send()

	def collect(self):
		if not self.collections:
			self.collectMenu.clear()
		raw = str(self.sendPlainTextEdit.toPlainText())
		form = 'N'
		if self.hexRadioButton.isChecked():
			form = 'H'
		elif self.extendRadioButton.isChecked():
			form = 'E'

		item = [form, raw]
		if item in self.collections:
			return

		self.collections.append(item)
		icon = QIcon(resource_path(ICON_LIB[form]))
		action = self.collectMenu.addAction(icon, raw)
		self.collectActions.append(action)

	def on_collect_context_menu(self, point):
		self.activeCollectAction = self.collectMenu.activeAction()
		self.collectContextMenu.exec_(self.collectMenu.mapToGlobal(point))

	def on_collect_item_clicked(self, action):
		try:
			index = self.collectActions.index(action)
		except ValueError:
			return
		self.send_collection(index)

	def send_collection(self, index):
		if len(self.collections) > index:
			form, raw = self.collections[index]
			if form == 'H':
				self.hexRadioButton.setChecked(True)
			elif form == 'E':
				self.extendRadioButton.setChecked(True)
			else:
				self.normalRadioButton.setChecked(True)

			self.sendPlainTextEdit.clear()
			self.sendPlainTextEdit.insertPlainText(raw)
			self.send()

	def remove_collection(self):
		try:
			index = self.collectActions.index(self.activeCollectAction)
		except ValueError:
			return

		del self.collectActions[index]
		del self.collections[index]

		self.collectMenu.clear()
		for item in self.collections:
			icon = QIcon(resource_path(ICON_LIB[item[0]]))
			action = self.collectMenu.addAction(icon, item[1])
			self.collectActions.append(action)

		save = open(PQCOM_DATA_FILE, 'wb')
		pickle.dump(self.collections, save)
		save.close()

	def remove_all_collections(self):
		self.collectMenu.clear()
		self.collections = []
		self.collectActions = []
		self.collectMenu.addAction('None')

		save = open(PQCOM_DATA_FILE, 'wb')
		save.close()
		pickle.dump(self.collections, save)

	def on_serial_failed(self):
		if self.sendButton.text().find('Stop') >= 0:
			self.repeater.stop()
			self.sendButton.setText('Start')
		self.serial_failed.emit()

	def handle_serial_error(self):
		if not self.is_last_error:
			self.oRecievedData.insertPlainText('<Error {}>\n'.format(serial.port))
			self.is_last_error = True
		self.actionRun.setChecked(False)
		if self.setupDialog.reconnect:
			if self._reconnect_timer_id < 0:
				self._reconnect_timer_id = self.startTimer(500)
		else:
			self.setup(True)

	def on_data_received(self):
		self.data_received.emit()

	def setup(self, warning=False):
		choice = self.setupDialog.show(warning)
		if choice == QDialog.Accepted:
			if self.actionRun.isChecked():
				self.actionRun.setChecked(False)
			self.actionRun.setChecked(True)

	def run(self, is_true):
		if is_true:
			port, vidpid, baud, bytebits, stopbits, parity = self.setupDialog.get()
			if port or vidpid:
				p = serial_bus.SerialParameters(baud, bytebits, stopbits, parity)
				serial.start(parameters=p, port_name=port,
					vid_pid=serial_bus.SerialParameters.get_vidpid_list(vidpid))
		else:
			if self.sendButton.text().find('Stop') >= 0:
				self.repeater.stop()
				self.sendButton.setText('Start')
			serial.join()
		self._show_port_status()

	def display(self):
		self.is_last_error = False
		data = serial.read()
		self.input_history += data  # store history data

		if self.actionHex.isChecked():
			data = translator.to_hex_prefix_string(data)

		self.oRecievedData.moveCursor(QTextCursor.End)
		self.oRecievedData.insertPlainText(data)
		self.oRecievedData.moveCursor(QTextCursor.End)

	def convert(self, is_true):
		if is_true:
			text = translator.to_hex_prefix_string(self.input_history)
		else:
			text = self.input_history

		self.oRecievedData.clear()
		self.oRecievedData.insertPlainText(text)
		self.oRecievedData.moveCursor(QTextCursor.End)

	def pin(self, is_true):
		if is_true:
			self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
		else:
			self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)

		self.show()

	def clear(self):
		self.oRecievedData.clear()
		self.input_history = ''

	def show_send(self, is_true):
		'Shows/hides send pane'
		if is_true:
			self.oSendPane.show()
		else:
			self.oSendPane.hide()

	def closeEvent(self, event):
		save = open(PQCOM_DATA_FILE, 'wb')
		pickle.dump(self.collections, save)
		save.close()

		event.accept()

	def timerEvent(self, event):
		# print('Reconnect timer. is Run: ' + str(self.actionRun.isChecked()))
		if self._reconnect_timer_id >= 0:
			self.killTimer(self._reconnect_timer_id)
			self._reconnect_timer_id = -1
		if not self.actionRun.isChecked():
			self.actionRun.setChecked(True)
		self._show_port_status()
		# end_s = self.windowTitle()[-1]
		# if end_s == '/':
		#     self.setWindowTitle(self.windowTitle()[:-1] + '-')
		# elif end_s == '-':
		#     self.setWindowTitle(self.windowTitle()[:-1] + '\\')
		# elif end_s == '\\':
		#     self.setWindowTitle(self.windowTitle()[:-1] + '|')
		# elif end_s == '|':
		#     self.setWindowTitle(self.windowTitle()[:-1] + '/')
		# else:
		#     self.setWindowTitle(self.windowTitle() + ' /')

class Repeater(object):
	def __init__(self):
		self.stop_event = threading.Event()
		self.period = 1
		self.thread = None

	def set_period(self, period):
		self.period = period

	def start(self, data, period):
		self.stop_event.clear()
		self.period = period
		self.thread = threading.Thread(target=self.repeat, args=(data,))
		self.thread.start()

	def stop(self):
		self.stop_event.set()

	def repeat(self, data):
		print('repeater thread is started')
		while not self.stop_event.is_set():
			serial.write(data)
			sleep(self.period)
		print('repeater thread exits')

def main():
	global serial

	DEFAULT_COM_BAUDRATE = 115200
	DEFAULT_COM_PARAMETERS = '8N1'

	def pase_args():
		parser = argparse.ArgumentParser(description='Simple serial port dump', formatter_class=argparse.RawTextHelpFormatter)
		parser.add_argument('-p', '--port', metavar='COM_PORT', help='serial port')
		parser.add_argument('-b', '--baudrate', metavar='BAUDRATE', default=DEFAULT_COM_BAUDRATE, type=int,
			help='serial port baudrate; default: '+str(DEFAULT_COM_BAUDRATE))
		parser.add_argument('--port-parameters', metavar='PARAMETERS', default=DEFAULT_COM_PARAMETERS,
			help='serial port parameters; default: '+str(DEFAULT_COM_PARAMETERS))
		# parser.add_argument('-v', action='count', default=0, help='verbose level: -v, -vv or -vvv (bytes); default: -v')
		parser.add_argument('-r', action='store_true', help='reconnect to serial port')
		parser.add_argument('-s', action='store_true', help='start and hide setup dialog')
		# parser.add_argument('--bytes', action='store_true', help='receive byte by byte')
		# parser.add_argument('--reconnect-delay', metavar='SEC', type=float, default=DEFAULT_COM_RECONNECT_DELAY,
		# 	help='reconnect delay, s; default: '+str(DEFAULT_COM_RECONNECT_DELAY))
		parser.add_argument('--vid-pid', metavar='VID:PID',
			help='search for USB: VendorID:ProductID[,VendorID:ProductID[...]]; example: 03eb:2404,03eb:6124')
		# parser.add_argument('--trace-error', action='store_true', help='show the errors trace; default: off')
		args = parser.parse_args()
		return args

	args = pase_args()

	app = QApplication(sys.argv)

	window = MainWindow(args=args)
	serial = serial_bus.SerialBus(window.on_data_received, window.on_serial_failed)

	window.show()
	if args.r:
		window.run(True)
	else:
		window.setup()
	app.exec_()
	serial.join()
	sys.exit(0)

if __name__ == '__main__':
	main()
