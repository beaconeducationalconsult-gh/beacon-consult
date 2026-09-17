# --- resolve bare data filenames against data/ (see tools/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[2] / "tools"))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import json
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# Load the enriched lessons list
with open("computing_b9_lessons_enriched.json") as f:
    lessons = json.load(f)

print(f"Building Word Document for {len(lessons)} lessons...")

doc = Document()

# Set standard margins (1 inch on all sides)
for section in doc.sections:
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(1.0)
    section.right_margin = Inches(1.0)

# Colors
COLOR_NAVY = RGBColor(0, 32, 96)
COLOR_DARK_GRAY = RGBColor(64, 64, 64)
COLOR_BLACK = RGBColor(0, 0, 0)

# Function to add a horizontal rule/line
def add_horizontal_rule(paragraph, color_hex="D3D3D3", size="12"):
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), size)
    bottom.set(qn('w:space'), '4')
    bottom.set(qn('w:color'), color_hex)
    pBdr.append(bottom)
    paragraph._p.get_or_add_pPr().append(pBdr)

# Let's write the Title Page
title_p = doc.add_paragraph()
title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run_title = title_p.add_run("\n\n\n\n\nFULL-YEAR DAILY LESSON PLANS")
run_title.font.name = 'Calibri'
run_title.font.size = Pt(24)
run_title.font.bold = True
run_title.font.color.rgb = COLOR_NAVY

sub_p = doc.add_paragraph()
sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run_sub = sub_p.add_run("\nComputing\nBasic 9  ·  JHS 3")
run_sub.font.name = 'Calibri'
run_sub.font.size = Pt(18)
run_sub.font.bold = True
run_sub.font.color.rgb = COLOR_DARK_GRAY

meta_p = doc.add_paragraph()
meta_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run_meta = meta_p.add_run(
    "\n\n\n\n\nAligned with the\nNaCCA Standards-Based Curriculum (2019)\n\n"
    "180 daily lesson plans\n"
    "36 weeks × 5 days/week × 30 minutes/period\n"
    "3 Terms · GES/NaCCA Full Standard Lesson Plan Template\n"
    "Spiral pedagogy: each indicator across multiple sessions"
)
run_meta.font.name = 'Calibri'
run_meta.font.size = Pt(12)
run_meta.font.color.rgb = COLOR_DARK_GRAY

source_p = doc.add_paragraph()
source_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run_source = source_p.add_run("\n\n\n\nSource: National Council for Curriculum and Assessment (NaCCA)\nMinistry of Education, Republic of Ghana")
run_source.font.name = 'Calibri'
run_source.font.size = Pt(10)
run_source.font.italic = True
run_source.font.color.rgb = COLOR_DARK_GRAY

doc.add_page_break()

# Function to style a run with Calibri
def style_run(run, size_pt, bold=False, italic=False, color=COLOR_BLACK):
    run.font.name = 'Calibri'
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color

