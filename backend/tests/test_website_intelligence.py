from types import SimpleNamespace

from app.services.website_intelligence import analyze_website_sync


def test_website_intelligence_extracts_business_signals(monkeypatch):
    html = '''
    <html><head>
      <title>Acme Dental Clinic</title>
      <meta name="description" content="Dental care and appointments in town">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <link rel="canonical" href="https://acme.example/">
    </head><body>
      <h1>Acme Dental Clinic</h1>
      <a href="/contact">Contact us</a>
      <a href="https://calendly.com/acme/consult">Book appointment</a>
      <a href="https://instagram.com/acme">Instagram</a>
      <a href="mailto:hello@acme.example">hello@acme.example</a>
      <a href="tel:+123456789">Call</a>
      <img src="hero.jpg" alt="Clinic reception">
      <script src="https://www.googletagmanager.com/gtag.js"></script>
    </body></html>
    '''

    monkeypatch.setattr(
        "app.services.website_intelligence.get_settings",
        lambda: SimpleNamespace(WEBSITE_FETCH_MAX_BYTES=100000, WEBSITE_FETCH_TIMEOUT_SECONDS=5),
    )
    monkeypatch.setattr(
        "app.services.website_intelligence.safe_fetch",
        lambda *args, **kwargs: SimpleNamespace(
            status_code=200, url="https://acme.example/", text=html
        ),
    )

    result = analyze_website_sync("https://acme.example/")
    findings = result["raw_findings"]

    assert result["http_status"] == 200
    assert result["has_ssl"] is True
    assert result["has_viewport"] is True
    assert result["booking_vendor_detected"] == "calendly"
    assert findings["title"] == "Acme Dental Clinic"
    assert findings["meta_description"]
    assert findings["h1_count"] == 1
    assert findings["has_cta"] is True
    assert "hello@acme.example" in findings["emails"]
    assert "+123456789" in findings["phone_links"]
    assert findings["social_presence_count"] == 1
    assert "google_analytics" in findings["analytics"]
    assert findings["quality_score"] == 100


def test_website_intelligence_marks_missing_conversion_and_mobile_signals(monkeypatch):
    html = "<html><head><title>Untitled</title></head><body><p>Welcome</p></body></html>"
    monkeypatch.setattr(
        "app.services.website_intelligence.get_settings",
        lambda: SimpleNamespace(WEBSITE_FETCH_MAX_BYTES=100000, WEBSITE_FETCH_TIMEOUT_SECONDS=5),
    )
    monkeypatch.setattr(
        "app.services.website_intelligence.safe_fetch",
        lambda *args, **kwargs: SimpleNamespace(
            status_code=200, url="http://example.test/", text=html
        ),
    )

    result = analyze_website_sync("http://example.test/")
    findings = result["raw_findings"]

    assert result["has_ssl"] is False
    assert result["has_viewport"] is False
    assert findings["has_cta"] is False
    assert findings["seo"]["missing_description"] is True
    assert findings["quality_score"] < 100
    assert "no_https" in findings["weak_reasons"]
    assert "no_cta" in findings["weak_reasons"]
