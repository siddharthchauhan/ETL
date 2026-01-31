"""
SDTM Mapping Engine
===================
Dynamic mapping specification parser and transformation executor.

This module provides a flexible, rule-based transformation engine that:
1. Parses mapping specification files (Excel/CSV)
2. Interprets transformation rules/DSL
3. Executes transformations based on specifications

Supported Transformation Functions:
- ASSIGN(value) - Assign constant value
- CONCAT(a, b, ...) - Concatenate multiple values
- SUBSTR(field, start, length) - Extract substring
- IF(condition, true_val, false_val) - Conditional logic
- ISO8601DATEFORMAT(field, format) - Date formatting
- ISO8601DATETIMEFORMATS(field, format1, format2, ...) - Multi-format date parsing
- FORMAT(field, codelist) - Apply codelist/format
- UPCASE(field) - Convert to uppercase
- LOWERCASE(field) - Convert to lowercase
- TRIM(field) - Remove whitespace
- COMPRESS(field, pattern) - Remove characters
- set to VARIABLE - Direct column mapping

Author: SDTM ETL Pipeline
Version: 1.0.0
"""

import os
import re
import asyncio
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache

import pandas as pd
import numpy as np

from .async_utils import async_read_csv


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class VariableMapping:
    """Represents a single variable mapping specification."""
    variable: str                      # Target SDTM variable name
    variable_order: int               # Order in the domain
    label: str                        # Variable label
    data_type: str                    # Target data type (string, integer, float)
    length: Optional[int]             # Maximum length
    controlled_terms: Optional[str]   # CT codelist or format name
    origin: Optional[str]             # Data origin
    role: str                         # SDTM role (Identifier, Topic, etc.)
    core: str                         # Core status (req, exp, perm)
    source_datasets: List[str]        # Source dataset(s)
    source_variables: List[str]       # Source variable(s)
    source_datatypes: List[str]       # Source data type(s)
    rule: str                         # Transformation rule/expression
    comments: Optional[str] = None    # Additional comments


@dataclass
class DomainMapping:
    """Represents a complete domain mapping specification."""
    domain: str                       # SDTM domain code (DM, AE, VS, etc.)
    label: str                        # Domain label
    variables: List[VariableMapping]  # List of variable mappings
    source_datasets: List[str]        # All source datasets used
    notes: Optional[str] = None       # Domain-level notes


@dataclass
class MappingSpecification:
    """Complete mapping specification for a study."""
    study_id: str
    sponsor: str
    protocol: str
    domains: Dict[str, DomainMapping]
    raw_datasets: Dict[str, Dict[str, Any]]  # Raw dataset definitions
    global_info: Dict[str, Any]              # Global conversion settings
    codelists: Dict[str, Dict[str, str]]     # Format/codelist mappings


# =============================================================================
# MAPPING SPECIFICATION PARSER
# =============================================================================

