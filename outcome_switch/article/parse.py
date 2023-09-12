from xml.etree import ElementTree as ET
from typing import List, Dict, Any, Union
from os.path import join

class XMLParser :

    def _get_text(self, element: ET.Element) -> str:
        """Extract text contained in `xml.etree.ElementTree.Element` 
        object(text and tail of all children)"""
        text = element.text if element.text else ''
        text += " " + element.tail if element.tail else ''
        for child in element:
            te = child.text if child.text else ''
            ta = child.tail if child.tail else ''
            text += " " + te + ta
        return text.encode("ascii", "ignore").decode("utf-8").strip()

    def _get_table(self, table_element: ET.Element) -> List[str]:
        """Extract text from XML table element with first column as title and other columns 
        as list of values

        Args:
            table_element (ET.Element): element representing a table in XML

        Returns:
            List[str]: List of column lines printed as : '<1st_column> : <2nd_column> , <3rd column> , ...'
        """
        columns = []
        for row in table_element.findall('.//{*}tr'):
            row_index = 0
            for cell in row:
                cell_type = cell.tag.split('}')[1] if '}' in cell.tag else cell.tag
                cell_text = cell.text.encode("ascii", "ignore").decode(
                    "utf-8") if cell.text else ''
                if cell_type == "th":
                    columns.append(cell_text + " : ")
                elif cell_type == "td" and row_index < len(columns):
                    columns[row_index] += cell_text + " , "
                row_index += 1
        return columns

    def _get_sections(self, element: ET.Element, prefix="") -> Dict[str, List[str]]:
        """Get all sections titles and content from an XML element using
        depth-first search

        Args:
            element (ET.Element): XML element of an article containing hierarchy of text
            prefix (str, optional): prefix to add to section title. Defaults to "".

        Returns:
            Dict[str,List[str]]: dictionary containing all sections titles (keys) and their corresponding text content (values)
        """
        prefix = [prefix] if prefix else []
        title_stack = []
        result_dict = {}
        for element, depth in self._depth_iter(element):
            el_type = element.tag.split('}')[1] if '}' in element.tag else element.tag

            if el_type == "title":
                if not title_stack or title_stack[-1][0] < depth:
                    title_stack.append((depth, element.text))
                elif title_stack[-1][0] >= depth:
                    while depth <= title_stack[-1][0]:
                        title_stack.pop(-1)
                        if not title_stack:
                            break
                    title_stack.append((depth, element.text))

            elif el_type in ["p","table","label"]:
                title = " - ".join(prefix + [text for _,
                                   text in title_stack if text])
                content_text = self._get_table(element) if el_type == "table" else [self._get_text(element)]
                if title not in result_dict:
                    result_dict[title] = content_text
                else:
                    result_dict[title] += content_text
            
        return result_dict

    def _depth_iter(self, element, tag=None):
        """Iterate over an ElementTree object and yield element and depth"""
        stack = []
        stack.append(iter([element]))
        while stack:
            e = next(stack[-1], None)
            if e == None:
                stack.pop()
            else:
                stack.append(iter(e))
                if tag == None or e.tag == tag:
                    yield (e, len(stack) - 1)

class PMCXMLParser(XMLParser):

    def parse_metadata(self, xml_string: str) -> Dict[str, Any]:
        front = ET.fromstring(xml_string).find('.//{*}front')
        journal_iso_abbrev = front.find(
            './/{*}journal-id[@journal-id-type="iso-abbrev"]')
        publisher_name = front.find('.//{*}publisher-name')
        keywords = front.findall('.//{*}kwd-group//{*}kwd')
        funding_institutions = front.findall(
            './/{*}funding-group//{*}institution')
        authors = front.findall(
            './/{*}contrib-group//{*}contrib[@contrib-type="author"]')
        affiliations = front.findall('.//{*}aff')
        metadata = {
            "journal": self._get_text(journal_iso_abbrev),
            "publisher": self._get_text(publisher_name),
            "keywords": [self._get_text(k) for k in keywords],
            "funding_institutions": [self._get_text(f) for f in funding_institutions],
            "authors": [{
                        "first_name": author_el.find('.//{*}given-names').text,
                        "last_name": author_el.find('.//{*}surname').text,
                        "affiliations": [self._get_text(aff) for aff in author_el.findall('.//{*}xref')]
                        } for author_el in authors],
            "affiliations": {self._get_text(aff.find('.//{*}label')) : self._get_text(aff.find('.//{*}institution'))
                            for aff in affiliations}
        }
        return metadata
    
    def parse_keywords(self, xml_string:str) -> List[str]:
        front = ET.fromstring(xml_string).find('.//{*}front')
        keywords = front.findall('.//{*}kwd-group//{*}kwd')
        return [self._get_text(k) for k in keywords]

    def parse_fulltext(self, xml_input: Union[str,ET.Element]) -> Dict[str, List[str]]:
        """Parse all text of article using sections structure, 
        if multiple subsection, will get the smallest section 
        and append all subtitles to the key, e.g : 
        ```json
        {
            "Methods - Outcomes - Primary Outcomes" : "Primary outcomes subsection text",
            "Methods - Outcomes - Secondary Outcomes" : "Secondary outcomes subsection text"
        }
        ```

        Args:
            element (ET.Element): XML element of an article containing hierarchy of text

        Returns:
            Dict[str,List[str]]: dictionary containing all sections titles (keys) and their corresponding text content (values)
        """
        if isinstance(xml_input, str):
            root = ET.fromstring(xml_input)
        elif isinstance(xml_input, ET.Element):
            root = xml_input
        else:
            raise TypeError("xml_input must be a string or an ET.Element")
        title = {"Title": [self._get_text(root.find('.//{*}article-title'))]}
        abstract = root.find('.//{*}abstract')
        abstract_sections = self._get_sections(abstract, prefix="Abstract")
        body = root.find('.//{*}body')
        body_sections = self._get_sections(body)
        parsed_text = title | abstract_sections | body_sections
        return parsed_text


