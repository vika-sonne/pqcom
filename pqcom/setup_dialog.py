
from typing import Optional, Tuple
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog
from pqcom import serial_bus
from pqcom import setup_dialog_ui


class SetupDialog(QDialog, setup_dialog_ui.Ui_Dialog):
	def __init__(self, parent=None):
		super(SetupDialog, self).__init__(parent)
		self.setupUi(self)
		self.setWindowFlags(self.windowFlags() ^ Qt.WindowContextHelpButtonHint)

		self.ports = []
		self.refresh()

		self.portComboBox.clicked.connect(self.refresh)

	def show(self, warning=False):
		if warning:
			self.portComboBox.setStyleSheet('QComboBox {color: red;}')
		else:
			self.refresh()

		return self.exec_()

	def refresh(self):
		self.portComboBox.setStyleSheet('QComboBox {color: black;}')
		ports = serial_bus.get_ports()
		if ports != self.ports:
			self.ports = ports
			self.portComboBox.clear()
			for port in ports:
				self.portComboBox.addItem(port)

	def get(self) -> Tuple[Optional[str], Optional[str], int, int, str, str]:
		if self.oRadioName.isChecked():
			# port name
			port = str(self.portComboBox.currentText())
			vidpid = None
		else:
			# USB VID:PID list
			vidpid = str(self.oVidpid.text())
			port = None
		baud = int(self.oBaud.currentText())
		bytebits = int(self.oBytebits.currentText())
		stopbits = str(self.oStopbits.currentText())
		parity = str(self.oParity.currentText())[0]

		return port, vidpid, baud, bytebits, stopbits, parity

	def set_baud(self, baud: int):
		i = self.oBaud.findText(str(baud))
		if i < 0:
			i = self.oBaud.count()
			self.oBaud.addItem(str(baud))
		self.oBaud.setCurrentIndex(i)

	def set_bytebits(self, bytebits: int):
		i = self.oBytebits.findText(str(bytebits))
		if i >= 0:
			self.oBytebits.setCurrentIndex(i)

	def set_parity(self, parity: str):
		i = self.oParity.findText(parity, Qt.MatchStartsWith)
		if i >= 0:
			self.oParity.setCurrentIndex(i)

	def set_stopbits(self, stopbits: str):
		i = self.oStopbits.findText(stopbits)
		if i >= 0:
			self.oStopbits.setCurrentIndex(i)

	def set_reconnect(self, reconnect=True):
		self.oReconnect.setChecked(reconnect)

	def set_vidpid(self, vidpid: str):
		self.oVidpid.setText(vidpid)
		self.oRadioVIDPID.setChecked(True)

	@property
	def reconnect(self):
		return self.oReconnect.isChecked()