class MappingSpecificationParser:
    """
    Parses SDTM mapping specification files.

    Supports:
    - Excel (.xls, .xlsx) with multiple sheets per domain
    - CSV files with structured format
    """

    # Standard column mappings (flexible to handle variations)
    COLUMN_ALIASES = {
        'variable': ['Variable', 'Variable Name', 'VARIABLE', 'Var'],
        'variable_order': ['Variable Order', 'Order', 'Seq', 'VAR ORDER'],
        'label': ['Label', 'Variable Label', 'LABEL', 'Description'],
        'data_type': ['Type', 'Data Type', 'DataType', 'TYPE'],
        'length': ['Length', 'LEN', 'Max Length'],
        'controlled_terms': ['Controlled Terms Or Formats', 'CT', 'Codelist', 'Format'],
        'origin': ['Origin', 'ORIGIN', 'Data Origin'],
        'role': ['Role', 'ROLE', 'Variable Role'],
        'core': ['Core', 'CORE', 'Core Status'],
        'source_dataset': ['Source Dataset', 'Source', 'SRC Dataset'],
        'source_variable': ['Source Variable', 'Source Var', 'SRC Variable'],
        'source_datatype': ['Source DataType', 'Source Type', 'SRC DataType'],
        'rule': ['Rule/Conversion Details', 'Rule', 'Conversion', 'Mapping Rule', 'Algorithm'],
        'comments': ['Comments', 'Notes', 'Reviewer Comments'],
    }

    # All 63 SDTM domains organized by class (SDTM-IG 3.4)
    DOMAIN_SHEETS = [
        # Special Purpose Domains (4)
        'CO',   # Comments
        'DM',   # Demographics
        'SE',   # Subject Elements
        'SV',   # Subject Visits

        # Interventions Domains (7)
        'AG',   # Procedure Agents
        'CM',   # Concomitant Medications
        'EC',   # Exposure as Collected
        'EX',   # Exposure
        'ML',   # Meals
        'PR',   # Procedures
        'SU',   # Substance Use

        # Events Domains (6)
        'AE',   # Adverse Events
        'CE',   # Clinical Events
        'DS',   # Disposition
        'DV',   # Protocol Deviations
        'HO',   # Healthcare Encounters
        'MH',   # Medical History

        # Findings Domains (37)
        'BE',   # Biospecimen Events
        'BM',   # Bone Measurements
        'BS',   # Biospecimen Findings
        'CP',   # Cell Phenotyping
        'CV',   # Cardiovascular System Findings
        'DA',   # Drug Accountability
        'DD',   # Death Details
        'EG',   # ECG Test Results
        'FA',   # Findings About Events or Interventions
        'FT',   # Functional Tests
        'GF',   # Genomics Findings
        'IE',   # Inclusion/Exclusion Criteria Not Met
        'IS',   # Immunogenicity Specimen Assessments
        'LB',   # Laboratory Test Results
        'MB',   # Microbiology Specimen
        'MI',   # Microscopic Findings
        'MK',   # Musculoskeletal System Findings
        'MO',   # Morphology
        'MS',   # Microbiology Susceptibility
        'NV',   # Nervous System Findings
        'OE',   # Ophthalmic Examinations
        'OX',   # Oxygen Saturation Measurements
        'PC',   # Pharmacokinetics Concentrations
        'PE',   # Physical Examination
        'PI',   # Principal Investigator
        'PP',   # Pharmacokinetics Parameters
        'QS',   # Questionnaires
        'RE',   # Respiratory System Findings
        'RP',   # Reproductive System Findings
        'RS',   # Disease Response and Clinical Classification
        'SC',   # Subject Characteristics
        'SK',   # Skin Findings
        'SS',   # Subject Status
        'TR',   # Tumor/Lesion Results
        'TU',   # Tumor/Lesion Identification
        'UR',   # Urinary System Findings
        'VS',   # Vital Signs

        # Trial Design Domains (7)
        'TA',   # Trial Arms
        'TD',   # Trial Disease Assessments
        'TE',   # Trial Elements
        'TI',   # Trial Inclusion/Exclusion Criteria
        'TM',   # Trial Disease Milestones
        'TS',   # Trial Summary
        'TV',   # Trial Visits

        # Relationship Domain (1)
        'RELREC',  # Related Records

        # Device Domains (1)
        'DI',   # Device Identifiers
        'DO',   # Device Properties
        'DR',   # Device-Subject Relationships
        'DX',   # Device Events

        # Associated Persons Domains
        'APSC', # Associated Persons Subject Characteristics
        'APDM', # Associated Persons Demographics
        'APFA', # Associated Persons Findings About
        'APMH', # Associated Persons Medical History

        # Supplemental Qualifier Domains (SUPP--)
        # These are dynamically matched with startswith('SUPP')
        'SUPPAE', 'SUPPBE', 'SUPPCM', 'SUPPCO', 'SUPPDA', 'SUPPDD',
        'SUPPDM', 'SUPPDS', 'SUPPDV', 'SUPPEC', 'SUPPEG', 'SUPPEX',
        'SUPPFA', 'SUPPFT', 'SUPPGF', 'SUPPHO', 'SUPPIE', 'SUPPIS',
        'SUPPLB', 'SUPPMB', 'SUPPMI', 'SUPPMH', 'SUPPML', 'SUPPMO',
        'SUPPMS', 'SUPPNV', 'SUPPOE', 'SUPPOX', 'SUPPPC', 'SUPPPE',
        'SUPPPP', 'SUPPPR', 'SUPPQS', 'SUPPRE', 'SUPPRP', 'SUPPRS',
        'SUPPSC', 'SUPPSK', 'SUPPSS', 'SUPPSU', 'SUPPTR', 'SUPPTU',
        'SUPPUR', 'SUPPVS',
    ]

    def __init__(self):
        self.codelists: Dict[str, Dict[str, str]] = {}

    async def parse_excel(self, file_path: str) -> MappingSpecification:
        """
        Parse an Excel mapping specification file.

        Args:
            file_path: Path to the Excel file

        Returns:
            MappingSpecification object
        """
        # Read Excel file in thread to avoid blocking
        xl = await asyncio.to_thread(pd.ExcelFile, file_path)

        # Extract global information
        global_info = await self._parse_global_info(xl)

        # Extract raw dataset definitions
        raw_datasets = await self._parse_raw_datasets(xl)

        # Parse each domain sheet
        domains = {}
        for sheet in xl.sheet_names:
            if sheet.upper() in self.DOMAIN_SHEETS or sheet.upper().startswith('SUPP'):
                domain_mapping = await self._parse_domain_sheet(xl, sheet)
                if domain_mapping:
                    domains[domain_mapping.domain] = domain_mapping

        return MappingSpecification(
            study_id=global_info.get('study_id', 'UNKNOWN'),
            sponsor=global_info.get('sponsor', ''),
            protocol=global_info.get('protocol', ''),
            domains=domains,
            raw_datasets=raw_datasets,
            global_info=global_info,
            codelists=self.codelists,
        )

    async def _parse_global_info(self, xl: pd.ExcelFile) -> Dict[str, Any]:
        """Parse global information from Title Page or Global Information sheets."""
        global_info = {}

        for sheet_name in ['Title Page', 'Global Information', 'Study Info']:
            if sheet_name in xl.sheet_names:
                df = await asyncio.to_thread(pd.read_excel, xl, sheet_name=sheet_name, header=None)

                # Extract key-value pairs
                for _, row in df.iterrows():
                    for i, cell in enumerate(row):
                        if pd.notna(cell):
                            cell_str = str(cell).upper()
                            if 'SPONSOR' in cell_str and i + 1 < len(row):
                                global_info['sponsor'] = str(row.iloc[i + 1]) if pd.notna(row.iloc[i + 1]) else ''
                            elif 'PROTOCOL' in cell_str and 'NUMBER' in cell_str and i + 1 < len(row):
                                global_info['protocol'] = str(row.iloc[i + 1]) if pd.notna(row.iloc[i + 1]) else ''
                            elif 'STUDY' in cell_str and 'ID' in cell_str and i + 1 < len(row):
                                global_info['study_id'] = str(row.iloc[i + 1]) if pd.notna(row.iloc[i + 1]) else ''
                break

        return global_info

    async def _parse_raw_datasets(self, xl: pd.ExcelFile) -> Dict[str, Dict[str, Any]]:
        """Parse raw dataset definitions."""
        raw_datasets = {}

        if 'Raw Datasets' in xl.sheet_names:
            df = await asyncio.to_thread(pd.read_excel, xl, sheet_name='Raw Datasets', header=None)

            # Find header row
            header_row = self._find_header_row(df, ['Dataset', 'Source Dataset'])
            if header_row is not None:
                df.columns = df.iloc[header_row].values
                df = df.iloc[header_row + 1:].reset_index(drop=True)

                for _, row in df.iterrows():
                    ds_name = self._get_column_value(row, ['Source Dataset', 'Dataset'])
                    if pd.notna(ds_name) and ds_name:
                        raw_datasets[str(ds_name)] = {
                            'label': self._get_column_value(row, ['Label']),
                            'target': self._get_column_value(row, ['Target Dataset']),
                        }

        return raw_datasets

    async def _parse_domain_sheet(self, xl: pd.ExcelFile, sheet_name: str) -> Optional[DomainMapping]:
        """Parse a single domain mapping sheet."""
        df = await asyncio.to_thread(pd.read_excel, xl, sheet_name=sheet_name, header=None)

        # Find header row containing mapping columns
        header_row = self._find_header_row(df, ['Variable', 'Source Dataset', 'Rule'])
        if header_row is None:
            return None

        # Set header and filter data
        df.columns = df.iloc[header_row].values
        df = df.iloc[header_row + 1:].reset_index(drop=True)

        # Extract domain name from sheet or data
        domain = sheet_name.upper()

        # Parse variable mappings
        variables = []
        source_datasets = set()

        for _, row in df.iterrows():
            var_name = self._get_column_value(row, self.COLUMN_ALIASES['variable'])
            if pd.isna(var_name) or not var_name:
                continue

            # Parse source datasets and variables (can be comma-separated)
            src_ds = self._get_column_value(row, self.COLUMN_ALIASES['source_dataset']) or ''
            src_var = self._get_column_value(row, self.COLUMN_ALIASES['source_variable']) or ''
            src_dtype = self._get_column_value(row, self.COLUMN_ALIASES['source_datatype']) or ''

            src_datasets_list = [s.strip() for s in str(src_ds).split(',') if s.strip()]
            src_vars_list = [s.strip() for s in str(src_var).split(',') if s.strip()]
            src_dtypes_list = [s.strip() for s in str(src_dtype).split(',') if s.strip()]

            source_datasets.update(src_datasets_list)

            # Get transformation rule
            rule = self._get_column_value(row, self.COLUMN_ALIASES['rule']) or ''

            # Parse order
            order_val = self._get_column_value(row, self.COLUMN_ALIASES['variable_order'])
            try:
                var_order = int(order_val) if pd.notna(order_val) else 0
            except (ValueError, TypeError):
                var_order = 0

            # Parse length
            len_val = self._get_column_value(row, self.COLUMN_ALIASES['length'])
            try:
                var_length = int(len_val) if pd.notna(len_val) else None
            except (ValueError, TypeError):
                var_length = None

            mapping = VariableMapping(
                variable=str(var_name).strip(),
                variable_order=var_order,
                label=str(self._get_column_value(row, self.COLUMN_ALIASES['label']) or ''),
                data_type=str(self._get_column_value(row, self.COLUMN_ALIASES['data_type']) or 'string'),
                length=var_length,
                controlled_terms=self._get_column_value(row, self.COLUMN_ALIASES['controlled_terms']),
                origin=self._get_column_value(row, self.COLUMN_ALIASES['origin']),
                role=str(self._get_column_value(row, self.COLUMN_ALIASES['role']) or ''),
                core=str(self._get_column_value(row, self.COLUMN_ALIASES['core']) or 'perm'),
                source_datasets=src_datasets_list,
                source_variables=src_vars_list,
                source_datatypes=src_dtypes_list,
                rule=str(rule),
                comments=self._get_column_value(row, self.COLUMN_ALIASES['comments']),
            )
            variables.append(mapping)

        if not variables:
            return None

        # Sort by variable order
        variables.sort(key=lambda v: v.variable_order)

        return DomainMapping(
            domain=domain,
            label=f"{domain} Domain",
            variables=variables,
            source_datasets=list(source_datasets),
        )

    def _find_header_row(self, df: pd.DataFrame, keywords: List[str]) -> Optional[int]:
        """Find the row containing header columns."""
        for i, row in df.iterrows():
            row_str = ' '.join([str(x) for x in row.values if pd.notna(x)]).upper()
            if any(kw.upper() in row_str for kw in keywords):
                return i
        return None

    def _get_column_value(self, row: pd.Series, column_aliases: List[str]) -> Optional[str]:
        """Get value from row using multiple possible column names."""
        for alias in column_aliases:
            if alias in row.index:
                val = row[alias]
                if pd.notna(val):
                    return str(val).strip()
        return None


