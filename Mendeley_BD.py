#%% Bibliotecas y funciones
import sqlite3
import urllib.request
import re
from os import path, listdir


def conjunciones_minuscula(titulo):
    pal_min = ["and", "the", "for", "in", "to", "at", "as", "an", "on", "of",
               "el", "la", "lo", "los", "las", "y", "de", "a", "con", "sin", "para", "su", "sus"]
    palabras = titulo.capitalize().split()
    nuevo_titulo = " ".join([p if p in pal_min else p.capitalize() for p in palabras])
    return nuevo_titulo


class mendeleyRescue:
    def __init__(self):
        """
        :rtype: DB conection
        """

        def dict_factory(cursor, row):
            # Función para recuperar datos identificados por nombre de columna
            d = {}
            for idx, col in enumerate(cursor.description):
                d[col[0]] = row[idx]
            return d

        # Prepara la conexión a la base de datos
        usuario = path.expanduser("~")
        path_bd_mendeley = path.join(usuario, "AppData", "Local",
                                     "Mendeley Ltd", "Mendeley Desktop")
        self.mendeley_bd_path = [bd for bd in listdir(path_bd_mendeley)
                                 if bd.endswith("@www.mendeley.com.sqlite")]
        self.mendeley_bd_path = path.join(path_bd_mendeley, self.mendeley_bd_path[0])

        try:
            self.connect = sqlite3.connect(self.mendeley_bd_path)

        except sqlite3.Error as e:
            print(e)

        # Prepara recuperación de registros a un diccionario {columna: valor}
        self.connect.row_factory = dict_factory

    def mendeley_schema(self):
        # Recupera el esquema de la base de datos
        schema = self.connect.cursor()
        schema.execute("SELECT SQL FROM sqlite_master WHERE SQL NOT NULL")
        schema_txt = [s["sql"] + "\n\n" for s in schema.fetchall()]
        with open("esquema_mendeley2.txt", "w") as f:
            f.writelines(schema_txt)

        # Recupera la lista de tablas definidas en la base de datos
        res = self.connect.cursor()
        res.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tablas = [n["name"] for n in res]

        # Guarda la lista de tablas en la BD de Mendeley
        with open("tablas_mendeley.txt", "w") as f:
            f.writelines(["\n\nTablas en la base de datos de Mendeley\n", "*" * 38, "\n"])
            for name in tablas:
                f.write(name + "\n")
            f.writelines(["-" * 38, "\n\n"])

    def listDocs(self):
        # Lista de documentos en la BD
        docs_conn = self.connect.cursor()
        docs_conn.execute(
            """
            SELECT id, title, year, deletionPending
            FROM Documents 
            WHERE DeletionPending = 'false'
            ORDER BY title
            """)

        docs = [d for d in docs_conn.fetchall()]
        return docs

    def numDocs(self):
        # Cuenta el número total de registros en la BD de Mendeley ("Mi biblioteca" + grupos compartidos)
        num_docs = self.connect.cursor()
        num_docs.execute("""
            SELECT COUNT(*) as entries, RemoteDocuments.groupId as gr, Groups.name  as gr_name
            FROM Documents
                LEFT JOIN RemoteDocuments ON RemoteDocuments.documentId = Documents.id 
                JOIN Groups ON RemoteDocuments.groupId = Groups.id
            WHERE DeletionPending = 'false'
            GROUP BY gr 
            ORDER BY gr;""")
        datos = [d for d in num_docs.fetchall()]

        if datos[0]["gr"] == 0:
            datos[0]["gr_name"] = "My library"

        return datos

    def dups(self, grupo=0):
        # Registros con duplicados en la colección principal gr = 0 o en el grupo elegido (existente en Groups.id)
        dups = self.connect.cursor()
        dups.execute(
            """
            SELECT COUNT(*) as entries, LOWER(title) as title, year, 
                   RemoteDocuments.groupId as gr, Groups.name as gr_name
            FROM Documents
                LEFT JOIN RemoteDocuments ON RemoteDocuments.documentId = Documents.id 
                JOIN Groups ON RemoteDocuments.groupId = Groups.id
            WHERE DeletionPending = 'false'
            GROUP BY title, year, gr HAVING entries > 1 AND gr = {grupo}
            ORDER BY entries DESC ;
            """.format(grupo=grupo))

        candidatos_borrables = [b for b in dups.fetchall()]

        return candidatos_borrables

    def doc_grupo(self, grupo=0):
        docs_inecol = self.connect.execute(
            """
            SELECT RemoteDocuments.groupId, Groups.name as grp_name, lower(Documents.title) as title, Documents.id
            FROM RemoteDocuments
                JOIN Groups ON RemoteDocuments.groupId = Groups.id
                JOIN Documents ON RemoteDocuments.documentId = Documents.id
            WHERE RemoteDocuments.groupId = {grupo} AND Documents.DeletionPending = 'false'
            ORDER BY Documents.title;
            """.format(grupo=grupo))

        titulos = [t for t in docs_inecol]
        return titulos

    def autores(self):
        autores = self.connect.execute(
            """
            SELECT id, firstNames, lastName
            FROM DocumentContributors
            """)

        listaAutores = list(set([" ".join([a["firstNames"], a["lastName"]]) for a in autores]))
        return listaAutores

    def archivos(self):
        archivos = self.connect.execute(
            """
            SELECT localUrl as file_path
            FROM Files
            """)

        listaArchivos = [{"file": urllib.request.unquote(path.basename(a["file_path"])),
                          "dir": urllib.request.unquote(path.dirname(a["file_path"]))}
                         for a in archivos if not a["file_path"] == ""]
        return listaArchivos

    def update_titles(self):
        symbolInitial = ["'", "(", "[", "{", '"', " ", ".", "¿", "¡", "\u201c"]
        all_docs = self.listDocs()
        updated_title = {"title": "", "id": None}
        for doc in all_docs:
            if doc["title"][0] in symbolInitial:
                updated_title.update({"title": doc["title"][0] + doc["title"][1].capitalize() +
                                               doc["title"][2:].lower(), "id": doc["id"]})
            else:
                updated_title.update({"title": doc["title"].lower().capitalize(), "id": doc["id"]})
            self.connect.execute("UPDATE Documents SET title =:title WHERE id = :id ", updated_title)
        self.connect.commit()

    def fileArchive(self, dicPaths):
        self.connect.execute(
            """
            UPDATE Files SET localUrl = REPLACE(localUrl, '{oldPath}', '{newPath}')
            WHERE localUrl LIKE '%{oldPath}%';
            """.format(**dicPaths))
        self.connect.commit()

    def close(self):
        self.connect.commit()
        self.connect.close()