class PubMedXMLParser(XMLParser):
    def _get_text(self, element: ET.Element) -> str:
        """Extract text contained in `xml.etree.ElementTree.Element` 
        object(text and tail of all children)"""
        text = element.text if element.text else ''
        text += " " + element.tail if element.tail else ''
        for child in element:
            te = child.text if child.text else ''
            ta = child.tail if child.tail else ''
            text += " " + te + ta
        return text.encode("ascii", "ignore").decode("utf-8").strip()

    def _get_sections(self, abstract_element: ET.Element) -> Dict[str, List[str]]:
        sections = {}
        for section in abstract_element.findall('.//{*}AbstractText'):
            section_title = section.attrib.get("Label") if "Label" in section.attrib else ""
            section_text = self._get_text(section)
            sections["Abstract - " + section_title] = [section_text]
        return sections

    def parse(self, xml_input: Union[str,ET.Element]) -> Dict[str, List[str]]:
        if isinstance(xml_input, str):
            root = ET.fromstring(xml_input)
        elif isinstance(xml_input, ET.Element):
            root = xml_input
        else:
            raise TypeError("xml_input must be a string or an ET.Element")
        title = {"Title": [self._get_text(root.find('.//{*}ArticleTitle'))]}
        abstract_tree = root.find('.//{*}Abstract')
        abstract_sections = self._get_sections(abstract_tree)
        return title | abstract_sections


class ResponseParser(XMLParser):

    def _parse_article_response(self, article_element:ET.Element, db:str, save_dir:str="") -> Dict[str,Any]:
        """ Parse a single article XML element (PMC or PubMed) depending on the `db` parameter."""
        ret = {
            "retrieved_article_id": None,
            "article_xml_string":ET.tostring(article_element, encoding="unicode", method="xml"),
            "db": db,
            "text_type": None,
            "text_sections": None,
        }
        if db == "pubmed":
            ret["retrieved_article_id"] = article_element.find(".//{*}ArticleId[@IdType='pubmed']").text
            ret["db"], ret["text_type"] = "pubmed", "abstract"
            pubmed_parser = PubMedXMLParser()
            ret['text_sections'] = pubmed_parser.parse(ret["article_xml_string"])
        elif db == "pmc" :
            ret["retrieved_article_id"] = 'PMC' + article_element.find(".//{*}article-id[@pub-id-type='pmc']").text
            ret["db"]="pmc"
            ret['text_type'] = "fulltext" if article_element.find('.//{*}body') is not None else "abstract"
            pmc_parser = PMCXMLParser()
            ret['text_sections'] = pmc_parser.parse_fulltext(ret["article_xml_string"])
        if save_dir : # if save_dir is set save the xmls to save_dir
            output_path = join(save_dir, f'{ret["retrieved_article_id"]}.xml')
            with open(output_path, "w") as f:
                f.write(ret["article_xml_string"])
        return ret
    
    def parse_multiple_response(self, response_xml: str, db: str, save_dir:str="") -> List[Dict[str,str]]:
        """ Parse a Entrez esearch XML response potentially containing multiple articles (PMC or PubMed)
        depending on the `db` parameter."""
        root = ET.fromstring(response_xml)
        article_tag = "{*}article" if db == "pmc" else "{*}PubmedArticle"
        return [self._parse_article_response(a,db,save_dir) for a in root.findall(f'.//{article_tag}')]
    
    