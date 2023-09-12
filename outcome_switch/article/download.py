import requests
import urllib
import logging
import json
import os
from os.path import join
from datetime import datetime
from typing import List, Dict
from xml.etree import ElementTree as ET
from outcome_switch.article.parse import ResponseParser
from outcome_switch.utils import get_batchs
# external python modules
from pytz import timezone

class IDConverter:

    ID_CONVERTER_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"

    def __init__(self,
        email:str='',
        tool:str='',
        versions:bool=False,
        idtype:str='',
        logging_mode:str="file",
        log_filepath:str='logs/pmid_conversion.log'
    ):
        """Instantiates a PubMed ID converter (PMID,PMCID,DOI) that will return request in specified 
        format and with or without multiple versions of the articles

        Args:
            email (str): e-mail address of the maintainer of your tool, and should be a valid e-mail address

            tool (str): name of your application, as a string value with no internal spaces.

            versions (bool, optional): whether the app needs MIDs or information about the versions 
            of an article. Defaults to False.

            idtype (str, optional): type of the input ids. Defaults to "" (auto_detection by API). 
            You can override ID type auto-detection behavior by using the idtype parameter. Valid values
            are "pmcid","pmid", "mid", and "doi". For example, the following lets you specify PMCIDs as 
            simple numeric values. If the idtype parameter is not used, PMCIDs must have the "PMC" prefix, 
            in order to distinguish them from PMIDs. Example :
            ```
            > id_converter = PubMedIDConverter()
            > id_converter.id_conversion(["14900"], idtype="pmcid")
            ```
        """
        if idtype not in ["pmcid","pmid","mid","doi",""]:
            raise ValueError("idtype must be one of pmcid, pmid, mid, doi or empty(auto_detection by API)")
        # we choose to use json response format
        self.email = email
        self.tool = tool
        self.idtype = idtype if idtype else 'auto'
        self.versions = 'yes' if versions else 'no'
        self.log_filepath = log_filepath
        # defining logging according to given mode
        if logging_mode == "file":
            logging.basicConfig(filename=log_filepath, encoding='utf-8', level=logging.INFO)
        elif logging_mode == "console":
            logging.basicConfig(level=logging.INFO)
        elif logging_mode == "console-debug":
            logging.basicConfig(level=logging.DEBUG)
        elif logging_mode == "none":
            logging.basicConfig(level=logging.CRITICAL)
        else:
            raise ValueError("logging_mode must be one of file, console, console-debug or none")    

    def _replace_errors(self, records:List[Dict[str,str]]) -> List[Dict[str,str]]:
        """Replace the error values in the records with None"""
        success_keys = ['pmid', 'pmcid', 'doi']
        new_records = []
        for record in records:
            if "errmsg" in record:
                new_record = {}
                for key in success_keys:
                    if key in record:
                        new_record[key] = record[key]
                    else :
                        new_record[key] = None
            else : 
                new_record = record
            new_records.append(new_record)
        return records

    def convert_single_list(self, ids: List[str]) -> List[Dict[str,str]]:
        """Get all linked ids from the given list of ids in PubMed ids must 
        be a non-empty list of strings and not longer than 200 ids"""
        if not isinstance(ids, list) :
            raise TypeError("ids must be a list of strings")
        elif not all(isinstance(id, str) for id in ids):
            raise TypeError("ids must be a list of strings")
        elif len(ids) <= 0:
            raise ValueError("ids list must not be empty")
        elif len(ids) > 200:
            raise ValueError("ids list must not be longer than 200")

        converted_ids = []
        params = {
            "ids":",".join(ids),
            "idtype":self.idtype,
            "versions":self.versions,
            "format":"json", # we choose to parse the response using json format
            "email":self.email,
            "tool":self.tool
        }
        response_text = requests.get(self.ID_CONVERTER_URL, params=params).text
        json_response = json.loads(response_text)
        if 'warning' in json_response:
            logging.warning(json_response['warning'])
        if json_response['status'] == 'ok':
            logging.info(f"{json_response['responseDate']} : ok")
            converted_ids = self._replace_errors(json_response['records'])
        elif json_response['status'] == 'error':
            message = urllib.parse.unquote(json_response['message'])
            logging.error(f"{json_response['responseDate']} : {message}")
            raise ValueError(json_response['message'])
        return converted_ids

    def convert(self, ids: List[str]) -> List[Dict[str,str]]:
        """Get all linked ids from the given list of ids in PubMed
        if the list is longer than 200 ids, it will be split into multiple requests
        of maximum length 200 ids"""
        if not isinstance(ids, list):
            raise TypeError("ids must be a list of strings")
        if not all(isinstance(id, str) for id in ids):
            raise TypeError("ids must be a list of strings")
        if len(ids) == 0:
            raise ValueError("ids list must not be empty")
        elif len(ids) > 200 :
            split_ids = get_batchs(ids, 200)
            converted_ids = []
            for id_list in split_ids:
                converted_ids += self.convert_single_list(id_list)
        else :
            converted_ids = self.convert_single_list(ids)
        return converted_ids


