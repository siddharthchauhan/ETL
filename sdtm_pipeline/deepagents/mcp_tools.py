"""
Healthcare Connector Tools
===========================
Direct API wrapper tools for 6 healthcare data sources,
providing the same capabilities as deepsense.ai MCP connectors.

Data Sources:
- ClinicalTrials.gov API v2: Clinical trial search and retrieval
- NPI Registry (NPPES): Healthcare provider lookups
- CMS Coverage Database: Medicare coverage policies (NCDs/LCDs)
- ICD-10-CM (NLM): Diagnosis code lookups
- ChEMBL REST API: Drug/compound bioactivity data
- bioRxiv API: Preprint paper search

All tools are async to prevent blocking the ASGI event loop.
No authentication required for any of these public APIs.

Usage:
    from .mcp_tools import HEALTHCARE_TOOLS
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

import aiohttp
from langchain_core.tools import tool


# =============================================================================
# HTTP HELPER
# =============================================================================

async def _http_get(url: str, params: Optional[Dict[str, Any]] = None,
                    headers: Optional[Dict[str, str]] = None,
                    timeout: int = 30) -> Dict[str, Any]:
    """Make an async HTTP GET request and return JSON response."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers=headers,
                               timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            if resp.status != 200:
                text = await resp.text()
                return {"error": f"HTTP {resp.status}: {text[:500]}"}
            try:
                return await resp.json()
            except aiohttp.ContentTypeError:
                # Some APIs return JSON with wrong content-type
                text = await resp.text()
                return json.loads(text)


# =============================================================================
# 1. CLINICAL TRIALS (ClinicalTrials.gov API v2)
# =============================================================================

@tool
async def search_clinical_trials(
    condition: Optional[str] = None,
    intervention: Optional[str] = None,
    term: Optional[str] = None,
    location: Optional[str] = None,
    status: Optional[str] = None,
    sponsor: Optional[str] = None,
    page_size: int = 10,
) -> Dict[str, Any]:
    """Search ClinicalTrials.gov for clinical trials by condition, intervention, location, or sponsor.

    Args:
        condition: Disease or condition to search for (e.g., "breast cancer", "diabetes")
        intervention: Treatment or intervention (e.g., "pembrolizumab", "radiation therapy")
        term: General search term across all fields
        location: Geographic location (e.g., "New York", "United States")
        status: Trial status filter. Options: RECRUITING, COMPLETED, ACTIVE_NOT_RECRUITING,
                NOT_YET_RECRUITING, TERMINATED, WITHDRAWN, SUSPENDED
        sponsor: Sponsor or collaborator name
        page_size: Number of results to return (max 50)

    Returns:
        Dict with totalCount and list of trial summaries including NCT ID, title,
        status, conditions, interventions, sponsor, and phase.
    """
    params: Dict[str, Any] = {
        "pageSize": min(page_size, 50),
        "countTotal": "true",
    }
    if condition:
        params["query.cond"] = condition
    if intervention:
        params["query.intr"] = intervention
    if term:
        params["query.term"] = term
    if location:
        params["query.locn"] = location
    if status:
        params["filter.overallStatus"] = status.upper()
    if sponsor:
        params["query.spons"] = sponsor

    data = await _http_get("https://clinicaltrials.gov/api/v2/studies", params=params)
    if "error" in data:
        return data

    studies = data.get("studies", [])
    results = []
    for s in studies:
        ps = s.get("protocolSection", {})
        ident = ps.get("identificationModule", {})
        status_mod = ps.get("statusModule", {})
        desc = ps.get("descriptionModule", {})
        conds = ps.get("conditionsModule", {})
        design = ps.get("designModule", {})
        sponsor_mod = ps.get("sponsorCollaboratorsModule", {})

        results.append({
            "nct_id": ident.get("nctId"),
            "title": ident.get("briefTitle"),
            "status": status_mod.get("overallStatus"),
            "conditions": conds.get("conditions", []),
            "phases": design.get("phases", []),
            "study_type": design.get("studyType"),
            "sponsor": (sponsor_mod.get("leadSponsor") or {}).get("name"),
            "summary": (desc.get("briefSummary") or "")[:300],
            "url": f"https://clinicaltrials.gov/study/{ident.get('nctId')}",
        })

    return {
        "total_count": data.get("totalCount", len(results)),
        "returned": len(results),
        "trials": results,
    }


