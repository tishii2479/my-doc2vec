from typing import List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import cm
from sklearn.decomposition import PCA
from sklearn.feature_extraction.text import TfidfTransformer
from torch import Tensor


def visualize_cluster(
    features: List[Tensor],
    num_cluster: int,
    cluster_labels: List[int],
    answer_labels: Optional[List[int]] = None
) -> None:
    r'''
    Visualize cluster to 2d
    '''
    pca = PCA(n_components=2)
    pca.fit(features)
    pca_features = pca.fit_transform(features)

    colors = cm.rainbow(np.linspace(0, 1, num_cluster))

    plt.figure()

    for i in range(pca_features.shape[0]):
        if answer_labels is not None:
            marker = '$' + str(answer_labels[i]) + '$'
        else:
            marker = '.'
        plt.scatter(x=pca_features[i, 0], y=pca_features[i, 1],
                    color=colors[cluster_labels[i]], marker=marker)
    plt.show()


def visualize_loss(
    losses: List[float]
) -> None:
    plt.plot(losses)
    plt.show()


def top_cluster_items(
    num_cluster: int,
    cluster_labels: List[int],
    sequences: List[List[int]],
    num_top_item: int,
    num_item: int
) -> List[Tuple[List[int], List[float]]]:
    r'''
    Args:
        num_cluster: number of clusters
        topic_indicies: list of sequence indicies for each topic
            shape: (num_topic, len(sequence_indicies))
        sequences: all sequence data
        num_top_item: number of item to list
        num_item: number of items in data
    Return:
        top items for each cluster
            shape: (num_topic, num_top_item)
    '''
    item_counts = np.zeros((num_cluster, num_item))
    cluster_size = [0] * num_cluster
    for i, sequence in enumerate(sequences):
        cluster_size[cluster_labels[i]] += 1
        for item_index in set(sequence):
            item_counts[cluster_labels[i]][item_index] += 1

    transformer = TfidfTransformer()
    tf_idf = transformer.fit_transform(item_counts).toarray()

    top_items = []
    for cluster in range(num_cluster):
        # Get item index of top items which has largest item_count
        top_items_for_cluster = list(
            tf_idf[cluster].argsort()[::-1][:num_top_item])
        top_item_counts = np.sort(tf_idf[cluster])[::-1][:num_top_item]
        top_items_for_cluster_counts = \
            list(top_item_counts / cluster_size[cluster])
        top_items.append((top_items_for_cluster, top_items_for_cluster_counts))
    return top_items
