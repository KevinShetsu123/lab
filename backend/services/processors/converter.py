"""
Module for converting PDF pages to images with page number markers
and base64 encoding.
"""
import logging
import base64
from io import BytesIO
from typing import List
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from pdf2image import convert_from_bytes
import requests


logger = logging.getLogger(__name__)


class ImageConverter:
    """ _summary_ """
    def __init__(self, dpi: int = 300):
        """_summary_

        Args:
            file_url (str): _description_

        Returns:
            _type_: _description_
        """
        self.dpi = dpi

    def get_file_bytes(self, file_url: str):
        """_summary_

        Args:
            file_url (str): _description_

        Returns:
            _type_: _description_
        """

        response = requests.get(file_url, timeout=60)
        if response.status_code == 200:
            return response.content
        else:
            logger.info(
                "Failed to download file: %s",
                response.status_code
            )
            return None

    def images_converter(self, pdf_bytes, start_page, end_page):
        """_summary_

        Args:
            file_url (str): _description_
            start_page (int): _description_
            end_page (int): _description_

        Returns:
            _type_: _description_
        """

        images = convert_from_bytes(
            pdf_bytes,
            dpi=self.dpi,
            first_page=start_page,
            last_page=end_page
        )
        return images

    def page_number_marker(
        self,
        images: List[Image.Image],
        current_page: int,
    ) -> List[Image.Image]:
        """_summary_

        Args:
            file_url (str): _description_
            current_page (int): _description_

        Returns:
            _type_: _description_
        """

        marked_images = []
        margin_left, margin_bottom = 75, 75
        padding = 20
        for idx, img in enumerate(images):
            actual_page = current_page + idx
            _, height = img.size

            draw = ImageDraw.Draw(img)
            text_tag = f"PAGE: {actual_page}"
            try:
                font = ImageFont.truetype("arial.ttf", 80)
            except (OSError, IOError):
                font = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), text_tag, font=font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]

            rect_x0 = margin_left
            rect_y0 = height - margin_bottom - h - (padding * 2)
            rect_x1 = rect_x0 + w + (padding * 2)
            rect_y1 = height - margin_bottom

            draw.rectangle([rect_x0, rect_y0, rect_x1, rect_y1], fill="black")
            text_x = rect_x0 + padding
            text_y = rect_y0 + padding - bbox[1]
            draw.text((text_x, text_y), text_tag, fill="white", font=font)
            marked_images.append(img)

        return marked_images

    def image_enhance(self, images: List[Image.Image],) -> List[Image.Image]:
        """_summary_

        Args:
            file_url (str): _description_

        Returns:
            _type_: _description_
        """

        enhanced_images = []
        for img in images:
            img = img.convert("L")
            img = ImageEnhance.Contrast(img).enhance(1.8)
            enhanced_images.append(img)
        return enhanced_images

    def base64_encode(self, images: List[Image.Image]) -> List[str]:
        """_summary_

        Args:
            file_url (str): _description_

        Returns:
            _type_: _description_
        """

        base64_images = []
        for img in images:
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=85)
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            base64_images.append(img_str)
            buffered.close()

        return base64_images
