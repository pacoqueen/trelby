import pml
import util

# users should only use this.
def generate(doc):
    tmp = PDFExporter()
    return tmp.generate(doc)
    
class PDFExporter:
    def __init__(self):
        pass

    # generate PDF document from doc, which is a pml.Document. returns a
    # string containing the PDF data.
    def generate(self, doc):
        self.doc = doc
        
        # the stupid 'f' thingy in the xref table is an object of some
        # kind or something...
        self.objectCnt = 1
        
        self.data = util.String()
        self.xref = util.String()

        pages = len(doc.pages)

        # object numbers for various things
        catalogNr = 1
        pagesNr = catalogNr + 1
        firstPageNr = pagesNr + 1
        lastPageNr = firstPageNr + pages * 2 - 1
        firstFontNr = lastPageNr + 1

        kids = "["
        for i in range(firstPageNr, lastPageNr, 2):
            kids += "%d 0 R\n" % i
        kids += "]"
        
        self.addXref(65535, "f")
        self.data += "%PDF-1.4\n"
        
        self.addObj("<< /Type /Catalog\n"
                    "/Pages %d 0 R\n"
                    ">>" % pagesNr)

        self.addObj("<< /Type /Pages\n"
                    "/Kids %s\n"
                    "/Count %d\n"
                    "/MediaBox [0 0 %f %f]\n"
                    "/Resources << /Font <<\n"
                    "/F0 %d 0 R /F1 %d 0 R /F2 %d 0 R /F3 %d 0 R >> >>\n"
                    ">>" % (kids, pages, self.mm2points(doc.w),
                            self.mm2points(doc.h),
                            firstFontNr,
                            firstFontNr + 1,
                            firstFontNr + 2,
                            firstFontNr + 3))

        for i in range(pages):
            self.addObj("<< /Type /Page\n"
                        "/Parent %d 0 R\n"
                        "/Contents %d 0 R\n"
                        ">>" % (pagesNr, firstPageNr + i * 2 + 1))

            pg = doc.pages[i]

            cont = util.String()

            currentFont = ""

            for op in pg.ops:
                if op.type == pml.OP_TEXT:

                    s = op.text.replace("\\", "\\\\").replace("(", "\\(").\
                        replace(")", "\\)")

                    # we need to adjust y position since PDF uses baseline
                    # of text as the y pos, but pml uses top of the text
                    # as y pos. The Adobe standard Courier family font
                    # metrics give 157 units in 1/1000 point units as the
                    # Descender value, thus giving (1000 - 157) = 843
                    # units from baseline to top of text.
                    
                    # http://partners.adobe.com/asn/tech/type/ftechnotes.jsp
                    # contains the "Font Metrics for PDF Core 14 Fonts"
                    # document.
                    
                    x = self.x(op.x)
                    y = self.y(op.y) - 0.843 * op.size

                    newFont = "F%d %d" % (op.flags & 3, op.size)
                    if newFont != currentFont:
                        cont += "/%s Tf\n" % newFont
                        currentFont = newFont
                    
                    cont += "BT\n"\
                            "%f %f Td\n"\
                            "(%s) Tj\n"\
                            "ET\n" % (x, y, s)

                    if op.flags & pml.UNDERLINED:

                        # AFM says Courier fonts have a width of 600 units
                        ch_x = 0.6 * op.size

                        # AFM says Courier has the underline line 100
                        # units below baseline with a thickness of 50
                        undY = y - 0.1 * op.size
                        undLen = len(op.text) * ch_x

                        cont += "%f w\n"\
                                "%f %f m\n"\
                                "%f %f l\n"\
                                "S\n" % (0.05 * op.size, x, undY,
                                         x + undLen, undY)
                    
                elif op.type == pml.OP_LINE:
                    p = op.points
                    
                    pc = len(p)

                    if pc < 2:
                        print "LineOp contains only %d points" % pc

                        continue

                    cont += "%f w\n"\
                            "%s m\n" % (self.mm2points(op.width),
                                        self.xy(p[0]))

                    for i in range(1, pc):
                        cont += "%s l\n" % (self.xy(p[i]))

                    if op.isClosed:
                        cont += "s\n"
                    else:
                        cont += "S\n"
                    
                elif op.type == pml.OP_RECT:
                    if op.lw != -1:
                        cont += "%f w\n" % self.mm2points(op.lw)

                    cont += "%f %f %f %f re\n" % (
                        self.x(op.x),
                        self.y(op.y) - self.mm2points(op.height),
                        self.mm2points(op.width), self.mm2points(op.height))

                    if op.isFilled:
                        cont += "f\n"
                    else:
                        cont += "S\n"

                elif op.type == pml.OP_PDF:
                    cont += "%s\n" % op.cmds
                    
                else:
                    print "unknown op type %d" % op.type

            self.addStream(str(cont))

        for s in ["", "-Bold", "-Oblique", "-BoldOblique"]:
            self.addObj("<< /Type /Font\n"
                        "/Subtype /Type1\n"
                        "/BaseFont /Courier%s\n"
                        "/Encoding /WinAnsiEncoding\n"
                        ">>" % s)

        xrefPos = self.data.getPos()

        self.data += "xref\n0 %d\n" % (self.objectCnt)
        self.data += str(self.xref) + "\n"

        self.data += "trailer\n<< /Size %d\n/Root %d 0 R\n>>\n"\
                     % (self.objectCnt, catalogNr)
            
        self.data += "startxref\n%d\n%%%%EOF\n" % (xrefPos)

        self.doc = None
        
        return str(self.data)

    # add new stream. 's' is all data between 'stream/endstream' tags,
    # excluding newlines.
    def addStream(self, s):
        compress = True

        filter = " "
        if compress:
            prev = len(s)
            s = s.encode("zlib")
            new = len(s)
            filter = "\n/Filter /FlateDecode "
        
        self.addObj("<< /Length %d%s>>\n"
                    "stream\n"
                    "%s\n"
                    "endstream" % (len(s), filter, s))
        
    # add new object. 's' is all data between 'obj/endobj' tags, excluding
    # newlines. adds an xref for the object also.
    def addObj(self, s):
        self.addXref()
        self.data += "%d 0 obj\n%s\nendobj\n" % (self.objectCnt, s)
        self.objectCnt += 1
        
    # add a reference to the xref table, using generation 'gen' and type
    # 'typ'.
    def addXref(self, gen = 0, typ = "n"):
        self.xref += "%010d %05d %s \n" % (self.data.getPos(), gen, typ)

    # convert mm to points (1/72 inch).
    def mm2points(self, mm):
        # 2.834 = 72 / 25.4
        return mm * 2.83464567

    # convert x coordinate
    def x(self, x):
        return self.mm2points(x)

    # convert y coordinate
    def y(self, y):
        return self.mm2points(self.doc.h - y)

    # convert xy, which is (x, y) pair, into PDF coordinates, and format
    # it as "%f %f", and return that.
    def xy(self, xy):
        x = self.x(xy[0])
        y = self.y(xy[1])

        return "%f %f" % (x, y)