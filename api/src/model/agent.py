from typing import Optional

from pydantic import BaseModel

class Question(BaseModel):
  userInput: str

class Answer(BaseModel):
  textResponse: str
  textExplanation: str
  data: Optional[str] = ''