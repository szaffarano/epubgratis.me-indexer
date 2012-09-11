ePubGratis.me Indexer
=====================

Indexa el contenido de la página epubgratis.me

Modo de uso
===========

En esta primera versión no hay un indexado incremental, con lo que hace requests de todo el site, lo
que insume mucho tiempo.  Por tal motivo genera en el directorio en donde se corre el programa
un cache para almacenar las páginas que consulta (en la carpeta .cache).  Actualmente ocupa ~ 200MB.

	$ ./epub.py > archivo-de-salida.html

Derajá en *archivo-de-salida.html* el HTML con los datos ordenados por Inicial del nombre del autor -> Nombre del autor -> Listado de obras.
