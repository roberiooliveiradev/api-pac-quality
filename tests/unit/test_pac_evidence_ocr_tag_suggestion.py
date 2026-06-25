from app.domain.services.quality_intelligence.pac_evidence_ocr_tag_suggestion_service import (
    PacEvidenceOcrTagSuggestionService,
)


def test_suggest_tags_from_ocr_text():
    result = PacEvidenceOcrTagSuggestionService.suggest(
        ocr_text="Foto da NC com oxidação em parafusos do produto 90110001",
        file_name="nc_parafuso.jpg",
    )

    assert "oxidação" in result["suggested_symptom_tags"]
    assert "90110001" in result["suggested_product_codes"]
    assert result["suggested_failure_modes"]


def test_suggest_tags_from_filename_when_no_ocr():
    result = PacEvidenceOcrTagSuggestionService.suggest(
        file_name="evidencia_trinca_chicote.png",
        description="detalhe da trinca superficial",
    )

    assert "trinca" in result["suggested_symptom_tags"]


def test_suggest_tags_empty_corpus():
    result = PacEvidenceOcrTagSuggestionService.suggest()

    assert result["suggested_symptom_tags"] == []
    assert result["suggested_product_codes"] == []
