import csrmesh
from bluepy import btle
import logging
from time import sleep

class Feit():
  def __init__(self, mac, pin):
    self.mac = mac
    self.password = csrmesh.network_key_feit(pin)
    self.device = None

  def connect(self):
    self.device = btle.Peripheral(self.mac, addrType=btle.ADDR_TYPE_PUBLIC)

    characteristics = self.device.getCharacteristics()

    for characteristic in characteristics:
      if characteristic.uuid == "c4edc000-9daf-11e3-8003-00025b000b00":
        self.lowhandle = characteristic.getHandle()
      elif characteristic.uuid == "c4edc000-9daf-11e3-8004-00025b000b00":
        self.highhandle = characteristic.getHandle()

  def disconnect(self):
      if self.device:
          self.device.disconnect()

  def set_brightness(self, brightness):
    packet = csrmesh.light_set_cmd(brightness,255,255,255)
    csrpacket = csrmesh.make_packet(self.password, csrmesh.random_seq(), packet)
    self.device.writeCharacteristic(self.lowhandle, csrpacket[0:20], withResponse=True)
    self.device.writeCharacteristic(self.highhandle, csrpacket[20:], withResponse=True)
