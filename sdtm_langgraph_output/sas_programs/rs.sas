/*******************************************************************************
* Program:    rs.sas
* Purpose:    Create SDTM RS domain from source data
* Study:      MAXIS-08
* Source:     RESP.csv
* Created:    2026-01-20
* Author:     SDTM Pipeline (Auto-generated)
*
* Modification History:
* Date        Author      Description
* ----------  ----------  ---------------------------------------------------
* 2026-01-20  Pipeline    Initial creation
********************************************************************************/

%include "&programs/setup.sas";

%log_step(step=RS Domain - Start, status=RUNNING);

/*------------------------------------------------------------------------------
* Step 1: Read source data
------------------------------------------------------------------------------*/
data rs_raw;
    set raw.resp;
run;

%put NOTE: Source records read: %sysfunc(nobs(rs_raw));

/*------------------------------------------------------------------------------
* Step 2: Apply mappings and transformations
------------------------------------------------------------------------------*/
data rs_temp;
    length
        STUDYID $20
        DOMAIN $2
        USUBJID $40
        STUDYID $20
        DOMAIN $2
        USUBJID $40
    ;

    set rs_raw;

    /* Standard variables */
    STUDYID = "&study";
    DOMAIN = "RS";

    /* Generate USUBJID */
    USUBJID = %gen_usubjid(study=STUDY, site=scan(INVSITE, -1, "_"), subj=PT);

    /* STUDYID from STUDY */
    STUDYID = STUDY;

    /* DOMAIN: Domain abbreviation for Response domain */
    DOMAIN = Set to 'RS' for all records;

    /* USUBJID from PT */
    USUBJID = PT;
    /* TODO: Apply transformation: STUDY + '-' + INVSITE + '-' + PT */

    /* RSSEQ: Sequence number for response records within subject */
    /* Derivation: Generate sequence number for each record per USUBJID */

    /* RSTESTCD from DCMNAME */
    RSTESTCD = DCMNAME;
    /* TODO: Apply transformation: Map 'TM_ASSESS_RESP' to standard code */

    /* RSTEST from DCMNAME */
    RSTEST = DCMNAME;
    /* TODO: Apply transformation: Map 'TM_ASSESS_RESP' to descriptive text */

    /* RSCAT from CPEVENT */
    RSCAT = CPEVENT;

    /* RSORRES from TMRSPO */
    RSORRES = TMRSPO;

    /* RSSTRESC from TMRSPN */
    RSSTRESC = upcase(strip(TMRSPN));
    /* Apply controlled terminology mapping */

    /* RSDTC from TMDT1 */
    %convert_to_iso(invar=TMDT1, outvar=RSDTC);

run;

/*------------------------------------------------------------------------------
* Step 3: Generate sequence numbers
------------------------------------------------------------------------------*/
%gen_seq(domain=rs, sortvar=USUBJID);

/*------------------------------------------------------------------------------
* Step 4: Final dataset with variable ordering
------------------------------------------------------------------------------*/
data sdtm.rs (label="SDTM RS Domain");
    retain STUDYID DOMAIN USUBJID;
    set rs_temp;

    /* Apply formats */
    format _numeric_ best12.;
    format _character_ $varying.;

    /* Keep only SDTM variables */
    keep STUDYID DOMAIN USUBJID;
run;

/*------------------------------------------------------------------------------
* Step 5: Validation checks
------------------------------------------------------------------------------*/

/* Check for required variables */
proc sql noprint;
    select count(*) into :missing_studyid
    from sdtm.rs
    where missing(STUDYID);

    select count(*) into :missing_usubjid
    from sdtm.rs
    where missing(USUBJID);
quit;

%if &missing_studyid > 0 %then %do;
    %put ERROR: Found &missing_studyid records with missing STUDYID;
%end;

%if &missing_usubjid > 0 %then %do;
    %put ERROR: Found &missing_usubjid records with missing USUBJID;
%end;

/* Check for duplicates */
proc sort data=sdtm.rs out=_dup_check nodupkey dupout=_dups;
    by usubjid rsseq;
run;

%let dup_count = %sysfunc(nobs(_dups));
%if &dup_count > 0 %then %do;
    %put ERROR: Found &dup_count duplicate records by USUBJID + RSSEQ;
%end;


/*------------------------------------------------------------------------------
* Step 6: Generate documentation
------------------------------------------------------------------------------*/
proc contents data=sdtm.rs out=work.rs_contents noprint;
run;

proc print data=sdtm.rs(obs=10) label;
    title "Sample of SDTM RS Domain";
run;

%log_step(step=RS Domain - Complete, status=SUCCESS);