@tool
async def get_clinical_trial_details(nct_id: str) -> Dict[str, Any]:
    """Get complete details for a specific clinical trial by NCT ID.

    Args:
        nct_id: ClinicalTrials.gov identifier (e.g., "NCT04267848")

    Returns:
        Dict with full trial details including eligibility, arms, outcomes,
        contacts, and study design.
    """
    data = await _http_get(f"https://clinicaltrials.gov/api/v2/studies/{nct_id}")
    if "error" in data:
        return data

    ps = data.get("protocolSection", {})
    return {
        "nct_id": ps.get("identificationModule", {}).get("nctId"),
        "title": ps.get("identificationModule", {}).get("officialTitle"),
        "brief_title": ps.get("identificationModule", {}).get("briefTitle"),
        "status": ps.get("statusModule", {}).get("overallStatus"),
        "start_date": (ps.get("statusModule", {}).get("startDateStruct") or {}).get("date"),
        "completion_date": (ps.get("statusModule", {}).get("completionDateStruct") or {}).get("date"),
        "conditions": ps.get("conditionsModule", {}).get("conditions", []),
        "interventions": [
            {"name": i.get("name"), "type": i.get("type")}
            for i in (ps.get("armsInterventionsModule", {}).get("interventions") or [])
        ],
        "eligibility": ps.get("eligibilityModule", {}),
        "sponsor": (ps.get("sponsorCollaboratorsModule", {}).get("leadSponsor") or {}).get("name"),
        "summary": ps.get("descriptionModule", {}).get("briefSummary"),
        "design": ps.get("designModule", {}),
        "outcomes": ps.get("outcomesModule", {}),
        "url": f"https://clinicaltrials.gov/study/{nct_id}",
    }


# =============================================================================
# 2. NPI REGISTRY (NPPES)
# =============================================================================

