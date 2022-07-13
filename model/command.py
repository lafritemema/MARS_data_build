from typing import Dict
from uuid import uuid4
class Command:
  def __init__(self,
               target:str,
               action:str,
               description:str,
               definition:Dict):
    self.__uid = str(uuid4())
    self.__action = action
    self.__target = target
    self.__description = description
    self.__definition = definition
  
  @property
  def uid(self):
    return self.__uid
  
  def to_dict(self):
    return {
      'uid': self.__uid,
      'action': self.__action,
      'target': self.__target,
      'description' : self.__description,
      'definition' : self.__definition
    }
