"""Tests for the ContentClassifier: text classification."""

from __future__ import annotations

import pytest

from src.moderation.classifier import ContentClassification, ContentClassifier


@pytest.fixture
def classifier():
    return ContentClassifier(toxicity_threshold=0.8, nsfw_threshold=0.9)


def test_classify_text_safe(classifier):
    result = classifier.classify_text("This is a perfectly normal and safe post about cooking.")
    assert isinstance(result, ContentClassification)
    assert result.nsfw_score == 0.0
    assert result.toxicity_score == 0.0
    assert result.violence_score == 0.0
    assert result.confidence == 0.0
    assert len(result.labels) == 0


def test_classify_text_nsfw(classifier):
    result = classifier.classify_text(
        "This contains explicit nudity and pornographic adult content with sexually explicit material"
    )
    assert result.nsfw_score > 0
    assert "NSFW" in result.labels


def test_classify_text_toxic(classifier):
    result = classifier.classify_text(
        "You are an idiot and a stupid moron, what a loser, absolutely disgusting and pathetic"
    )
    assert result.toxicity_score > 0
    assert "TOXICITY" in result.labels


def test_classify_text_violence(classifier):
    result = classifier.classify_text(
        "The kill threat involved murder and assault with a weapon bomb attack"
    )
    assert result.violence_score > 0
    assert "VIOLENCE" in result.labels


def test_classify_text_spam(classifier):
    result = classifier.classify_text(
        "Buy now free money click here limited offer act now congratulations you won"
    )
    assert result.spam_score > 0
    assert "SPAM" in result.labels


def test_classify_text_mixed(classifier):
    result = classifier.classify_text(
        "This stupid idiot posted explicit nudity with a kill threat and buy now spam"
    )
    assert len(result.labels) >= 2
    assert result.confidence > 0


def test_classify_text_empty(classifier):
    result = classifier.classify_text("")
    assert result.nsfw_score == 0.0
    assert result.toxicity_score == 0.0
    assert len(result.labels) == 0


def test_classify_text_metadata(classifier):
    result = classifier.classify_text("Hello world")
    assert "word_count" in result.metadata
    assert "text_length" in result.metadata
    assert result.metadata["text_length"] == len("Hello world")


def test_classification_scores_range(classifier):
    result = classifier.classify_text(
        "Kill murder assault bomb weapon stupid idiot hate pornographic nude"
    )
    for score in [result.nsfw_score, result.toxicity_score, result.violence_score, result.spam_score]:
        assert 0.0 <= score <= 1.0


def test_classify_image_small_file(classifier):
    result = classifier.classify_image(b"\x00" * 1000, filename="photo.jpg")
    assert result.nsfw_score == 0.1


def test_classify_image_large_file(classifier):
    result = classifier.classify_image(b"\x00" * 6_000_000, filename="photo.jpg")
    assert result.nsfw_score == 0.85
