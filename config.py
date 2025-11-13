from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()

@dataclass
class Config():
    serpapi_key:str=os.getenv("SERPER_API_KEY","")
    timeout_s:float = 10.0
    default_num_pages:int = 1

    def validate(self):
        assert self.serpapi_key, "SERPAPI_KEY lipsa - adauga-1 in .env"