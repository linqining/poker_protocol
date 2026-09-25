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
import csv
import json
import textwrap

OUT = Path('/Users/mac/projects/poker_protocol/paper')
OUT.mkdir(parents=True, exist_ok=True)
ASSET = OUT / 'figures'
ASSET.mkdir(exist_ok=True)
METADATA_PATH = OUT / 'submission_metadata.json'
EXPERIMENTS = OUT / 'experiments'

NAVY = '17365D'
BLUE = '2F75B5'
LIGHT = 'EAF2F8'
PALE = 'F6F8FB'
MID = 'D9E2F3'
GRAY = '666666'
BLACK = '000000'

DEFAULT_METADATA = {
    'title': 'Authenticated Privacy-Preserving Deck Reconstruction for Mental Poker',
    'subtitle': 'Exact carrier coverage, slot semantics, and a machine-checked composition boundary',
    'authors': [],
    'corresponding_author': None,
    'funding': None,
    'acknowledgements': None,
    'keywords': ['Mental Poker', 'zero knowledge', 'authenticated reconstruction', 'formal verification'],
}

REPOSITORY_URL = 'https://github.com/linqining/poker_protocol'

REFERENCES = [
    'R. Canetti. “Universally Composable Security: A New Paradigm for Cryptographic Protocols.” In IEEE FOCS, pp. 136–145, 2001. doi:10.1109/SFCS.2001.959888.',
    'S. Bayer and J. Groth. “Efficient Zero-Knowledge Argument for Correctness of a Shuffle.” In EUROCRYPT, LNCS 7237, pp. 263–280, 2012. doi:10.1007/978-3-642-29011-4_17.',
    'D. Chaum and T. P. Pedersen. “Wallet Databases with Observers.” In CRYPTO, LNCS 740, pp. 89–105, 1992. doi:10.1007/3-540-48071-4_7.',
    'R. Cramer, I. Damgard, and B. Schoenmakers. “Proofs of Partial Knowledge and Simplified Design of Witness Hiding Protocols.” In CRYPTO, LNCS 839, pp. 174–187, 1994. doi:10.1007/3-540-48658-5_19.',
    'A. Fiat and A. Shamir. “How To Prove Yourself: Practical Solutions to Identification and Signature Problems.” In CRYPTO, LNCS 263, pp. 186–194, 1986. doi:10.1007/3-540-47721-7_12.',
    'C.-P. Schnorr. “Efficient Identification and Signatures for Smart Cards.” In CRYPTO, LNCS 435, pp. 239–252, 1989. doi:10.1007/0-387-34805-0_22.',
    'J. Castella-Roca, F. Sebe, and J. Domingo-Ferrer. “Dropout-Tolerant TTP-Free Mental Poker.” In Trust, Privacy, and Security in Digital Business, LNCS 3592, pp. 30–40, 2005. doi:10.1007/11537878_4.',
    'J. Castella-Roca. “Contributions to Mental Poker.” PhD thesis, Universitat Autonoma de Barcelona, 2005.',
    'A. Barnett and N. P. Smart. “Mental Poker Revisited.” In Cryptography and Coding, LNCS 2898, pp. 370–383, 2003. doi:10.1007/978-3-540-40974-8_29.',
    'K. Kurosawa, Y. Katayama, and W. Ogata. “Reshufflable and Laziness Tolerant Mental Card Game Protocol.” IEICE Transactions on Fundamentals, 1997.',
    'W. H. Soo, A. Samsudin, and A. Goh. “Efficient Mental Card Shuffling via Optimised Arbitrary-Sized Benes Permutation Network.” In Information Security, LNCS 2433, pp. 446–458, 2002. doi:10.1007/3-540-45811-5_35.',
    'I. Bentov, R. Kumaresan, and A. Miller. “Instantaneous Decentralized Poker.” In ASIACRYPT, LNCS 10625, pp. 410–440, 2017. doi:10.1007/978-3-319-70697-9_15.',
    'B. David, R. Dowsley, and M. Larangeira. “Kaleidoscope: An Efficient Poker Protocol with Payment Distribution and Penalty Enforcement.” In Financial Cryptography and Data Security, LNCS 10958, pp. 500–519, 2018. doi:10.1007/978-3-662-58387-6_27.',
    'B. David, R. Dowsley, and M. Larangeira. “ROYALE: A Framework for Universally Composable Card Games with Financial Rewards and Penalties Enforcement.” In Financial Cryptography and Data Security, LNCS 11598, pp. 282–300, 2019. doi:10.1007/978-3-030-32101-7_18.',
    'T. ElGamal. “A Public Key Cryptosystem and a Signature Scheme Based on Discrete Logarithms.” IEEE Transactions on Information Theory, vol. 31, no. 4, pp. 469–472, 1985. doi:10.1109/TIT.1985.1057074.',
    'S. Goldwasser, S. Micali, and C. Rackoff. “The Knowledge Complexity of Interactive Proof Systems.” SIAM Journal on Computing, vol. 18, no. 1, pp. 186–208, 1989. doi:10.1137/0218012.',
    'M. Blum, P. Feldman, and S. Micali. “Non-Interactive Zero-Knowledge and Its Applications.” In ACM STOC, pp. 103–112, 1988. doi:10.1145/62212.62222.',
    'M. Bellare and P. Rogaway. “Random Oracles Are Practical: A Paradigm for Designing Efficient Protocols.” In ACM CCS, pp. 62–73, 1993. doi:10.1145/168588.168596.',
    'D. Pointcheval and J. Stern. “Security Proofs for Signature Schemes.” In EUROCRYPT, LNCS 1070, pp. 387–398, 1996. doi:10.1007/3-540-68339-9_33.',
    'M. Fischlin. “Communication-Efficient Non-Interactive Proofs of Knowledge with Online Extractors.” In CRYPTO, LNCS 3621, pp. 152–168, 2005. doi:10.1007/11535218_10.',
    'D. Unruh. “The Fiat-Shamir Transformation in a Quantum World.” In ASIACRYPT, LNCS 8270, pp. 1–18, 2013. doi:10.1007/978-3-642-42045-0_4.',
    'J. Furukawa and K. Sako. “An Efficient Scheme for Proving a Shuffle.” In CRYPTO, LNCS 2139, pp. 368–387, 2001. doi:10.1007/3-540-44647-8_22.',
    'C. A. Neff. “A Verifiable Secret Shuffle and Its Application to E-Voting.” In ACM CCS, pp. 116–125, 2001. doi:10.1145/501983.502000.',
    'J. Groth. “A Verifiable Secret Shuffle of Homomorphic Encryptions.” Journal of Cryptology, vol. 23, pp. 546–579, 2010. doi:10.1007/s00145-010-9067-9.',
    'D. Wikstrom. “A Universally Composable Mix-Net.” In TCC, LNCS 2951, pp. 317–335, 2004. doi:10.1007/978-3-540-24638-1_18.',
    'J. Groth and A. Sahai. “Efficient Non-Interactive Proof Systems for Bilinear Groups.” In EUROCRYPT, LNCS 4965, pp. 415–432, 2008. doi:10.1007/978-3-540-78967-3_19.',
    'M. Belenkiy, M. Chase, C. C. Erway, J. Jannotti, A. Kupcu, A. Lysyanskaya, and E. Rachlin. “Simulation-Sound NIZK Proofs for a Practical Language and Constant Size Group Signatures.” In ASIACRYPT, LNCS 4284, pp. 444–459, 2006. doi:10.1007/11935230_29.',
    'G. Barthe, B. Gregoire, S. Heraud, and S. Zanella Beguelin. “Computer-Aided Cryptographic Proofs.” In ITP, LNCS 7406, pp. 11–27, 2012. doi:10.1007/978-3-642-33125-1_1.',
    'A. Lochbihler. “CryptHOL: Game-Based Proofs in Higher-Order Logic.” Journal of Cryptology, vol. 33, pp. 494–566, 2020. doi:10.1007/s00145-019-09341-z.',
    'J. B. Almeida, M. Barbosa, G. Barthe, A. Blot, B. Gregoire, V. Laporte, T. Oliveira, H. Pacheco, B. Schmidt, and P.-Y. Strub. “Jasmin: High-Assurance and High-Speed Cryptography.” In ACM CCS, pp. 1807–1823, 2017. doi:10.1145/3133956.3134078.',
    'J.-K. Zinzindohoue, K. Bhargavan, J. Protzenko, and B. Beurdouche. “HACL*: A Verified Modern Cryptographic Library.” In ACM CCS, pp. 1789–1806, 2017. doi:10.1145/3133956.3134043.',
    'K. Bonawitz et al. “Practical Secure Aggregation for Privacy-Preserving Machine Learning.” In ACM CCS, pp. 1175–1191, 2017. doi:10.1145/3133956.3133982.',
    'J. H. Bell, K. A. Bonawitz, A. Gascon, T. Lepoint, and M. Raykova. “Secure Single-Server Aggregation with (Poly)Logarithmic Overhead.” In ACM CCS, pp. 1253–1269, 2020. doi:10.1145/3372297.3417885.',
    'D. Mouris and N. G. Tsoutsos. “Zilch: A Framework for Deploying Transparent Zero-Knowledge Proofs.” IEEE TIFS, vol. 16, pp. 3269–3284, 2021. doi:10.1109/TIFS.2021.3074869.',
    'A. Bay, Z. Erkin, J.-H. Hoepman, S. Samardjiska, and J. Vos. “Practical Multi-Party Private Set Intersection Protocols.” IEEE TIFS, vol. 17, pp. 1–15, 2022. doi:10.1109/TIFS.2021.3118879.',
    'B. Mennink. “Secure Distributed Modular Exponentiation: Systematic Analysis and New Results.” IEEE TIFS, vol. 18, pp. 4188–4197, 2023. doi:10.1109/TIFS.2023.3293396.',
    'X. Cao, Z. Yang, J. Ning, C. Jin, R. Lu, Z. Liu, and J. Zhou. “Dynamic Group Time-Based One-Time Passwords.” IEEE TIFS, vol. 19, pp. 4897–4913, 2024. doi:10.1109/TIFS.2024.3386350.',
    'A. Haas, A. Rossberg, D. L. Schuff, B. L. Titzer, M. Holman, D. Gohman, L. Wagner, A. Zakai, and J. Bastien. “Bringing the Web up to Speed with WebAssembly.” In ACM PLDI, pp. 185–200, 2017. doi:10.1145/3062341.3062363.',
    'J. Groth. “On the Size of Pairing-Based Non-Interactive Arguments.” In EUROCRYPT, LNCS 9666, pp. 305–326, 2016. doi:10.1007/978-3-662-49896-5_11.',
    'E. Ben-Sasson, A. Chiesa, C. Garman, M. Green, I. Miers, E. Tromer, and M. Virza. “Zerocash: Decentralized Anonymous Payments from Bitcoin.” In IEEE Symposium on Security and Privacy, pp. 459–474, 2014. doi:10.1109/SP.2014.36.',
    'A. Shamir, R. L. Rivest, and L. M. Adleman. “Mental Poker.” In The Mathematical Gardner, pp. 37–43. Prindle, Weber, and Schmidt, 1981. doi:10.1007/978-1-4684-6686-7_5.',
    'S. Goldwasser and S. Micali. “Probabilistic Encryption and How to Play Mental Poker Keeping Secret All Partial Information.” In ACM STOC, pp. 365–377, 1982. doi:10.1145/800070.802212.',
    'B. David, R. Dowsley, and M. Larangeira. “21 - Bringing Down the Complexity: Fast Composable Protocols for Card Games Without Secret State.” In ACISP, LNCS 11046, pp. 45–63, 2018. doi:10.1007/978-3-319-93638-3_4.',
    'T. Oozu, M. Ishii, and K. Tanaka. “Dropout-Tolerant Mental Poker Protocol with Small Deposit and Optimal Upper Bound on Number of Dropouts.” In Symposium on Cryptography and Information Security, 2020.',
    'T.-J. Wei. “Secure and Practical Constant Round Mental Poker.” Information Sciences, vol. 280, pp. 386–396, 2014. doi:10.1016/j.ins.2014.02.151.',
    'T.-J. Wei. “Communication Efficient Shuffle for Mental Poker Protocols.” Information Sciences, vol. 181, no. 22, pp. 4661–4671, 2011. doi:10.1016/j.ins.2011.06.018.',
    'X. Bultel and P. Lafourcade. “Secure Trick-Taking Game Protocols: How to Play Online Spades with Cheaters.” In Financial Cryptography and Data Security, 2019. https://eprint.iacr.org/2019/375.',
    'R. Bella, X. Bultel, C. Chevalier, P. Lafourcade, and C. Olivier-Anclin. “Practical Construction for Secure Trick-Taking Games Even with Cards Set Aside.” In Financial Cryptography and Data Security, LNCS 13955, pp. 166–181, 2023. doi:10.1007/978-3-031-47754-6_10.',
    'D. Beaver. “Extending Mental Poker.” Cryptology ePrint Archive, Paper 2025/1821, 2025. https://eprint.iacr.org/2025/1821.',
]

TABLE_INDEX = 0
TABLE_LABEL = 'TABLE'
TWO_COLUMN_BODY = False

def submission_metadata():
    metadata = dict(DEFAULT_METADATA)
    if METADATA_PATH.exists():
        with METADATA_PATH.open(encoding='utf-8') as handle:
            metadata.update(json.load(handle))
    return metadata

def author_block(metadata):
    if not metadata.get('authors'):
        return 'Author names and affiliations must be supplied before submission'
    rendered = []
    for author in metadata['authors']:
        if isinstance(author, str):
            rendered.append(author)
            continue
        name = ' '.join(part for part in [author.get('first_name'), author.get('last_name')] if part)
        affiliation = author.get('affiliation')
        rendered.append(f'{name} ({affiliation})' if affiliation else name)
    return '; '.join(rendered)

def author_identity_lines(metadata, include_corresponding=True):
    lines = []
    for author in metadata.get('authors', []):
        if not isinstance(author, dict):
            continue
        name = ' '.join(part for part in [author.get('first_name'), author.get('last_name')] if part)
        details = []
        if author.get('email'):
            details.append(author['email'])
        if author.get('orcid'):
            details.append(f"ORCID {author['orcid']}")
        if author.get('is_corresponding') and include_corresponding:
            details.append('corresponding author')
        if name and details:
            lines.append(f"{name}: " + ' · '.join(details))
    return lines

def arxiv_metadata(metadata):
    value = metadata.get('arxiv')
    if not isinstance(value, dict):
        raise ValueError('paper/submission_metadata.json must contain an arxiv object')
    return value

def arxiv_author_field(metadata):
    rendered = []
    for author in metadata.get('authors', []):
        if not isinstance(author, dict):
            continue
        name = ' '.join(part for part in [author.get('first_name'), author.get('last_name')] if part)
        affiliation = author.get('affiliation')
        rendered.append(f'{name} ({affiliation})' if affiliation else name)
    return ', '.join(rendered)

def write_arxiv_submission_fields(metadata):
    arxiv = arxiv_metadata(metadata)
    secondary = ', '.join(arxiv.get('secondary_categories', []))
    fields = [
        f"Title: {metadata['title']}",
        f"Authors: {arxiv_author_field(metadata)}",
        f"Abstract: {arxiv['abstract'].replace(chr(10) + chr(10), ' ')}",
        f"Comments: {arxiv['comments']}",
        f"Primary category: {arxiv['primary_category']}",
        f"Secondary categories: {secondary}",
        f"License: {arxiv['license']}",
    ]
    for label, key in [('Report number', 'report_number'), ('Journal ref', 'journal_ref'), ('DOI', 'doi')]:
        if arxiv.get(key):
            fields.append(f'{label}: {arxiv[key]}')
    path = OUT / 'arxiv_submission_fields.txt'
    path.write_text('\n'.join(fields) + '\n', encoding='utf-8')
    return path

def validate_submission_metadata(metadata):
    if not metadata.get('authors'):
        raise ValueError('paper/submission_metadata.json authors must be filled before DOCX generation')
    arxiv = arxiv_metadata(metadata)
    for key in ['primary_category', 'license', 'comments', 'abstract']:
        if not arxiv.get(key):
            raise ValueError(f'arxiv.{key} must be filled for an arXiv preprint')
    abstract = arxiv['abstract']
    if not abstract.isascii():
        raise ValueError('The arXiv abstract metadata must contain only ASCII characters')
    if len(abstract) > 1920:
        raise ValueError('The arXiv abstract metadata exceeds the 1,920-character limit')
    comments = arxiv['comments']
    if not comments.isascii():
        raise ValueError('The arXiv comments metadata must contain only ASCII characters')

def benchmark_rows(filename):
    with (EXPERIMENTS / filename).open(newline='', encoding='utf-8') as handle:
        return {
            (int(row['n']), int(row['k'])): row
            for row in csv.DictReader(handle)
        }

def native_ms(row, field):
    return float(row[field]) / 1000.0

def ns_ms(row, field):
    return float(row[field]) / 1_000_000.0

def timing_summary(row, prefix, native=False):
    suffix = 'us' if native else 'ms'
    scale = 1000.0 if native else 1.0
    median = float(row[f'{prefix}_median_{suffix}']) / scale
    mean = float(row[f'{prefix}_mean_{suffix}']) / scale
    stddev = float(row[f'{prefix}_stddev_{suffix}']) / scale
    p95 = float(row[f'{prefix}_p95_{suffix}']) / scale
    return f'{median:.1f} / {mean:.1f}±{stddev:.1f} / {p95:.1f} ms'

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
    d.multiline_text((900,215),'Subtract\nsubmitted tokens',font=bold,fill='#'+NAVY,anchor='ma',align='center',spacing=2)
    d.text((900,320),'t_p,i = r_i Q_p',font=font,fill='#'+BLACK,anchor='ma')
    d.multiline_text((900,390),'C_i - sum t_p,i\nfor p in A',font=small,fill='#'+BLACK,anchor='ma',align='center',spacing=2)
    d.line((1040,325,1240,325),fill='#'+BLUE,width=7); d.polygon([(1240,325),(1220,312),(1220,338)],fill='#'+BLUE)
    d.rounded_rectangle((1240,170,1710,480),radius=22,fill='#'+LIGHT,outline='#'+BLUE,width=4)
    d.text((1475,225),'Residual carrier',font=bold,fill='#'+NAVY,anchor='ma')
    d.text((1475,310),'Enc_Q_U(m_i; r_i)',font=font,fill='#'+BLACK,anchor='ma')
    d.text((1475,370),'Q_U = sum Q_p for p in U',font=small,fill='#'+BLACK,anchor='ma')
    d.text((1475,425),'U = Players minus A',font=small,fill='#'+BLACK,anchor='ma')
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
    left=[('Group / encoding','A1'),('ElGamal privacy','A2-A3'),('Concrete proofs','A4-A5'),('Ideal NIZK hybrid','A6'),('State / corruption','A7-A9')]
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
    d.text((1525,275),'F_NIZK hybrid',font=bold,fill='#'+NAVY,anchor='ma')
    d.text((1525,360),'session-bound ideal proofs',font=font,fill='#'+BLACK,anchor='ma')
    d.text((1525,445),'real protocol ~ F_RECON',font=font,fill='#'+BLACK,anchor='ma')
    d.text((1525,530),'no concrete FS-to-UC\ninstantiation claim',font=small,fill='#'+GRAY,anchor='ma')
    im.save(ASSET/'fig_composition.png',dpi=(180,180))

