"""Build the downloadable CV from cv/index.html (requires lxml and reportlab)."""
from pathlib import Path
from html import escape

from lxml import html
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether

ROOT = Path(__file__).resolve().parents[1]
tree = html.parse(str(ROOT / 'cv/index.html'))
WIDTH = A4[0] - 84
styles = {
    'body': ParagraphStyle('body', fontName='Helvetica', fontSize=9, leading=12, spaceAfter=4),
    'small': ParagraphStyle('small', fontName='Helvetica', fontSize=8, leading=10),
    'heading': ParagraphStyle('heading', fontName='Helvetica-Bold', fontSize=12, leading=15, spaceBefore=12, spaceAfter=7, textColor=colors.HexColor('#183e50')),
    'name': ParagraphStyle('name', fontName='Helvetica-Bold', fontSize=23, leading=28, spaceAfter=7),
}

def text(element):
    return ' '.join(element.text_content().replace('🎉', '').split())

def p(value, style='body'):
    return Paragraph(escape(value), styles[style])

def section(key):
    return tree.xpath(f'//h3[@id="{key}"]/..')[0]

story = [p('YEONGHUN PARK', 'name'), p('Nursing Undergraduate | Chung-Ang University'),
         p('pjs12101113@cau.ac.kr | (+82)-10-4094-5719'),
         Paragraph('<link href="https://yh-pa-rk.github.io/portfolio/">yh-pa-rk.github.io/portfolio/</link>', styles['body'])]

def heading(key):
    story.append(p(text(section(key).find('h3')), 'heading'))

heading('interests')
story.append(p(text(section('interests').xpath('.//div[@class="cv-entry"]/div')[1])))

for key in ('education', 'experience'):
    heading(key)
    for entry in section(key).xpath('./div[contains(@class,"cv-entry")]'):
        for child in entry:
            if child.tag == 'ul':
                for li in child:
                    story.append(p('• ' + text(li)))
            elif child.xpath('.//strong'):
                story.append(Paragraph('<b>' + escape(text(child)) + '</b>', styles['body']))
            else:
                story.append(p(text(child)))

heading('clinical-practicum')
rows = [[p(text(c), 'small') for c in r] for r in section('clinical-practicum').xpath('.//tr')]
table = Table(rows, colWidths=[116, 168, 190 - 4.72, 42], repeatRows=1, hAlign='LEFT')
table.setStyle(TableStyle([
    ('VALIGN', (0,0), (-1,-1), 'TOP'), ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#edf2f5')),
    ('LINEBELOW',(0,0),(-1,0),0.5,colors.HexColor('#a9bac3')),
    ('LINEBELOW',(0,1),(-1,-1),0.3,colors.HexColor('#dbe2e6')),
    ('LEFTPADDING',(0,0),(-1,-1),5), ('RIGHTPADDING',(0,0),(-1,-1),5),
    ('TOPPADDING',(0,0),(-1,-1),5), ('BOTTOMPADDING',(0,0),(-1,-1),5),
]))
story.extend([table, Spacer(1,5), p(text(section('clinical-practicum').xpath('./p')[0]), 'small'), Spacer(1,6)])
for li in section('clinical-practicum').xpath('./ul/li'):
    story.append(p('• ' + text(li)))

story.append(PageBreak())
for key in ('awards', 'volunteer', 'certificates'):
    heading(key)
    if key == 'volunteer':
        for entry in section(key).xpath('./div[contains(@class,"cv-entry")]'):
            divs = entry.xpath('./div')
            title = text(divs[0]) + ' | ' + text(divs[1])
            details = [text(d) for d in divs[2:]] + [text(li) for li in entry.xpath('./ul/li')]
            story.append(KeepTogether([Paragraph('<b>' + escape(title) + '</b>', styles['body']), p(' '.join(details)), Spacer(1,3)]))
    else:
        rows = []
        for entry in section(key).xpath('./div[contains(@class,"cv-entry")]'):
            divs = entry.xpath('./div')
            if key == 'awards':
                values = [text(divs[0]), text(divs[2]).replace('Awarded in ', '').rstrip('.'), text(divs[1])]
            else:
                values = [text(divs[0]), text(divs[1]), text(divs[2])]
            rows.append([p(v, 'small') for v in values])
        table = Table(rows, colWidths=[220, 125, WIDTH-345], hAlign='LEFT')
        table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
        story.append(table)

def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor('#667780'))
    canvas.drawString(42, 25, 'Yeonghun Park | Curriculum Vitae')
    canvas.drawRightString(A4[0]-42, 25, str(doc.page))
    canvas.restoreState()

SimpleDocTemplate(str(ROOT / 'assets/pdf/yeonghun-park-cv.pdf'), pagesize=A4,
                  rightMargin=42, leftMargin=42, topMargin=32, bottomMargin=38,
                  title='Yeonghun Park — Curriculum Vitae', author='Yeonghun Park').build(story, onFirstPage=footer, onLaterPages=footer)