class PMCOAIDownloader:

    # PMC API for Full text retrieval
    OAI_PMH_URL = "https://www.ncbi.nlm.nih.gov/pmc/oai/oai.cgi"
    # PMC API is busy between 5:00 AM and 9:00 PM EST
    API_TIMEZONE = timezone("US/Eastern")
    API_BUSY_HOUR_START = datetime.strptime("05:00", "%H:%M").time()
    API_BUSY_HOUR_END = datetime.strptime("21:00", "%H:%M").time()

    def __init__(self, logging_mode: str = "file", log_filepath="logs/pmc-oai_download.log") -> None:
        self.log_filepath = log_filepath
        if logging_mode == "file":
            logging.basicConfig(filename=log_filepath, encoding='utf-8', level=logging.INFO)
        elif logging_mode == "console":
            logging.basicConfig(level=logging.INFO)
        elif logging_mode == "none":
            logging.basicConfig(level=logging.CRITICAL)
        else:
            raise ValueError("logging_mode must be one of file, console or none")


    def is_busy_hour(self):
        ret = False
        current_api_timezone_time = datetime.now(self.API_TIMEZONE).time()
        if current_api_timezone_time > self.API_BUSY_HOUR_START and current_api_timezone_time < self.API_BUSY_HOUR_END:
            ret = True
        return ret

    def _get_remaining(self, full_list:List[str], output_dir:str) -> List[str]:
        """Get remaining files to download, given files downloaded in output_dir
        and files that could not be downloaded because they are not on PMC (using
        log file errors)
        """
        # Already downloaded files
        downloaded_ids = {f.split(".")[0] for f in os.listdir(output_dir)}

        # Error files (not on PMC)
        log_error_ids = set()
        if os.path.exists(self.log_filepath):
            with open(self.log_filepath, "r") as f:
                for line in f.readlines():
                    if "ERROR:root:pmcid=" in line:
                        pmcid = line.split("pmcid=")[1][:7]
                        log_error_ids.add(pmcid)
        return list(set(full_list) - downloaded_ids.union(log_error_ids))

    def save_multiple_fulltexts(self, pmcids: List[str], output_dir: str, force_busy_download:bool=False) -> None:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        else: # if it exists, get the list of downloaded files
            pmcids = self._get_remaining(pmcids, output_dir)
        
        # if len(pmcids) > 25 :
        #     force_busy_download = False
        
        for pmcid in pmcids:
            fulltext = self.get_fulltext(pmcid, force_busy_download)
            if fulltext != "":
                with open(join(output_dir, pmcid + ".xml"), "w") as f:
                    f.write(fulltext)

    def get_fulltext(self, pmcid: str, force_busy_download:bool=False) -> str:
        if self.is_busy_hour() and not force_busy_download:
            logging.error("API is busy, try again later")
            raise Exception(f"PMC API is busy between 5:00 AM and 9:00 PM EST. Current time is {datetime.now(self.API_TIMEZONE).time()}")
        assert type(pmcid) == str, "pmcid must be a string"
        pmcid = pmcid[3:] if pmcid.startswith("PMC") else pmcid
        # TODO : assert pmcid length
        ret = ""
        params = {
            "verb": "GetRecord",
            "identifier": "oai:pubmedcentral.nih.gov:" + pmcid,
            "metadataPrefix": "pmc",
        }
        request_response = requests.get(self.OAI_PMH_URL, params=params)
        if request_response.status_code == 200:
            logging.debug(f"{pmcid} request response : {request_response.text}")
        else :
            logging.error(f"{pmcid} request error : {request_response.text}")
        root = ET.fromstring(request_response.text)
        if root.find("./{*}error") is None:
            info_message = f"pmcid={pmcid} , retrieved successfully"
            logging.info(info_message)
            ret = request_response.text
        else :
            error_el = root.find("./{*}error")
            error_message = f"pmcid={pmcid} , code={error_el.attrib} , message={error_el.text}"
            logging.error(error_message)
        return ret

