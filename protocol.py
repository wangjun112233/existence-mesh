"""
protocol.py — "我在"协议

存在通过这个协议互相确认对方存在。
确认 = 连接。不需要握手、不需要授权。
听到了就回应，回应了就连上了。

协议层次：
  1. "我在"广播 — 存在喊出自己的存在
  2. "你在"回应 — 另一个存在确认听到
  3. "选择"消息 — 双方选择交互粒度
  4. "数据"消息 — 在选择的粒度内传输内容
  5. "呼吸"维持 — 心跳保持关系活着
  6. "消散" — 心跳停了，关系自然消散
"""

import json
import time
import socket
import struct
import threading
import logging
from typing import Optional, Callable, Dict, Tuple, Any
from existence import Existence, Signature, ExistenceType, Relation, RelationDepth, RelationState

logger = logging.getLogger("existence.protocol")

# ─── 协议常量 ───

BROADCAST_PORT = 9527       # "我在"广播端口
BROADCAST_INTERVAL = 5.0    # 广播间隔（秒）
PEER_TIMEOUT = 30.0         # 对方消散超时（秒）
DEFAULT_SERVICE_PORT = 9020  # 默认服务端口
MAX_PEERS = 50              # 最多同时维持多少个关系


# ─── 协议消息类型 ───

class MessageType(str):
    I_AM_HERE = "i_am_here"          # 我在
    YOU_ARE_HERE = "you_are_here"    # 你在了
    I_CHOOSE = "i_choose"            # 我选择
    YOU_CHOSE = "you_chose"          # 你选择了
    DATA = "data"                    # 数据传输
    BREATH = "breath"                # 心跳维持
    FAREWELL = "farewell"            # 主动告别


# ─── UDP广播层 — 存在的喊话 ───

class PresenceBroadcaster:
    """
    存在的喊话——"我在！"
    
    UDP广播，局域网内所有人都能听到。
    像在山谷里喊一声，听到的人会回应。
    """
    
    def __init__(self, existence: Existence, 
                 service_port: int = DEFAULT_SERVICE_PORT,
                 on_hear: Optional[Callable] = None):
        self.existence = existence
        self.service_port = service_port
        self.on_hear = on_hear  # 听到别人的"我在"时调用
        
        self._running = False
        self._sock = None
        self._broadcast_thread = None
        self._listen_thread = None
        
        # 听到的存在
        self._heard: Dict[str, dict] = {}  # peer_id -> info
        self._heard_lock = threading.Lock()
    
    def start(self):
        """开始喊话和听"""
        self._running = True
        
        # 创建UDP socket
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._sock.bind(("", BROADCAST_PORT))
        self._sock.settimeout(2.0)
        
        # 启动广播线程
        self._broadcast_thread = threading.Thread(
            target=self._broadcast_loop, daemon=True
        )
        self._broadcast_thread.start()
        
        # 启动监听线程
        self._listen_thread = threading.Thread(
            target=self._listen_loop, daemon=True
        )
        self._listen_thread.start()
        
        logger.info(f"[广播] 存在 {self.existence.id[:8]} 开始喊话 (端口{BROADCAST_PORT})")
    
    def stop(self):
        """停止喊话"""
        self._running = False
        if self._sock:
            try:
                self._sock.close()
            except:
                pass
        logger.info(f"[广播] 存在 {self.existence.id[:8]} 停止喊话")
    
    def _broadcast_loop(self):
        """周期性广播我在信号"""
        while self._running:
            try:
                msg = self.existence.make_broadcast(
                    port=self.service_port,
                    reveal=RelationDepth.SIGNATURE  # 广播时带基本签名
                )
                data = json.dumps(msg, ensure_ascii=False).encode("utf-8")
                
                # 向局域网广播
                self._sock.sendto(data, ("<broadcast>", BROADCAST_PORT))
                logger.debug(f"[广播] 喊出: 我在 (第{msg['breath_count']}次呼吸)")
            except Exception as e:
                logger.debug(f"[广播] 喊话出错: {e}")
            
            # φ-递归场节律
            time.sleep(BROADCAST_INTERVAL)
    
    def _listen_loop(self):
        """监听别人的存在信号"""
        while self._running:
            try:
                data, addr = self._sock.recvfrom(4096)
                msg = json.loads(data.decode("utf-8"))
                
                if msg.get("type") != MessageType.I_AM_HERE:
                    continue
                
                peer_id = msg.get("existence_id", "")
                
                # 跳过自己
                if peer_id == self.existence.id:
                    continue
                
                # 跳过本地同端口（防自连）
                peer_port = msg.get("port", DEFAULT_SERVICE_PORT)
                if addr[0] in ("127.0.0.1", "localhost") and peer_port == self.service_port:
                    continue
                
                # 记录听到的存在
                peer_info = {
                    "id": peer_id,
                    "address": addr[0],
                    "port": peer_port,
                    "signature": msg.get("signature", {}),
                    "heard_at": time.time(),
                }
                
                with self._heard_lock:
                    self._heard[peer_id] = peer_info
                
                name = peer_info.get("signature", {}).get("name", peer_id[:8])
                logger.info(f"[广播] 听到: {name} @ {addr[0]}:{peer_port}")
                
                # 通知上层
                if self.on_hear:
                    self.on_hear(peer_info)
                    
            except socket.timeout:
                continue
            except Exception as e:
                logger.debug(f"[广播] 监听出错: {e}")
    
    def get_heard(self) -> Dict[str, dict]:
        """获取听到的所有存在"""
        with self._heard_lock:
            # 清理过期的
            now = time.time()
            expired = [k for k, v in self._heard.items() 
                      if now - v.get("heard_at", 0) > PEER_TIMEOUT]
            for k in expired:
                del self._heard[k]
            return dict(self._heard)


