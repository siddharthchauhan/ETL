"""
SDTM Pipeline Orchestrator
==========================
Main orchestration class for the complete SDTM transformation pipeline.
Includes human-in-the-loop review checkpoints.
"""

import os
import json
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field

from .models.sdtm_models import (
    MappingSpecification,
    ValidationResult,
    TransformationResult
)
from .validators.raw_data_validator import RawDataValidator
from .validators.sdtm_validator import SDTMValidator
from .transformers.mapping_generator import MappingSpecificationGenerator
from .transformers.domain_transformers import get_transformer
from .generators.sas_generator import SASCodeGenerator
from .generators.r_generator import RCodeGenerator


@dataclass
class PipelineConfig:
    """Configuration for SDTM pipeline execution."""
    study_id: str
    raw_data_dir: str
    output_dir: str
    api_key: str
    human_review: bool = True
    generate_sas: bool = True
    generate_r: bool = True
    skip_validation: bool = False


@dataclass
class PipelineState:
    """State tracking for pipeline execution."""
    phase: str = "initialized"
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    raw_validation_results: List[ValidationResult] = field(default_factory=list)
    mapping_specifications: List[MappingSpecification] = field(default_factory=list)
    transformation_results: List[TransformationResult] = field(default_factory=list)
    sdtm_validation_results: List[ValidationResult] = field(default_factory=list)
    generated_code: Dict[str, Dict[str, str]] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    human_approvals: Dict[str, bool] = field(default_factory=dict)


