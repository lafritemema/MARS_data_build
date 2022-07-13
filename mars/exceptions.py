from typing import List
from exceptions import BaseException, ExceptionType
from enum import Enum

class MarsExceptionType(ExceptionType):
  CONFIG_ERROR = "MARS_CONFIG_ERROR"
  CONFIG_MISSING = "MARS_CONFIG_MISSING"

class MarsException(BaseException):
  def __init__(self, origin_stack:List[str], type:MarsExceptionType, description:str):
    super().__init__(origin_stack,
                     type,
                     description)