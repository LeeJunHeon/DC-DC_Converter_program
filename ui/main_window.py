# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'mainWindowDCrPyQ.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QSpacerItem, QSpinBox, QVBoxLayout,
    QWidget)

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(1082, 662)
        self.verticalLayout_3 = QVBoxLayout(Form)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.gridLayout_5 = QGridLayout()
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.Graph_widget = QWidget(Form)
        self.Graph_widget.setObjectName(u"Graph_widget")
        self.Graph_widget.setAutoFillBackground(True)

        self.verticalLayout_2.addWidget(self.Graph_widget)

        self.verticalLayout_2.setStretch(0, 20)

        self.gridLayout_5.addLayout(self.verticalLayout_2, 1, 1, 1, 1)

        self.gridLayout_4 = QGridLayout()
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.recodeStart_button = QPushButton(Form)
        self.recodeStart_button.setObjectName(u"recodeStart_button")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.recodeStart_button.sizePolicy().hasHeightForWidth())
        self.recodeStart_button.setSizePolicy(sizePolicy)
        self.recodeStart_button.setMaximumSize(QSize(16777215, 80))

        self.gridLayout_4.addWidget(self.recodeStart_button, 5, 0, 1, 1)

        self.recodeStop_button = QPushButton(Form)
        self.recodeStop_button.setObjectName(u"recodeStop_button")
        sizePolicy.setHeightForWidth(self.recodeStop_button.sizePolicy().hasHeightForWidth())
        self.recodeStop_button.setSizePolicy(sizePolicy)
        self.recodeStop_button.setMaximumSize(QSize(16777215, 80))

        self.gridLayout_4.addWidget(self.recodeStop_button, 5, 1, 1, 1)

        self.setValue_button = QPushButton(Form)
        self.setValue_button.setObjectName(u"setValue_button")
        sizePolicy.setHeightForWidth(self.setValue_button.sizePolicy().hasHeightForWidth())
        self.setValue_button.setSizePolicy(sizePolicy)
        self.setValue_button.setMaximumSize(QSize(16777215, 80))
        font = QFont()
        font.setFamilies([u"\ub9d1\uc740 \uace0\ub515"])
        font.setPointSize(11)
        self.setValue_button.setFont(font)

        self.gridLayout_4.addWidget(self.setValue_button, 4, 0, 1, 2)

        self.powerOff_button = QPushButton(Form)
        self.powerOff_button.setObjectName(u"powerOff_button")
        sizePolicy.setHeightForWidth(self.powerOff_button.sizePolicy().hasHeightForWidth())
        self.powerOff_button.setSizePolicy(sizePolicy)
        self.powerOff_button.setMaximumSize(QSize(16777215, 80))
        font1 = QFont()
        font1.setPointSize(11)
        self.powerOff_button.setFont(font1)

        self.gridLayout_4.addWidget(self.powerOff_button, 3, 0, 1, 2)

        self.powerOn_button = QPushButton(Form)
        self.powerOn_button.setObjectName(u"powerOn_button")
        sizePolicy.setHeightForWidth(self.powerOn_button.sizePolicy().hasHeightForWidth())
        self.powerOn_button.setSizePolicy(sizePolicy)
        self.powerOn_button.setMinimumSize(QSize(0, 0))
        self.powerOn_button.setMaximumSize(QSize(16777215, 80))
        self.powerOn_button.setFont(font1)

        self.gridLayout_4.addWidget(self.powerOn_button, 2, 0, 1, 2)

        self.groupBox_2 = QGroupBox(Form)
        self.groupBox_2.setObjectName(u"groupBox_2")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.groupBox_2.sizePolicy().hasHeightForWidth())
        self.groupBox_2.setSizePolicy(sizePolicy1)
        self.groupBox_2.setMaximumSize(QSize(16777215, 16777215))
        self.gridLayout_3 = QGridLayout(self.groupBox_2)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.outputPower_label = QLabel(self.groupBox_2)
        self.outputPower_label.setObjectName(u"outputPower_label")
        font2 = QFont()
        font2.setPointSize(12)
        self.outputPower_label.setFont(font2)

        self.gridLayout_3.addWidget(self.outputPower_label, 0, 0, 1, 1)

        self.outputVoltage_label = QLabel(self.groupBox_2)
        self.outputVoltage_label.setObjectName(u"outputVoltage_label")
        self.outputVoltage_label.setFont(font2)

        self.gridLayout_3.addWidget(self.outputVoltage_label, 1, 0, 1, 1)

        self.outputCurrent_label = QLabel(self.groupBox_2)
        self.outputCurrent_label.setObjectName(u"outputCurrent_label")
        self.outputCurrent_label.setFont(font2)

        self.gridLayout_3.addWidget(self.outputCurrent_label, 2, 0, 1, 1)

        self.outputPower_edit = QLineEdit(self.groupBox_2)
        self.outputPower_edit.setObjectName(u"outputPower_edit")

        self.gridLayout_3.addWidget(self.outputPower_edit, 0, 1, 1, 1)

        self.outputVoltage_edit = QLineEdit(self.groupBox_2)
        self.outputVoltage_edit.setObjectName(u"outputVoltage_edit")

        self.gridLayout_3.addWidget(self.outputVoltage_edit, 1, 1, 1, 1)

        self.outputCurrent_edit = QLineEdit(self.groupBox_2)
        self.outputCurrent_edit.setObjectName(u"outputCurrent_edit")

        self.gridLayout_3.addWidget(self.outputCurrent_edit, 2, 1, 1, 1)


        self.gridLayout_4.addWidget(self.groupBox_2, 1, 0, 1, 2)

        self.groupBox = QGroupBox(Form)
        self.groupBox.setObjectName(u"groupBox")
        sizePolicy1.setHeightForWidth(self.groupBox.sizePolicy().hasHeightForWidth())
        self.groupBox.setSizePolicy(sizePolicy1)
        self.groupBox.setMaximumSize(QSize(16777215, 16777215))
        self.groupBox.setBaseSize(QSize(0, 0))
        self.gridLayout_2 = QGridLayout(self.groupBox)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(-1, -1, 9, -1)
        self.inputPower_label = QLabel(self.groupBox)
        self.inputPower_label.setObjectName(u"inputPower_label")
        self.inputPower_label.setFont(font2)

        self.gridLayout_2.addWidget(self.inputPower_label, 0, 0, 1, 1)

        self.inputCurrent_label = QLabel(self.groupBox)
        self.inputCurrent_label.setObjectName(u"inputCurrent_label")
        self.inputCurrent_label.setFont(font2)

        self.gridLayout_2.addWidget(self.inputCurrent_label, 2, 0, 1, 1)

        self.inputVoltage_label = QLabel(self.groupBox)
        self.inputVoltage_label.setObjectName(u"inputVoltage_label")
        self.inputVoltage_label.setFont(font2)

        self.gridLayout_2.addWidget(self.inputVoltage_label, 1, 0, 1, 1)

        self.inputPower_edit = QLineEdit(self.groupBox)
        self.inputPower_edit.setObjectName(u"inputPower_edit")

        self.gridLayout_2.addWidget(self.inputPower_edit, 0, 1, 1, 1)

        self.inputVoltage_edit = QLineEdit(self.groupBox)
        self.inputVoltage_edit.setObjectName(u"inputVoltage_edit")

        self.gridLayout_2.addWidget(self.inputVoltage_edit, 1, 1, 1, 1)

        self.inputCurrent_edit = QLineEdit(self.groupBox)
        self.inputCurrent_edit.setObjectName(u"inputCurrent_edit")

        self.gridLayout_2.addWidget(self.inputCurrent_edit, 2, 1, 1, 1)


        self.gridLayout_4.addWidget(self.groupBox, 0, 0, 1, 2)


        self.gridLayout_5.addLayout(self.gridLayout_4, 1, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label = QLabel(Form)
        self.label.setObjectName(u"label")

        self.horizontalLayout.addWidget(self.label)

        self.comPort_comboBox = QComboBox(Form)
        self.comPort_comboBox.setObjectName(u"comPort_comboBox")

        self.horizontalLayout.addWidget(self.comPort_comboBox)

        self.label_2 = QLabel(Form)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout.addWidget(self.label_2)

        self.slaveID_spinBox = QSpinBox(Form)
        self.slaveID_spinBox.setObjectName(u"slaveID_spinBox")

        self.horizontalLayout.addWidget(self.slaveID_spinBox)

        self.connect_button = QPushButton(Form)
        self.connect_button.setObjectName(u"connect_button")

        self.horizontalLayout.addWidget(self.connect_button)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.deviceError_button = QPushButton(Form)
        self.deviceError_button.setObjectName(u"deviceError_button")

        self.horizontalLayout.addWidget(self.deviceError_button)


        self.gridLayout_5.addLayout(self.horizontalLayout, 0, 0, 1, 2)

        self.gridLayout_5.setColumnStretch(0, 3)
        self.gridLayout_5.setColumnStretch(1, 9)

        self.verticalLayout_3.addLayout(self.gridLayout_5)


        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.recodeStart_button.setText(QCoreApplication.translate("Form", u"\ub179\ud654 \uc2dc\uc791", None))
        self.recodeStop_button.setText(QCoreApplication.translate("Form", u"\ub179\ud654 \uc911\uc9c0", None))
        self.setValue_button.setText(QCoreApplication.translate("Form", u"\uc124\uc815 \uac12 \uc801\uc6a9", None))
        self.powerOff_button.setText(QCoreApplication.translate("Form", u"\ucd9c\ub825 OFF", None))
        self.powerOn_button.setText(QCoreApplication.translate("Form", u"\ucd9c\ub825 ON", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("Form", u"\ucd9c\ub825", None))
        self.outputPower_label.setText(QCoreApplication.translate("Form", u"\ud30c\uc6cc[W]", None))
        self.outputVoltage_label.setText(QCoreApplication.translate("Form", u"\uc804\uc555[V]", None))
        self.outputCurrent_label.setText(QCoreApplication.translate("Form", u"\uc804\ub958[A]", None))
        self.groupBox.setTitle(QCoreApplication.translate("Form", u"\uc785\ub825", None))
        self.inputPower_label.setText(QCoreApplication.translate("Form", u"\ud30c\uc6cc[W]", None))
        self.inputCurrent_label.setText(QCoreApplication.translate("Form", u"\uc804\ub958[A]", None))
        self.inputVoltage_label.setText(QCoreApplication.translate("Form", u"\uc804\uc555[V]", None))
        self.label.setText(QCoreApplication.translate("Form", u"COM \ud3ec\ud2b8", None))
        self.label_2.setText(QCoreApplication.translate("Form", u"Slave ID", None))
        self.connect_button.setText(QCoreApplication.translate("Form", u"\uc5f0\uacb0", None))
        self.deviceError_button.setText(QCoreApplication.translate("Form", u"\uc7a5\ube44 \uc54c\ub9bc/\uc624\ub958", None))
    # retranslateUi

