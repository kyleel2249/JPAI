"""Tests for bounded and safe web intelligence collection."""
import socket
import pytest
from jpai_api.research.crawler import CrawlPolicyError,CrawlerStore,PageExtractor,validate_public_url

def test_private_destination_rejected(monkeypatch):
    monkeypatch.setattr(socket,"getaddrinfo",lambda *a,**k:[(None,None,None,None,("127.0.0.1",0))])
    with pytest.raises(CrawlPolicyError): validate_public_url("http://example.test")
def test_public_url_normalized(monkeypatch):
    monkeypatch.setattr(socket,"getaddrinfo",lambda *a,**k:[(None,None,None,None,("93.184.216.34",0))])
    assert validate_public_url("https://example.com/path#section")=="https://example.com/path"
def test_credentials_and_non_http_rejected():
    with pytest.raises(CrawlPolicyError): validate_public_url("file:///etc/passwd")
    with pytest.raises(CrawlPolicyError): validate_public_url("https://user:pass@example.com")
def test_html_extraction():
    parser=PageExtractor()
    parser.feed('<title>Example</title><meta name="description" content="A test"><h1>Welcome</h1><p>Useful content</p><a href="/next">Next</a><script>secret()</script>')
    assert "Example" in parser.title_parts and "Useful content" in parser.text_parts
    assert "/next" in parser.links and parser.meta["description"]=="A test"
    assert "secret()" not in parser.text_parts
def test_persistence_and_search(tmp_path):
    store=CrawlerStore(str(tmp_path/"web.sqlite3")); job=store.create_job("https://example.com",5)
    parser=PageExtractor(); parser.feed("<title>Market research</title><p>Economic intelligence report</p>")
    store.save_page(job["id"],"https://example.com/report","example.com",parser,200,"text/html","abc123")
    store.update_job(job["id"],"completed",1)
    assert store.get_job(job["id"])["pages_crawled"]==1
    assert store.search_pages("economic report")[0]["title"]=="Market research"
    assert store.stats()["pages_stored"]==1
