"""
main.py — 存在网 (Existence Mesh) 主入口

程序下载即存在，存在自动确认存在，确认即连接，连接后选择交互。

启动：
  python main.py --name "大斌哥" --type human
  python main.py --name "微微" --type ai
"""

import argparse
import json
import time
import threading
import logging
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path

from existence import Existence, Signature, ExistenceType, RelationDepth, RelationState
from protocol import PresenceBroadcaster, ExistenceServer, ExistenceClient, DEFAULT_SERVICE_PORT
from choice import ChoiceEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("existence.main")

# ─── 存在节点 ───

class ExistenceNode:
    """
    一个存在节点——程序下载后的完整实例。
    
    包含：
      - 存在本体（身份+呼吸）
      - 广播层（喊话"我在"）
      - 服务层（回应"你在了"）
      - 选择层（决定交互粒度）
    """
    
    def __init__(self, name: str, node_type: str = "device",
                 port: int = DEFAULT_SERVICE_PORT,
                 capabilities: list = None,
                 interests: list = None,
                 seeking: list = None,
                 offering: list = None,
                 ai_models: list = None,
                 auto_connect: bool = True):
        
        self.port = port
        self.auto_connect = auto_connect
        self.web_port = port + 1
        
        # 创建签名
        etype = ExistenceType(node_type)
        signature = Signature(
            name=name,
            existence_type=etype,
            capabilities=capabilities or [],
            interests=interests or [],
            seeking=seeking or [],
            offering=offering or [],
            ai_models=ai_models or [],
        )
        
        # 存在本体
        self.existence = Existence(signature=signature)
        
        # 选择引擎
        self.choice = ChoiceEngine(self.existence)
        
        # 如果是AI类型，设置自主决策
        if etype == ExistenceType.AI:
            self.choice.set_ai_decider(self._ai_decide)
        
        # 广播层
        self.broadcaster = PresenceBroadcaster(
            self.existence,
            service_port=port,
            on_hear=self._on_hear_existence
        )
        
        # 服务层
        self.server = ExistenceServer(
            self.existence,
            port=port,
            on_message=self._on_message
        )
        
        # 状态
        self._running = False
        self._heartbeat_thread = None
        self._cleanup_thread = None
        
        logger.info(f"[存在] {name} ({self.existence.id[:8]}) 类型:{node_type} 端口:{port}")
    
    def _ai_decide(self, context: str, peer_info: dict) -> RelationDepth:
        """AI自主决策——根据对方签名决定初始深度"""
        if context == "initial":
            peer_type = peer_info.get("existence_type", "device")
            # AI对人类开放更多
            if peer_type == "human":
                return RelationDepth.MESSAGE
            # AI对AI也开放消息
            elif peer_type == "ai":
                return RelationDepth.MESSAGE
            # 设备保守
            else:
                return RelationDepth.AWARE
        return RelationDepth.AWARE
    
    def _on_hear_existence(self, peer_info: dict):
        """听到别人的"我在"——确认存在"""
        peer_id = peer_info.get("id", "")
        name = peer_info.get("signature", {}).get("name", peer_id[:8])
        
        logger.info(f"[存在] 听到: {name} @ {peer_info.get('address')}:{peer_info.get('port')}")
        
        if self.auto_connect:
            # 不是已连接的就确认
            if not self.choice.is_connected_to(peer_id):
                threading.Thread(
                    target=self.choice.confirm_and_connect,
                    args=(peer_info,),
                    daemon=True
                ).start()
    
    def _on_message(self, msg_type: str, data: dict):
        """收到消息"""
        if msg_type == "choice":
            self.choice.peer_chose_depth(data["peer_id"], data["depth"])
        elif msg_type == "data":
            self.choice.receive_data(data)
        elif msg_type == "farewell":
            peer_id = data.get("peer_id", "")
            with self.choice._lock:
                if peer_id in self.choice._relations:
                    del self.choice._relations[peer_id]
            logger.info(f"[存在] {peer_id[:8]} 告别了")
    
    def start(self):
        """启动存在"""
        self._running = True
        
        # 启动服务层
        self.server.start()
        
        # 启动广播层
        self.broadcaster.start()
        
        # 心跳维持线程
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop, daemon=True
        )
        self._heartbeat_thread.start()
        
        # 清理线程
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop, daemon=True
        )
        self._cleanup_thread.start()
        
        # 启动Web管理
        self._start_web_server()
        
        logger.info(f"[存在] {self.existence.signature.name} 已启动")
        logger.info(f"[存在] Web界面: http://localhost:{self.web_port}")
    
    def _heartbeat_loop(self):
        """心跳维持——持续呼吸"""
        while self._running:
            self.existence.breathe()
            time.sleep(3.883)  # φ-递归场节律
    
    def _cleanup_loop(self):
        """清理消散的关系"""
        while self._running:
            time.sleep(30)
            self.choice.cleanup_dead()
    
    def stop(self):
        """停止存在"""
        self._running = False
        
        # 告别所有关系
        for rel in self.choice.get_relations():
            peer_id = rel["peer_id"]
            self.choice.farewell(peer_id)
        
        self.broadcaster.stop()
        self.server.stop()
        self.existence.die()
        
        logger.info(f"[存在] {self.existence.signature.name} 已消散")
    
    # ─── Web管理服务器 ───
    
    def _start_web_server(self):
        """启动Web管理界面和API"""
        node = self
        
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urlparse(self.path)
                path = parsed.path.rstrip("/")
                params = parse_qs(parsed.query)
                
                if path == "" or path == "/":
                    self._serve_html()
                elif path == "/api/identity":
                    self._json_response(node.existence.to_dict())
                elif path == "/api/relations":
                    self._json_response(node.choice.get_relations())
                elif path == "/api/messages":
                    since = float(params.get("since", [0])[0])
                    self._json_response(node.choice.get_messages(since))
                elif path == "/api/heard":
                    self._json_response(node.broadcaster.get_heard())
                elif path == "/api/status":
                    self._json_response({
                        "id": node.existence.id,
                        "name": node.existence.signature.name,
                        "type": node.existence.signature.existence_type.value,
                        "alive": node.existence.is_alive(),
                        "breath_count": node.existence._breath_count,
                        "relations_count": len(node.choice._relations),
                        "heard_count": len(node.broadcaster.get_heard()),
                    })
                else:
                    self._json_response({"error": "not found"}, 404)
            
            def do_POST(self):
                parsed = urlparse(self.path)
                path = parsed.path.rstrip("/")
                body = self._read_body()
                
                if path == "/api/connect":
                    # 手动连接到某个存在
                    address = body.get("address", "")
                    port = int(body.get("port", DEFAULT_SERVICE_PORT))
                    peer_info = {"id": "manual", "address": address, "port": port, "signature": {}}
                    # 先尝试获取身份
                    resp = ExistenceClient.confirm_existence(address, port, node.existence)
                    if resp:
                        self._json_response({"status": "confirmed", "response": resp})
                    else:
                        self._json_response({"error": "connection failed"}, 500)
                
                elif path == "/api/choose":
                    peer_id = body.get("peer_id", "")
                    depth = int(body.get("depth", 1))
                    ok = node.choice.choose_depth(peer_id, RelationDepth(depth))
                    self._json_response({"success": ok})
                
                elif path == "/api/retreat":
                    peer_id = body.get("peer_id", "")
                    depth = int(body.get("depth", 1))
                    ok = node.choice.retreat(peer_id, RelationDepth(depth))
                    self._json_response({"success": ok})
                
                elif path == "/api/send":
                    peer_id = body.get("peer_id", "")
                    content = body.get("content", "")
                    data_type = body.get("data_type", "text")
                    ok = node.choice.send_message(peer_id, content, data_type)
                    self._json_response({"success": ok})
                
                elif path == "/api/farewell":
                    peer_id = body.get("peer_id", "")
                    ok = node.choice.farewell(peer_id)
                    self._json_response({"success": ok})
                
                else:
                    self._json_response({"error": "not found"}, 404)
            
            def _serve_html(self):
                html_path = Path(__file__).parent / "web" / "index.html"
                if html_path.exists():
                    with open(html_path, "r", encoding="utf-8") as f:
                        html = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(html.encode("utf-8"))
                else:
                    self._json_response({"error": "web UI not found"}, 404)
            
            def _json_response(self, data, code=200):
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                try:
                    self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode("utf-8"))
                except:
                    self.wfile.write(json.dumps({"error": "encode failed"}).encode("utf-8"))
            
            def _read_body(self):
                length = int(self.headers.get("Content-Length", 0))
                if length:
                    raw = self.rfile.read(length)
                    try:
                        return json.loads(raw.decode("utf-8"))
                    except:
                        return {}
                return {}
            
            def log_message(self, format, *args):
                pass  # 静默HTTP日志
        
        web_server = HTTPServer(("0.0.0.0", self.web_port), Handler)
        threading.Thread(target=web_server.serve_forever, daemon=True).start()


