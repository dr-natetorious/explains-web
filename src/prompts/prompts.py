from os import PathLike
from pathlib import Path
DEFAULT_PROMPT_FOLDER = Path(__file__).parent

class Prompts:
    """
    A class to hold various prompts used in the application.
    """
    def __init__(self, prompts:PathLike=DEFAULT_PROMPT_FOLDER) -> None:
        self._base_path = Path(prompts)
        if not self._base_path.exists():
            raise FileNotFoundError(f"Prompt folder '{self._base_path}' does not exist.")
    
    def get_prompt(self, prompt_name: str) -> str:
        """
        Returns the prompt text for the given prompt name.
        """
        prompt_path = self._base_path / f"{prompt_name}.txt"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file '{prompt_name}.txt' does not exist.")
        
        with open(prompt_path, 'r', encoding='utf-8') as file:
            return file.read().strip()
            
    def get_context_prompt(self) -> str:
        """
        Returns the context prompt for the application.
        """
        return self.get_prompt("context")
    
    def get_headlines_prompt(self) -> str:
        """
        Returns the headlines prompt for the application.
        """
        return self.get_prompt("headlines")
    
        