def setup_styles(doc):
    styles=doc.styles
    normal=styles['Normal']; normal.font.name='Aptos'; normal.font.size=Pt(10.5); normal.font.color.rgb=RGBColor.from_string(BLACK)
    normal._element.rPr.rFonts.set(qn('w:eastAsia'),'Aptos')
    normal.paragraph_format.space_after=Pt(6); normal.paragraph_format.line_spacing=1.08
    for name,size,color in [('Title',25,BLACK),('Heading 1',15,BLACK),('Heading 2',12,BLACK),('Heading 3',11,BLACK)]:
        st=styles[name]; st.font.name='Aptos Display'; st.font.size=Pt(size); st.font.bold=True; st.font.color.rgb=RGBColor.from_string(color)
        st.paragraph_format.space_before=Pt(14 if name!='Title' else 0); st.paragraph_format.space_after=Pt(6); st.paragraph_format.keep_with_next=True
        ppr=st._element.get_or_add_pPr()
        pbdr=ppr.find(qn('w:pBdr'))
        if pbdr is not None:
            ppr.remove(pbdr)
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
        st.font.name = 'Arial Unicode MS'
        st._element.rPr.rFonts.set(qn('w:eastAsia'), 'Arial Unicode MS')
    doc.styles['Equation'].font.name = 'Cambria Math'
    doc.styles['Equation']._element.rPr.rFonts.set(qn('w:eastAsia'), 'Cambria Math')

def add_para(doc, text='', style=None, bold_prefix=None):
    p=doc.add_paragraph(style=style)
    if bold_prefix and text.startswith(bold_prefix):
        p.add_run(bold_prefix).bold=True; p.add_run(text[len(bold_prefix):])
    else: p.add_run(text)
    return p

def add_references(doc, refs):
    for index, ref in enumerate(refs, start=1):
        p=doc.add_paragraph(style='Normal')
        p.paragraph_format.left_indent=Inches(0.25)
        p.paragraph_format.first_line_indent=Inches(-0.25)
        p.paragraph_format.space_after=Pt(1)
        p.paragraph_format.line_spacing=1.0
        run = p.add_run(f'[{index}] {ref}')
        run.font.size = Pt(8)

def add_equation(doc, text):
    p = doc.add_paragraph(style='Equation')
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(text)
    return p

def add_figure(doc, path, caption, width=None):
    if width is None:
        width = 3.18 if TWO_COLUMN_BODY else 6.25
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
    global TABLE_INDEX
    caption = getattr(add_table, '_caption', None)
    if caption and TABLE_LABEL:
        TABLE_INDEX += 1
        roman = ['I','II','III','IV','V','VI','VII','VIII','IX','X','XI','XII'][TABLE_INDEX - 1]
        p = doc.add_paragraph(style='Caption Custom')
        p.paragraph_format.keep_with_next = True
        p.add_run(f'{TABLE_LABEL} {roman}. {caption}')
        add_table._caption = None
    t=doc.add_table(rows=1, cols=len(headers)); t.alignment=WD_TABLE_ALIGNMENT.CENTER; t.style='Table Grid'; t.autofit=False
    hdr=t.rows[0]; set_repeat_table_header(hdr); set_row_cant_split(hdr)
    for j,h in enumerate(headers):
        cell=hdr.cells[j]; set_cell_shading(cell,NAVY); set_cell_border(cell); set_cell_margins(cell)
        cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
        p=cell.paragraphs[0]; p.alignment=WD_ALIGN_PARAGRAPH.CENTER; r=p.add_run(h); r.bold=True; r.font.color.rgb=RGBColor(255,255,255); r.font.size=Pt(7.4 if TWO_COLUMN_BODY else 9.5)
    for i,row in enumerate(rows):
        added_row=t.add_row(); set_row_cant_split(added_row); cells=added_row.cells
        for j,val in enumerate(row):
            cell=cells[j]; set_cell_border(cell); set_cell_margins(cell); cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if i%2==1: set_cell_shading(cell,'F7F9FC')
            p=cell.paragraphs[0]; p.alignment=WD_ALIGN_PARAGRAPH.LEFT; r=p.add_run(val); r.font.size=Pt(7.1 if TWO_COLUMN_BODY else 9.2)
    if widths:
        if TWO_COLUMN_BODY and sum(widths) > 3.18:
            scale = 3.18 / sum(widths)
            widths = [w * scale for w in widths]
        if TWO_COLUMN_BODY and widths:
            min_first = 0.48 if headers[0] in ('No.', 'ID') else 0.34
            if widths[0] < min_first:
                deficit = min_first - widths[0]
                widths[0] = min_first
                donor = max(range(1, len(widths)), key=lambda i: widths[i])
                widths[donor] = max(0.30, widths[donor] - deficit)
        # python-docx cell.width alone leaves tblGrid at its default page
        # width. Write all three OOXML width representations explicitly so
        # column layout is honored by both Word and LibreOffice.
        widths_twips = [max(240, int(round(w * 1440))) for w in widths]
        tbl = t._tbl
        tbl_pr = tbl.tblPr
        tbl_w = tbl_pr.find(qn('w:tblW'))
        if tbl_w is None:
            tbl_w = OxmlElement('w:tblW'); tbl_pr.append(tbl_w)
        tbl_w.set(qn('w:type'), 'dxa'); tbl_w.set(qn('w:w'), str(sum(widths_twips)))
        grid = tbl.tblGrid
        for child in list(grid):
            grid.remove(child)
        for w in widths_twips:
            col = OxmlElement('w:gridCol'); col.set(qn('w:w'), str(w)); grid.append(col)
        for row in t.rows:
            for cell,w in zip(row.cells,widths): cell.width=Inches(w)
            for cell,w_twips in zip(row.cells,widths_twips):
                tc_pr = cell._tc.get_or_add_tcPr()
                tc_w = tc_pr.find(qn('w:tcW'))
                if tc_w is None:
                    tc_w = OxmlElement('w:tcW'); tc_pr.append(tc_w)
                tc_w.set(qn('w:type'), 'dxa'); tc_w.set(qn('w:w'), str(w_twips))
    doc.add_paragraph().paragraph_format.space_after=Pt(1)
    return t

def next_table_caption(caption):
    add_table._caption = caption

def set_two_columns(section, space_twips=360):
    sect_pr = section._sectPr
    cols = sect_pr.find(qn('w:cols'))
    if cols is None:
        cols = OxmlElement('w:cols')
        sect_pr.append(cols)
    cols.set(qn('w:num'), '2')
    cols.set(qn('w:space'), str(space_twips))

