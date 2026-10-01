from pydantic import BaseModel, Field
from datetime import datetime
from typing import List


class AnswerResponse(BaseModel):
    """Structured schema for Q&A responses."""
    question: str = Field(description="The original user question")
    answer: str = Field(description="The generated answer")
    sources: List[str] = Field(description="List of source document IDs used")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0 and 1")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the response was generated")


class UserIntent(BaseModel):
    """Structured schema for intent classification."""
    intent_type: str = Field(
        description='The classified intent: "qa", "summarization", "calculation", or "unknown"'
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in classification between 0 and 1")
    reasoning: str = Field(description="Explanation for the classification decision")


class SummarizationResponse(BaseModel):
    """Structured schema for summarization responses."""
    summary: str = Field(description="A comprehensive summary of the document(s)")
    key_points: List[str] = Field(description="List of key points extracted from the document")
    sources: List[str] = Field(description="List of source document IDs referenced")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the response was generated")


class CalculationResponse(BaseModel):
    """Structured schema for calculation responses."""
    question: str = Field(description="The original calculation question")
    result: str = Field(description="The final calculation result with context")
    expression: str = Field(description="The mathematical expression that was evaluated")
    sources: List[str] = Field(description="List of document IDs where data was sourced from")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the response was generated")
