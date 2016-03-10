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


'''
Nos basamos en el webserver.py del proyecto gesrut
'''

import os
import posixpath
import urllib
import sys
from datetime import datetime, timedelta


from BaseHTTPServer import HTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler
from SocketServer import ThreadingMixIn
import threading

import cgi
import urlparse
import time


from GestionaCaja import gestionaCaja
from Conexiones import *

import logging

def quita_segundos(cadena):
  return ":".join( str(cadena).split(":",2)[:2] )



class ManejaWeb(SimpleHTTPRequestHandler):
  '''
  Gestiona las peticones del seervidor web que presentará el estado de actividad de la máquina llamante
  '''

  _dia_str = [ 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo' ]
  _e2n = [ 'Desconectado', 'Conectado' ]

  def translate_path(self, path):
    """Modificamos para que el directorio sea relativo a la librería
    Translate a /-separated PATH to the local filename syntax.

    Components that mean special things to the local file system
    (e.g. drive or directory names) are ignored.  (XXX They should
    probably be diagnosed.)

    """
    # abandon query parameters
    path = path.split('?',1)[0]
    path = path.split('#',1)[0]
    path = posixpath.normpath(urllib.unquote(path))
    words = path.split('/')
    words = filter(None, words)
    path = self.server._path_static
    #print "path inicial de acceso directo: " + path
    for word in words:
      drive, word = os.path.splitdrive(word)
      head, word = os.path.split(word)
      if word in (os.curdir, os.pardir): continue
      path = os.path.join(path, word)
    #print "path de acceso directo: " + path
    return path

  def _respuesta200(self):
    self.send_response(200)
    self.send_header('Content-type', 'text/html; charset=UTF-8')
    self.send_header('Content-Language', 'es')
    self.end_headers()

  def _e(self,texto):
    self.wfile.write(texto + "\n")

  def _head(self, titulo):
    '''Envía la cabecera con el título'''
    self._e(
        '''<html>
        <head>
        <title>''' + titulo + '''</title>
        <link href="content.css" rel="stylesheet" type="text/css" />
        <link rel="shortcut icon" href="favicon.ico" type="image/x-icon">
        <link rel="icon" href="favicon.ico" type="image/x-icon">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta http-equiv="refresh" content="10">
        <!-- Generacion: ''' + str( datetime.now() ) + '''-->
        </head>
        <body>\n'''
        )

  def _elem(self, elem, text, clase = None):
    ini = "<" + elem
    if clase: ini += " class='" + clase + "'"
    ini += ">"
    self._e(ini + text + "</" + elem +">")

  def _p(self, parrafo, clase = None):
    self._elem('p', parrafo, clase)

  def _span(self, texto, clase = None):
    self._elem('span', texto, clase)

  def _h1(self, h1, clase = None):
    self._elem('h1', h1, clase)

  def _td(self, td, clase = None):
    self._elem('td', td, clase)

  def _cierra(self):
    self._e("\n</body>\n</html>")
    self.wfile.close()

  def _info_estado(self) :
    '''Muestra información de estado de la caja'''
    s = self
    s._respuesta200()
    s._head("Info máquina estado caja "+s.server._ges_caja.nombreNodo)
    s._p("Info máquina estado caja "+s.server._ges_caja.nombreNodo)
    s._p("Estado de las salidas:")
    s._e("<form action='index.html' method='post'>")
    s._e("<input type='hidden' name='oculto' value='oculto'>")
    s._e("<ul>")
    ahora = time.time()
    #puerto 4
    s._e("<li>Bomba agua :")
    if not s.server._ges_caja.estado4:
      s._e( "Apagado" )
    else:
      segundos = int( s.server._ges_caja.encendido4 - ahora )
      minutos = int( segundos/60 )
      segundos = segundos - minutos*60
      s._e( "Encendido durante {}:{} minutos".format( minutos, segundos ) )
      s._e("<input type='submit' name='s4' value='Apagar'>")
    s._e("<input type='submit' name='s4' value='Encender 5'>")
    s._e("<input type='submit' name='s4' value='Encender 15'>")
    s._e("<input type='submit' name='s4' value='Encender 30'>")
    s._e("</li>")

    #puerto 5
    s._e("<li>Luz portatil : ")
    if not s.server._ges_caja.estado5:
      s._e( "Apagado" )
    else:
      segundos = int( s.server._ges_caja.encendido5 - ahora )
      minutos = int( segundos/60 )
      segundos = segundos - minutos*60
      s._e( "Encendido durante {:01d}:{:02d} minutos".format( minutos, segundos ) )
      s._e("<input type='submit' name='s5' value='Apagar'>")
    s._e("<input type='submit' name='s5' value='Encender 5'>")
    s._e("<input type='submit' name='s5' value='Encender 15'>")
    s._e("<input type='submit' name='s5' value='Encender 30'>")
    s._e("</li>")

    s._e("</ul>")
    s._e("</form>")

    s._cierra()

  def _info_eventos_maquina_dada(self, maquina):
    s = self
    s._h1("Información de eventos de la máquina " + maquina)
    if not ( maquina in s.server._maq_tiempos ):
      s._p("Maquina  <span class='nombre_maquina'>{0}</span> no manejada".format(maquina) )
      s._p(":-(")
      return
    ahora = datetime.now()
    tiemposMq = s.server._maq_tiempos[maquina]
    estado, hasta = tiemposMq.estado_debido(ahora)
    s._p("Estado: <span class='{0}'>{0}</span> hasta <span class='hora'>{1}</span>"
      .format(s._e2n[estado], hasta) )
    resta = hasta - ahora
    s._p("Estado: <span class='{0}'>{0}</span> durante <span class='tiempo_resta'>{1}</span> (horas:minutos)"
      .format(s._e2n[estado], quita_segundos(resta)) )
    s._p("Estado: <span class='{0}'>{0}</span> durante <span class='minutos_resta'>{1}</span> minutos"
      .format(s._e2n[estado], int(resta.total_seconds() / 60)) )

    #Proximos eventos
    futuros = tiemposMq.eventos_futuros(ahora)

    #tabla de futuros
    s._e("""<table class='tabla_futuros'>
      <caption>Tiempos Futuros</caption>
      <thead>
      <tr><th>Instante</th>
      <th>distancia<br/>(minutos)</th>
      <th>Estado</th>
      </thead>
      <tbody>""")
    for instante, estado in futuros :
      s._e("<tr>")
      s._td( quita_segundos( instante ) )
      s._td( quita_segundos( instante - ahora) , 'izda')
      s._td( s._e2n[estado], s._e2n[estado] )
      s._e("</tr>")
      s._e("</tbody>\n</table>")

  def do_GET(self):
    parsed_path = urlparse.urlparse(self.path)
    logging.debug( "Recibido GET Th:{} Comm: {} From: {} path={} query={}".format(
      threading.current_thread().name
      , self.command, self.client_address, parsed_path.path, parsed_path.query) )
    #print "request_version: %s" % self.request_version
    #print "headers: %s" % self.headers

    if parsed_path.path == "/" or parsed_path.path == "/index.html":
      self._info_estado()
      return
    if parsed_path.path == "/cambia4.html" :
      self.server._ges_caja.fija4( not self.server._ges_caja.estado4 )
      self._info_estado()
      return
    if parsed_path.path == "/cambia5.html" :
      self.server._ges_caja.fija5( not self.server._ges_caja.estado5 )
      self._info_estado()
      return
    #Si no es nada de lo anterior se atiende por el padre
    SimpleHTTPRequestHandler.do_GET(self)
    return

  def do_POST(self):
    parsed_path = urlparse.urlparse(self.path)
    logging.debug( "Recibida POST Th:{} Comm: {} From: {} path={} query={}".format(
      threading.current_thread().name
      , self.command, self.client_address, parsed_path.path, parsed_path.query) )
    #print "request_version: %s" % self.request_version
    #print "headers: %s" % self.headers
    form = cgi.FieldStorage(
      fp=self.rfile,
      headers=self.headers,
      environ={'REQUEST_METHOD':'POST',
                'CONTENT_TYPE':self.headers['Content-Type'],
    })
    #for item in form.list:
      #print item
    logging.debug("Items del form: {}".format( form.list ) )

    if "s4" in form:
      logging.debug( "S4 vale >{}<".format( form.getvalue("s4") ) )
      if form.getvalue("s4") == 'Apagar':
        self.server._ges_caja.fija4( not self.server._ges_caja.estado4 )
      if form.getvalue("s4") == 'Encender 5':
        self.server._ges_caja.fija4( True, minutos = 5 )
      if form.getvalue("s4") == 'Encender 15':
        self.server._ges_caja.fija4( True, minutos = 15 )
      if form.getvalue("s4") == 'Encender 30':
        self.server._ges_caja.fija4( True, minutos = 30 )
    if "s5" in form:
      logging.debug( "S5 vale >{}<".format( form.getvalue("s5") ) )
      if form.getvalue("s5") == 'Apagar':
        self.server._ges_caja.fija5( not self.server._ges_caja.estado5 )
      if form.getvalue("s5") == 'Encender 5':
        self.server._ges_caja.fija5( True, minutos = 5 )
      if form.getvalue("s5") == 'Encender 15':
        self.server._ges_caja.fija5( True, minutos = 15 )
      if form.getvalue("s5") == 'Encender 30':
        self.server._ges_caja.fija5( True, minutos = 30 )

    #Si no es nada de lo anterior se atiende por el padre
    self.do_GET()
    return



class webserver(ThreadingMixIn, HTTPServer):

  def __init__(self, gestCaja):
    '''
    Necesita el gestor de la caja
    '''
    self._path_static = os.path.dirname(os.path.abspath(__file__)) + '/static/'
    logging.debug( "Static: " + self._path_static )
    self._ges_caja = gestCaja
    HTTPServer.__init__(self, ('', 9080), ManejaWeb)


### Programa principal
if __name__ == '__main__':
  '''
  Aplicación de gestión de la caja desde servidor web
  '''
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument("--port"
    , help="puerto de conexión", default="/dev/ttyUSB0" )
  parser.add_argument("--speed", type=int
    , help="velocidad de conexion", default=115200 )
  parser.add_argument("--log"
    , help="nivel de log", default="info" )
  parser.add_argument("--logfile"
    , help="fichero de log",default="/tmp/webserver.log" )

  args = parser.parse_args()

  loglevel = "debug"  #TODO leerlo de los argumentos
  # assuming loglevel is bound to the string value obtained from the
  # command line argument. Convert to upper case to allow the user to
  # specify --log=DEBUG or --log=debug
  numeric_level = getattr(logging, args.log.upper(), None)
  if not isinstance(numeric_level, int):
      raise ValueError('Invalid log level: %s' % loglevel)
  logging.basicConfig(level=numeric_level
    , format='%(asctime)s %(levelname)s:[%(funcName)s] %(message)s'
    , filename=args.logfile
    )

  logging.info( "Conectando a {} con velocidad {}".format( args.port, args.speed ) )

  try:
    gc = gestionaCaja( conexion_ser(args.port,args.speed), "NODE22" )
  except:
    logging.critical( "Unexpected error: {}".format( sys.exc_info()[0] ) )
    logging.critical( "No se pudo conectar con USB" )
    exit(1)

  gc.start()


  try:
    server = webserver( gc )
    logging.info( 'started httpserver...' )
    server.serve_forever()
  except KeyboardInterrupt:
    logging.info( '^C received, shutting down server' )
    server.socket.close()
    gc.finish()
    gc.join()
    logging.info( "Terminamos" )
