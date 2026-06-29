import torch
import torch.nn as nn


class CTRGC(nn.Module):
    """
    Channel-wise Topology Refinement Graph Convolution (CTR-GC)
    Supports K-partition spatial graph (K=3: identity, centripetal, centrifugal).
    """
    def __init__(self, in_channels, out_channels, num_subset=3, rel_reduction=8):
        super(CTRGC, self).__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.num_subset = num_subset

        # Avoid zero from integer division with small initial channels (e.g., 4 // 8)
        inter_channels = max(1, in_channels // rel_reduction)

        # Per-subset convolutions for channel-wise topology refinement
        self.conv1 = nn.ModuleList([
            nn.Conv2d(in_channels, inter_channels, kernel_size=1)
            for _ in range(num_subset)
        ])
        self.conv2 = nn.ModuleList([
            nn.Conv2d(in_channels, inter_channels, kernel_size=1)
            for _ in range(num_subset)
        ])
        self.conv3 = nn.ModuleList([
            nn.Conv2d(in_channels, out_channels, kernel_size=1)
            for _ in range(num_subset)
        ])
        self.conv4 = nn.ModuleList([
            nn.Conv2d(inter_channels, out_channels, kernel_size=1)
            for _ in range(num_subset)
        ])

        # Learnable alpha per subset to balance static vs dynamic graph
        self.alpha = nn.ParameterList([
            nn.Parameter(torch.zeros(1)) for _ in range(num_subset)
        ])

        self.bn = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x, A):
        # A shape: (K, V, V) where K = num_subset
        N, C, T, V = x.size()
        out = None

        for k in range(self.num_subset):
            # Channel-wise topology branches
            x1 = self.conv1[k](x).mean(dim=2)  # Temporal pooling → (N, C_red, V)
            x2 = self.conv2[k](x).mean(dim=2)

            # Dynamic affinity matrix (V, V) per channel
            x1 = x1.unsqueeze(-1)   # (N, C_red, V, 1)
            x2 = x2.unsqueeze(-2)   # (N, C_red, 1, V)
            B = torch.matmul(x1, x2)  # (N, C_red, V, V)
            B = self.conv4[k](B)       # (N, C_out, V, V)

            # Combine static partition A[k] with dynamic topology B
            A_k = A[k].unsqueeze(0).unsqueeze(0)  # (1, 1, V, V)
            A_dyn = A_k + self.alpha[k] * B

            # Feature transform + graph multiply
            x3 = self.conv3[k](x)  # (N, C_out, T, V)
            z = torch.einsum('nctv,ncvw->nctw', x3, A_dyn)

            out = z if out is None else out + z

        return self.relu(self.bn(out))


class TCN(nn.Module):
    """
    Temporal Convolutional Network (TCN)
    Processes information across the temporal (frame) dimension.
    """
    def __init__(self, in_channels, out_channels, kernel_size=9, stride=1):
        super(TCN, self).__init__()
        padding = (kernel_size - 1) // 2
        self.conv = nn.Conv2d(
            in_channels, out_channels,
            kernel_size=(kernel_size, 1),
            stride=(stride, 1),
            padding=(padding, 0)
        )
        self.bn = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        return self.relu(self.bn(self.conv(x)))


class CTRGCNBlock(nn.Module):
    def __init__(self, in_channels, out_channels, num_subset=3, stride=1, residual=True):
        super(CTRGCNBlock, self).__init__()
        self.gcn = CTRGC(in_channels, out_channels, num_subset=num_subset)
        self.tcn = TCN(out_channels, out_channels, stride=stride)

        if not residual or in_channels != out_channels or stride != 1:
            self.residual = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, stride=(stride, 1)),
                nn.BatchNorm2d(out_channels)
            )
        else:
            self.residual = lambda x: x

        self.relu = nn.ReLU(inplace=True)

    def forward(self, x, A):
        res = self.residual(x)
        x = self.gcn(x, A)
        x = self.tcn(x)
        return self.relu(x + res)


class CTRGCNStream(nn.Module):
    """
    A single stream of the network (Joint or Bone).
    """
    def __init__(self, num_class, num_point=75, in_channels=4, num_subset=3, base_channels=16):
        super(CTRGCNStream, self).__init__()

        # Initial data normalization
        self.data_bn = nn.BatchNorm1d(in_channels * num_point)

        # Network layers (compact for LSA-64 scale)
        self.l1 = CTRGCNBlock(in_channels, base_channels, num_subset=num_subset, residual=False)
        self.l2 = CTRGCNBlock(base_channels, base_channels, num_subset=num_subset)
        self.l3 = CTRGCNBlock(base_channels, base_channels * 2, num_subset=num_subset, stride=2)
        self.l4 = CTRGCNBlock(base_channels * 2, base_channels * 4, num_subset=num_subset, stride=2)

        # Final classifier
        self.drop = nn.Dropout(0.5)
        self.fc = nn.Linear(base_channels * 4, num_class)

    def forward(self, x, A):
        # x input shape: (Batch, Frames, Nodes, Channels) → (N, T, V, C)
        x = x.permute(0, 3, 1, 2).contiguous()
        N, C, T, V = x.size()

        # Initial normalization
        x = x.view(N, C * V, T)
        x = self.data_bn(x)
        x = x.view(N, C, T, V)

        # CTR-GCN blocks
        x = self.l1(x, A)
        x = self.l2(x, A)
        x = self.l3(x, A)
        x = self.l4(x, A)

        # Global Average Pooling
        x = x.mean(dim=[2, 3])

        # Dropout + prediction
        x = self.drop(x)
        return self.fc(x)


class TwoStreamModel(nn.Module):
    """
    Two-Stream Architecture (Joint + Bone).
    """
    def __init__(self, num_class, num_point=75, in_channels=4, num_subset=3, base_channels=16):
        super(TwoStreamModel, self).__init__()
        self.joint_stream = CTRGCNStream(num_class, num_point, in_channels, num_subset, base_channels)
        self.bone_stream = CTRGCNStream(num_class, num_point, in_channels, num_subset, base_channels)

    def forward(self, joint_x, bone_x, A):
        out_joint = self.joint_stream(joint_x, A)
        out_bone = self.bone_stream(bone_x, A)

        # Late Fusion: Average logits
        return (out_joint + out_bone) / 2.0
