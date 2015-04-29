#!/usr/bin/env python
# -*- coding: UTF-8 -*-

#Programa con la lógica para gestionar la caja con 2 reles (D0,D1), 2 leds(D2,D3) y 2 pulsadores(D4,D5)

from Conexiones import *
from DialogaAPI import *
import time
import sys
import re
import logging

class gestionaCaja(dialogoAPI):
  '''Clase que añade a dialogoAPI la lógina para gestionar
    la caja con 2 reles (D0,D1), 2 leds(D2,D3) y 2 botones (D4,D5)
  '''

  def __init__(self, c, NombreNodo):
    dialogoAPI.__init__(self, c)
    self.nombreNodo = NombreNodo
    self.estado4 = False
    self.encendido4 = 0
    self.estado5 = False
    self.encendido5 = 0
    logging.info( "Gestionando el nodo '{}'".format( self.nombreNodo ) )

  def parpadea( self ):
    '''Thead para hacer parpadear los leds para indicar la conección
    '''
    #TODO poner dirección de 16 bit en atributo.
    serial = self.nombretoSerial( self.nombreNodo )
    while True:
      time.sleep(5)
      #logging.debug("Comienza parpadea: >{}<".format( comandos ) )
      ahora = time.time()

      #Miramos si hay que apagar algo
      if self.estado4 and ahora>=self.encendido4:
        self.fija4(False)
      if self.estado5 and ahora>=self.encendido5:
        self.fija5(False)

      #Parpadeamos los leds
      comandos = []
      comandos.append( 'D24' if self.estado4 else 'D25' )
      comandos.append( 'D34' if self.estado5 else 'D35' )
      self.comandosATremoto( serial, -1, comandos)
      time.sleep(0.100)
      comandos = []
      comandos.append('D25' if self.estado4 else 'D24')
      comandos.append('D35' if self.estado5 else 'D34')
      self.comandosATremoto( serial, -1, comandos)

      #Segundo parpadeo
      time.sleep(0.200)
      comandos = []
      if self.pulsaLarga4:
        comandos.append( 'D24' if self.estado4 else 'D25' )
      if self.pulsaLarga5:
        comandos.append( 'D34' if self.estado5 else 'D35' )
      self.comandosATremoto( serial, -1, comandos)
      time.sleep(0.100)
      comandos = []
      if self.pulsaLarga4:
        comandos.append('D25' if self.estado4 else 'D24')
      if self.pulsaLarga5:
        comandos.append('D35' if self.estado5 else 'D34')
      self.comandosATremoto( serial, -1, comandos)

      #logging.debug("Fin parpadea: >{}<".format( comandos ))


  def fijaInicial( self ):
    logging.info( '''Fijamos el valor inicial''' )
    self.comandoATlocal("ND" + self.nombreNodo )
    time.sleep(2.0)
    self.fija4( self.estado4 )
    self.fija5( self.estado5 )
    self.timePulsa4 = 0
    self.timePulsa5 = 0
    self.inicioPulsa4 = 0.0
    self.inicioPulsa5 = 0.0
    self.pulsaLarga4 = True
    self.pulsaLarga5 = False
    self.tiempoRebotes = 2
    self.parpadea()

  def run(self):
    t = threading.Timer(2.0, self.fijaInicial)
    t.setDaemon(True)
    t.start()
    dialogoAPI.run( self )


  def respuestaATremota(self, paquete, breve=False ):
    dialogoAPI.respuestaATremota(self, paquete, breve )
    return

  def recepcionRemota( self, paquete, breve=False):
    dialogoAPI.recepcionRemota( self, paquete, breve)
    segAhora = time.time()
    #Vemos serial del nodo gestionado
    serial = self.nombretoSerial( self.nombreNodo )
    if serial == -1:
      logging.debug( "Nodo {} no visto aún".format( self.nombreNodo ) )
      return
    ind = 1
    #frameId = ord(paquete[ind]); ind +=1
    dir64 = toInt( paquete[ind:ind+8] ); ind += 8

    if dir64 != serial:
      logging.debug( "no es de nuestro nodo 0x{:016X} != 0x{:016X}".format(dir64, serial) )
      return

    dir16 = toInt( paquete[ind:ind+2] ); ind += 2
    srcEnd = toInt( paquete[ind:ind+1] ); ind += 1
    dstEnd = toInt( paquete[ind:ind+1] ); ind += 1
    cluster = toInt( paquete[ind:ind+2] ); ind += 2
    profile = toInt( paquete[ind:ind+2] ); ind += 2
    option = toInt( paquete[ind:ind+1] ); ind += 1

    sets = ord(paquete[ind]); ind += 1
    digiCh = toInt(paquete[ind:ind+2]); ind += 2
    anaCh = ord(paquete[ind]); ind += 1
    if (digiCh & (1<<4|1<<5)) == 0:
      logging.warning( "no hay información canales 4 ni 5" )
      return
    digiVal = toInt(paquete[ind:ind+2]); ind += 2
    #Canal 4
    if not (digiVal>>4)&1 and segAhora>self.timePulsa4:
      self.fija4( not self.estado4, breve )
      self.timePulsa4 = segAhora + self.tiempoRebotes
      self.inicioPulsa4 = segAhora
    if (digiVal>>4)&1 and self.inicioPulsa4>0.0: #Se soltó el pulsador
      dura4 = segAhora - self.inicioPulsa4
      logging.info( "Pulsación de 4 duró {} sg".format( dura4 ) )
      self.inicioPulsa4 = 0.0 #Para indicar que no hay pulsación
    #Canal 5
    if not (digiVal>>5)&1 and segAhora>self.timePulsa5 :
      self.fija5( not self.estado5, breve )
      self.timePulsa5 = segAhora + self.tiempoRebotes
      self.inicioPulsa5 = segAhora
    if (digiVal>>5)&1 and self.inicioPulsa5>0.0: #Se soltó el pulsador
      dura5 = segAhora - self.inicioPulsa5
      logging.info( "Pulsación de 5 duró {} sg".format( dura5 ) )
      self.inicioPulsa5 = 0.0 #Para indicar que no hay pulsación
    return

  def fija4(self, estado, breve=False, minutos = 15):
    self.estado4 = not (not estado)
    serial = self.nombretoSerial( self.nombreNodo )
    #comandos = ''
    if self.estado4:
      #encendido
      comandos = 'D04, D25'
      self.encendido4 = time.time() + minutos*60
    else:
      comandos = 'D05, D24'
    logging.debug( "Canal 4 fijado a {}, comando = >{}<".format(
        self.estado4, comandos ) )
    self.comandosATremoto( serial, -1, comandos, True)

  def fija5(self, estado, breve=False, minutos = 15):
    self.estado5 = not ( not estado )
    serial = self.nombretoSerial( self.nombreNodo )
    if self.estado5:
      comandos = 'D14, D35'
      self.encendido5 = time.time() + minutos*60
    else:
      comandos = 'D15, D34'
    logging.debug( "Canal 5 fijado a {}, comando = >{}<".format(
        self.estado5, comandos ) )
    self.comandosATremoto( serial, -1, comandos, True)



####################################################################
## Programa principal
if __name__ == "__main__":
  from ConsultaAPI import hiloPrincipal
  hiloPrincipal( gestionaCaja(None, "NODE22" ) )
