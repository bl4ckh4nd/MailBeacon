import pytest
from app.core.patterns import generate_email_patterns, extract_emails_from_text
from app.core.domain_utils import normalize_domain, get_base_domain

def test_generate_email_patterns():
    patterns = generate_email_patterns("John", "Doe")
    expected_patterns = {
        "johndoe",
        "doejohn",
        "jdoe",
        "johnd",
        "jdoe",
        "johnd"
    }
    assert patterns.intersection(expected_patterns) == expected_patterns

def test_extract_emails():
    text = """
    Contact us at:
    john.doe@example.com
    support@company.com
    Invalid email: not.an.email
    Another valid: test+123@sub.domain.com
    """
    emails = extract_emails_from_text(text)
    assert len(emails) == 3
    assert "john.doe@example.com" in emails
    assert "support@company.com" in emails
    assert "test+123@sub.domain.com" in emails

def test_normalize_domain():
    cases = [
        ("http://example.com", "example.com"),
        ("https://sub.example.com/path", "sub.example.com"),
        ("example.com:8080", "example.com"),
        ("user:pass@example.com", "example.com"),
        ("EXAMPLE.COM", "example.com"),
    ]
    for input_domain, expected in cases:
        assert normalize_domain(input_domain) == expected

def test_get_base_domain():
    cases = [
        ("example.com", "example.com"),
        ("sub.example.com", "example.com"),
        ("deep.sub.example.com", "example.com"),
        ("example.co.uk", "example.co.uk"),  # Simplified approach
    ]
    for input_domain, expected in cases:
        assert get_base_domain(input_domain) == expected

def test_normalize_domain_invalid():
    with pytest.raises(ValueError):
        normalize_domain("")
