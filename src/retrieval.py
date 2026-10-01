import os
import re
from pathlib import Path
from typing import Dict, List, Optional

# Sample financial and healthcare documents
SAMPLE_DOCUMENTS: Dict[str, Dict] = {
    "doc_financial_q1": {
        "content": """Q1 2024 Financial Report
Total Revenue: $4,200,000
Operating Expenses: $2,800,000
Net Profit: $1,400,000
Gross Margin: 65%
Customer Acquisition Cost: $120
Average Revenue Per User: $350
Year-over-Year Growth: 23%
Cash and Equivalents: $8,500,000
Total Assets: $15,200,000
Total Liabilities: $3,100,000
Debt-to-Equity Ratio: 0.25
Return on Assets: 9.2%
Number of Customers: 12,000""",
        "title": "Q1 2024 Financial Report",
        "type": "financial",
    },
    "doc_financial_q2": {
        "content": """Q2 2024 Financial Report
Total Revenue: $5,100,000
Operating Expenses: $3,200,000
Net Profit: $1,900,000
Gross Margin: 67%
Customer Acquisition Cost: $110
Average Revenue Per User: $380
Year-over-Year Growth: 31%
Cash and Equivalents: $10,200,000
Total Assets: $18,500,000
Total Liabilities: $3,800,000
Debt-to-Equity Ratio: 0.28
Return on Assets: 10.3%
Number of Customers: 13,421""",
        "title": "Q2 2024 Financial Report",
        "type": "financial",
    },
    "doc_healthcare_stats": {
        "content": """Healthcare Statistics Report 2024
Total Patients Treated: 12,450
Average Length of Stay: 4.2 days
Readmission Rate: 8.3%
Patient Satisfaction Score: 87 out of 100
Emergency Department Visits: 3,200
Surgical Procedures Performed: 1,850
Average Cost per Patient: $5,420
Insurance Coverage Rate: 92%
Staff-to-Patient Ratio: 1 to 4
Annual Budget: $67,500,000
Annual Operating Costs: $58,200,000
Pharmacy Expenditure: $8,300,000
Number of Beds: 450
Bed Occupancy Rate: 78%""",
        "title": "Healthcare Statistics 2024",
        "type": "healthcare",
    },
    "doc_healthcare_outcomes": {
        "content": """Patient Outcomes Report 2024
Total Procedures: 8,240
Successful Outcomes: 7,952 (96.5%)
Complications Rate: 3.5%
Average Recovery Time: 12.3 days
30-day Readmission Rate: 6.8%
Patient Mortality Rate: 0.8%
ICU Admissions: 420
Average ICU Stay: 3.1 days
Follow-up Compliance Rate: 78%
Preventive Care Visits: 4,650
Total Surgeries: 1,850
Minimally Invasive Procedures: 1,240""",
        "title": "Patient Outcomes Report 2024",
        "type": "healthcare",
    },
}


class DocumentRetriever:
    """Simple keyword-based document retriever for the assistant."""

    def __init__(self):
        self.documents = SAMPLE_DOCUMENTS

    def get_document(self, doc_id: str) -> Optional[Dict]:
        """Retrieve a single document by its exact ID."""
        return self.documents.get(doc_id.strip())

    def search_documents(self, query: str, top_k: int = 2) -> List[Dict]:
        """Search documents by keyword matching against content and title.

        Returns the top_k most relevant documents, falling back to all documents
        if no keywords match.
        """
        query_terms = query.lower().split()
        scored: List[tuple] = []

        for doc_id, doc_data in self.documents.items():
            combined = (doc_data["content"] + " " + doc_data["title"]).lower()
            score = sum(1 for term in query_terms if term in combined)
            if score > 0:
                scored.append((score, doc_id, doc_data))

        # Sort by relevance score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        results = [
            {"id": doc_id, "title": data["title"], "content": data["content"], "type": data["type"]}
            for _, doc_id, data in scored[:top_k]
        ]

        # Fall back to the first two documents if no keyword matches
        if not results:
            for doc_id, data in list(self.documents.items())[:top_k]:
                results.append({"id": doc_id, "title": data["title"], "content": data["content"], "type": data["type"]})

        return results

    def list_documents(self) -> List[Dict]:
        """List all available documents (id, title, type only)."""
        return [
            {"id": doc_id, "title": data["title"], "type": data["type"]}
            for doc_id, data in self.documents.items()
        ]

    def load_document(self, file_path: str) -> str:
        """Load a plain-text or .txt file and register it as a new document.

        The document ID is derived from the filename (without extension).
        Returns the generated document ID on success, or an error message.
        """
        path = Path(file_path)
        if not path.exists():
            return f"Error: File not found — {file_path}"

        suffix = path.suffix.lower()
        if suffix not in ("", ".txt", ".md", ".csv"):
            return (
                f"Error: Unsupported file type '{suffix}'. "
                "Supported types: .txt, .md, .csv (plain text files)."
            )

        try:
            content = path.read_text(encoding="utf-8")
        except Exception as exc:
            return f"Error reading file: {exc}"

        # Build a clean document ID from the filename
        raw_id = re.sub(r"[^a-zA-Z0-9_]", "_", path.stem).strip("_").lower()
        doc_id = raw_id if raw_id else "uploaded_doc"

        # Avoid overwriting existing docs silently
        if doc_id in self.documents:
            doc_id = f"{doc_id}_{len(self.documents)}"

        self.documents[doc_id] = {
            "content": content,
            "title": path.name,
            "type": "uploaded",
        }
        return doc_id


# Module-level retriever instance shared by tools
retriever = DocumentRetriever()
