"""
SDTM Document Registry
======================

Manages and tracks all documents required for the SDTM ETL process.

The 10 required documents are:
1. Protocol
2. Annotated Case Report Form (aCRF)
3. EDC Data Dictionary/Specification
4. Data Transfer Specifications (DTS)
5. SDTM Implementation Guide (SDTMIG)
6. CDISC Controlled Terminology (CT)
7. SDTM Mapping Specification
8. Study Data Reviewer's Guide (SDRG)
9. Define.xml
10. Validation Report

Author: SDTM ETL Pipeline
Version: 2.0.0
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field
import json


class DocumentType(str, Enum):
    """Types of documents required for SDTM ETL process."""
    PROTOCOL = "protocol"
    ANNOTATED_CRF = "annotated_crf"
    EDC_DATA_DICTIONARY = "edc_data_dictionary"
    DATA_TRANSFER_SPEC = "data_transfer_spec"
    SDTMIG = "sdtmig"
    CONTROLLED_TERMINOLOGY = "controlled_terminology"
    MAPPING_SPECIFICATION = "mapping_specification"
    SDRG = "sdrg"
    DEFINE_XML = "define_xml"
    VALIDATION_REPORT = "validation_report"


class DocumentStatus(str, Enum):
    """Status of a document in the registry."""
    NOT_AVAILABLE = "not_available"
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    FINAL = "final"
    SUPERSEDED = "superseded"


class DocumentSource(str, Enum):
    """Source/Owner of documents."""
    SPONSOR = "sponsor"
    DATA_MANAGEMENT = "data_management"
    STATISTICAL_PROGRAMMING = "statistical_programming"
    CDISC = "cdisc"
    VENDOR = "vendor"
    QUALITY_CONTROL = "quality_control"
    SYSTEM_GENERATED = "system_generated"


# Document metadata definitions
DOCUMENT_DEFINITIONS: Dict[DocumentType, Dict[str, Any]] = {
    DocumentType.PROTOCOL: {
        "name": "Protocol",
        "purpose": "Provides the context, study design, and objectives which inform data collection and derivation rules",
        "default_source": DocumentSource.SPONSOR,
        "required_for_phases": ["metadata_preparation", "sdtm_transformation"],
        "file_extensions": [".pdf", ".docx"],
        "is_cdisc_standard": False
    },
    DocumentType.ANNOTATED_CRF: {
        "name": "Annotated Case Report Form (aCRF)",
        "purpose": "Links data collection fields (CRF) to corresponding SDTM variables. Essential for creating mapping specification",
        "default_source": DocumentSource.DATA_MANAGEMENT,
        "required_for_phases": ["metadata_preparation"],
        "file_extensions": [".pdf"],
        "is_cdisc_standard": False
    },
    DocumentType.EDC_DATA_DICTIONARY: {
        "name": "EDC Data Dictionary/Specification",
        "purpose": "Defines the structure, format, and content of raw source data extracted from EDC system",
        "default_source": DocumentSource.DATA_MANAGEMENT,
        "required_for_phases": ["metadata_preparation", "raw_data_validation"],
        "file_extensions": [".xlsx", ".csv", ".json"],
        "is_cdisc_standard": False
    },
    DocumentType.DATA_TRANSFER_SPEC: {
        "name": "Data Transfer Specifications (DTS)",
        "purpose": "Defines format and content of data received from external vendors (labs, ECG, etc.)",
        "default_source": DocumentSource.VENDOR,
        "required_for_phases": ["data_ingestion", "metadata_preparation"],
        "file_extensions": [".xlsx", ".pdf", ".docx"],
        "is_cdisc_standard": False
    },
    DocumentType.SDTMIG: {
        "name": "SDTM Implementation Guide (SDTMIG)",
        "purpose": "Primary standard reference for structure and content of all SDTM domains",
        "default_source": DocumentSource.CDISC,
        "required_for_phases": ["metadata_preparation", "sdtm_transformation", "target_data_validation"],
        "file_extensions": [".pdf", ".json"],
        "is_cdisc_standard": True,
        "version_required": True
    },
    DocumentType.CONTROLLED_TERMINOLOGY: {
        "name": "CDISC Controlled Terminology (CT)",
        "purpose": "Provides standardized, permissible values for coded variables in SDTM datasets",
        "default_source": DocumentSource.CDISC,
        "required_for_phases": ["sdtm_transformation", "target_data_validation"],
        "file_extensions": [".xlsx", ".json", ".xml"],
        "is_cdisc_standard": True,
        "version_required": True
    },
    DocumentType.MAPPING_SPECIFICATION: {
        "name": "SDTM Mapping Specification",
        "purpose": "The MOST CRITICAL document - details source-to-target mapping, transformation logic, and derivation rules for every SDTM variable",
        "default_source": DocumentSource.STATISTICAL_PROGRAMMING,
        "required_for_phases": ["sdtm_transformation"],
        "file_extensions": [".xlsx", ".json"],
        "is_cdisc_standard": False,
        "is_generated": True
    },
    DocumentType.SDRG: {
        "name": "Study Data Reviewer's Guide (SDRG)",
        "purpose": "Explains non-standard data, deviations from SDTMIG, and provides narrative for submitted data. Documents mapping decisions and data issues",
        "default_source": DocumentSource.STATISTICAL_PROGRAMMING,
        "required_for_phases": ["data_warehouse_loading"],
        "file_extensions": [".pdf", ".docx"],
        "is_cdisc_standard": False
    },
    DocumentType.DEFINE_XML: {
        "name": "Define.xml",
        "purpose": "Machine-readable metadata file describing submitted SDTM datasets including variable attributes, controlled terminology, and derivation methods",
        "default_source": DocumentSource.SYSTEM_GENERATED,
        "required_for_phases": ["target_data_generation", "target_data_validation"],
        "file_extensions": [".xml"],
        "is_cdisc_standard": True,
        "is_generated": True
    },
    DocumentType.VALIDATION_REPORT: {
        "name": "Validation Report",
        "purpose": "Output from target data validation (e.g., Pinnacle 21 report), serving as official record of dataset compliance status",
        "default_source": DocumentSource.SYSTEM_GENERATED,
        "required_for_phases": ["target_data_validation", "data_warehouse_loading"],
        "file_extensions": [".html", ".pdf", ".json", ".xlsx"],
        "is_cdisc_standard": False,
        "is_generated": True
    }
}


class DocumentRecord(BaseModel):
    """
    A record of a document in the registry.
    """
    document_type: DocumentType
    name: str
    version: Optional[str] = None
    status: DocumentStatus = DocumentStatus.NOT_AVAILABLE
    source: DocumentSource

    # File information
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    file_size_bytes: Optional[int] = None
    file_hash: Optional[str] = None  # For integrity verification

    # CDISC version info (for standard documents)
    cdisc_version: Optional[str] = None  # e.g., "3.4" for SDTMIG
    ct_version: Optional[str] = None  # e.g., "2024-03-29" for CT

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None

    # Content metadata
    description: Optional[str] = None
    notes: Optional[str] = None

    # For generated documents
    is_generated: bool = False
    generated_by: Optional[str] = None  # Pipeline phase or component
    generation_config: Optional[Dict[str, Any]] = None


class DocumentRegistry:
    """
    Registry for managing all SDTM ETL process documents.
    """

    def __init__(self, study_id: str, storage_path: Optional[str] = None):
        self.study_id = study_id
        self.storage_path = Path(storage_path) if storage_path else Path("./documents")
        self.documents: Dict[DocumentType, DocumentRecord] = {}
        self._initialize_registry()

    def _initialize_registry(self):
        """Initialize the registry with all required document types."""
        for doc_type, definition in DOCUMENT_DEFINITIONS.items():
            self.documents[doc_type] = DocumentRecord(
                document_type=doc_type,
                name=definition["name"],
                source=definition["default_source"],
                is_generated=definition.get("is_generated", False),
                description=definition["purpose"]
            )

    def register_document(
        self,
        document_type: DocumentType,
        file_path: str,
        version: Optional[str] = None,
        status: DocumentStatus = DocumentStatus.DRAFT,
        cdisc_version: Optional[str] = None,
        ct_version: Optional[str] = None,
        notes: Optional[str] = None
    ) -> DocumentRecord:
        """
        Register or update a document in the registry.
        """
        path = Path(file_path)
        record = self.documents[document_type]

        record.file_path = str(path.absolute())
        record.file_name = path.name
        record.version = version
        record.status = status
        record.updated_at = datetime.utcnow()

        if cdisc_version:
            record.cdisc_version = cdisc_version
        if ct_version:
            record.ct_version = ct_version
        if notes:
            record.notes = notes

        # Get file size if file exists
        if path.exists():
            record.file_size_bytes = path.stat().st_size

        return record

    def register_generated_document(
        self,
        document_type: DocumentType,
        file_path: str,
        generated_by: str,
        generation_config: Optional[Dict[str, Any]] = None,
        version: Optional[str] = None
    ) -> DocumentRecord:
        """
        Register a document that was generated by the pipeline.
        """
        record = self.register_document(
            document_type=document_type,
            file_path=file_path,
            version=version,
            status=DocumentStatus.DRAFT
        )

        record.is_generated = True
        record.generated_by = generated_by
        record.generation_config = generation_config

        return record

    def get_document(self, document_type: DocumentType) -> Optional[DocumentRecord]:
        """Get a document record by type."""
        return self.documents.get(document_type)

    def is_document_available(self, document_type: DocumentType) -> bool:
        """Check if a document is available (has a file path)."""
        record = self.documents.get(document_type)
        return record is not None and record.file_path is not None

    def get_documents_for_phase(self, phase: str) -> List[DocumentRecord]:
        """Get all documents required for a specific phase."""
        required_docs = []
        for doc_type, definition in DOCUMENT_DEFINITIONS.items():
            if phase in definition.get("required_for_phases", []):
                required_docs.append(self.documents[doc_type])
        return required_docs

    def check_phase_readiness(self, phase: str) -> Dict[str, Any]:
        """
        Check if all required documents are available for a phase.
        """
        required_docs = self.get_documents_for_phase(phase)
        missing_docs = []
        available_docs = []

        for doc in required_docs:
            if self.is_document_available(doc.document_type):
                available_docs.append(doc.document_type.value)
            else:
                missing_docs.append(doc.document_type.value)

        return {
            "phase": phase,
            "is_ready": len(missing_docs) == 0,
            "available_documents": available_docs,
            "missing_documents": missing_docs,
            "total_required": len(required_docs)
        }

    def approve_document(
        self,
        document_type: DocumentType,
        approved_by: str,
        notes: Optional[str] = None
    ) -> DocumentRecord:
        """Approve a document."""
        record = self.documents[document_type]
        record.status = DocumentStatus.APPROVED
        record.approved_at = datetime.utcnow()
        record.approved_by = approved_by
        if notes:
            record.notes = notes
        return record

    def get_registry_summary(self) -> Dict[str, Any]:
        """Get a summary of the document registry."""
        total_docs = len(self.documents)
        available_docs = sum(1 for d in self.documents.values() if d.file_path is not None)
        approved_docs = sum(1 for d in self.documents.values() if d.status == DocumentStatus.APPROVED)
        generated_docs = sum(1 for d in self.documents.values() if d.is_generated and d.file_path)

        return {
            "study_id": self.study_id,
            "total_documents": total_docs,
            "available_documents": available_docs,
            "approved_documents": approved_docs,
            "generated_documents": generated_docs,
            "completion_percentage": round((available_docs / total_docs) * 100, 1),
            "documents": {
                doc_type.value: {
                    "name": record.name,
                    "status": record.status.value,
                    "available": record.file_path is not None,
                    "version": record.version,
                    "is_generated": record.is_generated
                }
                for doc_type, record in self.documents.items()
            }
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert registry to dictionary for serialization."""
        return {
            "study_id": self.study_id,
            "storage_path": str(self.storage_path),
            "documents": {
                doc_type.value: record.model_dump()
                for doc_type, record in self.documents.items()
            }
        }

    def save(self, file_path: Optional[str] = None):
        """Save registry to JSON file."""
        path = Path(file_path) if file_path else self.storage_path / f"document_registry_{self.study_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)

    @classmethod
    def load(cls, file_path: str) -> "DocumentRegistry":
        """Load registry from JSON file."""
        with open(file_path, 'r') as f:
            data = json.load(f)

        registry = cls(
            study_id=data["study_id"],
            storage_path=data.get("storage_path")
        )

        # Restore document records
        for doc_type_str, record_data in data.get("documents", {}).items():
            doc_type = DocumentType(doc_type_str)
            registry.documents[doc_type] = DocumentRecord(**record_data)

        return registry


# CDISC Standard Version References
CDISC_VERSIONS = {
    "sdtmig": {
        "3.4": {
            "release_date": "2021-11-15",
            "notes": "Current version for most submissions"
        },
        "3.3": {
            "release_date": "2018-11-26",
            "notes": "Legacy version"
        }
    },
    "ct": {
        "2024-12-20": {
            "notes": "Latest controlled terminology package"
        },
        "2024-09-27": {
            "notes": "Q3 2024 release"
        },
        "2024-06-28": {
            "notes": "Q2 2024 release"
        }
    }
}
