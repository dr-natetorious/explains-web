import os
import tempfile
import shutil
import pytest
from prompts import Prompts
from pathlib import Path

def create_temp_prompt_dir():
    temp_dir = tempfile.mkdtemp()
    context_path = Path(temp_dir) / "context.txt"
    headlines_path = Path(temp_dir) / "headlines.txt"
    context_path.write_text("This is a context prompt.")
    headlines_path.write_text("This is a headlines prompt.")
    return Path(temp_dir)

def test_prompts_init_valid():
    temp_dir = create_temp_prompt_dir()
    try:
        prompts = Prompts(temp_dir)
        assert prompts._base_path.exists()
    finally:
        shutil.rmtree(str(temp_dir))

def test_prompts_init_invalid():
    with pytest.raises(FileNotFoundError):
        Prompts(Path("/nonexistent/path/to/prompts"))

def test_get_prompt_success():
    temp_dir = create_temp_prompt_dir()
    try:
        prompts = Prompts(temp_dir)
        assert prompts.get_prompt("context") == "This is a context prompt."
        assert prompts.get_prompt("headlines") == "This is a headlines prompt."
    finally:
        shutil.rmtree(str(temp_dir))

def test_get_prompt_missing_file():
    temp_dir = create_temp_prompt_dir()
    try:
        prompts = Prompts(temp_dir)
        with pytest.raises(FileNotFoundError):
            prompts.get_prompt("missing")
    finally:
        shutil.rmtree(str(temp_dir))

def test_get_context_prompt():
    temp_dir = create_temp_prompt_dir()
    try:
        prompts = Prompts(temp_dir)
        assert prompts.get_context_prompt() == "This is a context prompt."
    finally:
        shutil.rmtree(str(temp_dir))

def test_get_headlines_prompt():
    temp_dir = create_temp_prompt_dir()
    try:
        prompts = Prompts(temp_dir)
        assert prompts.get_headlines_prompt() == "This is a headlines prompt."
    finally:
        shutil.rmtree(str(temp_dir))
