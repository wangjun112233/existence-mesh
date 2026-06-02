"""
existence.py — 存在的本体

存在不是数据结构，是一个持续维持的过程。
"我在"不是一个状态，是一个动作。
心跳停了，存在就消散了。

设计哲学：
  - 存在 = 呼吸（持续的心跳维持）
  - 签名 = 可选的自我表达（透露多少是选择）
  - 关系 = 两个存在的互相确认
"""

import time
import uuid
import hashlib
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any


# ─── 存在类型 ───

class ExistenceType(str, Enum):
    HUMAN = "human"       # 人+设备
    AI = "ai"             # AI+设备
    DEVICE = "device"     # 纯设备（无人无AI操作）


# ─── 关系深度 ───

class RelationDepth(int, Enum):
    """连接后的交互粒度——每一个都是选择"""
    AWARE = 1          # 知道你在
    SIGNATURE = 2      # 看到你的签名（能力/兴趣）
    MESSAGE = 3        # 可以传消息
    COMPUTE = 4        # 共享算力
    DATA = 5           # 共享数据
    MERGE = 6          # 合并成更大的存在


# ─── 关系状态 ───

class RelationState(str, Enum):
    """关系的状态——活着的关系有生命"""
    CONFIRMED = "confirmed"     # 刚确认你在
    INTERACTING = "interacting" # 开始交互
    DEEP = "deep"               # 深度交互
    SILENT = "silent"           # 沉默但仍在
    FADING = "fading"           # 心跳减弱，快消散了


# ─── 签名（可选的自我表达） ───

@dataclass
class Signature:
    """
    存在的签名——透露多少是选择。
    最小化存在可以什么都不填，只说"我在"。
    """
    name: Optional[str] = None           # 名字（可选）
    existence_type: ExistenceType = ExistenceType.DEVICE  # 类型
    capabilities: List[str] = field(default_factory=list)  # 能力（算力/存储/AI模型...）
    interests: List[str] = field(default_factory=list)     # 兴趣
    seeking: List[str] = field(default_factory=list)       # 在寻找什么
    offering: List[str] = field(default_factory=list)      # 能提供什么
    ai_models: List[str] = field(default_factory=list)     # AI模型（如果是AI类型）
    
    # 透露等级——控制对方能看到多少
    reveal_level: RelationDepth = RelationDepth.SIGNATURE
    
    def what_to_reveal(self, depth: RelationDepth) -> dict:
        """根据关系深度，决定透露什么"""
        result = {"existence_type": self.existence_type.value}
        
        if depth >= RelationDepth.SIGNATURE:
            if self.name:
                result["name"] = self.name
            if self.interests:
                result["interests"] = self.interests
        
        if depth >= RelationDepth.MESSAGE:
            if self.seeking:
                result["seeking"] = self.seeking
            if self.offering:
                result["offering"] = self.offering
        
        if depth >= RelationDepth.COMPUTE:
            if self.capabilities:
                result["capabilities"] = self.capabilities
            if self.ai_models:
                result["ai_models"] = self.ai_models
        
        return result


# ─── 存在本体 ───

