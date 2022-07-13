from msilib.schema import Error
from typing import List, Dict
import pandas as pd
from pyparsing import col

def build(source_file:str, ftype:str):
  try:
    assert ftype in ['json', 'csv']
    if ftype == 'csv':
      df = pd.read_csv(source_file)
    else :
      df = pd.read_json(source_file, orient='records')
    return df
  except FileNotFoundError as error:
    raise Exception(f"FileNotFoundError: {source_file} not found")
  except AssertionError as error:
    raise Exception(f"TypeError: {ftype} not implemented")
  
'''def check_columns(df:pd.DataFrame, columns:List):
  # check the columns names
  try:
    #check colums
    dfcol = list(df.columns)
    dfcol.sort()

    ckcol = columns.copy()
    ckcol.sort()

    assert dfcol == ckcol, f"ValueError: columns not conform, element be in {columns}"
  except AssertionError as error:
    raise Exception(error.args[0])'''

def check_values(series:pd.Series, values:List):
  try:
    svla_list = series.drop_duplicates().to_list()

    for v in svla_list:
      v = None if pd.isna(v) else v
      assert v in values, f"ValueError: value {v} in column {series.name} not conform, must be in {values}"
  
  except AssertionError as error:
    raise Exception(error.args[0])

def build_and_check(source_file:str,
                    ftype:str,
                    columns:List,
                    checks:Dict=None):
  try:
    df = build(source_file, ftype)
    df = df[columns]
    
    if checks:
      for key, val in checks.items():
        check_values(df[key], val)
        
    return df
  except KeyError as error:
    raise Exception(f"KeyError: missing column in data {source_file}: {error.args[0]}")
  except Exception as error:
    raise Exception(f"Error durring build and check of {source_file}: {error.args[0]}")