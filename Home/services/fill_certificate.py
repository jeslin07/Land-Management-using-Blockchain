import os
import qrcode
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from django.conf import settings


TEMPLATE = os.path.join(settings.MEDIA_ROOT, "landecertififcate1.pdf")


def generate_certificate(tx):
    output_path = os.path.join(settings.MEDIA_ROOT, f"cert_{tx.id}.pdf")

    data = {
        "certificate_no": f"CERT-{tx.id}",
        "date": tx.submission_date.strftime("%d-%m-%Y"),
        "local_body": tx.office.name if tx.office else "",

        "name": tx.customer.user.get_full_name(),
        "survey": tx.survey_number,
        "plot": tx.party_id,
        "village":  tx.office.name if tx.office else "",
        "district": tx.office.district if tx.office else "",
        "area": str(tx.valuation),
        "land_type": tx.deed_type,

        "verify_url": f"http://localhost:8000/verify/{tx.id}",
    }

    # QR
    qr_file = os.path.join(settings.MEDIA_ROOT, f"qr_{tx.id}.png")
    qrcode.make(data["verify_url"]).save(qr_file)
    data["qr_file"] = qr_file

    # overlay
    overlay = os.path.join(settings.MEDIA_ROOT, f"overlay_{tx.id}.pdf")
    c = canvas.Canvas(overlay, pagesize=letter)

    c.setFont("Helvetica-Bold", 10)
    c.drawString(250, 712, data["local_body"])

    c.setFont("Helvetica", 10)
    c.drawString(135, 643, data["certificate_no"])
    c.drawString(435, 644, data["date"])

    c.setFont("Helvetica-Bold", 14)
    c.drawString(255, 570, data["name"])

    c.setFont("Helvetica", 12)
    c.drawString(122, 481, data["survey"])
    c.drawString(355, 481, data["plot"])
    c.drawString(135, 438, data["village"])
    c.drawString(355, 438, data["district"])
    c.drawString(133, 394, data["area"])
    c.drawString(370, 394, data["land_type"])

    c.drawImage(qr_file, 426, 180, width=60, height=60)
    c.save()

    # merge
    base = PdfReader(TEMPLATE)
    overlay_pdf = PdfReader(overlay)

    writer = PdfWriter()
    page = base.pages[0]
    page.merge_page(overlay_pdf.pages[0])
    writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)

    tx.certificate_file = f"cert_{tx.id}.pdf"
    tx.save()

    return output_path