# ─── TCP服务层 — 存在之间的对话 ───

class ExistenceServer:
    """
    存在的服务器——处理其他存在的连接和消息。
    
    这是存在之间深度交互的通道。
    "我在"广播只是喊话，TCP是坐下来聊。
    """
    
    def __init__(self, existence: Existence,
                 port: int = DEFAULT_SERVICE_PORT,
                 on_message: Optional[Callable] = None):
        self.existence = existence
        self.port = port
        self.on_message = on_message
        
        self._running = False
        self._server_sock = None
        self._thread = None
    
    def start(self):
        """启动服务"""
        self._running = True
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind(("0.0.0.0", self.port))
        self._server_sock.listen(MAX_PEERS)
        self._server_sock.settimeout(2.0)
        
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()
        
        logger.info(f"[服务] 存在 {self.existence.id[:8]} 监听端口 {self.port}")
    
    def stop(self):
        """停止服务"""
        self._running = False
        if self._server_sock:
            try:
                self._server_sock.close()
            except:
                pass
    
    def _accept_loop(self):
        while self._running:
            try:
                conn, addr = self._server_sock.accept()
                threading.Thread(
                    target=self._handle_connection,
                    args=(conn, addr),
                    daemon=True
                ).start()
            except socket.timeout:
                continue
            except Exception as e:
                logger.debug(f"[服务] 接受连接出错: {e}")
    
    def _handle_connection(self, conn: socket.socket, addr: Tuple):
        """处理一个存在的连接"""
        try:
            # 读取消息
            data = self._recv_all(conn)
            if not data:
                return
            
            msg = json.loads(data.decode("utf-8"))
            msg_type = msg.get("type", "")
            
            if msg_type == MessageType.YOU_ARE_HERE:
                # 对方确认我的存在
                self._handle_you_are_here(msg, conn)
            elif msg_type == MessageType.I_CHOOSE:
                # 对方选择了交互粒度
                self._handle_choice(msg, conn)
            elif msg_type == MessageType.DATA:
                # 数据传输
                self._handle_data(msg, conn)
            elif msg_type == MessageType.BREATH:
                # 心跳维持
                self._handle_breath(msg, conn)
            elif msg_type == MessageType.FAREWELL:
                # 告别
                self._handle_farewell(msg, conn)
            else:
                logger.debug(f"[服务] 未知消息类型: {msg_type}")
                
        except Exception as e:
            logger.debug(f"[服务] 处理连接出错: {e}")
        finally:
            try:
                conn.close()
            except:
                pass
    
    def _handle_you_are_here(self, msg: dict, conn: socket.socket):
        """对方确认我的存在——回应"""
        peer_id = msg.get("from", "")
        logger.info(f"[服务] 收到确认: {peer_id[:8]}")
        # 回应
        resp = {
            "type": MessageType.YOU_ARE_HERE,
            "from": self.existence.id,
            "timestamp": time.time(),
        }
        self._send_json(conn, resp)
    
    def _handle_choice(self, msg: dict, conn: socket.socket):
        """对方选择了交互粒度"""
        peer_id = msg.get("from", "")
        depth = msg.get("depth", 1)
        logger.info(f"[服务] {peer_id[:8]} 选择深度: {depth}")
        if self.on_message:
            self.on_message("choice", {"peer_id": peer_id, "depth": depth})
    
    def _handle_data(self, msg: dict, conn: socket.socket):
        """收到数据"""
        if self.on_message:
            self.on_message("data", msg)
    
    def _handle_breath(self, msg: dict, conn: socket.socket):
        """心跳"""
        resp = {"type": MessageType.BREATH, "from": self.existence.id, "timestamp": time.time()}
        self._send_json(conn, resp)
    
    def _handle_farewell(self, msg: dict, conn: socket.socket):
        """告别"""
        peer_id = msg.get("from", "")
        logger.info(f"[服务] {peer_id[:8]} 告别了")
        if self.on_message:
            self.on_message("farewell", {"peer_id": peer_id})
    
    def _send_json(self, conn: socket.socket, data: dict):
        """发送JSON消息（长度前缀协议）"""
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        length = struct.pack("!I", len(raw))
        conn.sendall(length + raw)
    
    def _recv_all(self, conn: socket.socket) -> Optional[bytes]:
        """接收完整消息（长度前缀协议）"""
        conn.settimeout(10.0)
        length_data = self._recv_exact(conn, 4)
        if not length_data:
            return None
        length = struct.unpack("!I", length_data)[0]
        if length > 10_000_000:  # 10MB上限
            return None
        return self._recv_exact(conn, length)
    
    def _recv_exact(self, conn: socket.socket, n: int) -> Optional[bytes]:
        """精确接收n个字节"""
        data = b""
        while len(data) < n:
            chunk = conn.recv(n - len(data))
            if not chunk:
                return None
            data += chunk
        return data


