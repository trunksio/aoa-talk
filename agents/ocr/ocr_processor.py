"""
DeepSeek-OCR Processor Module

Handles OCR extraction from images and scanned PDFs using DeepSeek-OCR model.
Optimized for NVIDIA DGX Spark with GB10 GPU.
"""

import io
import logging
from pathlib import Path
from typing import List, Optional, Union, Tuple
from PIL import Image
import torch

logger = logging.getLogger(__name__)


class DeepSeekOCRProcessor:
    """
    DeepSeek-OCR processor for extracting text from images and scanned documents.

    Uses the deepseek-ai/deepseek-ocr model from Hugging Face.
    Optimized for NVIDIA DGX Spark (GB10 GPU with sm_121 compute capability).
    """

    def __init__(self, model_name: str = "deepseek-ai/deepseek-ocr", device: str = "auto"):
        """
        Initialize DeepSeek-OCR processor.

        Args:
            model_name: Hugging Face model identifier
            device: Device to use ('auto', 'cuda', 'cpu')
        """
        self.model_name = model_name
        self.model = None
        self.processor = None

        # Determine device
        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        logger.info(
            f"Initializing DeepSeek-OCR processor: model={model_name}, device={self.device}, cuda_available={torch.cuda.is_available()}"
        )

        # Lazy loading - only load model when first needed
        # This avoids issues with RQ worker forking
        self._model_loaded = False

    def _load_model(self):
        """Lazy load the model and processor."""
        if self._model_loaded:
            return

        try:
            from transformers import AutoModel, AutoProcessor

            logger.info(f"Loading DeepSeek-OCR model from {self.model_name}")

            # Load processor (tokenizer + image processor)
            self.processor = AutoProcessor.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )

            # Load model
            self.model = AutoModel.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            )

            # Move to device
            self.model = self.model.to(self.device)
            self.model.eval()

            self._model_loaded = True

            logger.info(
                f"DeepSeek-OCR model loaded successfully: device={self.device}, dtype={self.model.dtype}"
            )

        except Exception as e:
            logger.error(f"Failed to load DeepSeek-OCR model: {e}")
            raise

    def process_image(
        self,
        image: Union[str, Path, Image.Image],
        prompt_mode: str = "free_ocr"
    ) -> str:
        """
        Extract text from a single image using DeepSeek-OCR.

        Args:
            image: Path to image file or PIL Image object
            prompt_mode: OCR mode - 'free_ocr' (fastest), 'markdown' (structured),
                        'grounding' (with coordinates)

        Returns:
            Extracted text from the image
        """
        self._load_model()

        try:
            # Load image if path provided
            if isinstance(image, (str, Path)):
                img = Image.open(image).convert("RGB")
            else:
                img = image.convert("RGB")

            # Prepare prompt based on mode
            prompts = {
                "free_ocr": "<image>\nOCR this image.",
                "markdown": "<image>\nConvert this document to markdown format.",
                "grounding": "<image>\n<|grounding|>OCR this image.",
            }

            prompt = prompts.get(prompt_mode, prompts["free_ocr"])

            logger.debug(
                f"Processing image with DeepSeek-OCR: mode={prompt_mode}, image_size={img.size}"
            )

            # Prepare inputs
            inputs = self.processor(
                text=prompt,
                images=img,
                return_tensors="pt"
            ).to(self.device)

            # Generate OCR output
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=4096,
                    do_sample=False,
                    temperature=0.0,
                )

            # Decode output
            text = self.processor.batch_decode(
                outputs,
                skip_special_tokens=True
            )[0]

            # Remove the prompt from the output
            if prompt in text:
                text = text.replace(prompt, "").strip()

            logger.debug(
                f"Image processed successfully: output_length={len(text)}, mode={prompt_mode}"
            )

            return text

        except Exception as e:
            logger.error(f"Failed to process image: {e}")
            raise

    def process_pdf(
        self,
        pdf_path: Union[str, Path],
        prompt_mode: str = "free_ocr",
        max_pages: Optional[int] = None
    ) -> Tuple[str, int]:
        """
        Extract text from a PDF file by converting to images and running OCR.

        Args:
            pdf_path: Path to PDF file
            prompt_mode: OCR mode (see process_image)
            max_pages: Maximum number of pages to process (None = all)

        Returns:
            Tuple of (combined_text, num_pages_processed)
        """
        self._load_model()

        try:
            import pypdfium2 as pdfium

            logger.info(f"Processing PDF with OCR: {pdf_path}")

            # Open PDF
            pdf = pdfium.PdfDocument(str(pdf_path))
            num_pages = len(pdf)

            if max_pages:
                num_pages = min(num_pages, max_pages)

            logger.info(f"PDF has {len(pdf)} pages, processing {num_pages}")

            # Process each page
            all_text = []

            for page_num in range(num_pages):
                logger.debug(f"Processing page {page_num + 1}/{num_pages}")

                # Render page to image
                page = pdf[page_num]
                bitmap = page.render(scale=2.0)  # 2x scale for better OCR quality
                pil_image = bitmap.to_pil()

                # Run OCR on page
                page_text = self.process_image(pil_image, prompt_mode=prompt_mode)

                # Add page separator
                all_text.append(f"\n--- Page {page_num + 1} ---\n")
                all_text.append(page_text)

            # Combine all pages
            combined_text = "\n".join(all_text)

            logger.info(
                f"PDF processing completed: pages_processed={num_pages}, total_chars={len(combined_text)}"
            )

            return combined_text, num_pages

        except Exception as e:
            logger.error(f"Failed to process PDF: {e}")
            raise

    def process_pdf_fallback(
        self,
        pdf_path: Union[str, Path],
        prompt_mode: str = "free_ocr"
    ) -> Tuple[str, int]:
        """
        Fallback PDF processing using pdf2image.

        Args:
            pdf_path: Path to PDF file
            prompt_mode: OCR mode (see process_image)

        Returns:
            Tuple of (combined_text, num_pages_processed)
        """
        self._load_model()

        try:
            from pdf2image import convert_from_path

            logger.info(f"Processing PDF with OCR (pdf2image fallback): {pdf_path}")

            # Convert PDF to images
            images = convert_from_path(str(pdf_path))
            num_pages = len(images)

            logger.info(f"Converted PDF to {num_pages} images")

            # Process each page
            all_text = []

            for page_num, image in enumerate(images):
                logger.debug(f"Processing page {page_num + 1}/{num_pages}")

                # Run OCR on page
                page_text = self.process_image(image, prompt_mode=prompt_mode)

                # Add page separator
                all_text.append(f"\n--- Page {page_num + 1} ---\n")
                all_text.append(page_text)

            # Combine all pages
            combined_text = "\n".join(all_text)

            logger.info(
                f"PDF processing completed (fallback): pages_processed={num_pages}, total_chars={len(combined_text)}"
            )

            return combined_text, num_pages

        except Exception as e:
            logger.error(f"Failed to process PDF (fallback): {e}")
            raise

    def get_model_info(self) -> dict:
        """Get information about the loaded model."""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "model_loaded": self._model_loaded,
            "cuda_available": torch.cuda.is_available(),
            "cuda_device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
            "cuda_device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        }
