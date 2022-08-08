import os
import pickle
from argparse import ArgumentParser, Namespace

from data import (SequenceDataset, create_20newsgroup_data,  # noqa
                  create_hm_data)
from model import AttentiveDoc2Vec


def main() -> None:
    def parse_args() -> Namespace:
        parser = ArgumentParser()
        parser.add_argument('--num_cluster', type=int, default=10)
        parser.add_argument('--d_model', type=int, default=100)
        parser.add_argument('--batch_size', type=int, default=64)
        parser.add_argument('--epochs', type=int, default=5)
        parser.add_argument('--lr', type=float, default=0.0005)
        parser.add_argument('--verbose', action='store_true')
        parser.add_argument('--load_model', action='store_true')
        return parser.parse_args()

    def load_dataset(dataset_path: str = 'data/hm_dataset.pickle') -> SequenceDataset:
        if os.path.exists(dataset_path):
            print(f'load dataset at: {dataset_path}')
            with open(dataset_path, 'rb') as f:
                dataset: SequenceDataset = pickle.load(f)
        else:
            print(f'dataset does not exist at: {dataset_path}, create dataset')
            raw_sequences, items = create_hm_data(max_data_size=1000)
            dataset = SequenceDataset(
                raw_sequences=raw_sequences, items=items, window_size=8)
            with open(dataset_path, 'wb') as f:  # type: ignore
                pickle.dump(dataset, f)
        print('end loading dataset')
        return dataset

    args = parse_args()
    dataset = load_dataset()
    doc2vec = AttentiveDoc2Vec(
        dataset=dataset, d_model=args.d_model,
        batch_size=args.batch_size, epochs=args.epochs, lr=args.lr, model='attentive',
        model_path='weights/model_hm_meta.pt', word2vec_path='weights/word2vec_hm.model',
        verbose=args.verbose, load_model=args.load_model)
    _ = doc2vec.train()

    doc2vec.top_items(num_cluster=args.num_cluster, show_fig=True)
    _ = doc2vec.calc_coherence(num_cluster=args.num_cluster)


if __name__ == '__main__':
    main()
