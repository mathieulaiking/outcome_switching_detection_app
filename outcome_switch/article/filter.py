from typing import Dict, List, Any
import re


class SectionFilter :

    STRICT_OUTCOME_REGEX = '(outcome|end(\s)?point)'
    OUTCOME_REGEX = '(outcome|end(\s)?point|measure|objective|assessment|analysis)'
    
    METHOD_REGEX = '(method|approach|strategy|design|protocol)'
    SAMPLE_SIZE_REGEX = 'sample\s(size|number)'
    ABSTRACT_REGEX = '(abstract|summary)'

    STRICT_PRIM_SEC_REGEX = f'(primary|secondary|main|)\s(efficacy\s)?{STRICT_OUTCOME_REGEX}'
    PRIM_SEC_REGEX = f'(primary|secondary|main|)\s(efficacy\s)?{OUTCOME_REGEX}'
    STRICT_METHOD_AND_PRIM_SEC_REGEX = f'{METHOD_REGEX}.+{STRICT_PRIM_SEC_REGEX}' 
    METHOD_AND_PRIM_SEC_REGEX = f'{METHOD_REGEX}.+{PRIM_SEC_REGEX}'

    # Probably not useful but might be later
    INTRODUCTION_REGEX = '(introduction|background|aim|objective|purpose)'
    RESULTS_REGEX = '(result|findings|data|analysis|outcome)'
    DISCUSSION_REGEX = '(discussion|interpretation|conclusion)'
    CONCLUSION_REGEX = '(conclusion|interpretation)'

    CHECK_PRIORITY = [
        ("strict_method_and_prim_sec","title",STRICT_METHOD_AND_PRIM_SEC_REGEX),
        ("strict_prim_sec","title",STRICT_PRIM_SEC_REGEX),
        ("prim_sec","title",PRIM_SEC_REGEX),
        ("outcome","title",OUTCOME_REGEX),
        ("strict_prim_sec","content",STRICT_PRIM_SEC_REGEX),
        ("prim_sec","content",PRIM_SEC_REGEX),
        ("method_and_prim_sec","title",METHOD_AND_PRIM_SEC_REGEX),
        ("outcome","content",OUTCOME_REGEX),
        ("sample_size","title",SAMPLE_SIZE_REGEX),
        ("method","title",METHOD_REGEX),
        ("abstract","title",ABSTRACT_REGEX),
    ]

    def filter_sections(self, sections_dict: Dict[str, List[str]], text_type:str) -> Dict[str, Any] :
        """Filter sections to keep only the ones containing relevant information if the text is a fulltext
        else keep all sections of abstract

        Args:
            sections_dict (Dict[str,List[str]]): dictionary containing all sections titles (keys) and their corresponding text content (values)
            text_type (str): type of text to filter (abstract or fulltext)

        Returns:
            Dict[str,Any]: dictionary containing the following keys:
                - filtered_sections: dictionary containing all sections titles (keys) and their corresponding text content (values) that contain relevant information
                - regex_priority_index: index of the regex used to filter the sections in the CHECK_PRIORITY list
                - regex_priority_name: name of the regex used to filter the sections in the CHECK_PRIORITY list
                - check_type: type of check used to filter the sections (title or content)
        """
        filter_output = {
            "filtered_sections" : {},
            "regex_priority_index" : None,
            "regex_priority_name" : None,
            "check_type" : None,
        }
        if text_type == "abstract" and sections_dict :
            filter_output["filtered_sections"] = sections_dict
        elif sections_dict and text_type == "fulltext":
            match_found = False
            for i, el  in enumerate(self.CHECK_PRIORITY) :
                priority_name, content_type, current_regex = el
                current_regex = re.compile(current_regex, re.IGNORECASE)
                for title, content_list in sections_dict.items() :
                    content = title if content_type == "title" else '\n'.join(content_list)
                    if current_regex.search(content) :
                        filter_output["check_type"] = content_type
                        filter_output["regex_priority_name"] = priority_name
                        filter_output["regex_priority_index"] = i
                        filter_output["filtered_sections"][title] = content_list
                        match_found = True
                if match_found :
                    break
        return filter_output

