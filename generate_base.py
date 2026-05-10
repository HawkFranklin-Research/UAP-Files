import pandas as pd
import json

base_schema = [
    "file_id", "title", "review_group", "cluster", "graph_community", 
    "agency", "file_group", "human_document_genre", "case_or_compilation", 
    "single_event_or_multi_event", "event_date_precision", "event_location_precision", 
    "primary_location", "witness_type", "sensor_type", "raw_media_present", 
    "object_shape", "object_color", "motion_description", "duration_available", 
    "altitude_speed_available", "official_explanation_present", "resolution_status", 
    "external_verification_possible", "scientific_usefulness_score_0_10", 
    "reason_for_scientific_usefulness", "why_algorithm_selected_this_file", 
    "content_unique_or_format_unique", "reviewer_confidence_0_3", "short_human_summary"
]

target_ids = ["doc_0121", "doc_0123", "doc_0122", "doc_0129", "doc_0119"]

doc = pd.read_csv("analysis/embeddings/document_index.csv").fillna("")
clusters = pd.read_csv("analysis-2.0/cluster_interpretation/baseline_kmeans_clusters.csv").fillna("")
graph = pd.read_csv("analysis-2.0/graph_analysis/file_graph_nodes.csv").fillna("")

results = []
for file_id in target_ids:
    row = {col: "" for col in base_schema}
    row["file_id"] = file_id
    
    d_row = doc[doc["document_id"] == file_id]
    if not d_row.empty:
        row["title"] = d_row.iloc[0]["title"]
        row["agency"] = d_row.iloc[0]["agency"]
        row["file_group"] = d_row.iloc[0]["file_group"]
        
    c_row = clusters[clusters["document_id"] == file_id]
    if not c_row.empty:
        row["cluster"] = str(int(c_row.iloc[0]["cluster"]))
        
    g_row = graph[graph["document_id"] == file_id]
    if not g_row.empty:
        row["graph_community"] = str(int(g_row.iloc[0]["graph_community"]))

    results.append(row)

print(json.dumps(results, indent=2))
