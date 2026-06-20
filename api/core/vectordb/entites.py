from enum import Enum


class VectorField(Enum):
    ID = "id"
    VECTOR = "vector"
    METADATA = "metadata"
    SPARSE_VECTOR = "sparse_vector"
    CONTENT = "content"
