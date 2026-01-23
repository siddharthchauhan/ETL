"""
Interactive SDTM Chat Agent
===========================
Conversational interface for EDC to SDTM conversion with step-by-step output.

Usage:
    python -m sdtm_pipeline.chat_agent

Commands:
    /help           - Show available commands
    /load           - Load EDC data from S3 or local
    /domains        - List available domains
    /convert <domain> - Convert a specific domain (e.g., /convert DM)
    /convert all    - Convert all domains
    /mapping <domain> - Show mapping specification for domain
    /validate <domain> - Validate a domain
    /report         - Show validation report
    /export         - Export results to S3
    /status         - Show current pipeline status
    /quit           - Exit the chat
"""

import os
import sys
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

# Load environment
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sdtm_pipeline.transformers.mapping_generator import MappingSpecificationGenerator
from sdtm_pipeline.transformers.domain_transformers import get_transformer
from sdtm_pipeline.validators.sdtm_validator import SDTMValidator
from sdtm_pipeline.models.sdtm_models import SDTM_DOMAINS, MappingSpecification

# Try to import knowledge tools
try:
    from sdtm_pipeline.langgraph_agent.knowledge_tools import get_knowledge_retriever
    KNOWLEDGE_AVAILABLE = True
except ImportError:
    KNOWLEDGE_AVAILABLE = False

console = Console()


