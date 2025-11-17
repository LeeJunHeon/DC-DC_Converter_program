# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'mainWindowfjZVrt.ui'
##
## Created by: Qt User Interface Compiler version 6.9.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QGroupBox, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QWidget)

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(1082, 661)
        self.powerOn_button = QPushButton(Form)
        self.powerOn_button.setObjectName(u"powerOn_button")
        self.powerOn_button.setGeometry(QRect(10, 410, 261, 63))
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.powerOn_button.sizePolicy().hasHeightForWidth())
        self.powerOn_button.setSizePolicy(sizePolicy)
        font = QFont()
        font.setPointSize(12)
        self.powerOn_button.setFont(font)
        self.powerOff_button = QPushButton(Form)
        self.powerOff_button.setObjectName(u"powerOff_button")
        self.powerOff_button.setGeometry(QRect(10, 470, 261, 61))
        sizePolicy.setHeightForWidth(self.powerOff_button.sizePolicy().hasHeightForWidth())
        self.powerOff_button.setSizePolicy(sizePolicy)
        self.powerOff_button.setFont(font)
        self.setValue_button = QPushButton(Form)
        self.setValue_button.setObjectName(u"setValue_button")
        self.setValue_button.setGeometry(QRect(10, 530, 259, 61))
        sizePolicy.setHeightForWidth(self.setValue_button.sizePolicy().hasHeightForWidth())
        self.setValue_button.setSizePolicy(sizePolicy)
        font1 = QFont()
        font1.setFamilies([u"\ub9d1\uc740 \uace0\ub515"])
        font1.setPointSize(12)
        self.setValue_button.setFont(font1)
        self.recodeStop_button = QPushButton(Form)
        self.recodeStop_button.setObjectName(u"recodeStop_button")
        self.recodeStop_button.setGeometry(QRect(140, 590, 131, 61))
        sizePolicy.setHeightForWidth(self.recodeStop_button.sizePolicy().hasHeightForWidth())
        self.recodeStop_button.setSizePolicy(sizePolicy)
        self.recodeStart_button = QPushButton(Form)
        self.recodeStart_button.setObjectName(u"recodeStart_button")
        self.recodeStart_button.setGeometry(QRect(10, 590, 131, 61))
        sizePolicy.setHeightForWidth(self.recodeStart_button.sizePolicy().hasHeightForWidth())
        self.recodeStart_button.setSizePolicy(sizePolicy)
        self.Graph_widget = QWidget(Form)
        self.Graph_widget.setObjectName(u"Graph_widget")
        self.Graph_widget.setGeometry(QRect(280, 20, 791, 631))
        self.groupBox = QGroupBox(Form)
        self.groupBox.setObjectName(u"groupBox")
        self.groupBox.setGeometry(QRect(10, 10, 261, 191))
        self.inputPower_label = QLabel(self.groupBox)
        self.inputPower_label.setObjectName(u"inputPower_label")
        self.inputPower_label.setGeometry(QRect(10, 30, 61, 21))
        self.inputPower_label.setFont(font)
        self.inputVoltage_label = QLabel(self.groupBox)
        self.inputVoltage_label.setObjectName(u"inputVoltage_label")
        self.inputVoltage_label.setGeometry(QRect(10, 90, 61, 21))
        self.inputVoltage_label.setFont(font)
        self.inputCurrent_label = QLabel(self.groupBox)
        self.inputCurrent_label.setObjectName(u"inputCurrent_label")
        self.inputCurrent_label.setGeometry(QRect(10, 150, 61, 21))
        self.inputCurrent_label.setFont(font)
        self.inputPower_edit = QLineEdit(self.groupBox)
        self.inputPower_edit.setObjectName(u"inputPower_edit")
        self.inputPower_edit.setGeometry(QRect(70, 20, 181, 41))
        self.inputVoltage_edit = QLineEdit(self.groupBox)
        self.inputVoltage_edit.setObjectName(u"inputVoltage_edit")
        self.inputVoltage_edit.setGeometry(QRect(70, 80, 181, 41))
        self.inputCurrent_edit = QLineEdit(self.groupBox)
        self.inputCurrent_edit.setObjectName(u"inputCurrent_edit")
        self.inputCurrent_edit.setGeometry(QRect(70, 140, 181, 41))
        self.groupBox_2 = QGroupBox(Form)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.groupBox_2.setGeometry(QRect(10, 210, 261, 191))
        self.outputPower_label = QLabel(self.groupBox_2)
        self.outputPower_label.setObjectName(u"outputPower_label")
        self.outputPower_label.setGeometry(QRect(10, 30, 61, 21))
        self.outputPower_label.setFont(font)
        self.outputVoltage_label = QLabel(self.groupBox_2)
        self.outputVoltage_label.setObjectName(u"outputVoltage_label")
        self.outputVoltage_label.setGeometry(QRect(10, 90, 61, 21))
        self.outputVoltage_label.setFont(font)
        self.outputCurrent_label = QLabel(self.groupBox_2)
        self.outputCurrent_label.setObjectName(u"outputCurrent_label")
        self.outputCurrent_label.setGeometry(QRect(10, 150, 61, 21))
        self.outputCurrent_label.setFont(font)
        self.outputPower_edit = QLineEdit(self.groupBox_2)
        self.outputPower_edit.setObjectName(u"outputPower_edit")
        self.outputPower_edit.setGeometry(QRect(70, 20, 181, 41))
        self.outputPower_edit.setReadOnly(True)
        self.outputVoltage_edit = QLineEdit(self.groupBox_2)
        self.outputVoltage_edit.setObjectName(u"outputVoltage_edit")
        self.outputVoltage_edit.setGeometry(QRect(70, 80, 181, 41))
        self.outputVoltage_edit.setReadOnly(True)
        self.outputCurrent_edit = QLineEdit(self.groupBox_2)
        self.outputCurrent_edit.setObjectName(u"outputCurrent_edit")
        self.outputCurrent_edit.setGeometry(QRect(70, 140, 181, 41))
        self.outputCurrent_edit.setReadOnly(True)

        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.powerOn_button.setText(QCoreApplication.translate("Form", u"\ucd9c\ub825 ON", None))
        self.powerOff_button.setText(QCoreApplication.translate("Form", u"\ucd9c\ub825 OFF", None))
        self.setValue_button.setText(QCoreApplication.translate("Form", u"\uc124\uc815 \uac12 \uc801\uc6a9", None))
        self.recodeStop_button.setText(QCoreApplication.translate("Form", u"\ub179\ud654 \uc911\uc9c0", None))
        self.recodeStart_button.setText(QCoreApplication.translate("Form", u"\ub179\ud654 \uc2dc\uc791", None))
        self.groupBox.setTitle(QCoreApplication.translate("Form", u"\uc785\ub825", None))
        self.inputPower_label.setText(QCoreApplication.translate("Form", u"\ud30c\uc6cc[W]", None))
        self.inputVoltage_label.setText(QCoreApplication.translate("Form", u"\uc804\uc555[V]", None))
        self.inputCurrent_label.setText(QCoreApplication.translate("Form", u"\uc804\ub958[A]", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("Form", u"\ucd9c\ub825", None))
        self.outputPower_label.setText(QCoreApplication.translate("Form", u"\ud30c\uc6cc[W]", None))
        self.outputVoltage_label.setText(QCoreApplication.translate("Form", u"\uc804\uc555[V]", None))
        self.outputCurrent_label.setText(QCoreApplication.translate("Form", u"\uc804\ub958[A]", None))
    # retranslateUi

