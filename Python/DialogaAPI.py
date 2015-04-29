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

from Conexiones import *
import threading
import time
from datetime import datetime
import logging

############################################################################33
## Funciones axiliares

def toInt( charList ):
  '''Dado string considera como bytes y devuelve intero correspondiente '''
  tot = 0
  for ca in charList:
    tot = tot*256 + ord(ca)
  return tot

def num2bytes(valor, numbytes = -1):
  '''Dado un entero lo descompone en sus bytes y lo devuelve como strig '''
  vecbyte = ''
  if ( numbytes<0 and valor<0 ): return vecbyte
  if ( numbytes<0 and valor==0 ): return '\x00' #Por si el valor es inicialmente 0
  bytea = 0
  while ( ( (numbytes>0) and (bytea<numbytes) ) or ( (numbytes<0) and (valor>0) ) ):
    bytea += 1
    vecbyte = chr(valor & 0xFF) + vecbyte
    valor >>= 8
  return vecbyte

def vecByte2strig( frame ):
  '''Dada una cadena de bytes devuelve su representación como hexadecimales '''
  resp = "[ ({})".format( len(frame))
  for ca in frame:
    resp += " 0x{:02X}".format( ord(ca) )
  resp += " ]"
  return resp

def hexStr2Int( hexStr ):
  hexStr = hexStr.upper().strip()
  value = 0
  for ca in hexStr:
    if ca>='0' and ca<='9': va = ord( ca ) - ord( '0' )  #Es digito
    elif ca>='A' and ca<='F': va = ord( ca ) - ord( 'A' ) +10   #Es letra
    else:
      logging.warning( "Caracter '{}' no es digito hexadecimal.".format( ca ) )
      return -1
    value = value*16 + va
  return value

def miraMas( comando ):
  '''Para tratar los comando AT,
  si aparece + se supone que resto es un número decimal, lo cambia por hexadecimal
  '''
  #m = re.search(r"([^+]*)+(.*)", comando)
  m = comando.split("+",1)
  if len(m)==1 : #NO aparece el +
    return comando
  return m[0] + hex( int(m[1]) )[2:]

