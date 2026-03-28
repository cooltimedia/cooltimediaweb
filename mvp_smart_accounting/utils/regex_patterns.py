TAX_ID_PATTERN = r"(?P<tax_id>\d{1,4}-\d{1,4}-\d{1,6})"
VERIFICATION_DIGIT_PATTERN = r"(DV|dv)\s*[:\-]?\s*(?P<verification_digit>\d{1,2})"
COMPANY_NAME_PATTERN = r"(company|empresa|raz[oó]n social)\s*[:\-]?\s*(?P<company_name>.+)"