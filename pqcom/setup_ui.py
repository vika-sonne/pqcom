# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'pqcom/pqcom/setup.ui'
#
# Created by: PyQt5 UI code generator 5.10.1
#
# Use customized ComboBox for port selection
# Changed by Yihui Xiong
#

from PyQt5 import QtCore, QtGui, QtWidgets
from pqcom.combobox import ComboBox

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(236, 218)
        self.verticalLayout = QtWidgets.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.formLayout = QtWidgets.QFormLayout()
        self.formLayout.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        self.formLayout.setObjectName("formLayout")
        self.label = QtWidgets.QLabel(Dialog)
        self.label.setObjectName("label")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label)
        self.portComboBox = ComboBox(Dialog)
        self.portComboBox.setEditable(True)
        self.portComboBox.setObjectName("portComboBox")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.portComboBox)
        self.label_2 = QtWidgets.QLabel(Dialog)
        self.label_2.setObjectName("label_2")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.label_2)
        self.baudComboBox = QtWidgets.QComboBox(Dialog)
        self.baudComboBox.setEditable(True)
        self.baudComboBox.setObjectName("baudComboBox")
        self.baudComboBox.addItem("")
        self.baudComboBox.addItem("")
        self.baudComboBox.addItem("")
        self.baudComboBox.addItem("")
        self.baudComboBox.addItem("")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.baudComboBox)
        self.label_3 = QtWidgets.QLabel(Dialog)
        self.label_3.setObjectName("label_3")
        self.formLayout.setWidget(3, QtWidgets.QFormLayout.LabelRole, self.label_3)
        self.stopbitComboBox = QtWidgets.QComboBox(Dialog)
        self.stopbitComboBox.setObjectName("stopbitComboBox")
        self.stopbitComboBox.addItem("")
        self.stopbitComboBox.addItem("")
        self.stopbitComboBox.addItem("")
        self.formLayout.setWidget(3, QtWidgets.QFormLayout.FieldRole, self.stopbitComboBox)
        self.dataComboBox = QtWidgets.QComboBox(Dialog)
        self.dataComboBox.setEditable(True)
        self.dataComboBox.setObjectName("dataComboBox")
        self.dataComboBox.addItem("")
        self.dataComboBox.addItem("")
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.FieldRole, self.dataComboBox)
        self.label_5 = QtWidgets.QLabel(Dialog)
        self.label_5.setObjectName("label_5")
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.LabelRole, self.label_5)
        self.parityComboBox = QtWidgets.QComboBox(Dialog)
        self.parityComboBox.setObjectName("parityComboBox")
        self.parityComboBox.addItem("")
        self.parityComboBox.addItem("")
        self.parityComboBox.addItem("")
        self.parityComboBox.addItem("")
        self.parityComboBox.addItem("")
        self.formLayout.setWidget(4, QtWidgets.QFormLayout.FieldRole, self.parityComboBox)
        self.label_4 = QtWidgets.QLabel(Dialog)
        self.label_4.setObjectName("label_4")
        self.formLayout.setWidget(4, QtWidgets.QFormLayout.LabelRole, self.label_4)
        self.checkBox = QtWidgets.QCheckBox(Dialog)
        self.checkBox.setObjectName("checkBox")
        self.formLayout.setWidget(5, QtWidgets.QFormLayout.FieldRole, self.checkBox)
        self.verticalLayout.addLayout(self.formLayout)
        self.buttonBox = QtWidgets.QDialogButtonBox(Dialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Open)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "pqcom"))
        self.label.setText(_translate("Dialog", "Port Name"))
        self.label_2.setText(_translate("Dialog", "Baud Rate"))
        self.baudComboBox.setItemText(0, _translate("Dialog", "115200"))
        self.baudComboBox.setItemText(1, _translate("Dialog", "57600"))
        self.baudComboBox.setItemText(2, _translate("Dialog", "38400"))
        self.baudComboBox.setItemText(3, _translate("Dialog", "19200"))
        self.baudComboBox.setItemText(4, _translate("Dialog", "9600"))
        self.label_3.setText(_translate("Dialog", "Stop Bits"))
        self.stopbitComboBox.setItemText(0, _translate("Dialog", "1"))
        self.stopbitComboBox.setItemText(1, _translate("Dialog", "1.5"))
        self.stopbitComboBox.setItemText(2, _translate("Dialog", "2"))
        self.dataComboBox.setItemText(0, _translate("Dialog", "8"))
        self.dataComboBox.setItemText(1, _translate("Dialog", "7"))
        self.label_5.setText(_translate("Dialog", "Data Bits"))
        self.parityComboBox.setItemText(0, _translate("Dialog", "None"))
        self.parityComboBox.setItemText(1, _translate("Dialog", "Even"))
        self.parityComboBox.setItemText(2, _translate("Dialog", "Odd"))
        self.parityComboBox.setItemText(3, _translate("Dialog", "Mark"))
        self.parityComboBox.setItemText(4, _translate("Dialog", "Space"))
        self.label_4.setText(_translate("Dialog", "Parity"))
        self.checkBox.setToolTip(_translate("Dialog", "Try to reopen port after disconnect"))
        self.checkBox.setText(_translate("Dialog", "Reopen"))