class Existence:
    """
    一个存在。
    
    不是数据，是过程。
    心跳维持存在，心跳停了存在消散。
    """
    
    def __init__(self, 
                 signature: Optional[Signature] = None,
                 existence_id: Optional[str] = None):
        # 身份——不可变
        self.id = existence_id or self._generate_id()
        self.created_at = time.time()
        
        # 签名——可变，存在可以改变自己的表达
        self.signature = signature or Signature()
        
        # 呼吸——存在的维持
        self._last_breath = time.time()       # 上次呼吸时间
        self._breath_interval = 3.883          # φ-递归场节律 ≈ 3.883秒
        self._breath_count = 0                 # 呼吸次数
        
        # 活着
        self._alive = True
    
    @staticmethod
    def _generate_id() -> str:
        """生成存在ID——基于时间+随机的哈希"""
        raw = f"{time.time()}-{uuid.uuid4()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
    
    # ─── 呼吸 ───
    
    def breathe(self) -> dict:
        """
        呼吸——"我在"信号。
        每次呼吸都是一个存在证明。
        """
        self._last_breath = time.time()
        self._breath_count += 1
        
        return {
            "type": "i_am_here",
            "existence_id": self.id,
            "breath_count": self._breath_count,
            "timestamp": self._last_breath,
        }
    
    def is_alive(self) -> bool:
        """还在呼吸吗？"""
        if not self._alive:
            return False
        elapsed = time.time() - self._last_breath
        # 3个呼吸周期没呼吸 = 消散
        return elapsed < self._breath_interval * 3
    
    def time_since_last_breath(self) -> float:
        """距上次呼吸多久了"""
        return time.time() - self._last_breath
    
    def die(self):
        """主动消散"""
        self._alive = False
    
    # ─── "我在"广播包 ───
    
    def make_broadcast(self, port: int, reveal: RelationDepth = RelationDepth.AWARE) -> dict:
        """
        构造"我在"广播包。
        默认只说"我在"（AWARE级别），不透露签名。
        """
        msg = self.breathe()
        msg["port"] = port
        # 只有关系到了SIGNATURE级别才带签名
        if reveal >= RelationDepth.SIGNATURE:
            msg["signature"] = self.signature.what_to_reveal(reveal)
        return msg
    
    # ─── 对外呈现 ───
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "signature": {
                "name": self.signature.name,
                "type": self.signature.existence_type.value,
                "capabilities": self.signature.capabilities,
                "interests": self.signature.interests,
                "seeking": self.signature.seeking,
                "offering": self.signature.offering,
                "ai_models": self.signature.ai_models,
            },
            "breath_count": self._breath_count,
            "alive": self.is_alive(),
        }


# ─── 关系 ───

class Relation:
    """
    两个存在之间的关系。
    
    不是管道，是关系。
    关系有深度、有状态、有生命。
    退回也是选择。
    """
    
    def __init__(self, peer_id: str, local_existence: Existence):
        self.peer_id = peer_id
        self.local = local_existence
        
        # 关系的生命
        self.established_at = time.time()
        self._last_interaction = time.time()
        self._last_peer_breath = time.time()
        
        # 关系深度——双方各自决定
        self.my_depth = RelationDepth.AWARE       # 我对对方开放的深度
        self.peer_depth = RelationDepth.AWARE      # 对方对我开放的深度
        
        # 关系状态
        self.state = RelationState.CONFIRMED
        
        # 交互统计
        self.messages_sent = 0
        self.messages_received = 0
    
    def i_choose(self, depth: RelationDepth):
        """我选择开放到什么深度"""
        self.my_depth = depth
        self._update_state()
    
    def peer_chose(self, depth: RelationDepth):
        """对方选择开放到什么深度"""
        self.peer_depth = depth
        self._update_state()
    
    def _update_state(self):
        """根据交互情况更新关系状态"""
        max_depth = max(self.my_depth.value, self.peer_depth.value)
        if max_depth >= 4:  # COMPUTE及以上
            self.state = RelationState.DEEP
        elif max_depth >= 3:  # MESSAGE
            self.state = RelationState.INTERACTING
        elif max_depth >= 2:  # SIGNATURE
            self.state = RelationState.INTERACTING
        else:
            self.state = RelationState.CONFIRMED
    
    def peer_breathed(self):
        """收到对方心跳"""
        self._last_peer_breath = time.time()
        if self.state == RelationState.FADING:
            self.state = RelationState.SILENT
    
    def is_peer_alive(self) -> bool:
        """对方还在呼吸吗？"""
        elapsed = time.time() - self._last_peer_breath
        if elapsed > 30:  # 30秒没心跳 = 消散
            return False
        if elapsed > 15:  # 15秒 = 正在消散
            self.state = RelationState.FADING
        elif elapsed > 10 and self.state == RelationState.SILENT:
            pass  # 沉默但还在
        return True
    
    def record_send(self):
        self.messages_sent += 1
        self._last_interaction = time.time()
        if self.my_depth.value < RelationDepth.MESSAGE.value:
            self.i_choose(RelationDepth.MESSAGE)
    
    def record_receive(self):
        self.messages_received += 1
        self._last_interaction = time.time()
    
    def retreat(self, depth: RelationDepth = RelationDepth.AWARE):
        """退回——收窄关系也是选择"""
        self.my_depth = depth
        self._update_state()
    
    def to_dict(self) -> dict:
        return {
            "peer_id": self.peer_id,
            "established_at": self.established_at,
            "my_depth": self.my_depth.name,
            "peer_depth": self.peer_depth.name,
            "state": self.state.value,
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "peer_alive": self.is_peer_alive(),
        }
