#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from lxml import etree
import os
import urllib2
import logging
import sqlite3
from datetime import datetime
   
class Letra(object):
    def __init__(self, letra):
        self.__url = 'obras/%s'%letra
        self.__letra = letra.upper()
    
    def letra(self):
        return self.__letra
    
    def link(self):
        return self.__url
    
    def __repr__(self):
        return self.letra()

class Obra(object):
    def __init__(self, element, autor, link):
        self.__id = int(link.split('/')[len(link.split('/'))-1])
        self.__titulo = element.xpath('//h1[@class="eBook_titulo"]')[0].text
        self.__sinopsis = etree.tostring(element.xpath('//div[@class="eBook_sinopsis"]/p')[0])
        magnet_path = element.xpath('//div[@class="eBook_descarga_enlace magnet"]/a')
        self.__magnet = magnet_path[0].attrib['href'] if len(magnet_path) > 0 else None
        self.__link = link
        self.__generos = list()
        for g in element.xpath('//div[@class="eBook_genero"]/div[@class="field-item"]/a'):
            self.__generos.append(g.text)
        self.__version = element.xpath('//div[@class="eBook_version"]/b/text()')[0]
        pags = element.xpath('//div[@class="eBook_paginas"]/text()')
        self.__paginas = pags[0] if len(pags) > 0 else 'N/A'
        self.__usuario = element.xpath('//div[@class="eBook_usuario"]/a/text()')[0]
        creado = element.xpath('//div[@class="eBook_creado"]/text()')[0].split(".")
        self.__fecha_creacion = datetime(int(creado[2])+2000, int(creado[1]), int(creado[0]))
        self.__autor = autor

    def id(self):
        return self.__id
    
    def titulo(self):
        return self.__titulo
    
    def autor(self):
        return self.__autor

    def link(self):
        return self.__link
  
    def magnet(self):
        return self.__magnet
  
    def generos(self):
        return self.__generos

    def version(self):
        return self.__version

    def paginas(self):
        return self.__paginas

    def usuario(self):
        return self.__usuario

    def fecha_creacion(self):
        return self.__fecha_creacion

    def sinopsis(self):
        return self.__sinopsis

    @classmethod
    def sql_create(cls):
        return '''
            CREATE TABLE IF NOT EXISTS OBRA (
                id integer,
                titulo text,
                id_autor integer,
                link text,
                magnet text,
                generos text,
                version double,
                paginas integer,
                maquetador text,
                fecha_creacion text,
                sinopsis text,
                primary key (id, id_autor)
            );
        '''
    @classmethod
    def sql_insert(cls):
        return '''
            INSERT INTO OBRA (
                id,
                titulo,
                id_autor,
                link,
                magnet,
                generos,
                version,
                paginas,
                maquetador,
                fecha_creacion,
                sinopsis
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?);'''
        
    def sql_params(self):
        return [
            self.id(),
            self.titulo(), 
            self.autor().id(), 
            self.link(), 
            self.magnet(), 
            ",".join(self.generos()), 
            self.version(),
            self.paginas(),
            self.usuario(),
            self.fecha_creacion(),
            self.sinopsis(),
        ]

    def __repr__(self):
        return '%s { %s }' % (self.titulo(), self.magnet())
    
class Autor(object):
    def __init__(self, element):
        self.__nombre = element.text
        self.__link = element.attrib['href'][1:]
        self.__id = int(self.__link.split('/')[len(self.__link.split('/'))-1])
        
    def id(self):
        return self.__id
    
    def nombre(self):
        return self.__nombre
  
    def link(self):
        return self.__link
    
    @classmethod
    def sql_create(cls):
        return '''
            CREATE TABLE IF NOT EXISTS AUTOR (
                id integer primary key,
                nombre text,
                link text
            );
        '''
        
    @classmethod
    def sql_insert(cls):
        return '''
            INSERT INTO AUTOR (id, nombre, link)
            VALUES (?,?,?);
        '''
        
    def sql_params(self):
        return [
            self.id(),
            self.nombre(),
            self.link()
        ]

    def __repr__(self):
        return '%s: %s' % (self.nombre(), self.obras())
 
