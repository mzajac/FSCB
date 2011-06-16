#!/usr/bin/env python
#encoding: utf-8
import sys, os, shutil, string, codecs, re
from lxml import etree
from lxml.cssselect import CSSSelector

SUBDIRECTORY = "data"

def err(msg="unknown"):
    print "Error: %s" % msg
    sys.exit(1)
    
def extract_font_info(string, font_sizes, font_families):
    def match_attribute(attribute, default=""):
        regex = "%s: .*?;" % attribute
        match = re.search(regex, string)
        return string[match.span()[0] + len(attribute) + 2 : match.span()[1] - 1] if match else default

    """converts from 
    font-family: TimesNewRoman; font-size: 12pt; font-weight: bold; font-style: italic
    ======>
    font:italic:bold:TimesNewRoman:12pt
    and adds font-size and font-family to corresponding sets"""
    string += ";"
    font_style = match_attribute("font-style", "straight")
    font_weight = match_attribute("font-weight", "normal")
    font_family = match_attribute("font-family")
    #poliqarp has a problem with attributes containing commas which are removed
    font_family = "".join([c for c in font_family if c not in [',', ' ']])
    font_size = match_attribute("font-size")
    font_sizes.add(font_size)
    font_families.add(font_family)
    return "font:%s:%s:%s:%s" % (font_style, font_weight, font_family, font_size)

def create_directories():
    try:
        shutil.rmtree(DIRECTORY)
    except OSError:
        pass
    try:
        os.mkdir(DIRECTORY)
        os.chdir(DIRECTORY)
        os.mkdir(SUBDIRECTORY)
    except:
        err("couldn`t create directories")
        
def write_bp_config():
    bp_cfg = """[locale]
locale = pl_PL

[meta]
name = autor
multiple = yes
path = /cesHeader/fileDesc/sourceDesc//biblStruct/analytic/h.author
path = /cesHeader/fileDesc/sourceDesc//biblStruct/monogr/h.author

[meta]
name = tytuł
path = /cesHeader/fileDesc/sourceDesc/biblFull/titleStmt/h.title
path = /cesHeader/fileDesc/sourceDesc//biblStruct/analytic/h.title
path = /cesHeader/fileDesc/sourceDesc//biblStruct/monogr/h.title

[meta]
name = wydawca
path = /cesHeader/fileDesc/sourceDesc//biblStruct/monogr/imprint/publisher

[meta]
name = miejsce_wydania
path = /cesHeader/fileDesc/sourceDesc//biblStruct/monogr/imprint/pubPlace

[meta]
name = data_wydania
type = date
path = /cesHeader/fileDesc/sourceDesc//biblFull/publicationStmt/pubDate/@value
path = /cesHeader/fileDesc/sourceDesc//biblStruct/monogr/imprint/pubDate/@value

[meta]
name = data_pierwszego_wydania
type = date
path = /cesHeader/fileDesc/sourceDesc//biblStruct/analytic/origDate/firstPubDate/@value
path = /cesHeader/fileDesc/sourceDesc//biblStruct/monogr/imprint/origDate/firstPubDate/@value

[meta]
name = data_powstania
type = date
path = /cesHeader/fileDesc/sourceDesc//biblStruct/analytic/origDate/createDate/@value
path = /cesHeader/fileDesc/sourceDesc//biblStruct/monogr/imprint/origDate/createDate/@value

[meta]
name = styl
type = enum
values = "artystyczny" "proza" "poezja" "dramat" "publicystyczny" "literatura faktu" "naukowo-dydaktyczny" "naukowy humanistyczny" "naukowy przyrodniczy" "naukowy techniczny" "popularno-naukowy" "podręcznik" "urzędowo-kancelaryjny" "protokół" "ustawa" "informacyjno-poradnikowy" "potoczny"
multiple = yes
path = /cesHeader/profileDesc/textClass/h.keywords/keyTerm

[meta]
name = medium
type = enum
values = "prasa" "książka" "internet" "rękopis"
path = /cesHeader/profileDesc/textDesc/channel
    """
    try:
        f = open("%s.bp.conf" % DIRECTORY, "w")
    except IOError:
        err("Error writing corpus builder config")
    print >> f, bp_cfg

