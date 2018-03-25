import sqlite3
import os, errno, time

import sys
import papyrus_pb2
import cairocffi
import math
import shutil

from PIL import Image

reload(sys)
sys.setdefaultencoding('utf8')

# This is a quick fix to check whether we can use pyPdf (depreciated) or PyPDF2
import pip
installed_packages = pip.get_installed_distributions()
flat_installed_packages = [package.project_name for package in installed_packages]

if 'PyPDF2' in flat_installed_packages:
    from PyPDF2 import PdfFileWriter, PdfFileReader
elif 'pyPdf' in flat_installed_packages:
    from PyPDF2 import PdfFileWriter, PdfFileReader

class color:
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'


DEBUG=False
base_directory = "./"
if len(sys.argv) == 2:
    base_directory = sys.argv[1]

conn = sqlite3.connect(base_directory+'papyrus.db')

c = conn.cursor()

def makedir(directory):
    try:
        os.makedirs(directory)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

def titlesafe(title):
    if title is None or title == "":
        return "Untitled Note"
    return title

def dirsafe(name):
    name = name.replace("/","_")
    name = name.replace(" ","_")
    return name

def getNotes(uuid):
    c.execute('SELECT uuid, name, created, modified, starred, unfiled, ui_mode, current_page, password, version FROM notes WHERE uuid IN ' +
    '(SELECT note_uuid FROM notebook_note_association WHERE notebook_uuid=?)', (uuid, ))
    return c.fetchall()

def getPages(uuid):
    c.execute('SELECT uuid, note_uuid, created, modified, page_num, offset_x, offset_y, zoom, fit_mode, doc_hash ' +
    'FROM pages WHERE note_uuid = ?', (uuid, ))
    return c.fetchall()

DPI = 72 # defined by cairocffi
def cm_to_point(cm):
    return cm / 2.54 * DPI

def u32_to_4f(u):
    return [((u>>24) & 0xFF) / 255.0, ((u>>16) & 0xFF) / 255.0, ((u>>8) & 0xFF) / 255.0, (u & 0xFF) / 255.0]

