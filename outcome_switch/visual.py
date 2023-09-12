import plotly.graph_objects as go
from typing import List, Dict, Any, Tuple, Union

# gradio highlitghted text
def get_highlighted_text(entities:List[Dict[str,Any]], original_text:str) -> List[Tuple[str,Union[str,None]]] :
    """Convert the output of the model to a list of tuples (entity, label)
    for `gradio.HighlightedText`output"""
    conversion = {"Prim":"primary","Sec":"secondary"}
    highlighted_text = []
    for entity in entities:
        entity_original_text = original_text[entity["start"]:entity["end"]]
        if entity["entity_group"] == "O":
            entity_output = (entity_original_text, None)
        else:
            entity_output = (entity_original_text, conversion[entity["entity_group"]])
        highlighted_text.append(entity_output)
    return highlighted_text

# article filtered sections markdown output
def get_markdown(detection_output: Dict[str, Any], template:str) -> str:
    """Get the markdown of a list of sections"""
    format_dict = {}
    article_id = detection_output["retrieved_article_id"]
    if detection_output["db"] == "pubmed":
        format_dict["text_link"]= f"https://pubmed.ncbi.nlm.nih.gov/{article_id}/"
    elif detection_output["db"] == "pmc":
        format_dict["text_link"]= f"https://www.ncbi.nlm.nih.gov/pmc/articles/{article_id}/"
    format_dict["text_content"] = ""
    for title, content in detection_output["filtered_sections"].items():
        format_dict["text_content"] += "## " + title + " \n"
        for paragraph in content:
            format_dict["text_content"] += paragraph + " \n"
    format_dict["db"] = detection_output["db"]
    format_dict["text_type"] = detection_output["text_type"]
    format_dict["check_type"] = detection_output["check_type"]
    format_dict["regex_priority_name"] = detection_output["regex_priority_name"]
    return template.format(**format_dict)

## Functions for Sankey diagram
def sankey_preprocess(sentence:str, max_words:int=10) -> str:
    words = sentence.split()
    # make batchs of 15 words 
    batchs = [words[i:i+max_words] for i in range(0, len(words), max_words)]
    # join the batchs with a <br> tag
    return "<br>".join([" ".join(batch) for batch in batchs])

def find_entity_score(entity_text, raw_entities):
    for tc_output in raw_entities:
        if entity_text == tc_output["word"]:
            return tc_output["score"]


def format_data(true,compared,connections):
    color_map = {
        "primary": "red",
        "secondary": "green",
        "other": "grey",
    }
    list1 = [(sankey_preprocess(sent), color_map[typ]) for typ, sent in true]
    list2 = [(sankey_preprocess(sent), color_map[typ]) for typ, sent in compared]
    connections = [(list1[i][0],list2[j][0],"mediumaquamarine") if cosine > 0.44 else (list1[i][0],list2[j][0],"lightgray") for i,j,cosine in connections]
    # Create a list of labels and colors for the nodes
    labels = [x[0] for x in list1 + list2]
    colors = [x[1] for x in list1 + list2]
    # Create lists of sources and targets for the connections
    sources = [labels.index(x[0]) for x in connections]
    targets = [labels.index(x[1]) for x in connections]
    # Create a list of values and colors for the connections
    values = [1] * len(connections)
    connection_colors = [x[2] for x in connections]
    return labels, colors, sources, targets, values, connection_colors


def format_display(true,compared,connections, raw_entities):
    node_customdata = ["from: registry"]*len(true) + ["from: article<br>confidence: " + str(find_entity_score(s, raw_entities)) for _,s in compared]
    node_hovertemplate = "outcome: %{label}<br>%{customdata} <extra></extra>"
    link_customdata = [cosine for _,_,cosine in connections]
    link_hovertemplate = "similarity: %{customdata} <extra></extra>"
    return node_customdata, node_hovertemplate, link_customdata, link_hovertemplate


def get_sankey_diagram(detection_output: Dict[str, Any]):
    labels, colors, sources, targets, values, connection_colors = format_data(detection_output["registry"],detection_output["article"],detection_output["connections"])
    node_customdata, node_hovertemplate, link_customdata, link_hovertemplate = format_display(detection_output["registry"],detection_output["article"],detection_output["connections"], detection_output["raw_entities"])
    sankey =  go.Sankey(node=dict(
                            pad=15,
                            thickness=20,
                            line=dict(color="black", width=0.5),
                            label=labels,
                            customdata=node_customdata,
                            color=colors,
                            hovertemplate=node_hovertemplate
                        ),
                        link=dict(
                            source=sources,
                            target=targets,
                            value=values,
                            customdata=link_customdata,
                            color=connection_colors,
                            hovertemplate=link_hovertemplate)
                        )
    # Create the Sankey diagram
    fig = go.Figure(data=[sankey])
    fig.update_layout(
        title_text="Registry outcomes (left) connections with article outcomes (right)", 
        font_size=10,
        width=1200,
        xaxis=dict(rangeslider=dict(visible=True),type="linear")
    )
    return fig