# =============================================================================
# TRANSFORMATION RULE INTERPRETER
# =============================================================================

class TransformationRuleInterpreter:
    """
    Interprets and executes transformation rules from mapping specifications.

    Supports a DSL (Domain Specific Language) with functions like:
    - ASSIGN("value")
    - CONCAT(a, b, c)
    - SUBSTR(field, start, len)
    - IF(condition, true_val, false_val)
    - ISO8601DATEFORMAT(field, format)
    - FORMAT(field, codelist)
    - UPCASE(field)
    - etc.
    """

    def __init__(self, codelists: Optional[Dict[str, Dict[str, str]]] = None):
        self.codelists = codelists or {}
        self.data_elements: Dict[str, Any] = {}  # For ASSIGNDATAELEMENT lookups

        # Register built-in functions
        self.functions: Dict[str, Callable] = {
            'ASSIGN': self._func_assign,
            'CONCAT': self._func_concat,
            'SUBSTR': self._func_substr,
            'IF': self._func_if,
            'ISO8601DATEFORMAT': self._func_iso8601_date,
            'ISO8601DATETIMEFORMATS': self._func_iso8601_datetime_multi,
            'FORMAT': self._func_format,
            'UPCASE': self._func_upcase,
            'LOWERCASE': self._func_lowercase,
            'TRIM': self._func_trim,
            'COMPRESS': self._func_compress,
            'ASSIGNDATAELEMENT': self._func_assign_data_element,
            'MULTIPLE_DIFFDATE_FRMTS': self._func_date_diff,
        }

    def interpret(
        self,
        rule: str,
        source_data: Dict[str, pd.DataFrame],
        row_idx: int,
        mapping: VariableMapping,
    ) -> Any:
        """
        Interpret and execute a transformation rule.

        Args:
            rule: The transformation rule string
            source_data: Dictionary of source DataFrames keyed by dataset name
            row_idx: Current row index in the source data
            mapping: The variable mapping specification

        Returns:
            Transformed value
        """
        if not rule or pd.isna(rule):
            return None

        rule = str(rule).strip()

        # Handle "set to VARIABLE" pattern
        if rule.lower().startswith('set to '):
            var_name = rule[7:].strip().rstrip('.')
            return self._get_source_value(var_name, source_data, row_idx, mapping)

        # Handle direct function calls
        if '(' in rule:
            return self._execute_function(rule, source_data, row_idx, mapping)

        # Handle direct variable reference
        if mapping.source_variables:
            return self._get_source_value(
                mapping.source_variables[0],
                source_data,
                row_idx,
                mapping
            )

        return None

    def _execute_function(
        self,
        expr: str,
        source_data: Dict[str, pd.DataFrame],
        row_idx: int,
        mapping: VariableMapping,
    ) -> Any:
        """Execute a function expression."""
        # Parse function name and arguments
        match = re.match(r'(\w+)\s*\((.*)\)', expr, re.DOTALL)
        if not match:
            return expr

        func_name = match.group(1).upper()
        args_str = match.group(2)

        if func_name not in self.functions:
            # Unknown function, return as-is
            return expr

        # Parse arguments (handle nested functions and quoted strings)
        args = self._parse_arguments(args_str, source_data, row_idx, mapping)

        # Execute function
        return self.functions[func_name](args, source_data, row_idx, mapping)

    def _parse_arguments(
        self,
        args_str: str,
        source_data: Dict[str, pd.DataFrame],
        row_idx: int,
        mapping: VariableMapping,
    ) -> List[Any]:
        """Parse function arguments, handling nested functions and quotes."""
        args = []
        current = ""
        depth = 0
        in_string = False
        string_char = None

        for char in args_str:
            if char in ('"', "'") and not in_string:
                in_string = True
                string_char = char
                current += char
            elif char == string_char and in_string:
                in_string = False
                string_char = None
                current += char
            elif char == '(' and not in_string:
                depth += 1
                current += char
            elif char == ')' and not in_string:
                depth -= 1
                current += char
            elif char == ',' and depth == 0 and not in_string:
                args.append(self._evaluate_argument(current.strip(), source_data, row_idx, mapping))
                current = ""
            else:
                current += char

        if current.strip():
            args.append(self._evaluate_argument(current.strip(), source_data, row_idx, mapping))

        return args

    def _evaluate_argument(
        self,
        arg: str,
        source_data: Dict[str, pd.DataFrame],
        row_idx: int,
        mapping: VariableMapping,
    ) -> Any:
        """Evaluate a single argument."""
        arg = arg.strip()

        # Quoted string
        if (arg.startswith('"') and arg.endswith('"')) or (arg.startswith("'") and arg.endswith("'")):
            return arg[1:-1]

        # Numeric literal
        try:
            if '.' in arg:
                return float(arg)
            return int(arg)
        except ValueError:
            pass

        # Nested function
        if '(' in arg:
            return self._execute_function(arg, source_data, row_idx, mapping)

        # Variable reference (DATASET.VARIABLE)
        if '.' in arg:
            return self._get_source_value(arg, source_data, row_idx, mapping)

        # Simple variable name - use from mapping's source datasets
        return self._get_source_value(arg, source_data, row_idx, mapping)

    def _get_source_value(
        self,
        var_ref: str,
        source_data: Dict[str, pd.DataFrame],
        row_idx: int,
        mapping: VariableMapping,
    ) -> Any:
        """Get a value from source data."""
        var_ref = str(var_ref).strip()

        # Handle DATASET.VARIABLE format
        if '.' in var_ref:
            parts = var_ref.split('.', 1)
            ds_name = parts[0].strip()
            var_name = parts[1].strip()

            if ds_name in source_data and var_name in source_data[ds_name].columns:
                if row_idx < len(source_data[ds_name]):
                    return source_data[ds_name].iloc[row_idx][var_name]

        # Try mapping's source datasets
        for ds_name in mapping.source_datasets:
            if ds_name in source_data and var_ref in source_data[ds_name].columns:
                if row_idx < len(source_data[ds_name]):
                    return source_data[ds_name].iloc[row_idx][var_ref]

        # Try all datasets
        for ds_name, df in source_data.items():
            if var_ref in df.columns:
                if row_idx < len(df):
                    return df.iloc[row_idx][var_ref]

        return None

    # =========================================================================
    # BUILT-IN FUNCTIONS
    # =========================================================================

    def _func_assign(self, args: List[Any], *_) -> Any:
        """ASSIGN("value") - Return constant value."""
        return args[0] if args else None

    def _func_concat(self, args: List[Any], *_) -> str:
        """CONCAT(a, b, ...) - Concatenate values."""
        return ''.join(str(a) if pd.notna(a) else '' for a in args)

    def _func_substr(self, args: List[Any], *_) -> str:
        """SUBSTR(field, start, length) - Extract substring."""
        if len(args) < 3:
            return str(args[0]) if args else ''

        value = str(args[0]) if pd.notna(args[0]) else ''
        start = int(args[1]) - 1  # Convert to 0-based index
        length = int(args[2])

        return value[start:start + length]

    def _func_if(self, args: List[Any], source_data, row_idx, mapping) -> Any:
        """IF(condition, true_val, false_val) - Conditional logic."""
        if len(args) < 3:
            return None

        condition = args[0]
        true_val = args[1]
        false_val = args[2]

        # Evaluate condition
        if isinstance(condition, str):
            # Parse condition expressions
            condition = self._evaluate_condition(condition, source_data, row_idx, mapping)

        return true_val if condition else false_val

    def _evaluate_condition(
        self,
        condition: str,
        source_data: Dict[str, pd.DataFrame],
        row_idx: int,
        mapping: VariableMapping,
    ) -> bool:
        """Evaluate a condition expression."""
        condition = str(condition).strip()

        # Handle boolean values
        if condition.lower() in ('true', '1'):
            return True
        if condition.lower() in ('false', '0', ''):
            return False

        # Handle comparison operators
        for op in ['==', '!=', '>=', '<=', '>', '<']:
            if op in condition:
                parts = condition.split(op, 1)
                left = self._evaluate_argument(parts[0].strip(), source_data, row_idx, mapping)
                right = self._evaluate_argument(parts[1].strip(), source_data, row_idx, mapping)

                # Convert to strings for comparison if needed
                left_str = str(left) if pd.notna(left) else ''
                right_str = str(right) if pd.notna(right) else ''

                if op == '==':
                    return left_str == right_str
                elif op == '!=':
                    return left_str != right_str
                elif op == '>=':
                    return float(left_str or 0) >= float(right_str or 0)
                elif op == '<=':
                    return float(left_str or 0) <= float(right_str or 0)
                elif op == '>':
                    return float(left_str or 0) > float(right_str or 0)
                elif op == '<':
                    return float(left_str or 0) < float(right_str or 0)

        # Handle OR (||)
        if '||' in condition:
            parts = condition.split('||')
            return any(self._evaluate_condition(p.strip(), source_data, row_idx, mapping) for p in parts)

        # Handle AND (&&)
        if '&&' in condition:
            parts = condition.split('&&')
            return all(self._evaluate_condition(p.strip(), source_data, row_idx, mapping) for p in parts)

        return bool(condition)

    def _func_iso8601_date(self, args: List[Any], *_) -> str:
        """ISO8601DATEFORMAT(field, format) - Convert to ISO 8601 date."""
        if not args:
            return ''

        value = args[0]
        if pd.isna(value) or value == '':
            return ''

        fmt = args[1] if len(args) > 1 else 'YYYYMMDD'

        return self._convert_to_iso8601(str(value), fmt)

    def _func_iso8601_datetime_multi(self, args: List[Any], *_) -> str:
        """ISO8601DATETIMEFORMATS(field, format1, format2, ...) - Try multiple formats."""
        if not args:
            return ''

        value = args[0]
        if pd.isna(value) or value == '':
            return ''

        formats = args[1:] if len(args) > 1 else ['YYYYMMDD']

        for fmt in formats:
            result = self._convert_to_iso8601(str(value), str(fmt))
            if result:
                return result

        return ''

    def _convert_to_iso8601(self, value: str, fmt: str) -> str:
        """Convert a date value to ISO 8601 format.

        Supports both explicit format hints and auto-detection fallback.
        Handles 2-digit year formats (M/D/YY, MM/DD/YY) and 6-digit YYYYMM.
        """
        value = str(value).strip()
        fmt = str(fmt).upper()

        if not value:
            return ''

        # Map format strings to Python strptime formats
        format_map = {
            'YYYYMMDD': '%Y%m%d',
            'YYYY-MM-DD': '%Y-%m-%d',
            'YYYYMM': '%Y%m',
            'YYYY-MM': '%Y-%m',
            'YYYY': '%Y',
            'DD-MON-YYYY': '%d-%b-%Y',
            'DD/MM/YYYY': '%d/%m/%Y',
            'MM/DD/YYYY': '%m/%d/%Y',
            'DD-MON-YY': '%d-%b-%y',
            'DD/MM/YY': '%d/%m/%y',
            'MM/DD/YY': '%m/%d/%y',
            'M/D/YY': '%m/%d/%y',
        }

        # Determine output precision from format
        partial_formats = {'YYYYMM', 'YYYY-MM'}
        year_only_formats = {'YYYY'}

        # Try the specified format first
        py_fmt = format_map.get(fmt)
        if py_fmt:
            try:
                dt = datetime.strptime(value, py_fmt)
                if fmt in year_only_formats:
                    return dt.strftime('%Y')
                elif fmt in partial_formats:
                    return dt.strftime('%Y-%m')
                else:
                    return dt.strftime('%Y-%m-%d')
            except (ValueError, TypeError):
                pass

        # Auto-detection fallback: try all known formats
        # Already ISO 8601
        if re.match(r'^\d{4}-\d{2}-\d{2}', value):
            return value[:10]
        if re.match(r'^\d{4}-\d{2}$', value):
            return value
        if re.match(r'^\d{4}$', value):
            return value

        # Numeric-only values
        if value.isdigit():
            if len(value) == 8:  # YYYYMMDD
                try:
                    return datetime.strptime(value, '%Y%m%d').strftime('%Y-%m-%d')
                except ValueError:
                    pass
            elif len(value) == 6:  # YYYYMM
                try:
                    return datetime.strptime(value, '%Y%m').strftime('%Y-%m')
                except ValueError:
                    pass

        # Try common formats (4-digit year, then 2-digit year)
        auto_formats = [
            '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d',
            '%m-%d-%Y', '%d-%b-%Y', '%d-%B-%Y',
            '%d %b %Y', '%b %d, %Y',
            '%m/%d/%y', '%d/%m/%y', '%d-%b-%y', '%m-%d-%y',
        ]
        for auto_fmt in auto_formats:
            try:
                dt = datetime.strptime(value, auto_fmt)
                return dt.strftime('%Y-%m-%d')
            except (ValueError, TypeError):
                continue

        # If nothing worked, return original if it looks like ISO 8601
        if re.match(r'^\d{4}(-\d{2}(-\d{2})?)?$', value):
            return value
        return ''

    def _func_format(self, args: List[Any], *_) -> str:
        """FORMAT(field, codelist) - Apply codelist/format mapping."""
        if len(args) < 2:
            return str(args[0]) if args else ''

        value = str(args[0]).strip() if pd.notna(args[0]) else ''
        codelist_name = str(args[1]).strip()

        # Look up in codelists
        if codelist_name in self.codelists:
            return self.codelists[codelist_name].get(value, value)

        return value

    def _func_upcase(self, args: List[Any], *_) -> str:
        """UPCASE(field) - Convert to uppercase."""
        return str(args[0]).upper() if args and pd.notna(args[0]) else ''

    def _func_lowercase(self, args: List[Any], *_) -> str:
        """LOWERCASE(field) - Convert to lowercase."""
        return str(args[0]).lower() if args and pd.notna(args[0]) else ''

    def _func_trim(self, args: List[Any], *_) -> str:
        """TRIM(field) - Remove leading/trailing whitespace."""
        return str(args[0]).strip() if args and pd.notna(args[0]) else ''

    def _func_compress(self, args: List[Any], *_) -> str:
        """COMPRESS(field, pattern) - Remove specified characters/pattern."""
        if not args:
            return ''

        value = str(args[0]) if pd.notna(args[0]) else ''
        pattern = str(args[1]) if len(args) > 1 else ''

        return value.replace(pattern, '')

    def _func_assign_data_element(self, args: List[Any], *_) -> Any:
        """ASSIGNDATAELEMENT(key) - Lookup from pre-computed data elements."""
        if not args:
            return None

        key = str(args[0])
        return self.data_elements.get(key)

    def _func_date_diff(self, args: List[Any], *_) -> str:
        """MULTIPLE_DIFFDATE_FRMTS(unit, date1, date2, format1, format2, ...) - Date difference."""
        # Simplified implementation
        if len(args) < 3:
            return ''

        unit = str(args[0]).upper()
        date1 = args[1]
        date2 = args[2]

        # For now, return empty string - full implementation would calculate difference
        return ''


