from __future__ import annotations

import importlib.util
from typing import Any

import numpy as np

from .errors import AlgorithmInputError
from .graph import build_nx_graph
from .results import chart, overlay, table


def _adjacency(graph: dict[str, Any], *, include_attributes: bool = False) -> tuple[list[Any], np.ndarray, int]:
    network = build_nx_graph(graph)
    nodes = list(sorted(network.nodes, key=str))
    if len(nodes) < 2:
        raise AlgorithmInputError("嵌入聚类至少需要 2 个节点。")
    matrix = np.asarray(
        [[float(network[source][target].get("weight", 1)) if network.has_edge(source, target) else 0.0 for target in nodes] for source in nodes],
        dtype=np.float64,
    )
    matrix += np.eye(len(nodes), dtype=np.float64)
    maximum = float(matrix.max()) or 1.0
    matrix = matrix / maximum
    attribute_dimensions = 0
    if include_attributes:
        rows = []
        expected: int | None = None
        node_lookup = {node["id"]: node for node in graph["nodes"]}
        for node in nodes:
            features = node_lookup[str(node)].get("attributes", {}).get("features")
            if not isinstance(features, list) or not features:
                raise AlgorithmInputError("AE 属性案例的每个节点都必须包含 features 数组。", path=f"nodes.{node}.attributes.features")
            if expected is None:
                expected = len(features)
            if len(features) != expected:
                raise AlgorithmInputError("节点 features 维数必须一致。", path=f"nodes.{node}.attributes.features")
            try:
                row = [float(value) for value in features]
            except (TypeError, ValueError) as exc:
                raise AlgorithmInputError("节点 features 必须是数值数组。", path=f"nodes.{node}.attributes.features") from exc
            if not np.isfinite(row).all():
                raise AlgorithmInputError("节点 features 必须是有限数值。", path=f"nodes.{node}.attributes.features")
            rows.append(row)
        attribute_dimensions = expected or 0
        features_matrix = np.asarray(rows, dtype=np.float64)
        scale = np.max(np.abs(features_matrix), axis=0)
        scale[scale == 0] = 1
        matrix = np.concatenate([matrix, features_matrix / scale], axis=1)
    return nodes, matrix, attribute_dimensions


def _kmeans(values: np.ndarray, clusters: int, seed: int | None, max_iterations: int = 100) -> tuple[np.ndarray, int]:
    n = len(values)
    if not np.isfinite(values).all():
        raise AlgorithmInputError("嵌入向量必须全部是有限数值。", path="embeddings")
    if not 1 <= clusters <= n:
        raise AlgorithmInputError(f"clusters 必须在 1–{n} 之间。", path="parameters.clusters")
    distinct = np.unique(values, axis=0)
    if clusters > len(distinct):
        raise AlgorithmInputError(f"聚类数 {clusters} 超过不同嵌入向量数 {len(distinct)}。", path="parameters.clusters")
    rng = np.random.default_rng(seed)
    first = int(rng.integers(0, n))
    indices = [first]
    while len(indices) < clusters:
        distance = np.min(np.stack([np.sum((values - values[index]) ** 2, axis=1) for index in indices]), axis=0)
        distance[indices] = -1
        indices.append(int(np.argmax(distance)))
    centroids = values[indices].copy()
    labels = np.zeros(n, dtype=int)
    for iteration in range(1, max_iterations + 1):
        distances = np.sum((values[:, None, :] - centroids[None, :, :]) ** 2, axis=2)
        updated = np.argmin(distances, axis=1)
        # Deterministic empty-cluster repair keeps the requested k represented.
        for cluster in range(clusters):
            if not np.any(updated == cluster):
                nearest = np.min(distances, axis=1)
                counts = np.bincount(updated, minlength=clusters)
                donors = np.flatnonzero(counts[updated] > 1)
                if not len(donors):
                    raise AlgorithmInputError("无法在不清空已有聚类的前提下修复空聚类。", code="algorithm_failure")
                candidate = int(donors[np.argmax(nearest[donors])])
                updated[candidate] = cluster
        new_centroids = np.stack([values[updated == cluster].mean(axis=0) for cluster in range(clusters)])
        if np.array_equal(labels, updated) and np.allclose(centroids, new_centroids):
            labels = updated
            if set(labels.tolist()) != set(range(clusters)):
                raise AlgorithmInputError("聚类修复后仍存在空聚类。", code="algorithm_failure")
            return labels, iteration
        labels, centroids = updated, new_centroids
    if set(labels.tolist()) != set(range(clusters)):
        raise AlgorithmInputError("聚类迭代结束后仍存在空聚类。", code="algorithm_failure")
    return labels, max_iterations


