import http.server
import socketserver
import subprocess
import json
import os
import sys
import tempfile

PORT = 8001

# CMD ekranını gizlemek için Windows flag'i
CREATE_NO_WINDOW = 0x08000000

class BridgeHandler(http.server.SimpleHTTPRequestHandler):
    
    def _read_payload(self):
        """POST body'sini oku ve JSON olarak döndür."""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        return json.loads(post_data.decode('utf-8'))

    def _launch_script(self, script_name, json_path, wait_for_completion=False):
        """Bir Python scriptini başlatır. İstenirse tamamlanana kadar bekler."""
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), script_name)
        cmd = ["python", script_path, json_path] if sys.platform == "win32" else ["python3", script_path, json_path]
        
        if wait_for_completion:
            if sys.platform == "win32":
                result = subprocess.run(cmd, creationflags=CREATE_NO_WINDOW, capture_output=True, text=True)
            else:
                result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or f"{script_name} failed with code {result.returncode}")
            return

        if sys.platform == "win32":
            # Windows: CMD ekranı açılmadan arka planda çalıştır
            subprocess.Popen(cmd, creationflags=CREATE_NO_WINDOW)
        else:
            subprocess.Popen(cmd)

    def _success(self, data):
        """200 yanıtı gönder."""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _error(self, msg, code=500):
        """Hata yanıtı gönder."""
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"error": str(msg)}).encode())

    def do_POST(self):
        # ─── ENDPOINT 1: Canlı AI Vizyon Şovu ───
        if self.path == '/launch-vision':
            try:
                payload = self._read_payload()
                url = payload.get("url", "https://google.com")
                elements = payload.get("elements", None)
                wait_for_completion = bool(payload.get("wait_for_completion", False))

                print(f"🚨 [Bridge] AI Görüş Şovu talebi: {url}")
                if elements:
                    print(f"   → Docker'dan {len(elements)} element verisi alındı (DINO tekrar yüklenmeyecek!)")
                if wait_for_completion:
                    print("   → Senkron mod: Vision Inspector tamamlanana kadar beklenecek.")

                # Veriyi geçici JSON dosyasına yaz
                tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
                json.dump(payload, tmp, ensure_ascii=False)
                tmp.close()

                self._launch_script("vision_inspector.py", tmp.name, wait_for_completion=wait_for_completion)
                status = "vision_completed" if wait_for_completion else "vision_launched"
                self._success({"status": status})

            except Exception as e:
                print(f"❌ [Bridge] Vision Hatası: {e}")
                self._error(e)

        # ─── ENDPOINT 2: Canlı Test Yürütme ───
        elif self.path == '/deploy-test':
            try:
                payload = self._read_payload()
                test_title = payload.get("test_title", "Adsız Test")
                url = payload.get("url", "")
                steps = payload.get("steps", [])

                print(f"🚀 [Bridge] Canlı Test: '{test_title}' | URL: {url} | Adım: {len(steps)}")

                # Veriyi geçici JSON dosyasına yaz
                tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
                json.dump(payload, tmp, ensure_ascii=False)
                tmp.close()

                self._launch_script("deploy_inspector.py", tmp.name)
                self._success({"status": "deploy_launched"})

            except Exception as e:
                print(f"❌ [Bridge] Deploy Hatası: {e}")
                self._error(e)

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """HTTP log'larını bastır (gereksiz çıktıları engelleriz)."""
        pass  # Bridge kendi loglamasını yapıyor


# Sunucuyu başlat
with socketserver.TCPServer(("0.0.0.0", PORT), BridgeHandler) as httpd:
    print(f"🌉 [VisionQA Desktop Bridge] {PORT} portunda dinleniyor...")
    print("🤖 Sistem otonom modda. Docker'dan gelecek emirler bekleniyor.")
    print("   /launch-vision → Canlı AI Vizyon Şovu")
    print("   /deploy-test   → Canlı Test Yürütme")
    httpd.serve_forever()