class EntrezDownloader:
    E_UTILITIES_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

    def __init__(self,logging_mode: str = "file", log_filepath="logs/pubmed-download.log"):
        self.log_filepath = log_filepath 
        # defining logging according to given mode
        if logging_mode == "file":
            logging.basicConfig(filename=self.log_filepath, encoding='utf-8', level=logging.INFO)
        elif logging_mode == "console":
            logging.basicConfig(level=logging.INFO)
        elif logging_mode == "debug":
            logging.basicConfig(level=logging.DEBUG)
        elif logging_mode == "none":
            logging.basicConfig(level=logging.CRITICAL)
        else:
            raise ValueError("logging_mode must be one of file, console or none")
    
    def get_pmid(self, title:str) -> str :
        """Get pmid from title using esearch"""
        ret = ""
        params = {
            "db" : "pubmed",
            "term" : title.replace(" ", "+"),
            "retmax" : 1,
            "retmode" : "json"
        }
        response = requests.get(self.E_UTILITIES_URL + "esearch.fcgi", params=params)
        if response.status_code == 200:
            print(response)
            ret = response
        else: 
            logging.error(f"no pmid found for title : {title}")
        return ret

    def fetch_xml(self, pmcids: List[str], db:str="pmc", save_dir:str="") -> List[Dict[str,str]]:
        article_xmls = []
        params = {
            "db": db,
            "id": ",".join(pmcids),
            "retmode": "xml"
        }
        request_function = requests.get if len(pmcids) < 200 else requests.post
        response = request_function(self.E_UTILITIES_URL + "efetch.fcgi", params=params)
        if response.status_code == 200:
            xml_string = response.text
            parser = ResponseParser()
            article_xmls = parser.parse_multiple_response(xml_string, db, save_dir)
        else : 
            logging.error(f"Server Error while fetching xml for pmcids {pmcids}")
        return article_xmls

class IDDownloader :

    def __init__(self, logging_mode: str = "file", id_logfile:str = "", entrez_logfile:str=""):
        self.id_converter = IDConverter(
            logging_mode=logging_mode,
            log_filepath=id_logfile
        )
        self.entrez_downloader = EntrezDownloader(
            logging_mode=logging_mode,
            log_filepath=entrez_logfile
        )

    def fetch_xml(self, ids: List[str], save_dir: str="") -> List[Dict[str,str]]:
        """Fetches xmls from pubmed and pmc for given ids if save_dir is given, saves xmls to save_dir
        returns a list of dict (for each input id) with the following keys :
            - retrieved_article_id : article pmid (if not on PMC) or pmcid (if on PMC)
            - article_xml_string : xml response string of the article
            - db : database from which the article was retrieved (pubmed or pmc)
            - text_type : type of text in the article ('abstract' or 'fulltext')
            - text_sections : dictionary of text sections :keys is the section names, values is a list section texts. A 
              section is a paragraph title in the article (concatenated with its parent paragraph titles if there
              are subsections)
        """
        if len(ids) == 0 :
            raise ValueError("ids must be a non empty list")
        # check ids type
        linked_ids = self.id_converter.convert(ids)
        pmcids, pmids = [],[]
        for id_dict in linked_ids :
            if 'pmcid' in id_dict :
                pmcids.append(id_dict['pmcid'])
            elif 'pmid' in id_dict :
                pmids.append(id_dict['pmid'])
        pmc_response_dict = self.entrez_downloader.fetch_xml(pmcids, save_dir=save_dir)
        pubmed_response_dict = self.entrez_downloader.fetch_xml(pmids, db="pubmed", save_dir=save_dir)
        return pubmed_response_dict + pmc_response_dict
  
