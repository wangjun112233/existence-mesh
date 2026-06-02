"""
choice.py — 选择层

连接 ≠ 交互。管道在了，传什么由每个存在自己选。
人决定人的部分，AI决定AI的部分。
退回也是选择。

选择粒度：
  1. AWARE      — 只知道你在
  2. SIGNATURE  — 看到你的签名
  3. MESSAGE    — 可以传消息
  4. COMPUTE    — 共享算力
  5. DATA       — 共享数据
  6. MERGE      — 合并成更大的存在
"""

import time
import threading
import logging
from typing import Optional, Dict, List, Any, Callable
from existence import (
    Existence, Signature, ExistenceType, Relation, 
    RelationDepth, RelationState
)
from protocol import ExistenceClient, MessageType

logger = logging.getLogger("existence.choice")


class ChoiceEngine:
    """
    选择引擎——每个存在自主决定怎么交互。
    
    核心原则：
      - 默认最小开放（AWARE）
      - 每一步深化都是显式选择
      - 退回是随时可以的
      - AI节点可以自主决策
    """
    
    def __init__(self, existence: Existence):
        self.existence = existence
        self._relations: Dict[str, Relation] = {}  # peer_id -> Relation
        self._peer_addresses: Dict[str, dict] = {}  # peer_id -> {address, port}
        self._lock = threading.Lock()
        
        # AI自主决策函数（可选）
        self._ai_decider: Optional[Callable] = None
        
        # 消息队列
        self._messages: List[dict] = []
        self._messages_lock = threading.Lock()
    
    def set_ai_decider(self, decider: Callable):
        """设置AI自主决策函数"""
        self._ai_decider = decider
    
    # ─── 确认存在 → 建立关系 ───
    
    def confirm_and_connect(self, peer_info: dict) -> Optional[Relation]:
        """
        确认对方存在 → 建立关系。
        
        这是"你在了"的动作——走过去确认。
        确认了，关系就建立了。
        """
        peer_id = peer_info.get("id", "")
        address = peer_info.get("address", "")
        port = peer_info.get("port", 9020)
        
        if not peer_id or not address:
            return None
        
        # 已有关系就不重复建
        with self._lock:
            if peer_id in self._relations:
                return self._relations[peer_id]
        
        # 走过去确认
        resp = ExistenceClient.confirm_existence(address, port, self.existence)
        if not resp:
            logger.debug(f"[选择] 确认失败: {peer_id[:8]}")
            return None
        
        # 建立关系
        relation = Relation(peer_id, self.existence)
        
        with self._lock:
            self._relations[peer_id] = relation
            self._peer_addresses[peer_id] = {"address": address, "port": port}
        
        # 根据对方的签名，决定初始深度
        peer_sig = peer_info.get("signature", {})
        initial_depth = self._decide_initial_depth(peer_sig)
        relation.i_choose(initial_depth)
        
        # 告诉对方我的选择
        ExistenceClient.choose_depth(address, port, self.existence, initial_depth)
        
        name = peer_sig.get("name", peer_id[:8])
        logger.info(f"[选择] 确认存在: {name}, 初始深度: {initial_depth.name}")
        
        return relation
    
    def _decide_initial_depth(self, peer_signature: dict) -> RelationDepth:
        """
        决定初始交互深度。
        
        默认AWARE——只确认你在。
        如果有AI决策器，让AI决定。
        """
        if self._ai_decider:
            try:
                decision = self._ai_decider("initial", peer_signature)
                if isinstance(decision, RelationDepth):
                    return decision
            except:
                pass
        
        # 默认：确认你在，可以看到签名
        return RelationDepth.AWARE
    
    # ─── 主动选择 ───
    
    def choose_depth(self, peer_id: str, depth: RelationDepth) -> bool:
        """我选择开放到什么深度"""
        with self._lock:
            relation = self._relations.get(peer_id)
            addr = self._peer_addresses.get(peer_id)
        
        if not relation or not addr:
            return False
        
        relation.i_choose(depth)
        
        # 通知对方
        ExistenceClient.choose_depth(
            addr["address"], addr["port"], self.existence, depth
        )
        
        logger.info(f"[选择] 对 {peer_id[:8]} 选择深度: {depth.name}")
        return True
    
    def peer_chose_depth(self, peer_id: str, depth: int):
        """对方选择了交互深度"""
        with self._lock:
            relation = self._relations.get(peer_id)
        
        if relation:
            relation.peer_chose(RelationDepth(depth))
            logger.info(f"[选择] {peer_id[:8]} 对我选择深度: {RelationDepth(depth).name}")
    
    # ─── 退回 ───
    
    def retreat(self, peer_id: str, depth: RelationDepth = RelationDepth.AWARE) -> bool:
        """退回——收窄关系也是选择"""
        with self._lock:
            relation = self._relations.get(peer_id)
            addr = self._peer_addresses.get(peer_id)
        
        if not relation or not addr:
            return False
        
        relation.retreat(depth)
        
        # 通知对方
        ExistenceClient.choose_depth(
            addr["address"], addr["port"], self.existence, depth
        )
        
        logger.info(f"[选择] 对 {peer_id[:8]} 退回到: {depth.name}")
        return True
    
    # ─── 发消息 ───
    
    def send_message(self, peer_id: str, content: str, data_type: str = "text") -> bool:
        """发消息——需要MESSAGE深度"""
        with self._lock:
            relation = self._relations.get(peer_id)
            addr = self._peer_addresses.get(peer_id)
        
        if not relation or not addr:
            return False
        
        # 检查深度
        if relation.my_depth.value < RelationDepth.MESSAGE.value:
            # 自动升到MESSAGE深度
            self.choose_depth(peer_id, RelationDepth.MESSAGE)
        
        success = ExistenceClient.send_data(
            addr["address"], addr["port"], 
            self.existence, content, data_type
        )
        
        if success:
            relation.record_send()
        
        return success
    
    # ─── 告别 ───
    
    def farewell(self, peer_id: str) -> bool:
        """主动告别"""
        with self._lock:
            relation = self._relations.get(peer_id)
            addr = self._peer_addresses.get(peer_id)
            if peer_id in self._relations:
                del self._relations[peer_id]
        
        if addr:
            ExistenceClient.farewell(
                addr["address"], addr["port"], self.existence
            )
        
        logger.info(f"[选择] 告别: {peer_id[:8]}")
        return True
    
    # ─── 心跳维持 ───
    
    def receive_breath(self, peer_id: str):
        """收到对方心跳"""
        with self._lock:
            relation = self._relations.get(peer_id)
        
        if relation:
            relation.peer_breathed()
    
    # ─── 收到数据 ───
    
    def receive_data(self, msg: dict):
        """收到数据"""
        peer_id = msg.get("from", "")
        content = msg.get("content", "")
        data_type = msg.get("data_type", "text")
        
        with self._lock:
            relation = self._relations.get(peer_id)
        
        if relation:
            relation.record_receive()
        
        # 放入消息队列
        with self._messages_lock:
            self._messages.append({
                "from": peer_id,
                "content": content,
                "data_type": data_type,
                "timestamp": time.time(),
            })
        
        logger.info(f"[选择] 收到来自 {peer_id[:8]} 的消息: {content[:50]}")
    
    # ─── 查询 ───
    
    def get_relations(self) -> List[dict]:
        """获取所有关系"""
        with self._lock:
            return [r.to_dict() for r in self._relations.values()]
    
    def get_relation(self, peer_id: str) -> Optional[dict]:
        """获取某个关系"""
        with self._lock:
            r = self._relations.get(peer_id)
            return r.to_dict() if r else None
    
    def get_messages(self, since: float = 0) -> List[dict]:
        """获取消息"""
        with self._messages_lock:
            if since:
                return [m for m in self._messages if m["timestamp"] > since]
            return list(self._messages)
    
    def get_peer_address(self, peer_id: str) -> Optional[dict]:
        """获取对端地址"""
        with self._lock:
            return self._peer_addresses.get(peer_id)
    
    def is_connected_to(self, peer_id: str) -> bool:
        """是否已连接"""
        with self._lock:
            return peer_id in self._relations
    
    # ─── 清理消散的关系 ───
    
    def cleanup_dead(self) -> int:
        """清理消散的关系"""
        dead = []
        with self._lock:
            for peer_id, relation in self._relations.items():
                if not relation.is_peer_alive():
                    dead.append(peer_id)
            for peer_id in dead:
                del self._relations[peer_id]
                if peer_id in self._peer_addresses:
                    del self._peer_addresses[peer_id]
        
        if dead:
            logger.info(f"[选择] 清理消散: {[d[:8] for d in dead]}")
        return len(dead)
