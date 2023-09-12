import bs4
import re
import requests
from datetime import datetime
from unicodedata import normalize
from typing import List, Dict, Union, Tuple, Any
from outcome_switch.data import Outcome
        
# - look for nct id in the registration part if it exists
class CTGOVAPILinker:

    CTGOV_API_URL = "https://clinicaltrials.gov/api/query/"

    FIELDS = {
        "outcomes": ["PrimaryOutcomeDescription", "PrimaryOutcomeMeasure",
                     "PrimaryOutcomeTimeFrame", "SecondaryOutcomeDescription",
                     "SecondaryOutcomeMeasure", "SecondaryOutcomeTimeFrame",
                     "OtherOutcomeDescription", "OtherOutcomeMeasure", "OtherOutcomeTimeFrame"], 
        "dates": ["StartDate", "StartDateType","PrimaryCompletionDate", 
                  "PrimaryCompletionDateType","CompletionDate","StudyFirstPostDate",
                  "StudyFirstPostDateType","StudyFirstSubmitDate","StudyFirstSubmitQCDate"],
        "references": ["ReferencePMID", "ReferenceCitation","ReferenceType"],
    }

    def get_study_fields(self, search_expression: str, study_fields: List[str], min_rank=1, max_rank=1000) -> List[Dict]:
        ret = []
        params = {
            "expr": search_expression,
            "fmt": "json",
            "fields": ",".join(study_fields),
            "min_rnk": min_rank,
            "max_rnk": max_rank,
        }
        r = requests.get(self.CTGOV_API_URL + 'study_fields', params=params)
        data = r.json()['StudyFieldsResponse']
        if data["NStudiesFound"] != 0:
            ret = data["StudyFields"]
        return ret

    def get_fields(self, nct_id: str, field_key: str) -> Dict[str, List[str]]:
        """Extract fields from ctgov database using nct_id and
        returns a dictionary of field name and list of values

        Args:
            nct_id (str): nct id of the study
            field_key (str): key of the field to extract (outcomes, dates, references)

        Returns:
            Dict[str, List[str]]: dictionary of field name and list of values
        """
        ret = {}
        if nct_id:
            sf = self.get_study_fields(nct_id, self.FIELDS[field_key])
            if sf:
                ret = sf[0]
        return ret

    def get_outcomes(self, nct_id: str, add_description:bool=False) -> List[Tuple[str,str]]:
        """Extract outcomes from ctgov database using nct_id and 
        returns list of tuples (outcome_type, outcome_text)"""
        outcomes_dict = self.get_fields(nct_id, "outcomes")
        outcomes = []
        if outcomes_dict:
            for ot_type in ["Primary", "Secondary", "Other"]:
                for i in range(len(outcomes_dict[f"{ot_type}OutcomeMeasure"])):
                    outcome_text = outcomes_dict[f"{ot_type}OutcomeMeasure"][i] + " , " + outcomes_dict[f"{ot_type}OutcomeTimeFrame"][i]
                    res = (ot_type.lower(), outcome_text)
                    if add_description:
                        res += (outcomes_dict[f"{ot_type}OutcomeDescription"][i],)
                    outcomes.append((ot_type.lower(), outcome_text))
        return outcomes

    def get_outcome_related_informations(self, nct_id: str):
        dates_dict = self.get_fields(nct_id, "dates")
        references_dict = self.get_fields(nct_id, "references")
        return dict(dates_dict, **references_dict)
        
        