#%% Main ---------------
mendeley = mendeleyRescue()
conecta_bd = mendeley.connect
mendeley.mendeley_schema()

#%% Lista de documentos descargados
listaArchivos = mendeley.archivos()
simp_arch_dir = list(set([f["dir"].split("file:///")[1] for f in listaArchivos]))

with open("Mendeley_documentos_descargados.txt", "w", encoding="utf-8") as f:
    f.writelines(["Documentos de Mendeley con archivos descargados en este equipo\n", "*"*63, "\n\n"])

    f.writelines(["Los documentos están almacenados en:\n", "-"*37, "\n"])
    for d in simp_arch_dir:
        f.writelines([d, "\n"])

    f.writelines(["\n\nLista de documentos descargados:\n", "-"*32, "\n"])
    for doc in listaArchivos:
        f.writelines([doc["file"], "\n"])

#%% Lista de autores
listaAutores = mendeley.autores()
listaAutores.sort()

with open("Mendeley_lista_autores.txt", "w", encoding="utf-8") as f:
    f.writelines(["Lista de autores de los documentos en Mendeley\n", "*"*46, "\n\n"
                  "Registros sospechosos:\n", "-"*22, "\n"])
    for a in listaAutores:
        if len(a.strip())> 50 or len(a.split())>5 or len(a.strip())<5 or (a.strip()[0] in ["(", "[", "{", "<"]):
            f.writelines([a.strip(), "\n"])

    f.writelines(["\n\nLista completa de autores:\n", "-"*26, "\n"])
    for a in listaAutores:
        f.writelines([a.strip(), "\n"])

#%% Lista de documentos en Mendeley
documentos = mendeley.listDocs()
# Archivo con la lista de todos los documentos
with open("Mendeley_todos_los_titulos.txt", "w", encoding="utf-8") as f:
    f.write("sec, id, title, year, deletionPending\n")
    i = 0
    for d in documentos:
        i += 1
        if d["year"] == None:
            d["year"] = "sa"
        else:
            d["year"] = str(d["year"])
        line = "{:5d}:, {:10d}, {:.60}, {:6}, {:5}\n".format(i, d["id"], d["title"], d["year"], d["deletionPending"])
        f.write(line)

#%% Distribución de documentos entre los grupos y "My library"
num_docs_grp = mendeley.numDocs()
with open("Mendeley_duplicados.txt", "w") as f:
    f.write("Número de documentos en la BD de Mendeley\n")
    f.write("{:10}  {:5}  {:15}\n".format("Num docs", "gr_id", "gr_name"))
    f.write("{:<50}\n".format("-" * 50))
    for d in num_docs_grp:
        f.write("{:10}  {:5}  {:15}\n".format(d["entries"], d["gr"], d["gr_name"]))
    f.write("{:<50}\n".format("-" * 50))

#%% Análisis de duplicados
lista_duplicados = mendeley.dups(grupo=0)

total = sum([r["entries"] for r in lista_duplicados])
grupo = lista_duplicados[0]["gr_name"]
if grupo is "":  # Si no hay grupo el documento es de "mi colección"
    grupo = "My library"

with open("Mendeley_duplicados.txt", "a") as f:
    f.write("\nEl total de duplicados en el grupo '{}' es = {}\n\n\n".format(grupo, total))
    for d in lista_duplicados:
        f.write("{entries}: {title:_<80.80} ({year})\n".format(**d))

#%% Documentos en el grupo seleccionado
titulos = mendeley.doc_grupo(grupo=0)
grupo = titulos[0]["grp_name"]
if grupo == "":
    grupo = "My library"
with open("Mendeley_docs_en_{}.txt".format(grupo), "wb") as f:
    linea = " ".join(["Documentos en el grupo '{grupo}'\n".format(grupo=grupo),
                      u"*" * 40, u"\n"]).encode("utf-8")
    f.write(linea)
    i = 0
    for titulo in titulos:
        i += 1
        f.write("{:>4}: {: <120.120}\n".format(i, conjunciones_minuscula(titulo["title"])).encode("utf-8"))

#%% Update directory to hold file archive
listaArchivos = mendeley.archivos()
simp_arch_dir = list(set([f["dir"] for f in listaArchivos]))
dirs = {}
if len(dirs) > 1:
    for f in simp_arch_dir:
        if not "AppData" in f:
            dirs = {"newPath": f.replace(" ", "%20"), "oldPath": ""}
        else:
            dirs["oldPath"] = f.replace(" ", "%20")

    mendeley.fileArchive(dirs)

#%% Actualización de los títulos para usar minúsculas con inicial mayúscula
mendeley.update_titles()

#%% Finish processing
mendeley.close()