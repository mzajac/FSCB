#!/usr/bin/env python
import sys, os, shutil, string, codecs, re
from xml.dom import minidom

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
    """
    try:
        f = open("%s.bp.conf" % DIRECTORY, "w")
    except IOError:
        err("Error writing corpus builder config")
    print >> f, bp_cfg

def write_config(font_families, font_sizes):
    font_families_string, font_sizes_string = "font-family =", "font-size ="
    for font_family in font_families:
        font_families_string += " %s" % font_family
    for font_size in font_sizes:
        font_sizes_string += " %s" % font_size
    
    cfg = """[attr]
font-style = italic straight
font-weight = bold normal
%s
%s

[pos]
font = font-style font-weight font-family font-size
interp =

[named-entity]
entity-orth = orth
entity-base = base
entity-tag = tag
entity-pos = pos
    """ % (font_families_string, font_sizes_string)
    
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
        #f = open("%s/morph.xml" % SUBDIRECTORY, "w")
    except IOError:
        err("Error writing morph")
    print >> f, morph
    

#returns morph.xml in XCES format and two sets: one containing all font-families used and second all font sizes used in the document (both are needed to create corpus.cfg file)
def parse_hOCR_file(f):
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
    morph_interp = """<tok>
<orth>%s</orth>
<lex disamb="1"><base></base><ctag>interp</ctag></lex>
</tok>
"""
    morph_content = ""
    try:
        dom = minidom.parse(f)
    except:
        err("Error parsing XML")
    paragraphs = dom.getElementsByTagName("p")
    for paragraph in paragraphs:
        morph_content += '<chunk type="p">\n'
        spans = paragraph.getElementsByTagName("span")
        line_ended = True
        for span in spans:
            if len(span.childNodes) == 1:
                #contains text
                line = span.childNodes[0].nodeValue
                words = string.split(line)
                font_info = extract_font_info(span.attributes["style"].value, font_sizes, font_families)
               
                if line_ended:
                    morph_content += '<chunk type="s">\n'
               
                for word in words:
                    #word may contain punctuation at the beginning and end
                        while word and word[0] in string.punctuation:
                            morph_content += morph_interp % word[0]
                            word = word[1:]
                        temporary_content = ""
                        while word and word[-1] in string.punctuation:
                            temporary_content += morph_interp % word[-1]
                            word = word[:-1]
                        if word:
                            morph_content += morph_word % (word, font_info)
                        morph_content += temporary_content
                
                if line[-1] == '.':
                    #sentence ends
                    morph_content += '</chunk>\n'
                    line_ended = True
                else:
                    line_ended = False
        if not line_ended:
            morph_content += '</chunk>\n'
        morph_content += '</chunk>\n'
    
    return morph_header + morph_content + morph_footer, font_families, font_sizes

def main():
    try:
        filename = sys.argv[1]
    except:
        err("input file not specified")
    global DIRECTORY
    DIRECTORY = "corpus" if len(sys.argv) < 3 else sys.argv[2]
    try:
        f = open(filename)
    except:
        err("specified file doesn't exist")

    #reads first line which contains encoding "utf8" instead of "utf-8" and causes the parser to crash
    f.readline()

    morph, font_families, font_sizes = parse_hOCR_file(f)
    create_directories()
    write_morph(morph)
    write_header()
    write_config(font_families, font_sizes)
    write_bp_config()
    os.system("bpng %s" % (DIRECTORY))

def tests():
    print extract_font_info("font-family: TimesNewRoman; font-size: 12pt; font-weight: bold; font-style: italic", set([]), set([]))
    print extract_font_info("font-family: TimesNewRoman; font-size: 9.2pt;", set([]), set([]))

main()
#tests()
