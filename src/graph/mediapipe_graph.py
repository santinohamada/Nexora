import numpy as np
from collections import deque


class MediaPipeGraph:
    def __init__(self):
        self.num_node = 75
        self.center = 0  # Nariz como centro

        self.edge = self._get_edge()
        self.A = self._get_adjacency(self.edge, self.num_node)

    def _get_edge(self):
        # 1. Conexiones de Pose (MediaPipe) - COMPLETAS
        #    Includes bridge edges so BFS from center (nariz=0) reaches ALL 75 nodes.
        pose_edges = [
            # Face
            (0, 1), (1, 2), (2, 3), (3, 7),     # Right eye → right ear
            (0, 4), (4, 5), (5, 6), (6, 8),     # Left eye → left ear
            (0, 9), (0, 10), (9, 10),            # Mouth → Nose
            # Face periphery (nodes 17-22 in MediaPipe)
            (7, 17), (8, 18),                     # Ears → Pinky side ear
            (9, 19), (10, 20),                    # Mouth → Mouth corners
            (9, 21), (10, 22),                    # Mouth → Extra mouth points
            # Face → Body bridge
            (0, 11), (0, 12),                     # Nose → Shoulders
            # Upper body
            (11, 12),                              # Hombros
            (11, 13), (13, 15),                    # Brazo Izquierdo
            (12, 14), (14, 16),                    # Brazo Derecho
            # Torso
            (11, 23), (12, 24), (23, 24),          # Cadera
            # Legs (included for graph connectivity, even if not primary features)
            (23, 25), (25, 27), (27, 29), (29, 31),  # Pierna Izquierda
            (24, 26), (26, 28), (28, 30), (30, 32),  # Pierna Derecha
        ]

        # 2. Conexiones de la Mano Izquierda (Nodos 33 al 53)
        lh_offset = 33
        lh_edges = [
            (0, 1), (1, 2), (2, 3), (3, 4),
            (0, 5), (5, 6), (6, 7), (7, 8),
            (5, 9), (9, 10), (10, 11), (11, 12),
            (9, 13), (13, 14), (14, 15), (15, 16),
            (13, 17), (17, 18), (18, 19), (19, 20),
            (0, 17)
        ]
        lh_edges = [(i + lh_offset, j + lh_offset) for (i, j) in lh_edges]

        # 3. Conexiones de la Mano Derecha (Nodos 54 al 74)
        rh_offset = 54
        rh_edges = [
            (0, 1), (1, 2), (2, 3), (3, 4),
            (0, 5), (5, 6), (6, 7), (7, 8),
            (5, 9), (9, 10), (10, 11), (11, 12),
            (9, 13), (13, 14), (14, 15), (15, 16),
            (13, 17), (17, 18), (18, 19), (19, 20),
            (0, 17)
        ]
        rh_edges = [(i + rh_offset, j + rh_offset) for (i, j) in rh_edges]

        # 4. Conectar Pose con Manos
        # Muñeca Izquierda (15) conectada a la base de la mano izquierda (33)
        # Muñeca Derecha (16) conectada a la base de la mano derecha (54)
        bridge_edges = [(15, 33), (16, 54)]

        edges = pose_edges + lh_edges + rh_edges + bridge_edges
        return edges

    def _get_adjacency(self, edges, num_node):
        A = np.zeros((num_node, num_node))
        for i in range(num_node):
            A[i, i] = 1

        for (i, j) in edges:
            A[i, j] = 1
            A[j, i] = 1

        return A

    def _get_hop_distance(self, edges, num_node, center):
        """BFS from center to compute hop distance for each node."""
        adj = {i: [] for i in range(num_node)}
        for (i, j) in edges:
            adj[i].append(j)
            adj[j].append(i)

        hop = np.full(num_node, -1, dtype=int)
        hop[center] = 0
        queue = deque([center])

        while queue:
            node = queue.popleft()
            for neighbor in adj[node]:
                if hop[neighbor] == -1:
                    hop[neighbor] = hop[node] + 1
                    queue.append(neighbor)

        return hop

    def _normalize_adjacency(self, A):
        """Row-normalize an adjacency matrix."""
        Dl = np.sum(A, axis=1)
        Dn = np.zeros_like(A)
        for i in range(A.shape[0]):
            if Dl[i] > 0:
                Dn[i, i] = Dl[i] ** (-1)
        return np.dot(Dn, A)

    def get_spatial_graph(self):
        """
        Spatial partitioning strategy (K=3):
          A[0] = Identity (self-loops only)
          A[1] = Centripetal subset (neighbor closer to center than current node)
          A[2] = Centrifugal subset (neighbor farther from center or equal distance)

        Each partition is row-normalized independently.
        Output shape: (3, num_node, num_node)
        """
        num_node = self.num_node
        hop = self._get_hop_distance(self.edge, num_node, self.center)

        # Partition 0: Identity (self-loops)
        A_identity = np.eye(num_node)

        # Partition 1: Centripetal (inward — neighbor is closer to center)
        A_centripetal = np.zeros((num_node, num_node))

        # Partition 2: Centrifugal (outward — neighbor is farther or same distance)
        A_centrifugal = np.zeros((num_node, num_node))

        for (i, j) in self.edge:
            # For edge (i, j): from perspective of node i, is j closer or farther?
            if hop[j] >= 0 and hop[i] >= 0:
                if hop[j] < hop[i]:
                    # j is closer to center than i → centripetal from i's view
                    A_centripetal[i, j] = 1
                    # from j's view, i is farther → centrifugal
                    A_centrifugal[j, i] = 1
                elif hop[j] > hop[i]:
                    # j is farther from center than i → centrifugal from i's view
                    A_centrifugal[i, j] = 1
                    # from j's view, i is closer → centripetal
                    A_centripetal[j, i] = 1
                else:
                    # Same hop distance → put in centrifugal (convention)
                    A_centrifugal[i, j] = 1
                    A_centrifugal[j, i] = 1
            else:
                # Disconnected node — put in centrifugal as fallback
                A_centrifugal[i, j] = 1
                A_centrifugal[j, i] = 1

        # Normalize each partition independently
        A_identity = self._normalize_adjacency(A_identity)
        A_centripetal = self._normalize_adjacency(A_centripetal)
        A_centrifugal = self._normalize_adjacency(A_centrifugal)

        return np.stack([A_identity, A_centripetal, A_centrifugal], axis=0)


if __name__ == '__main__':
    graph = MediaPipeGraph()
    A = graph.get_spatial_graph()
    print(f"Grafo generado exitosamente. Shape de la matriz de adyacencia: {A.shape}")
    print(f"  Partition 0 (Identity): {A[0].sum():.0f} connections")
    print(f"  Partition 1 (Centripetal): {A[1].sum():.1f} connections")
    print(f"  Partition 2 (Centrifugal): {A[2].sum():.1f} connections")