class SDTMPipelineOrchestrator:
    """
    Orchestrates the complete SDTM transformation pipeline.

    Pipeline phases:
    1. Raw Data Ingestion
    2. Raw Data Validation
    3. Human Review (optional)
    4. Mapping Specification Generation
    5. Human Review of Mappings (optional)
    6. SDTM Transformation
    7. SDTM Validation
    8. Human Review of SDTM (optional)
    9. Code Generation (SAS/R)
    10. Final Report
    """

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.state = PipelineState()

        # Initialize components
        self.raw_validator = RawDataValidator(config.study_id)
        self.sdtm_validator = SDTMValidator(config.study_id)
        self.mapping_generator = MappingSpecificationGenerator(
            config.api_key, config.study_id
        )
        self.sas_generator = SASCodeGenerator(
            config.study_id,
            os.path.join(config.output_dir, "sas_programs")
        )
        self.r_generator = RCodeGenerator(
            config.study_id,
            os.path.join(config.output_dir, "r_programs")
        )

        # Setup output directories
        self._setup_directories()

    def _setup_directories(self):
        """Create output directory structure."""
        dirs = [
            self.config.output_dir,
            os.path.join(self.config.output_dir, "raw_validation"),
            os.path.join(self.config.output_dir, "mapping_specs"),
            os.path.join(self.config.output_dir, "sdtm_data"),
            os.path.join(self.config.output_dir, "sdtm_validation"),
            os.path.join(self.config.output_dir, "sas_programs"),
            os.path.join(self.config.output_dir, "r_programs"),
            os.path.join(self.config.output_dir, "reports"),
        ]
        for d in dirs:
            os.makedirs(d, exist_ok=True)

    def run_pipeline(
        self,
        source_files: List[Dict[str, Any]],
        human_decision: str = "approve"
    ) -> Dict[str, Any]:
        """
        Run the complete SDTM pipeline.

        Args:
            source_files: List of source file information dicts
            human_decision: Human decision for review checkpoints
                           ("approve", "reject", "modify")

        Returns:
            Pipeline execution results
        """
        print("\n" + "=" * 70)
        print("   SDTM TRANSFORMATION PIPELINE")
        print(f"   Study: {self.config.study_id}")
        print(f"   Started: {self.state.started_at}")
        print("=" * 70)

        try:
            # Phase 1: Raw Data Ingestion
            self._phase_ingest_data(source_files)

            # Phase 2: Raw Data Validation
            raw_data = self._phase_validate_raw_data(source_files)

            # Phase 3: Human Review (if enabled)
            if self.config.human_review:
                if not self._human_review_checkpoint("raw_validation", human_decision):
                    return self._generate_rejection_report("Raw data validation")

            # Phase 4: Generate Mapping Specifications
            self._phase_generate_mappings(source_files, raw_data)

            # Phase 5: Human Review of Mappings
            if self.config.human_review:
                if not self._human_review_checkpoint("mapping_specs", human_decision):
                    return self._generate_rejection_report("Mapping specifications")

            # Phase 6: SDTM Transformation
            sdtm_data = self._phase_transform_to_sdtm(raw_data)

            # Phase 7: SDTM Validation
            self._phase_validate_sdtm(sdtm_data)

            # Phase 8: Human Review of SDTM
            if self.config.human_review:
                if not self._human_review_checkpoint("sdtm_validation", human_decision):
                    return self._generate_rejection_report("SDTM validation")

            # Phase 9: Code Generation
            self._phase_generate_code()

            # Phase 10: Final Report
            report = self._generate_final_report()

            self.state.completed_at = datetime.now().isoformat()
            self.state.phase = "completed"

            print("\n" + "=" * 70)
            print("   PIPELINE COMPLETED SUCCESSFULLY")
            print("=" * 70)

            return report

        except Exception as e:
            self.state.errors.append(str(e))
            self.state.phase = "error"
            print(f"\n ERROR: {str(e)}")
            raise

    def _phase_ingest_data(self, source_files: List[Dict[str, Any]]):
        """Phase 1: Ingest raw data."""
        self.state.phase = "ingesting"
        print("\n" + "-" * 60)
        print("PHASE 1: Raw Data Ingestion")
        print("-" * 60)

        print(f"Found {len(source_files)} source files:")
        for f in source_files:
            print(f"  - {f['name']}")

    def _phase_validate_raw_data(
        self, source_files: List[Dict[str, Any]]
    ) -> Dict[str, pd.DataFrame]:
        """Phase 2: Validate raw data."""
        self.state.phase = "validating_raw"
        print("\n" + "-" * 60)
        print("PHASE 2: Raw Data Validation")
        print("-" * 60)

        raw_data = {}
        validation_results = []

        for file_info in source_files:
            filepath = file_info["path"]
            filename = file_info["name"]

            print(f"\nValidating: {filename}")

            # Read data
            df = pd.read_csv(filepath)
            raw_data[filename] = df

            # Validate
            result = self.raw_validator.validate_dataframe(df, filename)
            validation_results.append(result)

            # Report
            status = "PASS" if result.is_valid else "FAIL"
            print(f"  Records: {result.total_records}")
            print(f"  Status: {status}")
            print(f"  Errors: {result.error_count}, Warnings: {result.warning_count}")

        self.state.raw_validation_results = validation_results

        # Save validation report
        report = self.raw_validator.generate_report(validation_results)
        report_path = os.path.join(
            self.config.output_dir, "raw_validation", "validation_report.json"
        )
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\nRaw validation report saved to: {report_path}")
        return raw_data

    def _phase_generate_mappings(
        self,
        source_files: List[Dict[str, Any]],
        raw_data: Dict[str, pd.DataFrame]
    ):
        """Phase 4: Generate SDTM mapping specifications."""
        self.state.phase = "generating_mappings"
        print("\n" + "-" * 60)
        print("PHASE 4: Mapping Specification Generation")
        print("-" * 60)

        mappings = []

        for file_info in source_files:
            filename = file_info["name"]
            df = raw_data[filename]

            print(f"\nGenerating mapping for: {filename}")

            # Generate mapping
            spec = self.mapping_generator.generate_mapping(df, filename)
            mappings.append(spec)

            print(f"  Source: {spec.source_domain}")
            print(f"  Target: {spec.target_domain}")
            print(f"  Mappings: {len(spec.column_mappings)}")

            # Save mapping spec
            spec_path = os.path.join(
                self.config.output_dir,
                "mapping_specs",
                f"{spec.target_domain}_mapping.json"
            )
            self.mapping_generator.generate_mapping_json(spec, spec_path)
            print(f"  Saved to: {spec_path}")

        self.state.mapping_specifications = mappings
        print(f"\n Generated {len(mappings)} mapping specifications")

    def _phase_transform_to_sdtm(
        self, raw_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, pd.DataFrame]:
        """Phase 6: Transform data to SDTM format."""
        self.state.phase = "transforming"
        print("\n" + "-" * 60)
        print("PHASE 6: SDTM Transformation")
        print("-" * 60)

        sdtm_data = {}
        transformation_results = []

        for spec in self.state.mapping_specifications:
            source_name = spec.source_domain
            domain = spec.target_domain

            print(f"\nTransforming {source_name} to {domain}")

            # Get source data
            df = raw_data.get(source_name)
            if df is None:
                print(f"  WARNING: Source data not found for {source_name}")
                continue

            # Get transformer
            try:
                transformer = get_transformer(domain, self.config.study_id, spec)
            except ValueError as e:
                print(f"  WARNING: {str(e)}")
                continue

            # Execute transformation
            result = transformer.execute(df)
            transformation_results.append(result)

            if result.success:
                # Get transformed data
                sdtm_df = transformer.transform(df)
                sdtm_data[domain] = sdtm_df

                # Save to CSV
                output_path = os.path.join(
                    self.config.output_dir, "sdtm_data", f"{domain.lower()}.csv"
                )
                sdtm_df.to_csv(output_path, index=False)

                print(f"  Records: {result.records_processed} -> {result.records_output}")
                print(f"  Saved to: {output_path}")
            else:
                print(f"  ERROR: Transformation failed")
                for error in result.errors:
                    print(f"    - {error}")

        self.state.transformation_results = transformation_results
        print(f"\n Transformed {len(sdtm_data)} domains")
        return sdtm_data

    def _phase_validate_sdtm(self, sdtm_data: Dict[str, pd.DataFrame]):
        """Phase 7: Validate SDTM datasets."""
        self.state.phase = "validating_sdtm"
        print("\n" + "-" * 60)
        print("PHASE 7: SDTM Validation")
        print("-" * 60)

        validation_results = []

        for domain, df in sdtm_data.items():
            print(f"\nValidating {domain} domain")

            result = self.sdtm_validator.validate_domain(df, domain)
            validation_results.append(result)

            status = "PASS" if result.is_valid else "FAIL"
            print(f"  Records: {result.total_records}")
            print(f"  Status: {status}")
            print(f"  Errors: {result.error_count}, Warnings: {result.warning_count}")

        self.state.sdtm_validation_results = validation_results

        # Save validation report
        report = self.sdtm_validator.generate_report(validation_results)
        report_path = os.path.join(
            self.config.output_dir, "sdtm_validation", "validation_report.json"
        )
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\nSDTM validation report saved to: {report_path}")

    def _phase_generate_code(self):
        """Phase 9: Generate SAS and R code."""
        self.state.phase = "generating_code"
        print("\n" + "-" * 60)
        print("PHASE 9: Code Generation")
        print("-" * 60)

        generated = {}

        # Generate SAS code
        if self.config.generate_sas:
            print("\nGenerating SAS programs...")
            sas_files = self.sas_generator.generate_all(
                self.state.mapping_specifications
            )
            generated["sas"] = sas_files
            print(f"  Generated {len(sas_files)} SAS programs")
            for name, path in sas_files.items():
                print(f"    - {name}: {path}")

        # Generate R code
        if self.config.generate_r:
            print("\nGenerating R scripts...")
            r_files = self.r_generator.generate_all(
                self.state.mapping_specifications
            )
            generated["r"] = r_files
            print(f"  Generated {len(r_files)} R scripts")
            for name, path in r_files.items():
                print(f"    - {name}: {path}")

        self.state.generated_code = generated

    def _human_review_checkpoint(self, checkpoint: str, decision: str) -> bool:
        """Human-in-the-loop review checkpoint."""
        print(f"\n HUMAN REVIEW CHECKPOINT: {checkpoint}")

        # In a real system, this would pause and wait for human input
        # For automated testing, we use the provided decision
        approved = decision.lower() == "approve"
        self.state.human_approvals[checkpoint] = approved

        if approved:
            print(f"  Decision: APPROVED")
        else:
            print(f"  Decision: REJECTED")

        return approved

    def _generate_rejection_report(self, phase: str) -> Dict[str, Any]:
        """Generate report when pipeline is rejected."""
        return {
            "status": "rejected",
            "rejected_at": phase,
            "state": self.state,
            "message": f"Pipeline rejected at {phase} review checkpoint"
        }

    def _generate_final_report(self) -> Dict[str, Any]:
        """Generate final pipeline execution report."""
        print("\n" + "-" * 60)
        print("PHASE 10: Final Report")
        print("-" * 60)

        # Calculate statistics
        total_raw_records = sum(
            r.total_records for r in self.state.raw_validation_results
        )
        total_sdtm_records = sum(
            r.total_records for r in self.state.sdtm_validation_results
        )
        raw_errors = sum(
            r.error_count for r in self.state.raw_validation_results
        )
        sdtm_errors = sum(
            r.error_count for r in self.state.sdtm_validation_results
        )

        report = {
            "study_id": self.config.study_id,
            "status": "success",
            "started_at": self.state.started_at,
            "completed_at": datetime.now().isoformat(),
            "summary": {
                "source_files_processed": len(self.state.raw_validation_results),
                "sdtm_domains_created": len(self.state.sdtm_validation_results),
                "total_raw_records": total_raw_records,
                "total_sdtm_records": total_sdtm_records,
                "raw_validation_errors": raw_errors,
                "sdtm_validation_errors": sdtm_errors,
                "submission_ready": sdtm_errors == 0
            },
            "domains": [
                {
                    "domain": spec.target_domain,
                    "source": spec.source_domain,
                    "mappings": len(spec.column_mappings)
                }
                for spec in self.state.mapping_specifications
            ],
            "generated_code": self.state.generated_code,
            "output_directory": self.config.output_dir
        }

        # Save report
        report_path = os.path.join(
            self.config.output_dir, "reports", "pipeline_report.json"
        )
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        # Print summary
        print(f"\n Pipeline Summary:")
        print(f"  Source files processed: {report['summary']['source_files_processed']}")
        print(f"  SDTM domains created: {report['summary']['sdtm_domains_created']}")
        print(f"  Total records: {report['summary']['total_raw_records']} -> {report['summary']['total_sdtm_records']}")
        print(f"  Submission ready: {report['summary']['submission_ready']}")
        print(f"\n Report saved to: {report_path}")

        return report


def run_sdtm_pipeline(
    study_id: str,
    raw_data_dir: str,
    output_dir: str,
    api_key: str,
    source_files: List[Dict[str, Any]],
    human_review: bool = True,
    human_decision: str = "approve"
) -> Dict[str, Any]:
    """
    Convenience function to run the SDTM pipeline.

    Args:
        study_id: Study identifier
        raw_data_dir: Directory containing raw data files
        output_dir: Output directory for results
        api_key: Anthropic API key for LLM features
        source_files: List of source file information
        human_review: Enable human-in-the-loop checkpoints
        human_decision: Default decision for checkpoints

    Returns:
        Pipeline execution report
    """
    config = PipelineConfig(
        study_id=study_id,
        raw_data_dir=raw_data_dir,
        output_dir=output_dir,
        api_key=api_key,
        human_review=human_review
    )

    orchestrator = SDTMPipelineOrchestrator(config)
    return orchestrator.run_pipeline(source_files, human_decision)
