import collections
from typing import Dict, List, Optional, Tuple

import numpy as np
from sklearn.cluster import KMeans

from config import ModelConfig, TrainerConfig
from data import SequenceDatasetManager
from trainers import GensimTrainer, PyTorchTrainer, Trainer
from util import (
    calc_cluster_occurence_array,
    calc_coherence,
    calc_sequence_occurence_array,
    to_full_meta_value,
    top_cluster_items,
    visualize_cluster,
    visualize_loss,
)


class Analyst:
    trainer: Trainer

    def __init__(
        self,
        dataset_manager: SequenceDatasetManager,
        trainer_config: TrainerConfig,
        model_config: ModelConfig,
    ):
        self.dataset_manager = dataset_manager
        self.trainer_config = trainer_config
        self.model_config = model_config

        match self.trainer_config.model_name:
            case "attentive":
                self.trainer = PyTorchTrainer(
                    dataset_manager=self.dataset_manager,
                    trainer_config=trainer_config,
                    model_config=model_config,
                )
            case "doc2vec":
                self.trainer = GensimTrainer(
                    dataset_manager=self.dataset_manager,
                    trainer_config=trainer_config,
                    model_config=model_config,
                )
            case _:
                print(f"invalid model_name: {trainer_config.model_name}")
                assert False

    def fit(self, show_fig: bool = True) -> List[float]:
        losses = self.trainer.fit()
        if show_fig and len(losses) > 0:
            visualize_loss(losses)
        return losses

    def cluster_embeddings(
        self, num_cluster: int, show_fig: bool = True, target: str = "sequence"
    ) -> List[int]:
        """Cluster using K-means

        Args:
            num_cluster (int): number of clusters
            show_fig (bool, optional): visualize cluster. Defaults to True.

        Returns:
            List[int]: cluster labels
        """
        kmeans = KMeans(n_clusters=num_cluster)
        match target:
            case "sequence":
                embeddings = self.seq_embeddings.values()
            case "item":
                embeddings = self.item_embeddings.values()
            case _:
                print(f"Invalid target: {target}")
                assert False

        h_seq = np.array(list(embeddings))
        print(f"Start k-means: {h_seq.shape}")
        kmeans.fit(h_seq)
        print("End k-means")
        cluster_labels: List[int] = kmeans.labels_

        if show_fig:
            visualize_cluster(list(h_seq), num_cluster, cluster_labels)

        return cluster_labels

    def top_items(
        self,
        num_cluster: int = 10,
        num_top_item: int = 10,
        item_name_dict: Optional[Dict[str, str]] = None,
        show_fig: bool = False,
    ) -> None:
        cluster_labels = self.cluster_embeddings(
            num_cluster, show_fig=show_fig, target="sequence"
        )
        seq_cnt = collections.Counter(cluster_labels)
        cluster_occurence_array, cluster_size = calc_cluster_occurence_array(
            num_cluster=num_cluster,
            cluster_labels=cluster_labels,
            sequences=self.dataset_manager.train_dataset.sequences,
            num_item=self.dataset_manager.num_item,
        )
        top_item_infos = top_cluster_items(
            num_cluster=num_cluster,
            cluster_occurence_array=cluster_occurence_array,
            cluster_size=cluster_size,
            num_top_item=num_top_item,
        )

        for cluster, (top_items, ratios) in enumerate(top_item_infos):
            print(f"Top items for cluster {cluster} (size {seq_cnt[cluster]}):")
            for index, item in enumerate(
                self.dataset_manager.item_le.inverse_transform(top_items)
            ):
                if item_name_dict is not None:
                    name = item_name_dict[item]
                else:
                    name = item
                print(name + " " + str(ratios[index]))
            print()

    def calc_coherence(
        self, num_cluster: int = 10, num_top_item: int = 10, show_fig: bool = False
    ) -> float:
        """Calculate coherence

        Args:
            num_cluster (int, optional): Number of clusters. Defaults to 10.
            num_top_item (int, optional): Number of top K items. Defaults to 10.
            show_fig (bool, optional): visualize. Defaults to False.

        Returns:
            float: coherence
        """
        # TODO: refactor
        cluster_labels = self.cluster_embeddings(
            num_cluster, show_fig=show_fig, target="sequence"
        )
        cluster_occurence_array, cluster_size = calc_cluster_occurence_array(
            num_cluster=num_cluster,
            cluster_labels=cluster_labels,
            sequences=self.dataset_manager.train_dataset.sequences,
            num_item=self.dataset_manager.num_item,
        )
        sequence_occurence_array = calc_sequence_occurence_array(
            sequences=self.dataset_manager.train_dataset.sequences,
            num_item=self.dataset_manager.num_item,
        )
        top_item_infos = top_cluster_items(
            num_cluster=num_cluster,
            cluster_occurence_array=cluster_occurence_array,
            cluster_size=cluster_size,
            num_top_item=num_top_item,
        )
        coherence = calc_coherence(
            sequence_occurence_array=sequence_occurence_array,
            top_item_infos=top_item_infos,
        )
        print(f"coherence: {coherence}")
        return coherence

    def attention_weights_to_meta(
        self, seq_index: int, meta_name: str, num_top_values: int = 5
    ) -> None:
        meta_values = list(self.dataset_manager.item_meta_dict[meta_name])
        meta_names = [to_full_meta_value(meta_name, value) for value in meta_values]
        meta_indicies = self.dataset_manager.item_meta_le.transform(meta_names)
        weight = list(
            self.trainer.attention_weight_to_meta(seq_index, meta_indicies)[0]
        )
        meta_weights = [(weight[i], meta_values[i]) for i in range(len(meta_values))]
        print(f"attention weights of seq: {seq_index} for meta: {meta_name}")
        for weight, name in sorted(meta_weights)[::-1][:num_top_values]:
            print(f"{weight.item():.4f}", name)

    def attention_weights_to_sequence(
        self, seq_index: int, num_recent_items: int = 100
    ) -> None:
        item_indicies = self.dataset_manager.train_dataset.sequences[seq_index][
            -num_recent_items:
        ]
        item_names = self.dataset_manager.item_le.inverse_transform(item_indicies)
        weight = list(
            self.trainer.attention_weight_to_item(seq_index, item_indicies)[0]
        )
        item_weights = [(weight[i], item_names[i]) for i in range(num_recent_items)]
        print(f"item weights of seq: {seq_index}")
        for weight, name in sorted(item_weights)[::-1]:
            print(f"{weight.item():.4f}", self.dataset_manager.item_metadata[name])

    def prediction_accuracy(
        self,
    ) -> float:
        return self.trainer.eval()

    def similar_items(
        self, item_index: int, num_items: int = 10
    ) -> List[Tuple[float, str]]:
        item_name = self.dataset_manager.item_le.inverse_transform([item_index])[0]

        item_embedding = self.item_embeddings
        similar_items: List[Tuple[float, str]] = []

        h = item_embedding[item_name]

        item_names = self.dataset_manager.item_le.inverse_transform(
            list(range(self.dataset_manager.num_item))
        )

        for i, item_name in enumerate(item_names):
            if i == item_index:
                continue
            h_item = item_embedding[item_name]
            distance = np.sum((h - h_item) ** 2)
            similar_items.append((distance, item_name))

        similar_items.sort()

        print(f"{item_name} {self.dataset_manager.item_metadata[item_name]}")
        for distance, item_name in similar_items[:num_items]:
            item = self.dataset_manager.item_metadata[item_name]
            print(f"Item: {item_name} {item['prod_name']}, Distance: {distance}")

        return similar_items[:num_items]

    @property
    def seq_embeddings(self) -> Dict[str, np.ndarray]:
        return self.trainer.seq_embedding

    @property
    def item_embeddings(self) -> Dict[str, np.ndarray]:
        return self.trainer.item_embedding
