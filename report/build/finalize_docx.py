"""Opens a .docx in headless LibreOffice, updates all fields/indexes (table of contents, page numbers),
saves it back as .docx and exports a PDF.  usage: python3 finalize_docx.py in.docx out.pdf"""
import os
import subprocess
import sys
import time

import uno
from com.sun.star.beans import PropertyValue

src = os.path.abspath(sys.argv[1])
pdf = os.path.abspath(sys.argv[2])


def prop(n, v):
    p = PropertyValue()
    p.Name, p.Value = n, v
    return p


proc = subprocess.Popen(
    ["soffice", "--headless", "--invisible", "--nologo", "--norestore", '--accept=socket,host=127.0.0.1,port=2083;urp;'],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
ctx = None
local = uno.getComponentContext()
resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
for _ in range(60):
    try:
        ctx = resolver.resolve("uno:socket,host=127.0.0.1,port=2083;urp;StarOffice.ComponentContext")
        break
    except Exception:
        time.sleep(0.5)
smgr = ctx.ServiceManager
desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
doc = desktop.loadComponentFromURL(uno.systemPathToFileUrl(src), "_blank", 0, (prop("Hidden", True),))
idx = doc.getDocumentIndexes()
for i in range(idx.getCount()):
    idx.getByIndex(i).update()
doc.getTextFields().refresh()
doc.storeToURL(uno.systemPathToFileUrl(src), (prop("FilterName", "MS Word 2007 XML"),))
doc.storeToURL(uno.systemPathToFileUrl(pdf), (prop("FilterName", "writer_pdf_Export"),))
doc.close(True)
try:
    desktop.terminate()
except Exception:
    pass
proc.wait(timeout=30)
print("updated", src, "->", pdf)
