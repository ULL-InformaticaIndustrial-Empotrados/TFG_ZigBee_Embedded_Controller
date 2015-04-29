#!/usr/bin/env python
# -*- coding: UTF-8 -*-

#Copyright © 2015  Alberto Hamilton Castro
#
#Este programa es software libre: usted puede redistribuirlo y/o modificarlo conforme a los términos
# de la Licencia Pública General de GNU publicada por la Fundación para el Software Libre,
# ya sea la versión 3 de esta Licencia o (a su elección) cualquier versión posterior.
#Este programa se distribuye con el deseo de que le resulte útil, pero SIN GARANTÍAS DE NINGÚN TIPO;
# ni siquiera con las garantías implícitas de COMERCIABILIDAD o APTITUD PARA UN PROPÓSITO DETERMINADO.
#Para más información, consulte la Licencia Pública General de GNU.

import socket
import serial

class conexionTimeOut(Exception):
  pass

#################################################################################
class conexion_sock:
  '''Clase para gestionar la coneccion mediante socket.
  '''
  def __init__(self, bbb="bbb1", port=23004, timeout=2.0):
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.sock.connect((bbb,port))
    self.timeout = timeout
    #TODO debería poder especificase timeout. Según se lea de XBee a alto nivel
    self.sock.settimeout(self.timeout)  #ponemos timeout al pasado

  def read(self, nbytes=1):
    try:
      c = self.sock.recv(nbytes)
    except socket.timeout:
      raise conexionTimeOut
    return c

  def readline(self):
    msg = ''
    c = ''
    while c != '\r' :
      c = self.read(1)
      if c == '' :
        raise RuntimeError("socket connection broken")
      msg = msg + c
    return msg

  def write(self, msg):
    self.sock.sendall(msg)

  def setTimeout(self, timeout, setDef=0):
    '''Modifica el timeout
      y fija el por defecto def!=0
    '''
    self.sock.settimeout(timeout)
    if setDef:
      self.timeout = timeout

  def setTimeoutDefault(self):
    '''Restauara el timeout por defecto
    '''
    self.sock.settimeout(self.timeout)

  def close(self):
    self.sock.shutdown(socket.SHUT_RDWR)
    self.sock.close()

#################################################################################
class conexion_ser:
  '''Clase para gestionar la coneccion mediante fichero.
  '''
  def __init__(self, dev="/dev/ttyUSB0", speed=9600, timeout=2.0):
    self.ser = serial.Serial(dev, speed, timeout=timeout)
    self.timeout = timeout
    #TODO debería poder especificase timeout. Según se lea de XBee a alto nivel

  def read(self, nbytes=1):
    c = self.ser.read(nbytes)
    if c == '' :
      raise conexionTimeOut
    return c

  def readline(self):
    msg = ''
    c = ''
    while c != '\r' :
      c = self.read(1)
      msg = msg + c
    return msg

  def setTimeout(self, timeout, setDef=0):
    '''Modifica el timeout
      y fija el por defecto def!=0
    '''
    self.ser.timeout = timeout
    if setDef:
      self.timeout = timeout

  def setTimeoutDefault(self):
    '''Restauara el timeout por defecto
    '''
    self.ser.timeout = self.timeout

  def write(self, msg):
    self.ser.write(msg)
    self.ser.flush()

  def close(self):
    self.ser.close()