class EPubGratis(object):
    CACHE_DIR = '.cache' 
    DB_PATH = 'obras.db'
    
    def __init__(self, url):
        self.base = url
        self.__init_cache()
        self.__init_db()

    def procesar_obras(self, letra_desde = 'a', letra_hasta = 'z'):
        conn = None
        try:
            conn = sqlite3.connect(self.DB_PATH)
            for l in map(chr, range(ord(letra_desde), ord(letra_hasta) + 1)):
                letra = Letra(l)
    
                for e in self.__request(letra.link()).xpath('//div[@class="item-list"]/ul[@class="vocabindex alphabetical"]/li/a'):
                    autor = Autor(e)
                    logging.info('Insertando autor %s' % autor.nombre())
                    self.__insert_or_update(autor, conn)

                    for o in self.__request(e.attrib['href']).xpath('//a[@class="eBook_titulo"]'):
                        link_obra = o.attrib['href']
                        obra = Obra(self.__request(link_obra), autor, link_obra)
                        
                        logging.info('\tInsertando obra %s [id: %s - link: %s]' % (obra.titulo(), obra.id(), obra.link()))
                        self.__insert_or_update(obra, conn)

                    conn.commit()
        finally:
            if conn is not None:
                conn.close()

    def __insert_or_update(self, obj, conn):
        c = conn.cursor()
        c.execute(obj.sql_insert(), obj.sql_params())

    def __request(self, url):
        req_url = '%s/%s' % (self.base, url)
        cache_file = os.path.join(self.CACHE_DIR, url.replace("/", "_"))
        req = None
        sys.stderr.flush()
        try:
            if os.path.isfile(cache_file):
                logging.debug('Leyendo del cache %s' % url)
                req = open(cache_file, "r")
                content = req.read()
            else:
                logging.debug('Haciendo request %s' % url)
                content =  urllib2.urlopen(req_url).read()
                req = open(cache_file, "w")
                req.write(content)
        except:
            # manejo de errores muy primitivo, para evitar que se corte ante un timeout.... 
            # TODO: Mejorar!
            logging.exception ("Error haciendo request a '%s', reintentando" % url)
            sys.stderr.write("e")
            return self.__request(url)
        finally:
                if req is not None:
                    req.close()
        sys.stderr.write(".")
        return etree.HTML(content, etree.HTMLParser(encoding='utf-8'))

    def __init_db(self):
        conn = None
        logging.debug("Inicializando base de datos sqlite: %s..." % self.DB_PATH)
        try:
            conn = sqlite3.connect(self.DB_PATH)
            c = conn.cursor()
            
            c.execute(Obra.sql_create())
            c.execute(Autor.sql_create())
        finally:
            if conn is not None:
                conn.close()

    def __init_cache(self):
        if not os.path.exists(self.CACHE_DIR):
            logging.debug("Creando directorio de cache: %s..." % self.CACHE_DIR)
            os.mkdir(self.CACHE_DIR)

def main(output):
    # configuracion
    logging.basicConfig(
        filename='epubgratis.log', 
        level=logging.INFO, 
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filemode = 'a',
    )
    
    logging.info('Iniciando aplicación...')

    base = 'http://epubgratis.me'
    
    EPubGratis(base).procesar_obras('a', 'z')

    sys.exit(99)
    
    letras = EPubGratis(base).get_autores_por_letra('a', 'z')

    html = etree.Element('html')
    body = etree.Element('body')
    html.append(body)

    for l in letras:
        autores = l.autores()
        
        ul_autor = etree.Element('div')
        body.append(ul_autor)

        for a in autores:
            obras = a.obras()
            if len(obras) == 0:
                continue

            li_autor = etree.Element('table', style="width: 100%;")
            
            td_autor = etree.Element('div', style="background: #CCC");
            
            href = etree.Element('a', href="%s/%s" % (base,a.link()))
            href.text = a.nombre()
            td_autor.append(href)
            
            ul_autor.append(td_autor)
            
            ul_autor.append(li_autor)

            ul_obra = etree.Element('td')
            li_autor.append(ul_obra)

            for o in obras:
                li_obra = etree.Element('tr')

                if o.magnet() is not None:
                    href = etree.Element('a', href=o.magnet())
                    img_magnet = etree.Element('img', src="magnetLink.png")
                    href.append(img_magnet)
                    #href.text = "magnet"
                    titulo = etree.Element('a', href="%s%s" % (base,o.link()))
                    titulo.text = o.titulo()
                else:
                    titulo = etree.Element('a', href="%s%s" % (base,o.link()))
                    titulo.text = o.titulo()
                    href = etree.Element('div', style="color: #999")
                    href.text = "magnet"
                    
                    
                td_titulo = etree.Element('td', style="width: 40%;");
                td_titulo.append(titulo)
                li_obra.append(td_titulo)
		
                td_magnet = etree.Element('td', style="width: 80px;");
                td_magnet.append(href)
                li_obra.append(td_magnet)
                
                td_pag = etree.Element('td', style="width: 40px;")
                td_pag.text = u'%s' % o.paginas()
                li_obra.append(td_pag)

                td_genero = etree.Element('td', style="width: 20%;")
                td_genero.text = u'%s' % ", ".join(o.generos())
                li_obra.append(td_genero)
                
                td_version = etree.Element('td', style="width: 30px")
                td_version.text = u'%s' % o.version()
                li_obra.append(td_version)
                
                td_user = etree.Element('td', style="width: 100px;")
                td_user.text = u'%s' % o.usuario()
                li_obra.append(td_user)
                
                td_fecha = etree.Element('td')
                td_fecha.text = u'%s' % o.fecha_creacion()
                li_obra.append(td_fecha)
 
                ul_obra.append(li_obra)
           
    file = None
    try:     
        logging.info("Guardando la salida en %s" % output)
        file = open(output, "w") 
        file.write(etree.tostring(html))
    finally:
        if file is not None:
            file.close()
        
    logging.info('Terminó la ejecución!')

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print "Modo de uso: %s <archivo de salida>" % sys.argv[0]
        sys.exit(1)
    output = sys.argv[1]
    if os.path.exists(output):
        print "El archivo %s ya existe, indique un nombre diferente" % output
        sys.exit(2)
    main(output)