@tool
async def search_npi_registry(
    number: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    organization_name: Optional[str] = None,
    taxonomy_description: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """Search the NPI Registry for healthcare providers by name, organization, specialty, or NPI number.

    Args:
        number: 10-digit NPI number for direct lookup
        first_name: Provider's first name (individual providers only)
        last_name: Provider's last name (individual providers only)
        organization_name: Organization name (supports trailing wildcard *)
        taxonomy_description: Provider specialty (e.g., "Family Medicine", "Cardiology")
        city: City name
        state: Two-letter state code (e.g., "NY", "CA")
        limit: Max results to return (1-200)

    Returns:
        Dict with result_count and list of providers including NPI, name,
        specialty, address, and credentials.
    """
    params: Dict[str, Any] = {"version": "2.1", "limit": min(limit, 200)}
    if number:
        params["number"] = number
    if first_name:
        params["first_name"] = first_name
    if last_name:
        params["last_name"] = last_name
    if organization_name:
        params["organization_name"] = organization_name
    if taxonomy_description:
        params["taxonomy_description"] = taxonomy_description
    if city:
        params["city"] = city
    if state:
        params["state"] = state

    data = await _http_get("https://npiregistry.cms.hhs.gov/api/", params=params)
    if "error" in data:
        return data

    results = []
    for r in data.get("results", []):
        basic = r.get("basic", {})
        taxonomies = r.get("taxonomies", [])
        addresses = r.get("addresses", [])

        provider = {
            "npi": r.get("number"),
            "type": r.get("enumeration_type"),
            "status": basic.get("status"),
        }

        # Individual vs Organization
        if r.get("enumeration_type") == "NPI-1":
            provider["name"] = f"{basic.get('first_name', '')} {basic.get('last_name', '')}".strip()
            provider["credential"] = basic.get("credential")
        else:
            provider["name"] = basic.get("organization_name", "")

        # Primary taxonomy
        primary = next((t for t in taxonomies if t.get("primary")), taxonomies[0] if taxonomies else {})
        provider["specialty"] = primary.get("desc", "")
        provider["taxonomy_code"] = primary.get("code", "")

        # Location address
        loc = next((a for a in addresses if a.get("address_purpose") == "LOCATION"), addresses[0] if addresses else {})
        if loc:
            provider["address"] = f"{loc.get('address_1', '')}, {loc.get('city', '')}, {loc.get('state', '')} {loc.get('postal_code', '')}"
            provider["phone"] = loc.get("telephone_number", "")

        results.append(provider)

    return {
        "result_count": data.get("result_count", len(results)),
        "providers": results,
    }


# =============================================================================
# 3. CMS COVERAGE DATABASE
# =============================================================================

@tool
async def search_cms_coverage(
    query: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """Search CMS Medicare National Coverage Determinations (NCDs) for coverage policies.

    Args:
        query: Search term for coverage topics (e.g., "MRI", "chemotherapy",
               "diabetes screening"). If not provided, returns recent NCDs.
        limit: Number of results to return (max 50)

    Returns:
        Dict with list of NCD coverage determinations including title, chapter,
        document ID, and last updated date.
    """
    # Fetch all NCDs (server has ~350 total), then filter client-side
    params: Dict[str, Any] = {"limit": 500}

    data = await _http_get(
        "https://api.coverage.cms.gov/v1/reports/national-coverage-ncd/",
        params=params,
    )
    if "error" in data:
        return data

    ncds = data.get("data", [])

    # Filter by query if provided (server-side search not supported)
    if query:
        q = query.lower()
        ncds = [n for n in ncds
                if q in (n.get("title") or "").lower()
                or q in (n.get("chapter") or "").lower()]

    results = []
    for ncd in ncds[:limit]:
        results.append({
            "document_id": ncd.get("document_display_id"),
            "title": ncd.get("title"),
            "chapter": ncd.get("chapter"),
            "last_updated": ncd.get("last_updated"),
            "url": f"https://www.cms.gov/medicare-coverage-database/view/ncd.aspx?ncdid={ncd.get('document_id')}&ncdver={ncd.get('document_version')}",
        })

    return {
        "total": len(results),
        "ncds": results,
    }


# =============================================================================
# 4. ICD-10-CM CODES (NLM Clinical Tables)
# =============================================================================

@tool
async def search_icd10_codes(
    terms: str,
    max_results: int = 20,
) -> Dict[str, Any]:
    """Search ICD-10-CM diagnosis codes by keyword or code prefix.

    Args:
        terms: Search term — can be a condition name (e.g., "diabetes",
               "hypertension") or code prefix (e.g., "E11", "I10")
        max_results: Maximum number of codes to return (max 100)

    Returns:
        Dict with total count and list of matching ICD-10-CM codes with descriptions.
    """
    params = {
        "sf": "code,name",
        "terms": terms,
        "maxList": min(max_results, 100),
    }

    data = await _http_get(
        "https://clinicaltables.nlm.nih.gov/api/icd10cm/v3/search",
        params=params,
    )
    if "error" in data:
        return data

    # Response is a JSON array: [total_count, codes, null, display_strings]
    if not isinstance(data, list) or len(data) < 4:
        return {"error": "Unexpected response format", "raw": str(data)[:500]}

    total_count = data[0]
    display_data = data[3] or []

    codes = []
    for item in display_data:
        if isinstance(item, list) and len(item) >= 2:
            codes.append({"code": item[0], "description": item[1]})

    return {
        "total_count": total_count,
        "returned": len(codes),
        "codes": codes,
    }


# =============================================================================
# 5. ChEMBL (Drug/Compound Data)
# =============================================================================

@tool
async def search_chembl_compounds(
    query: Optional[str] = None,
    max_phase: Optional[int] = None,
    molecule_type: Optional[str] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """Search the ChEMBL database for drug compounds and molecules.

    Args:
        query: Compound name or partial name to search (e.g., "aspirin", "ibuprofen")
        max_phase: Filter by clinical phase (4=approved, 3=phase III, 2=phase II, 1=phase I)
        molecule_type: Filter by type (e.g., "Small molecule", "Antibody", "Protein")
        limit: Number of results to return (max 50)

    Returns:
        Dict with list of compounds including ChEMBL ID, name, type, phase,
        molecular properties, and SMILES structure.
    """
    params: Dict[str, Any] = {
        "format": "json",
        "limit": min(limit, 50),
    }
    if max_phase is not None:
        params["max_phase"] = max_phase
    if molecule_type:
        params["molecule_type__iexact"] = molecule_type

    # Use search endpoint if query provided, otherwise list endpoint
    if query:
        url = "https://www.ebi.ac.uk/chembl/api/data/molecule/search.json"
        params["q"] = query
    else:
        url = "https://www.ebi.ac.uk/chembl/api/data/molecule.json"

    data = await _http_get(url, params=params)
    if "error" in data:
        return data

    molecules = data.get("molecules", [])
    results = []
    for m in molecules:
        props = m.get("molecule_properties") or {}
        structs = m.get("molecule_structures") or {}
        results.append({
            "chembl_id": m.get("molecule_chembl_id"),
            "name": m.get("pref_name"),
            "molecule_type": m.get("molecule_type"),
            "max_phase": m.get("max_phase"),
            "molecular_weight": props.get("full_mwt"),
            "alogp": props.get("alogp"),
            "hba": props.get("hba"),
            "hbd": props.get("hbd"),
            "psa": props.get("psa"),
            "ro5_violations": props.get("num_ro5_violations"),
            "smiles": structs.get("canonical_smiles"),
        })

    return {
        "total_count": (data.get("page_meta") or {}).get("total_count"),
        "returned": len(results),
        "compounds": results,
    }


@tool
async def get_chembl_bioactivities(
    chembl_id: str,
    limit: int = 20,
) -> Dict[str, Any]:
    """Get bioactivity data for a specific ChEMBL compound.

    Args:
        chembl_id: ChEMBL compound ID (e.g., "CHEMBL25" for aspirin)
        limit: Number of activity records to return (max 50)

    Returns:
        Dict with bioactivity records including target, assay type,
        activity value, and units.
    """
    params = {
        "molecule_chembl_id": chembl_id,
        "format": "json",
        "limit": min(limit, 50),
    }

    data = await _http_get(
        "https://www.ebi.ac.uk/chembl/api/data/activity.json",
        params=params,
    )
    if "error" in data:
        return data

    activities = data.get("activities", [])
    results = []
    for a in activities:
        results.append({
            "target_name": a.get("target_pref_name"),
            "target_chembl_id": a.get("target_chembl_id"),
            "target_organism": a.get("target_organism"),
            "assay_type": a.get("assay_type"),
            "activity_type": a.get("standard_type"),
            "value": a.get("standard_value"),
            "units": a.get("standard_units"),
            "relation": a.get("standard_relation"),
        })

    return {
        "chembl_id": chembl_id,
        "total_count": (data.get("page_meta") or {}).get("total_count"),
        "returned": len(results),
        "activities": results,
    }


# =============================================================================
# 6. bioRxiv / medRxiv (Preprint Papers)
# =============================================================================

@tool
async def search_biorxiv_papers(
    query: Optional[str] = None,
    server: str = "biorxiv",
    days_back: int = 30,
    category: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """Search bioRxiv or medRxiv for recent preprint papers.

    Args:
        query: Search term to filter paper titles/abstracts (client-side filtering)
        server: Repository to search: "biorxiv" or "medrxiv"
        days_back: Number of days to look back (default 30, max 90)
        category: Subject category filter (e.g., "neuroscience", "cell_biology",
                  "bioinformatics", "genomics", "pharmacology")
        limit: Number of results to return (max 50)

    Returns:
        Dict with list of preprint papers including title, authors, abstract,
        DOI, date, and category.
    """
    days = min(days_back, 90)
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    url = f"https://api.biorxiv.org/details/{server}/{start_date}/{end_date}/0"

    data = await _http_get(url, timeout=45)
    if "error" in data:
        return data

    papers = data.get("collection", [])

    # Apply category filter if provided
    if category:
        cat = category.lower().replace(" ", "_")
        papers = [p for p in papers if cat in (p.get("category") or "").lower()]

    # Apply query filter if provided (search in title and abstract)
    if query:
        q = query.lower()
        papers = [p for p in papers if
                  q in (p.get("title") or "").lower() or
                  q in (p.get("abstract") or "").lower()]

    # Limit results
    papers = papers[:limit]

    results = []
    for p in papers:
        results.append({
            "title": p.get("title"),
            "authors": p.get("authors"),
            "corresponding_author": p.get("author_corresponding"),
            "institution": p.get("author_corresponding_institution"),
            "doi": p.get("doi"),
            "date": p.get("date"),
            "category": p.get("category"),
            "abstract": (p.get("abstract") or "")[:500],
            "url": f"https://www.{server}.org/content/{p.get('doi')}",
            "server": p.get("server"),
        })

    messages = data.get("messages", [{}])
    total = messages[0].get("total", len(results)) if messages else len(results)

    return {
        "total_available": total,
        "returned": len(results),
        "date_range": f"{start_date} to {end_date}",
        "papers": results,
    }


# =============================================================================
# TOOL COLLECTION
# =============================================================================

HEALTHCARE_TOOLS = [
    # Clinical Trials
    search_clinical_trials,
    get_clinical_trial_details,
    # NPI Registry
    search_npi_registry,
    # CMS Coverage
    search_cms_coverage,
    # ICD-10 Codes
    search_icd10_codes,
    # ChEMBL
    search_chembl_compounds,
    get_chembl_bioactivities,
    # bioRxiv
    search_biorxiv_papers,
]


def get_healthcare_tools_status() -> str:
    """Get a human-readable status string for healthcare connector tools."""
    return f"{len(HEALTHCARE_TOOLS)} tools (6 data sources: ClinicalTrials.gov, NPI Registry, CMS Coverage, ICD-10, ChEMBL, bioRxiv)"
