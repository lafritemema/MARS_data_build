
from enum import Enum
from functools import partial
from typing import Dict
  
class EquipmentI(Enum):
  pass
  @property
  def type(self)->str:
    return self.__class__.__name__.upper()
  @property
  def reference(self)->str:
    return self.value

def load(equipment:EquipmentI):
  return {
    'manipulation': 'LOAD',
    'equipment': {
      'type':equipment.type,
      'reference': equipment.reference
    }
  }

def unload(equipment:EquipmentI):
  return {
    'manipulation': 'UNLOAD',
    'equipment': {
      'type': equipment.type,
      'reference': equipment.reference
    }
  }

class Operation(Enum):
  LOAD = partial(load)
  UNLOAD = partial(unload)

  def apply_on(self, equipement:EquipmentI):
    fct = self.value
    return fct(equipement)



  