# =============================================================================
# TRANSFORMATION ENGINE
# =============================================================================

class SDTMTransformationEngine:
    """
    Main transformation engine that orchestrates mapping-driven SDTM conversions.
    """

    def __init__(self):
        self.parser = MappingSpecificationParser()
        self.interpreter = TransformationRuleInterpreter()
        self._spec: Optional[MappingSpecification] = None

    async def load_specification(self, spec_path: str) -> MappingSpecification:
        """Load a mapping specification file."""
        self._spec = await self.parser.parse_excel(spec_path)
        self.interpreter.codelists = self._spec.codelists
        return self._spec

    async def transform_domain(
        self,
        domain: str,
        source_data: Dict[str, pd.DataFrame],
        study_id: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Transform source data to an SDTM domain using the loaded specification.

        Args:
            domain: Target SDTM domain code
            source_data: Dictionary of source DataFrames keyed by dataset name
            study_id: Study identifier (overrides spec if provided)

        Returns:
            Transformed SDTM DataFrame
        """
        if not self._spec:
            raise ValueError("No mapping specification loaded. Call load_specification first.")

        domain = domain.upper()
        if domain not in self._spec.domains:
            raise ValueError(f"Domain {domain} not found in mapping specification")

        domain_mapping = self._spec.domains[domain]

        # Determine number of output records
        primary_ds = domain_mapping.source_datasets[0] if domain_mapping.source_datasets else None
        num_records = len(source_data[primary_ds]) if primary_ds and primary_ds in source_data else 0

        if num_records == 0:
            return pd.DataFrame()

        # Initialize output DataFrame
        output_data = {}

        # Process each variable mapping
        for var_mapping in domain_mapping.variables:
            values = []

            for row_idx in range(num_records):
                value = self.interpreter.interpret(
                    var_mapping.rule,
                    source_data,
                    row_idx,
                    var_mapping,
                )
                values.append(value)

            output_data[var_mapping.variable] = values

        # Create DataFrame
        result = pd.DataFrame(output_data)

        # Apply study_id override if provided
        if study_id and 'STUDYID' in result.columns:
            result['STUDYID'] = study_id

        # Ensure column order matches specification
        ordered_cols = [vm.variable for vm in domain_mapping.variables if vm.variable in result.columns]
        other_cols = [c for c in result.columns if c not in ordered_cols]
        result = result[ordered_cols + other_cols]

        return result

    def get_domain_list(self) -> List[str]:
        """Get list of available domains in the specification."""
        if not self._spec:
            return []
        return list(self._spec.domains.keys())

    def get_domain_info(self, domain: str) -> Optional[Dict[str, Any]]:
        """Get information about a domain mapping."""
        if not self._spec or domain.upper() not in self._spec.domains:
            return None

        dm = self._spec.domains[domain.upper()]
        return {
            'domain': dm.domain,
            'label': dm.label,
            'num_variables': len(dm.variables),
            'source_datasets': dm.source_datasets,
            'variables': [
                {
                    'name': v.variable,
                    'label': v.label,
                    'core': v.core,
                    'role': v.role,
                }
                for v in dm.variables
            ],
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def load_mapping_spec(file_path: str) -> MappingSpecification:
    """
    Load a mapping specification file.

    Args:
        file_path: Path to the mapping specification file (.xls, .xlsx)

    Returns:
        MappingSpecification object
    """
    parser = MappingSpecificationParser()
    return await parser.parse_excel(file_path)


async def transform_with_spec(
    spec_path: str,
    domain: str,
    source_data: Dict[str, pd.DataFrame],
    study_id: Optional[str] = None,
) -> pd.DataFrame:
    """
    Transform source data to SDTM using a mapping specification.

    Args:
        spec_path: Path to the mapping specification file
        domain: Target SDTM domain code
        source_data: Dictionary of source DataFrames
        study_id: Optional study identifier override

    Returns:
        Transformed SDTM DataFrame
    """
    engine = SDTMTransformationEngine()
    await engine.load_specification(spec_path)
    return await engine.transform_domain(domain, source_data, study_id)
