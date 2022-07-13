from typing import List
from enum import Enum

class ExceptionType(Enum):
  pass

class BaseExceptionType(ExceptionType):
  CONFIG_MISSING = "BASE_CONFIG_MISSING"
  CONFIG_NOT_CONFORM = "BASE_CONFIG_NOT_CONFORM"

class BaseException(Exception):
  def __init__(self, origin_stack:List[str], type:ExceptionType, description:str):
    self._origin_stack = origin_stack
    self._type = type
    self._description = description
  
  def add_in_stack(self, stack_update:List[str]):
    self._origin_stack = stack_update + self._origin_stack
  
  def describe(self):
    return {
      "origin" : '.'.join(self._origin_stack),
      "default" : self._type.value,
      "description": self._description
    }

  