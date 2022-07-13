# MODIFGEN from ..model.equipment import EquipmentI
from model.equipment import EquipmentI
# MODIFGEN from ..utils import GetItemEnum
from utils import GetItemEnum
from enum import Enum


class Effector(EquipmentI):
  WEB_C_DRILLING = 'WEB_C_DRILLING'
  FLANGE_C_DRILLING = 'FLANGE_C_DRILLING'
  # TODO : Try to delete no effector entry
  NO_EFFECTOR = 'NO_EFFECTOR'


class Equipment(Enum, metaclass=GetItemEnum):
  EFFECTOR = Effector
