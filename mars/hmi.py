from model.command import Command
from enum import Enum
from typing import Dict, List

from model.definition import Manipulation

class HmiAction(Enum):
  REQUEST = "REQUEST"

class HmiMethod(Enum):
  NOTIFY = "NOTIFY"

class HmiCommand(Command):
  def __init__(self, action:HmiAction, description:str, definition:Dict):
    super().__init__("HMI", action.value, description, definition)

def send_manipulation_message(manipulation:Manipulation) -> List[HmiCommand]:
  """function to generate list of commands to send manipulation message to HMI 

  Args:
      manipulation (Manipulation): object describing the manipulation

  Returns:
      List[HmiCommand]: _description_
  """

  METHOD = HmiMethod.NOTIFY
  PATH = "/sequencer/manipulation"

  body = manipulation.to_dict()

  definition = {
    "body":body,
    "path":PATH,
    "method":METHOD.value 
  }

  return [HmiCommand(HmiAction.REQUEST,
                     f"send message to HMI to {manipulation.operation} {manipulation.equipment.type} {manipulation.equipment.reference}",
                     definition)] 
