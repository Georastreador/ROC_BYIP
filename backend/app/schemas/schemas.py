from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class Subject(BaseModel):
    what: str
    who: str
    where: str

class TimeWindow(BaseModel):
    start: str
    end: str

class UserInfo(BaseModel):
    principal: str
    others: Optional[str] = ""
    depth: Literal["executivo","gerencial","tecnico"]
    secrecy: Literal["publico","restrito","confidencial","secreto"]

class Deadline(BaseModel):
    date: str
    urgency: Literal["baixa","media","alta","critica"]

class PIR(BaseModel):
    aspect_ref: Optional[int] = None
    question: str
    priority: Literal["baixa","media","alta","critica"] = "media"
    justification: Optional[str] = ""

class CollectionTask(BaseModel):
    pir_index: int
    source: str
    method: str
    frequency: Literal["unico","diario","semanal","mensal"] = "unico"
    owner: str
    sla_hours: int = 0

class EvidenceRead(BaseModel):
    id: int
    filename: str
    sha256: str
    size: int

class PlanBase(BaseModel):
    title: str = "Plano de Inteligência"
    subject: Subject
    time_window: TimeWindow
    user: UserInfo
    purpose: str
    deadline: Deadline
    aspects_essential: List[str] = Field(default_factory=list)
    aspects_known: List[str] = Field(default_factory=list)
    aspects_to_know: List[str] = Field(default_factory=list)
    pirs: List[PIR] = Field(default_factory=list)
    collection: List[CollectionTask] = Field(default_factory=list)
    extraordinary: List[str] = Field(default_factory=list)
    security: List[str] = Field(default_factory=list)

class PlanCreate(PlanBase):
    pass

class PlanRead(PlanBase):
    id: int
    evidences: List[EvidenceRead] = Field(default_factory=list)
    class Config:
        from_attributes = True
