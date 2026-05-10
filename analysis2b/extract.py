import pandas as pd
import os

# Create directories
dirs = ['analysis2b/cluster_cards', 'analysis2b/anomaly_cards', 'analysis2b/bridge_cards', 'analysis2b/manual_review']
for d in dirs:
    os.makedirs(d, exist_ok=True)

# Load metadata for missing fields
metadata = pd.read_csv('ufo_release_metadata.csv')
metadata_info = metadata[['Output Path', 'Incident Date', 'Incident Location']].drop_duplicates(subset=['Output Path'])

# 1. Top 10 representative files per cluster
rep_df = pd.read_csv('analysis-2.0/cluster_interpretation/cluster_representatives.csv')
rep_df = pd.merge(rep_df, metadata_info, on='Output Path', how='left')
rep_df = rep_df[rep_df['representative_rank'] <= 10].copy()
rep_out = rep_df[['cluster', 'representative_rank', 'Title', 'Agency', 'File Group', 'Incident Date', 'Incident Location', 'centroid_cosine_distance', 'Output Path']].copy()
rep_out.columns = ['cluster', 'rank_within_cluster', 'title', 'agency', 'file_group', 'incident_date', 'incident_location', 'distance_to_cluster_center', 'output_path']
rep_out.to_csv('analysis2b/cluster_cards/cluster_cards.csv', index=False)

# Create cluster_cards.md template
with open('analysis2b/cluster_cards/cluster_cards.md', 'w') as f:
    f.write("# Cluster Cards\n\nFor each cluster, provide interpretation here.\n\n")

# 2. Top 15 bridge files
bridge_df = pd.read_csv('analysis-2.0/graph_analysis/bridge_files.csv')
nodes_df = pd.read_csv('analysis-2.0/graph_analysis/file_graph_nodes.csv')
bridge_df = bridge_df.sort_values(by='betweenness', ascending=False).head(15).copy()

# Add Output Path from metadata based on document_id (or title) if possible, let's join with rep_df which has it, or usefulness proxy
usefulness_df = pd.read_csv('analysis-2.0/usefulness_proxy/scientific_usefulness_proxy.csv')
path_map = usefulness_df[['document_id', 'Output Path']].drop_duplicates()
bridge_df = pd.merge(bridge_df, path_map, on='document_id', how='left')

bridge_df['nearest_communities'] = '' # Placeholder as we don't have it directly
bridge_out = bridge_df[['title', 'agency', 'file_group', 'graph_community', 'betweenness', 'degree', 'nearest_communities', 'Output Path']].copy()
bridge_out.columns = ['title', 'agency', 'file_group', 'graph_community', 'betweenness', 'degree', 'nearest_communities', 'output_path']
bridge_out.to_csv('analysis2b/bridge_cards/bridge_file_cards.csv', index=False)

with open('analysis2b/bridge_cards/bridge_file_cards.md', 'w') as f:
    f.write("# Bridge File Cards\n\nFor each top bridge file, provide interpretation here.\n\n")

# 3. Top 25 anomalies with nearest neighbors
anom_df = pd.read_csv('analysis-2.0/anomaly_validation/top25_ensemble_anomalies.csv')
nn_df = pd.read_csv('analysis-2.0/nearest_neighbors/top_anomaly_neighbors.csv')

nn_pivoted = []
for doc_id, group in nn_df.groupby('document_id'):
    group = group.sort_values('neighbor_rank').head(3)
    titles = group['neighbor_title'].tolist()
    dists = group['cosine_distance'].tolist()
    titles += [''] * (3 - len(titles))
    dists += [''] * (3 - len(dists))
    nn_pivoted.append({
        'document_id': doc_id,
        'nearest_neighbor_1': titles[0],
        'nearest_neighbor_2': titles[1],
        'nearest_neighbor_3': titles[2],
        'distances': str([round(d, 4) if isinstance(d, float) else d for d in dists])
    })
