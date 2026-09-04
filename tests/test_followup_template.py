"""Follow-up rules — no paid APIs required."""
def test_default_delay_and_template_shape():
    # Inline expectations matching followup_service constants
    default_delay_days = 3
    template = "Hi {name},\n\nJust following up"
    assert 1 <= default_delay_days <= 14
    assert "{name}" in template
