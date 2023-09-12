from outcome_switch.registry import CTGOVExtractor
from outcome_switch.article.download import IDDownloader
from outcome_switch.outcome_comparison import OutcomeSimilarity
from outcome_switch.article.filter import SectionFilter
from outcome_switch.utils import get_sections_text, filter_outcomes, convert_registry_outcomes
from typing import List, Dict, Tuple, Any
from transformers import BertTokenizerFast, BertForTokenClassification, TokenClassificationPipeline

class OutcomeSwitchingDetector:
    """Main Class for the whole pipeline of outcome switching detection"""
    def __init__(self, config: Dict[str,str]) -> None:
        self.outcomes_ner = TokenClassificationPipeline(
            model = BertForTokenClassification.from_pretrained(config["outcome_extractor_path"]),
            tokenizer = BertTokenizerFast.from_pretrained(config["outcome_extractor_path"]),
            ignore_labels = [],
            aggregation_strategy = "average",
            stride=64
        )
        self.similarity_assessor = OutcomeSimilarity(config["outcome_sim_path"])

    def detect_registry_outcomes(self, nct_id_or_text:str, date_type:str="original") -> Tuple[str, Dict[str, List[str]]] :
        """detect nct id in text (or directly from nct_id) and get outcomes from ctgov database using html parser
        returns a dict with retrieved information on outcomes and trial registration dates
        
        Args:
            nct_id_or_text (str): nct id or article text containing nct id
            date_type (str, optional): "original" or "current" , filter applied to outcomes to only take 
            in account the ones we want to consider. Defaults to "original".
        """
        cte = CTGOVExtractor()
        detected_nct_id = cte.find_nct_id(nct_id_or_text)
        # get outcomes from ctgov database using S api
        infos_dict = cte.get_all_infos(detected_nct_id)
        # outcomes_dict = cte.get_outcomes(detected_nct_id)
        # reformat and filter registry outcomes :
        outcomes_lot = convert_registry_outcomes(infos_dict["full_registry_outcomes"], add_time_frame=False)
        return {"detected_nct_id": detected_nct_id } | infos_dict | {"registry_outcomes": outcomes_lot}

    def detect_article_outcomes(self, article_sections:Dict[str,List[str]], text_type:str) -> Dict[str, Any]:
        """filter outcome-related sections and detect outcomes in them
        returns a dictionary with the following keys (potentially all keys related to filter are None 
        if the text is an abstract (will not filter abstracts)
        - filtered_sections : dict of all filtered sections of the article key=title, value=list of text content
        - regex_priority_index: index of the regex used to filter the sections in the CHECK_PRIORITY list
        - regex_priority_name: name of the regex used to filter the sections in the CHECK_PRIORITY list
        - check_type: type of check used to filter the sections (title or content)
        - raw_entities : list of all entities detected in the article (output of huggingface token classifier)
        - article_outcomes : dict of all outcomes detected in the article key=type, value=list of outcomes
        """
        section_filter = SectionFilter()
        # Filter outcome-related sections
        filtered_output = section_filter.filter_sections(article_sections, text_type)
        input_text = get_sections_text(filtered_output["filtered_sections"])
        # get article outcomes (all pieces of text annotated)
        entities_list = self.outcomes_ner(input_text)
        # filter outcomes only
        detected_outcomes =  filter_outcomes(entities_list)
        return filtered_output | {"raw_entities" :entities_list, "article_outcomes" : detected_outcomes}

    
    def compare_outcomes(self, registry_outcomes: List[Tuple[str,str]], article_outcomes: List[Tuple[str,str]]) -> Dict[str,Any]:   
        # get similarity
        similarity_output = {
            "registry": registry_outcomes,
            "article": article_outcomes,
            "connections" : self.similarity_assessor.get_similarity(registry_outcomes, article_outcomes)
        }
        return similarity_output

    def detect(self, input_id:str) :
        """detect outcome switching in input id (pmid, pmcid or doi)
        returns a dictionary with the following keys:
        
        - input_id : input entered by the user
        Article Detection:
        - retrieved_article_id : id of the retrieved article (pmcid if exists else pmid or none if not found)
        - db : database of the retrieved article (pmc or pubmed)
        - text_type : type of the retrieved article (fulltext or abstract)
        - text_sections : dict of all sections of the article key=title, value=list of text content
        - check_type : type of the check for regex outcome section filtering (title or content)
        - regex_priority_name : name of the regex used for outcome section filtering
        - regex_priority_index : number of priority of the regex used for outcome section filtering (0 is the highest priority)
        - filtered_sections : dict of all filtered sections of the article key=title, value=list of text content
        - raw_entities : list of all entities detected in the article (output of huggingface token classifier)
        - article_outcomes : List of tuples (type, outcome) of all outcomes detected in the article

        Registry Detection:
        - detected_nct_id : first nct id detected in the article
        - registry_outcomes : List of tuples (type, outcome) of all outcomes detected in the registry
        - date_type : type of the date of the registry outcomes (current or original)
        - primary_current-original_modif : modifications of the primary outcome between current and original if there is one 
        - full_registry_outcomes : List of Outcomes objects of all outcomes detected in the registry


        Similarity and Decision:
        - decision
        - outcomes_associations
        """
        # get articles
        self.article_downloader = IDDownloader(logging_mode='console')
        download_responses = self.article_downloader.fetch_xml([input_id])
        if download_responses :
            download_output = {"input_id" : input_id} |  download_responses[0]
        else :
            download_output = {"input_id" : input_id, "retrieved_article_id":"", "article_xml_string": "", "text_type":""}
        registry_output = self.detect_registry_outcomes(download_output["article_xml_string"]) 
        article_output = self.detect_article_outcomes(download_output["text_sections"], download_output["text_type"] )
        comparison_output = self.compare_outcomes(registry_output["registry_outcomes"], article_output["article_outcomes"])
        return download_output | registry_output | article_output | comparison_output
