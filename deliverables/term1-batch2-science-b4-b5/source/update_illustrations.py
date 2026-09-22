"""Embed reviewed standalone B4/B5 maps without rebuilding questions or answer keys."""
from pathlib import Path
import hashlib,json,argparse
from docx.shared import Inches
parser=argparse.ArgumentParser();parser.add_argument("--grade",type=int,choices=(4,5),default=4)
grade=parser.parse_args().grade
from docx import Document
from PIL import Image
ROOT=Path(__file__).resolve().parent.parent
folder=ROOT/f'files/B{grade}/Science'
book=folder/f'B{grade}_Science_Weekly_Lessons_W01-W12.docx'
doc=Document(book)
assert len(doc.inline_shapes)==12
before=[p.text for p in doc.paragraphs]
manifest=[]
for week,shape in enumerate(doc.inline_shapes,1):
    path=folder/'Mind-maps'/f'B{grade}_Science_Week_{week:02d}.png'
    image=Image.open(path);image.verify()
    w,h=Image.open(path).size
    rid=shape._inline.graphic.graphicData.pic.blipFill.blip.embed
    doc.part.related_parts[rid]._blob=path.read_bytes()
    shape.width=round(min(Inches(6.9), Inches(7)*w/h))
    shape.height=round(shape.width*h/w)
    manifest.append({'week':week,'path':str(path.relative_to(ROOT/'files')),'size':[w,h],'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
doc.save(book)
assert [p.text for p in Document(book).paragraphs]==before
(ROOT/'source'/('illustrated_maps.json' if grade==4 else 'illustrated_maps_b5.json')).write_text(json.dumps({'grade':grade,'subject':'Science','weeks':manifest,'status':'AI-generated illustrations with editorial corrections; teacher-review draft','provenance':('Week 1 approved preview; Weeks 2–11 generated for their topics; Week 12 composed from approved common-bean artwork.' if grade==4 else 'Weeks 1–10 generated for B5 topics; Week 11 reuses reviewed plant-parts artwork with B5 heading; Week 12 is the approved B5 bean/maize preview.'),'review':'All twelve visually inspected. No independent scientific sign-off.'},indent=2)+'\n')
print(f'Embedded 12 B{grade} illustrations; lesson/assessment paragraph text unchanged.')