nn_pivoted_df = pd.DataFrame(nn_pivoted)
anom_df = pd.merge(anom_df, nn_pivoted_df, on='document_id', how='left')
anom_df = anom_df.sort_values('ensemble_rank').head(25)
anom_out = anom_df[['ensemble_rank', 'Title', 'Agency', 'File Group', 'ensemble_uniqueness', 'nearest_neighbor_1', 'nearest_neighbor_2', 'nearest_neighbor_3', 'distances']].copy()
anom_out.columns = ['rank', 'title', 'agency', 'file_group', 'ensemble_uniqueness', 'nearest_neighbor_1', 'nearest_neighbor_2', 'nearest_neighbor_3', 'distances']
anom_out.to_csv('analysis2b/anomaly_cards/anomaly_contrast_cards.csv', index=False)

with open('analysis2b/anomaly_cards/anomaly_contrast_cards.md', 'w') as f:
    f.write("# Anomaly Contrast Cards\n\nFor each top 25 anomaly, provide interpretation here.\n\n")

# 4. Cluster composition summary
purity_df = pd.read_csv('analysis-2.0/cluster_interpretation/cluster_purity.csv')
purity_out = purity_df[['cluster', 'size', 'dominant_agency', 'agency_purity', 'dominant_modality', 'modality_purity']].copy()
purity_out.to_csv('analysis2b/cluster_cards/cluster_composition_summary.csv', index=False)

# 5. Review packet with group labels
review_df = pd.read_csv('analysis-2.0/review_packet/review_sample.csv')

# Get cluster
full_rep = pd.read_csv('analysis-2.0/cluster_interpretation/cluster_representatives.csv')[['document_id', 'cluster']]
review_df = pd.merge(review_df, full_rep, on='document_id', how='left')

# Get graph_community
nodes_map = nodes_df[['document_id', 'graph_community']]
review_df = pd.merge(review_df, nodes_map, on='document_id', how='left')

# Get anomaly_rank
anom_map = pd.read_csv('analysis-2.0/anomaly_validation/top25_ensemble_anomalies.csv')[['document_id', 'ensemble_rank']]
anom_map.columns = ['document_id', 'anomaly_rank']
review_df = pd.merge(review_df, anom_map, on='document_id', how='left')

# Get usefulness_proxy_score
usefulness_map = usefulness_df[['document_id', 'usefulness_proxy_score']]
review_df = pd.merge(review_df, usefulness_map, on='document_id', how='left')

review_out = review_df[['review_group', 'Title', 'Agency', 'File Group', 'cluster', 'graph_community', 'anomaly_rank', 'usefulness_proxy_score', 'Output Path']].copy()
review_out.columns = ['review_group', 'title', 'agency', 'file_group', 'cluster', 'graph_community', 'anomaly_rank', 'usefulness_proxy_score', 'output_path']
review_out.to_csv('analysis2b/manual_review/review_sample_annotated.csv', index=False)

# 6. Create manual_review_template.csv
template_cols = [
    'file_id', 'title', 'review_group', 'cluster', 'graph_community', 'agency', 'file_group',
    'human_document_genre', 'case_or_compilation', 'single_event_or_multi_event',
    'event_date_precision', 'event_location_precision', 'primary_location',
    'witness_type', 'sensor_type', 'raw_media_present', 'object_shape', 'object_color',
    'motion_description', 'duration_available', 'altitude_speed_available',
    'official_explanation_present', 'resolution_status', 'external_verification_possible',
    'scientific_usefulness_score_0_10', 'reason_for_scientific_usefulness',
    'why_algorithm_selected_this_file', 'content_unique_or_format_unique',
    'reviewer_confidence_0_3', 'short_human_summary'
]

template_df = review_df[['document_id', 'Title', 'review_group', 'cluster', 'graph_community', 'Agency', 'File Group']].copy()
template_df.columns = ['file_id', 'title', 'review_group', 'cluster', 'graph_community', 'agency', 'file_group']

for col in template_cols:
    if col not in template_df.columns:
        template_df[col] = ''

template_df = template_df[template_cols]
template_df.to_csv('analysis2b/manual_review/manual_review_template.csv', index=False)

# Create README.md
with open('analysis2b/README.md', 'w') as f:
    f.write("# Analysis 2b: Cluster Humanization & Case-Level Evidence Coding\n\nThis phase converts technical embedding structures (clusters, bridge files, anomalies) into human-interpretable evidence families. It prepares the dataset for the final manual case-level coding phase.\n")

print("Analysis 2b artifacts created successfully.")
