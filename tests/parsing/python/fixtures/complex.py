"""Complex Python file for testing with classes, inheritance, and method calls."""

from abc import ABC, abstractmethod
from typing import List, Optional


class BaseClass(ABC):
    """Abstract base class."""
    
    @abstractmethod
    def abstract_method(self) -> str:
        pass
    
    def base_method(self) -> int:
        return 42


class DerivedClass(BaseClass):
    """Class that extends BaseClass."""
    
    def __init__(self, name: str, items: List[str]):
        self.name = name
        self.items = items
        self._count = 0
    
    def abstract_method(self) -> str:
        return f"Implemented: {self.name}"
    
    def process_items(self) -> List[str]:
        """Process all items."""
        result = []
        for item in self.items:
            processed = self.transform_item(item)
            result.append(processed)
        return result
    
    def transform_item(self, item: str) -> str:
        """Transform a single item."""
        return item.upper()
    
    def get_count(self) -> int:
        return self._count


@decorator_one
@decorator_two
class DecoratedClass:
    """Class with decorators."""
    
    class_var: int = 10
    
    def method_with_defaults(self, a: int = 1, b: str = "default") -> bool:
        return True


def standalone_function(x: int, y: int, *args, **kwargs) -> int:
    """Standalone function with various parameters."""
    return x + y


def calls_other_function():
    """Function that calls another function."""
    result = standalone_function(1, 2)
    return result
