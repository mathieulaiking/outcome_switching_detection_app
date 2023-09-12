Demo of outcome switching detection using transformers models. Outcome switching is defined as the modification, inversion, suppression of a primary outcome in a Randomized Controlled Trial(RCT) between the  published article and the registry entry (only for clinicaltrials.gov registry for now) 

What this demo is doing : Retrieve PMC article fulltext from PMC ID using the API, Parse the Methods section of the article and get section text, Use finetuned NER model for detecting primary outcomes in that text, Use a RegEx to find the NCT ID (ClinicalTrials.gov) in the full text, Use CTGOV API to extract registry primary outcome (considered as ground truth), Use Semantic Textual Similarity Model to compare CTGOV outcome to article detected outcomes