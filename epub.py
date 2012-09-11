#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from lxml import etree
import os
import urllib2
import logging
   
class Letra(object):
    def __init__(self, letra):
        self.__url = 'obras/%s'%letra
        self.__letra = letra.upper()
        self.__autores = list()
    
    def letra(self):
        return self.__letra
    
    def agregar_autor(self, autor):
        self.__autores.append(autor)
        
    def autores(self):
        return self.__autores
    
    def link(self):
        return self.__url
    
    def __repr__(self):
        return self.letra()

class Obra(object):
    def __init__(self, element, link):
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
        self.__fecha_creacion = element.xpath('//div[@class="eBook_creado"]/text()')[0]
                    
    def titulo(self):
        return self.__titulo
    
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
    
    def __repr__(self):
        return '%s { %s }' % (self.titulo(), self.magnet())
    
class Autor(object):
    def __init__(self, element):
        self.__nombre = element.text
        self.__obras = list()
        self.__link = element.attrib['href'][1:]

    def agregar_obra(self, obra):
        self.__obras.append(obra)  

    def nombre(self):
        return self.__nombre
  
    def link(self):
        return self.__link
  
    def obras(self):
        return self.__obras
  
    def __repr__(self):
        return '%s: %s' % (self.nombre(), self.obras())
 
class EPubGratis(object):
    CACHE_DIR = ".cache" 

    def __init__(self, url):
        self.base = url
        if not os.path.exists(self.CACHE_DIR):
            logging.debug("Creando directorio de cache: %s..." % self.CACHE_DIR)
            os.mkdir(self.CACHE_DIR) 

    def get_autores_por_letra(self):
        por_letra = list()
        for l in map(chr, range(ord('a'), ord('z') + 1)):
            letra = Letra(l)
            por_letra.append(letra)

            for e in self.__request(letra.link()).xpath('//div[@class="item-list"]/ul[@class="vocabindex alphabetical"]/li/a'):
                autor = Autor(e)
                logging.info("agregando autor %s" % autor.nombre())
                letra.agregar_autor(autor)
                for o in self.__request(e.attrib['href']).xpath('//a[@class="eBook_titulo"]'):
                    link_obra = o.attrib['href']
                    obra = Obra(self.__request(link_obra), link_obra)
                    logging.info("agregando obra: %s" % obra.titulo())
                    autor.agregar_obra(obra)
        return por_letra
    
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
        except Exception, e:
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

def main():
    # configuracion
    logging.basicConfig(
        filename='epubgratis.log', 
        level=logging.INFO, 
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filemode = 'a',
    )
    
    logging.info('Iniciando aplicación...')
    #urllib2.install_opener(urllib2.build_opener(urllib2.ProxyHandler({'http': 'HOST:PORT'})))

    base = 'http://epubgratis.me'
  
    letras = EPubGratis(base).get_autores_por_letra()

    html = etree.Element('html')
    body = etree.Element('body')
    html.append(body)

    ul_letra = etree.Element('ul')
    body.append(ul_letra)
    
    for l in letras:
        autores = l.autores()
        
        li_letra = etree.Element('li')
        href = etree.Element('a', href="%s/%s" %(base,l.link()))
        href.text = l.letra()
        li_letra.append(href)
        
        ul_letra.append(li_letra)

        ul_autor = etree.Element('ul')
        li_letra.append(ul_autor)

        for a in autores:
            obras = a.obras()
            if len(obras) == 0:
                continue

            li_autor = etree.Element('li')

            href = etree.Element('a', href="%s/%s" % (base,a.link()))
            href.text = a.nombre()
            li_autor.append(href)
            
            ul_autor.append(li_autor)

            ul_obra = etree.Element('ul')
            li_autor.append(ul_obra)

            for o in obras:
                li_obra = etree.Element('li')

                if o.magnet() is not None:
                    href = etree.Element('a', href=o.magnet())
                    href.text = o.titulo()
                else:
                    href = etree.Element('a', href="%s%s" % (base,o.link()))
                    href.text = "%s (proximamente)" % o.titulo()

                li_obra.append(href)
                div_obra = etree.Element('div')
                div_obra.text = u'Géneros: %s - Versión: %s - Cantidad de Páginas: %s - Usuario: %s - Fecha de creación: %s' % (
                   ", ".join(o.generos()), o.version(), o.paginas(), o.usuario(), o.fecha_creacion())
                li_obra.append(div_obra)
 
                ul_obra.append(li_obra)
                
    print etree.tostring(html)
        
    logging.info('Terminó la ejecución!')

if __name__ == '__main__':
    main()
