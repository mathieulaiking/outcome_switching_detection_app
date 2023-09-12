---
title: Outcome Switching Detector
emoji: 🔄 
colorFrom: blue
colorTo: gray
sdk: gradio
sdk_version: 3.43.2
app_file: app.py
pinned: false
python_version: 3.11.5
models: ['Mathking/scibert_scivocab_uncased-ner-prim_out','Mathking/all-mpnet-base-v2_outcome_sim']
---

# Outcome Switching Detector

## Installation

1. Download dependencies : `pip install -r requirements.txt`

2. Define pretrained models path in config file : you must redefine `config.json` so that it points to the models if you do not have them on disk :
```json
{
    "outcome_extractor_path": "Mathking/PubMedBERT-base-uncased-abstract-finetuned-outcomes-ner",
    "outcome_sim_path": "Mathking/all-mpnet-base-v2_outcome_sim"
}
```

3. Run `python3 -m app.py`