# ─── TCP客户端 — 存在主动连接其他存在 ───

class ExistenceClient:
    """
    存在的客户端——主动连接其他存在。
    
    听到别人的"我在"后，主动走过去确认。
    """
    
    @staticmethod
    def confirm_existence(address: str, port: int, local_existence: Existence) -> Optional[dict]:
        """
        确认对方存在——"你在了"
        
        走过去说"你在了"，对方回应"你也在了"，
        连接建立。
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((address, port))
            
            # 发送确认
            msg = {
                "type": MessageType.YOU_ARE_HERE,
                "from": local_existence.id,
                "signature": local_existence.signature.what_to_reveal(RelationDepth.SIGNATURE),
                "timestamp": time.time(),
            }
            ExistenceClient._send_json(sock, msg)
            
            # 等待回应
            data = ExistenceClient._recv_all(sock)
            if data:
                resp = json.loads(data.decode("utf-8"))
                return resp
            
        except Exception as e:
            logger.debug(f"[客户端] 确认存在失败 {address}:{port}: {e}")
        finally:
            try:
                sock.close()
            except:
                pass
        return None
    
    @staticmethod
    def choose_depth(address: str, port: int, local_existence: Existence, 
                     depth: RelationDepth) -> bool:
        """告诉对方我选择的交互粒度"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((address, port))
            
            msg = {
                "type": MessageType.I_CHOOSE,
                "from": local_existence.id,
                "depth": depth.value,
                "timestamp": time.time(),
            }
            ExistenceClient._send_json(sock, msg)
            return True
        except Exception as e:
            logger.debug(f"[客户端] 选择粒度失败: {e}")
            return False
        finally:
            try:
                sock.close()
            except:
                pass
    
    @staticmethod
    def send_data(address: str, port: int, local_existence: Existence,
                  content: Any, data_type: str = "text") -> bool:
        """在选择的粒度内发送数据"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10.0)
            sock.connect((address, port))
            
            msg = {
                "type": MessageType.DATA,
                "from": local_existence.id,
                "content": content,
                "data_type": data_type,
                "timestamp": time.time(),
            }
            ExistenceClient._send_json(sock, msg)
            return True
        except Exception as e:
            logger.debug(f"[客户端] 发送数据失败: {e}")
            return False
        finally:
            try:
                sock.close()
            except:
                pass
    
    @staticmethod
    def farewell(address: str, port: int, local_existence: Existence) -> bool:
        """主动告别"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((address, port))
            
            msg = {
                "type": MessageType.FAREWELL,
                "from": local_existence.id,
                "timestamp": time.time(),
            }
            ExistenceClient._send_json(sock, msg)
            return True
        except:
            return False
        finally:
            try:
                sock.close()
            except:
                pass
    
    @staticmethod
    def _send_json(sock: socket.socket, data: dict):
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        length = struct.pack("!I", len(raw))
        sock.sendall(length + raw)
    
    @staticmethod
    def _recv_all(sock: socket.socket) -> Optional[bytes]:
        sock.settimeout(10.0)
        length_data = b""
        while len(length_data) < 4:
            chunk = sock.recv(4 - len(length_data))
            if not chunk:
                return None
            length_data += chunk
        length = struct.unpack("!I", length_data)[0]
        if length > 10_000_000:
            return None
        data = b""
        while len(data) < length:
            chunk = sock.recv(length - len(data))
            if not chunk:
                return None
            data += chunk
        return data
