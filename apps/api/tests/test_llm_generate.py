"""Facade routing for generate_json (mocked providers — no network)."""

from unittest.mock import patch

from app.llm import generate as generate_mod


def test_generate_json_routes_to_ollama_by_default(monkeypatch):
    monkeypatch.setattr(generate_mod.settings, "llm_provider", "ollama")
    with patch("app.llm.generate.ollama_generate_json", return_value={"ok": True}) as m:
        assert generate_mod.generate_json("hi") == {"ok": True}
        m.assert_called_once()


def test_generate_json_routes_to_cloud(monkeypatch):
    monkeypatch.setattr(generate_mod.settings, "llm_provider", "cloud")
    with patch("app.llm.generate.cloud_generate_json", return_value={"ok": True}) as m:
        assert generate_mod.generate_json("hi") == {"ok": True}
        m.assert_called_once()


def test_provider_override_wins(monkeypatch):
    monkeypatch.setattr(generate_mod.settings, "llm_provider", "ollama")
    with patch("app.llm.generate.cloud_generate_json", return_value={"c": 1}) as m:
        assert generate_mod.generate_json("hi", provider="cloud") == {"c": 1}
        m.assert_called_once()
