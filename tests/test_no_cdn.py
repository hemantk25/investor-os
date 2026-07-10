from pathlib import Path


def test_templates_do_not_load_external_scripts_or_cdns():
    forbidden = ("<script src=\"http", "<script src='http", "cdn.jsdelivr", "unpkg.com",
                 "cdnjs.cloudflare")
    for path in Path("app/templates").glob("*.html"):
        text = path.read_text(encoding="utf-8").lower()
        assert not any(token in text for token in forbidden), path
