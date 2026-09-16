from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.style import WD_STYLE_TYPE
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import textwrap

OUT = Path('/Users/mac/projects/poker_protocol/paper')
OUT.mkdir(parents=True, exist_ok=True)
ASSET = OUT / 'figures'
ASSET.mkdir(exist_ok=True)

NAVY = '17365D'
BLUE = '2F75B5'
LIGHT = 'EAF2F8'
PALE = 'F6F8FB'
MID = 'D9E2F3'
GRAY = '666666'
BLACK = '000000'

def set_cell_shading(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = tcPr.find(qn('w:shd'))
    if shd is None:
        shd = OxmlElement('w:shd'); tcPr.append(shd)
    shd.set(qn('w:fill'), fill)

def set_cell_margins(cell, top=100, start=120, bottom=100, end=120):
    tc = cell._tc; tcPr = tc.get_or_add_tcPr()
    tcMar = tcPr.first_child_found_in('w:tcMar')
    if tcMar is None:
        tcMar = OxmlElement('w:tcMar'); tcPr.append(tcMar)
    for m, v in [('top',top),('start',start),('bottom',bottom),('end',end)]:
        node = tcMar.find(qn('w:'+m))
        if node is None: node = OxmlElement('w:'+m); tcMar.append(node)
        node.set(qn('w:w'), str(v)); node.set(qn('w:type'), 'dxa')

def set_cell_border(cell, color='D9D9D9', sz='6'):
    tc = cell._tc; tcPr = tc.get_or_add_tcPr()
    borders = tcPr.first_child_found_in('w:tcBorders')
    if borders is None:
        borders = OxmlElement('w:tcBorders'); tcPr.append(borders)
    for edge in ('top','left','bottom','right','insideH','insideV'):
        tag = 'w:'+edge; el = borders.find(qn(tag))
        if el is None: el = OxmlElement(tag); borders.append(el)
        el.set(qn('w:val'),'single'); el.set(qn('w:sz'),sz); el.set(qn('w:space'),'0'); el.set(qn('w:color'),color)

def set_repeat_table_header(row):
    trPr = row._tr.get_or_add_trPr(); tblHeader = OxmlElement('w:tblHeader'); tblHeader.set(qn('w:val'),'true'); trPr.append(tblHeader)

def set_row_cant_split(row):
    trPr = row._tr.get_or_add_trPr()
    cant_split = trPr.find(qn('w:cantSplit'))
    if cant_split is None:
        cant_split = OxmlElement('w:cantSplit')
        trPr.append(cant_split)

def add_page_field(paragraph):
    run = paragraph.add_run()
    fldChar1 = OxmlElement('w:fldChar'); fldChar1.set(qn('w:fldCharType'), 'begin')
    instrText = OxmlElement('w:instrText'); instrText.set(qn('xml:space'), 'preserve'); instrText.text = ' PAGE '
    fldChar2 = OxmlElement('w:fldChar'); fldChar2.set(qn('w:fldCharType'), 'end')
    run._r.extend([fldChar1, instrText, fldChar2])

def add_hyperlink(paragraph, text, url):
    part = paragraph.part; r_id = part.relate_to(url, 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink', is_external=True)
    hyperlink = OxmlElement('w:hyperlink'); hyperlink.set(qn('r:id'), r_id)
    new_run = OxmlElement('w:r'); rPr = OxmlElement('w:rPr')
    color = OxmlElement('w:color'); color.set(qn('w:val'), BLUE); rPr.append(color)
    u = OxmlElement('w:u'); u.set(qn('w:val'), 'single'); rPr.append(u)
    new_run.append(rPr); t = OxmlElement('w:t'); t.text = text; new_run.append(t); hyperlink.append(new_run)
    paragraph._p.append(hyperlink)

def draw_text(draw, xy, text, font, fill=BLACK, max_width=520, line_gap=6, anchor='la'):
    words = text.split(); lines=[]; cur=''
    for w in words:
        test = (cur+' '+w).strip()
        if draw.textlength(test, font=font) <= max_width: cur=test
        else:
            if cur: lines.append(cur)
            cur=w
    if cur: lines.append(cur)
    y=xy[1]
    for line in lines:
        draw.text((xy[0],y),line,font=font,fill=fill,anchor=anchor)
        y += font.size + line_gap
    return y

def make_figures():
    try:
        font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 28)
        small = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 22)
        bold = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 30)
    except Exception:
        font = small = bold = ImageFont.load_default()
    # Figure 1
    im = Image.new('RGB',(1800,900),'white'); d=ImageDraw.Draw(im)
    d.text((900,50),'Reconstruction protocol at a glance',font=bold,fill='#'+NAVY,anchor='ma')
    boxes=[(70,220,370,470,'Authenticated\nstate','canonical deck • residual\nlineage • epoch digest'),(470,220,770,470,'Prover','carrier links\nslot contributions\nhidden permutation'),(870,220,1170,470,'Verifier','statement checks\nBG proof • OR proofs\ntranscript binding'),(1270,220,1570,470,'Aggregate','homomorphic sum\naccepted submitters\nnext encrypted deck')]
    for x1,y1,x2,y2,title,sub in boxes:
        d.rounded_rectangle((x1,y1,x2,y2),radius=24,fill='#'+LIGHT,outline='#'+BLUE,width=4)
        d.text(((x1+x2)//2,y1+55),title,font=bold,fill='#'+NAVY,anchor='ma')
        draw_text(d,(x1+25,y1+125),sub,small,fill='#'+BLACK,max_width=x2-x1-50,line_gap=4)
    for a,b in [(370,470),(770,870),(1170,1270)]:
        d.line((a,345,b,345),fill='#'+BLUE,width=7); d.polygon([(b,345),(b-20,332),(b-20,358)],fill='#'+BLUE)
    d.rounded_rectangle((520,620,1280,775),radius=20,fill='#FDF4E7',outline='#C97A15',width=3)
    d.text((900,655),'Absent or late participant',font=bold,fill='#9A5B00',anchor='ma')
    d.text((900,715),'deadline event → no fresh proof → no-op contribution',font=small,fill='#6D4A12',anchor='ma')
    d.line((620,470,620,620),fill='#C97A15',width=5); d.line((1180,470,1180,620),fill='#C97A15',width=5)
    im.save(ASSET/'fig_protocol.png',dpi=(180,180))
    # Figure 2
    im = Image.new('RGB',(1800,930),'white'); d=ImageDraw.Draw(im)
    d.text((900,50),'Per-slot semantics and exact carrier coverage',font=bold,fill='#'+NAVY,anchor='ma')
    d.text((90,165),'Canonical slot i',font=bold,fill='#'+NAVY)
    d.rounded_rectangle((90,220,530,430),radius=20,fill='#'+LIGHT,outline='#'+BLUE,width=4)
    d.text((310,270),'Base ciphertext B_i = Enc_P(m_i)',font=font,fill='#'+BLACK,anchor='ma')
    d.text((310,345),'Contribution C_i',font=bold,fill='#'+NAVY,anchor='ma')
    d.line((530,325,730,325),fill='#'+BLUE,width=6); d.polygon([(730,325),(710,312),(710,338)],fill='#'+BLUE)
    d.rounded_rectangle((730,150,1120,500),radius=20,fill='#F7FBFF',outline='#'+BLUE,width=4)
    d.text((925,200),'OR proof',font=bold,fill='#'+NAVY,anchor='ma')
    d.text((925,300),'branch 0: Enc_P(0)',font=font,fill='#'+BLACK,anchor='ma')
    d.text((925,390),'branch 1: Enc_P(-m_i)',font=font,fill='#'+BLACK,anchor='ma')
    d.text((925,435),'branch 1 requires\na linked residual carrier',font=small,fill='#'+GRAY,anchor='ma')
    d.line((1120,325,1300,325),fill='#'+BLUE,width=6); d.polygon([(1300,325),(1280,312),(1280,338)],fill='#'+BLUE)
    d.rounded_rectangle((1300,220,1710,430),radius=20,fill='#'+LIGHT,outline='#'+BLUE,width=4)
    d.text((1505,275),'B_i_prime',font=bold,fill='#'+NAVY,anchor='ma')
    d.text((1505,345),'Dec_P(B_i_prime) in {0, m_i}',font=font,fill='#'+BLACK,anchor='ma')
    d.line((920,500,920,640),fill='#C97A15',width=5); d.polygon([(920,640),(907,620),(933,620)],fill='#C97A15')
    d.rounded_rectangle((460,640,1380,820),radius=20,fill='#FDF4E7',outline='#C97A15',width=3)
    d.text((920,690),'Authenticated residual vector',font=bold,fill='#9A5B00',anchor='ma')
    d.text((920,755),'injective map  j -> i(j)  |  each carrier removed at most once',font=small,fill='#6D4A12',anchor='ma')
    im.save(ASSET/'fig_slot_semantics.png',dpi=(180,180))
    # Figure 3
    im = Image.new('RGB',(1800,1050),'white'); d=ImageDraw.Draw(im)
    d.text((900,50),'From reveal tokens to a reconstruction carrier',font=bold,fill='#'+NAVY,anchor='ma')
    d.rounded_rectangle((90,190,560,460),radius=22,fill='#'+LIGHT,outline='#'+BLUE,width=4)
    d.text((325,245),'Full card ciphertext',font=bold,fill='#'+NAVY,anchor='ma')
    d.text((325,330),'C_i = Enc_P(m_i; r_i)',font=font,fill='#'+BLACK,anchor='ma')
    d.text((325,405),'P = sum Q_p',font=font,fill='#'+BLACK,anchor='ma')
    d.line((560,325,760,325),fill='#'+BLUE,width=7); d.polygon([(760,325),(740,312),(740,338)],fill='#'+BLUE)
    d.rounded_rectangle((760,170,1040,480),radius=22,fill='#F7FBFF',outline='#'+BLUE,width=4)
    d.text((900,225),'Subtract submitted tokens',font=bold,fill='#'+NAVY,anchor='ma')
    d.text((900,320),'t_p,i = r_i Q_p',font=font,fill='#'+BLACK,anchor='ma')
    d.text((900,405),'C_i - sum t_p,i for p in A',font=font,fill='#'+BLACK,anchor='ma')
    d.line((1040,325,1240,325),fill='#'+BLUE,width=7); d.polygon([(1240,325),(1220,312),(1220,338)],fill='#'+BLUE)
    d.rounded_rectangle((1240,170,1710,480),radius=22,fill='#'+LIGHT,outline='#'+BLUE,width=4)
    d.text((1475,225),'Residual carrier',font=bold,fill='#'+NAVY,anchor='ma')
    d.text((1475,320),'= Enc_(sum Q_p for p in U)(m_i; r_i)',font=font,fill='#'+BLACK,anchor='ma')
    d.text((1475,405),'U = Players minus A',font=font,fill='#'+BLACK,anchor='ma')
    d.line((1475,480,1475,625),fill='#C97A15',width=6); d.polygon([(1475,625),(1462,605),(1488,605)],fill='#C97A15')
    d.rounded_rectangle((180,625,870,905),radius=22,fill='#FDF4E7',outline='#C97A15',width=3)
    d.text((525,690),'One missing token  |U| = 1',font=bold,fill='#9A5B00',anchor='ma')
    d.text((525,785),'The residual is under one owner key;',font=font,fill='#6D4A12',anchor='ma')
    d.text((525,845),'that owner can decrypt m_i.',font=font,fill='#6D4A12',anchor='ma')
    d.line((1475,625,1475,680),fill='#C97A15',width=6)
    d.line((1475,680,1150,680),fill='#C97A15',width=6); d.polygon([(1150,680),(1170,667),(1170,693)],fill='#C97A15')
    d.rounded_rectangle((930,625,1710,905),radius=22,fill='#F2F6FB',outline='#7A8FA6',width=3)
    d.text((1320,690),'Multiple missing tokens  |U| >= 2',font=bold,fill='#'+NAVY,anchor='ma')
    d.text((1320,785),'No individual online player learns m_i;',font=font,fill='#'+BLACK,anchor='ma')
    d.text((1320,845),'reconstruction retains the card without revealing it.',font=font,fill='#'+BLACK,anchor='ma')
    im.save(ASSET/'fig_residual_derivation.png',dpi=(180,180))
    # Figure 4
    im = Image.new('RGB',(1800,900),'white'); d=ImageDraw.Draw(im)
    d.text((900,50),'Machine-checked composition boundary',font=bold,fill='#'+NAVY,anchor='ma')
    left=[('Group / encoding','A1'),('ElGamal privacy','A2-A3'),('BG shuffle','A4'),('Cross-key + OR','A5'),('Transcript + state','A6-A9')]
    y=165
    for label,tag in left:
        d.rounded_rectangle((90,y,480,y+90),radius=15,fill='#'+PALE,outline='#AAB7C4',width=3)
        d.text((120,y+45),label,font=small,fill='#'+BLACK,anchor='lm'); d.text((450,y+45),tag,font=bold,fill='#'+BLUE,anchor='rm'); y+=115
    d.line((500,410,735,410),fill='#'+BLUE,width=7); d.polygon([(735,410),(715,397),(715,423)],fill='#'+BLUE)
    d.rounded_rectangle((735,220,1110,600),radius=24,fill='#'+LIGHT,outline='#'+BLUE,width=4)
    d.text((922,275),'Lean boundary',font=bold,fill='#'+NAVY,anchor='ma')
    d.text((922,365),'verified_package_semantics',font=font,fill='#'+BLACK,anchor='ma')
    d.text((922,455),'valid relation • exact coverage\nzero-or-negative membership',font=small,fill='#'+GRAY,anchor='ma')
    d.line((1110,410,1340,410),fill='#'+BLUE,width=7); d.polygon([(1340,410),(1320,397),(1320,423)],fill='#'+BLUE)
    d.rounded_rectangle((1340,220,1710,600),radius=24,fill='#F7FBFF',outline='#'+BLUE,width=4)
    d.text((1525,275),'Conditional UC',font=bold,fill='#'+NAVY,anchor='ma')
    d.text((1525,360),'simulator + extractor',font=font,fill='#'+BLACK,anchor='ma')
    d.text((1525,445),'real protocol ~ F_RECON',font=font,fill='#'+BLACK,anchor='ma')
    d.text((1525,530),'computational assumptions\nremain explicit',font=small,fill='#'+GRAY,anchor='ma')
    im.save(ASSET/'fig_composition.png',dpi=(180,180))

def setup_styles(doc):
    styles=doc.styles
    normal=styles['Normal']; normal.font.name='Aptos'; normal.font.size=Pt(10.5); normal.font.color.rgb=RGBColor.from_string(BLACK)
    normal._element.rPr.rFonts.set(qn('w:eastAsia'),'Aptos')
    normal.paragraph_format.space_after=Pt(6); normal.paragraph_format.line_spacing=1.08
    for name,size,color in [('Title',25,BLACK),('Heading 1',15,BLACK),('Heading 2',12,BLACK),('Heading 3',11,BLACK)]:
        st=styles[name]; st.font.name='Aptos Display'; st.font.size=Pt(size); st.font.bold=True; st.font.color.rgb=RGBColor.from_string(color)
        st.paragraph_format.space_before=Pt(14 if name!='Title' else 0); st.paragraph_format.space_after=Pt(6); st.paragraph_format.keep_with_next=True
    if 'Subtitle Custom' not in styles:
        st=styles.add_style('Subtitle Custom',WD_STYLE_TYPE.PARAGRAPH); st.font.name='Aptos'; st.font.size=Pt(13); st.font.italic=True; st.font.color.rgb=RGBColor.from_string(GRAY); st.paragraph_format.space_after=Pt(18)
    if 'Equation' not in styles:
        st=styles.add_style('Equation',WD_STYLE_TYPE.PARAGRAPH); st.font.name='Cambria Math'; st.font.size=Pt(10.5); st.font.color.rgb=RGBColor.from_string(BLACK); st.paragraph_format.left_indent=Inches(0.28); st.paragraph_format.space_before=Pt(5); st.paragraph_format.space_after=Pt(7)
    if 'Caption Custom' not in styles:
        st=styles.add_style('Caption Custom',WD_STYLE_TYPE.PARAGRAPH); st.font.name='Aptos'; st.font.size=Pt(9); st.font.italic=True; st.font.color.rgb=RGBColor.from_string(GRAY); st.paragraph_format.space_before=Pt(3); st.paragraph_format.space_after=Pt(10); st.paragraph_format.keep_with_next=False
    if 'Small Note' not in styles:
        st=styles.add_style('Small Note',WD_STYLE_TYPE.PARAGRAPH); st.font.name='Aptos'; st.font.size=Pt(9); st.font.color.rgb=RGBColor.from_string(GRAY); st.paragraph_format.space_after=Pt(5)

def setup_styles_zh(doc):
    setup_styles(doc)
    for name in ['Normal', 'Title', 'Heading 1', 'Heading 2', 'Heading 3', 'Subtitle Custom', 'Caption Custom', 'Small Note']:
        st = doc.styles[name]
        st.font.name = 'PingFang SC'
        st._element.rPr.rFonts.set(qn('w:eastAsia'), 'PingFang SC')
    doc.styles['Equation'].font.name = 'Cambria Math'
    doc.styles['Equation']._element.rPr.rFonts.set(qn('w:eastAsia'), 'Cambria Math')

def add_para(doc, text='', style=None, bold_prefix=None):
    p=doc.add_paragraph(style=style)
    if bold_prefix and text.startswith(bold_prefix):
        p.add_run(bold_prefix).bold=True; p.add_run(text[len(bold_prefix):])
    else: p.add_run(text)
    return p

def add_equation(doc, text):
    p=doc.add_paragraph(style='Equation'); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run(text); return p

def add_figure(doc, path, caption, width=6.25):
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_before=Pt(6); p.paragraph_format.space_after=Pt(2)
    run = p.add_run(); run.add_picture(str(path),width=Inches(width))
    drawing = run._r.find(qn('w:drawing'))
    if drawing is not None:
        docPr = drawing.find('.//' + qn('wp:docPr'))
        if docPr is not None:
            docPr.set('descr', caption)
            docPr.set('title', caption.split('.')[0])
    c=doc.add_paragraph(style='Caption Custom'); c.alignment=WD_ALIGN_PARAGRAPH.CENTER; c.add_run(caption)

def add_table(doc, headers, rows, widths=None):
    t=doc.add_table(rows=1, cols=len(headers)); t.alignment=WD_TABLE_ALIGNMENT.CENTER; t.style='Table Grid'
    hdr=t.rows[0]; set_repeat_table_header(hdr); set_row_cant_split(hdr)
    for j,h in enumerate(headers):
        cell=hdr.cells[j]; set_cell_shading(cell,NAVY); set_cell_border(cell); set_cell_margins(cell)
        cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
        p=cell.paragraphs[0]; p.alignment=WD_ALIGN_PARAGRAPH.CENTER; r=p.add_run(h); r.bold=True; r.font.color.rgb=RGBColor(255,255,255); r.font.size=Pt(9.5)
    for i,row in enumerate(rows):
        added_row=t.add_row(); set_row_cant_split(added_row); cells=added_row.cells
        for j,val in enumerate(row):
            cell=cells[j]; set_cell_border(cell); set_cell_margins(cell); cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if i%2==1: set_cell_shading(cell,'F7F9FC')
            p=cell.paragraphs[0]; p.alignment=WD_ALIGN_PARAGRAPH.LEFT; r=p.add_run(val); r.font.size=Pt(9.2)
    if widths:
        for row in t.rows:
            for cell,w in zip(row.cells,widths): cell.width=Inches(w)
    doc.add_paragraph().paragraph_format.space_after=Pt(1)
    return t

def build():
    make_figures()
    doc=Document(); setup_styles(doc)
    sec=doc.sections[0]; sec.top_margin=Inches(0.75); sec.bottom_margin=Inches(0.7); sec.left_margin=Inches(0.82); sec.right_margin=Inches(0.82)
    # header/footer
    header=sec.header.paragraphs[0]; header.text='COMPOSABLE PRIVACY-PRESERVING DECK RECONSTRUCTION'; header.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    header.runs[0].font.size=Pt(8); header.runs[0].font.color.rgb=RGBColor.from_string(GRAY)
    footer=sec.footer.paragraphs[0]; footer.alignment=WD_ALIGN_PARAGRAPH.CENTER; footer.add_run('Poker Protocol  •  '); add_page_field(footer)
    for r in footer.runs: r.font.size=Pt(8); r.font.color.rgb=RGBColor.from_string(GRAY)
    # title page
    p=doc.add_paragraph(style='Title'); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run('Composable Privacy Preserving Deck Reconstruction for Mental Poker')
    p=doc.add_paragraph(style='Subtitle Custom'); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run('Slot semantics, cross-key proofs, and a machine-checked composition boundary')
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_before=Pt(25); p.add_run('17 September 2026  •  poker_protocol repository')
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_after=Pt(4)
    p.add_run('Source repository: ').bold=True; add_hyperlink(p,'github.com/linqining/poker_protocol/tree/feat/paper','https://github.com/linqining/poker_protocol/tree/feat/paper')
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_before=Pt(36)
    r=p.add_run('Scope of the claim'); r.bold=True; r.font.color.rgb=RGBColor.from_string(NAVY)
    add_para(doc,'The conditional UC theorem is stated in the random-oracle model and assumes the security of the Bayer–Groth, cross-key, and slot OR components, authenticated reveal-token state, and a byte-level refinement relation between the implementation and the formal model. Lean checks the residual-carrier lineage, algebraic reconstruction relation, cross-key Sigma protocol, slot OR protocol, and the composition theorem. Computational component security and implementation refinement remain explicit assumptions; they are not silently treated as algebraic facts.','Small Note')
    doc.add_page_break()
    # abstract + metadata
    doc.add_heading('Abstract', level=1)
    add_para(doc,'Mental Poker encrypts and shuffles a deck so that no single participant learns the complete order or contents. A multiplayer shuffle normally requires every participant to perform its step. If a participant leaves or stops responding, the table can become unable to reconstruct the next deck: the remaining players must remove the departed participant’s cards without learning or altering the other cards, yet the departed participant can no longer cooperate. The shuffle mechanism alone does not solve this liveness gap.')
    add_para(doc,'This paper presents a residual-ciphertext reconstruction protocol that lets the remaining table continue after a participant leaves. The implementation historically calls the input `readable_card`, but that name is exact only when one reveal token is missing. In general, the input is an authenticated state-bound residual carrier obtained by subtracting the reveal tokens that were actually submitted. With one missing token, the residual is encrypted under one owner key and that owner can decrypt it; with two or more missing tokens, the residual is encrypted under the sum of several keys and no individual player can decrypt it. Reconstruction nevertheless remains possible: only an authenticated owner-residual carrier may authorize a negative contribution, while a jointly keyed unknown card receives the zero branch and therefore remains in the freshly rebuilt canonical deck without being revealed.')
    add_para(doc,'For each canonical slot, the prover contributes an encryption under the aggregate public key of either zero or the negative of that slot’s card. A cross-key proof links every negative branch to an authenticated residual carrier; a hidden shuffle conceals the mapping; a two-branch OR proof enforces the per-slot plaintext relation; and a domain-separated transcript binds the table context, epoch, state digest, keys, cards, residual carriers, and contributions. Under the stated assumptions, an accepted package yields an extractable witness with exact carrier coverage. The Lean theorem `verified_package_semantics` composes these guarantees into public validity, authenticated residual coverage, and per-slot plaintext membership.')
    p=doc.add_paragraph(); p.paragraph_format.space_before=Pt(8); r=p.add_run('Keywords. '); r.bold=True; p.add_run('Mental Poker; verifiable shuffle; ElGamal; generalized Schnorr; zero knowledge; UC security; formal verification.')
    doc.add_heading('Reading guide', level=1)
    add_para(doc,'Sections 1–3 motivate the departure problem and state the algebraic and computational assumptions. Section 4 gives the protocol. Sections 5–6 state correctness, standalone security, and the conditional UC composition theorem. Section 7 explains the Lean boundary, while Sections 8–10 cover reproducibility, limitations, and conclusions.')

    doc.add_heading('1. Introduction and motivation', level=1)
    add_para(doc,'Mental Poker protocols use public-key encryption, re-encryption, and proofs of correct shuffling to let several players deal and play without revealing the deck. The basic multiplayer construction is cooperative: each player applies a private shuffle or masking step, and the next phase assumes that all required steps are completed. This assumption is reasonable for a synchronous toy protocol, but it is a serious availability problem for a real table. A player may disconnect, crash, or deliberately refuse to continue. If the cards still contain that player’s encryption layer, the remaining players cannot simply delete the layer or guess which cards belonged to the absent player. The deck then cannot be safely reconstructed.')
    add_para(doc,'The central contribution of this work is to separate card provenance from the absent user’s participation in the current round. During normal play, the table state records authenticated residual ciphertexts together with the reveal-token lineage that produced them. After one or more players fail to submit a token, an active participant can use each decryptable owner-residual carrier to construct a reconstruction proof. The proof removes exactly those authorized cards, preserves every other canonical card, and exposes neither the mapping nor the card values. A jointly keyed residual that no player can decrypt authorizes no negative branch, so its canonical card remains in the new deck. Thus the table can proceed without requiring every previous card plaintext to be known by an online player.')
    add_para(doc,'Let the canonical deck be a public, duplicate-free sequence of curve points M = (m₀,…,mₙ₋₁). A card is initially encrypted under the aggregate key P = Σₚ Qₚ. If A is the set of players whose reveal tokens were submitted and U is the missing-token set, the residual is encrypted under Q_U = Σₚ∈U Qₚ. The special case |U| = 1 is an owner-residual carrier; the general case |U| ≥ 2 is jointly keyed. Reconstruction must preserve this distinction while ensuring that the owner-to-slot mapping and branch choices remain hidden and the output remains a valid ElGamal deck for the next shuffle.')
    add_para(doc,'The difficult part is slot semantics. A proof of a ciphertext multiset or of a global linear sum is insufficient: compensating ciphertexts can make the sum look correct while changing an individual slot. The protocol therefore proves the allowed plaintext relation independently for every slot, and separately proves that each negative branch is linked to an authenticated residual carrier.')
    doc.add_heading('Contributions', level=2)
    contributions=[('1','Reveal-token derivation','We derive the residual carrier by subtracting submitted reveal tokens and distinguish the owner-residual and jointly keyed cases.'),('2','Liveness-aware reconstruction','Authenticated residual carriers allow an active table to rebuild after non-participation; a deadline is a no-op event, not a plaintext disclosure.'),('3','Aggregate-key encryption','All contributions use the same aggregate key P, so the reconstructed deck retains the standard ElGamal shape.'),('4','Cross-key negation proof','For an authenticated carrier and a negative contribution under P, the prover proves the required ciphertext relation without exposing the card or its mapping.'),('5','Per-slot OR semantics','Each canonical slot is proven to contain either an encryption of zero or an encryption of the slot’s negative card.'),('6','State and transcript binding','The table context, epoch, previous-state digest, public keys, canonical cards, residual carriers, and contributions are bound into a domain-separated transcript.'),('7','Composable security model','We give an ideal functionality, a real protocol, and a conditional UC composition theorem for static corruption.'),('8','Machine-checked composition','Lean derives end-to-end package semantics from explicit component and refinement interfaces.')]
    add_table(doc,['No.','Contribution','Statement'],contributions,widths=[0.42,1.55,4.15])
    add_figure(doc,ASSET/'fig_protocol.png','Figure 1. The reconstruction path separates authenticated provenance from current-round participation. A missed deadline contributes no fresh proof and therefore has no effect on the aggregate deck.')

    doc.add_heading('2. Background and related work', level=1)
    add_para(doc,'Classical Mental Poker constructions combine public-key encryption with successive private shuffles. Bayer–Groth gives a compact zero-knowledge argument for a hidden permutation and re-encryption [2]. Schnorr, Chaum–Pedersen, and partial-knowledge protocols establish the required linear and disjunctive relations [3,4,6], while Fiat–Shamir turns Sigma protocols into non-interactive proofs in the random-oracle model [5]. UC security accounts for state, scheduling, concurrency, and adversarial message delivery [1]. Castellà-Roca, Sebé, and Domingo-Ferrer specifically address dropout-tolerant, TTP-free Mental Poker [7].')
    add_para(doc,'Those ingredients do not by themselves solve the departure problem. A shuffle proof can show that an output is a re-encrypted permutation of an input, but it does not say that a particular output slot contains either the original card or an identity correction. Nor does it identify which correction is authorized by the authenticated history of the table. Our protocol adds the missing reconstruction layer: hidden shuffling protects the mapping, the slot OR proof restricts plaintexts, the cross-key proof links a negative contribution to a readable ciphertext, and the state digest authenticates the card’s provenance.')

    doc.add_heading('3. Model and assumptions', level=1)
    add_para(doc,'Let q be a large prime, F_q the scalar field, and G a prime-order additive group with generator g. For a public key P = xg, define the additive ElGamal encryption and decryption functions as follows.')
    add_equation(doc,'Encₚ(m; r) = (rg, m + rP),      Decₓ(C) = C.c₂ − xC.c₁.')
    add_para(doc,'ElGamal is additively homomorphic:')
    add_equation(doc,'Encₚ(m; r) + Encₚ(m′; r′) = Encₚ(m + m′; r + r′).')
    add_para(doc,'The aggregate public key is P = Σₚ pkₚ, and Qₚ = skₚg. Canonical cards are nonzero and pairwise distinct. The protocol relies on the following assumptions; the distinction between algebraic facts and computational assumptions is part of the security claim.')
    doc.add_heading('3.1 Reveal-token algebra and the origin of the reconstruction carrier', level=2)
    add_para(doc,'The term “readable card” is a legacy API name, not the invariant that the security proof needs. We therefore use residual carrier for the general object, and owner-residual carrier only for the single-missing-token specialization. The invariant is a residual ciphertext derived from an authenticated reveal-token transcript. Let the fully masked card be')
    add_equation(doc,'Cᵢ = Encₚ(mᵢ; rᵢ) = (rᵢg, mᵢ + rᵢP),      P = Σₚ Qₚ.')
    add_para(doc,'For player p, the reveal token is the first ciphertext component multiplied by that player’s secret key:')
    add_equation(doc,'tₚ,ᵢ = skₚ Cᵢ.c₁ = rᵢQₚ.')
    add_para(doc,'The Chaum–Pedersen/DLEQ proof attached to tₚ,ᵢ establishes that the same secret key links Qₚ = skₚg and tₚ,ᵢ = skₚCᵢ.c₁. Therefore a verifier may subtract only tokens that are authenticated for the current card and epoch. Let A be the set of players whose reveal tokens were submitted, and let U = Players minus A be the missing-token set. Define Q_U = Σₚ∈U Qₚ. The residual carrier is')
    add_equation(doc,'Cᵢ^(A) = Cᵢ − Σₚ∈A tₚ,ᵢ = (rᵢg, mᵢ + rᵢΣₚ∈U Qₚ) = Enc_{Q_U}(mᵢ; rᵢ),      Q_U = Σₚ∈U Qₚ.')
    add_para(doc,'The derivation is a direct group identity, but its interpretation depends on |U|. If |U| = 1, say U = {q}, then Q_U = Q_q and the residual carrier is decryptable by q; this is the owner-residual carrier specialization used to authorize removal. If |U| ≥ 2, then Q_U is a sum of several public keys. The remaining online players do not possess the aggregate secret key sk_U = Σₚ∈U skₚ, so no individual player learns mᵢ from the residual. The protocol does not need to decrypt or remove that card. Reconstruction starts from a fresh canonical base Bᵢ = Enc_P(mᵢ; i+1). Because no owner-residual proof authorizes the negative branch for mᵢ, every accepted contribution for that slot encrypts zero; homomorphic aggregation therefore retains mᵢ in the new deck. The old jointly keyed ciphertext can be discarded after its authenticated state transition has determined that no removal is authorized. If U is empty, all tokens were submitted and the result is a plaintext/redeal boundary rather than a residual carrier that should be called readable.')
    add_para(doc,'The same derivation also explains why authenticated lineage is the foundation of reconstruction. An owner-residual carrier is not an arbitrary ciphertext supplied by a prover: its first component, masking randomness, owner key, card slot, epoch, and submitted-token set are fixed by the prior state. Consequently, the proof can safely establish the relation')
    add_equation(doc,'Q_U = sk_U g,   Sⱼ.c₁ = vⱼg,   sk_U Rⱼ.c₁ + vⱼP = Rⱼ.c₂ + Sⱼ.c₂,   Sⱼ = Encₚ(−mᵢ₍ⱼ₎; vⱼ).')
    add_para(doc,'For |U| = 1, sk_U is the owner secret key and the current code checks the relation after owner decryption. For |U| ≥ 2, the current protocol deliberately does not instantiate this negative relation: the slot takes the zero branch and the canonical card is retained. A deployment that instead wished to remove a jointly unknown card would need a distributed generalized-Schnorr or threshold relation proof; that stronger policy is outside the present construction. Thus reconstruction remains live even when every online player is unable to read the old ciphertext.')
    add_figure(doc,ASSET/'fig_residual_derivation.png','Figure 2. Reveal-token subtraction produces a residual ciphertext. One missing token gives an owner-residual specialization; multiple missing tokens give a jointly keyed carrier that remains usable for reconstruction without becoming readable to any individual player.')
    assumptions=[('A1','Group and encoding','The curve implementation accepts only the prime-order subgroup and canonical encodings, and implements group operations correctly.'),('A2','Encryption privacy','ElGamal is IND-CPA secure under DDH or an equivalent assumption.'),('A3','Residual privacy','Every jointly keyed residual retains at least one honest, secret, uniform masking layer unless the protocol intentionally enters the plaintext/redeal path; privacy uses the corresponding fresh-discrete-log hardness assumption.'),('A4','Hidden shuffle','The Bayer–Groth component is complete, knowledge sound, and zero knowledge.'),('A5','Linear proofs','The cross-key and slot OR Sigma protocols are complete and specially sound, with perfect honest-verifier zero knowledge; their Fiat–Shamir transforms are secure in the random-oracle model.'),('A6','Transcript composition','Shared-challenge resampling and sequential composition do not create cross-component attacks, and transcript domains are separated and canonicalized.'),('A7','Authenticated state and refinement','The previous state digest cannot be forged, reveal-token proofs are bound to the card and epoch, and the Rust/AIR byte encoding refines the Lean statement.'),('A8','Authenticated missing-key sets','A negative contribution is accepted only for an authenticated singleton missing-token set. A residual with two or more missing keys authorizes only the zero branch, so its card remains in the rebuilt deck.'),('A9','Corruption model','Corruption is static, and an honest owner key or residual masking layer is not revealed before the execution ends.')]
    add_table(doc,['ID','Assumption','Operational meaning'],assumptions,widths=[0.42,1.55,4.15])

    doc.add_heading('4. Protocol', level=1)
    doc.add_heading('4.1 Public statement', level=2)
    add_para(doc,'The public statement is')
    add_equation(doc,'S = (context_digest, epoch, D_prev, P, Q, (mᵢ)ᵢ₍ₙ, (Rⱼ)ⱼ₍ₖ, (Cᵢ)ᵢ₍ₙ).')
    add_para(doc,'Here Rⱼ are authenticated residual ciphertexts and Cᵢ are the prover’s contributions. The verifier rejects malformed lengths, identity keys or ciphertexts, duplicate canonical cards, an empty carrier set, and a carrier set larger than the deck. The semantic relation is determined by these fields and by the reveal-token lineage that derives them; wire-level validation is fail-closed.')
    doc.add_heading('4.2 Proof generation', level=2)
    add_para(doc,'The prover has the authenticated owner-residual vector R₀,…,Rₖ₋₁ consisting precisely of the |U| = 1 carriers assigned to that owner, together with the state-bound token derivation and the owner secret key. Jointly keyed |U| ≥ 2 residuals are not placed in this removal-authorizing vector; their slots retain the zero branch. The prover performs the following steps.')
    for s in ['Derive each Rⱼ by subtracting the authenticated submitted tokens; in the owner-residual specialization, decrypt it and check that its plaintext is a distinct canonical card.','Sample vⱼ and construct Sⱼ = Encₚ(−mᵢ₍ⱼ₎; vⱼ); construct n−k deterministic zero contributions.','Apply a hidden permutation and fresh rerandomization to obtain the canonical contribution vector.','Prove the carrier-to-contribution relation for each pair (Rⱼ,Sⱼ); the one-owner path uses the cross-key Chaum–Pedersen relation described below.','Prove a Bayer–Groth relation from the hidden contribution vector to C.','Prove the two-branch OR relation for every canonical slot.']:
        p=doc.add_paragraph(style='List Number'); p.add_run(s)
    add_para(doc,'The carrier-to-slot mapping, branch choices, permutation, and randomness are prover witnesses and do not appear in the proof bytes.')
    doc.add_heading('4.3 Cross-key joint proof', level=2)
    add_para(doc,'For the owner-residual specialization, R = Enc_Q(m; r) and S = Enc_P(−m; v), and the prover shows knowledge of (sk_Q,v) satisfying')
    add_equation(doc,'Q = sk_Q g,      S.c₁ = vg,      sk_Q R.c₁ + vP = R.c₂ + S.c₂.')
    add_para(doc,'This is a two-scalar generalized-Schnorr relation over three linked group equations. The third equation implies that the two ciphertext plaintexts sum to zero, so the negative contribution is tied to the authenticated owner-residual plaintext. The witness does not contain r = DL(R.c₁). The relation is instantiated only when |U| = 1. For |U| ≥ 2, no player can supply sk_U, and the protocol consequently authorizes no negative contribution; retaining the zero branch is sufficient to rebuild the deck without learning the card.')
    doc.add_heading('4.4 Slot OR proof', level=2)
    add_para(doc,'For slot i, define T₀ = Cᵢ.c₂ and T₁ = Cᵢ.c₂ + mᵢ. The prover shows that there is a vᵢ such that')
    add_equation(doc,'Cᵢ.c₁ = vᵢg  and  T_b = vᵢP  for one branch b ∈ {0,1}.')
    add_para(doc,'Branch 0 is the zero contribution and branch 1 is the negative-card contribution. A standard OR proof honestly proves one branch, simulates the other with a challenge share, and enforces e₀ + e₁ = e for the global challenge.')
    doc.add_heading('4.5 Aggregate reconstruction', level=2)
    add_para(doc,'Starting from the canonical base deck Bᵢ = Encₚ(mᵢ; i+1), the host sums every contribution whose proof passes before the deadline:')
    add_equation(doc,'B̃ᵢ = Bᵢ + Σₚ∈S_submit Cₚ,ᵢ.')
    add_para(doc,'An absent or late participant contributes nothing. Under A8, at most one accepted contribution can carry the negative branch for a given authenticated residual slot. A participant cannot use a missed submission to authorize a negative contribution for a carrier outside the authenticated missing-key set.')
    add_figure(doc,ASSET/'fig_slot_semantics.png','Figure 3. Slot-local OR semantics and exact residual-carrier coverage. The global deck relation is obtained by composing these per-slot constraints with an injective carrier-to-slot map.')

    doc.add_heading('5. Correctness and standalone security', level=1)
    doc.add_heading('Theorem 1 (Completeness)', level=2)
    add_para(doc,'If the statement satisfies the authenticated-state conditions and an honest prover follows Section 4.2, the verifier accepts except for explicit zero-challenge events, with failure probability bounded by O((n+k)/q).')
    add_para(doc,'Proof sketch. Reveal-token lineage for each removal-authorizing carrier gives Rⱼ = Enc_Q(mᵢ₍ⱼ₎; rⱼ), where Q is the unique missing-token owner key, so the cross-key equation holds by direct substitution. A jointly keyed residual is absent from the removal-authorizing vector and induces the zero branch. Bayer–Groth is complete for the correct permutation and rerandomizers. The real OR branch is honest and the simulated branch satisfies its verification equation; the branch challenges sum to the global challenge. All statement fields enter the transcript in the same order.')
    doc.add_heading('Theorem 2 (Knowledge soundness)', level=2)
    add_para(doc,'Under A1, A4, A5, A6, and A7, an extractor for any accepted statement/proof returns a witness (removed, v, carrierIndex, …), except with the component security error, such that: (i) every slot contribution encrypts either 0 or −mᵢ; (ii) removedᵢ = true exactly when some authenticated carrier index maps to slot i; (iii) carrierIndex is injective; and (iv) every negative branch is linked to the authenticated residual-token derivation.')
    add_para(doc,'Proof sketch. Forking the shared transcript extracts the Bayer–Groth permutation and rerandomizers, the carrier relation witness (the same sk_Q,vⱼ in the one-owner path, or its aggregate analogue), and the branch witness from each OR proof. The extracted objects satisfy the Lean relation; exact carrier coverage yields items (ii)–(iv). Any failure reduces to a component security failure or to a state/serialization refinement failure.')
    doc.add_heading('Theorem 3 (Reconstruction semantics)', level=2)
    add_para(doc,'Let χᵢ = 1 exactly when an accepted submitter has an authenticated owner-residual carrier that authorizes removal of mᵢ in the current epoch. Under A8,')
    add_equation(doc,'Decₚ(B̃ᵢ) = 0  if χᵢ = 1;      Decₚ(B̃ᵢ) = mᵢ  if χᵢ = 0.')
    add_para(doc,'This follows from Theorem 2, the per-slot plaintext relation, exact owner-residual coverage, and ElGamal homomorphism. In particular, |U| ≥ 2 implies χᵢ = 0 for that residual: nobody learns mᵢ, yet the fresh canonical base ensures that mᵢ remains in the rebuilt encrypted deck.')

    doc.add_heading('6. UC ideal functionality and composition', level=1)
    doc.add_heading('6.1 Hybrid model', level=2)
    add_para(doc,'The protocol runs in a hybrid with a random-oracle functionality, authenticated state, and authenticated key/shuffle/reveal functionality. The state records the canonical deck, public keys, previous assignment, reveal-token lineage, residual-carrier derivation, epoch, and authenticated missing-key sets. The corruption set is static; the network adversary may reorder, drop, or delay messages.')
    doc.add_heading('6.2 Ideal functionality F_RECON', level=2)
    add_para(doc,'The functionality is addressed by sid = (context, table, hand, epoch, D_prev). It obtains each player’s authenticated residual-carrier derivation from the state functionality without revealing the underlying plaintexts. It waits for SUBMIT or a deadline and lets S be the successful submitters. It removes exactly the cards backed by singleton missing-token derivations of accepted submitters; a carrier with two or more missing keys is retained. An inconsistent or overlapping removal authorization produces STATE_INVALID.')
    add_para(doc,'The functionality generates a fresh aggregate-key encrypted deck. It reveals only the deck size, carrier count, keys, epoch, previous digest, verification results, deadline/abort status, and final state digest. It does not reveal the owner-to-slot mapping, branch choices, randomness, permutation, or whether a carrier was locally readable by any one player. A partial submission is an availability event: a submitter can authorize only the authenticated carrier relation, not another player’s cards.')
    doc.add_heading('6.3 Real protocol', level=2)
    add_para(doc,'The real protocol obtains the exact owner-residual vector, reveal-token lineage, previous digest, canonical deck, and aggregate key from authenticated state. The client runs ReconstructProof::prove; the verifier checks the statement and proof; the host performs homomorphic aggregation and validates call context, epoch, state digest, and the next shuffle input. A |U| ≥ 2 residual is not presented as an owner-residual input and therefore cannot authorize a negative contribution. An abort produces a no-op or timeout, never an arbitrary negative contribution.')
    doc.add_heading('6.4 Conditional UC theorem', level=2)
    add_para(doc,'Theorem 4. Under A1–A9, if the Bayer–Groth, cross-key, and slot OR Fiat–Shamir proofs are extractable, simulatable, and concurrently composable in the random-oracle hybrid, then every static adversary/environment has negligible distinguishing advantage between the real protocol and F_RECON. The bound is the sum of the component zero-knowledge and knowledge-soundness errors, DDH and fresh-discrete-log errors, state and serialization errors, and O((n+k)/q).')
    add_para(doc,'The simulator extracts corrupted proofs, simulates honest proofs, programs the shared challenge consistently, and uses IND-CPA plus fresh rerandomization to replace honest contributions. It forwards the public byte representation through the refinement relation. A negative contribution outside the authenticated residual-carrier set yields a reduction to state forgery, proof failure, or serialization failure. UC composition then gives the end-to-end result.')
    doc.add_heading('6.5 Vetoing another player’s card', level=2)
    add_para(doc,'Define Veto(p,m) as an accepted package by player p that removes m even though the authenticated residual-carrier derivation for p’s epoch does not authorize m.')
    add_para(doc,'Theorem 5. Under A1, A4, A5, A6, A7, and A8, Pr[Veto(p,m)] ≤ ε_KS + ε_state + ε_ser. Acceptance gives the extracted negative branch and its owner-residual witness. Exact-vector state binding identifies that carrier with an authenticated singleton missing-token derivation; otherwise the adversary forged the state digest, a proof, or the serialization refinement. If p does not submit, no contribution from p exists. The bound does not apply when the authenticated missing-key invariant or owner-key secrecy fails.')
    add_figure(doc,ASSET/'fig_composition.png','Figure 4. The formalization exposes a precise machine-checked boundary. Group algebra and component interfaces feed `verified_package_semantics`; computational assumptions are then used by the conditional UC argument.')

    doc.add_heading('7. Lean formalization', level=1)
    add_para(doc,'The Lean development separates the algebraic specification from the computational assumptions supplied by the implementation.')
    lean_rows=[('Residual lineage','ResidualCarrierProvenance.lean','authenticated_prior_hand_yields_residual_carrier; residual_carrier_c1_eq_accumulated_randomness'),('Reconstruction relation','Reconstruction.lean','relation_complete; valid_relation_complete; accepted_contribution_is_zero_or_negative_card; corrected_slot_semantics; aggregatePlaintext_unique_removal'),('Cross-key Sigma','ReconstructionJointSigma.lean','relation_iff_cross_key; sigma_complete; sigma_speciallySound; sigma_perfect_hvzk'),('Slot OR','ReconstructionSlotOr.lean','honest_accepts; specially_sound; perfect_hvzk_algebraic'),('Composition boundary','ReconstructionSecurity.lean','completeness_under_components; knowledge_soundness_under_components; zero_knowledge_under_components; verified_package_semantics')]
    add_table(doc,['Layer','File','Checked result'],lean_rows,widths=[1.3,1.75,3.07])
    add_para(doc,'The algebraic Statement contains the aggregate key, the authenticated residual-key description, canonical cards, residual ciphertexts, and contributions. The Witness contains the removed-slot bitmap, contribution randomness, carrier-to-slot map, residual randomness, injectivity, and exact-coverage condition. Relation states the reveal-token subtraction equations and the per-slot contribution equations. The one-owner witness is the concrete specialization currently implemented by the AIR producer.')
    add_para(doc,'ComponentInterface records the external guarantees for hidden shuffle, Fiat–Shamir forking, sequential zero knowledge, transcript binding, Rust-to-Lean serialization, authenticated state, and cross-player disjointness. Reduction connects those guarantees to the concrete implementation’s prove, verify, extraction, and view functions.')
    add_para(doc,'The main composition theorem is verified_package_semantics. Given a VerifiedPackage containing a well-formed statement, an extracted witness, the algebraic relation, and a proof that the component interface holds, it derives in one theorem: (i) ValidRelation for the public statement and witness; (ii) exact correspondence between removed i = true and an authenticated residual-carrier index; and (iii) the zero-or-negative-card membership equation for every contribution.')
    add_para(doc,'Thus Lean checks the semantic bridge used by the paper’s security argument. It does not claim that DDH, random-oracle security, Bayer–Groth knowledge soundness, or byte-level implementation refinement are consequences of group algebra. Those facts enter as explicit fields of ComponentInterface and Reduction, which makes the trust boundary visible and auditable.')
    add_para(doc,'The repository’s Lean checks include a no-sorry audit and an axiom audit for the principal reconstruction results. The audit reports only the trusted Lean foundations used by imported libraries and no protocol-specific axiom.')

    doc.add_heading('8. Implementation and reproducibility', level=1)
    add_para(doc,'The code is organized as follows:')
    add_table(doc,['Component','Role'],[('poker-protocol-core','Curve arithmetic, ElGamal, and transcripts.'),('poker-protocol-bg','Bayer–Groth shuffle component.'),('poker-protocol-proofs','Reconstruction, cross-key, OR, and related proofs.'),('poker_protocol','Native adapter, ABI, and game integration.'),('poker_protocol_lean','Formal specification and checked composition.')],widths=[2.1,4.0])
    add_para(doc,'The native path uses the Stark-curve/Poseidon transcript domain. The Ristretto adapter constructs the public submission object; verification of an external AIR archive is outside this repository. The Move contract stores the partial ciphertext after subtracting submitted reveal tokens, while the AIR test helper derives the |U| = 1 owner-residual vector by subtracting every other seat’s token. When two or more tokens are missing, no owner-residual vector entry is created and the rebuilt canonical slot remains unchanged. The repository branch containing the paper and implementation is `https://github.com/linqining/poker_protocol/tree/feat/paper`.')
    add_para(doc,'To reproduce the checks:')
    add_equation(doc,'cargo test --workspace\ncd poker_protocol_lean && lake build PokerProtocolLean\ncd poker_protocol_lean && bash scripts/count_sorries.sh')
    add_para(doc,'An experiment report should include the curve, transcript mode, proof size, proving and verification time, peak memory, and the linear growth in the number of cross-key proofs (k) and slot OR proofs (n).')

    doc.add_heading('9. Limitations and future work', level=1)
    limits=['A malicious player that never submits is an availability event. Deadlines, deposits, or a replacement submitter are needed for an application-level policy.','Authenticated reveal-token lineage is essential. Without the residual derivation, the veto theorem does not hold.','The deck size, owner-residual carrier count, public keys, canonical cards, epoch, and state digest are public; the protocol does not hide these metadata.','A |U| ≥ 2 residual authorizes no removal in this construction, so the corresponding canonical card remains in the new deck. Removing such a jointly unknown card would require a threshold relation proof and a different authorization policy.','Full UC security depends on a composable Fiat–Shamir NIZK treatment. A standard-model instantiation would require an extractable NIZK or a new proof system.','Adaptive corruption requires erasures or non-committing techniques.','Multiple authorization of the same owner-residual carrier is excluded by the authenticated missing-key invariant.']
    for s in limits: doc.add_paragraph(s,style='List Bullet')

    doc.add_heading('10. Conclusion', level=1)
    add_para(doc,'The reconstruction protocol addresses a liveness gap in cooperative Mental Poker. Authenticated reveal-token subtraction yields a residual ciphertext carrier for every card: owner-residual when one token is missing, jointly keyed when several tokens are missing. Owner-residual carriers authorize exact removals; a jointly keyed carrier authorizes no negative branch, so the corresponding canonical card remains in the freshly encrypted deck. The active table can therefore continue even when no individual player knows an old card plaintext. The proof system combines hidden mapping, carrier-to-plaintext binding, per-slot zero-or-negative semantics, and state/transcript binding in one auditable package.')
    add_para(doc,'An accepted package has an extractable witness with exact residual-carrier coverage; under authenticated lineage and missing-key binding, it cannot veto another player’s card except with the stated security error. The Lean composition layer connects the algebraic relation and the component/refinement interfaces through verified_package_semantics, giving the conditional UC argument a precise, machine-checked semantic boundary.')

    doc.add_heading('Appendix A. Relation to dropout-tolerant mental poker', level=1)
    add_para(doc,'Castellà-Roca, Sebé, and Domingo-Ferrer study dropout-tolerant Mental Poker without a trusted third party and use zero-knowledge techniques to let a game continue after a player leaves [7]. Their objective is closely related to our liveness motivation, but the protocol abstraction and security boundary differ. Our construction starts from an authenticated, state-bound reveal-token transcript and derives a residual carrier for each card. It proves exact coverage for the owner-residual subset, a hidden carrier-to-slot mapping, and a per-slot zero-or-negative plaintext relation. The distinction between one missing token and several missing tokens is essential: only the former yields an owner-residual carrier that one participant can decrypt and use to authorize removal; the latter yields a jointly keyed carrier whose canonical card is retained without revealing its plaintext.')
    add_para(doc,'Accordingly, [7] is prior work on dropout tolerance, not a proof of the residual-carrier semantics or the conditional UC theorem stated here. Our contribution is complementary: it makes the reconstruction object explicit, connects it to authenticated prior state, and exposes the implementation/formalization boundary for the cross-key and slot OR proofs. The comparison also clarifies the policy for multiple missing tokens: the present protocol retains the corresponding canonical card without revealing it; threshold-authorized removal would be a separate extension.')

    doc.add_heading('References', level=1)
    refs=['R. Canetti. “Universally Composable Security.” FOCS 2001.','S. Bayer and J. Groth. “Efficient Zero-Knowledge Argument for Correctness of a Shuffle.” EUROCRYPT 2012.','D. Chaum and T. Pedersen. “Wallet Databases with Observers.” CRYPTO 1992.','R. Cramer, I. Damgård, and B. Schoenmakers. “Proofs of Partial Knowledge and Simplified Design of Witness Hiding Protocols.” CRYPTO 1994.','A. Fiat and A. Shamir. “How to Prove Yourself.” CRYPTO 1986.','C.-P. Schnorr. “Efficient Identification and Signatures for Smart Cards.” CRYPTO 1989.','J. Castellà-Roca, F. Sebé, and J. Domingo-Ferrer. “Dropout-tolerant TTP-free mental poker.” Trust and Privacy in Digital Business, 2005.']
    for ref in refs: doc.add_paragraph(ref,style='List Number')
    # core properties
    props=doc.core_properties; props.title='Composable Privacy Preserving Deck Reconstruction for Mental Poker'; props.subject='Cryptographic research paper'; props.author='poker_protocol research team'; props.keywords='Mental Poker, zero knowledge, UC security, formal verification'
    path=OUT/'composable_privacy_preserving_deck_reconstruction.docx'; doc.save(path); print(path)

def build_zh():
    make_figures()
    doc=Document(); setup_styles_zh(doc)
    sec=doc.sections[0]; sec.top_margin=Inches(0.75); sec.bottom_margin=Inches(0.7); sec.left_margin=Inches(0.82); sec.right_margin=Inches(0.82)
    header=sec.header.paragraphs[0]; header.text='面向心智扑克的可组合隐私保护牌组重建'; header.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    header.runs[0].font.size=Pt(8); header.runs[0].font.color.rgb=RGBColor.from_string(GRAY)
    footer=sec.footer.paragraphs[0]; footer.alignment=WD_ALIGN_PARAGRAPH.CENTER; footer.add_run('Poker Protocol  •  '); add_page_field(footer)
    for r in footer.runs: r.font.size=Pt(8); r.font.color.rgb=RGBColor.from_string(GRAY)

    p=doc.add_paragraph(style='Title'); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run('面向心智扑克的可组合隐私保护牌组重建')
    p=doc.add_paragraph(style='Subtitle Custom'); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run('槽位语义 跨密钥证明与机器检查组合边界')
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_before=Pt(25); p.add_run('2026 年 9 月 17 日  •  poker_protocol 代码仓库')
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_after=Pt(4)
    p.add_run('代码仓库：').bold=True; add_hyperlink(p,'github.com/linqining/poker_protocol/tree/feat/paper','https://github.com/linqining/poker_protocol/tree/feat/paper')
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_before=Pt(36)
    r=p.add_run('主张边界'); r.bold=True; r.font.color.rgb=RGBColor.from_string(BLACK)
    add_para(doc,'本文的条件 UC 定理在随机预言机模型下成立，并显式依赖 Bayer–Groth、跨密钥证明、槽位 OR 证明、认证 reveal-token 状态，以及实现与形式模型之间的字节级 refinement。Lean 检查 residual-carrier 血统、代数重建关系、跨密钥 Sigma 协议、槽位 OR 协议和组合定理；组件的计算安全性与实现 refinement 仍是明确假设，而不是由群代数自动推出的结论。','Small Note')
    doc.add_page_break()

    doc.add_heading('摘要', level=1)
    add_para(doc,'心智扑克通过加密和可验证洗牌隐藏完整牌序，但多人洗牌通常要求所有参与者完成各自步骤。一名玩家离线、崩溃或拒绝继续时，其他玩家必须在不泄露、不篡改其余牌的前提下重建下一副牌；单独的 shuffle argument 并不能解决这一活性缺口。')
    add_para(doc,'本文给出一种基于 residual carrier 的牌组重建协议。旧实现使用 `readable_card` 这一名称，但它只在恰好缺少一个 reveal token 时准确。一般地，对已提交的 reveal token 做群减法后，所得 residual carrier 加密在缺失玩家公钥之和下。缺少一个 token 时，唯一 owner 可以解密；缺少两个或更多 token 时，没有任何单个在线玩家知道原牌。协议仍可继续：只有经过认证的 owner-residual carrier 才能授权负贡献；jointly keyed 且无人可读的牌只能走零分支，因此会保留在新构造的 canonical deck 中。')
    add_para(doc,'证明系统把每个 canonical slot 的贡献限制为聚合公钥下的零加密或该槽牌点负元的加密。跨密钥证明把每个负分支连接到认证 owner-residual carrier；隐藏 shuffle 隐藏映射；二分支 OR 证明强制逐槽语义；域分离 transcript 绑定 table context、epoch、状态摘要、公钥、牌点、carrier 和 contribution。在明确假设下，接受的 proof package 可提取具有精确 owner-residual 覆盖的见证。Lean 定理 `verified_package_semantics` 将公共有效性、认证覆盖和逐槽明文隶属关系组合在一个机器检查边界中。')
    p=doc.add_paragraph(); r=p.add_run('关键词：'); r.bold=True; p.add_run('心智扑克；可验证洗牌；ElGamal；广义 Schnorr；零知识；UC 安全；形式化验证。')

    doc.add_heading('1 引言与动机', level=1)
    add_para(doc,'经典心智扑克使用公钥加密、重加密和洗牌正确性证明，让多名玩家在不知道完整牌序的条件下完成发牌和对局。这类构造通常是协作式的：下一阶段默认所有参与者完成当前步骤。真实系统中，网络中断、崩溃或恶意拒绝都可能留下尚未移除的加密层，使牌桌无法安全进入下一局。')
    add_para(doc,'本文把牌的历史血统与参与者在当前轮是否在线分离。认证状态保存 dealt ciphertext、对应 reveal-token 证明以及提交集合。重建阶段从公开 canonical deck 重新构造 aggregate-key ciphertext，并且只对由 singleton missing-token set 认证的 owner-residual carrier 允许负贡献。若同一张牌缺少两个或更多 token，旧密文仍被多个密钥共同遮蔽；协议不解密它，也不删除 canonical card，而是在新牌组中保留该牌。')
    add_para(doc,'核心难点是逐槽语义。仅证明密文多重集正确或全局线性和正确并不充分，因为相互补偿的恶意贡献可能保持总和不变，却破坏单个槽位。协议因此分别证明每个槽位只能包含零或该槽牌点的负元，并另外证明每个负分支都来自认证 owner-residual carrier。')
    doc.add_heading('主要贡献', level=2)
    add_table(doc,['编号','贡献','内容'],[
        ('1','Reveal-token 推导','从完整 ElGamal 密文严格推出 residual carrier，并区分单缺失与多缺失 token。'),
        ('2','容错重建','无人知道旧牌明文时仍可重建：jointly keyed 牌走零分支并保留在新牌组。'),
        ('3','跨密钥负元证明','在不公开牌点和映射的条件下，将 owner-residual carrier 绑定到 aggregate-key 负贡献。'),
        ('4','逐槽 OR 语义','独立证明每个槽位贡献为零或该槽牌点负元，排除补偿攻击。'),
        ('5','组合安全与形式化','给出条件 UC 模型，并由 Lean 组合组件接口、状态血统和代数语义。'),
    ],widths=[0.5,1.45,4.2])
    add_figure(doc,ASSET/'fig_protocol.png','图 1  重建路径将认证血统与当前轮参与状态分离；超时只产生无操作，不产生未经授权的负贡献。')

    doc.add_heading('2 背景与相关工作', level=1)
    add_para(doc,'Bayer–Groth 提供隐藏置换与重加密的紧凑零知识论证 [2]。Schnorr、Chaum–Pedersen 和部分知识证明支持本文所需的线性关系与析取关系 [3,4,6]；Fiat–Shamir 在随机预言机模型中把 Sigma 协议转为非交互证明 [5]。Canetti 的 UC 框架用于描述状态、调度、并发和对手消息控制 [1]。')
    add_para(doc,'Castellà-Roca、Sebé 和 Domingo-Ferrer 已研究无需可信第三方的 dropout-tolerant mental poker，并用零知识技术让游戏在玩家退出后继续 [7]。本文与其目标相近，但安全边界不同：本文显式推导 residual carrier，区分 singleton 与 multi-key missing set，并增加逐槽语义、owner-residual 精确覆盖、跨密钥证明以及机器检查组合边界。')

    doc.add_heading('3 模型与假设', level=1)
    add_para(doc,'设 q 为大素数，F_q 为标量域，G 为 q 阶加法群，g 为生成元。对公钥 P=xg，采用可加 ElGamal：')
    add_equation(doc,'Encₚ(m; r) = (rg, m + rP),      Decₓ(C) = C.c₂ − xC.c₁.')
    add_para(doc,'其同态性为')
    add_equation(doc,'Encₚ(m; r) + Encₚ(m′; r′) = Encₚ(m + m′; r + r′).')
    add_para(doc,'聚合公钥为 P=ΣₚQₚ，且 Qₚ=skₚg。canonical cards 为公开、非零、两两不同的群元素。')

    doc.add_heading('3.1 从 reveal token 推导 residual carrier', level=2)
    add_para(doc,'槽位 i 的完整加密牌为')
    add_equation(doc,'Cᵢ = Encₚ(mᵢ; rᵢ) = (rᵢg, mᵢ + rᵢP),      P = ΣₚQₚ.')
    add_para(doc,'玩家 p 的 reveal token 是第一密文分量与其私钥的标量乘：')
    add_equation(doc,'tₚ,ᵢ = skₚ Cᵢ.c₁ = skₚ(rᵢg) = rᵢQₚ.')
    add_para(doc,'附带的 Chaum–Pedersen/DLEQ 证明保证同一秘密标量同时连接 Qₚ=skₚg 和 tₚ,ᵢ=skₚCᵢ.c₁，并将证明绑定到当前牌和 epoch。令 A 为已提交有效 token 的玩家集合，U=Players−A 为缺失 token 集合，Q_U=Σₚ∈UQₚ。减去所有已认证 token：')
    add_equation(doc,'Rᵢ(A) = Cᵢ − Σₚ∈A(0,tₚ,ᵢ)')
    add_equation(doc,'= (rᵢg, mᵢ + rᵢP − rᵢΣₚ∈A Qₚ)')
    add_equation(doc,'= (rᵢg, mᵢ + rᵢQ_U) = Enc_{Q_U}(mᵢ; rᵢ).')
    add_para(doc,'这就是 residual carrier 的精确定义。若 |U|=1 且 U={q}，则 Q_U=Q_q，玩家 q 能解密 mᵢ；该特例称为 owner-residual carrier。若 |U|≥2，Q_U 是多个公钥之和，没有任何单个在线玩家拥有 sk_U=Σₚ∈Uskₚ，因此所有人都不知道原牌。若 U 为空，则结果进入明文或 redeal 边界，不应称为 residual carrier。')
    add_para(doc,'多缺失 token 并不阻止牌组重建。重建从 Bᵢ=Enc_P(mᵢ;i+1) 的新 canonical base 开始。只有 owner-residual carrier 能通过跨密钥关系授权 Enc_P(−mᵢ)；jointly keyed residual 没有可用 owner witness，所以该槽的所有接受贡献都必须是 Enc_P(0)。最终同态和仍加密 mᵢ，旧 jointly keyed ciphertext 可以丢弃，而 mᵢ 从未向任何玩家公开。')
    add_para(doc,'对 owner-residual carrier Rⱼ 及隐藏映射 i(j)，构造 Sⱼ=Enc_P(−mᵢ₍ⱼ₎;vⱼ)，并证明')
    add_equation(doc,'Q = sk_Q g,   Sⱼ.c₁ = vⱼg,   sk_Q Rⱼ.c₁ + vⱼP = Rⱼ.c₂ + Sⱼ.c₂.')
    add_para(doc,'第三个等式消去两侧的加密随机项，推出两个密文明文之和为零。Bayer–Groth 隐藏 carrier-to-slot 映射，逐槽 OR 证明再把每个 canonical slot 限制在零或负元两个分支。由此，reconstruction 的可靠性直接建立在 reveal-token 减法和认证血统之上。')
    add_figure(doc,ASSET/'fig_residual_derivation.png','图 2  Reveal-token 减法得到 residual carrier。单缺失 token 产生 owner-residual carrier；多缺失 token 产生无人单独可读的 jointly keyed carrier，其 canonical card 在新牌组中被保留。')

    assumptions=[('A1','群与编码','实现只接受素数阶子群和 canonical encoding，并正确实现群运算。'),('A2','加密隐私','ElGamal 在 DDH 或等价假设下满足 IND-CPA。'),('A3','Residual 隐私','jointly keyed residual 至少保留一层诚实、秘密、均匀的遮罩；隐私依赖相应 fresh-DLog 困难性。'),('A4','隐藏洗牌','Bayer–Groth 组件具有完备性、知识可靠性和零知识。'),('A5','线性证明','跨密钥与槽位 OR Sigma 协议具备完备性、特殊可靠性和 perfect HVZK；Fiat–Shamir 变换在 ROM 中安全。'),('A6','Transcript 组合','共享挑战与顺序组合不产生跨组件攻击，所有域标签和编码均规范化。'),('A7','认证状态与 refinement','状态摘要不可伪造，token 绑定牌和 epoch，Rust/AIR 字节编码 refine Lean statement。'),('A8','缺失集合认证','只有 singleton missing-token set 可授权负贡献；|U|≥2 时只能走零分支。'),('A9','腐化模型','腐化静态固定，诚实 owner key 或 residual masking layer 在执行结束前不泄露。')]
    add_table(doc,['编号','假设','操作含义'],assumptions,widths=[0.48,1.45,4.25])

    doc.add_heading('4 协议', level=1)
    doc.add_heading('4.1 公共 statement', level=2)
    add_equation(doc,'S = (context_digest, epoch, D_prev, P, Q, (mᵢ), (Rⱼ), (Cᵢ)).')
    add_para(doc,'Rⱼ 是认证 owner-residual ciphertext，Cᵢ 是 prover contribution。验证器 fail closed：拒绝错误版本、长度不符、identity key 或 ciphertext、重复 canonical card、空 carrier 集以及 k>n。')
    doc.add_heading('4.2 证明生成', level=2)
    for s in ['从认证 token transcript 推导每个 |U|=1 的 Rⱼ，并用 owner secret 解密，确认其明文是互不重复的 canonical card。','采样 vⱼ，构造 Sⱼ=Enc_P(−mᵢ₍ⱼ₎;vⱼ)，并为其余 n−k 个槽构造零贡献。','对贡献向量应用隐藏 permutation 和新鲜 rerandomization。','为每对 (Rⱼ,Sⱼ) 生成跨密钥证明。','生成 Bayer–Groth 隐藏洗牌证明。','为每个 canonical slot 生成二分支 OR 证明。']:
        doc.add_paragraph(s,style='List Number')
    add_para(doc,'jointly keyed |U|≥2 residual 不进入 removal-authorizing vector，因此不会生成负贡献。carrier-to-slot 映射、分支、permutation 和随机性均不出现在 wire proof 中。')
    doc.add_heading('4.3 跨密钥联合证明', level=2)
    add_para(doc,'对 R=Enc_Q(m;r) 与 S=Enc_P(−m;v)，证明者证明知道 (sk_Q,v) 满足')
    add_equation(doc,'Q = sk_Qg,      S.c₁ = vg,      sk_QR.c₁ + vP = R.c₂ + S.c₂.')
    add_para(doc,'这是跨三个群方程共享响应的 two-scalar generalized-Schnorr relation。见证不包含 r=DL(R.c₁)。该关系只对 |U|=1 实例化；|U|≥2 时协议选择零分支。')
    doc.add_heading('4.4 逐槽 OR 证明', level=2)
    add_para(doc,'对槽 i，令 T₀=Cᵢ.c₂、T₁=Cᵢ.c₂+mᵢ。证明存在 vᵢ 使 Cᵢ.c₁=vᵢg，且对某个 b∈{0,1} 有 T_b=vᵢP。b=0 表示零贡献，b=1 表示负牌贡献。标准 OR proof 诚实证明一个分支，模拟另一个分支，并强制 e₀+e₁=e。')
    doc.add_heading('4.5 聚合重建', level=2)
    add_equation(doc,'Bᵢ = Encₚ(mᵢ; i+1),      B̃ᵢ = Bᵢ + Σₚ∈S_submit Cₚ,ᵢ.')
    add_para(doc,'超时或未提交玩家没有贡献。A8 保证每个槽最多接受一个负分支。若同一张牌缺少两个或更多 reveal token，则没有 owner-residual removal authorization，故该槽只累加零贡献并保留 mᵢ。')
    add_figure(doc,ASSET/'fig_slot_semantics.png','图 3  逐槽 OR 语义与 owner-residual 精确覆盖共同保证每张认证可移除牌最多被移除一次，其余槽保持 canonical plaintext。')

    doc.add_heading('5 正确性与独立安全性', level=1)
    doc.add_heading('定理 1 完备性', level=2)
    add_para(doc,'若 statement 满足认证状态条件且诚实证明者执行第 4.2 节，则验证器除显式零挑战事件外均接受，失败概率至多为 O((n+k)/q)。owner-residual 血统给出正确跨密钥关系；jointly keyed residual 对应零分支；Bayer–Groth 和 OR 证明分别由其完备性成立。')
    doc.add_heading('定理 2 知识可靠性', level=2)
    add_para(doc,'在 A1、A4–A7 下，任何接受的 statement/proof 都可提取见证，使得每个槽位贡献加密 0 或 −mᵢ，removedᵢ 当且仅当某个认证 owner-residual index 映射到 i，映射为单射，并且每个负分支都与认证 singleton token derivation 相连。否则可归约到组件可靠性、状态认证或序列化 refinement 的失败。')
    doc.add_heading('定理 3 重建语义', level=2)
    add_para(doc,'令 χᵢ=1 当且仅当某个已接受提交者拥有授权移除 mᵢ 的认证 owner-residual carrier。则')
    add_equation(doc,'Decₚ(B̃ᵢ) = 0  若 χᵢ=1；      Decₚ(B̃ᵢ) = mᵢ  若 χᵢ=0.')
    add_para(doc,'特别地，|U|≥2 时 χᵢ=0：无人知道旧密文明文，但新牌组仍正确保留 mᵢ。')

    doc.add_heading('6 UC 理想功能与组合', level=1)
    doc.add_heading('6.1 混合模型', level=2)
    add_para(doc,'协议运行在随机预言机、认证状态以及认证 key/shuffle/reveal 功能的 hybrid 中。状态记录 canonical deck、公钥、前一局 assignment、token 血统、epoch 和 missing-key set；腐化静态固定，网络对手可重排、丢弃或延迟消息。')
    doc.add_heading('6.2 理想功能 F_RECON', level=2)
    add_para(doc,'功能以 sid=(context,table,hand,epoch,D_prev) 标识，从认证状态获得 residual derivation，但不泄露底层 plaintext。它等待 SUBMIT 或 deadline，仅删除成功提交者中由 singleton missing-token set 授权的牌；|U|≥2 的牌被保留。不一致或重叠的 removal authorization 输出 STATE_INVALID。')
    doc.add_heading('6.3 条件 UC 定理', level=2)
    add_para(doc,'定理 4　在 A1–A9 下，若 Bayer–Groth、跨密钥和槽位 OR 的 Fiat–Shamir 证明在随机预言机 hybrid 中可提取、可模拟且可并发组合，则任意静态对手/环境在 real protocol 与 F_RECON 之间的区分优势可忽略。界由组件零知识与知识可靠性误差、DDH 与 fresh-DLog 误差、状态和序列化误差以及 O((n+k)/q) 之和给出。')
    doc.add_heading('6.4 非己牌否决', level=2)
    add_para(doc,'定义 Veto(p,m) 为玩家 p 的接受 package 删除 m，但认证 singleton token derivation 未授权 p 删除 m。定理 5 给出 Pr[Veto(p,m)]≤ε_KS+ε_state+ε_ser。接受意味着提取到负分支及 owner-residual witness；若它不在认证状态中，则必须伪造状态摘要、证明或 serialization refinement。')
    add_figure(doc,ASSET/'fig_composition.png','图 4  Lean 形式化把群代数和组件接口组合为 verified_package_semantics；计算安全假设仍显式保留。')

    doc.add_heading('7 Lean 形式化', level=1)
    add_table(doc,['层','文件','机器检查结果'],[
        ('Residual 血统','ResidualCarrierProvenance.lean','authenticated_prior_hand_yields_residual_carrier'),
        ('重建关系','Reconstruction.lean','relation_complete；corrected_slot_semantics；aggregatePlaintext_unique_removal'),
        ('跨密钥 Sigma','ReconstructionJointSigma.lean','relation_iff_cross_key；sigma_complete；sigma_speciallySound；sigma_perfect_hvzk'),
        ('槽位 OR','ReconstructionSlotOr.lean','honest_accepts；specially_sound；perfect_hvzk_algebraic'),
        ('组合边界','ReconstructionSecurity.lean','verified_package_semantics'),
    ],widths=[1.25,1.9,3.0])
    add_para(doc,'Statement 保存 aggregate key、owner key、canonical cards、owner-residual carriers 和 contributions。Witness 保存 removed bitmap、随机数、carrier-to-slot 单射和 exact-coverage 条件。`verified_package_semantics` 从 well-formed statement、提取见证、代数 relation 和组件接口，一次性导出 public validity、owner-residual 精确覆盖以及逐槽零或负元语义。')
    add_para(doc,'Lean 不把 DDH、随机预言机安全、Bayer–Groth 知识可靠性或 Rust 字节级 refinement 当作群代数定理；这些条件进入 `ComponentInterface` 与 `Reduction`，从而保持信任边界可见。')

    doc.add_heading('8 实现与可复现性', level=1)
    add_table(doc,['组件','职责'],[('poker-protocol-core','曲线、ElGamal 与 transcript。'),('poker-protocol-bg','Bayer–Groth shuffle。'),('poker-protocol-proofs','重建、跨密钥和 OR 证明。'),('poker_protocol','原生 adapter、ABI 与牌局集成。'),('poker_protocol_lean','形式规范与组合定理。')],widths=[2.1,4.0])
    add_para(doc,'代码已统一使用 `residual_carrier` / `residual_carriers`；只有单 owner 解密 API 使用 `owner_residual_carrier`。ABI 字段名称已更新，但序列化字段顺序保持不变。当前 V3 producer 为每个 |U|=1 的 owner 构造 residual vector；若同一牌缺少两个或更多 token，不创建 removal-authorizing entry，canonical slot 在重建中保持不变。')
    p=doc.add_paragraph(); p.add_run('代码仓库：').bold=True; add_hyperlink(p,'https://github.com/linqining/poker_protocol/tree/feat/paper','https://github.com/linqining/poker_protocol/tree/feat/paper')
    add_para(doc,'复现命令如下：')
    add_equation(doc,'cargo test --workspace\ncd poker_protocol_lean && lake build PokerProtocolLean\ncd poker_protocol_lean && bash scripts/count_sorries.sh')

    doc.add_heading('9 局限与未来工作', level=1)
    for s in ['恶意玩家不提交仍是应用层活性事件，需要 deadline、押金或替代策略。','认证 reveal-token 血统不可省略；缺少该条件时，非己牌否决定理不成立。','协议公开 deck size、owner-residual count、公钥、canonical cards、epoch 和 state digest。','本协议对 |U|≥2 的牌采取保留策略；若业务要求在无人知道明文时仍删除该牌，需要门限关系证明与不同授权策略。','完整 UC 安全依赖可组合 Fiat–Shamir NIZK 处理；标准模型需要可提取 NIZK 或新的证明系统。','自适应腐化需要擦除或 non-committing 技术。']:
        doc.add_paragraph(s,style='List Bullet')

    doc.add_heading('10 结论', level=1)
    add_para(doc,'本文补足了协作式心智扑克中的活性缺口。Reveal-token 减法严格推出 residual carrier：单缺失 token 产生可由唯一 owner 解密的 carrier，多缺失 token 产生无人单独可读的 jointly keyed carrier。前者通过跨密钥证明授权精确删除，后者不授权负贡献并在新 canonical deck 中被保留。因此在线玩家无需知道每张旧牌的明文，也能得到可继续洗牌的正确 ElGamal 牌组。')
    add_para(doc,'逐槽 OR 语义、隐藏映射、owner-residual 精确覆盖以及状态/transcript 绑定共同排除补偿攻击与非己牌否决。Lean 的 `verified_package_semantics` 将代数关系和组件/refinement 接口连接到同一个机器检查结论，同时清楚保留计算安全假设。')

    doc.add_heading('附录 A 与 dropout-tolerant mental poker 的关系', level=1)
    add_para(doc,'Castellà-Roca、Sebé 和 Domingo-Ferrer 的工作解决了无可信第三方条件下的玩家退出问题，并提出零知识方案使游戏在 dropout 后继续 [7]。本文应将其视为直接相关的先行工作，而不是遗漏的旁支。区别在于：本文把 reveal-token transcript 推导出的 residual carrier 作为显式协议对象，并进一步规定 owner-residual 精确覆盖、hidden carrier-to-slot mapping、逐槽零或负元语义以及条件 UC/Lean 组合边界。')
    add_para(doc,'两项工作的目标互补。先行工作确立 TTP-free dropout tolerance 的可行性；本文解释 singleton 与 multi-key missing set 如何改变 carrier 的可读性和授权语义。当前构造在 |U|≥2 时保留 canonical card 而不泄露它；若要删除 jointly unknown card，则需扩展为门限证明策略。')

    doc.add_heading('参考文献', level=1)
    refs=['R. Canetti. “Universally Composable Security.” FOCS 2001.','S. Bayer and J. Groth. “Efficient Zero-Knowledge Argument for Correctness of a Shuffle.” EUROCRYPT 2012.','D. Chaum and T. Pedersen. “Wallet Databases with Observers.” CRYPTO 1992.','R. Cramer, I. Damgård, and B. Schoenmakers. “Proofs of Partial Knowledge and Simplified Design of Witness Hiding Protocols.” CRYPTO 1994.','A. Fiat and A. Shamir. “How to Prove Yourself.” CRYPTO 1986.','C.-P. Schnorr. “Efficient Identification and Signatures for Smart Cards.” CRYPTO 1989.','J. Castellà-Roca, F. Sebé, and J. Domingo-Ferrer. “Dropout-tolerant TTP-free mental poker.” Trust and Privacy in Digital Business, 2005.']
    for ref in refs: doc.add_paragraph(ref,style='List Number')
    props=doc.core_properties; props.title='面向心智扑克的可组合隐私保护牌组重建'; props.subject='密码学研究论文中文译本'; props.author='poker_protocol research team'; props.keywords='心智扑克, 零知识, UC 安全, 形式化验证'
    path=OUT/'composable_privacy_preserving_deck_reconstruction_zh.docx'; doc.save(path); print(path)

if __name__=='__main__':
    build()
    build_zh()