def write_config(font_families, font_sizes):
    font_families = "font-family = " + " ".join(font_families)
    font_sizes = "font-size = " + " ".join(font_sizes)
    
    cfg = """[attr]
font-style = italic straight
font-weight = bold normal
%s
%s

[pos]
font = font-style font-weight font-family font-size

[named-entity]
entity-orth = orth
entity-base = base
entity-tag = tag
entity-pos = pos
    """ % (font_families, font_sizes)
    
    try:
        f = open("%s.cfg" % DIRECTORY, "w")
    except IOError:
        err("Error writing corpus config")
    print >> f, cfg
    
def write_header():
    header = """<?xml version="1.0" encoding="UTF-8"?>
<cesHeader creator="font-sensitive">
  <fileDesc>
    <titleStmt>
      <h.title>XCES-encoded version of font-sensitive corpus</h.title>
    </titleStmt>
    <sourceDesc>
      <biblStruct>
        <monogr></monogr>
            <title>test</title>
            <author>test</author>
      </biblStruct>
    </sourceDesc>
  </fileDesc>
</cesHeader>"""
    try:
        f = open("%s/header.xml" % SUBDIRECTORY, "w")
    except IOError:
        err("Error writing header")
    print >> f, header
    
    
def write_morph(morph):
    try:
        f = codecs.getwriter("utf-8")(open("%s/morph.xml" % SUBDIRECTORY, "w"))
    except IOError:
        err("Error writing morph")
    print >> f, morph
    

def parse_hOCR_file(f):
    """returns morph.xml in XCES format and two sets: one containing all font-families used and second all font sizes used in the document (both are needed to create corpus.cfg file)"""
    
    font_sizes, font_families = set([]), set([])
    morph_header = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE cesAna SYSTEM "xcesAnaIPI.dtd">
<cesAna xmlns:xlink="http://www.w3.org/1999/xlink" type="pre_morph" version="IPI-1.2">
<chunkList xml:base="text.xml">
<chunk type="wholedoc">\n"""
    morph_footer = "</chunk>\n</chunkList>\n</cesAna>"
    morph_word = """<tok>
<orth>%s</orth>
<lex disamb="1"><base></base><ctag>%s</ctag></lex>
</tok>"""
    morph_content = []
    try:
        dom = etree.parse(f)
    except:
        err("Error parsing XML")
        
    paragraphs = CSSSelector('p')(dom)
    for paragraph in paragraphs:
        morph_content.append('<chunk type="p">\n<chunk type="s">\n')
        style_spans = paragraph.getchildren()
        for style_span in style_spans:
            try:
                font_info = extract_font_info(style_span.attrib["style"], font_sizes, font_families)    
            except KeyError:
                err("Can`t find style info in XML file.")
            spans = style_span.getchildren()
            for span in spans:
                try:
                    if span.attrib["class"] == "ocrx_word" and span.text:
                        word = span.text.strip().replace('&', '&amp;')
                        if word:
                            morph_content.append(morph_word % (word, font_info))
                except KeyError:
                    pass
        morph_content.append('</chunk>\n</chunk>\n')
    
    return morph_header + "".join(morph_content) + morph_footer, font_families, font_sizes    

def main():
    try:
        filename = sys.argv[1]
    except IOError:
        err("input file not specified")
    global DIRECTORY
    DIRECTORY = "corpus" if len(sys.argv) < 3 else sys.argv[2]
    try:
        f = open(filename)
    except IOError:
        err("specified file doesn't exist")

    morph, font_families, font_sizes = parse_hOCR_file(f)
    create_directories()
    write_morph(morph)
    write_header()
    write_config(font_families, font_sizes)
    write_bp_config()
    os.system("bpng %s" % (DIRECTORY))

if __name__ == '__main__':
    main()
