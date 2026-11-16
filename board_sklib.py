from collections import defaultdict
from skidl import Pin, Part, Alias, SchLib, SKIDL, TEMPLATE

from skidl.pin import pin_types

SKIDL_lib_version = '0.0.1'

board = SchLib(tool=SKIDL).add_parts(*[
        Part(**{ 'name':'USB_C_HRO_TYPE-C-31-M-12', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'USB_C_HRO_TYPE-C-31-M-12'}), 'ref_prefix':'J', 'fplist':['hwlab:USB_C_Receptacle_HRO_TYPE-C-31-M-12'], 'footprint':'hwlab:USB_C_Receptacle_HRO_TYPE-C-31-M-12', 'keywords':'usb universal serial bus type-C USB2.0', 'description':'USB 2.0-only 16P Type-C Receptacle connector', 'datasheet':'https://www.usb.org/sites/default/files/documents/usb_type-c.zip', 'pins':[
            Pin(num='A1',name='GND',func=pin_types.PASSIVE,unit=1),
            Pin(num='A4',name='VBUS',func=pin_types.PASSIVE,unit=1),
            Pin(num='A5',name='CC1',func=pin_types.BIDIR,unit=1),
            Pin(num='A6',name='D+',func=pin_types.BIDIR,unit=1),
            Pin(num='A7',name='D-',func=pin_types.BIDIR,unit=1),
            Pin(num='A8',name='SBU1',func=pin_types.BIDIR,unit=1),
            Pin(num='A9',name='VBUS',func=pin_types.PASSIVE,unit=1),
            Pin(num='A12',name='GND',func=pin_types.PASSIVE,unit=1),
            Pin(num='B1',name='GND',func=pin_types.PASSIVE,unit=1),
            Pin(num='B4',name='VBUS',func=pin_types.PASSIVE,unit=1),
            Pin(num='B5',name='CC2',func=pin_types.BIDIR,unit=1),
            Pin(num='B6',name='D+',func=pin_types.BIDIR,unit=1),
            Pin(num='B7',name='D-',func=pin_types.BIDIR,unit=1),
            Pin(num='B8',name='SBU2',func=pin_types.BIDIR,unit=1),
            Pin(num='B9',name='VBUS',func=pin_types.PASSIVE,unit=1),
            Pin(num='B12',name='GND',func=pin_types.PASSIVE,unit=1),
            Pin(num='SH',name='SHIELD',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'R_5k1_0402', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'R_5k1_0402'}), 'ref_prefix':'R', 'fplist':['hwlab:R_0402_1005Metric'], 'footprint':'hwlab:R_0402_1005Metric', 'keywords':'R res resistor', 'description':'Resistor', 'datasheet':'', 'pins':[
            Pin(num='1',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'AMS1117-3.3', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'AMS1117-3.3'}), 'ref_prefix':'U', 'fplist':['hwlab:SOT-223-3_TabPin2'], 'footprint':'hwlab:SOT-223-3_TabPin2', 'keywords':'linear regulator ldo fixed positive', 'description':'1A Low Dropout regulator, positive, 3.3V fixed output, SOT-223', 'datasheet':'http://www.advanced-monolithic.com/pdf/ds1117.pdf', 'pins':[
            Pin(num='1',name='GND',func=pin_types.PWRIN,unit=1),
            Pin(num='2',name='VO',func=pin_types.PWROUT,unit=1),
            Pin(num='3',name='VI',func=pin_types.PWRIN,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'C_10u_0603', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'C_10u_0603'}), 'ref_prefix':'C', 'fplist':['hwlab:C_0603_1608Metric'], 'footprint':'hwlab:C_0603_1608Metric', 'keywords':'cap capacitor', 'description':'Unpolarized capacitor', 'datasheet':'', 'pins':[
            Pin(num='1',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'C_22u_0805', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'C_22u_0805'}), 'ref_prefix':'C', 'fplist':['hwlab:C_0805_2012Metric'], 'footprint':'hwlab:C_0805_2012Metric', 'keywords':'cap capacitor', 'description':'Unpolarized capacitor', 'datasheet':'', 'pins':[
            Pin(num='1',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'ESP32-S3-WROOM-1-N8', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'ESP32-S3-WROOM-1-N8'}), 'ref_prefix':'U', 'fplist':['hwlab:ESP32-S3-WROOM-1'], 'footprint':'hwlab:ESP32-S3-WROOM-1', 'keywords':'RF Radio BT ESP ESP32-S3 Espressif onboard PCB antenna', 'description':'RF Module, ESP32-S3 SoC, Wi-Fi 802.11b/g/n, Bluetooth, BLE, 32-bit, 3.3V, onboard antenna, SMD', 'datasheet':'https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf', 'pins':[
            Pin(num='1',name='GND',func=pin_types.PWRIN,unit=1),
            Pin(num='2',name='3V3',func=pin_types.PWRIN,unit=1),
            Pin(num='3',name='EN',func=pin_types.INPUT,unit=1),
            Pin(num='4',name='IO4',func=pin_types.BIDIR,unit=1),
            Pin(num='5',name='IO5',func=pin_types.BIDIR,unit=1),
            Pin(num='6',name='IO6',func=pin_types.BIDIR,unit=1),
            Pin(num='7',name='IO7',func=pin_types.BIDIR,unit=1),
            Pin(num='8',name='IO15',func=pin_types.BIDIR,unit=1),
            Pin(num='9',name='IO16',func=pin_types.BIDIR,unit=1),
            Pin(num='10',name='IO17',func=pin_types.BIDIR,unit=1),
            Pin(num='11',name='IO18',func=pin_types.BIDIR,unit=1),
            Pin(num='12',name='IO8',func=pin_types.BIDIR,unit=1),
            Pin(num='13',name='USB_D-',func=pin_types.BIDIR,unit=1),
            Pin(num='14',name='USB_D+',func=pin_types.BIDIR,unit=1),
            Pin(num='15',name='IO3',func=pin_types.BIDIR,unit=1),
            Pin(num='16',name='IO46',func=pin_types.BIDIR,unit=1),
            Pin(num='17',name='IO9',func=pin_types.BIDIR,unit=1),
            Pin(num='18',name='IO10',func=pin_types.BIDIR,unit=1),
            Pin(num='19',name='IO11',func=pin_types.BIDIR,unit=1),
            Pin(num='20',name='IO12',func=pin_types.BIDIR,unit=1),
            Pin(num='21',name='IO13',func=pin_types.BIDIR,unit=1),
            Pin(num='22',name='IO14',func=pin_types.BIDIR,unit=1),
            Pin(num='23',name='IO21',func=pin_types.BIDIR,unit=1),
            Pin(num='24',name='IO47',func=pin_types.BIDIR,unit=1),
            Pin(num='25',name='IO48',func=pin_types.BIDIR,unit=1),
            Pin(num='26',name='IO45',func=pin_types.BIDIR,unit=1),
            Pin(num='27',name='IO0',func=pin_types.BIDIR,unit=1),
            Pin(num='28',name='IO35',func=pin_types.BIDIR,unit=1),
            Pin(num='29',name='IO36',func=pin_types.BIDIR,unit=1),
            Pin(num='30',name='IO37',func=pin_types.BIDIR,unit=1),
            Pin(num='31',name='IO38',func=pin_types.BIDIR,unit=1),
            Pin(num='32',name='IO39',func=pin_types.BIDIR,unit=1),
            Pin(num='33',name='IO40',func=pin_types.BIDIR,unit=1),
            Pin(num='34',name='IO41',func=pin_types.BIDIR,unit=1),
            Pin(num='35',name='IO42',func=pin_types.BIDIR,unit=1),
            Pin(num='36',name='RXD0',func=pin_types.BIDIR,unit=1),
            Pin(num='37',name='TXD0',func=pin_types.BIDIR,unit=1),
            Pin(num='38',name='IO2',func=pin_types.BIDIR,unit=1),
            Pin(num='39',name='IO1',func=pin_types.BIDIR,unit=1),
            Pin(num='40',name='GND',func=pin_types.PASSIVE,unit=1),
            Pin(num='41',name='GND',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'C_100n_0402', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'C_100n_0402'}), 'ref_prefix':'C', 'fplist':['hwlab:C_0402_1005Metric'], 'footprint':'hwlab:C_0402_1005Metric', 'keywords':'cap capacitor', 'description':'Unpolarized capacitor', 'datasheet':'', 'pins':[
            Pin(num='1',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'R_10k_0402', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'R_10k_0402'}), 'ref_prefix':'R', 'fplist':['hwlab:R_0402_1005Metric'], 'footprint':'hwlab:R_0402_1005Metric', 'keywords':'R res resistor', 'description':'Resistor', 'datasheet':'', 'pins':[
            Pin(num='1',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'C_1u_0402', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'C_1u_0402'}), 'ref_prefix':'C', 'fplist':['hwlab:C_0402_1005Metric'], 'footprint':'hwlab:C_0402_1005Metric', 'keywords':'cap capacitor', 'description':'Unpolarized capacitor', 'datasheet':'', 'pins':[
            Pin(num='1',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'SW_TS-1187A-B-A-B', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'SW_TS-1187A-B-A-B'}), 'ref_prefix':'SW', 'fplist':['hwlab:SW_Push_1P1T_XKB_TS-1187A'], 'footprint':'hwlab:SW_Push_1P1T_XKB_TS-1187A', 'keywords':'switch normally-open pushbutton push-button', 'description':'Push button switch, generic, two pins', 'datasheet':'', 'pins':[
            Pin(num='1',name='1',func=pin_types.PASSIVE),
            Pin(num='2',name='2',func=pin_types.PASSIVE)], 'unit_defs':[] }),
        Part(**{ 'name':'R_1k_0402', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'R_1k_0402'}), 'ref_prefix':'R', 'fplist':['hwlab:R_0402_1005Metric'], 'footprint':'hwlab:R_0402_1005Metric', 'keywords':'R res resistor', 'description':'Resistor', 'datasheet':'', 'pins':[
            Pin(num='1',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'LED_Green_0805', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'LED_Green_0805'}), 'ref_prefix':'D', 'fplist':['hwlab:LED_0805_2012Metric'], 'footprint':'hwlab:LED_0805_2012Metric', 'keywords':'LED diode', 'description':'Light emitting diode', 'datasheet':'', 'pins':[
            Pin(num='1',name='K',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',name='A',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'LSM6DSOTR', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'LSM6DSOTR'}), 'ref_prefix':'U', 'fplist':['hwlab:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y'], 'footprint':'hwlab:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y', 'keywords':'Accelerometer Gyroscope MEMS', 'description':'iNEMO 6DoF IMU, accelerometer + gyroscope, I2C/SPI/I3C, 1.71-3.6V, LGA-14L', 'datasheet':'https://www.st.com/resource/en/datasheet/lsm6dso.pdf', 'pins':[
            Pin(num='1',name='SDO/SA0',func=pin_types.BIDIR,unit=1),
            Pin(num='2',name='SDX',func=pin_types.BIDIR,unit=1),
            Pin(num='3',name='SCX',func=pin_types.INPUT,unit=1),
            Pin(num='4',name='INT1',func=pin_types.OUTPUT,unit=1),
            Pin(num='5',name='VDDIO',func=pin_types.PWRIN,unit=1),
            Pin(num='6',name='GND',func=pin_types.PWRIN,unit=1),
            Pin(num='7',name='GND',func=pin_types.PASSIVE,unit=1),
            Pin(num='8',name='VDD',func=pin_types.PWRIN,unit=1),
            Pin(num='9',name='INT2',func=pin_types.OUTPUT,unit=1),
            Pin(num='10',name='OCS_Aux',func=pin_types.NOCONNECT,unit=1),
            Pin(num='11',name='SDO_Aux',func=pin_types.NOCONNECT,unit=1),
            Pin(num='12',name='CS',func=pin_types.INPUT,unit=1),
            Pin(num='13',name='SCL',func=pin_types.INPUT,unit=1),
            Pin(num='14',name='SDA',func=pin_types.BIDIR,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'R_4k7_0402', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'R_4k7_0402'}), 'ref_prefix':'R', 'fplist':['hwlab:R_0402_1005Metric'], 'footprint':'hwlab:R_0402_1005Metric', 'keywords':'R res resistor', 'description':'Resistor', 'datasheet':'', 'pins':[
            Pin(num='1',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'JST_SH_SM04B-SRSS-TB', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'JST_SH_SM04B-SRSS-TB'}), 'ref_prefix':'J', 'fplist':['hwlab:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal'], 'footprint':'hwlab:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal', 'keywords':'connector', 'description':'Generic connectable mounting pin connector, single row, 01x04, script generated (kicad-library-utils/schlib/autogen/connector/)', 'datasheet':'', 'pins':[
            Pin(num='1',name='Pin_1',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',name='Pin_2',func=pin_types.PASSIVE,unit=1),
            Pin(num='3',name='Pin_3',func=pin_types.PASSIVE,unit=1),
            Pin(num='4',name='Pin_4',func=pin_types.PASSIVE,unit=1),
            Pin(num='MP',name='MountPin',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] })])