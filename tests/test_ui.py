import pathlib

from streamlit.testing.v1 import AppTest

from src.config.loader import load_config

APP = pathlib.Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"


def test_app_renders_brand_examples_and_tabs():
    cfg = load_config()
    at = AppTest.from_file(APP).run(timeout=30)

    assert not at.exception
    assert cfg.ui.title == "Dhairya-IQ"
    assert len(at.sidebar.button) == 11
    assert any(
        cfg.ui.example_questions[0] in button.label for button in at.button
    )
    assert len(at.tabs) == 0
    assert at.chat_input[0].placeholder.startswith(
        "Ask facts about HDFC schemes"
    )