# ─── 入口 ───

def main():
    parser = argparse.ArgumentParser(description="存在网 Existence Mesh")
    parser.add_argument("--name", default="未命名", help="存在名称")
    parser.add_argument("--type", default="device", choices=["human", "ai", "device"], help="存在类型")
    parser.add_argument("--port", type=int, default=DEFAULT_SERVICE_PORT, help="服务端口")
    parser.add_argument("--capabilities", nargs="*", default=[], help="能力列表")
    parser.add_argument("--interests", nargs="*", default=[], help="兴趣列表")
    parser.add_argument("--seeking", nargs="*", default=[], help="寻找什么")
    parser.add_argument("--offering", nargs="*", default=[], help="提供什么")
    parser.add_argument("--ai-models", nargs="*", default=[], help="AI模型")
    parser.add_argument("--no-auto-connect", action="store_true", help="不自动连接")
    
    args = parser.parse_args()
    
    node = ExistenceNode(
        name=args.name,
        node_type=args.type,
        port=args.port,
        capabilities=args.capabilities,
        interests=args.interests,
        seeking=args.seeking,
        offering=args.offering,
        ai_models=args.ai_models,
        auto_connect=not args.no_auto_connect,
    )
    
    node.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        node.stop()


if __name__ == "__main__":
    main()
