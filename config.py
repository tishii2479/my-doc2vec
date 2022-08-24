class TrainerConfig:
    model_name: str
    epochs: int
    batch_size: int
    load_model: bool
    model_path: str
    verbose: bool


class ModelConfig:
    d_model: int
    window_size: int
    negative_sample_size: int
    lr: float
    use_learnable_embedding: bool