def convert_page(path, note_name, notebook_path, directory, pdf_file, page_number):
    page = papyrus_pb2.Page()
    # Open and parse papyrus page using protobuf
    page.ParseFromString(open(path, 'rb').read())
    # Create a new pdf surface for drawing

    if page.background.width == 0 and page.background.height == 0:
        print("\tInfinite page!")

        max_x = 0
        max_y = 0

        for item in page.layer.item:
            bounds = None
            if item.type == papyrus_pb2.Item.Type.Value('Stroke'):
                bounds = item.stroke.bounds
            elif item.type == papyrus_pb2.Item.Type.Value('Shape'):
                if item.shape.type == 'Ellipse':
                    bounds = item.shape.ellipse.bounds
            elif item.type == papyrus_pb2.Item.Type.Value('Text'):
                bounds = item.text.bounds
            else:
                print(item)

            if bounds is not None:
                if bounds.right > max_x:
                    max_x = bounds.right

                if bounds.bottom > max_y:
                    max_y = bounds.bottom


        page.background.width = max_x + 1
        page.background.height = max_y + 1

    note_name = titlesafe(note_name)
    print("\t%s" % note_name)

    note_path = directory + '/' + notebook_path + '/' + dirsafe(note_name)
    new_note_path = note_path
    num = 1;

    #while os.path.exists(new_note_path):
    #    new_note_path = note_path + '(' + str(num) + ')'
    #    num += 1

    makedir(note_path)

    note_path = new_note_path

    pdfpath = note_path + '/pdf'
    makedir(pdfpath)

    pdffile = pdfpath + '/page' + str(page_number) +'.pdf'
    print("\tSource: %s\n\tOutput: %s" % (path, pdffile))

    pdf_out = open(pdffile, 'w')
    surface = cairocffi.PDFSurface(pdf_out, cm_to_point(page.background.width), cm_to_point(page.background.height))
    context = cairocffi.Context(surface)

    # Paint the page white
    context.set_source_rgba(0, 0, 0, 0)
    context.paint()


    for item in page.layer.item:
        if item.type == papyrus_pb2.Item.Type.Value('Stroke'):
            context.save()
            # Translate to reference_point (stroke origin)
            context.translate(cm_to_point(item.stroke.reference_point.x), cm_to_point(item.stroke.reference_point.y))
            # Set source color
            argb = u32_to_4f(item.stroke.color)
            context.set_source_rgba(argb[1], argb[2], argb[3], argb[0])
            # Set line width
            width = cm_to_point(item.stroke.weight)
            # Other parameter
            context.set_line_join(cairocffi.LINE_JOIN_ROUND)
            context.set_line_cap(cairocffi.LINE_CAP_ROUND)
            context.move_to(0,0)

            if item.stroke.stroke_type == papyrus_pb2.Stroke.Highlight:
                context.push_group()
                context.set_source_rgba(argb[1], argb[2], argb[3], 1)
                context.fill_preserve()
                context.set_line_cap(cairocffi.LINE_CAP_SQUARE)

            for point in item.stroke.point:
                context.line_to(cm_to_point(point.x), cm_to_point(point.y))
                if item.stroke.stroke_type == papyrus_pb2.Stroke.Highlight:
                    context.set_line_width(width)
                    #context.
                elif point.HasField('pressure'):
                    context.set_line_width(width * point.pressure)
                else:
                    context.set_line_width(width)
                context.stroke()
                context.move_to(cm_to_point(point.x), cm_to_point(point.y))
            if item.stroke.stroke_type == papyrus_pb2.Stroke.Highlight:
                context.pop_group_to_source()
                context.paint_with_alpha(argb[0])
            context.restore()
        elif item.type == papyrus_pb2.Item.Type.Value('Shape') and item.shape.ellipse is not None:
            width = item.shape.ellipse.weight * 0.3

            context.save()
            context.new_sub_path()
            context.translate(cm_to_point(item.shape.ellipse.center_x), cm_to_point(item.shape.ellipse.center_y))
            context.set_line_width(item.shape.ellipse.weight)
            argb = u32_to_4f(item.shape.ellipse.color)
            context.set_line_width(width)
            context.set_source_rgba(argb[1], argb[2], argb[3], argb[0])
            context.scale(cm_to_point(item.shape.ellipse.radius_x), cm_to_point(item.shape.ellipse.radius_y))
            context.arc(0, 0, 1, (item.shape.ellipse.start_angle / 360) * 2 * math.pi, (item.shape.ellipse.sweep_angle / 360) * 2 * math.pi)
            context.close_path()
            context.stroke()
            context.restore()
        elif item.type == papyrus_pb2.Item.Type.Value('Text'):
            context.save()
            context.set_font_size(item.text.weight)

            # Color
            argb = u32_to_4f(item.text.color)
            context.set_source_rgba(argb[1], argb[2], argb[3], argb[0])

            context.move_to(cm_to_point(item.text.bounds.left), cm_to_point(item.text.bounds.top))
            tw = int(item.text.weight)
            size_m = cairocffi.Matrix(tw,0,0,tw,0,0)
            scaledFont = cairocffi.ScaledFont(cairocffi.ToyFontFace("sans-serif"), size_m)
            glyphs = scaledFont.text_to_glyphs(cm_to_point(item.text.bounds.left), cm_to_point(item.text.bounds.bottom), item.text.text, False)
            context.show_glyphs(glyphs)
            context.restore()

        elif item.type == papyrus_pb2.Item.Type.Value('Image'):
            if(DEBUG):
                print("Got an image!")
                print(item.image.image_hash)

            # Convert JPEG image to PNG
            im = Image.open(base_directory+"data/imgs/" + item.image.image_hash)
            im = im.crop((item.image.crop_bounds.left, item.image.crop_bounds.top, item.image.crop_bounds.right, item.image.crop_bounds.bottom))
            im.save(base_directory+"data/imgs/" + item.image.image_hash + ".png", "PNG")
            im.close()

            matrix = cairocffi.Matrix()

            scale_x = cm_to_point(item.image.bounds.right-item.image.bounds.left)/(item.image.crop_bounds.right-item.image.crop_bounds.left)
            scale_y = cm_to_point(item.image.bounds.bottom-item.image.bounds.top)/(item.image.crop_bounds.bottom-item.image.crop_bounds.top)

            if(DEBUG):
                print("Scale X: %d" % (1/scale_x))
                print("Scale Y: %d" % (1/scale_y))
                print("Translate: %d" % cm_to_point(item.image.bounds.left))
            matrix.scale(1/scale_x, 1/scale_y)
            matrix.translate(-cm_to_point(item.image.bounds.left), -cm_to_point(item.image.bounds.top))

            im_surface = cairocffi.ImageSurface.create_from_png(base_directory+"./data/imgs/" + item.image.image_hash + ".png")
            im_surface_pattern = cairocffi.SurfacePattern(im_surface)

            im_surface_pattern.set_filter(cairocffi.FILTER_GOOD)
            im_surface_pattern.set_matrix(matrix)

            context.save()
            context.set_source(im_surface_pattern)
            context.rectangle(cm_to_point(item.image.bounds.left), cm_to_point(item.image.bounds.top), cm_to_point(item.image.bounds.right-item.image.bounds.left), cm_to_point(item.image.bounds.bottom-item.image.bounds.top))
            context.fill()
            context.restore()
        else:
            print(item)
            print("Item of type {} not supported".format(papyrus_pb2.Item.Type.Name(item.type)))
    surface.flush()
    surface.finish()
    pdf_out.close()

    if page.background.HasField("pdf_background"):

        try:
            output_file = PdfFileWriter()
            input_file = PdfFileReader(file(pdffile, "rb"))
            pdf_file = PdfFileReader(file(base_directory+"data/docs/" + pdf_file, "rb"))
            pdf_page = pdf_file.getPage(page.background.pdf_background.page_number)

            input_page = input_file.getPage(0)
            pdf_page.mergePage(input_page)

            output_file.addPage(pdf_page)

            with open(pdffile+".tmp", "wb") as outputStream:
                output_file.write(outputStream)
            os.rename(pdffile+".tmp", pdffile)
        except:
            print("\t%sUnable to merge PDFs - maybe the PDF was malformed? Result was %s%s" % (color.RED, sys.exc_info()[0], color.END))
    print("")
    return pdffile