class CTGOVHTMLParser :
    
    useful_rows = [
        "Current Primary Outcome Measures",
        "Original Primary Outcome Measures",
        "Current Secondary Outcome Measures",
        "Original Secondary Outcome Measures",
        "Current Other Pre-specified Outcome Measures ",
        "Original Other Pre-specified Outcome Measures ",
    ]
    URL = "https://classic.clinicaltrials.gov/ct2/show/record/{nct_id}"

    def filter_rows(self, tr_lines:bs4.ResultSet[bs4.element.Tag]) -> List[Tuple[str,bs4.element.Tag]]:
        """Find rows in html table that contains outcomes using useful_rows"""
        search_row_pile = self.useful_rows.copy()
        filtered_rows = []
        for tr in tr_lines:
            for i, label in enumerate(search_row_pile):
                if label in tr.text:
                    filtered_rows.append((label, tr))
                    search_row_pile.pop(i)
                    break
            if not search_row_pile:
                break
        return filtered_rows

    def get_lines_soup(self, nct_id:str) -> bs4.ResultSet[bs4.element.Tag]:
        return bs4.BeautifulSoup(requests.get(self.URL.format(nct_id=nct_id)).text, "lxml").find_all("tr") 


    def extract_outcome_lines(self, nct_id:str) -> Dict[str, List[Outcome]]:
        outcomes: Dict[str, List[Outcome]] = {key:[] for key in self.useful_rows}
        for title, tr_soup in self.filter_rows(self.get_lines_soup(nct_id)):
            date_type, outcome_type = [t.lower() for t in title.split()[0:2]] 
            submission_date = self.parse_submission_date(tr_soup)
            if tr_soup.find("td").find("i"): # if original outcome Same as current
                current_outcomes = outcomes["Current " + title.split("Original ")[1]]
                transformed_to_original = [Outcome(o.text,o.outcome_type, "original", o.submission_date, o.description, o.time_frame) for o in current_outcomes]
                outcomes[title] = transformed_to_original
                continue
            if tr_soup.find("td").find("ul"): # if list of outcomes
                for content_soup in tr_soup.find("td").find_all("li"):
                    outcome_text, outcome_desc, outcome_time = self.parse_outcome_content(content_soup)
                    outcomes[title].append(Outcome(outcome_text,outcome_type,date_type,submission_date,outcome_desc,outcome_time))
            else : # if single outcome
                outcome_text, outcome_desc, outcome_time  = self.parse_outcome_content(tr_soup.find("td"))
                if outcome_text != "Not Provided" :
                    outcomes[title].append(Outcome(outcome_text,outcome_type,date_type,submission_date,outcome_desc,outcome_time))
        return outcomes
            
    def parse_submission_date(self, tr_soup:bs4.element.Tag) -> Union[datetime,None]:
        submission_date = None
        datespan = tr_soup.find("span")
        if datespan and datespan.text:
            date_fullstring = normalize("NFKD", datespan.text)
            submission_date = datetime.strptime(date_fullstring, '(submitted: %B %d, %Y)')
        return submission_date

    def parse_outcome_content(self, content_soup:bs4.element.Tag) -> Tuple[str,str,str]:
        outcome_text, outcome_description, time_frame = "", "", ""
        if content_soup.contents:
            normalized_outcome_text = normalize("NFKD", content_soup.contents[0])
            time_frame_split = normalized_outcome_text.split("[ Time Frame:")
            if len(time_frame_split) == 2: # if time frame is specified
                outcome_text = time_frame_split[0].strip()
                time_frame = time_frame_split[1].split("]")[0].strip()
            else: # no time frame specified
                outcome_text = normalized_outcome_text.strip()
                time_frame = ""
            indent_description = content_soup.find("div", {"class":"tr-indent2"})
            if indent_description and indent_description.find('ul'): # if sublist of description
                outcome_description = normalize("NFKD", str(indent_description.contents[0])).strip()
                for li_soup in indent_description.find_all('li'):
                    outcome_description += normalize("NFKD", li_soup.text).strip() + " , "
            elif indent_description and indent_description.text:
                outcome_description = normalize("NFKD", indent_description.text).strip()
        return outcome_text, outcome_description, time_frame


class CTGOVExtractor : 

    def __init__(self) :
        self.api_linker = CTGOVAPILinker()
        self.html_parser = CTGOVHTMLParser()
    
    # TODO : first search in XML for registration title part and then search in whole text if not found
    def find_nct_id(self, text: str) -> Union[str,None]:
        """Finds the first NCT ID mentioned in the text and returns it,
        return empty string if not found"""
        ret = ""
        regex = r"NCT\d{8}"
        match = re.search(regex, text)
        if match:
            ret = match[0]
        return ret
    
    def get_all_infos(self, nct_id: str):
        api_info = self.api_linker.get_outcome_related_informations(nct_id)
        return dict(api_info, **self.get_outcomes(nct_id))
    
    def get_outcomes(self, nct_id: str, date_type:str="original") -> List[str]:
        outcomes_dict = self.html_parser.extract_outcome_lines(nct_id)
        modifs = self.is_current_original_modif(outcomes_dict)
        return {"date_type":date_type, "primary_current-original_modif": modifs, "full_registry_outcomes": outcomes_dict}
    
    def is_current_original_modif(self, outcomes: Dict[str,List[Outcome]]) -> str:
        """Check if there is a switch between original and current primary outcomes"""
        current, original = outcomes[self.html_parser.useful_rows[0]], outcomes[self.html_parser.useful_rows[1]]
        ret = ""
        if len(current) > len(original):
            ret += "added_primary_outcomes"
        elif len(current) < len(original):
            ret += "removed_primary_outcomes"
        else:
            for i in range(len(current)):
                cur_out, orig_out = current[i], original[i]
                if orig_out.text != "Not Provided":
                    ret += orig_out.compare(cur_out)
                else : 
                    ret += "original_not_provided"
        return ret
