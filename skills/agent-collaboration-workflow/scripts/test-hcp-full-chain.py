#!/usr/bin/env python3
"""
HCP 全链路测试脚本

测试场景:
  1. HCP Server 启动验证
  2. HCP Client 心跳上报
  3. HCP Client ACK 发送
  4. ACP Bridge 转发 (TCP → Unix Socket)
  5. Stale Detection v2 验证

用法:
  python3 scripts/test-hcp-full-chain.py
"""

import json
import socket
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

HERMES_HOME = Path.home() / ".hermes"
HCP_SOCKET = HERMES_HOME / "hcp.sock"
HCP_TOKEN = HERMES_HOME / "hcp.token"
ACP_BRIDGE_PORT = 18790

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def send_tcp(host, port, msg):
    """Send TCP message and receive response."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    sock.sendall((msg + "\n").encode())
    response = sock.recv(4096).decode()
    sock.close()
    return response.strip()

def send_unix_socket(path, msg):
    """Send Unix Socket message and receive response."""
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(str(path))
    sock.sendall((msg + "\n").encode())
    response = sock.recv(4096).decode()
    sock.close()
    return response.strip()

def log(status, msg):
    """Pretty print log."""
    icon = {"✅": "✅", "❌": "❌", "⚠️": "⚠️", "ℹ️": "ℹ️"}.get(status, status)
    print(f"{icon} {msg}")

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_hcp_server():
    """Test 1: HCP Server is running."""
    log("ℹ️", "Test 1: Check HCP Server...")
    
    if not HCP_SOCKET.exists():
        log("❌", f"HCP Socket not found: {HCP_SOCKET}")
        return False
    
    # Try to connect
    try:
        resp = send_unix_socket(HCP_SOCKET, '{"jsonrpc":"2.0","id":1,"method":"probe","params":{"session_id":"test_srv"}}')
        log("✅", f"HCP Server responding: {resp[:50]}...")
        return True
    except Exception as e:
        log("❌", f"HCP Server connection failed: {e}")
        return False

def test_hcp_heartbeat():
    """Test 2: HCP Heartbeat reporting."""
    log("ℹ️", "Test 2: HCP Heartbeat...")
    
    msg = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "heartbeat",
        "params": {
            "session_id": "test_hb_" + str(int(time.time())),
            "status": "running",
            "step": "testing",
            "progress": 50.0
        }
    }
    
    try:
        resp = send_unix_socket(HCP_SOCKET, json.dumps(msg))
        data = json.loads(resp)
        if data.get("result", {}).get("ack"):
            log("✅", "HCP Heartbeat OK")
            return True
        else:
            log("❌", f"HCP Heartbeat failed: {resp}")
            return False
    except Exception as e:
        log("❌", f"HCP Heartbeat error: {e}")
        return False

def test_hcp_ack():
    """Test 3: HCP Completion ACK."""
    log("ℹ️", "Test 3: HCP ACK...")
    
    msg = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "ack",
        "params": {
            "session_id": "test_ack_" + str(int(time.time())),
            "status": "completed",
            "duration_seconds": 123.45
        }
    }
    
    try:
        resp = send_unix_socket(HCP_SOCKET, json.dumps(msg))
        data = json.loads(resp)
        if data.get("result", {}).get("ack"):
            log("✅", "HCP ACK OK")
            return True
        else:
            log("❌", f"HCP ACK failed: {resp}")
            return False
    except Exception as e:
        log("❌", f"HCP ACK error: {e}")
        return False

def test_acp_bridge():
    """Test 4: ACP Bridge (TCP → Unix Socket)."""
    log("ℹ️", "Test 4: ACP Bridge...")
    
    # Ping
    try:
        resp = send_tcp("<ip>", ACP_BRIDGE_PORT, '{"jsonrpc":"2.0","id":1,"method":"openclaw.ping","params":{}}')
        data = json.loads(resp)
        if data.get("result", {}).get("status") == "pong":
            log("✅", "ACP Bridge Ping OK")
        else:
            log("❌", f"ACP Bridge Ping failed: {resp}")
            return False
    except Exception as e:
        log("❌", f"ACP Bridge connection failed: {e}")
        return False
    
    # Task Start
    session_id = f"test_acp_{int(time.time())}"
    try:
        resp = send_tcp("<ip>", ACP_BRIDGE_PORT, f'{{"jsonrpc":"2.0","id":2,"method":"openclaw.task.start","params":{{"session_id":"{session_id}"}}}}')
        data = json.loads(resp)
        if data.get("result", {}).get("ack"):
            log("✅", f"ACP Bridge Task Start OK (session: {session_id})")
        else:
            log("❌", f"ACP Bridge Task Start failed: {resp}")
            return False
    except Exception as e:
        log("❌", f"ACP Bridge Task Start error: {e}")
        return False
    
    return True

def test_stale_detection_v2():
    """Test 5: Stale Detection v2 (dual-indicator)."""
    log("ℹ️", "Test 5: Stale Detection v2...")
    
    # Read the integration code and verify the logic
    integration_file = HERMES_HOME / "hermes-agent" / "utils" / "hcp_integration.py"
    if not integration_file.exists():
        log("❌", f"Integration file not found: {integration_file}")
        return False
    
    content = integration_file.read_text()
    
    # Check for dual-indicator logic
    if "current_api_count" in content and "prev_api_count" in content:
        log("✅", "Stale Detection v2: dual-indicator logic found")
    else:
        log("❌", "Stale Detection v2: dual-indicator logic NOT found")
        return False
    
    if "current_step" in content and "prev_step" in content:
        log("✅", "Stale Detection v2: step comparison found")
    else:
        log("❌", "Stale Detection v2: step comparison NOT found")
        return False
    
    return True

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("HCP FULL CHAIN TEST SUITE")
    print("=" * 60)
    print(f"Socket: {HCP_SOCKET}")
    print(f"ACP Bridge Port: {ACP_BRIDGE_PORT}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()
    
    results = []
    
    # Test 1: HCP Server
    results.append(("HCP Server", test_hcp_server()))
    print()
    
    # Test 2: Heartbeat
    results.append(("HCP Heartbeat", test_hcp_heartbeat()))
    print()
    
    # Test 3: ACK
    results.append(("HCP ACK", test_hcp_ack()))
    print()
    
    # Test 4: ACP Bridge
    results.append(("ACP Bridge", test_acp_bridge()))
    print()
    
    # Test 5: Stale Detection v2
    results.append(("Stale Detection v2", test_stale_detection_v2()))
    print()
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        icon = "✅" if result else "❌"
        print(f"{icon} {name}")
    
    print()
    print(f"Total: {passed}/{total} passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!\n")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())