def _ae(matrix: np.ndarray, dimensions: int, epochs: int, learning_rate: float, seed: int | None) -> tuple[np.ndarray, list[float]]:
    rng = np.random.default_rng(seed)
    samples, inputs = matrix.shape
    encoder = rng.normal(0, 1 / max(1, np.sqrt(inputs)), size=(inputs, dimensions))
    decoder = rng.normal(0, 1 / max(1, np.sqrt(dimensions)), size=(dimensions, inputs))
    losses: list[float] = []
    for _ in range(epochs):
        embedding = np.tanh(matrix @ encoder)
        reconstruction = embedding @ decoder
        error = reconstruction - matrix
        losses.append(float(np.mean(error ** 2)))
        gradient_decoder = (embedding.T @ error) * (2 / (samples * inputs))
        gradient_embedding = (error @ decoder.T) * (2 / (samples * inputs))
        gradient_encoder = matrix.T @ (gradient_embedding * (1 - embedding ** 2))
        decoder -= learning_rate * np.clip(gradient_decoder, -5, 5)
        encoder -= learning_rate * np.clip(gradient_encoder, -5, 5)
    return np.tanh(matrix @ encoder), losses


def _convolve_rows(matrix: np.ndarray, kernels: np.ndarray, bias: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    n = matrix.shape[1]
    width = kernels.shape[1]
    pad = width // 2
    padded = np.pad(matrix, ((0, 0), (pad, pad)))
    convolution = np.empty((len(matrix), len(kernels), n), dtype=np.float64)
    for position in range(n):
        window = padded[:, position:position + width]
        convolution[:, :, position] = window @ kernels.T + bias
    activated = np.maximum(convolution, 0)
    return convolution, activated.mean(axis=2)


def _cnn(matrix: np.ndarray, dimensions: int, epochs: int, learning_rate: float, seed: int | None) -> tuple[np.ndarray, list[float]]:
    rng = np.random.default_rng(seed)
    n = len(matrix)
    width = min(3, n if n % 2 else max(1, n - 1))
    kernels = rng.normal(0, 0.3, size=(dimensions, width))
    bias = np.zeros(dimensions, dtype=np.float64)
    decoder = rng.normal(0, 1 / max(1, np.sqrt(dimensions)), size=(dimensions, n))
    losses: list[float] = []
    pad = width // 2
    padded = np.pad(matrix, ((0, 0), (pad, pad)))
    for _ in range(epochs):
        convolution, embedding = _convolve_rows(matrix, kernels, bias)
        reconstruction = embedding @ decoder
        error = reconstruction - matrix
        losses.append(float(np.mean(error ** 2)))
        gradient_decoder = (embedding.T @ error) * (2 / (n * n))
        gradient_embedding = (error @ decoder.T) * (2 / (n * n))
        gradient_convolution = gradient_embedding[:, :, None] * (convolution > 0) / n
        gradient_kernels = np.zeros_like(kernels)
        for position in range(n):
            window = padded[:, position:position + width]
            gradient_kernels += gradient_convolution[:, :, position].T @ window
        gradient_kernels *= 1 / n
        gradient_bias = gradient_convolution.sum(axis=(0, 2)) / n
        decoder -= learning_rate * np.clip(gradient_decoder, -5, 5)
        kernels -= learning_rate * np.clip(gradient_kernels, -5, 5)
        bias -= learning_rate * np.clip(gradient_bias, -5, 5)
    _, embedding = _convolve_rows(matrix, kernels, bias)
    return embedding, losses


def _torch_gcn(matrix: np.ndarray, dimensions: int, epochs: int, learning_rate: float, seed: int | None) -> tuple[np.ndarray, list[float]]:
    import torch

    torch.manual_seed(0 if seed is None else seed)
    torch.use_deterministic_algorithms(True)
    adjacency = torch.tensor(matrix, dtype=torch.float32, device="cpu")
    degree = adjacency.sum(dim=1)
    normalized = torch.diag(torch.pow(degree.clamp_min(1e-12), -0.5)) @ adjacency @ torch.diag(torch.pow(degree.clamp_min(1e-12), -0.5))
    encoder = torch.nn.Parameter(torch.randn(len(matrix), dimensions) / max(1, len(matrix) ** 0.5))
    decoder = torch.nn.Parameter(torch.randn(dimensions, len(matrix)) / max(1, dimensions ** 0.5))
    optimizer = torch.optim.Adam([encoder, decoder], lr=learning_rate)
    losses: list[float] = []
    for _ in range(epochs):
        optimizer.zero_grad()
        embedding = torch.relu(normalized @ encoder)
        reconstruction = embedding @ decoder
        loss = torch.mean((reconstruction - adjacency) ** 2)
        loss.backward()
        optimizer.step()
        losses.append(float(loss.detach()))
    return torch.relu(normalized @ encoder).detach().numpy().astype(np.float64), losses


def _torch_gat(matrix: np.ndarray, dimensions: int, epochs: int, learning_rate: float, seed: int | None) -> tuple[np.ndarray, list[float]]:
    import torch
    from torch_geometric.nn import GATConv

    torch.manual_seed(0 if seed is None else seed)
    rows, columns = np.nonzero(matrix)
    edge_index = torch.tensor(np.vstack([rows, columns]), dtype=torch.long)
    features = torch.eye(len(matrix), dtype=torch.float32)
    target = torch.tensor(matrix, dtype=torch.float32)
    layer = GATConv(len(matrix), dimensions, heads=1, concat=False, dropout=0)
    decoder = torch.nn.Linear(dimensions, len(matrix), bias=False)
    optimizer = torch.optim.Adam(list(layer.parameters()) + list(decoder.parameters()), lr=learning_rate)
    losses: list[float] = []
    for _ in range(epochs):
        optimizer.zero_grad()
        embedding = torch.relu(layer(features, edge_index))
        reconstruction = decoder(embedding)
        loss = torch.mean((reconstruction - target) ** 2)
        loss.backward()
        optimizer.step()
        losses.append(float(loss.detach()))
    return torch.relu(layer(features, edge_index)).detach().numpy().astype(np.float64), losses


def run_embedding(key: str, graph: dict[str, Any], params: dict[str, Any], seed: int | None) -> dict[str, Any]:
    has_features = key == "embedding.ae" and any(node.get("attributes", {}).get("features") for node in graph["nodes"])
    nodes, matrix, attribute_dimensions = _adjacency(graph, include_attributes=has_features)
    dimensions = min(params.get("embedding_dim", 2), len(nodes))
    epochs = params.get("epochs", 100)
    learning_rate = params.get("learning_rate", 0.05)
    if key == "embedding.ae":
        embedding, losses = _ae(matrix, dimensions, epochs, learning_rate, seed)
        implementation = "numpy_dense_autoencoder"
    elif key == "embedding.cnn":
        embedding, losses = _cnn(matrix, dimensions, epochs, learning_rate, seed)
        implementation = "numpy_conv1d_autoencoder"
    elif key == "embedding.gcn":
        if importlib.util.find_spec("torch") is None:
            raise AlgorithmInputError("GCN 能力不可用：未安装可选依赖 torch。", code="capability_unavailable", path="algorithm")
        embedding, losses = _torch_gcn(matrix, dimensions, epochs, learning_rate, seed)
        implementation = "torch_cpu_gcn"
    elif key == "embedding.gat":
        if importlib.util.find_spec("torch_geometric") is None:
            raise AlgorithmInputError("GAT 能力不可用：未安装可选依赖 torch_geometric (torch-geometric)。", code="capability_unavailable", path="algorithm")
        embedding, losses = _torch_gat(matrix, dimensions, epochs, learning_rate, seed)
        implementation = "torch_geometric_cpu_gat"
    else:
        raise KeyError(key)
    labels, kmeans_iterations = _kmeans(embedding, params["clusters"], seed)
    rows = [
        {"node": str(node), "embedding": [float(value) for value in embedding[index]], "cluster": int(labels[index])}
        for index, node in enumerate(nodes)
    ]
    scatter = [
        {"x": row["embedding"][0], "y": row["embedding"][1] if len(row["embedding"]) > 1 else 0.0, "label": row["node"], "cluster": row["cluster"]}
        for row in rows
    ]
    return {
        "tables": [table("embeddings", "节点嵌入与聚类", rows), table("training", "训练损失", [{"epoch": index + 1, "loss": loss} for index, loss in enumerate(losses)])],
        "overlays": [overlay("embedding_clusters", node_styles={row["node"]: {"community": row["cluster"]} for row in rows})],
        "charts": [chart("embedding_scatter", "scatter", [{"name": "embedding", "data": scatter}]), chart("training_loss", "line", [{"name": "loss", "data": [{"x": index + 1, "y": loss} for index, loss in enumerate(losses)]}])],
        "provenance": {"device": "cpu", "trained": True, "epochs": epochs, "final_loss": losses[-1], "implementation": implementation, "kmeans_iterations": kmeans_iterations, "node_attribute_dimensions": attribute_dimensions},
    }