def build():
    global TABLE_INDEX, TABLE_LABEL, TWO_COLUMN_BODY
    TABLE_INDEX = 0; TABLE_LABEL = 'TABLE'; add_table._caption = None
    metadata = submission_metadata(); validate_submission_metadata(metadata)
    make_figures()
    doc=Document(); setup_styles(doc)
    sec=doc.sections[0]; sec.top_margin=Inches(0.75); sec.bottom_margin=Inches(0.7); sec.left_margin=Inches(0.82); sec.right_margin=Inches(0.82)
    # header/footer
    header=sec.header.paragraphs[0]; header.text='AUTHENTICATED PRIVACY-PRESERVING DECK RECONSTRUCTION'; header.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    header.runs[0].font.size=Pt(8); header.runs[0].font.color.rgb=RGBColor.from_string(GRAY)
    footer=sec.footer.paragraphs[0]; footer.alignment=WD_ALIGN_PARAGRAPH.CENTER; footer.add_run('Poker Protocol  •  '); add_page_field(footer)
    for r in footer.runs: r.font.size=Pt(8); r.font.color.rgb=RGBColor.from_string(GRAY)
    # title page
    p=doc.add_paragraph(style='Title'); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run(metadata['title'])
    p=doc.add_paragraph(style='Subtitle Custom'); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run(metadata['subtitle'])
    arxiv=arxiv_metadata(metadata)
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_before=Pt(25); p.add_run('Preprint | September 25, 2026 | arXiv subject: ' + arxiv['primary_category'])
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run(author_block(metadata))
    structured_corresponding = any(
        isinstance(author, dict) and author.get('is_corresponding')
        for author in metadata.get('authors', [])
    )
    metadata_lines = [('Funding:', metadata.get('funding')), ('Acknowledgements:', metadata.get('acknowledgements'))]
    if not structured_corresponding:
        metadata_lines.insert(0, ('Corresponding author:', metadata.get('corresponding_author')))
    for label, value in metadata_lines:
        if value:
            p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; r=p.add_run(label+' '); r.bold=True; p.add_run(str(value))
    for identity_line in author_identity_lines(metadata, include_corresponding=False):
        p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run(identity_line)
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_after=Pt(4)
    p.add_run('Source repository: ').bold=True; add_hyperlink(p,'github.com/linqining/poker_protocol',REPOSITORY_URL)
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run('Article license: ' + arxiv['license'])
    body_sec = doc.add_section(WD_SECTION.CONTINUOUS)
    body_sec.top_margin=Inches(0.62); body_sec.bottom_margin=Inches(0.62); body_sec.left_margin=Inches(0.7); body_sec.right_margin=Inches(0.7)
    set_two_columns(body_sec)
    TWO_COLUMN_BODY = True
    # abstract + metadata
    doc.add_heading('Abstract', level=1)
    for paragraph in arxiv['abstract'].split('\n\n'):
        add_para(doc, paragraph)
    p=doc.add_paragraph(); p.paragraph_format.space_before=Pt(8); r=p.add_run('Keywords. '); r.bold=True; p.add_run('Mental Poker; verifiable shuffle; ElGamal; authenticated reconstruction; non-interactive zero knowledge; formal verification.')
    doc.add_heading('1. Introduction and motivation', level=1)
    add_para(doc,'Mental Poker protocols use public-key encryption, re-encryption, and proofs of correct shuffling to let several players deal and play without revealing the deck. The basic multiplayer construction is cooperative: each player applies a private shuffle or masking step, and the next phase assumes that all required steps are completed. This assumption is reasonable for a synchronous toy protocol, but it is a serious availability problem for a real table. A player may disconnect, crash, or deliberately refuse to continue. If the cards still contain that player’s encryption layer, the remaining players cannot simply delete the layer or guess which cards belonged to the absent player. The deck then cannot be safely reconstructed.')
    add_para(doc,'The central contribution of this work is to separate card provenance from the absent user’s participation in the current round. During normal play, the table state records authenticated residual ciphertexts together with the reveal-token lineage that produced them. After one or more players fail to submit a token, an active participant can use each decryptable owner-residual carrier to construct a reconstruction proof. The proof removes exactly those authorized cards, preserves every other canonical card, and exposes neither the mapping nor the card values. A jointly keyed residual that no player can decrypt authorizes no negative branch, so its canonical card remains in the new deck. Thus the table can proceed without requiring every previous card plaintext to be known by an online player.')
    add_para(doc,'Let the canonical deck be a public, duplicate-free sequence of curve points M = (m₀,…,mₙ₋₁). A card is initially encrypted under the aggregate key P = Σₚ Qₚ. For each residual derivation, let A be the set of players whose reveal tokens were submitted for that carrier and let U be the corresponding carrier-specific missing-token set; |U| is not the total number of absent players. The residual is encrypted under Q_U = Σₚ∈U Qₚ. The special case |U| = 1 is an owner-residual carrier; the general case |U| ≥ 2 is jointly keyed. Reconstruction must preserve this distinction while ensuring that the owner-to-slot mapping and branch choices remain hidden and the output remains a valid ElGamal deck for the next shuffle.')
    add_para(doc,'The difficult part is slot semantics. A proof of a ciphertext multiset or of a global linear sum is insufficient: compensating ciphertexts can make the sum look correct while changing an individual slot. The protocol therefore proves the allowed plaintext relation independently for every slot, and separately proves that each negative branch is linked to an authenticated residual carrier.')
    doc.add_heading('Contributions', level=2)
    contributions=[('1','Reveal-token derivation','We derive the residual carrier by subtracting submitted reveal tokens and distinguish the owner-residual and jointly keyed cases.'),('2','Liveness-aware reconstruction','Authenticated residual carriers allow an active table to rebuild after non-participation; a deadline is a no-op event, not a plaintext disclosure.'),('3','Aggregate-key encryption','All contributions use the same aggregate key P, so the reconstructed deck retains the standard ElGamal shape.'),('4','Cross-key negation proof','For an authenticated carrier and a negative contribution under P, the prover proves the required ciphertext relation without exposing the card or its mapping.'),('5','Per-slot OR semantics','Each canonical slot is proven to contain either an encryption of zero or an encryption of the slot’s negative card.'),('6','State and transcript binding','The table context, epoch, previous-state digest, public keys, canonical cards, residual carriers, and contributions are bound into a domain-separated transcript.'),('7','Explicit hybrid model','We define F_RECON command by command and prove static-corruption composition in the F_NIZK^R_RECON hybrid without claiming a concrete Fiat-Shamir UC instantiation.'),('8','Machine-checked composition','Lean derives end-to-end package semantics from explicit component and refinement interfaces.')]
    next_table_caption('Summary of contributions')
    add_table(doc,['No.','Contribution','Statement'],contributions,widths=[0.42,1.55,4.15])
    add_figure(doc,ASSET/'fig_protocol.png','Figure 1. The reconstruction path separates authenticated provenance from current-round participation. A missed deadline contributes no fresh proof and therefore has no effect on the aggregate deck.')

    doc.add_heading('2. Background and related work', level=1)
    add_para(doc,'The original Mental Poker problem asked players to deal and play cards without revealing hidden state [41,42]. Practical constructions combine ElGamal encryption [15] with successive private shuffles; constant-round and communication-efficient protocols refine the full-game interface [45,46]. Bayer–Groth [2], Furukawa–Sako [22], Neff [23], Groth [24], and universally composable mixnets [25] establish different efficiency and composition points for verifiable shuffling. Schnorr, Chaum–Pedersen, and partial-knowledge protocols provide the linear and disjunctive relations used here [3,4,6]. These components prove permutation or relation correctness; they do not authenticate which prior-state carrier authorizes removal from a new canonical deck.')
    add_para(doc,'Beaver’s 2025 study of extending Mental Poker addresses OT amplification/extraction, ordinary-deck base-OT construction, and two-player/card-cryptography foundations [49]. Its focus is therefore below the multiplayer reconstruction interface addressed here: it establishes a different primitive layer and does not state a state-bound residual-carrier language, per-slot zero-or-negative package relation, browser cost grid, or Lean composition boundary.')
    add_para(doc,'Fiat–Shamir [5], the random-oracle methodology [18], classical forking analyses [19], online extractors [20], and quantum-ROM analyses [21] give distinct security guarantees and should not be conflated with UC realization. CRS-based NIZK ranges from the original feasibility result [17] to pairing-based and simulation-sound systems [26,27]. Our UC statement therefore uses a session-bound ideal NIZK functionality for the aggregate relation. The Poseidon Fiat–Shamir code is evaluated as a concrete standalone implementation; this paper does not prove that it realizes that ideal functionality under concurrent scheduling.')
    add_para(doc,'Formal cryptographic developments such as EasyCrypt [28], CryptHOL [29], Jasmin [30], and HACL* [31] illustrate progressively stronger links between proofs and executable code. Our Lean development is narrower but not purely paper-only: it checks the reconstruction algebra and composition boundary, and the Rust/Lean fixtures cross-check a complete statement schema and one seeded proof-instance schema. Group implementation, component proof-system guarantees, concrete Fiat--Shamir realization, full byte-level serialization refinement, and authenticated host state remain explicit obligations. This scope is materially different from a verified implementation claim.')
    add_para(doc,'Dropout-resistant secure aggregation [32,33] addresses a related liveness problem in collaborative encrypted state, although its output semantics are aggregate vectors rather than a hidden card permutation. TIFS systems such as Zilch [34], practical multi-party PSI [35], secure distributed modular exponentiation [36], and dynamic group authentication [37] show the journal’s interest in implementations that connect proof systems, group protocols, and measured costs. WebAssembly deployment [38] and succinct circuit systems [39,40] motivate our browser and scoped Circom measurements, but they do not provide a functionally equivalent reconstruction baseline.')
    add_para(doc,'Barnett–Smart [9] supplies the widely reused ElGamal mental-poker foundation and shuffle verification. Kurosawa et al. [10] and Soo et al. [11] tolerate bounded absence or lazy updates using secret sharing and rearrangeable networks, but the fixed threshold and coalition recovery capability are security costs. The 21 protocol reduces complexity for composable card games without secret state [43], while Oozu, Ishii, and Tanaka study dropout tolerance with a small deposit and an optimal upper bound on the number of dropouts [44]. Newer financially enforced designs — Instantaneous Decentralized Poker [12], Kaleidoscope [13], and ROYALE [14] — strengthen collateral, penalties, and composable payment semantics. Their absence handling is primarily forfeiture, timeout, restart, or an economic policy; they do not derive per-carrier removal authorization from authenticated reveal-token lineage, nor do they prove the per-slot {0,−m_i} relation central to reconstruction.')
    add_para(doc,'A separate line enforces the rules of trick-taking games. Bultel and Lafourcade define secure online Spades and prevent a player from violating hidden play constraints [47]. Bella et al. extend that model to games with cards set aside, use partially homomorphic ciphertexts and a generic shuffle argument, and report a Rust implementation [48]. That work addresses play legality and set-aside-card semantics; it does not reconstruct a next-round aggregate-key deck from authenticated residual carriers after a participant fails to submit reveal tokens.')
    add_para(doc,'The protocol layers are therefore complementary rather than interchangeable. A complete deployment may need a full dealing and rule-compliance protocol, an economic dropout policy, and the reconstruction layer defined here. Table II summarizes this boundary without treating incomparable runtime numbers as a ranking.')
    next_table_caption('Position among secure card-game protocol layers')
    add_table(doc,['Protocol family','What it establishes','Boundary with this work'],[
        ('Foundations and efficient full games [9,41–43,45,46,49]','ElGamal deck representation, shuffling, dealing, OT/card-cryptography foundations, round/communication efficiency, and composable game execution.','Primarily assumes the required players or state transitions remain available; no authenticated residual-carrier removal semantics.'),
        ('Dropout and financial enforcement [7,12–14,44]','Continues after absence or enforces deposits, penalties, payouts, and bounded dropout behavior.','Provides liveness or economic incentives, but not exact per-card singleton authorization or the zero-or-negative slot relation.'),
        ('Trick-taking rule enforcement [47,48]','Hidden hand legality, play constraints, and set-aside-card game semantics.','Secures moves within a game rather than rebuilding the next aggregate-key deck from a prior authenticated state.'),
        ('This reconstruction layer','Authenticated owner-residual lineage, exact coverage, hidden carrier-to-slot mapping, per-slot plaintext membership, and a Lean composition boundary.','Does not replace dealing, rule enforcement, payments, penalties, or a complete game lifecycle.'),
    ],widths=[1.25,2.05,2.75])
    add_para(doc,'Those ingredients do not by themselves solve the departure problem. A shuffle proof can show that an output is a re-encrypted permutation of an input, but it does not say that a particular output slot contains either the original card or an identity correction. Nor does it identify which correction is authorized by the authenticated history of the table. Our protocol adds the missing reconstruction layer: hidden shuffling protects the mapping, the slot OR proof restricts plaintexts, the cross-key proof links a negative contribution to an authenticated owner-residual carrier, and the state digest authenticates the card’s provenance.')
    add_para(doc,'Earlier TTP-free routes either asked a departing player to reveal its secret layer or used secret sharing to tolerate a fixed number of absentees; the latter permits a sufficiently large coalition to recover the deck. The closest liveness construction [7] instead uses CDS partial-knowledge proofs and veto factors, so the remaining table can continue without the departed player’s cooperation.')
    add_para(doc,'To compare protocol boundaries without inventing runtime numbers, let N denote active players in [7], d=52 cards, and r prior dealing rounds. Dropout recovery regenerates the whole deck: each face-down card consists of N threshold-ElGamal components, for dN public components. Each player’s veto layer publishes d re-masking pairs and one non-veto CDS argument plus r veto CDS arguments, each over d Chaum–Pedersen instances. The subsequent re-masking chain uses about dN² Chaum–Pedersen proofs, followed by a full Barnett–Smart shuffle argument over dN ciphertext components. The extended thesis [8] states that dropout-path efficiency still needs improvement and reports no dropout-specific proof-byte or runtime measurements.')
    add_para(doc,'The comparison below summarizes the boundary with the closest dropout-tolerant construction. The comparison concerns the security object being proved: the earlier work provides a valuable liveness mechanism, while this paper adds authenticated per-card authorization and a machine-checked semantic bridge.')
    next_table_caption('Comparison with the closest dropout-tolerant construction')
    add_table(doc,['Property','Dropout-tolerant TTP-free Mental Poker [7]','This work'],[
        ('Dropout handling','Continues after a player leaves','Continues after deadline or crash'),
        ('Post-departure deck action','Remove leaver key share and regenerate; leaver’s cards return','Submit a state-bound package; singleton residuals removed, jointly keyed residuals retained'),
        ('Public deck size','N ciphertext components per card, dN total','d canonical contributions plus k authenticated carriers'),
        ('Proof relation count','N(r+1) CDS arguments over d CP instances; about dN² chain CP proofs; then a full shuffle proof','k cross-key proofs + one Bayer–Groth + d slot OR proofs'),
        ('Removal authorization','Protocol-level dropout recovery','Authenticated singleton residual-carrier lineage'),
        ('Per-slot plaintext relation','Not stated as zero-or-negative membership','OR proof for 0 or −m_i at every slot'),
        ('Mapping privacy','Hidden by protocol components','Hidden carrier-to-slot map plus BG proof'),
        ('Formal assurance','Cryptographic proof in the paper','Lean checked composition boundary plus explicit assumptions'),
        ('Multi-missing-key case','Not separated as a carrier class','Jointly keyed residual retained; no unauthorized removal'),
        ('Measured evidence','Symbolic description only; no dropout runtime or proof bytes','Native and WASM d,k grids; d=52,k=13 bundle is 27.75 KB'),
    ],widths=[1.45,2.55,2.2])

    doc.add_heading('3. Model and assumptions', level=1)
    add_para(doc,'Let q be a large prime, F_q the scalar field, and G a prime-order additive group with generator g. For a public key P = xg, define the additive ElGamal encryption and decryption functions as follows.')
    add_equation(doc,'Encₚ(m; r) = (rg, m + rP),      Decₓ(C) = C.c₂ − xC.c₁.')
    add_para(doc,'ElGamal is additively homomorphic:')
    add_equation(doc,'Encₚ(m; r) + Encₚ(m′; r′) = Encₚ(m + m′; r + r′).')
    add_para(doc,'The aggregate public key is P = Σₚ pkₚ, and Qₚ = skₚg. Canonical cards are nonzero and pairwise distinct. The protocol relies on the following assumptions; the distinction between algebraic facts and computational assumptions is part of the security claim.')
    doc.add_heading('3.1 Reveal-token algebra and the origin of the reconstruction carrier', level=2)
    add_para(doc,'We use residual carrier for the general object, and owner-residual carrier only for the single-missing-token specialization. The security invariant is a residual ciphertext derived from an authenticated reveal-token transcript. Let the fully masked card be')
    add_equation(doc,'Cᵢ = Encₚ(mᵢ; rᵢ) = (rᵢg, mᵢ + rᵢP),      P = Σₚ Qₚ.')
    add_para(doc,'For player p, the reveal token is the first ciphertext component multiplied by that player’s secret key:')
    add_equation(doc,'tₚ,ᵢ = skₚ Cᵢ.c₁ = rᵢQₚ.')
    add_para(doc,'The Chaum–Pedersen/DLEQ proof attached to tₚ,ᵢ establishes that the same secret key links Qₚ = skₚg and tₚ,ᵢ = skₚCᵢ.c₁. Therefore a verifier may subtract only tokens that are authenticated for the current card and epoch. Let A be the set of players whose reveal tokens were submitted for this carrier, and let U = Players minus A be its carrier-specific missing-token set. Define Q_U = Σₚ∈U Qₚ. The residual carrier is')
    add_equation(doc,'Cᵢ^(A) = Cᵢ − Σₚ∈A tₚ,ᵢ = (rᵢg, mᵢ + rᵢΣₚ∈U Qₚ) = Enc_{Q_U}(mᵢ; rᵢ),      Q_U = Σₚ∈U Qₚ.')
    add_para(doc,'The derivation is a direct group identity, but its interpretation depends on the carrier-specific value of |U|. If |U| = 1, say U = {q}, then Q_U = Q_q and the residual carrier is decryptable by q; this is the owner-residual carrier specialization used to authorize removal. If |U| ≥ 2, then Q_U is a sum of several public keys. The remaining online players do not possess the aggregate secret key sk_U = Σₚ∈U skₚ, so no individual player learns mᵢ from the residual. This does not make reconstruction inapplicable. The protocol does not need to decrypt or remove that card: reconstruction starts from a fresh canonical base Bᵢ = Enc_P(mᵢ; i+1), and because no owner-residual proof authorizes the negative branch for mᵢ, every accepted contribution for that slot encrypts zero. Homomorphic aggregation therefore retains mᵢ in the new deck. The old jointly keyed ciphertext can be discarded after its authenticated state transition has determined that no removal is authorized. If U is empty, all tokens were submitted and the protocol crosses the plaintext/redeal boundary rather than producing a residual carrier.')
    add_para(doc,'This retention rule is a deck-level safety policy, not a claim that every card game accepts the retained card in its next round. It preserves a well-formed ElGamal deck and prevents an unauthorized party from learning or deleting the jointly unknown card. An application must still define whether that canonical card may be dealt again, set aside, or removed; if removal is mandatory while no individual player knows the plaintext, the deployment needs a threshold authorization policy in addition to the present protocol.')
    add_para(doc,'The same derivation also explains why authenticated lineage is the foundation of reconstruction. An owner-residual carrier is not an arbitrary ciphertext supplied by a prover: its first component, masking randomness, owner key, card slot, epoch, and submitted-token set are fixed by the prior state. Consequently, the proof can safely establish the relation')
    add_equation(doc,'Q_U = sk_U g,   Sⱼ.c₁ = vⱼg,   sk_U Rⱼ.c₁ + vⱼP = Rⱼ.c₂ + Sⱼ.c₂,   Sⱼ = Encₚ(−mᵢ₍ⱼ₎; vⱼ).')
    add_para(doc,'For |U| = 1, sk_U is the owner secret key and the current code checks the relation after owner decryption. For |U| ≥ 2, the current protocol deliberately does not instantiate this negative relation: the slot takes the zero branch and the canonical card is retained. Thus reconstruction remains live even when every online player is unable to read the old ciphertext. A deployment that instead wished to remove a jointly unknown card would need a distributed generalized-Schnorr or threshold relation proof; that stronger removal policy is a future extension, not a completeness requirement of the present construction.')
    add_figure(doc,ASSET/'fig_residual_derivation.png','Figure 2. Reveal-token subtraction produces a residual ciphertext. One missing token gives an owner-residual specialization; multiple missing tokens give a jointly keyed carrier that remains usable for reconstruction without becoming individually decryptable.')
    assumptions=[('A1','Group and encoding','The curve implementation accepts only the prime-order subgroup and canonical encodings, and implements group operations correctly.'),('A2','Encryption privacy','ElGamal is IND-CPA secure under DDH or an equivalent assumption.'),('A3','Residual privacy','Every jointly keyed residual retains at least one honest, secret, uniform masking layer unless the protocol intentionally enters the plaintext/redeal path; privacy uses the corresponding fresh-discrete-log hardness assumption.'),('A4','Concrete hidden shuffle','For the standalone Rust theorem only, the Bayer–Groth component is complete, knowledge sound, and zero knowledge.'),('A5','Concrete linear proofs','For the standalone Rust theorem only, the cross-key and slot OR components are complete, specially sound, and HVZK; extracting a whole package requires their component extractors at their own Fiat–Shamir checkpoints.'),('A6','Ideal NIZK hybrid','Ordinary calls bind sid and the complete statement and accept only a valid aggregate witness. A simulator-only honest-proof interface and corrupted-proof witness interface are available only in the ideal comparison. No concrete Fiat–Shamir-to-UC realization is claimed.'),('A7','Authenticated state and refinement','The previous state digest cannot be forged, reveal-token proofs are bound to the card and epoch, and the Rust/AIR byte encoding refines the Lean statement.'),('A8','Authenticated missing-key sets','A negative contribution is accepted only for an authenticated singleton missing-token set. A residual with two or more missing keys authorizes only the zero branch, so its card remains in the rebuilt deck.'),('A9','Corruption model','Corruption is static, and an honest owner key or residual masking layer is not revealed before the execution ends.')]
    next_table_caption('Security assumptions and operational meaning')
    add_table(doc,['ID','Assumption','Operational meaning'],assumptions,widths=[0.42,1.55,4.15])
    add_para(doc,'Table V separates fixed implementation parameters from symbolic advantage terms. It does not assign numeric values to ε_DDH, ε_state, ε_ser, or ε_KS; those remain reductions to the corresponding assumptions. The table also does not claim a conventional λ-bit security level for the hash-to-scalar maps, because the production challenge is a field-output reduction rather than rejection sampling.')
    next_table_caption('Concrete parameters and theorem error boundaries')
    add_table(doc,['Parameter or bound','Value and scope'],[
        ('Production scalar order q','0x0800000000000010ffffffffffffffffb781126dcae7b2321e66a241adc64d2f, a 252-bit order; canonical scalars use 32-byte wire encoding.'),
        ('BN254 G1 scalar order q','0x30644e72e131a029b85045b68181585d2833e84879b9709143e1f593f0000001, a 254-bit order in the scoped curve-level baseline.'),
        ('Production challenge derivation','Poseidon transcript output is reduced modulo q. The domain labels and challenge ratchet are pinned by test vectors; the ideal-NIZK theorems do not claim that this map realizes concurrent UC NIZK.'),
        ('BN254 challenge derivation','SHA3-256 output with the top three bits cleared, yielding a value below 2^253 < q; this baseline domain is separate from the production Poseidon path.'),
        ('Completeness error','At most O((n+k)q_H/q) at the stated zero-challenge boundary, with q the production order and n,k the deck/carrier dimensions.'),
        ('Ideal UC distinguishing bound','At most k·ε_DDH + ε_state + ε_ser for static corruption under A2 and A3, A6–A9. No FS or random-oracle term enters this hybrid theorem.'),
        ('Non-owner veto bound','At most ε_state + ε_ser in the ideal hybrid; the concrete verifier adds package-extraction error ε_KS under A1, A4, and A5.'),
        ('Settlement transaction signature','Stark Schnorr uses a 32-byte public key and 64-byte signature over the domain-separated simulator message; it is test-model authenticity, not a deployed chain adapter.'),
        ('Measured wire shape at n=52,k=13','Production/BN254 Borsh shape: 21,781-byte proof, 5,969-byte statement, and 27,750-byte statement-plus-proof bundle.'),
        ('Frozen refinement schema','1,041-byte statement schema and 3,829-byte seeded proof-instance schema; fresh proofs remain randomized and are not canonicalized.'),
    ],widths=[1.35,4.75])

    doc.add_heading('4. Protocol', level=1)
    doc.add_heading('4.1 Public statement', level=2)
    add_para(doc,'The public statement is')
    add_equation(doc,'S = (context_digest, epoch, D_prev, P, Q, (mᵢ)ᵢ₍ₙ, (Rⱼ)ⱼ₍ₖ, (Cᵢ)ᵢ₍ₙ).')
    add_para(doc,'Here Rⱼ are authenticated residual ciphertexts and Cᵢ are the prover’s contributions. The verifier rejects malformed lengths, identity keys or ciphertexts, duplicate canonical cards, an empty carrier set, and a carrier set larger than the deck. The semantic relation is determined by these fields and by the reveal-token lineage that derives them; wire-level validation is fail-closed.')
    doc.add_heading('4.2 Proof generation', level=2)
    add_para(doc,'The prover has the authenticated owner-residual vector R₀,…,Rₖ₋₁ consisting precisely of carriers whose carrier-specific missing-token set has |U| = 1 and whose singleton owner is controlled by that prover. It also has the state-bound token derivation and the owner secret key. This vector is intentionally not the complete set of authenticated residual carriers. A jointly keyed carrier with |U| ≥ 2 is omitted from this removal-authorizing vector; its canonical slot remains in the deterministic zero-padding path, so reconstruction still applies and preserves the encrypted card. Deleting such a jointly unknown card would require a separate threshold proof and authorization policy. The prover performs the following steps.')
    for s in ['Derive each Rⱼ by subtracting the authenticated submitted tokens; in the owner-residual specialization, decrypt it and check that its plaintext is a distinct canonical card.','Sample vⱼ and construct Sⱼ = Encₚ(−mᵢ₍ⱼ₎; vⱼ); construct n−k deterministic zero contributions.','Apply a hidden permutation and fresh rerandomization to obtain the canonical contribution vector.','Prove the carrier-to-contribution relation for each pair (Rⱼ,Sⱼ); the one-owner path uses the cross-key Chaum–Pedersen relation described below.','Prove a Bayer–Groth relation from the hidden contribution vector to C.','Prove the two-branch OR relation for every canonical slot.']:
        p=doc.add_paragraph(style='List Number'); p.add_run(s)
    add_para(doc,'The carrier-to-slot mapping, branch choices, permutation, and randomness are prover witnesses and do not appear in the proof bytes.')
    doc.add_heading('4.3 Cross-key joint proof', level=2)
    add_para(doc,'For the owner-residual specialization, R = Enc_Q(m; r) and S = Enc_P(−m; v), and the prover shows knowledge of (sk_Q,v) satisfying')
    add_equation(doc,'Q = sk_Q g,      S.c₁ = vg,      sk_Q R.c₁ + vP = R.c₂ + S.c₂.')
    add_para(doc,'This is a two-scalar generalized-Schnorr relation over three linked group equations. The third equation implies that the two ciphertext plaintexts sum to zero, so the negative contribution is tied to the authenticated owner-residual plaintext. The witness does not contain r = DL(R.c₁). The relation is instantiated only when the carrier-specific set U is a singleton. For |U| ≥ 2, no individual player can supply sk_U, so the protocol authorizes no negative contribution for that carrier; retaining the zero branch is sufficient to rebuild the deck without learning the card.')
    doc.add_heading('4.4 Slot OR proof', level=2)
    add_para(doc,'For slot i, define T₀ = Cᵢ.c₂ and T₁ = Cᵢ.c₂ + mᵢ. The prover shows that there is a vᵢ such that')
    add_equation(doc,'Cᵢ.c₁ = vᵢg  and  T_b = vᵢP  for one branch b ∈ {0,1}.')
    add_para(doc,'Branch 0 is the zero contribution and branch 1 is the negative-card contribution. A standard OR proof honestly proves one branch, simulates the other with a challenge share, and enforces e₀ + e₁ = e for the global challenge.')
    doc.add_heading('4.5 Aggregate reconstruction', level=2)
    add_para(doc,'Starting from the canonical base deck Bᵢ = Encₚ(mᵢ; i+1), the host sums every contribution whose proof passes before the deadline:')
    add_equation(doc,'B̃ᵢ = Bᵢ + Σₚ∈S_submit Cₚ,ᵢ.')
    add_para(doc,'An absent or late participant contributes nothing. Under A8, at most one accepted contribution can carry the negative branch for a given authenticated residual slot. A participant cannot use a missed submission to authorize a negative contribution for a carrier outside the authenticated missing-key set.')
    add_figure(doc,ASSET/'fig_slot_semantics.png','Figure 3. Slot-local OR semantics and exact residual-carrier coverage. The global deck relation is obtained by composing these per-slot constraints with an injective carrier-to-slot map.')

    doc.add_heading('4.6 Proof-system design rationale', level=2)
    add_para(doc,'The protocol deliberately retains Bayer–Groth for permutation hiding. It is the mature shuffle argument used by the implementation, and replacing it with a generic circuit compiler would change both the trusted-setup boundary and the implementation stack rather than isolate the new reconstruction semantics. The client-side construction therefore composes Bayer–Groth with cross-key Sigma proofs and slot OR proofs.')
    add_para(doc,'The contribution is this semantic composition, not a claim that the individual proof engines are new: authenticated residual-carrier lineage, a cross-key negative relation, exact coverage, and a zero-or-negative relation for every canonical slot. Transparent Sigma algebra also maps directly to the Lean component interface and keeps browser proving within the measured sub-second envelope. The resulting proofs are larger than a succinct aggregated argument; host-side aggregation remains future engineering work and is not used as an unmeasured performance comparison.')

    doc.add_heading('4.7 Deadline and deposit policy boundary', level=2)
    add_para(doc,'A pure application policy can make absence costly without changing the cryptographic reconstruction relation. The implementation models one required package per listed submitter in one epoch. Each listed submitter locks a deposit D; after the cryptographic verifier accepts that submitter’s package, the host records its identity, proof digest, epoch, and submission time. Unknown submitters, duplicate submissions, wrong epochs, all-zero proof digests, and submissions after the deadline are rejected. The policy itself does not verify proofs and does not transfer funds; it emits a deterministic settlement proposal for an external settlement layer.')
    add_para(doc,'Let M be the set of listed submitters with no accepted package at the deadline. For each p in M, the proposed penalty is a_p = min(D, P), where P is the configured per-missed-package penalty. Let L = sum_{p in M} a_p and let T be the canonical-order list of timely submitters. If T is nonempty, each timely submitter receives floor(L/|T|), the first L mod |T| timely submitters receive one additional unit, and any remaining units are burned. If T is empty, L is burned. A missed submitter receives D-a_p; a timely submitter therefore releases its refund plus compensation. The no-claim and over-issue failure modes are excluded by construction: total compensation plus burned remainder equals L, and penalties never exceed locked deposits. If all packages arrive before the deadline, every deposit is refunded and no penalty is proposed.')
    add_para(doc,'The settlement adapter boundary turns this proposal into auditable ledger events without requiring a particular chain API. Before finalization, the adapter locks each listed submitter’s exact deposit; an identical retry returns the same lock receipt, while a different amount is rejected. When applying a settlement, it requires submitter names to be unique and canonically ordered, checks refund+penalty=locked deposit and refund+compensation=net release for every player, verifies that the missed-submitter list is exact, and enforces both compensation and locked-escrow conservation equations. The escrow set must match the settlement exactly: no missing participant, extra participant, or amount mismatch is accepted. Application is atomic; an identical replay returns the original execution, while a different proposal for the same epoch is rejected.')
    add_para(doc,'A separate simulated chain host makes the transaction boundary explicit without pretending to be a blockchain. A settlement request carries a nonzero deployment digest and a Stark-curve Schnorr signature over that digest, compressed public key, nonce, gas limit, and complete proposal; the simulator verifies the signature and derives the account from the verified key. The sender field must be the canonical lowercase encoding of that key; identity public keys and identity Schnorr commitments are rejected. A versioned PSTX reference envelope canonicalizes the complete signed request for an off-chain adapter; it is not a public chain standard or deployed contract format. Submission requires the account’s next nonce and a gas limit at least equal to deterministic base-plus-event gas. The candidate execution is isolated from the committed ledger until a configured confirmation depth; an identical pending transaction is idempotent, while a different transaction or reused nonce is rejected. A reorg before finality drops the candidate, restores the nonce, and leaves the original escrow unchanged. The simulator therefore covers authenticity, canonical sender/key binding, signature tamper rejection, cross-deployment replay rejection, and rollback semantics, but mempool propagation, production gas accounting, gas refunds, host-consensus finality, and a deployed contract adapter remain concrete-host responsibilities.')
    add_para(doc,'This policy supplies economic liveness incentives, not a replacement owner witness. A replacement submitter cannot produce an owner-residual proof for another player under the current v3 protocol. Supporting replacement or threshold authorization for a jointly keyed carrier requires a separate threshold relation and authentication policy; it is intentionally not smuggled in through deposit accounting.')

    doc.add_heading('5. Correctness and standalone security', level=1)
    doc.add_heading('Theorem 1 (Completeness)', level=2)
    add_para(doc,'If the statement satisfies the authenticated-state conditions and an honest prover follows Section 4.2, the verifier accepts except for explicit zero-challenge events, with failure probability bounded by O((n+k)q_H/q).')
    add_para(doc,'Proof. A witness exists for every component. Lineage gives Rⱼ = Enc_Q(mᵢ₍ⱼ₎; rⱼ). The honest prover decrypts the unique canonical card, samples vⱼ, and constructs Sⱼ = Enc_P(−mᵢ₍ⱼ₎; vⱼ). Substituting in the third cross-key equation gives sk_Q(rⱼg)+vⱼP = rⱼQ+vⱼP and mᵢ₍ⱼ₎+rⱼQ−mᵢ₍ⱼ₎+vⱼP = rⱼQ+vⱼP, so all three equations hold. The deterministic zero encryptions are Z_l = Enc_P(0; l+1), and the selected injective map defines a permutation and rerandomizers; hence a complete Bayer–Groth witness exists.')
    add_para(doc,'For slot i, a zero input satisfies Cᵢ.c₁ = vᵢg and T₀ = Cᵢ.c₂ = vᵢP, while a negative input satisfies T₁ = Cᵢ.c₂+mᵢ = vᵢP. The real OR branch is answered honestly; the simulated branch computes its commitment from a chosen challenge share and response, and the two shares sum to the global challenge. Every statement field enters the transcript in the same canonical order. Failure therefore requires a zero challenge/share or a previously queried programmed point; across k cross-key proofs and n OR proofs the union is O((n+k)q_H/q).')
    doc.add_heading('Theorem 2 (Knowledge soundness)', level=2)
    add_para(doc,'In a real F_NIZK^R_RECON-hybrid execution under A6 and A7, where the simulator-only interface is not invoked, ordinary acceptance yields a witness (removed, v, carrierIndex, …) such that: (i) every slot contribution encrypts either 0 or −mᵢ; (ii) removedᵢ = true exactly when some authenticated carrier index maps to slot i; (iii) carrierIndex is injective; and (iv) every negative branch is linked to the authenticated residual-token derivation. For the concrete Rust verifier, the same conclusion is conditional on A1, A4, A5, and A7 and on a package extractor that invokes each component extractor at its own Fiat–Shamir checkpoint.')
    add_para(doc,'Proof. In the hybrid theorem, F_NIZK^R_RECON accepts only if a supplied witness satisfies the aggregate relation, so the four properties follow directly from its exact-coverage, shuffle, cross-key, and slot-membership clauses. In the concrete corollary, the Bayer–Groth extractor returns a permutation and rerandomizers; each cross-key extractor returns (sk_Q,vⱼ); and each slot extractor returns a branch and randomness. Because the implementation uses a cumulative transcript with distinct sequential challenges, this corollary does not claim that changing one final challenge extracts all components.')
    add_para(doc,'Combining the extracted shuffle with the OR witnesses yields removedᵢ = true exactly when an extracted carrier maps to i. The prover rejects duplicate residual plaintexts and the extracted shuffle permutation is injective, so carrierIndex is injective. A7 and the byte refinement bind each accepted Rⱼ to the authenticated prior hand; otherwise the reduction forges the state digest or violates serialization. Extractor failure is counted in ε_KS, and the state/encoding failure is counted in ε_state+ε_ser.')
    doc.add_heading('Theorem 3 (Reconstruction semantics)', level=2)
    add_para(doc,'Let χᵢ = 1 exactly when an accepted submitter has an authenticated owner-residual carrier that authorizes removal of mᵢ in the current epoch. Under A8,')
    add_equation(doc,'Decₚ(B̃ᵢ) = 0  if χᵢ = 1;      Decₚ(B̃ᵢ) = mᵢ  if χᵢ = 0.')
    add_para(doc,'Proof. Apply Theorem 2 to every accepted submitter. Each contribution for slot i encrypts 0 or −mᵢ, and only an authenticated carrier mapped to i can produce the negative plaintext. By A8, cross-player carrier sets are disjoint, so at most one accepted contribution is negative. ElGamal homomorphism gives Dec_P(B̃ᵢ)=mᵢ+Σ plaintext(Cₚ,ᵢ), which is 0 when an authorized carrier exists and mᵢ otherwise. For a carrier-specific |U|≥2, no owner-residual witness is placed in the removal-authorizing vector, so every accepted contribution for its slot is zero and the card remains encrypted without being decrypted.')

    doc.add_heading('6. Ideal functionality and composition boundary', level=1)
    doc.add_heading('6.1 Hybrid model', level=2)
    add_para(doc,'The composition result is stated in the F_NIZK^R_RECON, F_STATE, F_KEY, F_SHUFFLE, and F_REVEAL hybrid. On its ordinary interface, F_NIZK^R_RECON binds sid and the complete public statement and accepts only if a witness satisfies the aggregate relation in Sections 4 and 5. In the ideal comparison only, an honest-proof simulator interface may register a session-bound simulated proof without revealing a witness, while a corrupted-proof interface supplies the accepted witness to the simulator. These capabilities are unavailable to the environment and ordinary protocol parties. This removes random-oracle programming and rewinding from the UC proof. The concrete Poseidon Fiat–Shamir implementation is outside this realization claim. The corruption set is fixed at initialization; the network adversary may reorder, delay, or drop submissions before the deadline.')
    doc.add_heading('6.2 Ideal functionality F_RECON', level=2)
    add_para(doc,'The session identifier is sid = (context, table, hand, epoch, D_prev). F_RECON stores phase ∈ {WAITING, FINAL}, the authenticated carrier authorization A_p for each player, a set of accepted submitters, and the final encrypted deck. F_STATE supplies the canonical deck, public keys, reveal-token lineage, missing-key sets, and epoch. Honest plaintexts, carrier-to-slot maps, proof witnesses, permutations, and rerandomizers are not leaked.')
    next_table_caption('Formal interface of F_RECON')
    add_table(doc,['Input','From','Effect'],[
        ('INIT(sid, deadline)','F_STATE','Reject if sid is already active, D_prev is invalid, or the epoch is not the unique successor. Fix the static corruption set and authenticated A_p values; publish only public metadata; set phase=WAITING.'),
        ('SUBMIT(sid,p,x)','Party or adversary','Reject wrong sid/epoch, FINAL phase, duplicates, malformed x, or failed F_NIZK^R_RECON validation. Otherwise record p and its public contribution vector. Arrival order has no semantic effect.'),
        ('STATUS(sid)','Environment','Return WAITING/FINAL, accepted identities, public validation results, deadline state, and public digests. Do not return witnesses, hidden maps, branches, or plaintexts.'),
        ('DEADLINE(sid)','Clock or adversary','Validate that accepted negative branches equal the submitting players’ authenticated singleton authorizations. On overlap or inconsistent state output STATE_INVALID. Otherwise aggregate accepted contributions, retain multi-key residual cards, publish the new encrypted deck and digest, and set phase=FINAL.'),
        ('REPLAY or duplicate','Any caller','A command with a stale epoch, different D_prev, finalized sid, or repeated submission identifier is rejected without changing state. Repeated STATUS and DEADLINE after FINAL return the recorded public result.'),
    ],widths=[1.15,1.0,4.0])
    add_para(doc,'For a statically corrupted player, the adversary chooses all local inputs and the simulator observes the witness submitted to F_NIZK^R_RECON while emulating that corrupted interface. Honest witnesses remain hidden. This timing is the only point at which the simulator learns a corrupted removal map. Deadlines reveal no additional residual information. Cross-epoch and cross-table replay fails because sid includes context, table, hand, epoch, and D_prev.')
    doc.add_heading('6.3 Hybrid protocol', level=2)
    add_para(doc,'The client obtains the exact owner-residual vector and state binding, forms the public contribution vector, and invokes F_NIZK^R_RECON on the aggregate relation. The host accepts only a successful functionality result with the current sid, then performs homomorphic aggregation. A carrier with |U| ≥ 2 never appears in the removal-authorizing vector; its zero branch is nevertheless a normal reconstruction path. An abort or missed deadline is a no-op, not an arbitrary negative contribution.')
    doc.add_heading('6.4 Composition theorem', level=2)
    add_para(doc,'Theorem 4. Under A2, A3, and A6–A9, the hybrid protocol UC-realizes F_RECON against static corruption. When the authenticated-state and byte-refinement layers are included as computational implementations, the distinguishing advantage is at most k·ε_DDH + ε_state + ε_ser. There is no Fiat–Shamir forking, random-oracle programming, or concurrent-FS error term in this theorem.')
    doc.add_heading('Simulator and hybrids', level=3)
    add_para(doc,'The simulator runs the adversary internally and relays public metadata and scheduling events. For an honest submission it publishes the ideal state adapter’s simulated contribution vector and invokes the simulator-only honest-proof interface; the ideal state retains the prescribed removal semantics. For a corrupted submission it reads the witness supplied by the corrupted-proof interface to F_NIZK^R_RECON, verifies the carrier map against F_STATE, and sends exactly the authenticated singleton removal set to F_RECON. Invalid, duplicate, late, replayed, and overlapping submissions receive the same public result in both executions.')
    add_para(doc,'H₀ is the hybrid protocol. In H₁, replace each honest Enc_P(−mᵢ;vᵢ) contribution by Enc_P(0;v′ᵢ) and register its proof through the simulator-only interface. A hybrid over at most k authorized negative contributions uses one IND-CPA reduction per replacement, for total cost k·ε_DDH; simulated public ciphertexts remain linked to the ideal semantic state only through F_STATE and are never used as extracted corrupted inputs. In H₂, replace the state and serialization adapters by their ideal authenticated interfaces, at costs ε_state and ε_ser. H₂ is the ideal F_RECON execution because accepted corrupted witnesses specify exactly the authorized removal set and all honest hidden values are maintained by the functionality. Summing the hops gives the stated bound. The UC composition theorem applies to the named ideal functionalities; it does not establish a concrete realization of F_NIZK by the current Rust proof bytes.')
    doc.add_heading('6.5 Vetoing another player’s card', level=2)
    add_para(doc,'Define Veto(p,m) as an accepted package by player p that removes m even though the authenticated residual-carrier derivation for p’s epoch does not authorize m.')
    add_para(doc,'Theorem 5. Under A6–A9, Pr[Veto(p,m)] ≤ ε_state + ε_ser in the F_NIZK^R_RECON hybrid. Acceptance supplies a relation witness whose negative branch and carrier map must equal an authenticated singleton missing-token derivation. If p does not submit, no contribution from p exists. For the concrete verifier, add the component package-extraction error ε_KS under A1, A4, and A5.')
    add_para(doc,'Proof. Suppose Veto(p,m) occurs although m is not in p’s authenticated set. Session authentication attributes the accepted submission to p. F_NIZK^R_RECON acceptance supplies a witness containing the negative branch, residual carrier, and carrier-to-slot map. Exact-vector state binding requires the matching (p,Rⱼ,m,epoch,missing-set) tuple in D_prev. If absent, either D_prev authentication failed or the implementation bytes refined to a different statement, giving ε_state+ε_ser. The concrete corollary additionally fails when an accepted component package has no extractable witness, contributing ε_KS. Overlapping carrier sets or pre-execution key leakage violate A8/A9 and fall outside the theorem.')
    add_figure(doc,ASSET/'fig_composition.png','Figure 4. The formalization exposes a precise machine-checked boundary. Group algebra and component interfaces feed the composition theorem; computational assumptions are then used by the ideal-NIZK-hybrid argument.')

    doc.add_heading('7. Lean formalization', level=1)
    add_para(doc,'The Lean development separates the algebraic specification from the computational assumptions supplied by the implementation.')
    lean_rows=[('Residual lineage','ResidualCarrier\nProvenance.lean','Residual carrier from authenticated prior state'),('Reconstruction relation','Reconstruction.lean','Slot relation and unique removal semantics'),('Cross-key Sigma','Reconstruction\nJointSigma.lean','Cross-key relation, completeness, soundness, and HVZK'),('Slot OR','Reconstruction\nSlotOr.lean','Completeness, soundness, and algebraic HVZK'),('Composition boundary','Reconstruction\nSecurity.lean','End-to-end package semantics under component interfaces'),('Veto bound','Reconstruction\nVeto.lean','Non-owner veto impossibility and negligible error union bound')]
    next_table_caption('Lean modules and checked results')
    add_table(doc,['Layer','File','Checked result'],lean_rows,widths=[1.3,1.75,3.07])
    add_para(doc,'The algebraic Statement contains the aggregate key, the authenticated residual-key description, canonical cards, residual ciphertexts, and contributions. The Witness contains the removed-slot bitmap, contribution randomness, carrier-to-slot map, residual randomness, injectivity, and exact-coverage condition. Relation states the reveal-token subtraction equations and the per-slot contribution equations. The one-owner witness is the concrete specialization currently implemented by the AIR producer.')
    add_para(doc,'ComponentInterface records the external guarantees for the concrete hidden shuffle and linear proofs, the ideal NIZK hybrid interface, session/statement binding, Rust-to-Lean serialization, authenticated state, and cross-player disjointness. Reduction connects those guarantees to prove, verify, extraction, and view functions. The Lean theorem does not derive a Fiat–Shamir-to-UC realization.')
    add_para(doc,'The main composition theorem is verified_package_semantics. Given a VerifiedPackage containing a well-formed statement, an extracted witness, the algebraic relation, and a proof that the component interface holds, it derives in one theorem: (i) ValidRelation for the public statement and witness; (ii) exact correspondence between removed i = true and an authenticated residual-carrier index; and (iii) the zero-or-negative-card membership equation for every contribution.')
    add_para(doc,'The Rust–Lean refinement evidence is intentionally scoped but now covers complete statement and proof-instance wire schemas. Both sides first consume paper/experiments/reconstruction_refinement_vector.json, fixing version 3, epoch 11, an eight-card statement, two residual carriers, and bitmap 01001000. The reconstruction_statement_schema_v3.json fixture then freezes a 1,041-byte valid StarkCurve statement as eleven contiguous fields: version, context digest, epoch, prior-state digest, aggregate key, owner key, card count, cards, carrier count, residual carriers, and contributions. It also records a seeded proof instance as 3,829 bytes: version, negative-contribution count and vector, cross-key proofs, the complete Bayer–Groth multi-exponentiation and product substructure, slot-proof count, and all slot OR proofs. The proof section contains seven top-level fields and thirty nested field slices.')
    add_para(doc,'Rust regenerates the statement and exact seeded proof bytes with ChaCha20, verifies the proof, and checks every top-level and nested offset, length, and byte slice. Lean checks the semantic vector, the eleven-field statement schema, the seven-field proof schema, the 141-byte statement prefix, five-byte proof prefix, and both SHA-256 digests. A fresh production proof remains randomized, so this is a frozen proof-instance schema rather than a claim that all proof encodings are canonical. Truncation, trailing-field, digest-reordering, epoch-replay, foreign-card, and swapped-key mutations remain negative tests. Lean still does not claim that DDH, random-oracle security, or Bayer–Groth knowledge soundness follow from group algebra; those facts enter ComponentInterface and Reduction explicitly.')
    add_para(doc,'The repository’s Lean checks include a no-sorry audit and an axiom audit for the principal reconstruction results. The audit reports only the trusted Lean foundations used by imported libraries and no protocol-specific axiom.')

    doc.add_heading('8. Implementation and reproducibility', level=1)
    add_para(doc,'The code is organized as follows:')
    next_table_caption('Implementation components')
    add_table(doc,['Component','Role'],[('poker-protocol-core','Curve arithmetic, ElGamal, and transcripts.'),('poker-protocol-bg','Bayer–Groth shuffle component.'),('poker-protocol-proofs','Reconstruction, cross-key, OR, and related proofs.'),('poker_protocol','Native adapter, ABI, game integration, deadline policy, and settlement ledger boundary.'),('client-wasm','Browser bridge and reproducible WASM benchmark.'),('poker_protocol_lean','Formal specification and checked composition.')],widths=[2.1,4.0])
    add_para(doc,f'The native path uses the Stark-curve/Poseidon transcript domain. The Ristretto adapter constructs the public submission object; verification of an external AIR archive is outside this repository. The Move contract stores the partial ciphertext after subtracting submitted reveal tokens, while the AIR test helper derives the |U| = 1 owner-residual vector by subtracting every other seat’s token. When two or more tokens are missing, no owner-residual vector entry is created and the rebuilt canonical slot remains unchanged. The paper and implementation repository is {REPOSITORY_URL}.')
    add_para(doc,'The repository also contains the pure Rust `ReconstructionSubmissionPolicy` and `ReconstructionSettlementAdapter`. Policy tests cover full refund, deposit-capped penalties, timely compensation, duplicate/late/unknown/wrong-epoch rejection, idempotent finalization, the all-missed burn case, digest validation, and arithmetic overflow. The in-memory settlement ledger adds tests for exact escrow matching, idempotent lock and settlement retries, conflicting same-epoch proposals, malformed player arithmetic, noncanonical submitter order, inaccurate missed-submitter metadata, extra or missing deposits, and escrow/release overflow. The simulated chain host additionally tests deployment-digest binding, domain-separated signed-transaction admission, canonical sender/public-key binding, identity-key rejection, signature and proposal tamper rejection, transaction-hash binding for deployment, public key, nonce, gas, proposal, and signature, canonical PSTX-envelope roundtrip, bad magic/version, truncation, trailing bytes, unsigned encoding rejection, nonce admission and replay, insufficient gas, pending idempotence, confirmation-depth commit, and reorg rollback with nonce restoration. A production adapter must still bridge this reference envelope to its chain format and supply consensus, mempool, deployed verifier, and finality semantics.')
    add_para(doc,'To reproduce the checks:')
    add_equation(doc,'./scripts/install_repro_deps.sh\n./scripts/reproduce_paper.sh')
    add_para(doc,'The installer configures pinned Rust, Lean, Node.js, wasm-pack, Circom 2.2.3, and snarkjs 0.7.5 versions in user-writable locations without sudo; CIRCOM_BIN can select an explicit compatible compiler. The runner verifies the committed baseline and source hashes, executes the Rust, WASM, Lean, scoped-baseline, and refinement checks, and writes fresh timing grids under .repro/results rather than replacing the paper baselines. Each run records the host, tool versions, Git state, and result hashes in run_metadata.json.')
    native = benchmark_rows('reconstruction_stark.csv')
    wasm = benchmark_rows('reconstruction_wasm.csv')
    components = benchmark_rows('reconstruction_components.csv')
    with (EXPERIMENTS / 'circom_multislot_baseline.json').open(encoding='utf-8') as handle:
        multislot_baseline = json.load(handle)
    with (EXPERIMENTS / 'reconstruction_bn254_n52_k13_30.json').open(encoding='utf-8') as handle:
        curve_baseline = json.load(handle)
    with (EXPERIMENTS / 'browser_chrome_headless_153_macos_20260924.json').open(encoding='utf-8') as handle:
        headless_chrome = json.load(handle)
    with (EXPERIMENTS / 'browser_chrome_headed_153_macos_20260924.json').open(encoding='utf-8') as handle:
        headed_chrome = json.load(handle)
    with (EXPERIMENTS / 'browser_safari_desktop_macos_20260924.json').open(encoding='utf-8') as handle:
        desktop_safari = json.load(handle)
    with (EXPERIMENTS / 'browser_chrome_headless_memory_153_macos_20260924.json').open(encoding='utf-8') as handle:
        chrome_memory = json.load(handle)
    with (EXPERIMENTS / 'network_chrome_cache_disabled_loopback_30_20260924.json').open(encoding='utf-8') as handle:
        network_loopback = json.load(handle)
    with (EXPERIMENTS / 'network_chrome_loopback_upload_30_20260924.json').open(encoding='utf-8') as handle:
        network_upload = json.load(handle)
    with (EXPERIMENTS / 'network_chrome_service_worker_loopback_upload_30_20260924.json').open(encoding='utf-8') as handle:
        network_service_worker = json.load(handle)
    with (EXPERIMENTS / 'network_chrome_cold_service_worker_install_30_20260924.json').open(encoding='utf-8') as handle:
        network_cold_service_worker = json.load(handle)
    with (EXPERIMENTS / 'network_chrome_service_worker_update_30_20260925.json').open(encoding='utf-8') as handle:
        network_service_worker_update = json.load(handle)
    with (EXPERIMENTS / 'network_chrome_http_cache_reuse_30_20260925.json').open(encoding='utf-8') as handle:
        network_http_cache = json.load(handle)
    with (EXPERIMENTS / 'network_safari_http_cache_reuse_30_20260925.json').open(encoding='utf-8') as handle:
        network_safari_http_cache = json.load(handle)
    with (EXPERIMENTS / 'network_chrome_http_current_loopback_upload_30_20260924.json').open(encoding='utf-8') as handle:
        network_http_current = json.load(handle)
    with (EXPERIMENTS / 'network_chrome_tls_loopback_upload_30_20260924.json').open(encoding='utf-8') as handle:
        network_tls = json.load(handle)
    headless_chrome_52_13 = next(row for row in headless_chrome['results'] if int(row['n']) == 52 and int(row['k']) == 13)
    headed_chrome_52_13 = next(row for row in headed_chrome['results'] if int(row['n']) == 52 and int(row['k']) == 13)
    desktop_safari_52_13 = next(row for row in desktop_safari['results'] if int(row['n']) == 52 and int(row['k']) == 13)
    native_52_13 = native[(52, 13)]
    native_52_26 = native[(52, 26)]
    wasm_52_13 = wasm[(52, 13)]
    component_52_13 = components[(52, 13)]
    add_para(doc,f'A reference native run uses StarkCurve, the production RECONSTRUCT_POSEIDON transcript domain, a release build, one untimed warm-up, and 30 timed samples per grid cell. For n = 52 and k = 13, proving has median/mean±sample-sd/P95 {timing_summary(native_52_13, "prove", native=True)}, while verification has {timing_summary(native_52_13, "verify", native=True)}. The proof is {int(native_52_13["proof_bytes"])/1000:.2f} KB; peak allocations are {int(native_52_13["prove_peak_bytes"])/1024:.1f} KiB for proving and {int(native_52_13["verify_peak_bytes"])/1024:.1f} KiB for verification. At k = 26, median proving and verification are {native_ms(native_52_26, "prove_median_us"):.1f} ms and {native_ms(native_52_26, "verify_median_us"):.1f} ms with a {int(native_52_26["proof_bytes"])/1000:.2f} KB proof. The full grid is committed at paper/experiments/reconstruction_stark.csv.')
    add_para(doc,'These timings describe only this reconstruction package on the recorded machine. They are not a head-to-head comparison with the trick-taking implementation of Bella et al. [48], whose published 52-card shuffle timings cover a different game relation, implementation stack, and hardware. No cross-implementation superiority claim is made.')
    next_table_caption('Native reconstruction benchmark: median / mean±sample sd / P95, 30 release samples')
    add_table(doc,['n','k','Prove statistics','Verify statistics','Proof','Peak prove'],[
        (str(n),str(k),timing_summary(native[(n,k)],'prove',native=True),timing_summary(native[(n,k)],'verify',native=True),f'{int(native[(n,k)]["proof_bytes"])/1000:.2f} KB',f'{int(native[(n,k)]["prove_peak_bytes"])/1024:.1f} KiB')
        for n,k in [(13,1),(26,13),(52,13),(52,26)]
    ],widths=[0.45,0.45,1.5,1.5,0.75,0.85])
    add_para(doc,f'Component profiling separates residual/setup and statement construction, cross-key proofs, Bayer–Groth shuffle, per-slot OR proofs, Borsh serialization, and the three corresponding verification stages. For n = 52 and k = 13, median proving components are {ns_ms(component_52_13, "residual_setup_ns"):.1f}, {ns_ms(component_52_13, "cross_key_ns"):.1f}, {ns_ms(component_52_13, "bayer_groth_ns"):.1f}, and {ns_ms(component_52_13, "slot_or_ns"):.1f} ms; verification components are {ns_ms(component_52_13, "verify_cross_key_ns"):.1f}, {ns_ms(component_52_13, "verify_bayer_groth_ns"):.1f}, and {ns_ms(component_52_13, "verify_slot_or_ns"):.1f} ms. These are observational stage timings sampled in separate calls, so their sums may differ from the end-to-end timer. The complete grid is committed at paper/experiments/reconstruction_components.csv.')
    add_para(doc,'As a scoped fairness baseline, we compile a single-slot Circom relation with a private Boolean selector and public field values satisfying out = selector·(−card), then run Groth16 over BN128 with snarkjs 0.7.5. The measured circuit has 2 constraints, an 808-byte proof in the recorded run, 270.4 ms proving, and 228.6 ms verification. This baseline intentionally excludes ElGamal ciphertexts, residual decryption, hidden carrier-to-slot mapping, Bayer–Groth, cross-key proofs, authenticated state, and dropout composition; it is not a claim that Groth16 implements the complete protocol. The circuit, setup commands, unsupported-semantics list, and JSON result are in paper/baselines and paper/experiments/circom_slot_baseline.json.')
    add_para(doc,f'A broader finite-domain Groth16 baseline models the central multi-slot semantics for the n = 52, k = 13 reference shape: each contribution is constrained to {{0,−cardᵢ}}, each of the 13 private carriers maps to exactly one canonical slot, and each negative slot is covered exactly once. The branch bits and 13×52 one-hot carrier map are private. The measured circuit has {multislot_baseline["constraints"]} constraints and {multislot_baseline["wires"]} wires; witness generation, proving, and verification take {multislot_baseline["witness_ms"]:.1f}, {multislot_baseline["prove_ms"]:.1f}, and {multislot_baseline["verify_ms"]:.1f} ms, with an {multislot_baseline["proof_bytes"]}-byte proof and {multislot_baseline["public_signal_bytes"]}-byte public-signal JSON. This is closer to reconstruction semantics than the single-slot baseline, but it still uses scalar card identifiers rather than curve ElGamal ciphertexts and excludes cross-key group equations, Bayer–Groth rerandomization, authenticated state, and protocol composition. The circuit and measured metadata are committed at paper/baselines/circom_multislot_relation.circom and paper/experiments/circom_multislot_baseline.json.')
    curve_baseline_prove = curve_baseline['timings']['prove']
    curve_baseline_verify = curve_baseline['timings']['verify']
    add_para(doc,f'A stronger curve-level baseline instantiates the same curve-generic reconstruction relation on BN254 G1: ElGamal ciphertexts, cross-key negation proofs, Bayer–Groth rerandomized permutation, per-slot OR proofs, and exact residual-carrier coverage all remain present. The baseline uses SHA3 Fiat–Shamir rather than the production StarkCurve Poseidon domain. A new BN254 Borsh v3 codec serializes 32-byte compressed G1 points and canonical big-endian scalars; the measured proof/statement sizes are therefore {curve_baseline["wire_shape"]["proof_bytes"]:,}/{curve_baseline["wire_shape"]["statement_bytes"]:,} bytes rather than inferred. The stable precompile ABI accepts this BN254/BayerGrothSlotOr/SHA3 combination, and a native ABI verifier roundtrips encoded requests. At n = 52 and k = 13, 30 release samples after one untimed warm-up have BN254 median/P95 proving {curve_baseline_prove["median_us"] / 1000:.1f}/{curve_baseline_prove["p95_us"] / 1000:.1f} ms and verification {curve_baseline_verify["median_us"] / 1000:.1f}/{curve_baseline_verify["p95_us"] / 1000:.1f} ms; the production StarkCurve medians from the committed grid are {native_ms(native_52_13, "prove_median_us"):.1f} ms and {native_ms(native_52_13, "verify_median_us"):.1f} ms on the same host class. Roundtrip, truncation, tampering, wrong-domain, and plaintext-semantics tests cover the codec, ABI, and proof package. This is a protocol-instantiation and native-ABI comparison, not an on-chain deployment or chain consensus claim.')
    add_para(doc,f'The same Rust reconstruction implementation is compiled to wasm32 through client-wasm. The bridge returns a BrowserReconstructionV3Bundle containing the canonical Borsh statement and proof, decodes it, and verifies it with the production Poseidon transcript domain before reporting a row. In the 30-sample release Node/V8 run, n = 52 and k = 13 has proving median/mean±sample-sd/P95 {timing_summary(wasm_52_13, "prove")}, and verification {timing_summary(wasm_52_13, "verify")}; the proof is {int(wasm_52_13["proof_bytes"])/1000:.2f} KB and the statement-plus-proof bundle is {int(wasm_52_13["bundle_bytes"])/1000:.2f} KB. Median WASM proving is {float(wasm_52_13["prove_median_ms"])/native_ms(native_52_13, "prove_median_us"):.1f} times the native result on this machine and remains below one second. The reference grid, commands, warm-up policy, environment, and hashes are recorded in paper/experiments. This grid remains a Node/V8 host measurement, not a browser-page measurement.')
    add_para(doc,f'Two separate automated browser-page runs use Chrome 153.0.8010.53 on the recorded macOS host. The Chrome DevTools Protocol opens an isolated temporary profile, serves the web-target package from a local server, and waits for the same ten-cell result in HeadlessChrome and headed modes. For n = 52 and k = 13, HeadlessChrome has 30-sample median/P95 proving {headless_chrome_52_13["prove_median_ms"]:.1f}/{headless_chrome_52_13["prove_p95_ms"]:.1f} ms and verification {headless_chrome_52_13["verify_median_ms"]:.1f}/{headless_chrome_52_13["verify_p95_ms"]:.1f} ms; headed Chrome has {headed_chrome_52_13["prove_median_ms"]:.1f}/{headed_chrome_52_13["prove_p95_ms"]:.1f} and {headed_chrome_52_13["verify_median_ms"]:.1f}/{headed_chrome_52_13["verify_p95_ms"]:.1f} ms. A manually opened user-normal Safari 18.3 page on the same recorded host completes the identical grid; its median/P95 proving and verification at n = 52, k = 13 are {desktop_safari_52_13["prove_median_ms"]:.1f}/{desktop_safari_52_13["prove_p95_ms"]:.1f} and {desktop_safari_52_13["verify_median_ms"]:.1f}/{desktop_safari_52_13["verify_p95_ms"]:.1f} ms. Module initialization after page script start is {headless_chrome["initialization"]["wasm_initialized_relative_ms"] - headless_chrome["initialization"]["script_start_relative_ms"]:.1f} ms in headless Chrome, {headed_chrome["initialization"]["wasm_initialized_relative_ms"] - headed_chrome["initialization"]["script_start_relative_ms"]:.1f} ms in headed Chrome, and {desktop_safari["initialization"]["wasm_initialized_relative_ms"] - desktop_safari["initialization"]["script_start_relative_ms"]:.1f} ms in desktop Safari. The Chrome runs are automated isolated-profile measurements; Safari is a user-normal desktop measurement. None of these runs is Android, iOS, full-network-cold-load, cache-state, or peak-memory coverage.')
    chrome_memory_stats = chrome_memory['collection']['memory']
    add_para(doc,f'A separate HeadlessChrome run repeats the ten-cell, 30-sample grid with Chrome DevTools Protocol Performance.getMetrics polling every {chrome_memory_stats["sampling_interval_ms"]} ms and a 20 ms yield between cells. It observes {chrome_memory_stats["metric_samples"]:,} renderer samples, with peak used/total JS heap {chrome_memory_stats["js_heap_used_peak_bytes"] / (1024 * 1024):.1f}/{chrome_memory_stats["js_heap_total_peak_bytes"] / (1024 * 1024):.1f} MiB. Sampling and yields perturb scheduling, so this is not a fourth timing run. It measures only the renderer JavaScript heap, not browser-process RSS, native/WASM-process peak allocation, Safari, Android, or iOS memory.')
    network_summary = network_loopback['summary']
    add_para(doc,f'A separate cache-disabled loopback experiment performs 30 independent page loads. Before each load, CDP clears and disables the browser cache; the page then downloads HTML, JavaScript, and the 243,642-byte WASM module from a local HTTP/1.1 server and executes one n = 52, k = 13 proof. Browser-reported transfer is exactly {network_summary["browser_transfer_bytes_total"]["median"]:,} bytes per run, while the server writes {network_summary["server_bytes_total"]["median"]:,} body bytes; the {network_summary["browser_transfer_bytes_total"]["median"] - network_summary["server_bytes_total"]["median"]}-byte difference is accounted for by response headers. Median/P95 WASM resource duration is {network_summary["wasm_duration_ms"]["median"]:.1f}/{network_summary["wasm_duration_ms"]["p95"]:.1f} ms, module initialization is {network_summary["wasm_initialized_ms"]["median"]:.1f}/{network_summary["wasm_initialized_ms"]["p95"]:.1f} ms, and the one-sample proof/verify pair is {network_summary["prove_ms"]["median"]:.0f}/{network_summary["verify_ms"]["median"]:.0f} ms median. This controls code-download and cache state, but it is loopback only: proof upload, TCP cold start, LAN, Internet, and peak memory remain outside its claims.')
    upload_summary = network_upload['summary']
    add_para(doc,f'The upload variant extends this controlled loopback experiment to the actual proof package. A new WASM export generates one n = 52, k = 13 statement/proof bundle, verifies and Borsh-decodes it, and returns the canonical {upload_summary["upload_request_bytes"]["median"]:,}-byte wire bundle. The page sends those bytes as an HTTP/1.1 binary POST; the Node server decodes the bundle and runs the production WASM verifier before returning its SHA-256. Across 30 cache-disabled runs, median/P95 upload wall time is {upload_summary["upload_wall_ms"]["median"]:.1f}/{upload_summary["upload_wall_ms"]["p95"]:.1f} ms. Browser download transfer is {upload_summary["browser_transfer_bytes_total"]["median"]:,} bytes, the server receives that code plus the {upload_summary["upload_request_bytes"]["median"]:,}-byte proof bundle, and every upload is accepted only after verification. Resource Timing reports a 432-byte transfer for the upload response separately from the 27,750-byte request body. This closes the local wire-upload boundary, but still does not model cold TCP setup, TLS, LAN transport, Internet transport, or service workers.')
    service_worker_summary = network_service_worker['summary']
    add_para(doc,f'A separate service-worker experiment installs a same-origin cache for only the benchmark HTML, JavaScript, and 247,743-byte WASM module before the measured loads; proof upload and result submission always bypass that cache. Across 30 controlled warm loads, every run reports zero Resource Timing transfer for HTML, JavaScript, and WASM, while the server observes exactly the {service_worker_summary["upload_request_bytes"]["median"]:,}-byte proof upload and verifies it. Median/P95 WASM resource duration is {service_worker_summary["wasm_duration_ms"]["median"]:.1f}/{service_worker_summary["wasm_duration_ms"]["p95"]:.1f} ms, module initialization is {service_worker_summary["wasm_initialized_ms"]["median"]:.1f}/{service_worker_summary["wasm_initialized_ms"]["p95"]:.1f} ms, and upload wall time is {service_worker_summary["upload_wall_ms"]["median"]:.1f}/{service_worker_summary["upload_wall_ms"]["p95"]:.1f} ms. This is a warm service-worker loopback measurement, not a cold-install measurement, browser HTTP-cache study, TLS/LAN/Internet path, or offline-availability claim.')
    cold_service_worker_summary = network_cold_service_worker['summary']
    add_para(doc,f'A cold-install companion uses a unique page scope, service-worker script query, and Cache API name for each of 30 runs. Browser HTTP cache is cleared and disabled, and the server observes exactly five requests per run: the cold page, worker script, upload HTML, JavaScript, and {cold_service_worker_summary["cached_bytes_total"]["median"] - 6827 - 18618:,}-byte WASM body. It writes {cold_service_worker_summary["cached_bytes_total"]["median"]:,} bytes into Cache Storage and receives {cold_service_worker_summary["server_bytes_total"]["median"]:,} body bytes in total. Median/P95 registration is {cold_service_worker_summary["register_ms"]["median"]:.1f}/{cold_service_worker_summary["register_ms"]["p95"]:.1f} ms, active-ready is {cold_service_worker_summary["ready_ms"]["median"]:.1f}/{cold_service_worker_summary["ready_ms"]["p95"]:.1f} ms, and total measured installation is {cold_service_worker_summary["total_ms"]["median"]:.1f}/{cold_service_worker_summary["total_ms"]["p95"]:.1f} ms. This measures first installation in isolated scopes, not update invalidation, browser HTTP-cache reuse, TLS, LAN, or Internet transport.')
    service_worker_update_summary = network_service_worker_update['summary']
    add_para(doc,f'An update-invalidations companion keeps the worker URL, scope, and cache name fixed within each run while changing the worker bytes from version 1 to version 2. The server records both worker versions, both generations fetch the three static assets, and the page observes controller version 1 then 2 before reporting an activated controller. Across 30 unique-scope updates, initial registration median/P95 is {service_worker_update_summary["initial_register_ms"]["median"]:.1f}/{service_worker_update_summary["initial_register_ms"]["p95"]:.1f} ms; `registration.update()` through activation and cache inspection is {service_worker_update_summary["update_call_ms"]["median"]:.1f}/{service_worker_update_summary["update_call_ms"]["p95"]:.1f} ms; and total measured update is {service_worker_update_summary["total_ms"]["median"]:.1f}/{service_worker_update_summary["total_ms"]["p95"]:.1f} ms. Each generation writes {service_worker_update_summary["initial_cached_bytes_total"]["median"]:,} cached bytes and the server sends {service_worker_update_summary["server_bytes_total"]["median"]:,} bytes across nine observations. This measures same-URL byte-update invalidation with browser HTTP cache disabled, not normal browser HTTP-cache reuse, TLS, LAN, or Internet transport.')
    http_cache_summary = network_http_cache['summary']
    add_para(doc,f'A separate no-service-worker companion measures normal browser HTTP-cache reuse. The server marks the benchmark HTML, JavaScript, and 247,743-byte WASM module `public,max-age=31536000,immutable`; one seed load clears and populates the cache, and each of 30 measured loads then uses the same stable URLs with browser HTTP cache enabled. Every measured run reports zero Resource Timing transfer for all three assets, while the server observes only the {http_cache_summary["upload_request_bytes"]["median"]:,}-byte proof upload and verifies it. Median/P95 WASM resource duration is {http_cache_summary["wasm_duration_ms"]["median"]:.1f}/{http_cache_summary["wasm_duration_ms"]["p95"]:.1f} ms, module initialization is {http_cache_summary["wasm_initialized_ms"]["median"]:.1f}/{http_cache_summary["wasm_initialized_ms"]["p95"]:.1f} ms, and upload wall time is {http_cache_summary["upload_wall_ms"]["median"]:.1f}/{http_cache_summary["upload_wall_ms"]["p95"]:.1f} ms. This measures ordinary HTTP-cache reuse, not service-worker Cache Storage, TLS, LAN, or Internet transport.')
    safari_http_cache_summary = network_safari_http_cache['summary']
    add_para(doc,f'A manual user-normal Safari 18.3 companion repeats the ordinary browser-cache experiment on the same immutable loopback origin. Across 30 measured loads after one seed, every HTML/JavaScript/WASM transfer is zero, each proof upload is the same {safari_http_cache_summary["upload_request_bytes"]["median"]:,}-byte package, and the server verifies it. Median/P95 WASM resource duration is {safari_http_cache_summary["wasm_duration_ms"]["median"]:.1f}/{safari_http_cache_summary["wasm_duration_ms"]["p95"]:.1f} ms, module initialization is {safari_http_cache_summary["wasm_initialized_ms"]["median"]:.1f}/{safari_http_cache_summary["wasm_initialized_ms"]["p95"]:.1f} ms, and upload wall time is {safari_http_cache_summary["upload_wall_ms"]["median"]:.1f}/{safari_http_cache_summary["upload_wall_ms"]["p95"]:.1f} ms. This provides desktop cross-browser HTTP-cache evidence, not mobile-device, TLS, LAN, Internet, or service-worker behavior.')
    http_current_summary = network_http_current['summary']
    tls_summary = network_tls['summary']
    add_para(doc,f'To separate transport from page-version effects, the current upload page was also rerun once over HTTP and once over TLS. Both 30-run pairs clear the browser cache, download the same {http_current_summary["browser_transfer_bytes_total"]["median"]:,} browser-transfer bytes, receive the same {http_current_summary["server_bytes_total"]["median"]:,} server-side bytes, and upload the same verified {http_current_summary["upload_request_bytes"]["median"]:,}-byte bundle. Median/P95 upload wall time is {http_current_summary["upload_wall_ms"]["median"]:.1f}/{http_current_summary["upload_wall_ms"]["p95"]:.1f} ms over HTTP and {tls_summary["upload_wall_ms"]["median"]:.1f}/{tls_summary["upload_wall_ms"]["p95"]:.1f} ms over TLS on this loopback host. The TLS run uses a temporary self-signed RSA-2048 127.0.0.1 certificate and Chrome certificate-error bypass, so it measures local TLS transport rather than public PKI, LAN, or Internet behavior.')
    next_table_caption('WASM reconstruction benchmark on Node/V8 with 30 timed samples')
    add_table(doc,['n','k','Prove: median / mean±sd / P95','Verify: median / mean±sd / P95','Proof','Total'],[
        (str(n),str(k),timing_summary(wasm[(n,k)],'prove'),timing_summary(wasm[(n,k)],'verify'),f'{int(wasm[(n,k)]["proof_bytes"])/1000:.2f} KB',f'{int(wasm[(n,k)]["bundle_bytes"])/1000:.2f} KB')
        for n,k in [(13,1),(26,13),(52,13),(52,26)]
    ],widths=[0.45,0.45,1.5,1.5,0.8,0.8])
    browser_table_rows = []
    for n,k in [(13,1),(26,13),(52,1),(52,13),(52,26)]:
        for label, result in [('Headless Chrome',headless_chrome),('Headed Chrome',headed_chrome),('Desktop Safari',desktop_safari)]:
            row = next(item for item in result['results'] if int(item['n']) == n and int(item['k']) == k)
            browser_table_rows.append((str(n),str(k),label,f'{row["prove_median_ms"]:.1f} / {row["prove_p95_ms"]:.1f}',f'{row["verify_median_ms"]:.1f} / {row["verify_p95_ms"]:.1f}',f'{int(row["bundle_bytes"])/1000:.2f} KB'))
    next_table_caption('Browser-page benchmarks on macOS, median / P95, 30 timed samples')
    add_table(doc,['n','k','Mode','Prove ms','Verify ms','Bundle'],browser_table_rows,widths=[0.32,0.32,0.55,0.95,0.95,0.58])
    next_table_caption('Measured native component attribution for n=52 and k=13')
    add_table(doc,['Stage','Prove cost','Verify cost','Interpretation'],[
        ('Residual and statement setup',f'{ns_ms(component_52_13, "residual_setup_ns"):.1f} ms','—','State-derived carriers and public statement construction.'),
        ('Cross-key proofs',f'{ns_ms(component_52_13, "cross_key_ns"):.1f} ms',f'{ns_ms(component_52_13, "verify_cross_key_ns"):.1f} ms','Cost attributable to k carrier-link relations.'),
        ('Bayer–Groth',f'{ns_ms(component_52_13, "bayer_groth_ns"):.1f} ms',f'{ns_ms(component_52_13, "verify_bayer_groth_ns"):.1f} ms','Cost attributable to hidden permutation and rerandomization.'),
        ('Slot OR proofs',f'{ns_ms(component_52_13, "slot_or_ns"):.1f} ms',f'{ns_ms(component_52_13, "verify_slot_or_ns"):.1f} ms','Cost attributable to n slot-membership relations.'),
        ('Serialization',f'{ns_ms(component_52_13, "serialization_ns"):.1f} ms','—','Borsh statement and proof encoding only.'),
    ],widths=[1.15,0.85,0.85,3.2])
    add_para(doc,'The component table is a measured stage attribution, not a claim that the protocol remains secure when a component is removed. It answers the ablation cost question by showing the wall-time contribution of cross-key, shuffle, slot-OR, and serialization stages. The closest Mental Poker comparison remains an operation-count comparison because its authors do not publish compatible runtime or proof-byte measurements.')

    doc.add_heading('9. Limitations and future work', level=1)
    limits=['A malicious player that never submits is an availability event. Deadlines, deposits, or a replacement submitter are needed for an application-level policy.','Authenticated reveal-token lineage is essential. Without the residual derivation, the veto theorem does not hold.','The deck size, owner-residual carrier count, public keys, canonical cards, epoch, and state digest are public; the protocol does not hide these metadata.','A carrier-specific |U| ≥ 2 residual takes the normal zero branch and the corresponding canonical card remains in the new deck. Threshold removal of such a jointly unknown card is a future protocol extension and is not required for the present reconstruction guarantee.','The UC theorem is an F_NIZK^R_RECON-hybrid result. The current cumulative Poseidon Fiat–Shamir transcript is not claimed to realize concurrent UC NIZK.','The Node/V8, automated Chrome, and one desktop Safari timing results do not cover Android, iOS, other Safari versions, cold TCP connection, TLS, LAN, Internet latency, service-worker behavior, or controlled browser-cache states. Chrome memory coverage is sampled renderer-JS-heap only and does not provide browser-process RSS or Safari/mobile peak memory. The network experiments control cache state and binary proof upload over loopback only.','Adaptive corruption requires erasures or non-committing techniques.','Multiple authorization of the same owner-residual carrier is excluded by the authenticated missing-key invariant.']
    limits[5] = 'The Node/V8, automated Chrome, and one desktop Safari timing results do not cover Android, iOS, other Safari versions, public PKI, LAN, Internet latency, or remote cold-connection behavior. The TLS experiment uses a temporary self-signed certificate and certificate-error bypass over loopback. Service-worker and HTTP-cache evidence covers isolated cold installation, same-URL byte-update invalidation, warm Cache Storage hits, immutable Chrome HTTP-cache reuse, and manual desktop Safari HTTP-cache reuse over loopback; it does not cover cross-browser SW update behavior or remote transport. Chrome memory coverage is sampled renderer-JS-heap only and does not provide browser-process RSS or mobile peak memory.'
    for s in limits: doc.add_paragraph(s,style='List Bullet')

    doc.add_heading('10. Conclusion', level=1)
    add_para(doc,'The reconstruction protocol addresses a liveness gap in cooperative Mental Poker. Authenticated reveal-token subtraction yields a residual ciphertext carrier for every card: owner-residual when one token is missing, jointly keyed when several tokens are missing. Owner-residual carriers authorize exact removals; a jointly keyed carrier authorizes no negative branch, so the corresponding canonical card remains in the freshly encrypted deck. The active table can therefore continue even when no individual player knows an old card plaintext. The proof system combines hidden mapping, carrier-to-plaintext binding, per-slot zero-or-negative semantics, and state/transcript binding in one auditable package.')
    add_para(doc,'An accepted ideal-NIZK submission has a witness with exact residual-carrier coverage; the concrete implementation has the same semantic consequence only under the stated component extraction assumptions. Authenticated lineage and missing-key binding then prevent a player from vetoing another player’s card except with the stated state, refinement, and concrete-extraction errors. The Lean layer connects the algebraic relation to this explicit boundary without claiming a verified concurrent Fiat–Shamir realization.')

    doc.add_heading('Declarations', level=1)
    add_para(doc,'Code and reproducibility. The implementation, Lean development, benchmark grids, measurement metadata, baseline circuit, and reproduction scripts are available at ' + REPOSITORY_URL + '. The committed native and WASM measurements are in reconstruction_stark.csv and reconstruction_wasm.csv; their environment, commands, hashes, and limits are recorded in benchmark_metadata.json. The reproduction runner writes fresh measurements separately rather than overwriting the committed baselines.')
    add_para(doc,'Data availability. No proprietary or third-party experimental data were used. The paper’s measurement files and canonical semantic fixture are included in the repository.')
    add_para(doc,'License. This article is distributed under ' + arxiv['license'] + '. The repository implementation is licensed separately under BUSL-1.1.')
    add_para(doc,'Conflict of interest. ' + metadata.get('conflict_of_interest', 'The author declares no conflict of interest.'))
    add_para(doc,'Funding. No funding was declared for this work.' if not metadata.get('funding') else 'Funding. ' + metadata['funding'])
    contribution = metadata.get('authors', [{}])[0].get('contribution') if metadata.get('authors') else None
    add_para(doc,'Author contributions. ' + (contribution if contribution else 'Qining Lin contributed to all aspects of the work.'))
    add_para(doc,'AI assistance. AI-assisted text and workflow tools (Codex/GPT-5) were used for language editing, manuscript preparation, and reproducibility support. The author reviewed and takes full responsibility for all technical claims, proofs, data, code, and final content.')

    doc.add_heading('Appendix A. Relation to dropout-tolerant mental poker', level=1)
    add_para(doc,'Castellà-Roca, Sebé, and Domingo-Ferrer study dropout-tolerant Mental Poker without a trusted third party and use zero-knowledge techniques to let a game continue after a player leaves [7]. Their construction is a relevant reference for liveness, but its prover-side authorization does not bind each removal to authenticated per-card owner-residual lineage. A prover may therefore be able to veto a card that is not its own. The present protocol treats exclusion of that behavior as a separate security goal: every accepted negative branch must correspond exactly to an authenticated singleton missing-token derivation for the submitting owner.')
    add_para(doc,'The protocol abstractions and security boundaries therefore differ. Our construction derives a residual carrier from an authenticated, state-bound reveal-token transcript, proves exact coverage for the owner-residual subset, hides the carrier-to-slot mapping, and enforces a per-slot zero-or-negative plaintext relation. Only one missing token yields an owner-residual carrier that one participant can decrypt and use to authorize removal. Several missing tokens yield a jointly keyed carrier whose canonical card is retained without revealing its plaintext. Accordingly, [7] supports the dropout-tolerance motivation but does not establish the residual-carrier semantics, non-owner-veto bound, or ideal-NIZK-hybrid composition theorem stated here.')

    doc.add_heading('References', level=1)
    refs=['R. Canetti. “Universally Composable Security: A New Paradigm for Cryptographic Protocols.” In IEEE FOCS, pp. 136–145, 2001. doi:10.1109/SFCS.2001.959888.','S. Bayer and J. Groth. “Efficient Zero-Knowledge Argument for Correctness of a Shuffle.” In EUROCRYPT, LNCS 7237, pp. 263–280, 2012. doi:10.1007/978-3-642-29011-4_17.','D. Chaum and T. P. Pedersen. “Wallet Databases with Observers.” In CRYPTO, LNCS 740, pp. 89–105, 1992. doi:10.1007/3-540-48071-4_7.','R. Cramer, I. Damgård, and B. Schoenmakers. “Proofs of Partial Knowledge and Simplified Design of Witness Hiding Protocols.” In CRYPTO, LNCS 839, pp. 174–187, 1994. doi:10.1007/3-540-48658-5_19.','A. Fiat and A. Shamir. “How To Prove Yourself: Practical Solutions to Identification and Signature Problems.” In CRYPTO, LNCS 263, pp. 186–194, 1986. doi:10.1007/3-540-47721-7_12.','C.-P. Schnorr. “Efficient Identification and Signatures for Smart Cards.” In CRYPTO, LNCS 435, pp. 239–252, 1989. doi:10.1007/0-387-34805-0_22.','J. Castellà-Roca, F. Sebé, and J. Domingo-Ferrer. “Dropout-Tolerant TTP-Free Mental Poker.” In Trust, Privacy, and Security in Digital Business, LNCS 3592, pp. 30–40, 2005. doi:10.1007/11537878_4.','J. Castellà-Roca. “Contributions to Mental Poker.” PhD thesis, Universitat Autònoma de Barcelona, 2005.','A. Barnett and N. P. Smart. “Mental Poker Revisited.” In Cryptography and Coding, LNCS 2898, pp. 370–383, 2003. doi:10.1007/978-3-540-40974-8_29.','K. Kurosawa, Y. Katayama, and W. Ogata. “Reshufflable and Laziness Tolerant Mental Card Game Protocol.” IEICE Transactions on Fundamentals, 1997.','W. H. Soo, A. Samsudin, and A. Goh. “Efficient Mental Card Shuffling via Optimised Arbitrary-Sized Benes Permutation Network.” In Information Security, LNCS 2433, pp. 446–458, 2002. doi:10.1007/3-540-45811-5_35.','I. Bentov, R. Kumaresan, and A. Miller. “Instantaneous Decentralized Poker.” In ASIACRYPT, LNCS 10625, pp. 410–440, 2017. doi:10.1007/978-3-319-70697-9_15.','B. David, R. Dowsley, and M. Larangeira. “Kaleidoscope: An Efficient Poker Protocol with Payment Distribution and Penalty Enforcement.” In Financial Cryptography and Data Security, LNCS 10958, pp. 500–519, 2018. doi:10.1007/978-3-662-58387-6_27.','B. David, R. Dowsley, and M. Larangeira. “ROYALE: A Framework for Universally Composable Card Games with Financial Rewards and Penalties Enforcement.” In Financial Cryptography and Data Security, LNCS 11598, pp. 282–300, 2019. doi:10.1007/978-3-030-32101-7_18.']
    add_references(doc, REFERENCES)
    # core properties
    props=doc.core_properties; props.title=metadata['title']; props.subject='Cryptography preprint prepared for arXiv'; props.author=author_block(metadata); props.keywords=', '.join(metadata['keywords'])
    path=OUT/'composable_privacy_preserving_deck_reconstruction.docx'; doc.save(path); print(path)
    print(write_arxiv_submission_fields(metadata))

