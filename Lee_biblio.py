import bibtexparser

dir_test = "C:/Users/equih/Documents/1 Nubes/Dropbox/3 Artículos descargados (archivar)/"

with open(dir_test + 'My_Collection.bib', "rb") as bibtex_file:
    bib_database = bibtexparser.load(bibtex_file)

print("Encontré {} registros en la base de datos".format(len(bib_database.entries)))

archivos = [f["file"] for f in bib_database.entries if "file" in f]





