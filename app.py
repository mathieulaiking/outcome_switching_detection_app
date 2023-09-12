from outcome_switch.main import OutcomeSwitchingDetector
from outcome_switch.utils import get_sections_text
from outcome_switch.visual import get_sankey_diagram, get_highlighted_text, get_markdown
import json
import gradio as gr

TITLE = "Outcome Switching Detection"
DESCRIPTION = open("front/DESCRIPTION.md").read()
ARTICLE_TEXT_TEMPLATE = open("front/ARTICLE_TEXT_TEMPLATE.md").read()
EXAMPLES_TITLE = open("front/EXAMPLES_TITLE.html").read()
PMC_LINK = open("front/PMC_LINK_BOX.html").read()
PMID_EXAMPLES = json.load(open("front/EXAMPLES.json"))
pmcid_start_value = PMID_EXAMPLES[0]

with open('./config.json', 'r') as f:
    config = json.load(f)
osd = OutcomeSwitchingDetector(config)

def detect_outswitch_pmid(id:str):
    output = osd.detect(str(id))
    filtered_article = get_markdown(output, ARTICLE_TEXT_TEMPLATE) if output["filtered_sections"] else "*Article not found*"
    detected_annotations = [("No annotations found", None)] if not output["raw_entities"] else get_highlighted_text(output["raw_entities"], get_sections_text(output["filtered_sections"]))
    registry_outcomes = {"CTGOV": "No registry entry found"} if not output["detected_nct_id"]  else {"NCT_ID": output["detected_nct_id"]} | {"registry_outcomes" : output["registry_outcomes"]}
    similarity_diagram = get_sankey_diagram(output) if output["connections"] and "NCT_ID" in registry_outcomes and not ("No annotations found", None) in detected_annotations else None
    return filtered_article, detected_annotations, registry_outcomes, similarity_diagram

def clean():
    return None, None, None, None

blocks = gr.Blocks()

with blocks:
    # BLOCK LAYOUT
    with gr.Column():
        gr.Markdown("# " + TITLE + '  \n' + DESCRIPTION )
        with gr.Box():
            with gr.Column():
                with gr.Row():
                    pmid_input = gr.Textbox(value=pmcid_start_value, label="PMID, PMCID or DOI (PMCID must be preceded by 'PMC' prefix)")
                with gr.Row():
                    clean_button = gr.ClearButton()    
                    detect_button = gr.Button(value="Detect", variant="primary")
        gr.Examples(examples = PMID_EXAMPLES, inputs=pmid_input)
        gr.Markdown("## Results  \n")
        with gr.Tabs():
            with gr.TabItem("Article Useful Sections"):
                filtered_article = gr.Markdown()
            with gr.TabItem("Article Detected Outcomes"):
                ner_output = gr.HighlightedText(show_legend=True,combine_adjacent=True, show_label=False)
            with gr.TabItem("Registry Outcomes"):
                ctgov_output = gr.JSON()
            with gr.TabItem("Similarity"):
                similarity_output = gr.Plot(show_label=False)
    # OUTPUTS AND BUTTONS
    outputs = [filtered_article, ner_output, ctgov_output, similarity_output]
    clean_button.click(fn=clean, inputs=pmid_input, outputs=outputs)
    detect_button.click(fn=detect_outswitch_pmid, inputs=pmid_input, outputs=outputs)

blocks.launch()
