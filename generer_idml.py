import zipfile
import os

def creer_idml_de_test(nom_fichier="page_test.idml"):
    # Le contenu XML minimal pour un IDML
    mimetype = "application/vnd.adobe.indesign-idml-package"
    
    container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
    <container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
        <rootfiles>
            <rootfile full-path="designmap.xml" media-type="text/xml"/>
        </rootfiles>
    </container>'''

    designmap_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <Document DOMVersion="19.0" Self="d">
        <idPkg:Story src="Stories/Story_1.xml" xmlns:idPkg="http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging"/>
    </Document>'''

    story_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <Story DOMVersion="19.0" Self="Story_1">
        <Content>TITRE_1</Content>
        <Content>CONTENU_1</Content>
    </Story>'''

    # On crée l'archive ZIP avec l'extension .idml
    with zipfile.ZipFile(nom_fichier, 'w', zipfile.ZIP_DEFLATED) as idml_zip:
        # Le mimetype doit être ajouté en premier et non compressé
        idml_zip.writestr('mimetype', mimetype, compress_type=zipfile.ZIP_STORED)
        idml_zip.writestr('META-INF/container.xml', container_xml)
        idml_zip.writestr('designmap.xml', designmap_xml)
        idml_zip.writestr('Stories/Story_1.xml', story_xml)

    print(f"Fichier {nom_fichier} généré avec succès !")

if __name__ == "__main__":
    creer_idml_de_test()