# Generate each of the 180 lessons
for idx, l in enumerate(lessons):
    lesson_num = l["lesson_num"]
    term = l["term"]
    week = l["week"]
    day = l["day"]
    
    # 1. Lesson Plan Header
    header_p = doc.add_paragraph()
    header_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    header_p.paragraph_format.space_before = Pt(0)
    header_p.paragraph_format.space_after = Pt(6)
    
    run_h = header_p.add_run(f"LESSON PLAN #{lesson_num}   ·   WEEK {week}   ·   {day.upper()}   ·   [{l['session_title']}]")
    style_run(run_h, 11, bold=True, color=COLOR_NAVY)
    
    # Add an elegant horizontal line below the header
    add_horizontal_rule(header_p, "002060", "18") # Navy blue line
    
    # 2. Identification Block
    id_p = doc.add_paragraph()
    id_p.paragraph_format.space_before = Pt(6)
    id_p.paragraph_format.space_after = Pt(4)
    id_p.paragraph_format.line_spacing = 1.15
    
    r = id_p.add_run("Week Ending: ")
    style_run(r, 10, bold=True)
    r = id_p.add_run("__________________    ")
    style_run(r, 10)
    
    r = id_p.add_run("Day / Date: ")
    style_run(r, 10, bold=True)
    r = id_p.add_run(f"{day}, __________________    ")
    style_run(r, 10)
    
    r = id_p.add_run("Subject: ")
    style_run(r, 10, bold=True)
    r = id_p.add_run("Integrated Science\n")
    style_run(r, 10)
    
    r = id_p.add_run("Class: ")
    style_run(r, 10, bold=True)
    r = id_p.add_run("Basic B9 (JHS 3)    ")
    style_run(r, 10)
    
    r = id_p.add_run("Class Size: ")
    style_run(r, 10, bold=True)
    r = id_p.add_run("_____    ")
    style_run(r, 10)
    
    r = id_p.add_run("Duration: ")
    style_run(r, 10, bold=True)
    r = id_p.add_run("30 minutes    ")
    style_run(r, 10)
    
    r = id_p.add_run("References: ")
    style_run(r, 10, bold=True)
    r = id_p.add_run(f"NaCCA Computing CCP Curriculum B9 (2021)\n")
    style_run(r, 10)
    
    r = id_p.add_run("Lesson No: ")
    style_run(r, 10, bold=True)
    r = id_p.add_run(f"{lesson_num} of 180  ·  Term {term}, Week {week}")
    style_run(r, 10)
    
    add_horizontal_rule(id_p, "D3D3D3", "6") # Thin gray line
    
    # 3. Curriculum Anchor Block
    anchor_p = doc.add_paragraph()
    anchor_p.paragraph_format.space_before = Pt(6)
    anchor_p.paragraph_format.space_after = Pt(6)
    anchor_p.paragraph_format.line_spacing = 1.15
    
    r = anchor_p.add_run("Strand: ")
    style_run(r, 10, bold=True)
    r = anchor_p.add_run(f"{l['strand_name']}\n")
    style_run(r, 10)
    
    r = anchor_p.add_run("Sub-Strand: ")
    style_run(r, 10, bold=True)
    r = anchor_p.add_run(f"{l['sub_strand']}\n")
    style_run(r, 10)
    
    r = anchor_p.add_run("Content Standard: ")
    style_run(r, 10, bold=True)
    r = anchor_p.add_run(f"{l['cs_code']} — {l['cs_desc']}\n")
    style_run(r, 10)
    
    r = anchor_p.add_run("Indicator: ")
    style_run(r, 10, bold=True)
    r = anchor_p.add_run(f"{l['ind_code']} — {l['ind_desc']}\n")
    style_run(r, 10)
    
    r = anchor_p.add_run("Session: ")
    style_run(r, 10, bold=True)
    r = anchor_p.add_run(f"{l['session_title']}\n")
    style_run(r, 10)
    
    r = anchor_p.add_run("Performance Indicator: ")
    style_run(r, 10, bold=True)
    r = anchor_p.add_run(f"{l['perf_indicator']}\n")
    style_run(r, 10)
    
    r = anchor_p.add_run("Core Competencies: ")
    style_run(r, 10, bold=True)
    r = anchor_p.add_run(f"{l['competencies']}\n")
    style_run(r, 10)
    
    r = anchor_p.add_run("Keywords: ")
    style_run(r, 10, bold=True)
    r = anchor_p.add_run(f"{l['keywords']}\n")
    style_run(r, 10)
    
    r = anchor_p.add_run("Teaching & Learning Resources (T/LR): ")
    style_run(r, 10, bold=True)
    r = anchor_p.add_run(f"{l['resources']}\n")
    style_run(r, 10)
    
    r = anchor_p.add_run("Relevant Previous Knowledge (RPK): ")
    style_run(r, 10, bold=True)
    r = anchor_p.add_run(f"{l['rpk']}")
    style_run(r, 10)
    
    add_horizontal_rule(anchor_p, "002060", "12") # Navy line
    
    # 4. Lesson Phases
    phases_h = doc.add_paragraph()
    phases_h.paragraph_format.space_before = Pt(8)
    phases_h.paragraph_format.space_after = Pt(4)
    r = phases_h.add_run("THREE-PHASE LESSON STRUCTURE")
    style_run(r, 11, bold=True, color=COLOR_NAVY)
    
    # Phase 1: Starter
    p1_p = doc.add_paragraph()
    p1_p.paragraph_format.space_before = Pt(4)
    p1_p.paragraph_format.space_after = Pt(4)
    r = p1_p.add_run("PHASE 1 — STARTER (Introduction)  ·  5 minutes")
    style_run(r, 10, bold=True, color=COLOR_DARK_GRAY)
    
    for s_act in l["starter"]:
        bullet_p = doc.add_paragraph(style='List Bullet')
        bullet_p.paragraph_format.space_before = Pt(0)
        bullet_p.paragraph_format.space_after = Pt(2)
        bullet_p.paragraph_format.left_indent = Inches(0.25)
        r = bullet_p.add_run(s_act)
        style_run(r, 10)
        
    # Phase 2: Main
    p2_p = doc.add_paragraph()
    p2_p.paragraph_format.space_before = Pt(6)
    p2_p.paragraph_format.space_after = Pt(4)
    r = p2_p.add_run("PHASE 2 — MAIN (New Learning / Practice)  ·  20 minutes")
    style_run(r, 10, bold=True, color=COLOR_DARK_GRAY)
    
    for m_act in l["main"]:
        bullet_p = doc.add_paragraph(style='List Bullet')
        bullet_p.paragraph_format.space_before = Pt(0)
        bullet_p.paragraph_format.space_after = Pt(2)
        bullet_p.paragraph_format.left_indent = Inches(0.25)
        r = bullet_p.add_run(m_act)
        style_run(r, 10)
        
    # Phase 3: Plenary
    p3_p = doc.add_paragraph()
    p3_p.paragraph_format.space_before = Pt(6)
    p3_p.paragraph_format.space_after = Pt(4)
    r = p3_p.add_run("PHASE 3 — PLENARY (Reflection & Closure)  ·  5 minutes")
    style_run(r, 10, bold=True, color=COLOR_DARK_GRAY)
    
    for p_act in l["plenary"]:
        bullet_p = doc.add_paragraph(style='List Bullet')
        bullet_p.paragraph_format.space_before = Pt(0)
        bullet_p.paragraph_format.space_after = Pt(2)
        bullet_p.paragraph_format.left_indent = Inches(0.25)
        r = bullet_p.add_run(p_act)
        style_run(r, 10)
        
    # 5. Assessment and Teacher's Reflection Block
    ass_p = doc.add_paragraph()
    ass_p.paragraph_format.space_before = Pt(6)
    ass_p.paragraph_format.space_after = Pt(4)
    
    r = ass_p.add_run("Assessment: ")
    style_run(r, 10, bold=True)
    r = ass_p.add_run(f"{l['assessment']}\n")
    style_run(r, 10)
    
    r = ass_p.add_run("Teacher's Reflection (complete after lesson):\n")
    style_run(r, 10, bold=True, color=COLOR_NAVY)
    
    reflections = [
        "How many learners achieved the performance indicator? ________________________",
        "Which learners need additional support? ______________________________________",
        "What worked well in this lesson? ____________________________________________",
        "What will I do differently next time? ________________________________________"
    ]
    for ref in reflections:
        ref_p = doc.add_paragraph(style='List Bullet')
        ref_p.paragraph_format.space_before = Pt(0)
        ref_p.paragraph_format.space_after = Pt(2)
        ref_p.paragraph_format.left_indent = Inches(0.25)
        r = ref_p.add_run(ref)
        style_run(r, 9, italic=True)
        
    # 6. Sign-off and Vetting block
    sign_p = doc.add_paragraph()
    sign_p.paragraph_format.space_before = Pt(10)
    sign_p.paragraph_format.space_after = Pt(0)
    
    r = sign_p.add_run("Teacher's Signature: ")
    style_run(r, 9, bold=True)
    r = sign_p.add_run("________________________    ")
    style_run(r, 9)
    
    r = sign_p.add_run("Vetted by (HoD): ")
    style_run(r, 9, bold=True)
    r = sign_p.add_run("________________________    ")
    style_run(r, 9)
    
    r = sign_p.add_run("Date: ")
    style_run(r, 9, bold=True)
    r = sign_p.add_run("____________")
    style_run(r, 9)
    
    # Page Break after each lesson, except the very last one
    if idx < len(lessons) - 1:
        doc.add_page_break()

# Save the final compiled DOCX
output_path = "Basic9_Computing_Lesson_Plans_Full_Year.docx"
doc.save(output_path)
print(f"Successfully generated full year's daily lesson plans Word Document: {output_path}")
