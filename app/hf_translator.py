from transformers import MarianMTModel, MarianTokenizer, AutoModelForSeq2SeqLM, AutoTokenizer, AutoModelForCausalLM
import torch
from loguru import logger

from app import TRANSLATION_OVERRIDES
from app.translator import BaseTranslator


class HuggingFaceTranslator(BaseTranslator):
    def __init__(self, source, target_langs, dry_run: bool) -> None:
        super().__init__(source, target_langs, dry_run)
        # Preload MarianMT models for Kinyarwanda and Swahili
        self.models = {
            "rw": {
                "tokenizer": MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-en-rw"),
                "model": MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-en-rw"),
            },
            "sw": {

                # "tokenizer": MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-en-sw"),
                # "model": MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-en-sw"),
                # "tokenizer": AutoTokenizer.from_pretrained("Bildad/English-Swahili_Translation"),
                # "model": AutoModelForSeq2SeqLM.from_pretrained("Bildad/English-Swahili_Translation")
                # "tokenizer": AutoTokenizer.from_pretrained("CraneAILabs/swahili-gemma-1b"),
                # "model": AutoModelForCausalLM.from_pretrained("CraneAILabs/swahili-gemma-1b")
                # "tokenizer": AutoTokenizer.from_pretrained("Chituyi/opus-mt-english-swahili-finetuned-en-to-sw"),
                # "model": AutoModelForSeq2SeqLM.from_pretrained("Chituyi/opus-mt-english-swahili-finetuned-en-to-sw")
                "tokenizer": AutoTokenizer.from_pretrained("masakhane/afri-mt5-base"),
                "model": AutoModelForSeq2SeqLM.from_pretrained("masakhane/afri-mt5-base")
            },
        }

    def _call_model(self, text: str, target_code: str) -> str:
        try:
            tokenizer = self.models[target_code]["tokenizer"]
            model = self.models[target_code]["model"]

            inputs = tokenizer([text], return_tensors="pt", padding=True)
            outputs = model.generate(**inputs, max_length=200)
            translation = tokenizer.decode(outputs[0], skip_special_tokens=True)

            logger.debug(f"  → {translation!r}")
            return translation
        except Exception as e:
            logger.exception(f"HuggingFace error [{target_code}] on {text!r}: {e}")
            return ""

