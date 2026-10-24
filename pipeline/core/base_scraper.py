from abc import ABC, abstractmethod
from typing import List, Dict, Generator, Any

class BaseCouncilScraper(ABC):
    def __init__(self, city_config: Dict[str, Any]):
        self.config = city_config
        self.city_code = city_config.get('city', {}).get('code', '')

    @abstractmethod
    def fetch_meeting_list(self, year: int) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def fetch_meeting_statements(self, meeting_id: str) -> Generator[Dict[str, Any], None, None]:
        pass