def build_zh():
    global TWO_COLUMN_BODY
    TWO_COLUMN_BODY = False
    metadata = submission_metadata(); validate_submission_metadata(metadata)
    make_figures()
    doc=Document(); setup_styles_zh(doc)
    sec=doc.sections[0]; sec.top_margin=Inches(0.75); sec.bottom_margin=Inches(0.7); sec.left_margin=Inches(0.82); sec.right_margin=Inches(0.82)
    header=sec.header.paragraphs[0]; header.text='面向心智扑克的认证隐私保护牌组重建'; header.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    header.runs[0].font.size=Pt(8); header.runs[0].font.color.rgb=RGBColor.from_string(GRAY)
    footer=sec.footer.paragraphs[0]; footer.alignment=WD_ALIGN_PARAGRAPH.CENTER; footer.add_run('Poker Protocol  •  '); add_page_field(footer)
    for r in footer.runs: r.font.size=Pt(8); r.font.color.rgb=RGBColor.from_string(GRAY)

    p=doc.add_paragraph(style='Title'); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run('面向心智扑克的认证隐私保护牌组重建')
    p=doc.add_paragraph(style='Subtitle Custom'); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run('精确 carrier 覆盖 槽位语义与机器检查组合边界')
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run(author_block(metadata))
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_before=Pt(25); p.add_run('2026 年 9 月 17 日  •  poker_protocol 代码仓库')
    for identity_line in author_identity_lines(metadata):
        p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run(identity_line)
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_after=Pt(4)
    p.add_run('代码仓库：').bold=True; add_hyperlink(p,'github.com/linqining/poker_protocol',REPOSITORY_URL)
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_before=Pt(36)
    r=p.add_run('主张边界'); r.bold=True; r.font.color.rgb=RGBColor.from_string(BLACK)
    add_para(doc,'本文的组合定理在会话绑定的 F_NIZK^R_RECON hybrid 中成立，不声称当前 Poseidon Fiat–Shamir 实现已经实现并发 UC NIZK。具体 Rust 证明的知识可靠性仍依赖 Bayer–Groth 与各 Sigma 组件在各自 challenge checkpoint 上的提取性质。Lean 检查 residual-carrier 血统、代数关系和组合边界；计算安全与字节 refinement 保持为显式条件。','Small Note')
    doc.add_page_break()

    doc.add_heading('摘要', level=1)
    add_para(doc,'心智扑克通过加密和可验证洗牌隐藏完整牌序，但多人洗牌通常要求所有参与者完成各自步骤。一名玩家离线、崩溃或拒绝继续时，其他玩家必须在不泄露、不篡改其余牌的前提下重建下一副牌；单独的 shuffle argument 并不能解决这一活性缺口。')
    add_para(doc,'本文给出一种基于 residual carrier 的牌组重建协议。一般地，对已提交的 reveal token 做群减法后，所得 residual carrier 加密在缺失玩家公钥之和下。缺少一个 token 时，唯一 owner 可以解密；缺少两个或更多 token 时，没有任何单个在线玩家知道原牌。协议仍可继续：只有经过认证的 owner-residual carrier 才能授权负贡献；jointly keyed 且无人可单独解密的牌只能走零分支，因此会保留在新构造的 canonical deck 中。')
    add_para(doc,'证明系统把每个 canonical slot 的贡献限制为聚合公钥下的零加密或该槽牌点负元的加密。跨密钥证明把负分支连接到认证 owner-residual carrier；隐藏 shuffle 隐藏映射；二分支 OR 证明强制逐槽语义。具体实现的安全结论依赖组件提取假设；组合定理则单独在 F_NIZK^R_RECON hybrid 中证明，不使用随机预言机编程或单一 final-challenge 回卷。Lean 将公共有效性、认证覆盖和逐槽明文关系组合在一个机器检查边界中。')
    p=doc.add_paragraph(); r=p.add_run('关键词：'); r.bold=True; p.add_run('心智扑克；可验证洗牌；ElGamal；认证重建；非交互零知识；形式化验证。')

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
        ('5','组合安全与形式化','形式化 F_RECON，并在 F_NIZK^R_RECON hybrid 中证明静态腐化组合结果。'),
    ],widths=[0.5,1.45,4.2])
    add_figure(doc,ASSET/'fig_protocol.png','图 1  重建路径将认证血统与当前轮参与状态分离；超时只产生无操作，不产生未经授权的负贡献。')

    doc.add_heading('2 背景与相关工作', level=1)
    add_para(doc,'可验证洗牌包括 Bayer–Groth [2]、Furukawa–Sako [22]、Neff [23]、Groth [24] 和 UC mixnet [25] 等不同路线。Schnorr、Chaum–Pedersen 与 CDS 部分知识证明支持本文的线性和析取关系 [3,4,6]。这些组件证明置换或代数关系正确，却不决定先前状态中的哪个 carrier 有权删除 canonical card。')
    add_para(doc,'Fiat–Shamir [5]、随机预言机方法 [18]、forking 分析 [19]、online extractor [20] 与 quantum-ROM 结果 [21] 的保证不同，不能直接替代 UC 实例化证明。本文因此把组合结论放在 F_NIZK^R_RECON hybrid；Poseidon Fiat–Shamir 代码只作为 concrete standalone implementation 评估。形式化方面，EasyCrypt、CryptHOL、Jasmin 和 HACL* [28–31] 提供了更强的 proof-to-code 路线；本文 Lean 结果覆盖代数与组合边界，并与 Rust 交叉校验完整 statement schema 和一个 seeded proof-instance schema，但群实现、组件证明保证、具体 Fiat–Shamir realization、完整字节级 serialization refinement 与认证 host state 仍是显式义务。')
    add_para(doc,'Barnett–Smart [9] 提供被广泛复用的 ElGamal mental-poker 基础和洗牌验证。Kurosawa 等人 [10] 与 Soo 等人 [11] 分别用 secret sharing 和可重排网络处理有界缺员/懒更新，但固定阈值与 coalition 恢复能力构成安全代价。较新的金融强制路线包括 Instantaneous Decentralized Poker [12]、Kaleidoscope [13] 和 ROYALE [14]；它们强化锁定、处罚和可组合支付语义，但缺席处理主要是 forfeit、超时或重开，而不是从认证 reveal-token 血统导出逐 carrier 删除授权，也没有本文的逐槽 {0,−m_i} 语义。')
    add_para(doc,'Castellà-Roca、Sebé 和 Domingo-Ferrer 已研究无需可信第三方的 dropout-tolerant mental poker，并用零知识技术让游戏在玩家退出后继续 [7]。该方案可作为活性方面的参考，但其 prover 侧授权并未像本文一样把每个删除绑定到认证的 owner-residual 血统，因此存在 prover 否决非自己手牌的可能。本文与其目标相近，但安全边界不同：本文显式推导 residual carrier，区分 singleton 与 multi-key missing set，并增加逐槽语义、owner-residual 精确覆盖、跨密钥证明以及机器检查组合边界。')
    add_para(doc,'更早的 TTP-free 路线要么要求离场者披露自己的秘密层，要么用 secret sharing 容忍固定数量缺员；后者的足够大 coalition 可恢复全部牌面信息。[7] 使用 CDS 部分知识证明和 veto 因子，使剩余玩家无需离场者配合也能继续，是本文最接近的活性先行方案。')
    add_para(doc,'为避免伪造运行数据，这里比较协议边界。设 [7] 中活跃玩家数为 N、牌数 d=52、历史发牌轮数为 r。dropout 后需重建整副牌：每个 face-down card 由 N 个 threshold-ElGamal 分量组成，公开牌组共 dN 个分量；每个玩家发布 d 个 re-masking pair，并给出一个非 veto CDS 证明与 r 个 veto CDS 证明（每个覆盖 d 个 Chaum–Pedersen 实例）；后续链式 re-masking 约需 dN² 个 Chaum–Pedersen 证明，再用 Barnett–Smart shuffle 处理 dN 个密文分量。作者完整论文 [8] 明确指出 dropout 路径效率仍需提升，且未给 dropout 专用证明字节或运行时间。')
    add_para(doc,'下表将本文与最接近的 dropout-tolerant 构造进行对比。比较对象是被证明的安全语义；先行工作对活性问题的贡献仍然成立，本文进一步加入逐牌授权和机器检查的语义边界。')
    add_table(doc,['属性','Dropout-tolerant TTP-free Mental Poker [7]','本文'],[('离场处理','玩家退出后继续运行','deadline 或崩溃后继续运行'),('离场后的牌组动作','删除离场者 key share 并重建；其已抽牌回到牌组','提交 state-bound package；singleton residual 移除，jointly keyed residual 保留'),('公开牌组规模','每张牌 N 个密文分量，共 dN','d 个 canonical contribution，另有 k 个认证 residual carrier'),('证明关系规模','每玩家 r+1 个覆盖 d 实例的 CDS 证明；约 dN² 个链式 CP 证明；再执行完整 shuffle proof','k 个跨密钥证明 + 1 个 Bayer–Groth + d 个槽位 OR'),('移除授权','协议级 dropout 恢复','认证 singleton residual-carrier 血统'),('逐槽明文关系','未明确为零或负元隶属','每个槽位的 0 或 −m_i OR proof'),('映射隐私','由协议组件隐藏','hidden carrier-to-slot map 与 BG proof'),('形式化保证','论文中的密码学证明','Lean 组合边界与显式假设'),('多缺失密钥','未单列 carrier 类型','jointly keyed residual 保留，不授权删除'),('实测证据','仅符号描述；无 dropout runtime/proof bytes','native+WASM d,k 网格；d=52,k=13 bundle 27.75 KB')],widths=[1.15,2.7,2.35])

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
    add_para(doc,'附带的 Chaum–Pedersen/DLEQ 证明保证同一秘密标量同时连接 Qₚ=skₚg 和 tₚ,ᵢ=skₚCᵢ.c₁，并将证明绑定到当前牌和 epoch。令 A 为该 carrier 已提交有效 token 的玩家集合，U=Players−A 为其对应的 carrier-specific missing-token set，Q_U=Σₚ∈UQₚ。减去所有已认证 token：')
    add_equation(doc,'Rᵢ(A) = Cᵢ − Σₚ∈A(0,tₚ,ᵢ)')
    add_equation(doc,'= (rᵢg, mᵢ + rᵢP − rᵢΣₚ∈A Qₚ)')
    add_equation(doc,'= (rᵢg, mᵢ + rᵢQ_U) = Enc_{Q_U}(mᵢ; rᵢ).')
    add_para(doc,'这就是 residual carrier 的精确定义。若 |U|=1 且 U={q}，则 Q_U=Q_q，玩家 q 能解密 mᵢ；该特例称为 owner-residual carrier。若 |U|≥2，Q_U 是多个公钥之和，没有任何单个在线玩家拥有 sk_U=Σₚ∈Uskₚ，因此所有人都不知道原牌。若 U 为空，则结果进入明文或 redeal 边界，不应称为 residual carrier。')
    add_para(doc,'多缺失 token 并不阻止牌组重建。这里的 U 是每个 residual carrier 自己的 missing-token set，不是全局离线玩家数。重建从 Bᵢ=Enc_P(mᵢ;i+1) 的新 canonical base 开始。只有 owner-residual carrier 能通过跨密钥关系授权 Enc_P(−mᵢ)；jointly keyed residual 没有单个可用 owner witness，所以该槽的所有接受贡献都必须是 Enc_P(0)。最终同态和仍加密 mᵢ，旧 jointly keyed ciphertext 可以丢弃，而 mᵢ 从未向任何玩家公开。这是当前协议的正常保留分支；若要删除 jointly unknown card，需要后续门限证明扩展。')
    add_para(doc,'对 owner-residual carrier Rⱼ 及隐藏映射 i(j)，构造 Sⱼ=Enc_P(−mᵢ₍ⱼ₎;vⱼ)，并证明')
    add_equation(doc,'Q = sk_Q g,   Sⱼ.c₁ = vⱼg,   sk_Q Rⱼ.c₁ + vⱼP = Rⱼ.c₂ + Sⱼ.c₂.')
    add_para(doc,'第三个等式消去两侧的加密随机项，推出两个密文明文之和为零。Bayer–Groth 隐藏 carrier-to-slot 映射，逐槽 OR 证明再把每个 canonical slot 限制在零或负元两个分支。由此，reconstruction 的可靠性直接建立在 reveal-token 减法和认证血统之上。')
    add_figure(doc,ASSET/'fig_residual_derivation.png','图 2  Reveal-token 减法得到 residual carrier。单缺失 token 产生 owner-residual carrier；多缺失 token 产生无人可单独解密的 jointly keyed carrier，其 canonical card 在新牌组中被保留。')

    assumptions=[('A1','群与编码','实现只接受素数阶子群和 canonical encoding，并正确实现群运算。'),('A2','加密隐私','ElGamal 在 DDH 或等价假设下满足 IND-CPA。'),('A3','Residual 隐私','jointly keyed residual 至少保留一层诚实、秘密、均匀的遮罩；隐私依赖相应 fresh-DLog 困难性。'),('A4','Concrete shuffle','仅用于 Rust standalone 结论：Bayer–Groth 组件具有完备性、知识可靠性和零知识。'),('A5','Concrete linear proofs','仅用于 Rust standalone 结论：cross-key 与 slot OR 组件可在各自 FS checkpoint 提取，并具有完备性和 HVZK。'),('A6','Ideal NIZK hybrid','普通接口绑定 sid 与完整 statement，且只接受有效 aggregate witness；理想比较中另有仅模拟器可用的诚实证明接口和腐化 witness 接口。具体 FS 不被主张为 UC 实现。'),('A7','认证状态与 refinement','状态摘要不可伪造，token 绑定牌和 epoch，Rust/AIR 字节编码 refine Lean statement。'),('A8','缺失集合认证','只有 singleton missing-token set 可授权负贡献；|U|≥2 时只能走零分支。'),('A9','腐化模型','腐化静态固定，诚实 owner key 或 residual masking layer 在执行结束前不泄露。')]
    add_table(doc,['编号','假设','操作含义'],assumptions,widths=[0.48,1.45,4.25])

    doc.add_heading('4 协议', level=1)
    doc.add_heading('4.1 公共 statement', level=2)
    add_equation(doc,'S = (context_digest, epoch, D_prev, P, Q, (mᵢ), (Rⱼ), (Cᵢ)).')
    add_para(doc,'Rⱼ 是认证 owner-residual ciphertext，Cᵢ 是 prover contribution。验证器 fail closed：拒绝错误版本、长度不符、identity key 或 ciphertext、重复 canonical card、空 carrier 集以及 k>n。')
    doc.add_heading('4.2 证明生成', level=2)
    for s in ['从认证 token transcript 推导每个 |U|=1 的 Rⱼ，并用 owner secret 解密，确认其明文是互不重复的 canonical card。','采样 vⱼ，构造 Sⱼ=Enc_P(−mᵢ₍ⱼ₎;vⱼ)，并为其余 n−k 个槽构造零贡献。','对贡献向量应用隐藏 permutation 和新鲜 rerandomization。','为每对 (Rⱼ,Sⱼ) 生成跨密钥证明。','生成 Bayer–Groth 隐藏洗牌证明。','为每个 canonical slot 生成二分支 OR 证明。']:
        doc.add_paragraph(s,style='List Number')
    add_para(doc,'jointly keyed |U|≥2 residual 不进入 removal-authorizing vector，但其对应 canonical slot 仍走正常零分支并被保留，协议依然适用。carrier-to-slot 映射、分支、permutation 和随机性均不出现在 wire proof 中。')
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
    doc.add_heading('4.6 证明系统设计取舍', level=2)
    add_para(doc,'协议刻意保留 Bayer–Groth 负责隐藏置换。它正是当前实现采用的成熟洗牌证明；用通用电路编译器替换它，改变的是 trusted-setup 边界和实现栈，而不是隔离本文新增的 reconstruction 语义。因此客户端构造由 Bayer–Groth、跨密钥 Sigma proof 和逐槽 OR proof 组成。')
    add_para(doc,'贡献在于语义组合，而非宣称单个证明引擎新颖：认证 residual-carrier 血统、跨密钥负元关系、exact coverage，以及每个 canonical slot 的零或负元关系。透明的 Sigma 代数便于映射到 Lean 组件接口，并使浏览器端证明保持在实测亚秒级范围内。代价是 proof 大于succinct 聚合论证；host 侧聚合仍是未来工程方向，本文不将其用作未经实测的性能对比。')

    doc.add_heading('5 正确性与独立安全性', level=1)
    doc.add_heading('定理 1 完备性', level=2)
    add_para(doc,'若 statement 满足认证状态条件且诚实证明者执行第 4.2 节，则验证器除显式零挑战事件外均接受，失败概率至多为 O((n+k)q_H/q)。')
    add_para(doc,'证明。血统给出 Rⱼ=Enc_Q(mᵢ₍ⱼ₎;rⱼ)。诚实证明者解密唯一 canonical card，采样 vⱼ 并构造 Sⱼ=Enc_P(−mᵢ₍ⱼ₎;vⱼ)。代入第三跨密钥方程，两侧均等于 rⱼQ+vⱼP。确定性零密文为 Z_l=Enc_P(0;l+1)，选定的单射映射给出 permutation 与 rerandomizers，因此完整 Bayer–Groth witness 存在。')
    add_para(doc,'对零输入，T₀=Cᵢ.c₂=vᵢP；对负输入，T₁=Cᵢ.c₂+mᵢ=vᵢP。真实 OR branch 诚实响应，模拟 branch 由 challenge share 与 response 反向构造，两个 share 之和为全局挑战。所有 statement 字段按 canonical 顺序进入 transcript。失败只能是零挑战/share 或编程点冲突，k 个跨密钥证明与 n 个 OR proof 的并集为 O((n+k)q_H/q)。')
    doc.add_heading('定理 2 知识可靠性', level=2)
    add_para(doc,'在不调用模拟器专用接口的真实 F_NIZK^R_RECON-hybrid 执行中，A6、A7 保证普通接口的接受直接给出满足 aggregate relation 的见证，因此逐槽明文属于 {0,−mᵢ}、carrierIndex 单射并满足 exact coverage。对 concrete Rust verifier，同一结论还需 A1、A4、A5，以及分别调用各组件 extractor 的 package extractor。')
    add_para(doc,'证明。Hybrid 结论由 F_NIZK^R_RECON 的 relation check 直接得到。Concrete corollary 分别从 Bayer–Groth、每个 cross-key proof 和每个 slot proof 的 checkpoint 提取见证，再组合 exact coverage。当前实现使用累计 transcript 和多个顺序 challenge，因此本文不再声称改变一个最终 challenge 即可提取全部组件。')
    doc.add_heading('定理 3 重建语义', level=2)
    add_para(doc,'令 χᵢ=1 当且仅当某个已接受提交者拥有授权移除 mᵢ 的认证 owner-residual carrier。则')
    add_equation(doc,'Decₚ(B̃ᵢ) = 0  若 χᵢ=1；      Decₚ(B̃ᵢ) = mᵢ  若 χᵢ=0.')
    add_para(doc,'证明。对每个接受提交者应用定理 2：槽 i 的明文属于 {0,−mᵢ}，且只有映射到 i 的认证 carrier 才能产生负元。A8 保证跨玩家 carrier 集不相交，故同一槽至多一个负贡献。由同态性，Dec_P(B̃ᵢ)=mᵢ+Σ plaintext(Cₚ,ᵢ)，存在授权 carrier 时为 0，否则为 mᵢ。|U|≥2 时没有 owner-residual witness 进入 removal-authorizing vector，因此所有贡献为零，牌在不解密的条件下保留。')

    doc.add_heading('6 理想功能与组合边界', level=1)
    doc.add_heading('6.1 混合模型', level=2)
    add_para(doc,'组合结论位于 F_NIZK^R_RECON、F_STATE、F_KEY、F_SHUFFLE 与 F_REVEAL hybrid。普通接口绑定 sid 和完整公开 statement，且只在 witness 满足 aggregate relation 时接受。仅在理想比较中，模拟器可为诚实会话注册不泄露 witness 的模拟证明，并从腐化证明接口取得被接受的 witness；环境和普通协议方不能调用这些接口。具体 Poseidon Fiat–Shamir 实现不在该 UC realization claim 内。腐化集合初始化时固定；网络对手可在 deadline 前重排、延迟或丢弃消息。')
    doc.add_heading('6.2 理想功能 F_RECON', level=2)
    add_para(doc,'sid=(context,table,hand,epoch,D_prev)。状态包含 WAITING/FINAL、每名玩家的认证 carrier authorization、已接受提交者和最终加密牌组。F_STATE 提供 canonical deck、token 血统、missing-key sets 与 epoch；功能不泄露 honest plaintext、carrier-to-slot map、branch、permutation 或随机数。')
    add_table(doc,['命令','调用者','规则'],[
        ('INIT','F_STATE','拒绝重复 sid、无效 D_prev 或非唯一后继 epoch；固定静态腐化集合并进入 WAITING。'),
        ('SUBMIT','玩家或对手','拒绝错误 sid/epoch、FINAL、重复、格式错误或 F_NIZK^R_RECON 失败；其余记录公开 contribution。'),
        ('STATUS','环境','只返回 phase、接受身份、验证结果、deadline 和公开 digest。'),
        ('DEADLINE','时钟或对手','检查负分支等于提交者的认证 singleton authorization；重叠或不一致输出 STATE_INVALID，否则聚合并进入 FINAL。'),
        ('REPLAY','任意方','旧 epoch、不同 D_prev、已结束 sid 或重复 submission 均 fail closed 且不改变状态。'),
    ],widths=[1.0,1.05,4.1])
    add_para(doc,'对静态腐化玩家，模拟器控制其 F_NIZK^R_RECON 调用，因此只在该提交时获得腐化 witness；诚实 witness 始终隐藏。sid 包含 context、table、hand、epoch 与 D_prev，因此跨 table、跨 epoch replay 被拒绝。')
    doc.add_heading('6.3 组合定理', level=2)
    add_para(doc,'定理 4　在 A2、A3、A6–A9 下，hybrid protocol 对静态腐化 UC-realize F_RECON。若认证状态和字节 refinement 采用计算实现，区分优势至多为 k·ε_DDH+ε_state+ε_ser；该定理没有 Fiat–Shamir forking、random-oracle programming 或 concurrent-FS error term。')
    add_para(doc,'模拟器转发公开状态和调度事件。诚实提交发布理想状态 adapter 产生的模拟 contribution，并通过仅模拟器可用的诚实证明接口注册；理想状态仍保存规定的删除语义。腐化提交的 witness 由腐化证明接口提供，模拟器据此向 F_RECON 提交精确认证删除集合。H₀ 到 H₁ 逐个把至多 k 个诚实 Enc_P(−mᵢ;vᵢ) 替换为 Enc_P(0;v′ᵢ)，并注册模拟证明，每次替换由一个 IND-CPA reduction 支撑，总代价 k·ε_DDH。H₁ 到 H₂ 把状态和 serialization adapter 替换为理想接口，代价为 ε_state+ε_ser。H₂ 与 F_RECON 理想执行相同。UC composition 只适用于明确列出的理想功能，不证明当前 Rust proof bytes 实现 F_NIZK。')
    doc.add_heading('6.4 非己牌否决', level=2)
    add_para(doc,'在 A6–A9 下，F_NIZK^R_RECON hybrid 中 Pr[Veto(p,m)]≤ε_state+ε_ser。接受 witness 的负分支和 carrier map 必须对应 D_prev 中 p 的认证 singleton derivation。Concrete verifier 还需在 A1、A4、A5 下加入 package extraction error ε_KS。')
    add_figure(doc,ASSET/'fig_composition.png','图 4  Lean 形式化把群代数和组件接口组合为 verified_package_semantics；计算安全假设仍显式保留。')

    doc.add_heading('7 Lean 形式化', level=1)
    add_table(doc,['层','文件','机器检查结果'],[
        ('Residual 血统','ResidualCarrierProvenance.lean','由认证先前状态推出 residual carrier'),
        ('重建关系','Reconstruction.lean','逐槽关系与唯一移除语义'),
        ('跨密钥 Sigma','ReconstructionJointSigma.lean','跨密钥关系、完备性、可靠性与 HVZK'),
        ('槽位 OR','ReconstructionSlotOr.lean','完备性、可靠性与代数 HVZK'),
        ('组合边界','ReconstructionSecurity.lean','组件接口下的端到端组合语义'),
        ('Veto 界','ReconstructionVeto.lean','非己牌否决不可行性与可忽略误差并集界'),
    ],widths=[1.25,1.9,3.0])
    add_para(doc,'Statement 保存 aggregate key、owner key、canonical cards、owner-residual carriers 和 contributions。Witness 保存 removed bitmap、随机数、carrier-to-slot 单射和 exact-coverage 条件。组合定理从 well-formed statement、提取见证、代数 relation 和组件接口，一次性导出 public validity、owner-residual 精确覆盖以及逐槽零或负元语义。')
    add_para(doc,'Lean 不把 DDH、随机预言机安全、Bayer–Groth 知识可靠性或 Rust 字节级 refinement 当作群代数定理；这些条件进入 ComponentInterface 与 Reduction，从而保持信任边界可见。')

    doc.add_heading('8 实现与可复现性', level=1)
    add_table(doc,['组件','职责'],[('poker-protocol-core','曲线、ElGamal 与 transcript。'),('poker-protocol-bg','Bayer–Groth shuffle。'),('poker-protocol-proofs','重建、跨密钥和 OR 证明。'),('poker_protocol','原生 adapter、ABI 与牌局集成。'),('client-wasm','浏览器桥接与可复现 WASM 基准。'),('poker_protocol_lean','形式规范与组合定理。')],widths=[2.1,4.0])
    add_para(doc,'代码已统一使用 residual_carrier / residual_carriers；只有单 owner 解密 API 使用 owner_residual_carrier。ABI 字段名称已更新，但序列化字段顺序保持不变。当前 V3 producer 为每个 |U|=1 的 owner 构造 residual vector；若同一牌缺少两个或更多 token，不创建 removal-authorizing entry，canonical slot 在重建中保持不变。')
    p=doc.add_paragraph(); p.add_run('代码仓库：').bold=True; add_hyperlink(p,REPOSITORY_URL,REPOSITORY_URL)
    add_para(doc,'复现命令如下：')
    add_equation(doc,'./scripts/install_repro_deps.sh\n./scripts/reproduce_paper.sh')
    add_para(doc,'安装脚本在用户目录或仓库 .repro/toolchains 下配置锁定版本的 Rust、Lean、Node.js 与 wasm-pack，不调用 sudo；--check 只检查环境。复现脚本先核对已提交基线和源码哈希，再执行 Rust、WASM 与 Lean 验证，并将新测量写入 .repro/results，避免覆盖论文基线。每轮运行均在 run_metadata.json 中记录机器、工具版本、Git 状态和结果哈希。')
    native = benchmark_rows('reconstruction_stark.csv')
    wasm = benchmark_rows('reconstruction_wasm.csv')
    components = benchmark_rows('reconstruction_components.csv')
    native_52_13 = native[(52, 13)]
    wasm_52_13 = wasm[(52, 13)]
    component_52_13 = components[(52, 13)]
    add_para(doc,f'参考实测使用 StarkCurve、生产 RECONSTRUCT_POSEIDON transcript 域、release 构建、一次非计时预热，并对每个网格点计时 30 次。n=52、k=13 时，原生证明的中位数/均值±样本标准差/P95 为 {timing_summary(native_52_13, "prove", native=True)}，验证为 {timing_summary(native_52_13, "verify", native=True)}；proof 为 {int(native_52_13["proof_bytes"])/1000:.2f} KB，证明与验证峰值分配分别为 {int(native_52_13["prove_peak_bytes"])/1024:.1f} KiB 和 {int(native_52_13["verify_peak_bytes"])/1024:.1f} KiB。')
    add_table(doc,['n','k','证明：中位/均值±sd/P95','验证：中位/均值±sd/P95','Proof','证明峰值'],[
        (str(n),str(k),timing_summary(native[(n,k)],'prove',native=True),timing_summary(native[(n,k)],'verify',native=True),f'{int(native[(n,k)]["proof_bytes"])/1000:.2f} KB',f'{int(native[(n,k)]["prove_peak_bytes"])/1024:.1f} KiB')
        for n,k in [(13,1),(26,13),(52,13),(52,26)]
    ],widths=[0.35,0.35,1.65,1.65,0.75,0.85])
    add_para(doc,f'组件计时把原生路径分解为 residual/setup、cross-key、Bayer–Groth、slot OR、序列化和对应验证阶段。n=52、k=13 时，证明阶段的中位数依次为 {ns_ms(component_52_13, "residual_setup_ns"):.1f}、{ns_ms(component_52_13, "cross_key_ns"):.1f}、{ns_ms(component_52_13, "bayer_groth_ns"):.1f}、{ns_ms(component_52_13, "slot_or_ns"):.1f} 和 {ns_ms(component_52_13, "serialization_ns"):.1f} ms；验证的 cross-key、Bayer–Groth、slot OR 分别为 {ns_ms(component_52_13, "verify_cross_key_ns"):.1f}、{ns_ms(component_52_13, "verify_bayer_groth_ns"):.1f} 和 {ns_ms(component_52_13, "verify_slot_or_ns"):.1f} ms。这是成本归因，不表示移除任一安全组件后协议仍然安全。')
    add_para(doc,f'同一 Rust 实现也通过 client-wasm 编译为 wasm32。桥接层先构造并重解码 BrowserReconstructionV3Bundle，再用生产 Poseidon transcript 验证。30 次 release Node/V8 测量中，n=52、k=13 的证明中位数/均值±样本标准差/P95 为 {timing_summary(wasm_52_13, "prove")}，验证为 {timing_summary(wasm_52_13, "verify")}；proof 为 {int(wasm_52_13["proof_bytes"])/1000:.2f} KB，完整 bundle 为 {int(wasm_52_13["bundle_bytes"])/1000:.2f} KB。英文稿另记录 Headless/headed Chrome、一次 macOS desktop Safari 实机页面基准，以及一次带 CDP JS-heap 采样的独立 Chrome 运行；Node/V8 数据仍不等价于这些浏览器页面结果。Android、iOS、浏览器进程 RSS、Safari/移动端峰值内存与互联网端到端延迟仍未测量。')
    add_table(doc,['n','k','WASM 证明','WASM 验证','Proof','Bundle'],[
        (str(n),str(k),timing_summary(wasm[(n,k)],'prove'),timing_summary(wasm[(n,k)],'verify'),f'{int(wasm[(n,k)]["proof_bytes"])/1000:.2f} KB',f'{int(wasm[(n,k)]["bundle_bytes"])/1000:.2f} KB')
        for n,k in [(13,1),(26,13),(52,13),(52,26)]
    ],widths=[0.35,0.35,1.65,1.65,0.85,0.85])
    add_para(doc,'英文稿另包含 30 次 warm service-worker loopback proof-upload 实验和 30 次唯一 scope/cache 的 cold-install 实验：前者 HTML/JavaScript/WASM 均由 service-worker cache 命中，proof upload 和结果提交绕过缓存并由服务器密码学验证；后者每次安装都从 server 拉取页面、worker、HTML、JavaScript 与 WASM。同一当前页面源码还分别记录 HTTP 与 TLS 各 30 次 cache-disabled upload；TLS 使用临时自签名 127.0.0.1 证书并让 Chrome 忽略证书错误，因此只代表本地 TLS loopback。上述实验不覆盖 service-worker 更新失效、浏览器 HTTP cache 复用、public PKI、LAN 或 Internet。')

    doc.add_heading('9 局限与未来工作', level=1)
    for s in ['恶意玩家不提交仍是应用层活性事件，需要 deadline、押金或替代策略。','认证 reveal-token 血统不可省略；缺少该条件时，非己牌否决定理不成立。','协议公开 deck size、owner-residual count、公钥、canonical cards、epoch 和 state digest。','本协议对 |U|≥2 的牌采取保留策略；若业务要求在无人知道明文时仍删除该牌，需要门限关系证明与不同授权策略。','组合定理只在会话绑定的 F_NIZK^R_RECON hybrid 中成立；当前累计 Poseidon Fiat–Shamir proof bytes 不被主张为并发 UC NIZK 的具体实现。','英文稿的浏览器计时数据包含自动 Chrome 与一次 macOS desktop Safari；Chrome 内存数据只覆盖采样到的 renderer JS heap，不覆盖浏览器进程 RSS、Safari 或移动端峰值内存，也不覆盖 Android、iOS、真实冷启动和互联网端到端延迟。','自适应腐化需要擦除或 non-committing 技术。']:
        doc.add_paragraph(s,style='List Bullet')

    doc.add_heading('10 结论', level=1)
    add_para(doc,'本文补足了协作式心智扑克中的活性缺口。Reveal-token 减法严格推出 residual carrier：单缺失 token 产生可由唯一 owner 解密的 carrier，多缺失 token 产生无人可单独解密的 jointly keyed carrier。前者通过跨密钥证明授权精确删除，后者不授权负贡献并在新 canonical deck 中被保留。因此在线玩家无需知道每张旧牌的明文，也能得到可继续洗牌的正确 ElGamal 牌组。')
    add_para(doc,'逐槽 OR 语义、隐藏映射、owner-residual 精确覆盖以及状态/transcript 绑定共同排除补偿攻击与非己牌否决。理想 NIZK 接口承载组合定理；具体 Rust 语义结论依赖各组件在各自 challenge checkpoint 的提取假设。Lean 的组合层将代数关系和组件/refinement 接口连接到同一个机器检查结论，但不声称当前 Fiat–Shamir 字节实现已经获得并发 UC 安全。')

    doc.add_heading('附录 A 与 dropout-tolerant mental poker 的关系', level=1)
    add_para(doc,'Castellà-Roca、Sebé 和 Domingo-Ferrer 的工作解决了无可信第三方条件下的玩家退出问题，并提出零知识方案使游戏在 dropout 后继续 [7]。该方案可作为活性方面的参考，但其 prover 侧授权并未像本文一样把每个删除绑定到认证的 owner-residual 血统，因此存在 prover 否决非自己手牌的可能。本文应将其视为相关先行工作，而不是本文非己牌否决定理的依据。区别在于：本文把 reveal-token transcript 推导出的 residual carrier 作为显式协议对象，并进一步规定 owner-residual 精确覆盖、hidden carrier-to-slot mapping、逐槽零或负元语义以及理想 NIZK hybrid/Lean 组合边界。')
    add_para(doc,'两项工作的目标互补。先行工作确立 TTP-free dropout tolerance 的可行性；本文解释 singleton 与 multi-key missing set 如何改变 carrier 的可解密性和授权语义，并通过认证血统排除 prover 对非己牌的未经授权否决。当前构造在 |U|≥2 时保留 canonical card 而不泄露它；若要删除 jointly unknown card，则需扩展为门限证明策略。')

    doc.add_heading('参考文献', level=1)
    refs=['R. Canetti. “Universally Composable Security: A New Paradigm for Cryptographic Protocols.” In IEEE FOCS, pp. 136–145, 2001. doi:10.1109/SFCS.2001.959888.','S. Bayer and J. Groth. “Efficient Zero-Knowledge Argument for Correctness of a Shuffle.” In EUROCRYPT, LNCS 7237, pp. 263–280, 2012. doi:10.1007/978-3-642-29011-4_17.','D. Chaum and T. P. Pedersen. “Wallet Databases with Observers.” In CRYPTO, LNCS 740, pp. 89–105, 1992. doi:10.1007/3-540-48071-4_7.','R. Cramer, I. Damgård, and B. Schoenmakers. “Proofs of Partial Knowledge and Simplified Design of Witness Hiding Protocols.” In CRYPTO, LNCS 839, pp. 174–187, 1994. doi:10.1007/3-540-48658-5_19.','A. Fiat and A. Shamir. “How To Prove Yourself: Practical Solutions to Identification and Signature Problems.” In CRYPTO, LNCS 263, pp. 186–194, 1986. doi:10.1007/3-540-47721-7_12.','C.-P. Schnorr. “Efficient Identification and Signatures for Smart Cards.” In CRYPTO, LNCS 435, pp. 239–252, 1989. doi:10.1007/0-387-34805-0_22.','J. Castellà-Roca, F. Sebé, and J. Domingo-Ferrer. “Dropout-Tolerant TTP-Free Mental Poker.” In Trust, Privacy, and Security in Digital Business, LNCS 3592, pp. 30–40, 2005. doi:10.1007/11537878_4.','J. Castellà-Roca. “Contributions to Mental Poker.” PhD thesis, Universitat Autònoma de Barcelona, 2005.','A. Barnett and N. P. Smart. “Mental Poker Revisited.” In Cryptography and Coding, LNCS 2898, pp. 370–383, 2003. doi:10.1007/978-3-540-40974-8_29.','K. Kurosawa, Y. Katayama, and W. Ogata. “Reshufflable and Laziness Tolerant Mental Card Game Protocol.” IEICE Transactions on Fundamentals, 1997.','W. H. Soo, A. Samsudin, and A. Goh. “Efficient Mental Card Shuffling via Optimised Arbitrary-Sized Benes Permutation Network.” In Information Security, LNCS 2433, pp. 446–458, 2002. doi:10.1007/3-540-45811-5_35.','I. Bentov, R. Kumaresan, and A. Miller. “Instantaneous Decentralized Poker.” In ASIACRYPT, LNCS 10625, pp. 410–440, 2017. doi:10.1007/978-3-319-70697-9_15.','B. David, R. Dowsley, and M. Larangeira. “Kaleidoscope: An Efficient Poker Protocol with Payment Distribution and Penalty Enforcement.” In Financial Cryptography and Data Security, LNCS 10958, pp. 500–519, 2018. doi:10.1007/978-3-662-58387-6_27.','B. David, R. Dowsley, and M. Larangeira. “ROYALE: A Framework for Universally Composable Card Games with Financial Rewards and Penalties Enforcement.” In Financial Cryptography and Data Security, LNCS 11598, pp. 282–300, 2019. doi:10.1007/978-3-030-32101-7_18.']
    add_references(doc, REFERENCES)
    props=doc.core_properties; props.title='面向心智扑克的认证隐私保护牌组重建'; props.subject='密码学研究论文中文译本'; props.author=author_block(metadata); props.keywords='心智扑克, 认证重建, 非交互零知识, 形式化验证'
    path=OUT/'composable_privacy_preserving_deck_reconstruction_zh.docx'; doc.save(path); print(path)

if __name__=='__main__':
    build()
    build_zh()
