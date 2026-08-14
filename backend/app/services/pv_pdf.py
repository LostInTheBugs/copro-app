"""Génération du procès-verbal d'AG en PDF (reportlab)."""
import os
from io import BytesIO
from datetime import date

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.services.country_rules import calculer_statut_resolution, MAJORITES
from app.services.emailer import _date_fr

_FONTS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")

_fonts_registered = False


def _register_fonts():
    global _fonts_registered
    if _fonts_registered:
        return
    pdfmetrics.registerFont(TTFont("DejaVu", os.path.join(_FONTS_DIR, "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", os.path.join(_FONTS_DIR, "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVu-Oblique", os.path.join(_FONTS_DIR, "DejaVuSans-Oblique.ttf")))
    _fonts_registered = True


_STYLES = {}


def _style(name, **kw):
    if name not in _STYLES:
        _STYLES[name] = ParagraphStyle(name, fontName="DejaVu", fontSize=10, leading=14)
    s = _STYLES[name]
    for k, v in kw.items():
        setattr(s, k, v)
    return s


_TYPE_LABEL = {
    "annuelle": "Assemblée Générale annuelle",
    "extraordinaire": "Assemblée Générale extraordinaire",
    "consultation_ecrite": "Consultation écrite",
}

_VOIX_LABEL = {"pour": "Pour", "contre": "Contre", "abstention": "Abstention"}


def generer_pv_pdf(copro, ag, db) -> BytesIO:
    """Génère le PV de l'AG au format PDF (retourne un BytesIO)."""
    _register_fonts()
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title=f"PV AG {copro.nom} {ag.date}",
    )

    # NB : import local pour éviter un cycle d'imports
    from app.models.lot import Lot
    lots = db.query(Lot).filter(Lot.copropriete_id == copro.id).all()
    total = sum(l.tantiemes for l in lots) or 1

    el = []
    el.append(Paragraph("PROCÈS-VERBAL D'ASSEMBLÉE GÉNÉRALE", _style("titre", fontName="DejaVu-Bold", fontSize=15, leading=20, alignment=TA_CENTER, spaceAfter=4)))
    el.append(Paragraph(_TYPE_LABEL.get(ag.type_ag, "Assemblée Générale"), _style("st", alignment=TA_CENTER, fontSize=11, textColor=colors.HexColor("#444444"), spaceAfter=12)))

    # En-tête copropriété
    el.append(Paragraph(f"<b>Copropriété :</b> {copro.nom}", _style("hdr", fontSize=10.5)))
    if copro.adresse:
        el.append(Paragraph(f"{copro.adresse} {copro.code_postal or ''} {copro.ville or ''}".strip(), _style("hdr")))
    el.append(Spacer(1, 6))

    # Informations de séance
    infos = [
        ("Type de séance", _TYPE_LABEL.get(ag.type_ag, "AG")),
        ("Date", _date_fr(ag.date) + (f" à {ag.heure}" if ag.heure else "")),
        ("Lieu", ag.lieu or "—"),
        ("Statut", {"projet": "Projet", "convoquee": "Convoquée", "terminee": "Terminée"}.get(ag.statut, ag.statut)),
    ]
    t = Table([[Paragraph(f"<b>{k}</b>", _style("cell", fontSize=9.5)), Paragraph(str(v), _style("cell", fontSize=9.5))] for k, v in infos],
              colWidths=[38 * mm, 130 * mm])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    el.append(t)
    el.append(Spacer(1, 8))

    # Ordre du jour
    resolutions = sorted(ag.resolutions, key=lambda x: x.numero)
    if resolutions:
        el.append(Paragraph("ORDRE DU JOUR", _style("sec", fontName="DejaVu-Bold", fontSize=11, spaceBefore=4, spaceAfter=4)))
        for r in resolutions:
            el.append(Paragraph(f"{r.numero}. {r.libelle}", _style("odj", fontSize=9.8, spaceAfter=2)))
        el.append(Spacer(1, 6))

    el.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#94a3b8"), spaceAfter=10))

    # Résolutions détaillées
    el.append(Paragraph("RÉSOLUTIONS ET VOTES", _style("sec", fontName="DejaVu-Bold", fontSize=11, spaceAfter=6)))
    for r in resolutions:
        el.append(Paragraph(
            f"Résolution {r.numero} — {r.libelle}",
            _style("res_t", fontName="DejaVu-Bold", fontSize=10.5, spaceBefore=6, spaceAfter=2),
        ))
        if r.texte:
            el.append(Paragraph(r.texte, _style("res_texte", fontSize=9.5, textColor=colors.HexColor("#444444"), spaceAfter=2)))
        resultat = calculer_statut_resolution(r, lots, r.votes)
        maj_label = MAJORITES.get(r.majorite, {}).get("label", r.majorite)
        el.append(Paragraph(
            f"<b>Majorité requise :</b> {maj_label}",
            _style("maj", fontSize=9.5, spaceAfter=3),
        ))

        # Tableau des votes par lot
        rows = [[Paragraph("<b>Lot</b>", _style("th", fontSize=9)), Paragraph("<b>Millièmes</b>", _style("th", fontSize=9)), Paragraph("<b>Voix</b>", _style("th", fontSize=9))]]
        for lot in lots:
            v = next((x for x in r.votes if x.lot_id == lot.id), None)
            voix = _VOIX_LABEL.get(v.voix if v else "", "—")
            if v and v.voix == "pour":
                voix = f"<font color='#059669'><b>Pour</b></font>"
            elif v and v.voix == "contre":
                voix = f"<font color='#dc2626'><b>Contre</b></font>"
            elif v and v.voix == "abstention":
                voix = "Abstention"
            rows.append([
                Paragraph(f"Lot {lot.numero}", _style("cell", fontSize=9)),
                Paragraph(str(lot.tantiemes), _style("cell", fontSize=9)),
                Paragraph(voix, _style("cell", fontSize=9)),
            ])
        vt = Table(rows, colWidths=[50 * mm, 35 * mm, 83 * mm])
        vt.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        el.append(vt)
        el.append(Spacer(1, 4))

        # Résultat
        statut_txt = {
            "adoptee": ("ADOPTÉE", "#059669"),
            "rejetee": ("REJETÉE", "#dc2626"),
            "a_voter": ("À VOTER", "#d97706"),
        }.get(resultat["statut"], (resultat["statut"], "#444444"))
        el.append(Paragraph(
            f"Pour : <b>{resultat['pour']}‰</b>  ·  Contre : <b>{resultat['contre']}‰</b>  ·  "
            f"Abstention : <b>{resultat['abstention']}‰</b>",
            _style("resultat", fontSize=9.5, spaceBefore=2),
        ))
        el.append(Paragraph(
            f"<b><font color='{statut_txt[1]}'>{statut_txt[0]}</font></b> — {resultat['detail']}",
            _style("detail", fontSize=9, textColor=colors.HexColor("#333333"), spaceAfter=8),
        ))

    el.append(Spacer(1, 14))
    el.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#94a3b8"), spaceAfter=8))
    ville = copro.ville or ""
    el.append(Paragraph(f"Fait à {ville}, le {_date_fr(date.today())}", _style("sign", fontSize=9.5, spaceAfter=24)))
    el.append(Paragraph("Le syndic bénévole", _style("sign", fontSize=9.5, spaceAfter=2)))
    el.append(Paragraph("<b>________________________</b>", _style("sign", fontSize=10)))
    el.append(Spacer(1, 10))
    el.append(Paragraph(
        "Conformément à l'article 17 du décret n°67-223 du 17 mars 1967, le présent procès-verbal "
        "est notifié à chaque copropriétaire dans un délai de deux mois à compter de la tenue de l'assemblée.",
        _style("legal", fontSize=7.8, textColor=colors.HexColor("#666666"), alignment=TA_JUSTIFY),
    ))

    doc.build(el)
    buf.seek(0)
    return buf
