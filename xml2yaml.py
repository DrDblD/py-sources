import yaml
import sys
from lxml import etree

def parseXml(filepath):
    def elem2dict(node):
        """
        Convert an lxml.etree node tree into a dict.
        """
        d = {}
        for e in node.getchildren():
            if type(d)==type({}):
                if d.get(e.tag):
                    d = [d[e.tag]]
                else:
                    d[e.tag] = e.text if e.text else elem2dict(e)
            else:
                d += [e.text if e.text else elem2dict(e)]
        if d == {}: d=None
        return d
    
    parser = etree.XMLParser(remove_blank_text=True,remove_comments=True)
    tree = etree.parse(filepath,parser)
    datadict = elem2dict(tree.getroot())
    return datadict

args = sys.argv
datadict = parseXml(args[1] if len(args) > 1 else input('path:\t'))
# print(datadict)
print(yaml.safe_dump(datadict))