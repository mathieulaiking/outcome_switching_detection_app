from typing import List, Dict, Any, Tuple
from outcome_switch.data import Outcome

def get_batchs(input_list: List[Any], batch_size: int) -> List[List[Any]]:
    """Split a list into batches of a given size"""
    # TODO : add overlap option and modify outcome extraction
    batchs = []
    for i in range(0, len(input_list), batch_size):
        batchs.append(input_list[i:i + batch_size])
    return batchs


def get_sections_text(sections_dict: Dict[str, List[str]]) -> str:
    """Get the text of a list of sections"""
    output_text = ""
    for title, content in sections_dict.items():
        content = " ".join(content)
        output_text += title + '\n' + content + '\n'
    return output_text


def filter_outcomes(entities: List[Dict[str, Any]]) -> List[Tuple[str,str]]:
    """Filter primary and secondary outcomes from the list of entities a key is created 
    only if at least one entity is found for the given group"""
    outcomes = []
    for entity in entities:
        if entity["entity_group"] == "O":
            continue
        elif entity["entity_group"] == "Prim" :
            outcomes.append(("primary", entity["word"]))
        elif entity["entity_group"] == "Sec":
            outcomes.append(("secondary", entity["word"]))
    return outcomes


def convert_registry_outcomes(full_registry_outcomes: Dict[str,List[Outcome]], 
                              date_type_filter:str="original", 
                              add_time_frame:bool=True,
                              add_description:bool=False) -> List[Tuple[str,str]]:
    """Convert registry outcomes to a list of tuples (type, outcome)"""
    ret_lot = []
    for o_list in full_registry_outcomes.values():
        for o in o_list:
            if not isinstance(o, Outcome):
                o = Outcome(**o)
            if o.date_type.value == date_type_filter :
                o_desc = o.description if add_description else ""
                o_tf = o.time_frame if add_time_frame else ""
                complete_text = o.text
                for additional_text in [o_tf, o_desc]:
                    if additional_text :
                        complete_text += " , " + additional_text 
                ret_lot.append((o.outcome_type.value, complete_text))
    return ret_lot