print('Your Papyrus App contains the following notebooks:')

c.execute('SELECT _id, uuid, name, created, modified FROM notebooks ORDER BY name')
notebooks = c.fetchall()
for i in notebooks:
    print("-", i[2])

directory = base_directory+'exported'
makedir(directory)

#directory = directory + time.strftime("%Y-%m-%d")
#makedir(directory)

for i in notebooks:
    makedir(directory + "/" + dirsafe(i[2]))

    notes = getNotes(i[1])

    for j in notes:
        print("%s%-50s%s (%s)" % (color.BOLD, titlesafe(j[1]), color.END,j[0]))
        # Associated PDF file
        pdfFile=None

        # Checks for an associated PDF file
        c.execute('SELECT hash FROM documents WHERE note_uuid= ?', (j[0],))
        result = c.fetchone()
        if result is not None:
            print("\tThis note has this associated document: %s" % (result))
            pdfFile = result[0]
        pages = getPages(j[0])

        count = 1
        files = []
        for k in pages:
            print("\tProcessing page %d/%d of %s" % (count, len(pages), j[1]))
            files.append(convert_page(base_directory+'data/pages/' + k[0] + '.page', j[1], dirsafe(i[2]), directory, pdfFile, count))
            count += 1;

        # Merge pages
        output_file = PdfFileWriter()
        for k in files:
            input_file = PdfFileReader(file(k, "rb")).getPage(0)
            output_file.addPage(input_file)
        final_pdf = directory + "/" + dirsafe(i[2]) + "/" + dirsafe(titlesafe(j[1])) + ".pdf"
        with open(final_pdf, "wb") as outputStream:
            output_file.write(outputStream)
        try:
            shutil.rmtree(directory + "/" + dirsafe(i[2]) + "/" + dirsafe(titlesafe(j[1])))
        except:
            ""

        unix_ts = int(j[3]/1000)

        os.utime(final_pdf, (unix_ts,unix_ts))
