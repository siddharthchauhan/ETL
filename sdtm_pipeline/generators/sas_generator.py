"""
SAS Code Generator
==================
Generates SAS code for SDTM transformations based on mapping specifications.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import os

from ..models.sdtm_models import MappingSpecification, ColumnMapping


class SASCodeGenerator:
    """
    Generates SAS programs for SDTM transformations.

    Creates production-ready SAS code following best practices:
    - Modular macro-based approach
    - Comprehensive logging
    - Error handling
    - Validation checks
    """

    def __init__(self, study_id: str, output_dir: str = "./sas_programs"):
        self.study_id = study_id
        self.output_dir = output_dir
        # Only create dir if it doesn't exist (avoid blocking in async contexts)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

    def generate_all(self, mappings: List[MappingSpecification]) -> Dict[str, str]:
        """
        Generate all SAS programs for given mappings.

        Args:
            mappings: List of mapping specifications

        Returns:
            Dictionary of program names to file paths
        """
        generated_files = {}

        # Generate setup program
        setup_path = self.generate_setup_program()
        generated_files["setup"] = setup_path

        # Generate domain programs
        for spec in mappings:
            domain_path = self.generate_domain_program(spec)
            generated_files[spec.target_domain] = domain_path

        # Generate master driver
        driver_path = self.generate_driver_program(mappings)
        generated_files["driver"] = driver_path

        return generated_files

    def generate_setup_program(self) -> str:
        """Generate setup/initialization SAS program."""
        code = f'''/*******************************************************************************
* Program:    setup.sas
* Purpose:    Initialize environment for SDTM transformations
* Study:      {self.study_id}
* Created:    {datetime.now().strftime("%Y-%m-%d")}
* Author:     SDTM Pipeline (Auto-generated)
********************************************************************************/

%let study = {self.study_id};
%let root = /clinical/&study;
%let rawdata = &root/rawdata;
%let sdtm = &root/sdtm;
%let programs = &root/programs;
%let logs = &root/logs;

/* Create library references */
libname raw "&rawdata" access=readonly;
libname sdtm "&sdtm";

/* Setup output options */
options mprint mlogic symbolgen;
options validvarname=upcase;
options nofmterr;

/* Macro for logging */
%macro log_step(step=, status=);
    %put NOTE: ================================================================;
    %put NOTE: Step: &step;
    %put NOTE: Status: &status;
    %put NOTE: Timestamp: %sysfunc(datetime(), datetime20.);
    %put NOTE: ================================================================;
%mend log_step;

/* Macro for date conversion to ISO 8601 */
%macro convert_to_iso(invar=, outvar=);
    length &outvar $20;
    if not missing(&invar) then do;
        if length(strip(put(&invar, best.))) = 8 then do;
            &outvar = put(input(put(&invar, 8.), yymmdd8.), e8601da.);
        end;
        else do;
            &outvar = put(&invar, e8601da.);
        end;
    end;
%mend convert_to_iso;

/* Macro for generating USUBJID */
%macro gen_usubjid(study=, site=, subj=);
    catx("-", &study, &site, &subj)
%mend gen_usubjid;

/* Macro for sequence number generation */
%macro gen_seq(domain=, sortvar=);
    proc sort data=&domain._temp;
        by usubjid &sortvar;
    run;

    data &domain._temp;
        set &domain._temp;
        by usubjid;
        if first.usubjid then &domain.seq = 0;
        &domain.seq + 1;
    run;
%mend gen_seq;

%log_step(step=Setup Complete, status=SUCCESS);
'''
        output_path = os.path.join(self.output_dir, "setup.sas")
        with open(output_path, 'w') as f:
            f.write(code)
        return output_path

    def generate_domain_program(self, spec: MappingSpecification) -> str:
        """Generate SAS program for a specific domain transformation."""
        domain = spec.target_domain
        source = spec.source_domain.replace(".csv", "").lower()

        # Build mapping code
        mapping_code = self._generate_mapping_code(spec)
        validation_code = self._generate_validation_code(spec)

        code = f'''/*******************************************************************************
* Program:    {domain.lower()}.sas
* Purpose:    Create SDTM {domain} domain from source data
* Study:      {spec.study_id}
* Source:     {spec.source_domain}
* Created:    {datetime.now().strftime("%Y-%m-%d")}
* Author:     SDTM Pipeline (Auto-generated)
*
* Modification History:
* Date        Author      Description
* ----------  ----------  ---------------------------------------------------
* {datetime.now().strftime("%Y-%m-%d")}  Pipeline    Initial creation
********************************************************************************/

%include "&programs/setup.sas";

%log_step(step={domain} Domain - Start, status=RUNNING);

/*------------------------------------------------------------------------------
* Step 1: Read source data
------------------------------------------------------------------------------*/
data {domain.lower()}_raw;
    set raw.{source};
run;

%put NOTE: Source records read: %sysfunc(nobs({domain.lower()}_raw));

/*------------------------------------------------------------------------------
* Step 2: Apply mappings and transformations
------------------------------------------------------------------------------*/
data {domain.lower()}_temp;
    length
        STUDYID $20
        DOMAIN $2
        USUBJID $40
{self._get_length_statements(spec)}
    ;

    set {domain.lower()}_raw;

    /* Standard variables */
    STUDYID = "&study";
    DOMAIN = "{domain}";

    /* Generate USUBJID */
    USUBJID = %gen_usubjid(study=STUDY, site=scan(INVSITE, -1, "_"), subj=PT);

{mapping_code}
run;

/*------------------------------------------------------------------------------
* Step 3: Generate sequence numbers
------------------------------------------------------------------------------*/
%gen_seq(domain={domain.lower()}, sortvar={self._get_sort_var(domain)});

/*------------------------------------------------------------------------------
* Step 4: Final dataset with variable ordering
------------------------------------------------------------------------------*/
data sdtm.{domain.lower()} (label="SDTM {domain} Domain");
    retain {self._get_retain_order(domain)};
    set {domain.lower()}_temp;

    /* Apply formats */
{self._get_format_statements(domain)}

    /* Keep only SDTM variables */
    keep {self._get_keep_vars(domain)};
run;

/*------------------------------------------------------------------------------
* Step 5: Validation checks
------------------------------------------------------------------------------*/
{validation_code}

/*------------------------------------------------------------------------------
* Step 6: Generate documentation
------------------------------------------------------------------------------*/
proc contents data=sdtm.{domain.lower()} out=work.{domain.lower()}_contents noprint;
run;

proc print data=sdtm.{domain.lower()}(obs=10) label;
    title "Sample of SDTM {domain} Domain";
run;

%log_step(step={domain} Domain - Complete, status=SUCCESS);
'''
        output_path = os.path.join(self.output_dir, f"{domain.lower()}.sas")
        with open(output_path, 'w') as f:
            f.write(code)
        return output_path

    def _generate_mapping_code(self, spec: MappingSpecification) -> str:
        """Generate SAS code for column mappings."""
        code_lines = []

        for mapping in spec.column_mappings:
            if not mapping.target_variable:
                continue

            target = mapping.target_variable
            source = mapping.source_column

            if mapping.derivation_rule and not source:
                # Derived variable
                code_lines.append(f"    /* {target}: {mapping.comments} */")
                if "'" in mapping.derivation_rule:
                    code_lines.append(f"    {target} = {mapping.derivation_rule};")
                else:
                    code_lines.append(f"    /* Derivation: {mapping.derivation_rule} */")
            elif source:
                # Direct mapping with optional transformation
                code_lines.append(f"    /* {target} from {source} */")

                if mapping.transformation:
                    if "ISO 8601" in str(mapping.transformation) or "date" in str(mapping.transformation).lower():
                        code_lines.append(f"    %convert_to_iso(invar={source}, outvar={target});")
                    elif "controlled terminology" in str(mapping.transformation).lower():
                        code_lines.append(f"    {target} = upcase(strip({source}));")
                        code_lines.append(f"    /* Apply controlled terminology mapping */")
                    else:
                        code_lines.append(f"    {target} = {source};")
                        code_lines.append(f"    /* TODO: Apply transformation: {mapping.transformation} */")
                else:
                    code_lines.append(f"    {target} = {source};")

            code_lines.append("")

        return "\n".join(code_lines)

    def _generate_validation_code(self, spec: MappingSpecification) -> str:
        """Generate SAS validation code."""
        domain = spec.target_domain

        code = f'''
/* Check for required variables */
proc sql noprint;
    select count(*) into :missing_studyid
    from sdtm.{domain.lower()}
    where missing(STUDYID);

    select count(*) into :missing_usubjid
    from sdtm.{domain.lower()}
    where missing(USUBJID);
quit;

%if &missing_studyid > 0 %then %do;
    %put ERROR: Found &missing_studyid records with missing STUDYID;
%end;

%if &missing_usubjid > 0 %then %do;
    %put ERROR: Found &missing_usubjid records with missing USUBJID;
%end;

/* Check for duplicates */
proc sort data=sdtm.{domain.lower()} out=_dup_check nodupkey dupout=_dups;
    by usubjid {domain.lower()}seq;
run;

%let dup_count = %sysfunc(nobs(_dups));
%if &dup_count > 0 %then %do;
    %put ERROR: Found &dup_count duplicate records by USUBJID + {domain}SEQ;
%end;
'''
        return code

    def _get_length_statements(self, spec: MappingSpecification) -> str:
        """Generate LENGTH statements for SDTM variables."""
        lengths = {
            # Standard lengths by variable type
            "STUDYID": "$20", "DOMAIN": "$2", "USUBJID": "$40",
            "SUBJID": "$20", "SITEID": "$10",
            # Date/time
            "BRTHDTC": "$20", "RFSTDTC": "$20", "RFENDTC": "$20",
            "AESTDTC": "$20", "AEENDTC": "$20",
            "VSDTC": "$20", "LBDTC": "$20", "CMSTDTC": "$20", "CMENDTC": "$20",
            # Character
            "SEX": "$2", "RACE": "$50", "ETHNIC": "$30",
            "AETERM": "$200", "AEDECOD": "$200", "AESEV": "$10",
            "VSTESTCD": "$8", "VSTEST": "$40", "VSORRES": "$20", "VSORRESU": "$20",
            "LBTESTCD": "$8", "LBTEST": "$40", "LBORRES": "$20", "LBORRESU": "$20",
            "CMTRT": "$200", "CMDECOD": "$200",
            # Numeric
            "AGE": "8", "AESEQ": "8", "VSSEQ": "8", "LBSEQ": "8", "CMSEQ": "8",
        }

        lines = []
        for mapping in spec.column_mappings:
            var = mapping.target_variable
            if var and var in lengths:
                lines.append(f"        {var} {lengths[var]}")

        return "\n".join(lines)

    def _get_sort_var(self, domain: str) -> str:
        """Get sort variable for sequence generation."""
        sort_vars = {
            "DM": "BRTHDTC",
            "AE": "AESTDTC",
            "VS": "VSDTC VSTESTCD",
            "LB": "LBDTC LBTESTCD",
            "CM": "CMSTDTC",
        }
        return sort_vars.get(domain, "USUBJID")

    def _get_retain_order(self, domain: str) -> str:
        """Get RETAIN order for standard variable ordering."""
        orders = {
            "DM": "STUDYID DOMAIN USUBJID SUBJID SITEID BRTHDTC AGE AGEU SEX RACE ETHNIC",
            "AE": "STUDYID DOMAIN USUBJID AESEQ AETERM AEDECOD AESTDTC AEENDTC AESEV AESER AEREL",
            "VS": "STUDYID DOMAIN USUBJID VSSEQ VSTESTCD VSTEST VSORRES VSORRESU VSSTRESC VSSTRESN VSSTRESU VSDTC",
            "LB": "STUDYID DOMAIN USUBJID LBSEQ LBTESTCD LBTEST LBORRES LBORRESU LBSTRESC LBSTRESN LBSTRESU LBDTC",
            "CM": "STUDYID DOMAIN USUBJID CMSEQ CMTRT CMDECOD CMDOSE CMDOSU CMROUTE CMSTDTC CMENDTC",
        }
        return orders.get(domain, "STUDYID DOMAIN USUBJID")

    def _get_format_statements(self, domain: str) -> str:
        """Generate FORMAT statements."""
        return '''    format _numeric_ best12.;
    format _character_ $varying.;'''

    def _get_keep_vars(self, domain: str) -> str:
        """Get KEEP variable list."""
        return self._get_retain_order(domain)

    def generate_driver_program(self, mappings: List[MappingSpecification]) -> str:
        """Generate master driver program."""
        domain_includes = "\n".join([
            f'%include "&programs/{spec.target_domain.lower()}.sas";'
            for spec in mappings
        ])

        code = f'''/*******************************************************************************
* Program:    driver.sas
* Purpose:    Master driver for SDTM transformation pipeline
* Study:      {self.study_id}
* Created:    {datetime.now().strftime("%Y-%m-%d")}
* Author:     SDTM Pipeline (Auto-generated)
********************************************************************************/

%let start_time = %sysfunc(datetime());
%put NOTE: ================================================================;
%put NOTE: SDTM Transformation Pipeline - Started;
%put NOTE: Study: {self.study_id};
%put NOTE: Start Time: %sysfunc(datetime(), datetime20.);
%put NOTE: ================================================================;

/* Run setup */
%include "&programs/setup.sas";

/* Execute domain transformations */
{domain_includes}

/* Generate final report */
%let end_time = %sysfunc(datetime());
%let duration = %sysevalf(&end_time - &start_time);

%put NOTE: ================================================================;
%put NOTE: SDTM Transformation Pipeline - Complete;
%put NOTE: Duration: %sysfunc(putn(&duration, time8.));
%put NOTE: ================================================================;

/* Summary of created datasets */
proc sql;
    title "SDTM Datasets Created";
    select memname as Dataset,
           nobs as Records,
           nvar as Variables
    from dictionary.tables
    where libname = "SDTM"
    order by memname;
quit;
'''
        output_path = os.path.join(self.output_dir, "driver.sas")
        with open(output_path, 'w') as f:
            f.write(code)
        return output_path

    def generate_define_xml_program(self) -> str:
        """Generate SAS program to create define.xml metadata."""
        code = f'''/*******************************************************************************
* Program:    define_xml.sas
* Purpose:    Generate define.xml metadata for SDTM submission
* Study:      {self.study_id}
* Created:    {datetime.now().strftime("%Y-%m-%d")}
********************************************************************************/

%include "&programs/setup.sas";

/* Extract metadata from SDTM datasets */
proc contents data=sdtm._all_ out=work.all_contents noprint;
run;

/* Create variable-level metadata */
proc sql;
    create table work.variable_metadata as
    select memname as Dataset,
           name as Variable,
           type,
           length,
           label,
           format
    from work.all_contents
    order by memname, varnum;
quit;

/* Export for define.xml generation */
proc export data=work.variable_metadata
    outfile="&root/metadata/variable_metadata.csv"
    dbms=csv replace;
run;

%put NOTE: Define.xml metadata extracted successfully;
'''
        output_path = os.path.join(self.output_dir, "define_xml.sas")
        with open(output_path, 'w') as f:
            f.write(code)
        return output_path