class SDTMChatAgent:
    """
    Interactive chat agent for SDTM conversion.

    Provides a conversational interface for:
    - Loading and previewing EDC data
    - Generating mapping specifications
    - Transforming data to SDTM
    - Validating SDTM datasets
    - Exporting results
    """

    def __init__(self):
        self.console = Console()
        self.study_id = "UNKNOWN"
        self.source_data: Dict[str, pd.DataFrame] = {}
        self.sdtm_data: Dict[str, pd.DataFrame] = {}
        self.mapping_specs: Dict[str, MappingSpecification] = {}
        self.validation_results: Dict[str, Any] = {}
        self.domain_mapping: Dict[str, str] = {}  # source_file -> domain

        # Initialize components
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.mapping_generator = None
        self.validator = None
        self.knowledge_retriever = None

        self._initialize_components()

    def _initialize_components(self):
        """Initialize pipeline components."""
        if self.anthropic_key:
            self.mapping_generator = MappingSpecificationGenerator(
                api_key=self.anthropic_key,
                study_id=self.study_id,
                use_knowledge_tools=True
            )

        self.validator = SDTMValidator(
            study_id=self.study_id,
            use_knowledge_tools=True
        )

        if KNOWLEDGE_AVAILABLE:
            try:
                self.knowledge_retriever = get_knowledge_retriever()
            except Exception:
                pass

    def print_header(self):
        """Print welcome header."""
        header = """
╔══════════════════════════════════════════════════════════════════╗
║           SDTM Interactive Conversion Agent                      ║
║                                                                  ║
║   Convert EDC data to SDTM with step-by-step guidance           ║
║   Type /help for available commands                              ║
╚══════════════════════════════════════════════════════════════════╝
        """
        self.console.print(Panel(header.strip(), style="bold blue"))

        # Show status
        status_items = []
        if self.anthropic_key:
            status_items.append("[green]✓[/green] Anthropic API")
        else:
            status_items.append("[red]✗[/red] Anthropic API (set ANTHROPIC_API_KEY)")

        if self.knowledge_retriever:
            status_items.append("[green]✓[/green] Knowledge Tools (Pinecone/Tavily)")
        else:
            status_items.append("[yellow]○[/yellow] Knowledge Tools")

        self.console.print("Status: " + " | ".join(status_items))
        self.console.print()

    def print_help(self):
        """Print help message."""
        help_text = """
## Available Commands

### Data Loading
- `/load local <path>` - Load EDC data from local zip file
- `/load s3` - Load EDC data from S3 (s3://s3dcri/incoming/EDC Data.zip)
- `/preview <file>` - Preview a source file

### Domain Operations
- `/domains` - List available source files and their target domains
- `/convert <domain>` - Convert a specific domain (e.g., `/convert DM`)
- `/convert all` - Convert all available domains

### Mapping & Validation
- `/mapping <domain>` - Generate and show mapping specification
- `/validate <domain>` - Validate a converted domain
- `/validate all` - Validate all converted domains
- `/report` - Show full validation report

### Knowledge Tools
- `/search <query>` - Search SDTM guidelines (Tavily)
- `/rules <domain>` - Get business rules for domain (Pinecone)

### Export & Status
- `/export` - Export SDTM datasets to S3
- `/status` - Show current pipeline status
- `/clear` - Clear all loaded data

### General
- `/help` - Show this help message
- `/quit` or `/exit` - Exit the chat
        """
        self.console.print(Markdown(help_text))

    async def load_data(self, source: str, path: str = None):
        """Load EDC data from local or S3."""
        if source == "local":
            if not path:
                self.console.print("[red]Error: Please provide a path. Usage: /load local <path>[/red]")
                return
            await self._load_local_data(path)
        elif source == "s3":
            await self._load_s3_data()
        else:
            self.console.print(f"[red]Unknown source: {source}. Use 'local' or 's3'[/red]")

    async def _load_local_data(self, zip_path: str):
        """Load data from local zip file."""
        import zipfile
        import tempfile

        if not os.path.exists(zip_path):
            self.console.print(f"[red]File not found: {zip_path}[/red]")
            return

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Loading EDC data...", total=None)

            try:
                # Extract zip
                temp_dir = tempfile.mkdtemp()
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    zf.extractall(temp_dir)

                # Find CSV files
                csv_files = list(Path(temp_dir).rglob("*.csv"))

                progress.update(task, description=f"Found {len(csv_files)} CSV files...")

                # Load each file
                for csv_file in csv_files:
                    try:
                        df = pd.read_csv(csv_file)
                        filename = csv_file.name
                        self.source_data[filename] = df

                        # Determine target domain
                        domain = self._determine_domain(filename)
                        self.domain_mapping[filename] = domain
                    except Exception as e:
                        self.console.print(f"[yellow]Warning: Could not load {csv_file.name}: {e}[/yellow]")

                # Detect study ID
                self._detect_study_id()

                progress.update(task, description="[green]Data loaded successfully![/green]")

            except Exception as e:
                self.console.print(f"[red]Error loading data: {e}[/red]")
                return

        # Show summary
        self._show_load_summary()

    async def _load_s3_data(self):
        """Load data from S3."""
        import boto3
        import zipfile
        import tempfile

        bucket = os.getenv("S3_ETL_BUCKET", "s3dcri")
        s3_key = "incoming/EDC Data.zip"

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task(f"Downloading from s3://{bucket}/{s3_key}...", total=None)

            try:
                s3 = boto3.client('s3')
                temp_dir = tempfile.mkdtemp()
                zip_path = os.path.join(temp_dir, "data.zip")

                s3.download_file(bucket, s3_key, zip_path)

                progress.update(task, description="Extracting files...")

                # Extract
                extract_dir = os.path.join(temp_dir, "extracted")
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    zf.extractall(extract_dir)

                # Load CSV files
                csv_files = list(Path(extract_dir).rglob("*.csv"))
                progress.update(task, description=f"Loading {len(csv_files)} CSV files...")

                for csv_file in csv_files:
                    try:
                        df = pd.read_csv(csv_file)
                        filename = csv_file.name
                        self.source_data[filename] = df
                        domain = self._determine_domain(filename)
                        self.domain_mapping[filename] = domain
                    except Exception as e:
                        pass

                self._detect_study_id()
                progress.update(task, description="[green]Data loaded from S3![/green]")

            except Exception as e:
                self.console.print(f"[red]Error loading from S3: {e}[/red]")
                return

        self._show_load_summary()

    def _determine_domain(self, filename: str) -> str:
        """Determine SDTM domain from filename."""
        name_upper = filename.upper().replace(".CSV", "")

        domain_map = {
            "DEMO": "DM", "DEMOGRAPHY": "DM",
            "AEVENT": "AE", "AEVENTC": "SUPPAE",
            "CONMEDS": "CM", "CONMEDSC": "SUPPCM",
            "VITALS": "VS", "VITAL": "VS",
            "CHEMLAB": "LB", "HEMLAB": "LB", "URINALYSIS": "LB",
            "DOSE": "EX", "EXPOSURE": "EX",
            "MEDHIST": "MH", "MEDHISC": "SUPPMH",
            "DISPOSI": "DS", "DISPOSIC": "SUPPDS",
            "ECG": "EG", "ECGC": "SUPPEG",
            "PHYSEX": "PE",
            "PHARMA": "PC",
            "INCEXC": "IE",
            "COMMENT": "CO",
            "QUEST": "QS",
            "RESPONSE": "RS",
            "TUMOR": "TR", "TUMORC": "SUPPTR",
            "TUMORID": "TU", "TUMOIDC": "SUPPTU",
            "TRIALARM": "TA",
        }

        for key, domain in domain_map.items():
            if key in name_upper:
                return domain

        return "UNKNOWN"

    def _detect_study_id(self):
        """Detect study ID from loaded data."""
        for df in self.source_data.values():
            if 'STUDY' in df.columns:
                self.study_id = str(df['STUDY'].iloc[0])
                break
            elif 'STUDYID' in df.columns:
                self.study_id = str(df['STUDYID'].iloc[0])
                break

        # Update components with study ID
        if self.mapping_generator:
            self.mapping_generator.study_id = self.study_id
        if self.validator:
            self.validator.study_id = self.study_id

    def _show_load_summary(self):
        """Show summary of loaded data."""
        table = Table(title=f"Loaded EDC Data - Study: {self.study_id}", box=box.ROUNDED)
        table.add_column("Source File", style="cyan")
        table.add_column("Target Domain", style="green")
        table.add_column("Records", justify="right")
        table.add_column("Columns", justify="right")

        # Group by domain
        domain_files = {}
        for filename, domain in self.domain_mapping.items():
            if domain not in domain_files:
                domain_files[domain] = []
            domain_files[domain].append(filename)

        for filename in sorted(self.source_data.keys()):
            df = self.source_data[filename]
            domain = self.domain_mapping.get(filename, "UNKNOWN")
            table.add_row(filename, domain, str(len(df)), str(len(df.columns)))

        self.console.print(table)
        self.console.print(f"\n[bold]Total:[/bold] {len(self.source_data)} files, {sum(len(df) for df in self.source_data.values())} records")

    def show_domains(self):
        """Show available domains."""
        if not self.source_data:
            self.console.print("[yellow]No data loaded. Use /load to load EDC data first.[/yellow]")
            return

        # Group files by domain
        domain_files: Dict[str, List[str]] = {}
        for filename, domain in self.domain_mapping.items():
            if domain not in domain_files:
                domain_files[domain] = []
            domain_files[domain].append(filename)

        table = Table(title="Available SDTM Domains", box=box.ROUNDED)
        table.add_column("Domain", style="bold green")
        table.add_column("Description")
        table.add_column("Source Files", style="cyan")
        table.add_column("Status")

        domain_descriptions = {
            "DM": "Demographics",
            "AE": "Adverse Events",
            "CM": "Concomitant Medications",
            "VS": "Vital Signs",
            "LB": "Laboratory",
            "EX": "Exposure",
            "MH": "Medical History",
            "DS": "Disposition",
            "EG": "ECG",
            "PE": "Physical Exam",
            "PC": "Pharmacokinetics",
            "IE": "Inclusion/Exclusion",
            "CO": "Comments",
            "QS": "Questionnaires",
            "RS": "Disease Response",
            "TR": "Tumor Results",
            "TU": "Tumor Identification",
            "TA": "Trial Arms",
        }

        for domain in sorted(domain_files.keys()):
            files = domain_files[domain]
            desc = domain_descriptions.get(domain, domain)

            # Check status
            if domain in self.sdtm_data:
                status = "[green]✓ Converted[/green]"
            elif domain.startswith("SUPP"):
                status = "[dim]Supplemental[/dim]"
            else:
                status = "[yellow]○ Pending[/yellow]"

            table.add_row(domain, desc, ", ".join(files), status)

        self.console.print(table)

    def preview_file(self, filename: str):
        """Preview a source file."""
        # Find the file
        matching = [f for f in self.source_data.keys() if filename.lower() in f.lower()]

        if not matching:
            self.console.print(f"[red]File not found: {filename}[/red]")
            return

        filename = matching[0]
        df = self.source_data[filename]

        self.console.print(Panel(f"[bold]Preview: {filename}[/bold]"))
        self.console.print(f"Records: {len(df)} | Columns: {len(df.columns)}")
        self.console.print(f"Target Domain: {self.domain_mapping.get(filename, 'UNKNOWN')}")
        self.console.print()

        # Show first few rows
        table = Table(box=box.SIMPLE, show_lines=True)
        for col in df.columns[:10]:  # Limit columns
            table.add_column(col, style="cyan", max_width=15)

        for _, row in df.head(5).iterrows():
            table.add_row(*[str(v)[:15] for v in row.values[:10]])

        self.console.print(table)

        if len(df.columns) > 10:
            self.console.print(f"[dim]... and {len(df.columns) - 10} more columns[/dim]")

    async def generate_mapping(self, domain: str):
        """Generate and display mapping specification for a domain."""
        if not self.source_data:
            self.console.print("[yellow]No data loaded. Use /load first.[/yellow]")
            return

        # Find source files for this domain
        source_files = [f for f, d in self.domain_mapping.items() if d == domain.upper()]

        if not source_files:
            self.console.print(f"[red]No source files found for domain: {domain}[/red]")
            return

        self.console.print(Panel(f"[bold]Generating Mapping Specification for {domain.upper()}[/bold]"))

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Analyzing source data...", total=None)

            # Get first source file
            source_file = source_files[0]
            df = self.source_data[source_file]

            # Retrieve knowledge if available
            if self.knowledge_retriever:
                progress.update(task, description="Retrieving SDTM guidelines from knowledge base...")
                try:
                    domain_spec = self.knowledge_retriever.get_domain_specification(domain.upper())
                    rules = self.knowledge_retriever.get_business_rules(domain.upper())
                    self.console.print(f"[dim]Retrieved {len(rules) if rules else 0} business rules from Pinecone[/dim]")
                except Exception:
                    pass

            progress.update(task, description="Generating mapping with Claude AI...")

            if self.mapping_generator:
                try:
                    spec = self.mapping_generator.generate_mapping(
                        df=df,
                        source_name=source_file,
                        target_domain=domain.upper()
                    )
                    self.mapping_specs[domain.upper()] = spec
                    progress.update(task, description="[green]Mapping generated![/green]")
                except Exception as e:
                    self.console.print(f"[red]Error generating mapping: {e}[/red]")
                    return
            else:
                self.console.print("[red]Mapping generator not initialized (check ANTHROPIC_API_KEY)[/red]")
                return

        # Display mapping specification
        self._display_mapping_spec(spec)

    def _display_mapping_spec(self, spec: MappingSpecification):
        """Display mapping specification in a nice format."""
        self.console.print()
        self.console.print(Panel(f"[bold green]Mapping Specification: {spec.source_domain} → SDTM {spec.target_domain}[/bold green]"))

        # Metadata
        self.console.print(f"[bold]Study ID:[/bold] {spec.study_id}")
        self.console.print(f"[bold]Created:[/bold] {spec.created_at}")
        self.console.print()

        # Column mappings table
        table = Table(title="Column Mappings", box=box.ROUNDED)
        table.add_column("Source Column", style="cyan")
        table.add_column("Target Variable", style="green")
        table.add_column("Transformation", style="yellow")
        table.add_column("Comments", max_width=30)

        for mapping in spec.column_mappings:
            source = str(mapping.source_column) if mapping.source_column else "[derived]"
            transform = str(mapping.transformation or mapping.derivation_rule or "-")[:30]
            comments = str(mapping.comments)[:30] if mapping.comments else ""
            table.add_row(
                source,
                str(mapping.target_variable),
                transform,
                comments
            )

        self.console.print(table)

        # Derivation rules
        if spec.derivation_rules:
            self.console.print()
            self.console.print("[bold]Derivation Rules:[/bold]")
            for var, rule in spec.derivation_rules.items():
                rule_str = str(rule) if not isinstance(rule, list) else ", ".join(str(r) for r in rule)
                self.console.print(f"  [green]{var}[/green]: {rule_str}")

        # Controlled terminology
        if spec.controlled_terminologies:
            self.console.print()
            self.console.print("[bold]Controlled Terminology:[/bold]")
            for var, values in spec.controlled_terminologies.items():
                if isinstance(values, list):
                    values_str = ", ".join(str(v) for v in values[:5])
                    if len(values) > 5:
                        values_str += "..."
                else:
                    values_str = str(values)
                self.console.print(f"  [green]{var}[/green]: {values_str}")

    async def convert_domain(self, domain: str):
        """Convert a specific domain to SDTM."""
        domain = domain.upper()

        if not self.source_data:
            self.console.print("[yellow]No data loaded. Use /load first.[/yellow]")
            return

        # Find source files
        source_files = [f for f, d in self.domain_mapping.items() if d == domain]

        if not source_files:
            self.console.print(f"[red]No source files found for domain: {domain}[/red]")
            return

        self.console.print(Panel(f"[bold]Converting {domain} Domain[/bold]"))

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            # Step 1: Generate mapping if not exists
            if domain not in self.mapping_specs:
                task = progress.add_task("Step 1/4: Generating mapping specification...", total=None)
                await self.generate_mapping(domain)
                progress.update(task, completed=True)

            # Step 2: Transform data
            task = progress.add_task("Step 2/4: Transforming data...", total=None)

            try:
                # Combine source files for this domain
                combined_df = pd.concat(
                    [self.source_data[f] for f in source_files],
                    ignore_index=True
                )

                # Get transformer
                transformer = get_transformer(
                    domain_code=domain,
                    study_id=self.study_id,
                    mapping_spec=self.mapping_specs.get(domain)
                )

                # Transform
                sdtm_df = transformer.transform(combined_df)
                self.sdtm_data[domain] = sdtm_df

                progress.update(task, description=f"Step 2/4: Transformed {len(sdtm_df)} records")

            except Exception as e:
                self.console.print(f"[red]Transformation error: {e}[/red]")
                return

            # Step 3: Validate
            task = progress.add_task("Step 3/4: Validating SDTM data...", total=None)

            result = self.validator.validate_domain(sdtm_df, domain)
            self.validation_results[domain] = result

            progress.update(task, description=f"Step 3/4: Validation complete - {'✓ Valid' if result.is_valid else '✗ Issues found'}")

            # Step 4: Summary
            task = progress.add_task("Step 4/4: Generating summary...", total=None)
            progress.update(task, description="[green]Conversion complete![/green]")

        # Show results
        self._show_conversion_result(domain, sdtm_df, result)

    def _show_conversion_result(self, domain: str, df: pd.DataFrame, validation_result):
        """Show conversion results."""
        self.console.print()

        # Summary panel
        status_color = "green" if validation_result.is_valid else "red"
        status_text = "VALID" if validation_result.is_valid else "ISSUES FOUND"

        summary = f"""
[bold]Domain:[/bold] {domain}
[bold]Records:[/bold] {len(df)}
[bold]Variables:[/bold] {len(df.columns)}
[bold]Status:[/bold] [{status_color}]{status_text}[/{status_color}]
[bold]Errors:[/bold] {validation_result.error_count}
[bold]Warnings:[/bold] {validation_result.warning_count}
        """
        self.console.print(Panel(summary.strip(), title="[bold green]Conversion Complete[/bold green]"))

        # Show sample data
        self.console.print()
        self.console.print("[bold]Sample SDTM Output:[/bold]")

        table = Table(box=box.SIMPLE)
        cols_to_show = ['STUDYID', 'DOMAIN', 'USUBJID'] + [c for c in df.columns if c not in ['STUDYID', 'DOMAIN', 'USUBJID']][:7]

        for col in cols_to_show:
            if col in df.columns:
                table.add_column(col, style="cyan", max_width=15)

        for _, row in df.head(5).iterrows():
            table.add_row(*[str(row.get(c, ''))[:15] for c in cols_to_show if c in df.columns])

        self.console.print(table)

        # Show validation issues
        if validation_result.issues:
            self.console.print()
            self.console.print("[bold]Validation Issues:[/bold]")
            for issue in validation_result.issues[:5]:
                severity_color = "red" if issue.severity.value == "error" else "yellow"
                kb_tag = "[KB] " if issue.rule_id.startswith("KB-") else ""
                self.console.print(f"  [{severity_color}]{issue.severity.value.upper()}[/{severity_color}] {kb_tag}{issue.message}")

            if len(validation_result.issues) > 5:
                self.console.print(f"  [dim]... and {len(validation_result.issues) - 5} more issues[/dim]")

    async def convert_all(self):
        """Convert all available domains."""
        if not self.source_data:
            self.console.print("[yellow]No data loaded. Use /load first.[/yellow]")
            return

        # Get unique domains (excluding UNKNOWN and SUPP domains for now)
        domains = sorted(set(
            d for d in self.domain_mapping.values()
            if d != "UNKNOWN" and not d.startswith("SUPP")
        ))

        self.console.print(Panel(f"[bold]Converting All Domains ({len(domains)} domains)[/bold]"))
        self.console.print(f"Domains: {', '.join(domains)}")
        self.console.print()

        for domain in domains:
            try:
                await self.convert_domain(domain)
                self.console.print()
            except Exception as e:
                self.console.print(f"[red]Error converting {domain}: {e}[/red]")

        # Show final summary
        self._show_final_summary()

    def _show_final_summary(self):
        """Show final conversion summary."""
        self.console.print(Panel("[bold]Conversion Summary[/bold]"))

        table = Table(box=box.ROUNDED)
        table.add_column("Domain", style="bold")
        table.add_column("Records", justify="right")
        table.add_column("Status")
        table.add_column("Errors", justify="right")
        table.add_column("Warnings", justify="right")

        total_records = 0
        total_errors = 0
        total_warnings = 0

        for domain, df in sorted(self.sdtm_data.items()):
            result = self.validation_results.get(domain)
            status = "[green]✓[/green]" if result and result.is_valid else "[red]✗[/red]"
            errors = result.error_count if result else 0
            warnings = result.warning_count if result else 0

            table.add_row(domain, str(len(df)), status, str(errors), str(warnings))

            total_records += len(df)
            total_errors += errors
            total_warnings += warnings

        self.console.print(table)
        self.console.print(f"\n[bold]Total:[/bold] {len(self.sdtm_data)} domains, {total_records} records, {total_errors} errors, {total_warnings} warnings")

    def validate_domain(self, domain: str):
        """Validate a specific domain."""
        domain = domain.upper()

        if domain not in self.sdtm_data:
            self.console.print(f"[red]Domain {domain} not converted yet. Use /convert {domain} first.[/red]")
            return

        self.console.print(Panel(f"[bold]Validating {domain} Domain[/bold]"))

        df = self.sdtm_data[domain]
        result = self.validator.validate_domain(df, domain)
        self.validation_results[domain] = result

        self._show_validation_result(domain, result)

    def _show_validation_result(self, domain: str, result):
        """Show detailed validation result."""
        status = "[green]VALID[/green]" if result.is_valid else "[red]INVALID[/red]"

        self.console.print(f"\n[bold]Domain:[/bold] {domain}")
        self.console.print(f"[bold]Status:[/bold] {status}")
        self.console.print(f"[bold]Records:[/bold] {result.total_records}")
        self.console.print(f"[bold]Errors:[/bold] {result.error_count}")
        self.console.print(f"[bold]Warnings:[/bold] {result.warning_count}")

        if result.issues:
            self.console.print()

            # Group by severity
            errors = [i for i in result.issues if i.severity.value == "error"]
            warnings = [i for i in result.issues if i.severity.value == "warning"]

            if errors:
                self.console.print("[bold red]Errors:[/bold red]")
                for issue in errors:
                    kb = "[KB] " if issue.rule_id.startswith("KB-") else ""
                    self.console.print(f"  [red]•[/red] [{issue.rule_id}] {kb}{issue.message}")

            if warnings:
                self.console.print("[bold yellow]Warnings:[/bold yellow]")
                for issue in warnings[:10]:
                    kb = "[KB] " if issue.rule_id.startswith("KB-") else ""
                    self.console.print(f"  [yellow]•[/yellow] [{issue.rule_id}] {kb}{issue.message}")

                if len(warnings) > 10:
                    self.console.print(f"  [dim]... and {len(warnings) - 10} more warnings[/dim]")

    def show_report(self):
        """Show full validation report."""
        if not self.validation_results:
            self.console.print("[yellow]No validation results. Convert and validate domains first.[/yellow]")
            return

        results = list(self.validation_results.values())
        report = self.validator.generate_report(results)

        self.console.print(Panel("[bold]SDTM Validation Report[/bold]"))

        # Summary
        self.console.print(f"[bold]Study ID:[/bold] {report['study_id']}")
        self.console.print(f"[bold]Generated:[/bold] {report['generated_at']}")
        self.console.print(f"[bold]Submission Ready:[/bold] {'[green]YES[/green]' if report['submission_ready'] else '[red]NO[/red]'}")
        self.console.print()

        # Summary table
        summary = report['summary']
        self.console.print("[bold]Summary:[/bold]")
        self.console.print(f"  Domains Validated: {summary['domains_validated']}")
        self.console.print(f"  Total Records: {summary['total_records']}")
        self.console.print(f"  Total Errors: {summary['total_errors']}")
        self.console.print(f"  Total Warnings: {summary['total_warnings']}")

        # Knowledge tools info
        kt = report.get('knowledge_tools', {})
        if kt.get('enabled'):
            self.console.print()
            self.console.print("[bold]Knowledge Tools:[/bold]")
            self.console.print(f"  Rules Retrieved: {kt.get('rules_retrieved', 0)}")
            self.console.print(f"  Domains with KB Rules: {', '.join(kt.get('domains_with_kb_rules', []))}")

    async def search_guidelines(self, query: str):
        """Search SDTM guidelines using Tavily."""
        if not self.knowledge_retriever:
            self.console.print("[red]Knowledge tools not available.[/red]")
            return

        self.console.print(Panel(f"[bold]Searching: {query}[/bold]"))

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Searching CDISC/FDA guidelines...", total=None)

            results = self.knowledge_retriever.search_web(query, max_results=5)

            progress.update(task, description=f"[green]Found {len(results)} results[/green]")

        if results:
            for i, r in enumerate(results, 1):
                self.console.print(f"\n[bold cyan]{i}. {r.get('title', 'No title')}[/bold cyan]")
                self.console.print(f"   [dim]{r.get('url', '')}[/dim]")
                content = r.get('content', '')[:200]
                self.console.print(f"   {content}...")
        else:
            self.console.print("[yellow]No results found.[/yellow]")

    async def get_rules(self, domain: str):
        """Get business rules for a domain from Pinecone."""
        if not self.knowledge_retriever:
            self.console.print("[red]Knowledge tools not available.[/red]")
            return

        domain = domain.upper()
        self.console.print(Panel(f"[bold]Business Rules for {domain}[/bold]"))

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Retrieving from Pinecone...", total=None)

            rules = self.knowledge_retriever.get_business_rules(domain)

            progress.update(task, description=f"[green]Found {len(rules)} rules[/green]")

        if rules:
            for i, rule in enumerate(rules[:10], 1):
                rule_id = rule.get('rule_id', rule.get('id', f'Rule {i}'))
                desc = rule.get('description', rule.get('content', str(rule)))[:100]
                self.console.print(f"  [cyan]{rule_id}[/cyan]: {desc}")
        else:
            self.console.print("[yellow]No rules found in knowledge base.[/yellow]")

    def show_status(self):
        """Show current pipeline status."""
        self.console.print(Panel("[bold]Pipeline Status[/bold]"))

        self.console.print(f"[bold]Study ID:[/bold] {self.study_id}")
        self.console.print(f"[bold]Source Files Loaded:[/bold] {len(self.source_data)}")
        self.console.print(f"[bold]Domains Converted:[/bold] {len(self.sdtm_data)}")
        self.console.print(f"[bold]Domains Validated:[/bold] {len(self.validation_results)}")

        if self.sdtm_data:
            self.console.print()
            self.console.print("[bold]Converted Domains:[/bold]")
            for domain, df in self.sdtm_data.items():
                result = self.validation_results.get(domain)
                status = "[green]✓[/green]" if result and result.is_valid else "[yellow]○[/yellow]"
                self.console.print(f"  {status} {domain}: {len(df)} records")

    async def process_command(self, user_input: str) -> bool:
        """Process a user command. Returns False if should quit."""
        user_input = user_input.strip()

        if not user_input:
            return True

        # Parse command
        parts = user_input.split(maxsplit=2)
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        try:
            if cmd in ["/quit", "/exit", "/q"]:
                self.console.print("[bold]Goodbye![/bold]")
                return False

            elif cmd == "/help":
                self.print_help()

            elif cmd == "/load":
                if args:
                    source = args[0].lower()
                    path = args[1] if len(args) > 1 else None
                    await self.load_data(source, path)
                else:
                    self.console.print("[yellow]Usage: /load local <path> OR /load s3[/yellow]")

            elif cmd == "/domains":
                self.show_domains()

            elif cmd == "/preview":
                if args:
                    self.preview_file(args[0])
                else:
                    self.console.print("[yellow]Usage: /preview <filename>[/yellow]")

            elif cmd == "/mapping":
                if args:
                    await self.generate_mapping(args[0])
                else:
                    self.console.print("[yellow]Usage: /mapping <domain>[/yellow]")

            elif cmd == "/convert":
                if args:
                    if args[0].lower() == "all":
                        await self.convert_all()
                    else:
                        await self.convert_domain(args[0])
                else:
                    self.console.print("[yellow]Usage: /convert <domain> OR /convert all[/yellow]")

            elif cmd == "/validate":
                if args:
                    if args[0].lower() == "all":
                        for domain in self.sdtm_data:
                            self.validate_domain(domain)
                    else:
                        self.validate_domain(args[0])
                else:
                    self.console.print("[yellow]Usage: /validate <domain> OR /validate all[/yellow]")

            elif cmd == "/report":
                self.show_report()

            elif cmd == "/search":
                if args:
                    query = " ".join(args)
                    await self.search_guidelines(query)
                else:
                    self.console.print("[yellow]Usage: /search <query>[/yellow]")

            elif cmd == "/rules":
                if args:
                    await self.get_rules(args[0])
                else:
                    self.console.print("[yellow]Usage: /rules <domain>[/yellow]")

            elif cmd == "/status":
                self.show_status()

            elif cmd == "/clear":
                self.source_data.clear()
                self.sdtm_data.clear()
                self.mapping_specs.clear()
                self.validation_results.clear()
                self.console.print("[green]All data cleared.[/green]")

            elif cmd.startswith("/"):
                self.console.print(f"[red]Unknown command: {cmd}. Type /help for available commands.[/red]")

            else:
                # Natural language input - could be extended with LLM
                self.console.print("[dim]Tip: Use commands starting with / (type /help for list)[/dim]")

        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

        return True

    async def run(self):
        """Run the interactive chat loop."""
        self.print_header()

        while True:
            try:
                user_input = self.console.input("\n[bold blue]SDTM>[/bold blue] ")
                should_continue = await self.process_command(user_input)
                if not should_continue:
                    break
            except KeyboardInterrupt:
                self.console.print("\n[bold]Use /quit to exit[/bold]")
            except EOFError:
                break


async def main():
    """Main entry point."""
    agent = SDTMChatAgent()
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