#################################################################################
class dialogoAPI(threading.Thread):
  '''Clase para gestionar el dialgo mediante API,
    el envio de comandos y respuestas a XBee
    Debe recibir una conexion inicializada
  '''
  def __init__(self, c):
    threading.Thread.__init__(self)
    self.conexion = c
    self.frameIdAT = 0
    self.corriendo = False
    #Si las direcciones de los mensajes se una nombre o direccion completa
    self.modoBreveRecepcion = False
    #Atributo diccionario con las direcciones y nombres de los nodos
    #  la clave primaria es el número serial del nodo (el único que no cambia)
    self.tablaDirecciones = {}
    # Posibilidades de 'Receive Options'
    self.recOpt = ['ERR', 'Ack', 'Broac']
    self.DevicesType = ['Coord', 'Router', 'End']


  def setConexion(self, c):
    self.conexion = c

  def __actualizaTablaDir(self, dir64, dir16=-1, nombre=''):
    ''' Actualiza la tabla de direcciones con los datos pasados
    '''
    logging.debug( "0x{:016X}:(0x{:04X}, '{}')".format(dir64, dir16, nombre) )
    if len(nombre)==0 and (dir64 in self.tablaDirecciones):
      nombre = self.tablaDirecciones[ dir64 ][1] #Cogemos nombre anterior
      logging.debug( "cogemos nombre '{}'".format( nombre ) )
    if dir16<0 and (dir64 in self.tablaDirecciones):
      dir16 = self.tablaDirecciones[ dir64 ][0] #Cogemos dir16 anterior
      logging.debug( "cogemos dir16 0x{:04X}".format( dir16 ) )
    self.tablaDirecciones[ dir64 ] = (dir16, nombre)

  def tablaDir2Str(self):
    msg = "TablaDirecciones: {"
    for k, v in self.tablaDirecciones.iteritems():
      msg += " 0x{:016X}:(0x{:04X}, '{}')".format(k, v[0], v[1])
    msg += " }"
    return msg

  def dir64toMy( self, dir64 ):
    my = -1
    if dir64 in self.tablaDirecciones:
      my = self.tablaDirecciones[ dir64 ][ 0 ]
    return my

  def dir16toSerial( self, dir16 ):
    serial = -1
    for k, v in self.tablaDirecciones.iteritems():
      if v[0] == dir16:
        serial = k
    return serial

  def nombretoSerial( self, nombre ):
    serial = -1
    for k, v in self.tablaDirecciones.iteritems():
      if v[1] == nombre:
        serial = k
    return serial

  def setModoBreveRecepcion(self, estado):
    self.modoBreveRecepcion = estado

  @staticmethod
  def compruebaCRC( frame):
    '''Suponiendo que frame es un paquete API válido
      comprueba el CRC
    '''
    lon = ord(frame[1])*256 + ord(frame[2])
    util = frame[3 : 3+lon+1]
    crc = reduce( lambda x,y: (x + ord(y)) & 0xFF, util, 0)
    return (crc == 0xFF)

  def enviaPaquete(self, paquete):
    frame = '\x7E'
    lenPq = len(paquete)
    frame += chr( (lenPq & 0xFF00) >> 8 )
    frame += chr( (lenPq & 0xFF) )
    frame += paquete
    crc = 0xff - reduce( lambda x,y: (x + ord(y)) & 0xFF, paquete, 0)
    frame += chr( crc )
    logging.debug( "Enviamos frame: {} CRC {}".format(
        vecByte2strig( frame  ), 'OK' if dialogoAPI.compruebaCRC( frame ) else 'FAIL' ) )
    self.conexion.write(frame)

  def recibePaquete(self):
    if self.corriendo:
      logging.warning( "Está el thread corriendo, NO invocar directamente" )
      return []
    return self.__recPaquete()

  def __recPaquete(self):
    frame = ''
    c = ''
    while c != '\x7e':
      c = self.conexion.read()
      if c != '\x7e':
        logging.warning( "Recibido {:} (0x{:02X}) fuera de paquete".format(c, ord(c)) )
    frame = c
    #Ya tenemos la cabecera, procedemos a leer logitud
    c = self.conexion.read(1)
    frame += c
    lon = ord( c )*256
    c = self.conexion.read(1)
    frame += c
    lon += ord( c )
    #Tenemos longitud, procedemos a leer paquete
    for i in range(lon):
      c = self.conexion.read(1)
      frame += c
    #Leemos byte de CRC
    c = self.conexion.read(1)
    frame += c
    logging.debug( "Frame recibido: {}".format( vecByte2strig(frame) ) )
    if not dialogoAPI.compruebaCRC( frame ):
      logging.warning( "Mensaje recibido tienen CRC incorrecto" )
    return frame[3:-1]

  def comandoATlocal(self, cmdori):
    '''Método que envia cmd AT a través del API usando API 0x08
    y devuelve tupla con mensaje enviado y respuesta.
      los AT \r se añaden y borran de manera transparente
    '''
    #montamos el paquete
    self.frameIdAT = (self.frameIdAT + 1) & 0xFF #generamos nuevo frame ID
    paquete = '\x08' + chr(self.frameIdAT)
    parteAT = dialogoAPI.__parteAT( cmdori )
    if len( parteAT ) == 0:
      #Ha habido problema
      return -1
    paquete += parteAT
    self.enviaPaquete( paquete )
    logging.debug( ">{}< Paquete para enviar: {}".format(
        cmdori, vecByte2strig( paquete ) ) )
    return self.frameIdAT

  @staticmethod
  def __parteAT( cmdori):
    #Tratamos la parte del comando
    cmd = miraMas( cmdori ) #parámetros enteros con +
    cmd = cmd.upper().strip()  #Pasamos a mayúsculas
    if cmd[-1] == '\r': #quitamos \r final si la hay
      cmd = cmd[0:-1]
    if cmd[0:2] == 'AT':
      cmd = cmd[2:]  #Quitamos el at inicial
    valor = cmd[2:]
    cmd = cmd[0:2]
    paquete = cmd
    if len( valor )>0: #hay un valor que enviar
      if (cmd == 'NI') or (cmd == 'DN') or (cmd == 'ND'):
        #consideramos cadena de caracteres
        paquete += valor #Añadimos directamente
      else: #Es numero hexadecimal
        value = hexStr2Int( valor )
        if value<0:
          logging.error( "Problema en la conversión hexadecimal. NO ENVIAMOS '{}'".format(ca, cmdori) )
          return ''
        paquete += num2bytes( value )
    return paquete

  def comandoATremoto(self, dest64, dest16, cmdori, inmediato=True):
    '''Método que envia cmd AT remoto a través del API usando API 0x17
    y devuelve tupla con mensaje enviado y respuesta.
    los AT \r se añaden y borran de manera transparente
    '''
    #montamos el paquete
    if (dest64<0) and (dest16<0):
      logging.error( "ambas direcciones no pueden ser desconocidas" )
      return -1
    if dest16<0:
      dest16 = self.dir64toMy( dest64 )
      if dest16<0: #no estaba en la tabla
        dest16 = 0xFFFE
    if dest64<0:
      dest64 = self.dir16toSerial( dest16 )
      if dest64<0: #No estaba en la tabla
        logging.error( "dirección 64 desconocida. No podemos enviar" )
        return -1

    #Comprobamos el comando AT
    parteAT = dialogoAPI.__parteAT( cmdori )
    if len( parteAT ) == 0:
      #Ha habido problema
      return -1
    #Todo correcto, vamos montando el paquete
    self.frameIdAT = (self.frameIdAT + 1) & 0xFF #generamos nuevo frame ID
    paquete = '\x17' + chr(self.frameIdAT)
    paquete += num2bytes( dest64, 8)
    paquete += num2bytes( dest16, 2)
    paquete += '\x02' if inmediato else '\x00'
    paquete += parteAT
    logging.debug( ">{}< Paquete para enviar: {}".format(
        cmdori,  vecByte2strig( paquete )) )
    self.enviaPaquete( paquete )
    return self.frameIdAT


  def run(self):
    ''' Método para lanzar el hilo de ejecución '''
    self.corriendo = True
    self.conexion.setTimeout(1)
    self.terminar = False
    while not self.terminar:
      try:
        paquete = self.__recPaquete( )
        self.reparteMensaje( paquete, self.modoBreveRecepcion )
      except conexionTimeOut:
        pass #no hacemos nada

  def finish(self):
    self.terminar = True

  def reparteMensaje(self, paquete, breve=False ):
    if len( paquete ) == 0:
      return
    logging.debug( "Repartiendo {}".format( vecByte2strig( paquete ) ) )
    apiId = ord( paquete[0] )
    if apiId == 0x88:
      self.respuestaATlocal(paquete,breve)
    elif apiId == 0x8A:
      self.modemStatus(paquete,breve)
    elif apiId == 0x97:
      self.respuestaATremota(paquete,breve)
    elif apiId == 0x91:
      self.recepcionRemota(paquete,breve)
    elif apiId == 0x92:
      self.recepcionIORemota(paquete,breve)
    elif apiId == 0x95:
      self.recepcionIndentifInd(paquete,breve)
    elif apiId == 0x90:
      self.recepcionDatos(paquete,breve)
    else:
      logging.warning( "Tipo 0x{:02X} no soportado {}".format(
        apiId, vecByte2strig( paquete ) ) )

  def respuestaATlocal(self, paquete, breve=False ):
    if ord(paquete[0]) != 0x88:
      logging.error( "el paquete no es 0x88" )
      return
    if len( paquete ) < 5:
      logging.error( "paquete 0x88 no tienen tamaño necesario {}<5 {}".format(
        len(paquete), vecByte2strig( paquete ) ) )
      return
    frameId = ord(paquete[1])
    (atCmd, estado, valor) = self.__respuestaAT( paquete[2:], breve=breve )
    #Sacamos la información del paquete
    logging.info( "Respuesta AT local: Id={}, Comando={}, Estado={} {}".format(
      frameId, atCmd, estado, valor) )

  def respuestaATremota(self, paquete, breve=False):
    if ord(paquete[0]) != 0x97:
      logging.error( "el paquete no es 0x97" )
      return
    if len( paquete ) < 15:
      logging.error( "paquete 0x97 no tienen tamaño necesario {}<15: {}".format(
        len(paquete),  vecByte2strig( paquete )) )
      return
    ind = 1
    frameId = ord(paquete[ind]); ind +=1
    dir64 = toInt( paquete[ind:ind+8] ); ind += 8
    dir16 = toInt( paquete[ind:ind+2] ); ind += 2
    self.__actualizaTablaDir(dir64,dir16)
    (atCmd, estado, valor) = self.__respuestaAT( paquete[ind:], dir64, breve )
    #Sacamos la información del paquete
    if breve and dir64 in self.tablaDirecciones :
      direccion = "'{}'".format( self.tablaDirecciones[ dir64 ][ 1 ] )
    else:
      direccion = "0x{:016X} (0x{:04X})".format( dir64, dir16 )
    logging.info( "Respuesta AT remota: Id={}, de {} Comando={}, Estado={} {}".format(
        frameId, direccion, atCmd, estado, valor) )

  def __respuestaAT(self, paquete, dir64=-1, breve=False ):
    logging.debug( "a procesar {}".format( vecByte2strig( paquete ) ) )
    estadoAT = [ 'OK', 'ERROR', 'Invalid command', 'Invalid parameter' ]
    ind = 0
    atCmd = paquete[ind:ind+2]; ind += 2
    estado = estadoAT[ ord(paquete[ind]) ]; ind +=1
    valor = ""
    if len( paquete )>3 :
      if atCmd == "NI":
        nombre = paquete[ind:]
        valor = ", Valor = '{}' (0x{:02X})".format(
          nombre, toInt(paquete[ind:]) )
        if dir64>-1: #apuntamos nombre en la tabla
          self.__actualizaTablaDir(dir64, nombre=nombre)
      elif atCmd == "DN":
        my = toInt(paquete[ind:ind+2]); ind += 2
        serial = toInt(paquete[ind:ind+8]); ind += 8
        self.__actualizaTablaDir(serial, my)
        valor = ", Valor: MY=0x{:04X} S=0x{:016X} ".format( my, serial)
      elif atCmd == "ND":
        my = toInt(paquete[ind:ind+2]); ind += 2
        serial = toInt(paquete[ind:ind+8]); ind += 8
        nombre = ''
        while paquete[ind] != '\x00':
          nombre += paquete[ind]; ind += 1
        ind += 1
        self.__actualizaTablaDir(serial, my, nombre)
        mp = toInt(paquete[ind:ind+2]); ind += 2
        devty = self.DevicesType[ ord(paquete[ind]) ]; ind += 1
        status = ord(paquete[ind]); ind += 1
        profile = toInt(paquete[ind:ind+2]); ind += 2
        manuf = toInt(paquete[ind:ind+2]); ind += 2
        valor = ", Valor: MY=0x{:04X} 0x{:016X} '{}' MP=0x{:04X} {} sta=0x{:02X} prof=0x{:04X} manu=0x{:04X} ".format(
          my, serial, nombre, mp, devty, status, profile, manuf )
      elif atCmd == "IS":
        valor = dialogoAPI.__parteIS( paquete[ind:], breve )
      elif atCmd == "%V":
        val = toInt(paquete[ind:])
        valor = " Voltaje = {:.3f}V (0x{:04X})".format( val*1.2/1023, val )
      else:
        logging.debug( "es valor {}".format( vecByte2strig( paquete[ind:] ) ) )
        valor = ", Valor = 0x{0:02X} ({0})".format( toInt(paquete[ind:]) )
    return (atCmd, estado, valor)

  @staticmethod
  def __parteIS( paquete, breve=False):
    ''' Tratamiento de las parte de muestreo I/O
    '''
    ind = 0
    sets = ord(paquete[ind]); ind += 1
    digiCh = toInt(paquete[ind:ind+2]); ind += 2
    anaCh = ord(paquete[ind]); ind += 1
    if breve:
      valor = ","
    else:
      valor = ", set:{} digi=0x{:04X} ana=0x{:02X}".format(
        sets, digiCh, anaCh )
    if digiCh != 0: #Tenemos valores digitales en los 2 siguientes bytes
      dChName = [ 'DIO0', 'DIO1', 'DIO2', 'DIO3', 'DIO4', 'DIO5', 'DIO6', 'GPIO7', 'N/A', 'N/A', 'DIO10', 'DIO11', 'DIO12' ]
      digiVal = toInt(paquete[ind:ind+2]); ind += 2
      digiChN = [ i  for i in range(16) if ((digiCh >> i)&1) ]
      for cha in digiChN:
        valor += " {}={}".format( dChName[ cha ], (digiVal>>cha)&1 )
    if anaCh != 0: #Tenemos valores analogicos, 2 bytes por cada
      aChName = [ 'AD0', 'AD1', 'AD2', 'AD3', 'N/A', 'N/A', 'N/A', 'Vcc']
      anaChN = [ i  for i in range(8) if ((anaCh >> i)&1) ]
      for cha in anaChN:
        va = toInt(paquete[ind:ind+2]); ind += 2
        valor += " {}={:.3f}V".format( aChName[ cha ], va*1.2/0x3FF )
    if ind < len(paquete): #Sobró algo
      valor += "Sobró: 0x{:02X}".format( toInt(paquete[ind:]) )
    return valor

  def modemStatus(self, paquete, breve=False):
    if ord(paquete[0]) != 0x8A:
      logging.error( "el paquete no es 0x8A" )
      return
    if len( paquete ) < 2:
      logging.error( "paquete 0x8A no tienen tamaño necesario {}<2".format( len(paquete) ) )
      return
    status = ['Hardware reset', 'Watchdog timer reset', 'Associated', 'Disassociated',
      'Synchronization Lost', 'Coordinator realignment', 'Coordinator started' ]
    logging.info( "-> Modem Status: {}".format( status[ ord(paquete[1]) ] ) )

  def recepcionRemota( self, paquete, breve=False):
    if ord(paquete[0]) != 0x91:
      logging.error( "el paquete no es 0x91" )
      return
    if len( paquete ) < 2:
      logging.error( "paquete 0x91 no tienen tamaño necesario {}<2".format( len(paquete) ) )
      return
    ind = 1
    #frameId = ord(paquete[ind]); ind +=1
    dir64 = toInt( paquete[ind:ind+8] ); ind += 8
    dir16 = toInt( paquete[ind:ind+2] ); ind += 2
    self.__actualizaTablaDir(dir64, dir16) #apuntamos dirección
    srcEnd = toInt( paquete[ind:ind+1] ); ind += 1
    dstEnd = toInt( paquete[ind:ind+1] ); ind += 1
    cluster = toInt( paquete[ind:ind+2] ); ind += 2
    profile = toInt( paquete[ind:ind+2] ); ind += 2
    option = toInt( paquete[ind:ind+1] ); ind += 1

    #Sacamos la información del paquete
    if breve and dir64 in self.tablaDirecciones :
      direccion = "'{}'".format( self.tablaDirecciones[ dir64 ][ 1 ] )
    else:
      direccion = "0x{:016X} (0x{:04X})".format( dir64, dir16 )
    mensaje = "Recepcion remota: de {} srcEnd=0x{:02X} dstEnd=0x{:02X}, Cluster=0x{:04X} profile=0x{:04X} option=0x{:02X}".format(
      direccion, srcEnd,  dstEnd, cluster, profile, option )
    if ind < len( paquete ):
      try:
        mensaje += dialogoAPI.__parteIS( paquete[ind:], breve )
      except:
        mensaje += " resto=0x{:02X}".format( toInt( paquete[ind:] ) )
    logging.info( mensaje )

  def recepcionIORemota( self, paquete, breve=False):
    if ord(paquete[0]) != 0x92:
      logging.error( "el paquete no es 0x92" )
      return
    if len( paquete ) < 2:
      logging.error( "paquete 0x92 no tienen tamaño necesario {}<2".format( len(paquete) ) )
      return
    ind = 1
    dir64 = toInt( paquete[ind:ind+8] ); ind += 8
    dir16 = toInt( paquete[ind:ind+2] ); ind += 2
    self.__actualizaTablaDir(dir64, dir16) #apuntamos dirección

    recOption = self.recOpt[toInt( paquete[ind:ind+1] )]; ind += 1

    valor = dialogoAPI.__parteIS( paquete[ind:], breve )

    #Sacamos la información del paquete
    if breve and dir64 in self.tablaDirecciones :
      direccion = "'{}'".format( self.tablaDirecciones[ dir64 ][ 1 ] )
    else:
      direccion = "0x{:016X} (0x{:04X})".format( dir64, dir16 )
    mensaje = "IO data sample: de {} recOpt={} {}".format(
      direccion, recOption,  valor )
    logging.info( mensaje )

  def recepcionIndentifInd( self, paquete, breve=False):
    if ord(paquete[0]) != 0x95:
      logging.error( "el paquete no es 0x95" )
      return
    if len( paquete ) < 29:
      logging.error( "paquete 0x95 no tienen tamaño necesario {}<29".format( len(paquete) ) )
      return
    ind = 1
    dir64 = toInt( paquete[ind:ind+8] ); ind += 8
    dir16 = toInt( paquete[ind:ind+2] ); ind += 2
    self.__actualizaTablaDir(dir64, dir16) #apuntamos dirección

    recOption = self.recOpt[ord( paquete[ind:ind+1] )]; ind += 1
    remAdd = toInt( paquete[ind:ind+2] ); ind += 2
    dir64_2 = toInt( paquete[ind:ind+8] ); ind += 8
    nombre = ''
    while paquete[ind] != '\x00':
      nombre += paquete[ind]; ind += 1
    ind += 1
    self.__actualizaTablaDir(dir64, dir16, nombre)
    parentAdd = toInt( paquete[ind:ind+2] ); ind += 2
    devty = self.DevicesType[ ord(paquete[ind]) ]; ind += 1
    source = ['ERR','Push','Join','OTRO']
    sourceAcc = source[ ord(paquete[ind]) ]; ind += 1
    profile = toInt( paquete[ind:ind+2] ); ind += 2
    manufac = toInt( paquete[ind:ind+2] ); ind += 2

    #Sacamos la información del paquete
    if breve and dir64 in self.tablaDirecciones :
      direccion = "'{}'".format( self.tablaDirecciones[ dir64 ][ 1 ] )
    else:
      direccion = "0x{:016X} (0x{:04X})".format( dir64, dir16 )
    mensaje = "Identificación: de {} recOpt={} ".format(
      direccion, recOption )
    if remAdd != dir16 or dir64 != dir64_2:
      mensaje += "DISTINTAS remAdd=0x{:04X} add=0x{:016X}".format( remAdd, dir64_2)
    mensaje += " '{}'  MP=0x{:04X} {} source={} prof=0x{:04X} manu=0x{:04X} ".format(
          nombre, parentAdd, devty, sourceAcc, profile, manufac )
    logging.info( mensaje )


  def recepcionDatos( self, paquete, breve=False):
    if ord(paquete[0]) != 0x90:
      logging.error( "el paquete no es 0x90" )
      return
    if len( paquete ) < 12:
      logging.error( "paquete 0x90 no tienen tamaño necesario {}<12".format( len(paquete) ) )
      return
    ind = 1
    dir64 = toInt( paquete[ind:ind+8] ); ind += 8
    dir16 = toInt( paquete[ind:ind+2] ); ind += 2
    self.__actualizaTablaDir(dir64, dir16) #apuntamos dirección
    recOption = self.recOpt[ord( paquete[ind:ind+1] )]; ind += 1

    #Sacamos la información del paquete
    if breve and dir64 in self.tablaDirecciones :
      direccion = "'{}'".format( self.tablaDirecciones[ dir64 ][ 1 ] )
    else:
      direccion = "0x{:016X} (0x{:04X})".format( dir64, dir16 )
    mensaje = "Datos: de {} recOpt={}".format( direccion, recOption )
    #El resto son datos
    mensaje += " datos=0x{:02X} '{}'".format( toInt( paquete[ind:]),  paquete[ind:] )
    logging.info( mensaje )


  def comandosATlocal(self, LCmd):
    '''Recibe una lista de comandos AT para aplicar localmente
    Tambien admite string de comandos separados por comas.
    '''
    if  isinstance(LCmd, str): #Comandos pasados como strig
      LCmd = LCmd.split(',')
    for ca in LCmd:
      self.comandoATlocal( ca )

  def comandosATremoto(self, dest64, dest16, LCmd, inmediato=True):
    '''Recibe una lista de comandos y los envía como AT remotos
    Tambien admite string de comandos separados por comas.
    '''
    if  isinstance(LCmd, str): #Comandos pasados como strig
      LCmd = LCmd.split(',')
    for ca in LCmd:
      self.comandoATremoto(dest64, dest16, ca, inmediato)

####################################################################
## Programa principal
if __name__ == "__main__":
  du = dialogoAPI( conexion_ser("/dev/ttyUSB0",115200) )

  du.start()

  cmds = 'SH, SL, VR, AI, OP, CH, NI, ND'
  print "Enviamos los comandos AT: {}".format( cmds )
  du.comandosAT( cmds )

  time.sleep(10)
  du.comandoATlocal( 'FR', 0)
  time.sleep(10)

  du.finish()
  du.join()
  print "Terminamos"
