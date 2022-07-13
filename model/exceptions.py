
from exceptions import BaseException
from utils import GetItemEnum
from enum import Enum

class ModelExceptionType(Enum, metaclass=GetItemEnum):
  PARSING_ERROR = "MODEL_PARSING_ERROR"

class ModelException(BaseException):
  def __init__(self, type:ModelExceptionType, description:str, module:str):
    super()