"""
QR code service.

This service generates QR codes as base64 data URIs so they can be
embedded directly into templates without requiring separate media files.
"""

import base64
from io import BytesIO


class QRCodeService:
    """
    Service for generating QR code images as embeddable data URIs.
    """

    @classmethod
    def build_data_uri(cls, value: str) -> str:
        """
        Generates a PNG QR code and returns it as a data URI.

        Args:
            value (str): The string that should be encoded in the QR code.

        Returns:
            str: A base64 data URI ready for use in an <img> tag.

        Raises:
            ValueError: If the value is empty.
        """
        normalized_value = cls._normalize_value(value=value)

        try:
            import qrcode
        except ImportError as exc:
            raise ImportError(
                "qrcode library is required. Install it with: pip install qrcode[pil]"
            ) from exc

        qr = qrcode.QRCode(
            version=3,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(normalized_value)
        qr.make(fit=True)

        image = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        image.save(buffer, format="PNG")
        encoded_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return f"data:image/png;base64,{encoded_image}"

    @staticmethod
    def _normalize_value(value: str) -> str:
        """
        Validates and normalizes the input string.

        Args:
            value (str): Raw input value.

        Returns:
            str: Normalized value.

        Raises:
            ValueError: If the value is empty.
        """
        if value is None:
            raise ValueError("QR value is required.")

        normalized = value.strip()

        if not normalized:
            raise ValueError("QR value is required.")

        return normalized