#!/usr/bin/env python
#encoding: utf-8
import sys, os, shutil, string, codecs, re, glob
from lxml import etree
from lxml.cssselect import CSSSelector

def err(msg):
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
    
def create_directories(n):
    try:
        shutil.rmtree(DIRECTORY)
    except OSError:
        pass
    os.mkdir(DIRECTORY)
    os.chdir(DIRECTORY)
    for i in xrange(n):
        try:
            os.mkdir(SUBDIRECTORY + str(i))
        except OSError:
            err("Couldn`t create directory.")
    os.chdir('..')
        
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
        f = open("%s/%s.bp.conf" % (DIRECTORY, DIRECTORY), "w")
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
        f = open("%s/%s.cfg" % (DIRECTORY, DIRECTORY), "w")
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
        f = open("%s/%s/header.xml" % (DIRECTORY, SUBDIRECTORY), "w")
    except IOError:
        err("Error writing to header.xml file.")
    print >> f, header

def parse_hOCR_file(f, font_families, font_sizes):
    """returns morph.xml in XCES format and two sets: one containing all font-families used and second all font sizes used in the document (both are needed to create corpus.cfg file)"""
    
    morph_header = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE cesAna SYSTEM "xcesAnaIPI.dtd">
<cesAna xmlns:xlink="http://www.w3.org/1999/xlink" type="pre_morph" version="IPI-1.2">
<chunkList xml:base="text.xml">
<chunk type="wholedoc">"""
    morph_footer = "</chunk>\n</chunkList>\n</cesAna>"
    morph_word = """<tok>
<orth>%s</orth>
<lex disamb="1"><base></base><ctag>%s</ctag></lex>
</tok>"""
    try:
        out = codecs.getwriter("utf-8")(open("%s/%s/morph.xml" % (DIRECTORY, SUBDIRECTORY), "w"))
    except IOError:
        err("Error writing to morph.xml file.")

    try:
        dom = etree.parse(f)
    except:
        err("Error parsing XML")
    
    print >> out, morph_header
    lines = CSSSelector('span.ocr_line')(dom)
    for line in lines:
        print >> out, '<chunk type="p">\n<chunk type="s">'
        for style_span in line.getchildren():
            try:
                font_info = extract_font_info(style_span.attrib["style"], font_sizes, font_families)    
            except (IndexError, KeyError):
                continue
            for outer_span in style_span.getchildren():
                if outer_span.attrib["class"] in ['ocrx_word'] and outer_span.text:
                    word = outer_span.text.strip().replace('&', '&amp;')
                    if word:
                        print >> out, morph_word % (word, font_info)
                for span in outer_span.getchildren():
                    if span.attrib["class"] in ['ocrx_word'] and span.text:
                        word = span.text.strip().replace('&', '&amp;')
                        if word:
                            print >> out, morph_word % (word, font_info)
        print >> out, '</chunk>\n</chunk>'
    print >> out, morph_footer

def main():
    global DIRECTORY
    global SUBDIRECTORY
    SUBDIRECTORY = 'data'
    try:
        DIRECTORY = sys.argv[1]
    except IndexError:
        err('Corpus basename not specified.')
    filenames = sys.argv[2:]
    if not filenames:
        err('No input files specified.')
    create_directories(len(filenames))
    
    font_families, font_sizes = set(), set()
    #builds XCES files for all hOCR files
    for i, filename in enumerate(filenames):
        SUBDIRECTORY = 'data' + str(i)
        try:
            f = open(filename)
        except:
            err('Input file %s not found.' % filename)
        parse_hOCR_file(f, font_families, font_sizes)
        write_header()
    
    write_config(font_families, font_sizes)
    write_bp_config()
    os.chdir(DIRECTORY)
    #uses bpng to build a corpus out of built files
    os.system("bpng %s" % (DIRECTORY))
    
if __name__ == '__main__':
    main()
