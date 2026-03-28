"""
Advanced Tax Information Extraction Service for Panama.
Fully integrated with models.py fields and dynamic confidence scoring.
"""

from datetime import datetime
import re

class TaxInformationExtractionService:
    def extract_fields(self, extracted_text: str) -> dict:
        # Text normalization while maintaining line structure
        text = "\n".join([line.strip() for line in extracted_text.split('\n') if line.strip()])

        raw_date = self._find_value([r"Fecha de Emisión:\s*([\d/]+)"], text)
        parsed_date = None
        if raw_date:
            try:
                # Format DD/MM/YYYY
                parsed_date = datetime.strptime(raw_date, "%d/%m/%Y")
            except ValueError:
                parsed_date = None

        data = {
            # --- General Information ---
            "document_number": self._find_value([r"Número:\s*(\d+)"], text),
            "cufe": self._find_value([r"CUFE:\s*([A-Z0-9]+)"], text),
            "issue_date": parsed_date,
            
            # --- Issuer ---
            "issuer_name": self._find_value([r"Emisor:\s*([A-Z0-9 ]+)"], text),
            "issuer_ruc": self._find_value([r"RUC:\s*([\d-]+)"], text),
            "issuer_dv": self._find_value([r"DV:\s*(\d+)"], text),
            
            # --- Receiver ---
            "receiver_name": self._find_value([r"Cliente:\s*([A-Z0-9 ]+)"], text),
            "receiver_type": self._find_value([r"Tipo de Receptor:\s*([A-Z0-9 ]+)"], text),
            "receiver_ruc": self._find_value([r"RUC/Cédula/Pasaporte:\s*([\d-]+)"], text),
            "receiver_dv": self._find_value([r"DV:\s*(\d+)"], text, search_after="Cliente"),

            # --- Totals ---
            "subtotal": self._extract_amount([r"Total Neto"], text),
            "tax_amount": self._extract_specific_itbms(text),
            "discount": self._extract_amount([r"Descuento Unitario"], text),
            "total_paid": self._extract_specific_total(text),
            
            "extraction_provider": "DGI-Panama-Official-v1",
        }

        data["extraction_confidence"] = self._calculate_confidence(data)
        return data

    def _find_value(self, patterns, text, search_after=None):
        work_text = text
        if search_after and search_after in text:
            work_text = text.split(search_after)[1]

        for p in patterns:
            match = re.search(p, work_text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""

    def _extract_amount(self, keywords, text):
        for key in keywords:
            pattern = key + r".*?(\d+[\.,]\d{2})"
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).replace(',', '')
        return "0.00"

    def _extract_specific_itbms(self, text):
        """
        Specifically search for the 'ITBMS' line
        avoiding 'ITBMS Taxable Amount'.
        """
        lines = text.split('\n')
        for line in lines:
            if "ITBMS" in line and "Gravado" not in line and "Exento" not in line:
                match = re.search(r"ITBMS\s+([\d,]+\.\d{2})", line, re.IGNORECASE)
                if match:
                    return match.group(1).replace(',', '')
        return "0.00"

    def _extract_specific_total(self, text):
        """
        Specifically search for the 'TOTAL' line.
        """
        lines = text.split('\n')
        for line in lines:
            if "Total" in line and "pagar" not in line and "PAGADO" not in line:
                match = re.search(r"Total\s+([\d,]+\.\d{2})", line, re.IGNORECASE)
                if match:
                    return match.group(1).replace(',', '')
        return "0.00"

    def _calculate_confidence(self, data):
        score = 0.0
        try:
            sub = float(data.get("subtotal", 0))
            tax = float(data.get("tax_amount", 0))
            total = float(data.get("total_paid", 0))
            if abs((sub + tax) - total) < 0.01 and total > 0:
                score = 1.0 
            else:
                score = 0.5
        except:
            score = 0.1
        return score