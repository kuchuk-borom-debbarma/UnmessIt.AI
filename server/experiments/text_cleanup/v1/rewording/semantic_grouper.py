import os
import sys
import numpy as np
import spacy
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering

# Load the lightweight semantic embedding model
MODEL_NAME = "all-MiniLM-L6-v2"

# Load spacy model for entity masking
try:
    nlp = spacy.load("en_core_web_sm", disable=["parser", "lemmatizer", "textcat"])
except OSError:
    import subprocess
    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load("en_core_web_sm", disable=["parser", "lemmatizer", "textcat"])

def group_sentences_semantically(text: str, distance_threshold: float = 1.0) -> str:
    """
    Groups atomic sentences into paragraphs based on their semantic context.
    
    Args:
        text (str): The multiline string of atomic sentences.
        distance_threshold (float): The threshold for agglomerative clustering.
                                    Higher means larger/fewer paragraphs.
                                    Lower means smaller/more paragraphs.
                                    
    Returns:
        str: The clustered sentences formatted into paragraphs.
    """
    sentences = [line.strip() for line in text.split('\n') if line.strip()]
    
    if not sentences:
        return ""
    if len(sentences) == 1:
        return sentences[0]
        
    print(f"\n[SEMANTIC GROUPER] Masking entities in {len(sentences)} sentences...")
    masked_sentences = []
    for sent in sentences:
        doc = nlp(sent)
        masked_sent = sent
        # Replace PERSON entities with a placeholder so clustering ignores names
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                masked_sent = masked_sent.replace(ent.text, "[PERSON]")
        masked_sentences.append(masked_sent)
        
    print(f"[SEMANTIC GROUPER] Loading {MODEL_NAME} model...")
    model = SentenceTransformer(MODEL_NAME)
    
    print(f"[SEMANTIC GROUPER] Encoding sentences...")
    embeddings = model.encode(masked_sentences)
    
    # Calculate pairwise cosine distances manually to apply chronological anchoring
    from sklearn.metrics.pairwise import cosine_distances
    distances = cosine_distances(embeddings)
    
    # Chronological Anchoring: 
    # If two sentences are sequentially adjacent, artificially reduce their distance 
    # to encourage them to stay in the same cluster unless they are wildly different.
    for i in range(len(distances) - 1):
        distances[i, i+1] *= 0.6  # Reduce distance between neighbors by 40%
        distances[i+1, i] *= 0.6
        
    print(f"[SEMANTIC GROUPER] Clustering with distance threshold {distance_threshold}...")
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=distance_threshold,
        metric="precomputed",
        linkage="average"
    )
    
    cluster_labels = clustering.fit_predict(distances)
    
    # Group sentences by their cluster label
    clusters = {}
    for idx, label in enumerate(cluster_labels):
        if label not in clusters:
            clusters[label] = []
        clusters[label].append((idx, sentences[idx]))
        
    # Order clusters by the appearance of their FIRST sentence
    # This preserves the general narrative flow of the original transcript
    ordered_clusters = sorted(clusters.values(), key=lambda cluster_sentences: cluster_sentences[0][0])
    
    # Format into paragraphs
    paragraphs = []
    for cluster_sentences in ordered_clusters:
        # Keep sentences within a cluster in their original chronological order
        cluster_sentences.sort(key=lambda x: x[0])
        paragraph_text = " ".join([sent for _, sent in cluster_sentences])
        paragraphs.append(paragraph_text)
        
    final_output = "\n\n".join(paragraphs)
    return final_output

if __name__ == "__main__":
    # Test script
    sample = "I ordered a cake.\nThe API failed to deploy.\nWe should check the logs.\nWhere is the dessert?"
    print(group_sentences_semantically(sample, distance_threshold=0.5))
