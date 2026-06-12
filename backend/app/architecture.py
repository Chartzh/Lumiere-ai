# app/utils/architecture.py
# Lumiere AI, diverifikasi langsung dari model_config di lumiere_ncf.h5
# + notebook Lumiere_NCF.ipynb.
#
# Tujuan: memuat model lewat build + load_weights, sehingga TIDAK ada
# deserialisasi arsitektur (InputLayer). Error
#   "deserializing class 'InputLayer' ... 'batch_shape'"
# menjadi MUSTAHIL, baik di TF 2.15 maupun TF 2.16+ / Keras 3.

import numpy as np
from tensorflow.keras.layers import (
    Input, Embedding, Multiply, Concatenate, Dense, Flatten, Dropout,
)
from tensorflow.keras.models import Model
from tensorflow.keras.regularizers import l2

# Konstanta hasil bongkar file .h5 (JANGAN diubah kecuali retrain):
NUM_USERS = 6040       # input_dim gmf/mlp_user_embedding
NUM_MOVIES = 3706      # input_dim gmf/mlp_movie_embedding
EMBEDDING_SIZE = 32
L2_REG = 1e-4


def build_ncf_model(
    num_users: int = NUM_USERS,
    num_movies: int = NUM_MOVIES,
    embedding_size: int = EMBEDDING_SIZE,
    l2_reg: float = L2_REG,
) -> Model:
    """Bangun ulang arsitektur identik dengan saat training (nama layer sama)."""
    user_input = Input(shape=(1,), name="user_input")
    movie_input = Input(shape=(1,), name="movie_input")

    # GMF path
    user_embed_gmf = Embedding(
        num_users, embedding_size,
        embeddings_regularizer=l2(l2_reg), name="gmf_user_embedding",
    )(user_input)
    movie_embed_gmf = Embedding(
        num_movies, embedding_size,
        embeddings_regularizer=l2(l2_reg), name="gmf_movie_embedding",
    )(movie_input)
    gmf_vector = Multiply(name="gmf_product")(
        [Flatten()(user_embed_gmf), Flatten()(movie_embed_gmf)]
    )

    # MLP path
    user_embed_mlp = Embedding(
        num_users, embedding_size,
        embeddings_regularizer=l2(l2_reg), name="mlp_user_embedding",
    )(user_input)
    movie_embed_mlp = Embedding(
        num_movies, embedding_size,
        embeddings_regularizer=l2(l2_reg), name="mlp_movie_embedding",
    )(movie_input)
    mlp_vector = Concatenate(name="mlp_concat")(
        [Flatten()(user_embed_mlp), Flatten()(movie_embed_mlp)]
    )
    mlp_layer = Dense(64, activation="relu", name="mlp_dense_1")(mlp_vector)
    mlp_layer = Dropout(0.3, name="mlp_dropout_1")(mlp_layer)
    mlp_layer = Dense(32, activation="relu", name="mlp_dense_2")(mlp_layer)
    mlp_layer = Dropout(0.2, name="mlp_dropout_2")(mlp_layer)

    # Fusion & Output
    predict_vector = Concatenate(name="fusion")([gmf_vector, mlp_layer])
    output_layer = Dense(1, activation="sigmoid", name="output")(predict_vector)

    return Model(inputs=[user_input, movie_input], outputs=output_layer, name="NeuMF")


def load_ncf_model(dest_path: str) -> Model:
    """
    Muat HANYA bobot dari file .h5 ke arsitektur yang dibangun ulang.
    File sudah di-download oleh pemanggil (lifespan / late-init).

    by_name=True  -> cocokkan bobot Embedding/Dense berdasar nama layer,
                     tahan beda format Keras 2 (TF 2.15) vs Keras 3.
    skip_mismatch=False -> gagal eksplisit bila arsitektur tak cocok.
    """
    model = build_ncf_model()
    model.load_weights(dest_path, by_name=True, skip_mismatch=False)
    # Warm-up agar predict pertama tidak lambat saat request.
    model.predict([np.array([[0]]), np.array([[0]])], verbose=0)
    return model
